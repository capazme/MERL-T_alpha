"""
Preprocessing Module
====================

Components for parsing and chunking legal documents from VisualexAPI.

Modules:
- comma_parser: Parse article text into structured components
- structural_chunker: Create comma-level chunks for vector storage
- visualex_ingestion: Full ingestion pipeline to graph database
"""

from .comma_parser import (
    Comma,
    ArticleStructure,
    CommaParser,
    parse_article,
    count_tokens,
)

from .structural_chunker import (
    Chunk,
    ChunkMetadata,
    StructuralChunker,
    chunk_article,
)

__all__ = [
    # Comma Parser
    "Comma",
    "ArticleStructure",
    "CommaParser",
    "parse_article",
    "count_tokens",
    # Structural Chunker
    "Chunk",
    "ChunkMetadata",
    "StructuralChunker",
    "chunk_article",
]
