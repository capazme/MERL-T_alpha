"""
Synthesizer - Combines Expert Opinions
=======================================

Combines outputs from multiple reasoning experts into a single coherent answer.

Two modes:
- Convergent: Experts agree on conclusion (different reasoning, same result)
- Divergent: Experts disagree (preserve multiple perspectives)

The synthesizer:
1. Analyzes expert opinions for agreement/disagreement
2. Extracts common themes and divergent points
3. Builds unified answer with full provenance
4. Preserves uncertainty when experts disagree
"""

import json
import logging
import time
from typing import List, Optional, Dict, Any, Literal
from datetime import datetime
from pathlib import Path

from pydantic import BaseModel, Field

from backend.rlcf_framework.ai_service import openrouter_service
from .base import ExpertOpinion

logger = logging.getLogger(__name__)


# ============================================================================
# Output Data Models
# ============================================================================

class ProvenanceClaim(BaseModel):
    """Individual claim with provenance."""
    claim_id: str
    claim_text: str  # The claim in Italian
    sources: List[Dict[str, Any]] = Field(default_factory=list)  # Legal sources
    expert_support: List[Dict[str, Any]] = Field(default_factory=list)  # Which experts agree


class ProvisionalAnswer(BaseModel):
    """
    Synthesized answer from multiple experts.

    Contains:
    - Final answer (Italian text)
    - Synthesis strategy (convergent/divergent)
    - Full provenance (every claim traced to sources + experts)
    - Confidence
    """
    trace_id: str

    # Final answer
    final_answer: str  # Unified Italian text

    # Synthesis metadata
    synthesis_mode: Literal["convergent", "divergent"]
    synthesis_strategy: str  # How experts were combined

    # Expert consensus
    experts_consulted: List[str] = Field(default_factory=list)
    consensus_level: float = Field(ge=0.0, le=1.0)  # 0=full disagreement, 1=full agreement

    # Confidence
    confidence: float = Field(ge=0.0, le=1.0)
    confidence_rationale: str = ""

    # Provenance
    provenance: List[ProvenanceClaim] = Field(default_factory=list)

    # Metadata
    llm_model: str
    tokens_used: int
    execution_time_ms: float
    timestamp: str = Field(default_factory=lambda: datetime.utcnow().isoformat())


# ============================================================================
# Synthesizer
# ============================================================================

class Synthesizer:
    """
    Synthesizes multiple expert opinions into single answer.

    Handles two modes:
    - Convergent: Extract consensus when experts agree
    - Divergent: Preserve perspectives when experts disagree
    """

    def __init__(self, config: Optional[Dict[str, Any]] = None):
        """
        Initialize synthesizer.

        Args:
            config: Synthesizer configuration
        """
        self.config = config or {}
        self.logger = logging.getLogger("synthesizer")

        # LLM configuration
        self.model = self.config.get("model", "google/gemini-2.5-flash")
        self.temperature = self.config.get("temperature", 0.2)
        self.max_tokens = self.config.get("max_tokens", 3000)

        # AI service
        self.ai_service = openrouter_service

        # Load prompts
        self.convergent_prompt = self._load_prompt("synthesizer_convergent.txt")
        self.divergent_prompt = self._load_prompt("synthesizer_divergent.txt")

        self.logger.info("Synthesizer initialized")

    def _load_prompt(self, filename: str) -> str:
        """
        Load prompt template.

        Args:
            filename: Prompt filename

        Returns:
            Prompt content
        """
        prompt_file = (
            Path(__file__).parent.parent
            / "prompts"
            / filename
        )

        if not prompt_file.exists():
            self.logger.warning(
                f"Prompt template not found: {prompt_file}. "
                f"Using default template."
            )
            return self._get_default_prompt(filename)

        return prompt_file.read_text(encoding="utf-8")

    def _get_default_prompt(self, filename: str) -> str:
        """
        Get default prompt for synthesizer.

        Args:
            filename: Prompt filename (convergent or divergent)

        Returns:
            Default prompt string
        """
        if "convergent" in filename:
            return """You are a legal synthesizer. Multiple expert opinions are provided.

Your task: Combine them into a single coherent answer when experts AGREE on the conclusion.

Focus on:
- Common legal basis cited by multiple experts
- Consensus on interpretation
- Unified reasoning chain

Output format: JSON object with fields:
- final_answer: str (unified answer in Italian)
- synthesis_strategy: str (how you combined opinions)
- consensus_level: float (0.0-1.0, how much experts agree)
- confidence: float (0.0-1.0)
- confidence_rationale: str
- provenance: List[Dict] (claims with sources and expert support)

Respond with valid JSON only."""

        else:  # divergent
            return """You are a legal synthesizer. Multiple expert opinions are provided.

Your task: Present multiple perspectives when experts DISAGREE.

Focus on:
- Different interpretations and why they differ
- Legal basis for each perspective
- Reasoning for disagreement

Output format: JSON object with fields:
- final_answer: str (multi-perspective answer in Italian)
- synthesis_strategy: str (how you preserved disagreement)
- consensus_level: float (0.0-1.0, low for divergent)
- confidence: float (0.0-1.0, typically lower when divergent)
- confidence_rationale: str
- provenance: List[Dict] (claims with sources and expert support)

Respond with valid JSON only."""

    async def synthesize(
        self,
        expert_opinions: List[ExpertOpinion],
        synthesis_mode: Literal["convergent", "divergent"],
        query_text: str,
        trace_id: str
    ) -> ProvisionalAnswer:
        """
        Synthesize multiple expert opinions.

        Args:
            expert_opinions: List of expert opinions to synthesize
            synthesis_mode: "convergent" or "divergent"
            query_text: Original query
            trace_id: Trace ID for provenance

        Returns:
            ProvisionalAnswer with synthesized result
        """
        start_time = time.time()

        self.logger.info(
            f"Synthesizing {len(expert_opinions)} expert opinions "
            f"(mode={synthesis_mode})"
        )

        if not expert_opinions:
            raise ValueError("No expert opinions to synthesize")

        # Select prompt based on mode
        system_prompt = (
            self.convergent_prompt
            if synthesis_mode == "convergent"
            else self.divergent_prompt
        )

        # Format expert opinions for LLM
        user_prompt = self._format_expert_opinions(
            expert_opinions,
            query_text
        )

        # Enhanced JSON enforcement for synthesizer
        enhanced_system_prompt = f"""{system_prompt}

CRITICAL JSON FORMAT REQUIREMENTS:
1. Your response MUST be a valid JSON object matching the schema specified above
2. Do NOT include markdown code fences (```json or ```)
3. Do NOT include any explanatory text before or after the JSON
4. Start your response with {{ and end with }}
5. All string values must use double quotes, not single quotes
6. Ensure all required fields are present (final_answer, synthesis_strategy, consensus_level, confidence, etc.)

If you cannot provide a complete synthesis, still return valid JSON with partial data.
"""

        # Call LLM with retry logic
        synthesis_data = await self._call_synthesis_llm(
            enhanced_system_prompt,
            user_prompt
        )

        # Build ProvisionalAnswer
        elapsed_ms = (time.time() - start_time) * 1000

        answer = ProvisionalAnswer(
            trace_id=trace_id,
            final_answer=synthesis_data.get("final_answer", ""),
            synthesis_mode=synthesis_mode,
            synthesis_strategy=synthesis_data.get("synthesis_strategy", ""),
            experts_consulted=[op.expert_type for op in expert_opinions],
            consensus_level=synthesis_data.get("consensus_level", 0.5),
            confidence=synthesis_data.get("confidence", 0.5),
            confidence_rationale=synthesis_data.get("confidence_rationale", ""),
            provenance=[
                ProvenanceClaim(**p)
                for p in synthesis_data.get("provenance", [])
            ],
            llm_model=self.model,
            tokens_used=0,  # TODO: Extract from LLM response when available
            execution_time_ms=elapsed_ms
        )

        self.logger.info(
            f"Synthesis completed in {elapsed_ms:.2f}ms "
            f"(confidence={answer.confidence:.2f}, consensus={answer.consensus_level:.2f})"
        )

        return answer

    def _format_expert_opinions(
        self,
        opinions: List[ExpertOpinion],
        query_text: str
    ) -> str:
        """
        Format expert opinions for LLM.

        Args:
            opinions: List of expert opinions
            query_text: Original query

        Returns:
            Formatted string
        """
        sections = []

        sections.append(f"## ORIGINAL QUERY\n{query_text}\n")

        for idx, opinion in enumerate(opinions, 1):
            sections.append(f"\n## EXPERT {idx}: {opinion.expert_type.upper().replace('_', ' ')}")
            sections.append(f"\n**Interpretation**:\n{opinion.interpretation}\n")
            sections.append(f"\n**Confidence**: {opinion.confidence:.2f}")
            sections.append(f"\n**Reasoning Steps**: {len(opinion.reasoning_steps)}")
            sections.append(f"\n**Legal Basis**: {len(opinion.legal_basis)} sources")
            sections.append(f"\n**Limitations**: {opinion.limitations}\n")

            # Include first few sources for context
            if opinion.sources:
                sections.append("\n**Key Sources**:")
                for source in opinion.sources[:3]:
                    sections.append(f"- {source.citation}: {source.relevance}")

        return "\n".join(sections)

    async def _call_synthesis_llm(
        self,
        system_prompt: str,
        user_prompt: str,
        max_retries: int = 3
    ) -> Dict[str, Any]:
        """
        Call LLM for synthesis with guaranteed JSON output.

        Modern techniques (2025):
        1. JSON mode enforcement via prompt engineering
        2. Retry logic with exponential backoff
        3. Automatic cleanup of markdown code fences
        4. Fallback synthesis on persistent failure

        Args:
            system_prompt: Enhanced system prompt with JSON enforcement
            user_prompt: Formatted expert opinions
            max_retries: Maximum retry attempts (default: 3)

        Returns:
            Parsed JSON dict with synthesis data

        Raises:
            ValueError: If parsing fails after all retries and fallback
        """
        import asyncio

        for attempt in range(max_retries):
            try:
                # Call AI service
                response = await self.ai_service.generate_response_async(
                    prompt=f"{system_prompt}\n\nEXPERT OPINIONS:\n{user_prompt}",
                    model=self.model,
                    temperature=self.temperature,
                    max_tokens=self.max_tokens
                )

                # Parse response
                if isinstance(response, dict):
                    content = response.get("content", str(response))
                else:
                    content = str(response)

                # Clean markdown fences
                content = content.strip()

                if content.startswith("```json"):
                    content = content[7:]
                elif content.startswith("```"):
                    content = content[3:]

                if content.endswith("```"):
                    content = content[:-3]

                content = content.strip()

                # Validate JSON
                try:
                    synthesis_data = json.loads(content)

                    self.logger.info(
                        f"Synthesis LLM call succeeded on attempt {attempt + 1}"
                    )

                    return synthesis_data

                except json.JSONDecodeError as json_err:
                    self.logger.warning(
                        f"Attempt {attempt + 1}/{max_retries}: Synthesis returned invalid JSON: {str(json_err)}"
                    )
                    self.logger.debug(f"Response preview: {content[:500]}")

                    if attempt == max_retries - 1:
                        # Last attempt - use fallback
                        self.logger.error(
                            f"All {max_retries} attempts failed for synthesis. "
                            f"Using fallback synthesis."
                        )

                        # Return minimal valid structure
                        return {
                            "final_answer": "Sintesi non disponibile per errore di parsing JSON.",
                            "synthesis_strategy": "Fallback: JSON parsing failed after max retries",
                            "consensus_level": 0.5,
                            "confidence": 0.3,
                            "confidence_rationale": "Bassa confidenza dovuta a fallimento della sintesi",
                            "provenance": []
                        }

                    # Exponential backoff
                    wait_time = (2 ** attempt) * 0.5
                    self.logger.info(f"Waiting {wait_time}s before retry...")
                    await asyncio.sleep(wait_time)
                    continue

            except Exception as e:
                self.logger.error(
                    f"Synthesis LLM call failed on attempt {attempt + 1}: {str(e)}",
                    exc_info=True
                )

                if attempt == max_retries - 1:
                    # Last retry - return fallback
                    self.logger.error("Using fallback synthesis due to LLM error")

                    return {
                        "final_answer": "Sintesi non disponibile per errore del servizio LLM.",
                        "synthesis_strategy": f"Fallback: LLM error - {str(e)}",
                        "consensus_level": 0.5,
                        "confidence": 0.2,
                        "confidence_rationale": "Confidenza molto bassa per fallimento LLM",
                        "provenance": []
                    }

                # Retry with backoff
                wait_time = (2 ** attempt) * 0.5
                await asyncio.sleep(wait_time)
                continue

    def _create_fallback_synthesis(
        self,
        opinions: List[ExpertOpinion],
        query_text: str
    ) -> str:
        """
        Create fallback synthesis when LLM parsing fails.

        Args:
            opinions: Expert opinions
            query_text: Original query

        Returns:
            Basic synthesis text
        """
        sections = []

        sections.append(f"**Query**: {query_text}\n")
        sections.append(f"**Experts Consulted**: {len(opinions)}\n")

        for opinion in opinions:
            expert_name = opinion.expert_type.replace('_', ' ').title()
            sections.append(f"\n**{expert_name}** (confidenza: {opinion.confidence:.2f}):")
            sections.append(opinion.interpretation[:300] + "...")

        sections.append("\n*Nota: Sintesi automatica generata (fallback).*")

        return "\n".join(sections)

    def __repr__(self) -> str:
        """String representation."""
        return f"Synthesizer(model={self.model}, temp={self.temperature})"


# Export
__all__ = ["Synthesizer", "ProvisionalAnswer", "ProvenanceClaim"]
