"""
Systemic-Teleological Reasoner - Finalismo Giuridico
=====================================================

Epistemology: Legal Teleology
- Law = System of norms with purpose
- Interpretation = Understanding ratio legis + systemic coherence
- Focus: WHY the law exists, how norms fit together

Strengths:
- Handles ambiguous norms well
- Considers purpose of legislation
- Systemic coherence analysis
- Fills legal gaps via analogy

Limitations:
- More subjective than literal interpretation
- Requires understanding of legislative intent (not always clear)
- Slower (multi-step analysis)

Reference: Emilio Betti, Luigi Mengoni (teleological interpretation)
"""

import logging
from typing import Optional, Dict, Any

from .base import ReasoningExpert, ExpertContext, ExpertOpinion

logger = logging.getLogger(__name__)


class SystemicTeleological(ReasoningExpert):
    """
    Systemic-Teleological Reasoner: Purpose-oriented interpretation.

    Applies teleological methodology:
    1. Identify applicable norms
    2. Ratio legis analysis (why was this rule created?)
    3. Systemic coherence (how does it fit in the legal system?)
    4. Teleological interpretation (interpret in light of purpose)
    5. Conclude
    """

    def __init__(self, config: Optional[Dict[str, Any]] = None):
        super().__init__(expert_type="systemic_teleological", config=config)

    async def analyze(self, context: ExpertContext) -> ExpertOpinion:
        """
        Perform systemic-teleological interpretation.

        Args:
            context: ExpertContext with query + retrieved data

        Returns:
            ExpertOpinion with teleological reasoning
        """
        self.logger.info(f"Systemic-Teleological analyzing query: {context.query_text[:50]}...")

        # Format context
        user_prompt = self._format_context(context)

        # Call LLM
        llm_response = await self._call_llm(
            system_prompt=self.prompt_template,
            user_prompt=user_prompt
        )

        # Parse response
        opinion = self._parse_llm_response(llm_response, context)

        self.logger.info(
            f"Systemic-Teleological completed (confidence={opinion.confidence:.2f})"
        )

        return opinion
