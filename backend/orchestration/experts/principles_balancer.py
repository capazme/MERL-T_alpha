"""
Principles Balancer - Costituzionalismo
========================================

Epistemology: Constitutionalism
- Law = Hierarchy of norms (Costituzione > Legge > Regolamento)
- Interpretation = Balancing competing constitutional principles
- Focus: Which principle prevails in case of conflict

Strengths:
- Handles principle conflicts (privacy vs free speech)
- Applies constitutional hierarchy
- Considers fundamental rights
- Balancing test (proportionality)

Limitations:
- Requires deep constitutional knowledge
- Balancing is context-dependent (no fixed rules)
- Slower (multi-level analysis)

Reference: Robert Alexy, Ronald Dworkin (principles theory)
"""

import logging
from typing import Optional, Dict, Any

from .base import ReasoningExpert, ExpertContext, ExpertOpinion

logger = logging.getLogger(__name__)


class PrinciplesBalancer(ReasoningExpert):
    """
    Principles Balancer: Constitutional principle balancing.

    Applies constitutionalist methodology:
    1. Identify principles in conflict
    2. Constitutional basis for each principle
    3. Hierarchical analysis (Costituzione > Legge)
    4. Balancing test (proportionality)
    5. Conclude which principle prevails
    """

    def __init__(self, config: Optional[Dict[str, Any]] = None):
        super().__init__(expert_type="principles_balancer", config=config)

    async def analyze(self, context: ExpertContext) -> ExpertOpinion:
        """
        Perform principle balancing.

        Args:
            context: ExpertContext with query + constitutional context

        Returns:
            ExpertOpinion with balancing analysis
        """
        self.logger.info(f"Principles Balancer analyzing query: {context.query_text[:50]}...")

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
            f"Principles Balancer completed (confidence={opinion.confidence:.2f})"
        )

        return opinion
