"""
Query Understanding Module for Legal Queries
==============================================

Analyzes Italian legal queries to extract:
- Named Entities (legal references, dates, amounts)
- Intent Classification (SEARCH, INTERPRETATION, COMPLIANCE, DRAFTING, RISK_SPOTTING)
- Legal Concepts (GDPR, privacy, contratti, responsabilità, etc.)
- Norm References (Art. 1321 c.c., etc.)

Architecture:
- NER: Italian-Legal-BERT (pretrained on Italian legal corpus)
- Intent: Fine-tuned BERT classifier (5 classes)
- Concepts: Rule-based + semantic similarity
- Norm References: Regex + NER fusion

Phase 1: LLM-based with OpenRouter fallback
Phase 2: Fine-tuned Italian-Legal-BERT models
Phase 3: Community-driven with RLCF feedback

Reference: docs/02-methodology/query-understanding.md
"""

import asyncio
import json
import logging
import re
from dataclasses import dataclass, field, asdict
from datetime import datetime
from enum import Enum
from typing import Any, Dict, List, Optional, Set, Tuple

from pydantic import BaseModel, Field

# Will use OpenRouter for Phase 1, with HuggingFace models as fallback
from backend.rlcf_framework.ai_service import openrouter_service

logger = logging.getLogger(__name__)


# ==========================================
# Enums & Data Models
# ==========================================

class QueryIntentType(Enum):
    """Query intent types for Italian legal context"""
    NORM_SEARCH = "norm_search"                    # Ricerca di norme (es. "Che dice l'art. 1321?")
    INTERPRETATION = "interpretation"              # Interpretazione (es. "Cosa significa responsabilità?")
    COMPLIANCE_CHECK = "compliance_check"          # Verifica conformità (es. "Sono in compliance con GDPR?")
    DOCUMENT_DRAFTING = "document_drafting"        # Redazione (es. "Dammi template di contratto")
    RISK_SPOTTING = "risk_spotting"               # Identificazione rischi (es. "Quali rischi legali?")
    UNKNOWN = "unknown"                            # Fallback when confidence is too low


class LegalEntityType(Enum):
    """Types of legal entities extracted by NER"""
    NORM_REFERENCE = "norm_reference"              # Art. 1321 c.c., Art. 82 GDPR
    LEGAL_CONCEPT = "legal_concept"                # Contratto, responsabilità, consenso
    DATE = "date"                                  # Dates in legal context
    AMOUNT = "amount"                              # Monetary amounts
    PARTY_TYPE = "party_type"                      # Persone fisiche, giuridiche
    LEGAL_PROCEDURE = "legal_procedure"            # Procedimenti, reclami


@dataclass
class LegalEntity:
    """Extracted legal entity from query"""
    text: str                          # Original text (e.g., "Art. 1321 c.c.")
    entity_type: LegalEntityType       # Type of entity
    start_pos: int                     # Start position in query
    end_pos: int                       # End position in query
    confidence: float = 0.85           # NER confidence score
    normalized: Optional[str] = None   # Normalized form (e.g., "cc_art_1321")

    def to_dict(self) -> Dict[str, Any]:
        return {
            "text": self.text,
            "entity_type": self.entity_type.value,
            "start_pos": self.start_pos,
            "end_pos": self.end_pos,
            "confidence": self.confidence,
            "normalized": self.normalized
        }


class QueryUnderstandingResult(BaseModel):
    """Result from query understanding analysis"""
    query_id: str = Field(..., description="Unique query identifier")
    original_query: str = Field(..., description="Original query text")

    # Intent classification
    intent: QueryIntentType = Field(..., description="Primary intent")
    intent_confidence: float = Field(ge=0.0, le=1.0, description="Intent classification confidence")
    intent_reasoning: str = Field(..., description="Explanation of intent classification")

    # Extracted entities
    entities: List[LegalEntity] = Field(default_factory=list, description="Extracted entities")

    # Extracted information
    norm_references: List[str] = Field(default_factory=list, description="Norm references (normalized)")
    legal_concepts: List[str] = Field(default_factory=list, description="Legal concepts mentioned")
    dates: List[str] = Field(default_factory=list, description="Temporal references")

    # Metadata
    language: str = Field(default="it", description="Language code")
    query_length: int = Field(..., description="Query length in characters")
    processing_time_ms: float = Field(..., description="Processing time in milliseconds")
    model_version: str = Field(default="phase1_openrouter", description="Model version used")
    timestamp: datetime = Field(default_factory=datetime.utcnow)

    # Quality metrics
    overall_confidence: float = Field(ge=0.0, le=1.0, description="Average confidence across components")
    needs_review: bool = Field(default=False, description="Whether query needs expert review")
    review_reason: Optional[str] = Field(None, description="Why this query needs review")

    class Config:
        json_encoders = {
            LegalEntityType: lambda v: v.value,
            QueryIntentType: lambda v: v.value,
            datetime: lambda v: v.isoformat(),
            LegalEntity: lambda v: v.to_dict()
        }

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for JSON serialization"""
        return {
            "query_id": self.query_id,
            "original_query": self.original_query,
            "intent": self.intent.value,
            "intent_confidence": self.intent_confidence,
            "intent_reasoning": self.intent_reasoning,
            "entities": [e.to_dict() for e in self.entities],
            "norm_references": self.norm_references,
            "legal_concepts": self.legal_concepts,
            "dates": self.dates,
            "language": self.language,
            "query_length": self.query_length,
            "processing_time_ms": self.processing_time_ms,
            "model_version": self.model_version,
            "timestamp": self.timestamp.isoformat(),
            "overall_confidence": self.overall_confidence,
            "needs_review": self.needs_review,
            "review_reason": self.review_reason
        }


# ==========================================
# Pattern Definitions for Italian Legal Text
# ==========================================

class LegalPatterns:
    """Regex patterns for extracting legal references from Italian text"""

    # Norm references patterns
    NORM_PATTERNS = {
        "codice_civile": r"(?:Art|art|articolo)\s+(\d+)(?:\s+(?:co|comma)\s+(\d+))?\s+c\.c\.(?!p)",
        "codice_penale": r"(?:Art|art|articolo)\s+(\d+)(?:\s+(?:co|comma)\s+(\d+))?\s+c\.p\.(?!c)",
        "codice_procedura_civile": r"(?:Art|art|articolo)\s+(\d+)(?:\s+(?:co|comma)\s+(\d+))?\s+c\.p\.c\.(?!p)",
        "codice_procedura_penale": r"(?:Art|art|articolo)\s+(\d+)(?:\s+(?:co|comma)\s+(\d+))?\s+c\.p\.p\.(?!c)",
        "costituzione": r"(?:Art|art|articolo|Artt|artt)\s+(\d+)(?:\s+(?:co|comma)\s+(\d+))?\s+(?:Cost|Cost\.|Costituzione)",
        "gdpr": r"(?:Art|art|articolo)\s+(\d+)(?:\s+(?:co|comma|par|paragrafo)\s+(\d+))?\s+(?:GDPR|Reg\..*679)",
        "decreto_legislativo": r"(?:D\.Lgs|d\.lgs|decreto\s+legislativo)\s+(\d+)/(\d{4})",
        "decreto_legge": r"(?:D\.L|d\.l|decreto\s+legge)\s+(\d+)/(\d{4})",
    }

    # Date patterns
    DATE_PATTERNS = {
        "iso_date": r"\d{4}-(?:0[1-9]|1[0-2])-(?:0[1-9]|[12]\d|3[01])",
        "italian_date": r"(?:0[1-9]|[12]\d|3[01])(?:/|-|\.)\s*(?:0[1-9]|1[0-2])(?:/|-|\.)\s*(?:\d{4}|\d{2})",
        "month_year": r"(?:gennaio|febbraio|marzo|aprile|maggio|giugno|luglio|agosto|settembre|ottobre|novembre|dicembre)\s+\d{4}",
    }

    # Monetary amounts
    AMOUNT_PATTERNS = {
        "euro_amount": r"€\s*[\d\.]{1,20}|\b[\d\.]+\s*€",
        "numeric_amount": r"\b(?:\d{1,3}(?:\.?\d{3})*|[\d]+)(?:,\d{2})?\s*(?:€|euro)",
    }

    # Party types
    PARTY_PATTERNS = {
        "person": r"(?:persona|individuo|soggetto|privato|cittadino|residente)",
        "legal_entity": r"(?:società|azienda|ditta|impresa|organizzazione|associazione|fondazione)",
        "pa": r"(?:pubblica amministrazione|amministrazione pubblica|ente pubblico|PA)",
    }

    # Legal concepts (domain vocabulary)
    LEGAL_CONCEPTS = {
        "gdpr": ["GDPR", "protezione dei dati", "privacy", "trattamento dati", "consenso", "titolare", "responsabile"],
        "contratti": ["contratto", "clausola", "offerta", "accettazione", "capacità", "consenso", "vizi del consenso"],
        "responsabilità": ["responsabilità", "danno", "dolo", "colpa", "negligenza", "imputabilità"],
        "diritti_reali": ["proprietà", "usufrutto", "diritti reali", "possesso", "servitù"],
        "diritti_successori": ["eredità", "testamento", "successione", "legittima", "legatario"],
        "diritto_lavoro": ["contratto di lavoro", "dipendente", "datore di lavoro", "sindacato", "sciopero"],
        "diritto_amministrativo": ["ricorso", "abuso di potere", "eccesso di potere", "eccesso di potere derivato"],
        "diritto_penale": ["reato", "delitto", "contravvenzione", "imputazione", "pena", "prescrizione"],
        "procedura_civile": ["giudizio", "ricorso", "sentenza", "appello", "cassazione", "competenza"],
    }

    @classmethod
    def extract_norms(cls, text: str) -> List[Tuple[str, str, str]]:
        """
        Extract norm references with their types.
        Returns: [(matched_text, norm_type, normalized_id), ...]
        """
        results = []
        for norm_type, pattern in cls.NORM_PATTERNS.items():
            matches = re.finditer(pattern, text, re.IGNORECASE)
            for match in matches:
                normalized = cls._normalize_norm_reference(match.group(0), norm_type)
                results.append((match.group(0), norm_type, normalized))
        return results

    @classmethod
    def extract_dates(cls, text: str) -> List[str]:
        """Extract date references"""
        dates = []
        for pattern_type, pattern in cls.DATE_PATTERNS.items():
            matches = re.finditer(pattern, text, re.IGNORECASE)
            dates.extend([m.group(0) for m in matches])
        return dates

    @classmethod
    def extract_amounts(cls, text: str) -> List[str]:
        """Extract monetary amounts"""
        amounts = []
        for pattern_type, pattern in cls.AMOUNT_PATTERNS.items():
            matches = re.finditer(pattern, text, re.IGNORECASE)
            amounts.extend([m.group(0) for m in matches])
        return amounts

    @classmethod
    def extract_legal_concepts(cls, text: str) -> List[str]:
        """Extract legal concepts mentioned in text"""
        concepts = set()
        text_lower = text.lower()
        for concept_domain, concept_list in cls.LEGAL_CONCEPTS.items():
            for concept in concept_list:
                if concept.lower() in text_lower:
                    concepts.add(concept)
        return sorted(list(concepts))

    @classmethod
    def _normalize_norm_reference(cls, text: str, norm_type: str) -> str:
        """
        Normalize norm reference to standard identifier.
        Examples:
        - "Art. 1321 c.c." → "cc_art_1321"
        - "Art. 82 GDPR" → "gdpr_art_82"
        """
        # Simple normalization - in production would be more complex
        match = re.search(r'(\d+)', text)
        if match:
            article = match.group(1)
            if "codice_civile" in norm_type:
                return f"cc_art_{article}"
            elif "codice_penale" in norm_type:
                return f"cp_art_{article}"
            elif "costituzione" in norm_type:
                return f"cost_art_{article}"
            elif "gdpr" in norm_type:
                return f"gdpr_art_{article}"
            else:
                return f"{norm_type}_art_{article}"
        return text


# ==========================================
# Query Understanding Service
# ==========================================

class QueryUnderstandingService:
    """
    Main service for analyzing Italian legal queries.

    Phase 1: Uses OpenRouter LLM with few-shot prompting
    Phase 2 (future): Fine-tuned Italian-Legal-BERT
    """

    def __init__(self):
        self.patterns = LegalPatterns()
        self.model_version = "phase1_openrouter"
        logger.info("QueryUnderstandingService initialized (Phase 1: OpenRouter)")

    async def analyze_query(
        self,
        query: str,
        query_id: Optional[str] = None,
        use_llm: bool = True
    ) -> QueryUnderstandingResult:
        """
        Analyze an Italian legal query.

        Args:
            query: The legal query text
            query_id: Optional unique identifier
            use_llm: Whether to use LLM for intent (Phase 1) or rule-based

        Returns:
            QueryUnderstandingResult with full analysis
        """
        import time
        start_time = time.time()

        if query_id is None:
            import uuid
            query_id = str(uuid.uuid4())

        # Extract entities using pattern matching + NER
        entities = self._extract_entities(query)

        # Extract structured information
        norm_references = [ref[2] for ref in self.patterns.extract_norms(query)]
        legal_concepts = self.patterns.extract_legal_concepts(query)
        dates = self.patterns.extract_dates(query)

        # Classify intent
        if use_llm:
            intent, intent_confidence, reasoning = await self._classify_intent_llm(query)
        else:
            intent, intent_confidence, reasoning = self._classify_intent_heuristic(query, legal_concepts)

        # Calculate overall confidence
        entity_confidences = [e.confidence for e in entities] if entities else [1.0]
        overall_confidence = (
            intent_confidence * 0.5 +
            sum(entity_confidences) / len(entity_confidences) * 0.5
        ) if entity_confidences else intent_confidence

        # Determine if review is needed
        needs_review = overall_confidence < 0.75 or intent == QueryIntentType.UNKNOWN
        review_reason = None
        if needs_review:
            review_reason = f"Low confidence ({overall_confidence:.2f}) or unknown intent"

        processing_time = (time.time() - start_time) * 1000  # Convert to ms

        return QueryUnderstandingResult(
            query_id=query_id,
            original_query=query,
            intent=intent,
            intent_confidence=intent_confidence,
            intent_reasoning=reasoning,
            entities=entities,
            norm_references=norm_references,
            legal_concepts=legal_concepts,
            dates=dates,
            query_length=len(query),
            processing_time_ms=processing_time,
            model_version=self.model_version,
            overall_confidence=overall_confidence,
            needs_review=needs_review,
            review_reason=review_reason
        )

    def _extract_entities(self, query: str) -> List[LegalEntity]:
        """Extract named entities from query using pattern matching"""
        entities = []

        # Extract norm references
        for text, norm_type, normalized in self.patterns.extract_norms(query):
            start = query.find(text)
            entity = LegalEntity(
                text=text,
                entity_type=LegalEntityType.NORM_REFERENCE,
                start_pos=start,
                end_pos=start + len(text),
                confidence=0.95,  # High confidence for regex-based matches
                normalized=normalized
            )
            entities.append(entity)

        # Extract dates
        for date_text in self.patterns.extract_dates(query):
            start = query.find(date_text)
            entity = LegalEntity(
                text=date_text,
                entity_type=LegalEntityType.DATE,
                start_pos=start,
                end_pos=start + len(date_text),
                confidence=0.90
            )
            entities.append(entity)

        # Extract amounts
        for amount_text in self.patterns.extract_amounts(query):
            start = query.find(amount_text)
            entity = LegalEntity(
                text=amount_text,
                entity_type=LegalEntityType.AMOUNT,
                start_pos=start,
                end_pos=start + len(amount_text),
                confidence=0.85
            )
            entities.append(entity)

        return entities

    async def _classify_intent_llm(self, query: str) -> Tuple[QueryIntentType, float, str]:
        """
        Phase 1: Use OpenRouter LLM for intent classification with few-shot prompting.
        """
        few_shot_examples = """
Esempi di classificazione:

Query: "Che significa l'articolo 1321 del codice civile?"
Intent: NORM_SEARCH (confidence: 0.95)
Reasoning: Query chiede spiegazione diretta di una norma specifica.

Query: "Sono in compliance con il GDPR nel trattamento dei dati personali?"
Intent: COMPLIANCE_CHECK (confidence: 0.92)
Reasoning: Query chiede verifica di conformità a normativa.

Query: "Quali sono i rischi legali nel stipulare un contratto con una startup?"
Intent: RISK_SPOTTING (confidence: 0.88)
Reasoning: Query chiede identificazione di rischi legali.

Query: "Dammi un template di contratto di lavoro autonomo"
Intent: DOCUMENT_DRAFTING (confidence: 0.91)
Reasoning: Query chiede redazione di documento legale.

Query: "Quando è responsabile il produttore per danni da prodotto difettoso?"
Intent: INTERPRETATION (confidence: 0.89)
Reasoning: Query chiede interpretazione principio legale.
"""

        prompt = f"""{few_shot_examples}

Ora classifica questa query:

Query: "{query}"

Rispondi in formato JSON:
{{
    "intent": "[una di: norm_search, interpretation, compliance_check, document_drafting, risk_spotting]",
    "confidence": [0.0-1.0],
    "reasoning": "[breve spiegazione in italiano]"
}}

Sii conciso nella spiegazione (max 20 parole).
"""

        try:
            response = await openrouter_service.generate_async(
                prompt=prompt,
                model="meta-llama/llama-2-13b-chat",
                max_tokens=200,
                temperature=0.1
            )

            # Parse JSON response
            import json
            result = json.loads(response)

            intent_str = result.get("intent", "unknown").lower()
            confidence = float(result.get("confidence", 0.5))
            reasoning = result.get("reasoning", "LLM classification")

            # Map string to enum
            try:
                intent = QueryIntentType[intent_str.upper()]
            except (KeyError, AttributeError):
                intent = QueryIntentType.UNKNOWN
                confidence = max(0.0, confidence - 0.2)

            return intent, confidence, reasoning

        except Exception as e:
            logger.warning(f"LLM intent classification failed: {e}, falling back to heuristic")
            legal_concepts = self.patterns.extract_legal_concepts(query)
            return self._classify_intent_heuristic(query, legal_concepts)

    def _classify_intent_heuristic(
        self,
        query: str,
        legal_concepts: List[str]
    ) -> Tuple[QueryIntentType, float, str]:
        """
        Heuristic intent classification based on keywords and patterns.
        Used as fallback or Phase 1 alternative to LLM.
        """
        query_lower = query.lower()

        # Compliance check patterns
        if any(word in query_lower for word in ["compliance", "conforme", "conformità", "sono in", "siamo in"]):
            return QueryIntentType.COMPLIANCE_CHECK, 0.85, "Detected compliance check keywords"

        # Risk spotting patterns
        if any(word in query_lower for word in ["rischi", "rischio", "pericolo", "quale rischio", "quali rischi"]):
            return QueryIntentType.RISK_SPOTTING, 0.82, "Detected risk-related keywords"

        # Document drafting patterns
        if any(word in query_lower for word in ["template", "modello", "dammi", "crea", "redigi", "scrivi", "documento"]):
            return QueryIntentType.DOCUMENT_DRAFTING, 0.88, "Detected drafting-related keywords"

        # Norm search patterns
        if any(word in query_lower for word in ["art.", "articolo", "che dice", "significa", "cosa dice", "dice l'"]):
            return QueryIntentType.NORM_SEARCH, 0.88, "Detected norm search keywords"

        # Interpretation patterns (fallback - most general)
        if any(word in query_lower for word in ["quando", "come", "è", "sono", "cosa", "quale", "significa"]):
            return QueryIntentType.INTERPRETATION, 0.70, "Detected interpretation keywords (default)"

        return QueryIntentType.UNKNOWN, 0.50, "Could not determine intent from keywords"


# ==========================================
# Singleton Factory
# ==========================================

_service_instance: Optional[QueryUnderstandingService] = None


def get_query_understanding_service() -> QueryUnderstandingService:
    """Get or create singleton instance of QueryUnderstandingService"""
    global _service_instance
    if _service_instance is None:
        _service_instance = QueryUnderstandingService()
    return _service_instance


async def analyze_query(query: str, query_id: Optional[str] = None) -> QueryUnderstandingResult:
    """Convenience function for query analysis"""
    service = get_query_understanding_service()
    return await service.analyze_query(query, query_id)


# ==========================================
# Integration with Pipeline
# ==========================================

async def prepare_query_for_enrichment(
    query: str,
    use_llm: bool = True
) -> Dict[str, Any]:
    """
    Prepare query analysis output for KG enrichment stage.
    Bridges Query Understanding → KG Enrichment.
    """
    result = await analyze_query(query)

    return {
        "query_id": result.query_id,
        "original_query": result.original_query,
        "intent": result.intent.value,
        "intent_confidence": result.intent_confidence,
        "extracted_entities": [e.to_dict() for e in result.entities],
        "norm_references": result.norm_references,
        "legal_concepts": result.legal_concepts,
        "dates": result.dates,
        "overall_confidence": result.overall_confidence,
        "needs_review": result.needs_review,
        "processing_time_ms": result.processing_time_ms
    }
