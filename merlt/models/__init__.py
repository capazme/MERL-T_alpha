"""
MERL-T Data Models
==================

Dataclasses condivisi tra i moduli del package.

Centralizza i modelli per evitare dipendenze circolari
e violazioni del principio di inversione delle dipendenze.
"""

from merlt.models.mappings import BridgeMapping

__all__ = [
    "BridgeMapping",
]
