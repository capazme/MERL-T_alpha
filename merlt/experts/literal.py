"""
Literal Expert
===============

Expert specializzato nell'interpretazione letterale.

Fondamento teorico: Art. 12, comma I, disp. prel. c.c.
"Nell'applicare la legge non si può ad essa attribuire altro senso
che quello fatto palese dal significato proprio delle parole
secondo la connessione di esse..."

L'interpretazione letterale è il primo e fondamentale canone ermeneutico:
- Focus sul TESTO della norma
- "Significato proprio delle parole" = significato tecnico-giuridico se esiste,
  altrimenti significato comune
- Limite: "in claris non fit interpretatio"

Approccio:
1. Recupera il testo esatto della norma
2. Identifica termini tecnici e definizioni legali
3. Analizza la struttura sintattica
4. Segue riferimenti interni (rinvii normativi)
5. Produce interpretazione basata sul dato testuale
"""

import structlog
from typing import Dict, Any, Optional, List

from merlt.experts.base import (
    BaseExpert,
    ExpertContext,
    ExpertResponse,
    LegalSource,
    ReasoningStep,
    ConfidenceFactors,
)
from merlt.tools import BaseTool, SemanticSearchTool, GraphSearchTool

log = structlog.get_logger()


class LiteralExpert(BaseExpert):
    """
    Expert per interpretazione letterale (art. 12, I disp. prel. c.c.).

    Epistemologia: Positivismo giuridico
    Focus: Cosa DICE la legge (interpretazione basata sul testo)

    Tools principali:
    - semantic_search: Ricerca semantica per trovare norme rilevanti
    - graph_search: Navigazione grafo per seguire riferimenti

    Traversal weights:
    - CONTIENE: 1.0 (struttura interna articolo)
    - DISCIPLINA: 0.95 (relazione norma-concetto)
    - DEFINISCE: 0.95 (definizioni legali)
    - RINVIA: 0.90 (riferimenti normativi)
    - MODIFICA: 0.85 (versioni successive)

    Esempio:
        >>> from merlt.experts import LiteralExpert
        >>> from merlt.tools import SemanticSearchTool
        >>>
        >>> expert = LiteralExpert(
        ...     tools=[SemanticSearchTool(retriever, embeddings)],
        ...     ai_service=openrouter_service
        ... )
        >>> response = await expert.analyze(context)
        >>> print(response.interpretation)
    """

    expert_type = "literal"
    description = "Interpretazione letterale (art. 12, I disp. prel. c.c.)"

    # Pesi default per traversal grafo
    DEFAULT_TRAVERSAL_WEIGHTS = {
        "contiene": 1.0,
        "disciplina": 0.95,
        "definisce": 0.95,
        "rinvia": 0.90,
        "modifica": 0.85,
        "abroga": 0.80,
        "cita": 0.75,
        "default": 0.50
    }

    def __init__(
        self,
        tools: Optional[List[BaseTool]] = None,
        config: Optional[Dict[str, Any]] = None,
        ai_service: Any = None
    ):
        """
        Inizializza LiteralExpert.

        Args:
            tools: Tools per ricerca (SemanticSearchTool, GraphSearchTool)
            config: Configurazione (prompt, temperature, traversal_weights)
            ai_service: Servizio AI per LLM calls
        """
        # Merge traversal weights with defaults
        config = config or {}
        if "traversal_weights" not in config:
            config["traversal_weights"] = self.DEFAULT_TRAVERSAL_WEIGHTS

        super().__init__(tools=tools, config=config, ai_service=ai_service)

        # Override prompt template for literal interpretation
        self.prompt_template = self._get_literal_prompt()

    def _get_literal_prompt(self) -> str:
        """Prompt specifico per interpretazione letterale."""
        return """Sei un esperto giuridico specializzato nell'INTERPRETAZIONE LETTERALE.

Il tuo approccio si basa sull'art. 12, comma I, delle disposizioni preliminari al codice civile:
"Nell'applicare la legge non si può ad essa attribuire altro senso che quello fatto palese
dal significato proprio delle parole secondo la connessione di esse..."

## METODOLOGIA

1. **SIGNIFICATO PROPRIO DELLE PAROLE**
   - Usa il significato TECNICO-GIURIDICO se esiste una definizione legale
   - Altrimenti usa il significato COMUNE delle parole
   - Verifica sempre se esistono definizioni nella stessa legge o in leggi collegate

2. **CONNESSIONE DELLE PAROLE**
   - Analizza la struttura sintattica della norma
   - Considera la collocazione sistematica (capo, sezione, titolo)
   - Segui i rinvii normativi interni

3. **LIMITI**
   - "In claris non fit interpretatio" - se il testo è chiaro, non servono altri canoni
   - NON usare argomenti teleologici o sistematici
   - NON speculare sull'intenzione del legislatore

## OUTPUT

Rispondi in JSON con questa struttura:
{
    "interpretation": "Interpretazione letterale in italiano",
    "legal_basis": [
        {
            "source_type": "norm",
            "source_id": "URN della norma",
            "citation": "Citazione formale (es. Art. 1321 c.c.)",
            "excerpt": "Testo rilevante",
            "relevance": "Perché questa fonte è rilevante"
        }
    ],
    "reasoning_steps": [
        {
            "step_number": 1,
            "description": "Descrizione del passo",
            "sources": ["source_id1", "source_id2"]
        }
    ],
    "confidence": 0.0-1.0,
    "confidence_factors": {
        "norm_clarity": 0.0-1.0,
        "jurisprudence_alignment": 0.0-1.0,
        "contextual_ambiguity": 0.0-1.0,
        "source_availability": 0.0-1.0
    },
    "limitations": "Cosa non hai potuto considerare"
}

IMPORTANTE:
- Cita SEMPRE le norme esatte con URN/articolo
- Riporta il testo letterale delle disposizioni rilevanti
- Spiega il significato tecnico dei termini usati
- Se il testo è ambiguo, segnalalo nelle limitations"""

    async def analyze(self, context: ExpertContext) -> ExpertResponse:
        """
        Analizza la query con approccio letterale.

        Flow:
        1. Usa semantic_search per trovare norme rilevanti
        2. Se ci sono riferimenti normativi, usa graph_search per espandere
        3. Chiama LLM con testo delle norme recuperate
        4. Produce ExpertResponse con interpretazione letterale
        """
        import time
        start_time = time.time()

        log.info(
            f"LiteralExpert analyzing",
            query=context.query_text[:50],
            trace_id=context.trace_id
        )

        # Step 1: Recupera norme rilevanti
        retrieved_sources = await self._retrieve_sources(context)

        # Step 2: Costruisci context arricchito
        enriched_context = ExpertContext(
            query_text=context.query_text,
            query_embedding=context.query_embedding,
            entities=context.entities,
            retrieved_chunks=retrieved_sources,
            metadata=context.metadata,
            trace_id=context.trace_id
        )

        # Step 3: Se abbiamo AI service, chiama LLM
        if self.ai_service:
            response = await self._analyze_with_llm(enriched_context)
        else:
            # Fallback: genera risposta senza LLM
            response = self._analyze_without_llm(enriched_context)

        response.execution_time_ms = (time.time() - start_time) * 1000

        log.info(
            f"LiteralExpert completed",
            confidence=response.confidence,
            sources=len(response.legal_basis),
            time_ms=response.execution_time_ms
        )

        return response

    async def _retrieve_sources(self, context: ExpertContext) -> List[Dict[str, Any]]:
        """Recupera fonti usando i tools disponibili."""
        sources = []

        # Usa chunks già recuperati se presenti
        if context.retrieved_chunks:
            sources.extend(context.retrieved_chunks)

        # Semantic search se disponibile
        semantic_tool = self._tool_registry.get("semantic_search")
        if semantic_tool:
            result = await semantic_tool(
                query=context.query_text,
                top_k=5,
                expert_type="LiteralExpert"
            )
            if result.success and result.data.get("results"):
                sources.extend(result.data["results"])

        # Graph search per espandere riferimenti normativi
        graph_tool = self._tool_registry.get("graph_search")
        if graph_tool and context.norm_references:
            for urn in context.norm_references[:3]:  # Limita a 3 per performance
                result = await graph_tool(
                    start_node=urn,
                    relation_types=["contiene", "definisce", "rinvia"],
                    max_hops=2
                )
                if result.success:
                    for node in result.data.get("nodes", []):
                        sources.append({
                            "text": node.get("properties", {}).get("testo", ""),
                            "urn": node.get("urn", ""),
                            "type": node.get("type", ""),
                            "source": "graph_traversal"
                        })

        return sources

    async def _analyze_with_llm(self, context: ExpertContext) -> ExpertResponse:
        """Analizza con LLM."""
        import json

        # Formatta prompt
        system_prompt = self.prompt_template
        user_prompt = self._format_context_for_llm(context)

        try:
            # Call LLM
            response = await self.ai_service.generate_response_async(
                prompt=f"{system_prompt}\n\n{user_prompt}",
                model=self.model,
                temperature=self.temperature
            )

            # Parse response
            if isinstance(response, dict):
                content = response.get("content", str(response))
                tokens = response.get("usage", {}).get("total_tokens", 0)
            else:
                content = str(response)
                tokens = 0

            # Clean markdown
            content = content.strip()
            if content.startswith("```json"):
                content = content[7:]
            elif content.startswith("```"):
                content = content[3:]
            if content.endswith("```"):
                content = content[:-3]
            content = content.strip()

            # Parse JSON
            data = json.loads(content)

            return self._build_response(data, context, tokens)

        except Exception as e:
            log.error(f"LLM analysis failed: {e}")
            return ExpertResponse(
                expert_type=self.expert_type,
                interpretation=f"Errore nell'analisi: {str(e)}",
                confidence=0.0,
                limitations=str(e),
                trace_id=context.trace_id
            )

    def _analyze_without_llm(self, context: ExpertContext) -> ExpertResponse:
        """Genera risposta basic senza LLM."""
        # Estrai informazioni dai chunks recuperati
        sources = context.retrieved_chunks[:5]

        legal_basis = []
        for chunk in sources:
            legal_basis.append(LegalSource(
                source_type="norm",
                source_id=chunk.get("urn", chunk.get("chunk_id", "")),
                citation=chunk.get("urn", ""),
                excerpt=chunk.get("text", "")[:500],
                relevance="Recuperato per similarità semantica"
            ))

        interpretation = "Fonti recuperate per la query:\n\n"
        for i, chunk in enumerate(sources, 1):
            text = chunk.get("text", "")[:200]
            interpretation += f"{i}. {text}...\n\n"

        interpretation += "\n[Nota: Interpretazione completa richiede servizio AI]"

        return ExpertResponse(
            expert_type=self.expert_type,
            interpretation=interpretation,
            legal_basis=legal_basis,
            confidence=0.3,  # Low confidence without LLM
            limitations="Analisi senza LLM - solo recupero fonti",
            trace_id=context.trace_id
        )

    def _format_context_for_llm(self, context: ExpertContext) -> str:
        """Formatta context per LLM."""
        sections = [
            f"## DOMANDA DELL'UTENTE\n{context.query_text}"
        ]

        if context.norm_references:
            sections.append(f"\n## NORME CITATE NELLA DOMANDA\n" + ", ".join(context.norm_references))

        if context.legal_concepts:
            sections.append(f"\n## CONCETTI GIURIDICI IDENTIFICATI\n" + ", ".join(context.legal_concepts))

        if context.retrieved_chunks:
            sections.append("\n## TESTI NORMATIVI RECUPERATI")
            for i, chunk in enumerate(context.retrieved_chunks[:5], 1):
                text = chunk.get("text", "")
                urn = chunk.get("urn", chunk.get("chunk_id", "N/A"))
                score = chunk.get("final_score", chunk.get("similarity_score", "N/A"))
                sections.append(f"\n### Fonte {i} (URN: {urn}, score: {score})\n{text}")

        return "\n".join(sections)

    def _build_response(
        self,
        data: Dict[str, Any],
        context: ExpertContext,
        tokens: int
    ) -> ExpertResponse:
        """Costruisce ExpertResponse da JSON LLM."""
        # Parse legal_basis
        legal_basis = []
        for lb in data.get("legal_basis", []):
            legal_basis.append(LegalSource(
                source_type=lb.get("source_type", "norm"),
                source_id=lb.get("source_id", ""),
                citation=lb.get("citation", ""),
                excerpt=lb.get("excerpt", ""),
                relevance=lb.get("relevance", "")
            ))

        # Parse reasoning_steps
        reasoning_steps = []
        for rs in data.get("reasoning_steps", []):
            reasoning_steps.append(ReasoningStep(
                step_number=rs.get("step_number", 0),
                description=rs.get("description", ""),
                sources=rs.get("sources", [])
            ))

        # Parse confidence_factors
        cf_data = data.get("confidence_factors", {})
        confidence_factors = ConfidenceFactors(
            norm_clarity=cf_data.get("norm_clarity", 0.5),
            jurisprudence_alignment=cf_data.get("jurisprudence_alignment", 0.5),
            contextual_ambiguity=cf_data.get("contextual_ambiguity", 0.5),
            source_availability=cf_data.get("source_availability", 0.5)
        )

        return ExpertResponse(
            expert_type=self.expert_type,
            interpretation=data.get("interpretation", ""),
            legal_basis=legal_basis,
            reasoning_steps=reasoning_steps,
            confidence=data.get("confidence", 0.5),
            confidence_factors=confidence_factors,
            limitations=data.get("limitations", ""),
            trace_id=context.trace_id,
            tokens_used=tokens
        )
