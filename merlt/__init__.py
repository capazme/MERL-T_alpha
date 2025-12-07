"""
MERL-T: Libreria per l'Informatica Giuridica Italiana
=====================================================

Knowledge graph giuridico con ricerca semantica ibrida.

Quick Start:
    from merlt import LegalKnowledgeGraph, MerltConfig

    config = MerltConfig()
    kg = LegalKnowledgeGraph(config)
    await kg.connect()

    # Ingestion
    result = await kg.ingest("codice penale", "52")

    # Ricerca
    results = await kg.search("legittima difesa")

Componenti:
- core: LegalKnowledgeGraph, MerltConfig
- sources: NormattivaScraper, BrocardiScraper
- storage: FalkorDBClient, EmbeddingService, BridgeTable
- pipeline: IngestionPipelineV2, MultivigenzaPipeline
- rlcf: AuthorityModule, AggregationEngine

Docs: https://github.com/your-org/merlt
"""

__version__ = "0.1.0"
__author__ = "MERL-T Team"

# Core API
from merlt.core import LegalKnowledgeGraph, MerltConfig

# Convenience exports
from merlt.sources import NormattivaScraper, BrocardiScraper
from merlt.storage import FalkorDBClient, EmbeddingService

__all__ = [
    # Core
    "LegalKnowledgeGraph",
    "MerltConfig",
    # Sources
    "NormattivaScraper",
    "BrocardiScraper",
    # Storage
    "FalkorDBClient",
    "EmbeddingService",
]
