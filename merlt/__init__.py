"""
MERL-T: Libreria per l'Informatica Giuridica Italiana
=====================================================

Knowledge graph giuridico con ricerca semantica ibrida e interpretazione
multi-expert basata sui canoni ermeneutici delle Preleggi (artt. 12-14).

Quick Start:
    from merlt import LegalKnowledgeGraph, MerltConfig

    config = MerltConfig()
    kg = LegalKnowledgeGraph(config)
    await kg.connect()

    # Ingestion
    result = await kg.ingest("codice penale", "52")

    # Ricerca
    results = await kg.search("legittima difesa")

    # Interpretazione multi-expert
    interpretation = await kg.interpret("Cos'è la legittima difesa?")
    print(interpretation.synthesis)

Componenti:
- core: LegalKnowledgeGraph, MerltConfig, InterpretationResult
- sources: NormattivaScraper, BrocardiScraper
- storage: FalkorDBClient, EmbeddingService, BridgeTable
- pipeline: IngestionPipelineV2, MultivigenzaPipeline
- experts: LiteralExpert, SystemicExpert, PrinciplesExpert, PrecedentExpert
- rlcf: AuthorityModule, AggregationEngine

Docs: https://github.com/your-org/merlt
"""

__version__ = "0.1.0"
__author__ = "MERL-T Team"

# Core API
from merlt.core import LegalKnowledgeGraph, MerltConfig
from merlt.core.legal_knowledge_graph import InterpretationResult

# Convenience exports
from merlt.sources import NormattivaScraper, BrocardiScraper
from merlt.storage import FalkorDBClient, EmbeddingService

__all__ = [
    # Core
    "LegalKnowledgeGraph",
    "MerltConfig",
    "InterpretationResult",
    # Sources
    "NormattivaScraper",
    "BrocardiScraper",
    # Storage
    "FalkorDBClient",
    "EmbeddingService",
]
