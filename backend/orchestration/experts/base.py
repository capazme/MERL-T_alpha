"""
Base classes and data models for Reasoning Experts

This module defines:
- ExpertContext: Input data for experts (query + retrieved data)
- ExpertOpinion: Output data from experts (interpretation + rationale)
- ReasoningExpert: Abstract base class for all experts

All experts follow the same interface:
- Input: ExpertContext
- Process: Legal reasoning methodology (LLM-based)
- Output: ExpertOpinion with full provenance
"""

import logging
import time
import json
from abc import ABC, abstractmethod
from typing import List, Dict, Any, Optional, Literal
from datetime import datetime
from pathlib import Path

from pydantic import BaseModel, Field

# Import AI service from Phase 1
from backend.rlcf_framework.ai_service import AIService

logger = logging.getLogger(__name__)


# ============================================================================
# Input Data Models
# ============================================================================

class ExpertContext(BaseModel):
    """
    Input context for reasoning experts.

    Contains all information needed for legal reasoning:
    - Original query
    - Retrieved data (norms, case law, doctrine)
    - Enriched metadata
    """
    # Query information
    query_text: str
    intent: str  # norm_explanation, contract_interpretation, etc.
    complexity: float = Field(ge=0.0, le=1.0)

    # Extracted entities
    norm_references: List[str] = Field(default_factory=list)
    legal_concepts: List[str] = Field(default_factory=list)
    entities: Dict[str, Any] = Field(default_factory=dict)

    # Retrieved data from agents
    kg_results: List[Dict[str, Any]] = Field(default_factory=list)
    api_results: List[Dict[str, Any]] = Field(default_factory=list)
    vectordb_results: List[Dict[str, Any]] = Field(default_factory=list)

    # Enriched context from KG
    enriched_context: Optional[Dict[str, Any]] = None

    # Metadata
    trace_id: str
    timestamp: str = Field(default_factory=lambda: datetime.utcnow().isoformat())


# ============================================================================
# Output Data Models
# ============================================================================

class LegalBasis(BaseModel):
    """Individual legal source cited in reasoning."""
    source_type: Literal["norm", "jurisprudence", "doctrine", "constitutional"]
    source_id: str
    citation: str  # e.g., "Art. 1321 c.c."
    excerpt: str   # Relevant text excerpt
    relevance: str  # Why this source is relevant
    application: Optional[str] = None  # How it applies to the query


class ReasoningStep(BaseModel):
    """Individual reasoning step."""
    step_number: int
    description: str  # What this step establishes
    sources: List[str] = Field(default_factory=list)  # source_ids


class ConfidenceFactors(BaseModel):
    """Breakdown of confidence score."""
    norm_clarity: float = Field(ge=0.0, le=1.0, default=0.5)
    jurisprudence_alignment: float = Field(ge=0.0, le=1.0, default=0.5)
    contextual_ambiguity: float = Field(ge=0.0, le=1.0, default=0.5)
    source_availability: float = Field(ge=0.0, le=1.0, default=0.5)


class ExpertOpinion(BaseModel):
    """
    Output from a reasoning expert.

    Contains:
    - Main interpretation (Italian text)
    - Structured rationale
    - Confidence score
    - Full source provenance
    - Acknowledged limitations
    """
    # Expert identification
    expert_type: Literal[
        "literal_interpreter",
        "systemic_teleological",
        "principles_balancer",
        "precedent_analyst"
    ]
    trace_id: str

    # Main reasoning output
    interpretation: str  # Main legal reasoning (Italian)

    # Structured rationale
    legal_basis: List[LegalBasis] = Field(default_factory=list)
    reasoning_steps: List[ReasoningStep] = Field(default_factory=list)

    # Confidence
    confidence: float = Field(ge=0.0, le=1.0)
    confidence_factors: ConfidenceFactors = Field(default_factory=ConfidenceFactors)

    # Provenance (every claim traced to source)
    sources: List[LegalBasis] = Field(default_factory=list)

    # Epistemic humility
    limitations: str = ""  # What this expert ignored/cannot address

    # Metadata
    llm_model: str
    temperature: float
    tokens_used: int
    execution_time_ms: float
    timestamp: str = Field(default_factory=lambda: datetime.utcnow().isoformat())


# ============================================================================
# Base Expert Class
# ============================================================================

class ReasoningExpert(ABC):
    """
    Abstract base class for all reasoning experts.

    All experts:
    - Receive ExpertContext (query + retrieved data)
    - Apply specific legal reasoning methodology
    - Return ExpertOpinion with full provenance
    - Are LLM-based (same model, different prompts)
    """

    def __init__(
        self,
        expert_type: str,
        config: Optional[Dict[str, Any]] = None
    ):
        """
        Initialize expert.

        Args:
            expert_type: Type of expert (literal_interpreter, etc.)
            config: Expert configuration (model, temperature, etc.)
        """
        self.expert_type = expert_type
        self.config = config or {}
        self.logger = logging.getLogger(f"expert.{expert_type}")

        # LLM configuration
        self.model = self.config.get("model", "anthropic/claude-3.5-sonnet")
        self.temperature = self.config.get("temperature", 0.3)
        self.max_tokens = self.config.get("max_tokens", 2000)

        # AI service (from Phase 1)
        self.ai_service = AIService()

        # Load prompt template
        self.prompt_template = self._load_prompt_template()

        self.logger.info(
            f"{expert_type} initialized "
            f"(model={self.model}, temp={self.temperature})"
        )

    @abstractmethod
    async def analyze(self, context: ExpertContext) -> ExpertOpinion:
        """
        Analyze query using expert's reasoning methodology.

        Args:
            context: ExpertContext with query + retrieved data

        Returns:
            ExpertOpinion with interpretation + rationale
        """
        pass

    def _load_prompt_template(self) -> str:
        """
        Load prompt template for this expert.

        Returns:
            Prompt template string
        """
        prompt_file = (
            Path(__file__).parent.parent
            / "prompts"
            / f"{self.expert_type}.txt"
        )

        if not prompt_file.exists():
            self.logger.warning(
                f"Prompt template not found: {prompt_file}. "
                f"Using default template."
            )
            return self._get_default_prompt()

        return prompt_file.read_text(encoding="utf-8")

    def _get_default_prompt(self) -> str:
        """
        Get default prompt template.

        Returns:
            Default prompt string
        """
        return f"""You are a legal reasoning expert ({self.expert_type}).

Analyze the user's query and provide a structured legal opinion.

Output format: JSON object with fields:
- interpretation: str (main reasoning in Italian)
- legal_basis: List[Dict] (sources cited)
- reasoning_steps: List[Dict] (step-by-step reasoning)
- confidence: float (0.0-1.0)
- confidence_factors: Dict (breakdown of confidence)
- sources: List[Dict] (all sources with provenance)
- limitations: str (what you ignored)

Respond with valid JSON only."""

    async def _call_llm(
        self,
        system_prompt: str,
        user_prompt: str,
        max_retries: int = 3
    ) -> Dict[str, Any]:
        """
        Call LLM with expert-specific prompts and guaranteed JSON output.

        Modern techniques for structured output (2025):
        1. JSON mode enforcement via prompt engineering
        2. Schema injection in system prompt for clarity
        3. Retry logic with exponential backoff for malformed JSON
        4. Automatic cleanup of markdown code fences
        5. Validation before returning

        Args:
            system_prompt: System message (expert methodology)
            user_prompt: User message (query + context)
            max_retries: Maximum retry attempts for malformed JSON (default: 3)

        Returns:
            LLM response with metadata (content as string, tokens, time)

        Raises:
            ValueError: If LLM returns invalid JSON after all retries
        """
        import asyncio

        start_time = time.time()

        # Inject JSON schema enforcement into system prompt
        enhanced_system_prompt = f"""{system_prompt}

CRITICAL JSON FORMAT REQUIREMENTS:
1. Your response MUST be a valid JSON object matching the schema specified above
2. Do NOT include markdown code fences (```json or ```)
3. Do NOT include any explanatory text before or after the JSON
4. Start your response with {{ and end with }}
5. All string values must use double quotes, not single quotes
6. Ensure all required fields are present

If you cannot provide a complete answer, still return valid JSON with partial data.
"""

        for attempt in range(max_retries):
            try:
                # Call AI service from Phase 1
                response = await self.ai_service.generate_response_async(
                    prompt=f"{enhanced_system_prompt}\n\nUSER QUERY AND CONTEXT:\n{user_prompt}",
                    model=self.model,
                    temperature=self.temperature,
                    max_tokens=self.max_tokens
                )

                elapsed_ms = (time.time() - start_time) * 1000

                # Parse tokens from response if available
                tokens_used = 0
                if isinstance(response, dict):
                    tokens_used = response.get("usage", {}).get("total_tokens", 0)
                    content = response.get("content", str(response))
                else:
                    content = str(response)

                # Clean potential markdown code fences
                content = content.strip()

                # Remove markdown fences if present
                if content.startswith("```json"):
                    content = content[7:]
                elif content.startswith("```"):
                    content = content[3:]

                if content.endswith("```"):
                    content = content[:-3]

                content = content.strip()

                # Validate JSON structure
                try:
                    # Attempt to parse JSON to validate structure
                    json.loads(content)

                    self.logger.info(
                        f"{self.expert_type} LLM call succeeded on attempt {attempt + 1} "
                        f"in {elapsed_ms:.2f}ms"
                    )

                    return {
                        "content": content,
                        "tokens_used": tokens_used,
                        "execution_time_ms": elapsed_ms
                    }

                except json.JSONDecodeError as json_err:
                    self.logger.warning(
                        f"Attempt {attempt + 1}/{max_retries}: {self.expert_type} "
                        f"returned invalid JSON: {str(json_err)}"
                    )
                    self.logger.debug(f"Response preview: {content[:500]}")

                    if attempt == max_retries - 1:
                        # Last attempt failed - log and raise
                        self.logger.error(
                            f"All {max_retries} attempts failed for {self.expert_type}. "
                            f"JSON error: {str(json_err)}"
                        )
                        self.logger.error(f"Final response: {content[:1000]}")

                        raise ValueError(
                            f"{self.expert_type} returned invalid JSON after {max_retries} attempts: "
                            f"{str(json_err)}\n"
                            f"Response preview: {content[:500]}"
                        )

                    # Exponential backoff before retry
                    wait_time = (2 ** attempt) * 0.5  # 0.5s, 1s, 2s
                    self.logger.info(f"Waiting {wait_time}s before retry...")
                    await asyncio.sleep(wait_time)
                    continue

            except Exception as e:
                # Non-JSON error (API failure, timeout, etc.)
                elapsed_ms = (time.time() - start_time) * 1000

                if "json" not in str(e).lower():
                    # Not a JSON parsing error - don't retry
                    self.logger.error(
                        f"{self.expert_type} LLM call failed after {elapsed_ms:.2f}ms: {str(e)}",
                        exc_info=True
                    )
                    raise

                if attempt == max_retries - 1:
                    # Last retry, give up
                    self.logger.error(
                        f"{self.expert_type} failed after {max_retries} attempts: {str(e)}",
                        exc_info=True
                    )
                    raise

                # Retry with backoff
                wait_time = (2 ** attempt) * 0.5
                self.logger.info(f"Retrying after error, waiting {wait_time}s...")
                await asyncio.sleep(wait_time)
                continue

    def _format_context(self, context: ExpertContext) -> str:
        """
        Format ExpertContext into user prompt string.

        Args:
            context: ExpertContext to format

        Returns:
            Formatted string for user prompt
        """
        sections = []

        # Query information
        sections.append("## QUERY")
        sections.append(f"Text: {context.query_text}")
        sections.append(f"Intent: {context.intent}")
        sections.append(f"Complexity: {context.complexity:.2f}")

        # Extracted entities
        if context.norm_references:
            sections.append("\n## NORM REFERENCES")
            sections.append(", ".join(context.norm_references))

        if context.legal_concepts:
            sections.append("\n## LEGAL CONCEPTS")
            sections.append(", ".join(context.legal_concepts))

        # Retrieved norms (from API agent)
        if context.api_results:
            sections.append("\n## RETRIEVED NORMS")
            for idx, result in enumerate(context.api_results[:5], 1):
                sections.append(f"\n### Norm {idx}")
                sections.append(f"ID: {result.get('norm_id', result.get('id', 'N/A'))}")
                sections.append(f"Citation: {result.get('citation', 'N/A')}")
                text = result.get('text', result.get('article_text', ''))
                if text:
                    sections.append(f"Text: {text[:500]}...")

        # Retrieved case law (from VectorDB agent)
        if context.vectordb_results:
            jurisprudence = [
                r for r in context.vectordb_results
                if r.get('metadata', {}).get('document_type') == 'jurisprudence'
            ]
            if jurisprudence:
                sections.append("\n## RETRIEVED CASE LAW")
                for idx, result in enumerate(jurisprudence[:3], 1):
                    sections.append(f"\n### Case {idx}")
                    metadata = result.get('metadata', {})
                    sections.append(f"Court: {metadata.get('court', 'N/A')}")
                    sections.append(f"Date: {metadata.get('date', 'N/A')}")
                    sections.append(f"Summary: {result.get('text', '')[:300]}...")

        # KG enriched context
        if context.enriched_context:
            sections.append("\n## KNOWLEDGE GRAPH ENRICHMENT")
            # Format enriched context nicely
            for key, value in context.enriched_context.items():
                sections.append(f"\n**{key}**: {value}")

        return "\n".join(sections)

    def _parse_llm_response(self, llm_response: Dict[str, Any], context: ExpertContext) -> ExpertOpinion:
        """
        Parse LLM response into ExpertOpinion.

        Args:
            llm_response: Response from _call_llm
            context: Original ExpertContext

        Returns:
            ExpertOpinion

        Raises:
            ValueError: If response cannot be parsed
        """
        content = llm_response["content"]

        # Extract JSON from response (may be wrapped in markdown)
        try:
            # Try to find JSON block
            if "```json" in content:
                json_start = content.find("```json") + 7
                json_end = content.find("```", json_start)
                json_str = content[json_start:json_end].strip()
            elif "```" in content:
                json_start = content.find("```") + 3
                json_end = content.find("```", json_start)
                json_str = content[json_start:json_end].strip()
            else:
                json_str = content.strip()

            opinion_data = json.loads(json_str)

        except json.JSONDecodeError as e:
            self.logger.error(f"Failed to parse LLM response as JSON: {e}")
            self.logger.debug(f"Response content: {content[:500]}...")

            # Fallback: Create minimal opinion
            opinion_data = {
                "interpretation": content[:1000],  # Use raw text
                "confidence": 0.3,  # Low confidence for unparsed response
                "limitations": "Failed to parse structured response"
            }

        # Build ExpertOpinion
        return ExpertOpinion(
            expert_type=self.expert_type,
            trace_id=context.trace_id,
            interpretation=opinion_data.get("interpretation", ""),
            legal_basis=[LegalBasis(**lb) for lb in opinion_data.get("legal_basis", [])],
            reasoning_steps=[ReasoningStep(**rs) for rs in opinion_data.get("reasoning_steps", [])],
            confidence=opinion_data.get("confidence", 0.5),
            confidence_factors=ConfidenceFactors(**opinion_data.get("confidence_factors", {})),
            sources=[LegalBasis(**s) for s in opinion_data.get("sources", [])],
            limitations=opinion_data.get("limitations", ""),
            llm_model=self.model,
            temperature=self.temperature,
            tokens_used=llm_response["tokens_used"],
            execution_time_ms=llm_response["execution_time_ms"]
        )

    def __repr__(self) -> str:
        """String representation."""
        return (
            f"{self.__class__.__name__}("
            f"type={self.expert_type}, "
            f"model={self.model}, "
            f"temp={self.temperature})"
        )


# Export all classes
__all__ = [
    "ExpertContext",
    "ExpertOpinion",
    "LegalBasis",
    "ReasoningStep",
    "ConfidenceFactors",
    "ReasoningExpert",
]
