"""
Precedent Analyst - Empirismo Giuridico
========================================

Epistemology: Legal Empiricism
- Law = What courts ACTUALLY do (not just what statutes say)
- Interpretation = Analyzing case law trends and precedents
- Focus: Judicial interpretation patterns

Strengths:
- Captures how courts actually interpret norms
- Identifies trends in case law
- Distinguishes binding vs persuasive precedents
- Predicts likely judicial outcome

Limitations:
- Requires access to case law database (VectorDB)
- Italian law is civil law (precedents less binding than common law)
- Slower (must analyze multiple cases)

Reference: Oliver Wendell Holmes Jr., Legal Realism
"""

import logging
from typing import Optional, Dict, Any

from .base import ReasoningExpert, ExpertContext, ExpertOpinion

logger = logging.getLogger(__name__)


class PrecedentAnalyst(ReasoningExpert):
    """
    Precedent Analyst: Case law analysis and trend identification.

    Applies empiricist methodology:
    1. Identify relevant case law from VectorDB
    2. Chronological analysis (identify trends)
    3. Precedent hierarchy (Corte Costituzionale > Cassazione > lower courts)
    4. Ratio decidendi extraction
    5. Synthesize trend and predict outcome
    """

    def __init__(self, config: Optional[Dict[str, Any]] = None):
        super().__init__(expert_type="precedent_analyst", config=config)

    async def analyze(self, context: ExpertContext) -> ExpertOpinion:
        """
        Perform precedent analysis.

        Args:
            context: ExpertContext with query + case law

        Returns:
            ExpertOpinion with precedent analysis
        """
        self.logger.info(f"Precedent Analyst analyzing query: {context.query_text[:50]}...")

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
            f"Precedent Analyst completed (confidence={opinion.confidence:.2f})"
        )

        return opinion
