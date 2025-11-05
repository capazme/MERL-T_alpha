"""
LLM Extractor
=============

Uses Large Language Models (Claude/GPT-4) via OpenRouter to extract
structured entities and relationships from legal text.

Extracts according to the MERL-T Knowledge Graph schema (23 node types).
"""

import asyncio
import json
import logging
from typing import List, Dict, Any, Optional
import aiohttp
from datetime import datetime

from .models import (
    DocumentSegment,
    ExtractedEntity,
    ExtractedRelationship,
    ExtractionResult,
    NodeType,
    RelationType,
)

logger = logging.getLogger(__name__)


# =================================================================
# EXTRACTION PROMPT TEMPLATE
# =================================================================

EXTRACTION_PROMPT_TEMPLATE = """You are a legal knowledge extraction system. Extract structured entities and relationships from Italian legal text.

INSTRUCTIONS:
1. Read the text carefully
2. Identify ALL legal entities (see ENTITY TYPES below)
3. Identify ALL relationships between entities
4. Return valid JSON only (no explanations)
5. Assign confidence scores (0.0-1.0) based on clarity

ENTITY TYPES (extract ALL applicable):

A. **Norma** - Legal norms (laws, articles, codes, decrees)
   Example: "Art. 1321 c.c.", "Legge n. 40/2004"
   Properties: estremi, titolo, descrizione, testo_vigente, stato

B. **Concetto Giuridico** - Abstract legal concepts
   Example: "buona fede", "simulazione", "contratto"
   Properties: nome, definizione, ambito_di_applicazione

C. **Soggetto Giuridico** - Legal subjects (persons, entities)
   Example: "persona fisica", "società", "ente pubblico"
   Properties: nome, tipo, ruolo

D. **Atto Giudiziario** - Judicial acts (court decisions)
   Example: "Sentenza Cass. n.1234/2023"
   Properties: estremi, descrizione, organo_emittente, data, tipologia

E. **Dottrina** - Legal doctrine/commentary
   Example: "Manuale di diritto civile" by "Torrente & Schlesinger"
   Properties: titolo, autore, descrizione, data_pubblicazione

F. **Procedura** - Legal procedures
   Example: "Processo civile ordinario"
   Properties: nome, descrizione, ambito, tipologia

G. **Principio Giuridico** - Legal principles
   Example: "Principio di legalità", "Buona fede contrattuale"
   Properties: nome, tipo, descrizione, ambito_applicazione

H. **Responsabilità** - Legal responsibility/liability
   Example: "Responsabilità civile", "Responsabilità penale"
   Properties: tipo_responsabilita, descrizione, fondamento

I. **Diritto Soggettivo** - Subjective rights
   Example: "Diritto di proprietà", "Diritto al nome"
   Properties: nome, tipo_diritto, descrizione, opponibilita

J. **Sanzione** - Sanctions/penalties
   Example: "Multa da 500 a 5000 EUR"
   Properties: tipo, descrizione, entita_minima, entita_massima

K. **Definizione Legale** - Legal definitions
   Example: Definition of "contratto" in Art. 1321
   Properties: termine, definizione, ambito_applicazione

L. **Fatto Giuridico** - Legal facts
   Example: "Nascita", "Morte", "Matrimonio"
   Properties: tipo_fatto, descrizione, effetti_giuridici

M. **Modalità Giuridica** - Deontic modalities (obligations, permissions)
   Example: "Obbligo di contrarre", "Permesso di agire"
   Properties: tipo_modalita, descrizione, soggetto_attivo

RELATIONSHIP TYPES (extract ALL applicable):

- **MODIFICA** - One norm modifies another
- **ABROGA** - One norm repeals another
- **INTEGRA** - One norm supplements another
- **APPLICA** - A principle/concept is applied
- **INTERPRETA** - An act interprets a norm
- **TRATTA** - Text discusses a concept
- **CITA** - Text cites another source
- **DEFINISCE** - Text defines a term
- **CONTIENE** - A norm contains sub-elements (articles, clauses)
- **PARTE_DI** - An element is part of a larger whole
- **PRESUPPONE** - One element presupposes another

TEXT TO ANALYZE:
```
{text}
```

RESPOND WITH VALID JSON ONLY:
{{
  "entities": [
    {{
      "type": "Norma",
      "label": "Art. 1321 c.c.",
      "properties": {{
        "estremi": "Art. 1321 c.c.",
        "titolo": "Nozione di contratto",
        "descrizione": "Definisce il contratto come accordo tra parti",
        "testo_vigente": "...",
        "stato": "vigente"
      }},
      "confidence": 0.95
    }},
    {{
      "type": "Concetto Giuridico",
      "label": "Contratto",
      "properties": {{
        "nome": "Contratto",
        "definizione": "Accordo di due o più parti per costituire, regolare o estinguere tra loro un rapporto giuridico patrimoniale",
        "ambito_di_applicazione": "Diritto civile - obbligazioni"
      }},
      "confidence": 1.0
    }}
  ],
  "relationships": [
    {{
      "source_label": "Art. 1321 c.c.",
      "target_label": "Contratto",
      "type": "DEFINISCE",
      "properties": {{}},
      "confidence": 1.0
    }}
  ]
}}
"""


class LLMExtractor:
    """
    Extracts entities and relationships from legal text using LLMs.

    Uses OpenRouter API to access multiple LLM providers.
    """

    def __init__(
        self,
        api_key: str,
        model: str = "anthropic/claude-3.5-sonnet",
        temperature: float = 0.1,
        max_tokens: int = 4000,
        timeout_seconds: int = 60,
    ):
        """
        Initialize LLM extractor.

        Args:
            api_key: OpenRouter API key
            model: Model to use (e.g., "anthropic/claude-3.5-sonnet")
            temperature: Temperature for generation (lower = more consistent)
            max_tokens: Maximum tokens in response
            timeout_seconds: Request timeout
        """
        self.api_key = api_key
        self.model = model
        self.temperature = temperature
        self.max_tokens = max_tokens
        self.timeout_seconds = timeout_seconds
        self.api_url = "https://openrouter.ai/api/v1/chat/completions"
        self.logger = logger

        # Pricing (approximate, per 1M tokens)
        self.pricing = {
            "anthropic/claude-3.5-sonnet": {
                "input": 3.0,   # $3 per 1M input tokens
                "output": 15.0,  # $15 per 1M output tokens
            },
            "openai/gpt-4-turbo": {
                "input": 10.0,
                "output": 30.0,
            },
            "openai/gpt-4o": {
                "input": 2.5,
                "output": 10.0,
            },
        }

    async def extract_from_segment(
        self,
        segment: DocumentSegment
    ) -> ExtractionResult:
        """
        Extract entities and relationships from a single segment.

        Args:
            segment: Document segment to process

        Returns:
            ExtractionResult with extracted entities/relationships
        """
        start_time = datetime.utcnow()

        try:
            # Build prompt
            prompt = EXTRACTION_PROMPT_TEMPLATE.format(text=segment.text)

            # Call LLM
            response = await self._call_llm(prompt)

            # Parse response
            entities, relationships = self._parse_response(
                response["content"],
                segment.provenance
            )

            # Calculate cost
            tokens_input = response.get("usage", {}).get("prompt_tokens", 0)
            tokens_output = response.get("usage", {}).get("completion_tokens", 0)
            cost = self._calculate_cost(tokens_input, tokens_output)

            duration = (datetime.utcnow() - start_time).total_seconds()

            return ExtractionResult(
                segment=segment,
                entities=entities,
                relationships=relationships,
                llm_model=self.model,
                cost_usd=cost,
                duration_seconds=duration,
                tokens_input=tokens_input,
                tokens_output=tokens_output,
                raw_response=response["content"],
            )

        except Exception as e:
            self.logger.error(f"Error extracting from segment: {e}", exc_info=True)
            duration = (datetime.utcnow() - start_time).total_seconds()

            return ExtractionResult(
                segment=segment,
                entities=[],
                relationships=[],
                llm_model=self.model,
                duration_seconds=duration,
                error=str(e),
            )

    async def extract_batch(
        self,
        segments: List[DocumentSegment],
        max_concurrent: int = 3
    ) -> List[ExtractionResult]:
        """
        Extract from multiple segments in parallel.

        Args:
            segments: List of segments to process
            max_concurrent: Maximum concurrent LLM requests

        Returns:
            List of ExtractionResult objects
        """
        self.logger.info(f"Extracting from {len(segments)} segments (max {max_concurrent} concurrent)")

        # Process in batches to limit concurrency
        results = []
        for i in range(0, len(segments), max_concurrent):
            batch = segments[i:i + max_concurrent]
            batch_results = await asyncio.gather(
                *[self.extract_from_segment(seg) for seg in batch],
                return_exceptions=True
            )

            for result in batch_results:
                if isinstance(result, Exception):
                    self.logger.error(f"Batch extraction error: {result}")
                else:
                    results.append(result)

            # Log progress
            self.logger.info(f"Processed {min(i + max_concurrent, len(segments))}/{len(segments)} segments")

        return results

    async def _call_llm(self, prompt: str) -> Dict[str, Any]:
        """
        Call OpenRouter API with prompt.

        Args:
            prompt: The prompt to send

        Returns:
            Response dict with content and usage stats
        """
        headers = {
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json",
        }

        payload = {
            "model": self.model,
            "messages": [
                {
                    "role": "user",
                    "content": prompt
                }
            ],
            "temperature": self.temperature,
            "max_tokens": self.max_tokens,
        }

        timeout = aiohttp.ClientTimeout(total=self.timeout_seconds)

        async with aiohttp.ClientSession(timeout=timeout) as session:
            async with session.post(
                self.api_url,
                headers=headers,
                json=payload
            ) as response:
                if response.status != 200:
                    error_text = await response.text()
                    raise RuntimeError(
                        f"OpenRouter API error (status {response.status}): {error_text}"
                    )

                data = await response.json()

                return {
                    "content": data["choices"][0]["message"]["content"],
                    "usage": data.get("usage", {}),
                }

    def _parse_response(
        self,
        response_text: str,
        provenance
    ) -> tuple[List[ExtractedEntity], List[ExtractedRelationship]]:
        """
        Parse JSON response from LLM.

        Args:
            response_text: Raw LLM response
            provenance: Provenance for extracted entities

        Returns:
            Tuple of (entities, relationships)
        """
        try:
            # Extract JSON from response (may have markdown code blocks)
            json_str = response_text
            if "```json" in response_text:
                json_str = response_text.split("```json")[1].split("```")[0].strip()
            elif "```" in response_text:
                json_str = response_text.split("```")[1].split("```")[0].strip()

            data = json.loads(json_str)

            # Parse entities
            entities = []
            for ent_data in data.get("entities", []):
                try:
                    # Map type string to NodeType enum
                    node_type_str = ent_data["type"]
                    node_type = self._map_to_node_type(node_type_str)

                    entity = ExtractedEntity(
                        type=node_type,
                        label=ent_data["label"],
                        properties=ent_data.get("properties", {}),
                        confidence=ent_data.get("confidence", 0.7),
                        provenance=provenance,
                    )
                    entities.append(entity)
                except Exception as e:
                    self.logger.warning(f"Skipping invalid entity: {e}")

            # Parse relationships
            relationships = []
            for rel_data in data.get("relationships", []):
                try:
                    # Map type string to RelationType enum
                    rel_type_str = rel_data["type"]
                    rel_type = RelationType[rel_type_str]

                    relationship = ExtractedRelationship(
                        source_label=rel_data["source_label"],
                        target_label=rel_data["target_label"],
                        type=rel_type,
                        properties=rel_data.get("properties", {}),
                        confidence=rel_data.get("confidence", 0.7),
                        provenance=provenance,
                    )
                    relationships.append(relationship)
                except Exception as e:
                    self.logger.warning(f"Skipping invalid relationship: {e}")

            return entities, relationships

        except json.JSONDecodeError as e:
            self.logger.error(f"Failed to parse LLM response as JSON: {e}")
            self.logger.debug(f"Response text: {response_text[:500]}")
            return [], []

    def _map_to_node_type(self, type_str: str) -> NodeType:
        """Map string type to NodeType enum."""
        type_map = {
            "Norma": NodeType.NORMA,
            "Concetto Giuridico": NodeType.CONCETTO_GIURIDICO,
            "Soggetto Giuridico": NodeType.SOGGETTO_GIURIDICO,
            "Atto Giudiziario": NodeType.ATTO_GIUDIZIARIO,
            "Dottrina": NodeType.DOTTRINA,
            "Procedura": NodeType.PROCEDURA,
            "Principio Giuridico": NodeType.PRINCIPIO_GIURIDICO,
            "Responsabilità": NodeType.RESPONSABILITA,
            "Diritto Soggettivo": NodeType.DIRITTO_SOGGETTIVO,
            "Sanzione": NodeType.SANZIONE,
            "Definizione Legale": NodeType.DEFINIZIONE_LEGALE,
            "Fatto Giuridico": NodeType.FATTO_GIURIDICO,
            "Modalità Giuridica": NodeType.MODALITA_GIURIDICA,
        }

        return type_map.get(type_str, NodeType.CONCETTO_GIURIDICO)  # Default fallback

    def _calculate_cost(self, tokens_input: int, tokens_output: int) -> float:
        """Calculate cost in USD for the API call."""
        pricing = self.pricing.get(self.model, {"input": 5.0, "output": 15.0})

        cost_input = (tokens_input / 1_000_000) * pricing["input"]
        cost_output = (tokens_output / 1_000_000) * pricing["output"]

        return cost_input + cost_output
