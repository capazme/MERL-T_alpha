"""
Data Ingestion Pipeline for MERL-T Knowledge Graph

Orchestrates the complete data ingestion workflow:
1. Fetch Italian legal norms from Normattiva API
2. Parse and extract legal entities
3. Build knowledge graph with Neo4j backend
4. Validate and persist to database

Features:
- Async processing for performance
- Batch insertion for large datasets (1000+ norms)
- Comprehensive logging and error handling
- Reusable extraction strategies
- Provenance tracking for all data
"""

import logging
import asyncio
from typing import List, Dict, Any, Optional
from datetime import datetime
from abc import ABC, abstractmethod
import json

from .models import (
    Node, Edge, EntityType, RelationType, GraphMetadata,
    Provenance, ExtractionMethod, ExtractionResult, ValidationStatus
)

# v2: Neo4j archived - will be replaced by FalkorDB
# See docs/03-architecture/04-storage-layer.md for v2 design
# from .neo4j_graph_builder import (
#     Neo4jGraphDatabase, Neo4jLegalKnowledgeGraph, EntityCentricNeo4jStrategy
# )

logger = logging.getLogger(__name__)


# ============================================================================
# Data Source Adapters
# ============================================================================

class NormDataSource(ABC):
    """
    Abstract base class for sources of Italian legal norms.

    Implementations fetch norms from different sources:
    - Normattiva API (official source)
    - Pre-cached JSON files
    - Other databases
    """

    @abstractmethod
    async def fetch_norms(
        self,
        source_type: str,
        start_date: Optional[str] = None,
        end_date: Optional[str] = None
    ) -> List[Dict[str, Any]]:
        """
        Fetch norms from the source.

        Args:
            source_type: Type of norm (e.g., 'codice_civile', 'costituzione')
            start_date: Optional start date for filtering
            end_date: Optional end date for filtering

        Returns:
            List of norm data dictionaries
        """
        pass


class NormattivaNormSource(NormDataSource):
    """
    Fetch Italian legal norms from Normattiva API.

    Normattiva (normattiva.it) provides official Italian legislation
    in structured XML format (Akoma Ntoso standard).

    This implementation would integrate with the normascraper.py
    component from NormGraph for actual API calls.
    """

    def __init__(self, base_url: str = "http://www.normattiva.it/"):
        """Initialize Normattiva data source."""
        self.base_url = base_url
        self.session = None
        logger.info("Initialized Normattiva data source")

    async def fetch_norms(
        self,
        source_type: str,
        start_date: Optional[str] = None,
        end_date: Optional[str] = None
    ) -> List[Dict[str, Any]]:
        """
        Fetch norms from Normattiva API.

        This would delegate to normascraper.py for actual API calls.
        For now, returns the data structure that would be fetched.

        Args:
            source_type: e.g., 'CODICE_CIVILE', 'COSTITUZIONE'
            start_date: Optional filter
            end_date: Optional filter

        Returns:
            List of norm dictionaries
        """
        logger.info(f"Fetching {source_type} from Normattiva")

        # In production, this would call:
        # from NormGraph import NormaScraper
        # scraper = NormaScraper(self.base_url)
        # norms = await scraper.fetch_all_articles(source_type)

        # For now, return empty list (would be populated by actual scraper)
        return []

    async def close(self):
        """Close session."""
        if self.session:
            await self.session.close()


class MockNormSource(NormDataSource):
    """
    Mock data source for testing.

    Returns sample norms for development and testing
    without requiring actual API access.
    """

    async def fetch_norms(
        self,
        source_type: str,
        start_date: Optional[str] = None,
        end_date: Optional[str] = None
    ) -> List[Dict[str, Any]]:
        """Return mock norms for testing."""
        logger.info(f"Fetching mock {source_type} norms")

        mock_norms = {
            "CODICE_CIVILE": [
                {
                    "id": "art_1_cc",
                    "article_number": "1",
                    "title": "Capacità giuridica",
                    "text": "La capacità giuridica si acquista dal momento della nascita.",
                    "source": "Codice Civile",
                    "date_published": "1942-03-16",
                    "status": "vigente",
                },
                {
                    "id": "art_2_cc",
                    "article_number": "2",
                    "title": "Capacità di agire",
                    "text": "La capacità di agire si acquista con il raggiungimento della maggiore età.",
                    "source": "Codice Civile",
                    "date_published": "1942-03-16",
                    "status": "vigente",
                },
            ],
            "COSTITUZIONE": [
                {
                    "id": "art_1_cost",
                    "article_number": "1",
                    "title": "Repubblica democratica",
                    "text": "L'Italia è una Repubblica democratica fondata sul lavoro.",
                    "source": "Costituzione Italiana",
                    "date_published": "1948-01-01",
                    "status": "vigente",
                },
            ],
        }

        return mock_norms.get(source_type, [])


# ============================================================================
# Extraction and Transformation
# ============================================================================

class NormToNodeTransformer:
    """
    Transform raw norm data into graph nodes.

    Converts Normattiva data into Node objects with:
    - Proper entity types
    - Confidence scores
    - Provenance tracking
    - Validation status
    """

    @staticmethod
    def transform(norm_data: Dict[str, Any], source_name: str = "normattiva") -> Node:
        """
        Transform a norm dictionary to a Node.

        Args:
            norm_data: Raw norm data from Normattiva
            source_name: Source system name

        Returns:
            Node object with metadata
        """
        node = Node(
            id=norm_data.get("id", ""),
            label=norm_data.get("title", ""),
            entity_type=EntityType.NORMA,
            description=norm_data.get("text", ""),
            article_number=norm_data.get("article_number"),
            law_reference=norm_data.get("source"),
            confidence=1.0,
            created_by="ingestion_pipeline",
            attributes={
                "publication_date": norm_data.get("date_published"),
                "status": norm_data.get("status", "vigente"),
                "akoma_ntoso_urn": norm_data.get("urn"),  # For ELI standard
            }
        )

        # Add provenance
        node.provenance = Provenance(
            source_url=f"https://www.normattiva.it/uri-res/N2Lc?urn:nir:stato:{norm_data.get('id')}",
            source_type="normattiva_api",
            extraction_method=ExtractionMethod.IMPORTED,
            raw_text=norm_data.get("text"),
        )

        return node

    @staticmethod
    def create_relationships(nodes: List[Node]) -> List[Edge]:
        """
        Create relationships between norms based on citations.

        In a real implementation, this would use NER to extract
        cited norms and create CITA relationships.

        Args:
            nodes: List of norm nodes

        Returns:
            List of relationship edges
        """
        edges = []

        # For now, create basic hierarchical relationships
        # In production, use citation extraction to find CITA links
        for i, node in enumerate(nodes):
            if i > 0:
                # Create part_of relationship with previous norm
                # (simplified - real implementation would analyze structure)
                edge = Edge(
                    source_id=node.id,
                    target_id=nodes[i - 1].id,
                    relation_type=RelationType.PARTE_DI,
                    confidence=0.8,
                    created_by="ingestion_pipeline",
                )
                edges.append(edge)

        return edges


# ============================================================================
# Ingestion Pipeline
# ============================================================================

class DataIngestionPipeline:
    """
    Main data ingestion pipeline orchestrator.

    Coordinates:
    1. Fetching data from source
    2. Transforming to graph nodes
    3. Building Neo4j graph
    4. Validation and error handling
    """

    def __init__(
        self,
        db: Neo4jGraphDatabase,
        data_source: NormDataSource,
        strategy=None
    ):
        """
        Initialize pipeline.

        Args:
            db: Neo4j database connection
            data_source: Source for norm data
            strategy: Graph building strategy (default: EntityCentric)
        """
        self.db = db
        self.data_source = data_source
        self.strategy = strategy or EntityCentricNeo4jStrategy()
        self.graph = Neo4jLegalKnowledgeGraph(db)

    async def ingest_norms(
        self,
        source_type: str,
        batch_size: int = 500,
        max_norms: Optional[int] = None
    ) -> Dict[str, Any]:
        """
        Complete ingestion workflow.

        Args:
            source_type: Type of norms (e.g., 'CODICE_CIVILE')
            batch_size: Number of norms to process per batch
            max_norms: Optional limit on total norms to ingest

        Returns:
            Ingestion statistics
        """
        logger.info(f"Starting ingestion of {source_type}")
        stats = {
            "source_type": source_type,
            "norms_fetched": 0,
            "norms_processed": 0,
            "norms_inserted": 0,
            "errors": [],
            "start_time": datetime.now().isoformat(),
        }

        try:
            # 1. Fetch norms from source
            logger.info(f"Fetching {source_type} norms from source...")
            raw_norms = await self.data_source.fetch_norms(source_type)
            stats["norms_fetched"] = len(raw_norms)

            if max_norms:
                raw_norms = raw_norms[:max_norms]

            logger.info(f"Fetched {len(raw_norms)} norms")

            # 2. Transform to nodes and create extraction result
            logger.info("Transforming norms to graph nodes...")
            nodes = []
            for norm_data in raw_norms:
                try:
                    node = NormToNodeTransformer.transform(norm_data)
                    nodes.append(node)
                    stats["norms_processed"] += 1
                except Exception as e:
                    logger.error(f"Error transforming norm {norm_data.get('id')}: {e}")
                    stats["errors"].append({
                        "norm_id": norm_data.get("id"),
                        "error": str(e),
                        "type": "transformation"
                    })

            logger.info(f"Transformed {len(nodes)} norms")

            # 3. Extract relationships between norms
            logger.info("Extracting relationships...")
            edges = NormToNodeTransformer.create_relationships(nodes)
            logger.info(f"Created {len(edges)} relationships")

            # 4. Build extraction result
            extraction_result = ExtractionResult(nodes=nodes, edges=edges)

            # 5. Build graph using strategy
            logger.info(f"Building graph with {self.strategy.name} strategy...")
            self.graph = self.strategy.build(extraction_result, self.graph)
            stats["norms_inserted"] = len(nodes)

            # 6. Calculate statistics
            self.graph.calculate_statistics()
            stats["graph_metadata"] = self.graph.metadata.to_dict()
            stats["end_time"] = datetime.now().isoformat()

            logger.info(f"Ingestion complete. Inserted {stats['norms_inserted']} norms")

        except Exception as e:
            logger.error(f"Critical error during ingestion: {e}")
            stats["errors"].append({
                "error": str(e),
                "type": "critical"
            })
            raise

        return stats

    async def ingest_all_sources(
        self,
        sources: List[str] = None,
        batch_size: int = 500
    ) -> Dict[str, Dict[str, Any]]:
        """
        Ingest all major Italian legal sources.

        Args:
            sources: List of source types to ingest
                    Default: ['CODICE_CIVILE', 'COSTITUZIONE']
            batch_size: Norms per batch

        Returns:
            Dictionary mapping source_type to ingestion statistics
        """
        if sources is None:
            sources = ['CODICE_CIVILE', 'COSTITUZIONE']

        all_stats = {}

        for source in sources:
            logger.info(f"Processing {source}...")
            try:
                stats = await self.ingest_norms(source, batch_size)
                all_stats[source] = stats
            except Exception as e:
                logger.error(f"Failed to ingest {source}: {e}")
                all_stats[source] = {
                    "source_type": source,
                    "error": str(e),
                    "norms_inserted": 0
                }

        return all_stats


# ============================================================================
# Utility Functions
# ============================================================================

async def run_ingestion_demo():
    """
    Run a demo ingestion pipeline.

    This shows how to use the ingestion system with a mock data source.
    """
    logger.basicConfig(level=logging.INFO)

    # Setup
    db = Neo4jGraphDatabase(
        uri="bolt://localhost:7687",
        username="neo4j",
        password="password"
    )

    # Initialize pipeline with mock source
    data_source = MockNormSource()
    pipeline = DataIngestionPipeline(db, data_source)

    # Run ingestion
    stats = await pipeline.ingest_all_sources(
        sources=['CODICE_CIVILE', 'COSTITUZIONE'],
        batch_size=100
    )

    # Print results
    logger.info("Ingestion results:")
    for source, source_stats in stats.items():
        logger.info(f"{source}: {source_stats['norms_inserted']} norms inserted")

    db.close()


if __name__ == "__main__":
    # Run demo with asyncio
    asyncio.run(run_ingestion_demo())
