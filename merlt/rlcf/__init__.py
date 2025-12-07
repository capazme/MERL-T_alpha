"""
MERL-T RLCF Framework
=====================

Reinforcement Learning from Collective Feedback per ricerca giuridica.

Componenti:
- AuthorityModule: Scoring basato su autorevolezza fonte
- AggregationEngine: Aggregazione feedback esperti

Esempio:
    from merlt.rlcf import AuthorityModule

    authority = AuthorityModule()
    score = authority.compute_authority_score(source)
"""

from merlt.rlcf.authority import AuthorityModule
from merlt.rlcf.aggregation import AggregationEngine
from merlt.rlcf.models import RLCFFeedback, AuthorityScore

__all__ = [
    "AuthorityModule",
    "AggregationEngine",
    "RLCFFeedback",
    "AuthorityScore",
]
