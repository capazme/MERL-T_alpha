"""
FalkorDB Config
===============

Configurazione per FalkorDB client.

Usage:
    from merlt.storage.graph import FalkorDBConfig

    config = FalkorDBConfig(host="localhost", port=6380, graph_name="merl_t")
"""

from dataclasses import dataclass


@dataclass
class FalkorDBConfig:
    """Configurazione connessione FalkorDB."""
    host: str = "localhost"
    port: int = 6380
    graph_name: str = "merl_t_dev"  # Convenzione: _dev per sviluppo, _prod per produzione
    password: str = ""
