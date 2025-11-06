"""
Literal Interpreter Expert - Positivismo Giuridico
===================================================

Epistemology: Legal Positivism
- Law = Written text of norms
- Interpretation = Strict textual analysis
- Focus: What the law SAYS (not why, not context)

Strengths:
- High precision for clear rules
- Fast (single-pass textual analysis)
- High confidence when norms are unambiguous

Limitations:
- Ignores ratio legis (purpose of law)
- Ignores jurisprudence trends
- Ignores constitutional principles
- Weak on ambiguous or incomplete norms

Reference: Hans Kelsen, Herbert Hart (legal positivism)
"""

import logging
from typing import Optional, Dict, Any

from .base import ReasoningExpert, ExpertContext, ExpertOpinion

logger = logging.getLogger(__name__)


class LiteralInterpreter(ReasoningExpert):
    """
    Literal Interpreter: Strict textual analysis of legal norms.

    Applies positivist methodology:
    1. Identify applicable norms from context
    2. Textual analysis (definitions, grammar, logical conditions)
    3. Apply to facts
    4. Conclude based on literal reading
    """

    def __init__(self, config: Optional[Dict[str, Any]] = None):
        super().__init__(expert_type="literal_interpreter", config=config)

    async def analyze(self, context: ExpertContext) -> ExpertOpinion:
        """
        Perform literal interpretation.

        Args:
            context: ExpertContext with query + retrieved norms

        Returns:
            ExpertOpinion with positivist reasoning
        """
        self.logger.info(f"Literal Interpreter analyzing query: {context.query_text[:50]}...")

        # Format context for LLM
        user_prompt = self._format_context(context)

        # Call LLM with literal interpreter prompt
        llm_response = await self._call_llm(
            system_prompt=self.prompt_template,
            user_prompt=user_prompt
        )

        # Parse LLM response into ExpertOpinion
        opinion = self._parse_llm_response(llm_response, context)

        self.logger.info(
            f"Literal Interpreter completed (confidence={opinion.confidence:.2f})"
        )

        return opinion
