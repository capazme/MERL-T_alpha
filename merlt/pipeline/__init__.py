"""
MERL-T Pipeline
===============

Pipeline di processing per ingestion articoli.

Componenti:
- IngestionPipelineV2: Pipeline principale
- CommaParser: Parsing articoli in componenti strutturati
- StructuralChunker: Chunking a livello comma
- MultivigenzaPipeline: Gestione versioni e modifiche

Esempio:
    from merlt.pipeline import IngestionPipelineV2

    pipeline = IngestionPipelineV2(falkordb_client, bridge_table)
    results = await pipeline.ingest_article(article)
"""

from merlt.pipeline.ingestion import IngestionPipelineV2
from merlt.pipeline.parsing import CommaParser, ArticleStructure, parse_article
from merlt.pipeline.chunking import StructuralChunker, Chunk, chunk_article
from merlt.pipeline.multivigenza import MultivigenzaPipeline

__all__ = [
    "IngestionPipelineV2",
    "CommaParser",
    "ArticleStructure",
    "parse_article",
    "StructuralChunker",
    "Chunk",
    "chunk_article",
    "MultivigenzaPipeline",
]
