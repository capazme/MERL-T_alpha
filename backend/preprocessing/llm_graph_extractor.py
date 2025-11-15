# =============================================================================
# LLM-Driven Knowledge Graph Extractor
# =============================================================================
#
# This module uses Claude 3.5 Sonnet to autonomously extract entities and
# relationships from legal documents (Codice Civile + BrocardiInfo).
#
# Features:
# - Intelligent entity extraction (Norme, Concetti, Soggetti, Principi, etc.)
# - Relationship inference (CITA, MODIFICA, DEFINISCE, APPLICA, etc.)
# - BrocardiInfo enrichment (brocardi → principi, massime → giurisprudenza)
# - Citation analysis (cross-references between articles)
# - Concept definition extraction
#
# Output:
# - Staging entities (for manual review)
# - Staging relationships (for manual review)
# - Confidence scores per entity/relationship
#
# The user validates the first batch → patterns learned → auto-approval
#
# =============================================================================

import asyncio
import json
from typing import List, Dict, Any, Optional, Tuple
from dataclasses import dataclass, field
import aiohttp
import structlog

log = structlog.get_logger(__name__)


# =============================================================================
# Data Models
# =============================================================================

@dataclass
class ExtractedEntity:
    """
    Entity extracted by LLM from legal document.
    """
    entity_type: str  # Norma, ConcettoGiuridico, SoggettoGiuridico, etc.
    properties: Dict[str, Any]
    confidence: float  # 0.0-1.0
    source_text: Optional[str] = None  # Text snippet supporting this extraction
    reasoning: Optional[str] = None  # LLM's reasoning for this entity

    def to_staging_dict(self) -> Dict[str, Any]:
        """Convert to staging entity format."""
        return {
            'entity_type': self.entity_type,
            'properties': self.properties,
            'confidence': self.confidence,
            'provenance': {
                'source': 'llm_graph_extractor',
                'source_text': self.source_text,
                'llm_reasoning': self.reasoning
            }
        }


@dataclass
class ExtractedRelationship:
    """
    Relationship extracted by LLM.
    """
    relationship_type: str  # CITA, MODIFICA, DEFINISCE, etc.
    source_entity: Dict[str, Any]  # Source entity identification
    target_entity: Dict[str, Any]  # Target entity identification
    properties: Dict[str, Any] = field(default_factory=dict)
    confidence: float = 0.0
    source_text: Optional[str] = None
    reasoning: Optional[str] = None

    def to_staging_dict(self) -> Dict[str, Any]:
        """Convert to staging relationship format."""
        return {
            'type': self.relationship_type,
            'source': self.source_entity,
            'target': self.target_entity,
            'properties': self.properties,
            'confidence': self.confidence,
            'provenance': {
                'source': 'llm_graph_extractor',
                'source_text': self.source_text,
                'llm_reasoning': self.reasoning
            }
        }


@dataclass
class GraphExtractionResult:
    """
    Complete extraction result for a document.
    """
    source_article: str  # Article number/identifier
    entities: List[ExtractedEntity] = field(default_factory=list)
    relationships: List[ExtractedRelationship] = field(default_factory=list)
    total_entities: int = 0
    total_relationships: int = 0
    avg_confidence_entities: float = 0.0
    avg_confidence_relationships: float = 0.0
    llm_cost_usd: float = 0.0
    processing_time_seconds: float = 0.0

    def finalize(self):
        """Calculate statistics."""
        self.total_entities = len(self.entities)
        self.total_relationships = len(self.relationships)

        if self.entities:
            self.avg_confidence_entities = sum(e.confidence for e in self.entities) / len(self.entities)

        if self.relationships:
            self.avg_confidence_relationships = sum(r.confidence for r in self.relationships) / len(self.relationships)


# =============================================================================
# LLM Prompt Templates
# =============================================================================

GRAPH_EXTRACTION_SYSTEM_PROMPT = """Sei un esperto di diritto civile italiano specializzato nell'analisi di testi normativi e nell'estrazione di knowledge graph.

Il tuo compito è analizzare articoli del Codice Civile italiano ed estrarre:
1. **Entità** menzionate o definite nell'articolo
2. **Relazioni** tra l'articolo e altre entità

**TIPI DI ENTITÀ** (13 categorie):
1. Norma - Altri articoli/norme citate (es. "art. 2043", "codice penale")
2. ConcettoGiuridico - Concetti legali (es. "responsabilità extracontrattuale", "capacità giuridica")
3. SoggettoGiuridico - Soggetti di diritto (es. "persona fisica", "ente", "società")
4. AttoGiudiziario - Atti processuali (es. "sentenza", "decreto ingiuntivo")
5. Dottrina - Riferimenti dottrinali/accademici
6. Procedura - Procedure legali (es. "procedimento civile", "esecuzione forzata")
7. PrincipioGiuridico - Principi di diritto (es. "neminem laedere", "buona fede")
8. Responsabilita - Tipi di responsabilità (es. "responsabilità civile", "colpa")
9. DirittoSoggettivo - Diritti soggettivi (es. "diritto di proprietà", "diritto al nome")
10. Sanzione - Sanzioni/pene (es. "risarcimento danni", "nullità")
11. DefinizioneLegale - Definizioni legali fornite dall'articolo
12. FattoGiuridico - Fatti rilevanti per il diritto (es. "fatto illecito", "contratto")
13. ModalitaGiuridica - Modalità deontiche (es. "obbligo", "divieto", "facoltà")

**TIPI DI RELAZIONI** (15 categorie principali):
1. CITA - L'articolo cita un'altra norma
2. MODIFICA - L'articolo modifica un'altra norma
3. ABROGA - L'articolo abroga un'altra norma
4. INTEGRA - L'articolo integra un'altra norma
5. APPLICA - L'articolo applica un principio/concetto
6. INTERPRETA - L'articolo interpreta un'altra norma
7. DEFINISCE - L'articolo definisce un concetto
8. PRESUPPONE - L'articolo presuppone un concetto/fatto
9. REGOLA - L'articolo regola una procedura/materia
10. STABILISCE - L'articolo stabilisce un diritto/obbligo
11. PREVEDE - L'articolo prevede una sanzione/conseguenza
12. DEROGA - L'articolo deroga a un principio/norma
13. RICHIAMA - L'articolo richiama una definizione/disciplina
14. HA_PRINCIPIO - L'articolo è fondato su un principio (da BrocardiInfo)
15. CITATO_IN - L'articolo è citato in giurisprudenza (da BrocardiInfo)

**REGOLE DI ESTRAZIONE**:
1. Estrai SOLO entità e relazioni ESPLICITAMENTE menzionate o fortemente implicite nel testo
2. NON inventare relazioni non supportate dal testo
3. Per ogni entità/relazione, fornisci il testo di supporto (citazione esatta)
4. Assegna un confidence score (0.0-1.0):
   - 1.0: Esplicitamente dichiarato ("l'articolo X cita Y")
   - 0.9: Fortemente implicito con terminologia tecnica
   - 0.8: Implicito con ragionamento solido
   - 0.7: Implicito con ragionamento moderato
   - <0.7: Speculativo (da evitare)
5. Per citazioni di articoli, estrai numero articolo, codice, e contesto
6. Per definizioni, identifica il concetto definito e la definizione completa

**FORMATO OUTPUT**: JSON con struttura:
{
  "entities": [
    {
      "entity_type": "Norma" | "ConcettoGiuridico" | ...,
      "properties": {
        "nome": "...",
        "numero_articolo": "..." (se Norma),
        "codice": "..." (se Norma),
        "definizione": "..." (se DefinizioneLegale),
        // altri campi specifici per tipo
      },
      "confidence": 0.0-1.0,
      "source_text": "citazione esatta dal testo",
      "reasoning": "perché hai estratto questa entità"
    }
  ],
  "relationships": [
    {
      "type": "CITA" | "MODIFICA" | "DEFINISCE" | ...,
      "source": {
        "entity_type": "Norma",
        "numero_articolo": "..." // identificativo dell'articolo corrente
      },
      "target": {
        "entity_type": "...",
        "identifier": "..." // identificativo entità target
      },
      "confidence": 0.0-1.0,
      "source_text": "citazione esatta",
      "reasoning": "perché questa relazione esiste"
    }
  ]
}

**IMPORTANTE**: Sii conservativo. È meglio non estrarre che estrarre erroneamente."""


def build_extraction_prompt(article_text: str, article_number: str, brocardi_info: Optional[Dict] = None) -> str:
    """
    Build user prompt for graph extraction.

    Args:
        article_text: Full article text from Normattiva
        article_number: Article number (e.g., "2043")
        brocardi_info: Optional BrocardiInfo data

    Returns:
        Formatted prompt string
    """
    prompt = f"""Analizza il seguente articolo del Codice Civile ed estrai entità e relazioni per il knowledge graph.

**ARTICOLO**: {article_number}

**TESTO NORMATTIVO**:
{article_text}
"""

    if brocardi_info:
        prompt += "\n\n**DATI DOTTRINALI E GIURISPRUDENZIALI** (Brocardi.it):\n"

        if brocardi_info.get('position'):
            prompt += f"- Posizione: {brocardi_info['position']}\n"

        if brocardi_info.get('brocardi'):
            brocardi_list = ', '.join(brocardi_info['brocardi']) if isinstance(brocardi_info['brocardi'], list) else brocardi_info['brocardi']
            prompt += f"- Brocardi (principi latini): {brocardi_list}\n"

        if brocardi_info.get('ratio'):
            prompt += f"- Ratio legis: {brocardi_info['ratio']}\n"

        if brocardi_info.get('spiegazione'):
            prompt += f"- Spiegazione: {brocardi_info['spiegazione'][:300]}...\n"

        if brocardi_info.get('massime'):
            massime_count = len(brocardi_info['massime']) if isinstance(brocardi_info['massime'], list) else 0
            prompt += f"- Massime giurisprudenziali: {massime_count} sentenze citate\n"

    prompt += """

**TASK**: Estrai entità e relazioni seguendo le istruzioni del system prompt.

Rispondi SOLO con JSON valido (senza markdown, senza spiegazioni extra)."""

    return prompt


# =============================================================================
# LLM Graph Extractor
# =============================================================================

class LLMGraphExtractor:
    """
    Extract knowledge graph (entities + relationships) from legal documents using LLM.

    Uses Claude 3.5 Sonnet via OpenRouter for intelligent extraction.
    """

    def __init__(
        self,
        openrouter_api_key: str,
        model: str = "anthropic/claude-3.5-sonnet",
        temperature: float = 0.1,  # Low temperature for consistent extraction
        max_tokens: int = 8000
    ):
        """
        Initialize LLM extractor.

        Args:
            openrouter_api_key: OpenRouter API key
            model: Model identifier (default: Claude 3.5 Sonnet)
            temperature: Sampling temperature (default: 0.1 for consistency)
            max_tokens: Max tokens in response
        """
        self.api_key = openrouter_api_key
        self.model = model
        self.temperature = temperature
        self.max_tokens = max_tokens
        self.api_url = "https://openrouter.ai/api/v1/chat/completions"

        log.info(
            "LLMGraphExtractor initialized",
            model=model,
            temperature=temperature
        )

    async def extract_graph(
        self,
        article_text: str,
        article_number: str,
        brocardi_info: Optional[Dict] = None
    ) -> GraphExtractionResult:
        """
        Extract knowledge graph from a single article.

        Args:
            article_text: Full article text
            article_number: Article number (e.g., "2043")
            brocardi_info: Optional BrocardiInfo enrichment

        Returns:
            GraphExtractionResult with entities and relationships
        """
        import time
        start_time = time.time()

        log.info(
            "Extracting graph from article",
            article_number=article_number,
            has_brocardi=bool(brocardi_info)
        )

        # Build prompt
        user_prompt = build_extraction_prompt(article_text, article_number, brocardi_info)

        # Call LLM
        try:
            response_data = await self._call_llm(user_prompt)

            # Parse JSON response
            entities, relationships = self._parse_llm_response(response_data, article_number)

            # Calculate cost (approximate)
            cost = self._estimate_cost(user_prompt, response_data)

            # Build result
            result = GraphExtractionResult(
                source_article=article_number,
                entities=entities,
                relationships=relationships,
                llm_cost_usd=cost,
                processing_time_seconds=time.time() - start_time
            )
            result.finalize()

            log.info(
                "Graph extraction complete",
                article=article_number,
                entities=result.total_entities,
                relationships=result.total_relationships,
                avg_confidence_entities=round(result.avg_confidence_entities, 3),
                cost_usd=round(cost, 4)
            )

            return result

        except Exception as e:
            log.error(
                "Graph extraction failed",
                article=article_number,
                error=str(e),
                exc_info=True
            )
            # Return empty result on error
            result = GraphExtractionResult(
                source_article=article_number,
                processing_time_seconds=time.time() - start_time
            )
            return result

    async def _call_llm(self, user_prompt: str) -> str:
        """
        Call OpenRouter LLM API.

        Args:
            user_prompt: User prompt text

        Returns:
            LLM response text (JSON string)
        """
        headers = {
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json",
        }

        payload = {
            "model": self.model,
            "messages": [
                {"role": "system", "content": GRAPH_EXTRACTION_SYSTEM_PROMPT},
                {"role": "user", "content": user_prompt}
            ],
            "temperature": self.temperature,
            "max_tokens": self.max_tokens,
        }

        async with aiohttp.ClientSession() as session:
            async with session.post(self.api_url, headers=headers, json=payload) as response:
                if response.status != 200:
                    error_text = await response.text()
                    raise Exception(f"OpenRouter API error: {response.status} - {error_text}")

                data = await response.json()
                return data["choices"][0]["message"]["content"]

    def _parse_llm_response(
        self,
        response_text: str,
        article_number: str
    ) -> Tuple[List[ExtractedEntity], List[ExtractedRelationship]]:
        """
        Parse LLM JSON response into entities and relationships.

        Args:
            response_text: LLM response (JSON string)
            article_number: Source article number

        Returns:
            Tuple of (entities, relationships)
        """
        try:
            # Remove markdown code blocks if present
            response_text = response_text.strip()
            if response_text.startswith("```"):
                response_text = response_text.split("```")[1]
                if response_text.startswith("json"):
                    response_text = response_text[4:]
                response_text = response_text.strip()

            data = json.loads(response_text)

            # Parse entities
            entities = []
            for entity_data in data.get("entities", []):
                entity = ExtractedEntity(
                    entity_type=entity_data.get("entity_type", "Unknown"),
                    properties=entity_data.get("properties", {}),
                    confidence=float(entity_data.get("confidence", 0.5)),
                    source_text=entity_data.get("source_text"),
                    reasoning=entity_data.get("reasoning")
                )
                entities.append(entity)

            # Parse relationships
            relationships = []
            for rel_data in data.get("relationships", []):
                relationship = ExtractedRelationship(
                    relationship_type=rel_data.get("type", "UNKNOWN"),
                    source_entity=rel_data.get("source", {}),
                    target_entity=rel_data.get("target", {}),
                    properties=rel_data.get("properties", {}),
                    confidence=float(rel_data.get("confidence", 0.5)),
                    source_text=rel_data.get("source_text"),
                    reasoning=rel_data.get("reasoning")
                )
                relationships.append(relationship)

            log.debug(
                "Parsed LLM response",
                entities_count=len(entities),
                relationships_count=len(relationships)
            )

            return entities, relationships

        except json.JSONDecodeError as e:
            log.error(
                "Failed to parse LLM response as JSON",
                error=str(e),
                response_preview=response_text[:200]
            )
            return [], []
        except Exception as e:
            log.error(
                "Error parsing LLM response",
                error=str(e),
                exc_info=True
            )
            return [], []

    def _estimate_cost(self, prompt: str, response: str) -> float:
        """
        Estimate cost in USD for LLM call.

        Claude 3.5 Sonnet pricing (via OpenRouter):
        - Input: $3.00 per 1M tokens
        - Output: $15.00 per 1M tokens

        Args:
            prompt: Input prompt
            response: LLM response

        Returns:
            Estimated cost in USD
        """
        # Rough token estimation (1 token ≈ 4 characters)
        input_tokens = len(prompt) / 4
        output_tokens = len(response) / 4

        input_cost = (input_tokens / 1_000_000) * 3.00
        output_cost = (output_tokens / 1_000_000) * 15.00

        return input_cost + output_cost


# =============================================================================
# CLI Entry Point (for testing)
# =============================================================================

async def main():
    """Test LLM graph extractor with Art. 2043."""
    import os

    # Configure logging
    structlog.configure(
        processors=[
            structlog.processors.add_log_level,
            structlog.processors.TimeStamper(fmt="iso"),
            structlog.dev.ConsoleRenderer()
        ]
    )

    api_key = os.getenv("OPENROUTER_API_KEY")
    if not api_key:
        print("Error: OPENROUTER_API_KEY not set")
        return

    # Sample article text (Art. 2043)
    article_text = """Art. 2043
Risarcimento per fatto illecito

Qualunque fatto doloso o colposo, che cagiona ad altri un danno ingiusto, obbliga colui che ha commesso il fatto a risarcire il danno."""

    # Sample BrocardiInfo
    brocardi_info = {
        'position': 'Libro VI - Tutela dei diritti',
        'brocardi': ['Neminem laedere', 'Alterum non laedere'],
        'ratio': 'Fondamento della responsabilità extracontrattuale',
        'spiegazione': 'Articolo fondamentale in materia di illecito aquiliano...'
    }

    # Create extractor
    extractor = LLMGraphExtractor(api_key)

    # Extract graph
    result = await extractor.extract_graph(
        article_text=article_text,
        article_number="2043",
        brocardi_info=brocardi_info
    )

    # Print results
    print("\n" + "=" * 60)
    print("EXTRACTION RESULTS")
    print("=" * 60)
    print(f"Article: {result.source_article}")
    print(f"Entities: {result.total_entities}")
    print(f"Relationships: {result.total_relationships}")
    print(f"Avg Confidence (Entities): {result.avg_confidence_entities:.2f}")
    print(f"Avg Confidence (Relationships): {result.avg_confidence_relationships:.2f}")
    print(f"Cost: ${result.llm_cost_usd:.4f}")
    print(f"Time: {result.processing_time_seconds:.2f}s")

    print("\n" + "-" * 60)
    print("ENTITIES")
    print("-" * 60)
    for entity in result.entities:
        print(f"\n[{entity.entity_type}] Confidence: {entity.confidence:.2f}")
        print(f"  Properties: {entity.properties}")
        if entity.source_text:
            print(f"  Source: \"{entity.source_text[:80]}...\"")
        if entity.reasoning:
            print(f"  Reasoning: {entity.reasoning[:100]}...")

    print("\n" + "-" * 60)
    print("RELATIONSHIPS")
    print("-" * 60)
    for rel in result.relationships:
        print(f"\n[{rel.relationship_type}] Confidence: {rel.confidence:.2f}")
        print(f"  Source: {rel.source_entity}")
        print(f"  Target: {rel.target_entity}")
        if rel.source_text:
            print(f"  Source: \"{rel.source_text[:80]}...\"")


if __name__ == "__main__":
    asyncio.run(main())
