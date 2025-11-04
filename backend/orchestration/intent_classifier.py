"""
LLM-Based Intent Classifier for Legal Queries (Evolvable Architecture)
========================================================================

Implements a 3-phase evolvable intent classifier:
- Phase 1 (Immediate): OpenRouter LLM with few-shot prompting
- Phase 2 (3-6 months): Fine-tuned small model (Italian-Legal-BERT) with fallback
- Phase 3 (6-12 months): Community-driven model with RLCF feedback loops

Architecture supports seamless transition between phases without code changes.
RLCF feedback collection active from Phase 1 for ground truth dataset building.

Configuration: backend/orchestration/config/intent_config.yaml
Integration: backend/rlcf_framework/routers/intent_router.py

Reference: docs/02-methodology/query-understanding.md Stage 4
"""

import asyncio
import json
import logging
from enum import Enum
from dataclasses import dataclass, field, asdict
from typing import Dict, List, Optional, Any
from datetime import datetime
import os

import yaml
from pydantic import BaseModel, Field

# Import existing OpenRouter service
from backend.rlcf_framework.ai_service import openrouter_service, AIModelConfig

logger = logging.getLogger(__name__)


# ===================================
# Enums & Data Structures
# ===================================

class IntentType(Enum):
    """Legal query intent types (Italian legal context)"""
    CONTRACT_INTERPRETATION = "contract_interpretation"  # Clausole contrattuali
    COMPLIANCE_QUESTION = "compliance_question"          # Conformità normativa
    NORM_EXPLANATION = "norm_explanation"                # Spiegazione norme
    PRECEDENT_SEARCH = "precedent_search"               # Ricerca giurisprudenza
    UNKNOWN = "unknown"                                  # Fallback


@dataclass
class IntentResult:
    """Result from intent classification"""
    intent: IntentType
    confidence: float  # 0.0 to 1.0
    reasoning: str
    norm_references: List[Dict[str, Any]] = field(default_factory=list)
    needs_review: bool = False
    timestamp: datetime = field(default_factory=datetime.utcnow)
    model_version: str = "phase1_openrouter"
    classification_source: str = "openrouter"

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for JSON serialization"""
        return {
            "intent": self.intent.value,
            "confidence": self.confidence,
            "reasoning": self.reasoning,
            "norm_references": self.norm_references,
            "needs_review": self.needs_review,
            "timestamp": self.timestamp.isoformat(),
            "model_version": self.model_version,
            "classification_source": self.classification_source
        }


# ===================================
# Configuration Management
# ===================================

class IntentConfigLoader:
    """Load and cache intent configuration from YAML"""

    _config: Optional[Dict[str, Any]] = None
    _config_path = os.path.join(
        os.path.dirname(__file__),
        "config/intent_config.yaml"
    )

    @classmethod
    def load(cls) -> Dict[str, Any]:
        """Load configuration with caching"""
        if cls._config is None:
            try:
                with open(cls._config_path, 'r') as f:
                    cls._config = yaml.safe_load(f)
                logger.info(f"Loaded intent configuration from {cls._config_path}")
            except FileNotFoundError:
                logger.warning(f"Intent config not found at {cls._config_path}, using defaults")
                cls._config = cls._get_default_config()
        return cls._config

    @classmethod
    def reload(cls) -> Dict[str, Any]:
        """Force reload configuration (for hot-reload capability)"""
        cls._config = None
        return cls.load()

    @staticmethod
    def _get_default_config() -> Dict[str, Any]:
        """Default configuration if YAML not available"""
        return {
            "intent_types": {
                "contract_interpretation": {
                    "description": "Interpretazione di clausole contrattuali",
                    "examples": [
                        "Cosa significa questa clausola di non concorrenza?",
                        "Come interpreto questa parte del contratto?",
                        "Quali sono le obbligazioni previste in questa clausola?"
                    ],
                    "confidence_threshold": 0.85
                },
                "compliance_question": {
                    "description": "Verifica conformità normativa",
                    "examples": [
                        "Il mio sistema è conforme al GDPR?",
                        "Sono in violazione del d.lgs. 196/2003?",
                        "Come posso verificare la conformità a questa norma?"
                    ],
                    "confidence_threshold": 0.80
                },
                "norm_explanation": {
                    "description": "Spiegazione semplificata di norme legali",
                    "examples": [
                        "Cosa dice l'articolo 2043 del codice civile?",
                        "Puoi spiegare il d.lgs. 196/2003?",
                        "Cosa significa questa legge?"
                    ],
                    "confidence_threshold": 0.90
                },
                "precedent_search": {
                    "description": "Ricerca giurisprudenza e precedenti",
                    "examples": [
                        "Ci sono sentenze su responsabilità extracontrattuale?",
                        "Quali sono i precedenti su questa questione?",
                        "Come hanno giudicato i tribunali questo caso?"
                    ],
                    "confidence_threshold": 0.80
                }
            },
            "llm_config": {
                "provider": "openrouter",
                "model": "anthropic/claude-3.5-sonnet",
                "temperature": 0.1,
                "max_tokens": 500,
                "top_p": 0.9,
                "timeout": 30
            },
            "rlcf_config": {
                "confidence_threshold_review": 0.85,
                "min_authority_score": 0.6,
                "min_validations_for_ground_truth": 3
            }
        }


# ===================================
# Phase 1: OpenRouter Intent Classifier
# ===================================

class OpenRouterIntentClassifier:
    """
    Uses OpenRouter LLM with few-shot prompting for intent classification.

    Phase 1 (Immediate): OpenRouter with Claude 3.5 Sonnet
    - Produces high-quality intent classifications
    - Builds ground truth dataset for Phase 2 fine-tuning
    - Confidence thresholds trigger RLCF community review
    """

    def __init__(self, config: Optional[Dict[str, Any]] = None):
        self.config = config or IntentConfigLoader.load()
        self.intent_types = self.config.get("intent_types", {})
        self.llm_config = self.config.get("llm_config", {})
        self._system_prompt = self._build_system_prompt()

    def _build_system_prompt(self) -> str:
        """Build few-shot system prompt for intent classification"""
        intent_descriptions = "\n".join([
            f"- {k}: {v.get('description', '')}"
            for k, v in self.intent_types.items()
        ])

        return f"""Sei un esperto di diritto italiano specializzato in classificazione di query legali.

Classifica l'intent della query legale in una delle seguenti categorie:

{intent_descriptions}

Rispondi SEMPRE in formato JSON con questa struttura:
{{
    "intent": "<nome_intent>",
    "confidence": <0.0-1.0>,
    "reasoning": "<spiegazione breve del perché hai scelto questo intent>",
    "key_legal_concepts": ["<concetto1>", "<concetto2>"]
}}

Se la query non corrisponde a nessun intent, rispondi con intent="unknown" e confidence bassa."""

    def _build_few_shot_examples(self) -> str:
        """Build few-shot examples from configuration"""
        examples = []
        for intent_type, config in self.intent_types.items():
            for example_query in config.get("examples", [])[:2]:  # Max 2 per type
                examples.append(
                    f'Query: "{example_query}"\nIntent: {intent_type}\n'
                )
        return "\n".join(examples)

    async def classify_intent(
        self,
        query_text: str,
        norm_references: Optional[List[Dict[str, Any]]] = None,
        context: Optional[str] = None
    ) -> IntentResult:
        """
        Classify intent of legal query using OpenRouter LLM.

        Args:
            query_text: User's legal query
            norm_references: NER-extracted norm references (optional context)
            context: Additional context (optional)

        Returns:
            IntentResult with classification, confidence, reasoning
        """
        try:
            # Build prompt with few-shot examples and context
            user_prompt = self._build_user_prompt(
                query_text,
                norm_references,
                context
            )

            # Call OpenRouter via existing service
            model_config = AIModelConfig(
                name=self.llm_config.get("model", "anthropic/claude-3.5-sonnet"),
                api_key=os.getenv("OPENROUTER_API_KEY", ""),
                temperature=self.llm_config.get("temperature", 0.1),
                max_tokens=self.llm_config.get("max_tokens", 500),
                top_p=self.llm_config.get("top_p", 0.9)
            )

            # Use custom task type for intent classification
            input_data = {
                "query": query_text,
                "norm_references": norm_references or [],
                "context": context or ""
            }

            response = await openrouter_service.generate_response(
                task_type="INTENT_CLASSIFICATION",
                input_data=input_data,
                model_config=model_config
            )

            # Parse LLM response
            result = await self._parse_llm_response(
                response.get("raw_content", response.get("response_text", "")),
                query_text,
                norm_references
            )

            return result

        except Exception as e:
            logger.error(f"Error classifying intent: {str(e)}")
            # Fallback to unknown with low confidence
            return IntentResult(
                intent=IntentType.UNKNOWN,
                confidence=0.2,
                reasoning=f"Classification failed: {str(e)}",
                needs_review=True,
                classification_source="fallback"
            )

    def _build_user_prompt(
        self,
        query_text: str,
        norm_references: Optional[List[Dict[str, Any]]] = None,
        context: Optional[str] = None
    ) -> str:
        """Build user prompt with few-shot examples and context"""
        norm_refs_str = ""
        if norm_references:
            norm_refs_str = "\n\nRiferimenti Normativi Estratti (da NER):\n"
            for ref in norm_references:
                norm_refs_str += f"- {ref.get('text', '')}: {ref.get('act_type', '')}\n"

        context_str = ""
        if context:
            context_str = f"\n\nContesto: {context}"

        few_shot = self._build_few_shot_examples()

        return f"""{few_shot}

Query da classificare: "{query_text}"{norm_refs_str}{context_str}

Classifica questa query seguendo il formato JSON richiesto."""

    async def _parse_llm_response(
        self,
        llm_response: str,
        query_text: str,
        norm_references: Optional[List[Dict[str, Any]]] = None
    ) -> IntentResult:
        """Parse LLM response and extract structured intent classification"""
        try:
            # Extract JSON from LLM response
            json_start = llm_response.find('{')
            json_end = llm_response.rfind('}') + 1

            if json_start >= 0 and json_end > json_start:
                json_str = llm_response[json_start:json_end]
                parsed = json.loads(json_str)
            else:
                logger.warning(f"No JSON found in LLM response: {llm_response}")
                return IntentResult(
                    intent=IntentType.UNKNOWN,
                    confidence=0.3,
                    reasoning="Could not parse LLM response",
                    needs_review=True
                )

            # Extract intent
            intent_str = parsed.get("intent", "unknown").lower()
            try:
                intent = IntentType(intent_str)
            except ValueError:
                intent = IntentType.UNKNOWN

            # Extract confidence
            confidence = float(parsed.get("confidence", 0.5))
            confidence = max(0.0, min(1.0, confidence))  # Clamp to [0, 1]

            # Extract reasoning
            reasoning = parsed.get("reasoning", "")

            # Determine if needs review based on confidence threshold
            intent_config = self.intent_types.get(intent_str, {})
            threshold = intent_config.get("confidence_threshold", 0.85)
            needs_review = confidence < threshold or intent == IntentType.UNKNOWN

            return IntentResult(
                intent=intent,
                confidence=confidence,
                reasoning=reasoning,
                norm_references=norm_references or [],
                needs_review=needs_review,
                model_version="phase1_openrouter",
                classification_source="openrouter"
            )

        except (json.JSONDecodeError, ValueError, KeyError) as e:
            logger.error(f"Error parsing LLM response: {str(e)}")
            return IntentResult(
                intent=IntentType.UNKNOWN,
                confidence=0.2,
                reasoning=f"Parsing error: {str(e)}",
                needs_review=True
            )


# ===================================
# Phase 1+: Evolvable Intent Classifier
# ===================================

class EvolvableIntentClassifier:
    """
    Wrapper that supports gradual evolution from Phase 1 to Phase 3.

    Phase 1 (Now): OpenRouter LLM
    Phase 2 (3-6 mo): Fine-tuned model + fallback
    Phase 3 (6-12 mo): Community model + active learning

    No code changes needed for transitions - just deploy new primary_classifier.
    RLCF feedback loop active throughout all phases.
    """

    def __init__(self, config: Optional[Dict[str, Any]] = None):
        self.config = config or IntentConfigLoader.load()

        # Phase 1: Primary = None, use fallback
        # Phase 2: Primary = FinetuneItalianLegalBERT (to be implemented)
        # Phase 3: Primary = CommunityDrivenModel (to be implemented)
        self.primary_classifier: Optional[Any] = None

        # Phase 1: OpenRouter fallback
        self.llm_classifier = OpenRouterIntentClassifier(config)

        # RLCF feedback collector (active from Phase 1)
        self.feedback_collector = RLCFIntentFeedbackCollector(config)

    async def classify_intent(
        self,
        query_text: str,
        norm_references: Optional[List[Dict[str, Any]]] = None,
        context: Optional[str] = None
    ) -> IntentResult:
        """
        Classify intent with automatic fallback and RLCF feedback collection.

        Flow:
        1. Try primary classifier if available (Phase 2+)
        2. If failed or low confidence: fallback to LLM
        3. Always collect feedback for RLCF
        4. Flag for community review if needed
        """
        result = None

        # Try primary classifier (Phase 2+)
        if self.primary_classifier:
            try:
                result = await self.primary_classifier.classify_intent(
                    query_text,
                    norm_references,
                    context
                )
                if result.confidence > 0.80:
                    # High confidence - use primary classifier
                    await self.feedback_collector.store_classification(
                        result, "primary_model"
                    )
                    return result
            except Exception as e:
                logger.warning(f"Primary classifier failed, falling back to LLM: {str(e)}")

        # Fallback: Use OpenRouter LLM (Phase 1, always available)
        result = await self.llm_classifier.classify_intent(
            query_text,
            norm_references,
            context
        )

        # 🔑 RLCF: Collect feedback for ground truth dataset
        await self.feedback_collector.store_classification(
            result, "openrouter_llm"
        )

        return result

    async def reload_config(self):
        """Hot-reload configuration without server restart"""
        self.config = IntentConfigLoader.reload()
        self.llm_classifier = OpenRouterIntentClassifier(self.config)
        logger.info("Intent classifier configuration reloaded")

    def set_primary_classifier(self, classifier: Any):
        """
        Phase 2+ transition: Install fine-tuned model as primary.
        Maintains fallback to LLM for robustness.
        """
        self.primary_classifier = classifier
        logger.info(f"Primary classifier updated: {type(classifier).__name__}")


# ===================================
# RLCF: Feedback Collection System
# ===================================

class RLCFIntentFeedbackCollector:
    """
    Collects community feedback on intent classifications for RLCF training.

    Builds ground truth dataset from Phase 1 that powers Phase 2 fine-tuning.
    Tracks confidence scores and creates review tasks for uncertain classifications.
    """

    def __init__(self, config: Optional[Dict[str, Any]] = None):
        self.config = config or IntentConfigLoader.load()
        self.rlcf_config = self.config.get("rlcf_config", {})
        self.confidence_threshold = self.rlcf_config.get(
            "confidence_threshold_review", 0.85
        )

    async def store_classification(
        self,
        result: IntentResult,
        source: str
    ) -> str:
        """
        Store classification for RLCF feedback loop.

        Args:
            result: Intent classification result
            source: Source of classification ("openrouter_llm", "primary_model", etc.)

        Returns:
            Classification ID (for linking feedback)
        """
        classification_id = self._generate_classification_id()

        # Prepare data for storage
        classification_data = {
            "id": classification_id,
            "intent": result.intent.value,
            "confidence": result.confidence,
            "reasoning": result.reasoning,
            "source": source,
            "timestamp": result.timestamp.isoformat(),
            "needs_review": result.needs_review,
            "model_version": result.model_version
        }

        # Store in database (to be implemented in models_intent.py)
        # For now: log as placeholder
        logger.info(f"RLCF Classification stored: {json.dumps(classification_data)}")

        # Create review task if needed
        if result.needs_review or result.confidence < self.confidence_threshold:
            await self._create_review_task(
                classification_id,
                result
            )

        return classification_id

    async def _create_review_task(
        self,
        classification_id: str,
        result: IntentResult
    ):
        """Create community review task for uncertain classifications"""
        task_data = {
            "classification_id": classification_id,
            "query": "NOT_YET_STORED",  # Will be populated from DB
            "predicted_intent": result.intent.value,
            "confidence": result.confidence,
            "reasoning": result.reasoning,
            "priority": "high" if result.confidence < 0.7 else "normal",
            "status": "pending_review"
        }

        # Store review task (to be implemented)
        logger.info(f"Review task created: {json.dumps(task_data)}")

    @staticmethod
    def _generate_classification_id() -> str:
        """Generate unique classification ID"""
        import uuid
        return str(uuid.uuid4())


# ===================================
# Singleton Instance
# ===================================

_evolvable_classifier: Optional[EvolvableIntentClassifier] = None


async def get_intent_classifier(
    config: Optional[Dict[str, Any]] = None
) -> EvolvableIntentClassifier:
    """Get or create evolvable intent classifier (lazy initialization)"""
    global _evolvable_classifier
    if _evolvable_classifier is None:
        _evolvable_classifier = EvolvableIntentClassifier(config)
    return _evolvable_classifier


async def reload_intent_classifier():
    """Reload intent classifier configuration (hot-reload)"""
    global _evolvable_classifier
    if _evolvable_classifier:
        await _evolvable_classifier.reload_config()
