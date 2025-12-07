"""
Legal Knowledge Graph
=====================

Core orchestration class that coordinates all MERL-T components:
- FalkorDB (graph storage)
- Qdrant (vector embeddings)
- PostgreSQL Bridge Table (chunk <-> node mapping)
- Multivigenza Pipeline (amendment tracking)

This class provides a unified API for legal knowledge management,
integrating components that were previously managed by separate scripts.

Usage:
    from merlt import LegalKnowledgeGraph, MerltConfig

    config = MerltConfig(
        falkordb_host="localhost",
        falkordb_port=6380,
        graph_name="merl_t_test",
        qdrant_host="localhost",
        qdrant_port=6333,
        postgres_url="postgresql://...",
    )

    kg = LegalKnowledgeGraph(config)
    await kg.connect()

    # Ingest a single article with all integrations
    result = await kg.ingest_norm(
        tipo_atto="codice penale",
        articolo="1",
        include_brocardi=True,
        include_embeddings=True,
        include_bridge=True,
        include_multivigenza=True,
    )

    # Search with hybrid retrieval
    results = await kg.search("Cos'è la legittima difesa?", top_k=5)

    await kg.close()
"""

import logging
from dataclasses import dataclass, field
from typing import Dict, List, Optional, Any
from uuid import UUID

# Storage
from merlt.storage import (
    FalkorDBClient,
    FalkorDBConfig,
    BridgeTable,
    BridgeTableConfig,
    GraphAwareRetriever,
    RetrieverConfig,
)
from merlt.storage.bridge import BridgeBuilder

# Pipeline
from merlt.pipeline.ingestion import (
    IngestionPipelineV2,
    IngestionResult,
    BridgeMapping,
)
from merlt.pipeline.multivigenza import (
    MultivigenzaPipeline,
    MultivigenzaResult,
)
from merlt.pipeline.visualex import VisualexArticle, NormaMetadata

# Sources
from merlt.sources.normattiva import NormattivaScraper
from merlt.sources.brocardi import BrocardiScraper
from merlt.sources.utils.norma import NormaVisitata, Norma
from merlt.sources.utils.tree import (
    NormTree,
    get_article_position,
    get_hierarchical_tree,
)

# Embeddings (optional, loaded lazily)
try:
    from merlt.storage.vectors.embeddings import EmbeddingService
    HAS_EMBEDDING_SERVICE = True
except ImportError:
    HAS_EMBEDDING_SERVICE = False

# Qdrant (optional, loaded lazily)
try:
    from qdrant_client import QdrantClient
    from qdrant_client.models import PointStruct, VectorParams, Distance
    HAS_QDRANT = True
except ImportError:
    HAS_QDRANT = False

logger = logging.getLogger(__name__)


@dataclass
class MerltConfig:
    """
    Configuration for LegalKnowledgeGraph.

    All URLs/hosts default to localhost development setup.
    """
    # FalkorDB
    falkordb_host: str = "localhost"
    falkordb_port: int = 6380
    graph_name: str = "merl_t_test"

    # Qdrant
    qdrant_host: str = "localhost"
    qdrant_port: int = 6333
    qdrant_collection: Optional[str] = None  # Defaults to graph_name

    # PostgreSQL Bridge Table
    postgres_host: str = "localhost"
    postgres_port: int = 5433
    postgres_database: str = "rlcf_dev"
    postgres_user: str = "dev"
    postgres_password: str = "devpassword"

    # Embedding model
    embedding_model: str = "intfloat/multilingual-e5-large"
    embedding_dimension: int = 1024

    # Rate limiting for scrapers
    delay_between_articles: float = 1.0
    batch_size: int = 10
    delay_between_batches: float = 3.0

    def __post_init__(self):
        if self.qdrant_collection is None:
            self.qdrant_collection = self.graph_name


@dataclass
class UnifiedIngestionResult:
    """
    Result of ingesting a norm with all integrations.

    Combines results from:
    - IngestionPipelineV2 (graph + chunks)
    - Bridge Table insertions
    - Qdrant vector upserts
    - MultivigenzaPipeline (amendments)
    """
    article_urn: str
    article_url: str

    # Graph
    nodes_created: List[str] = field(default_factory=list)
    relations_created: List[str] = field(default_factory=list)
    brocardi_enriched: bool = False

    # Chunks and embeddings
    chunks_created: int = 0
    embeddings_upserted: int = 0

    # Bridge table
    bridge_mappings_inserted: int = 0

    # Multivigenza
    modifiche_count: int = 0
    atti_modificanti_created: List[str] = field(default_factory=list)
    multivigenza_relations: List[str] = field(default_factory=list)

    # Errors
    errors: List[str] = field(default_factory=list)

    def summary(self) -> Dict[str, Any]:
        """Return summary for logging."""
        return {
            "article_urn": self.article_urn,
            "nodes": len(self.nodes_created),
            "relations": len(self.relations_created),
            "chunks": self.chunks_created,
            "embeddings": self.embeddings_upserted,
            "bridge_mappings": self.bridge_mappings_inserted,
            "modifiche": self.modifiche_count,
            "atti_modificanti": len(self.atti_modificanti_created),
            "brocardi": self.brocardi_enriched,
            "errors": len(self.errors),
        }


class LegalKnowledgeGraph:
    """
    Unified orchestration layer for MERL-T legal knowledge graph.

    This class coordinates all storage backends and processing pipelines,
    providing a single entry point for:

    1. **Ingestion**: Graph nodes + embeddings + bridge table + multivigenza
    2. **Search**: Hybrid semantic + graph-aware retrieval
    3. **Export**: Data export for training pipelines

    Architecture:
        LegalKnowledgeGraph
        ├── FalkorDBClient (graph storage)
        ├── QdrantClient (vector storage)
        ├── BridgeTable (chunk <-> node mapping)
        ├── IngestionPipelineV2 (graph ingestion)
        ├── MultivigenzaPipeline (amendment tracking)
        ├── EmbeddingService (vector generation)
        ├── NormattivaScraper (official text)
        └── BrocardiScraper (enrichment)
    """

    def __init__(self, config: Optional[MerltConfig] = None):
        """
        Initialize LegalKnowledgeGraph.

        Components are created but not connected until connect() is called.

        Args:
            config: MerltConfig with connection parameters
        """
        self.config = config or MerltConfig()

        # Storage clients (initialized in connect())
        self._falkordb: Optional[FalkorDBClient] = None
        self._qdrant: Optional[Any] = None  # QdrantClient
        self._bridge_table: Optional[BridgeTable] = None

        # Pipelines (initialized in connect())
        self._ingestion_pipeline: Optional[IngestionPipelineV2] = None
        self._multivigenza_pipeline: Optional[MultivigenzaPipeline] = None
        self._bridge_builder: Optional[BridgeBuilder] = None

        # Scrapers
        self._normattiva_scraper: Optional[NormattivaScraper] = None
        self._brocardi_scraper: Optional[BrocardiScraper] = None

        # Services
        self._embedding_service: Optional[Any] = None  # EmbeddingService

        # Hierarchies cache
        self._norm_trees: Dict[str, NormTree] = {}

        self._connected = False

        logger.info(f"LegalKnowledgeGraph initialized with config: {self.config.graph_name}")

    async def connect(self) -> None:
        """
        Connect to all storage backends.

        Must be called before any operations.
        """
        if self._connected:
            logger.warning("Already connected")
            return

        logger.info("Connecting to storage backends...")

        # FalkorDB
        falkordb_config = FalkorDBConfig(
            host=self.config.falkordb_host,
            port=self.config.falkordb_port,
            graph_name=self.config.graph_name,
        )
        self._falkordb = FalkorDBClient(falkordb_config)
        await self._falkordb.connect()
        logger.info(f"FalkorDB connected: {self.config.graph_name}")

        # Qdrant (optional)
        if HAS_QDRANT:
            try:
                self._qdrant = QdrantClient(
                    host=self.config.qdrant_host,
                    port=self.config.qdrant_port,
                )
                # Ensure collection exists
                await self._ensure_qdrant_collection()
                logger.info(f"Qdrant connected: {self.config.qdrant_collection}")
            except Exception as e:
                logger.warning(f"Qdrant connection failed: {e}")
                self._qdrant = None

        # Bridge Table
        try:
            bridge_config = BridgeTableConfig(
                host=self.config.postgres_host,
                port=self.config.postgres_port,
                database=self.config.postgres_database,
                user=self.config.postgres_user,
                password=self.config.postgres_password,
            )
            self._bridge_table = BridgeTable(bridge_config)
            await self._bridge_table.connect()
            self._bridge_builder = BridgeBuilder(self._bridge_table)
            logger.info("Bridge Table connected")
        except Exception as e:
            logger.warning(f"Bridge Table connection failed: {e}")
            self._bridge_table = None
            self._bridge_builder = None

        # Initialize pipelines
        self._ingestion_pipeline = IngestionPipelineV2(
            falkordb_client=self._falkordb,
        )

        # Initialize scrapers
        self._normattiva_scraper = NormattivaScraper()
        self._brocardi_scraper = BrocardiScraper()

        # Multivigenza pipeline
        self._multivigenza_pipeline = MultivigenzaPipeline(
            falkordb_client=self._falkordb,
            scraper=self._normattiva_scraper,
        )

        # Embedding service (lazy loaded on first use)
        if HAS_EMBEDDING_SERVICE:
            try:
                self._embedding_service = EmbeddingService.get_instance(
                    model_name=self.config.embedding_model
                )
            except Exception as e:
                logger.warning(f"Embedding service initialization failed: {e}")

        self._connected = True
        logger.info("LegalKnowledgeGraph connected successfully")

    async def close(self) -> None:
        """Close all connections."""
        if self._falkordb:
            await self._falkordb.close()
        if self._bridge_table:
            await self._bridge_table.close()
        if self._qdrant:
            self._qdrant.close()

        self._connected = False
        logger.info("LegalKnowledgeGraph connections closed")

    async def _ensure_qdrant_collection(self) -> None:
        """Ensure Qdrant collection exists with correct parameters."""
        if not self._qdrant:
            return

        collection_name = self.config.qdrant_collection
        collections = self._qdrant.get_collections().collections
        exists = any(c.name == collection_name for c in collections)

        if not exists:
            self._qdrant.create_collection(
                collection_name=collection_name,
                vectors_config=VectorParams(
                    size=self.config.embedding_dimension,
                    distance=Distance.COSINE,
                ),
            )
            logger.info(f"Created Qdrant collection: {collection_name}")

    async def ingest_norm(
        self,
        tipo_atto: str,
        articolo: str,
        include_brocardi: bool = True,
        include_embeddings: bool = True,
        include_bridge: bool = True,
        include_multivigenza: bool = True,
        norm_tree: Optional[NormTree] = None,
    ) -> UnifiedIngestionResult:
        """
        Ingest a single legal norm with all integrations.

        This is the main entry point for adding legal content to the knowledge graph.
        All backend operations (graph, vectors, bridge table, multivigenza) are
        handled automatically.

        Args:
            tipo_atto: Type of act (e.g., "codice penale", "codice civile")
            articolo: Article number (e.g., "1", "52", "81 bis")
            include_brocardi: Whether to fetch Brocardi enrichment
            include_embeddings: Whether to generate and store embeddings
            include_bridge: Whether to update bridge table
            include_multivigenza: Whether to track amendments

        Returns:
            UnifiedIngestionResult with all operation results
        """
        if not self._connected:
            raise RuntimeError("Not connected. Call connect() first.")

        # Normalize article number
        articolo_norm = articolo.replace(' ', '-')

        # Create NormaVisitata reference
        norma = Norma(tipo_atto=tipo_atto, data=None, numero_atto=None)
        nv = NormaVisitata(norma=norma, numero_articolo=articolo_norm)

        logger.info(f"Ingesting: {tipo_atto} art. {articolo}")

        # NormaVisitata ha solo .urn, l'URL viene recuperato dopo fetch
        result = UnifiedIngestionResult(
            article_urn=nv.urn,
            article_url="",  # Sarà aggiornato dopo fetch
        )

        try:
            # 1. Fetch from Normattiva
            article_text, article_url = await self._normattiva_scraper.get_document(nv)
            result.article_url = article_url

            # 2. Fetch Brocardi enrichment (optional)
            brocardi_info = None
            if include_brocardi:
                try:
                    # get_info returns (position, info_dict, brocardi_url)
                    position, info_dict, brocardi_url = await self._brocardi_scraper.get_info(nv)
                    if info_dict:
                        brocardi_info = info_dict
                        result.brocardi_enriched = True
                except Exception as e:
                    logger.warning(f"Brocardi fetch failed: {e}")
                    result.errors.append(f"Brocardi: {str(e)[:100]}")

            # 3. Build VisualexArticle for pipeline
            metadata = NormaMetadata(
                tipo_atto=tipo_atto,
                data=norma.data,
                numero_atto=norma.numero_atto,
                numero_articolo=articolo_norm,
            )

            visualex_article = VisualexArticle(
                metadata=metadata,
                article_text=article_text,
                url=article_url,
                brocardi_info=brocardi_info,
            )

            # 4. Run ingestion pipeline (graph + chunks)
            cached_tree = norm_tree or await self._get_cached_norm_tree(tipo_atto)
            ingestion_result = await self._ingestion_pipeline.ingest_article(
                article=visualex_article,
                create_graph_nodes=True,
                norm_tree=cached_tree,
            )

            result.nodes_created = ingestion_result.nodes_created
            result.relations_created = ingestion_result.relations_created
            result.chunks_created = len(ingestion_result.chunks)

            # 5. Insert bridge table mappings (optional)
            if include_bridge and self._bridge_builder and ingestion_result.bridge_mappings:
                try:
                    inserted = await self._bridge_builder.insert_mappings(
                        ingestion_result.bridge_mappings
                    )
                    result.bridge_mappings_inserted = inserted
                except Exception as e:
                    logger.warning(f"Bridge table insert failed: {e}")
                    result.errors.append(f"Bridge: {str(e)[:100]}")

            # 6. Generate and store embeddings (optional)
            if include_embeddings and self._qdrant and self._embedding_service:
                try:
                    upserted = await self._upsert_embeddings(
                        article_text=article_text,
                        article_urn=ingestion_result.article_urn,
                        chunks=ingestion_result.chunks,
                        metadata=metadata,
                    )
                    result.embeddings_upserted = upserted
                except Exception as e:
                    logger.warning(f"Embedding upsert failed: {e}")
                    result.errors.append(f"Embeddings: {str(e)[:100]}")

            # 7. Apply multivigenza (optional)
            if include_multivigenza:
                try:
                    mv_result = await self._multivigenza_pipeline.ingest_with_history(
                        nv,
                        fetch_all_versions=False,
                        create_modifying_acts=True,
                    )
                    result.modifiche_count = len(mv_result.storia.modifiche) if mv_result.storia else 0
                    result.atti_modificanti_created = mv_result.atti_modificanti_creati
                    result.multivigenza_relations = mv_result.relazioni_create
                except Exception as e:
                    logger.warning(f"Multivigenza failed: {e}")
                    result.errors.append(f"Multivigenza: {str(e)[:100]}")

            logger.info(f"Ingestion complete: {result.summary()}")

        except Exception as e:
            logger.error(f"Ingestion failed: {e}", exc_info=True)
            result.errors.append(f"Fatal: {str(e)}")

        return result

    async def _upsert_embeddings(
        self,
        article_text: str,
        article_urn: str,
        chunks: List[Any],  # Chunk objects
        metadata: NormaMetadata,
    ) -> int:
        """
        Generate and upsert embeddings for article chunks.

        Returns number of embeddings upserted.
        """
        if not self._qdrant or not self._embedding_service:
            return 0

        # For simplicity, embed the full article text
        # In production, you'd embed each chunk separately
        embedding = await self._embedding_service.encode_document_async(article_text)

        # Create point for Qdrant
        point = PointStruct(
            id=hash(article_urn) % (2**63),  # Convert URN to integer ID
            vector=embedding,
            payload={
                "urn": article_urn,
                "tipo_atto": metadata.tipo_atto,
                "numero_articolo": metadata.numero_articolo,
                "text": article_text[:1000],  # Truncate for payload
            },
        )

        self._qdrant.upsert(
            collection_name=self.config.qdrant_collection,
            points=[point],
        )

        return 1

    async def _get_cached_norm_tree(self, tipo_atto: str) -> Optional[NormTree]:
        """Get cached NormTree for act type, or fetch and cache it."""
        if tipo_atto not in self._norm_trees:
            try:
                norma = Norma(tipo_atto=tipo_atto, data=None, numero_atto=None)
                tree, status = await get_hierarchical_tree(norma.urn)
                if status == 200 and isinstance(tree, NormTree):
                    self._norm_trees[tipo_atto] = tree
            except Exception as e:
                logger.warning(f"Could not fetch NormTree for {tipo_atto}: {e}")
                return None

        return self._norm_trees.get(tipo_atto)

    async def search(
        self,
        query: str,
        top_k: int = 5,
        include_graph_context: bool = True,
    ) -> List[Dict[str, Any]]:
        """
        Search the knowledge graph with hybrid retrieval.

        Uses semantic search (embeddings) combined with graph context
        for improved legal information retrieval.

        Args:
            query: Natural language query
            top_k: Number of results to return
            include_graph_context: Whether to expand results with graph neighbors

        Returns:
            List of search results with scores and context
        """
        if not self._connected:
            raise RuntimeError("Not connected. Call connect() first.")

        if not self._qdrant or not self._embedding_service:
            raise RuntimeError("Search requires Qdrant and EmbeddingService")

        # Encode query
        query_embedding = await self._embedding_service.encode_query_async(query)

        # Search Qdrant
        results = self._qdrant.search(
            collection_name=self.config.qdrant_collection,
            query_vector=query_embedding,
            limit=top_k,
        )

        # Format results
        formatted = []
        for hit in results:
            result = {
                "urn": hit.payload.get("urn"),
                "tipo_atto": hit.payload.get("tipo_atto"),
                "numero_articolo": hit.payload.get("numero_articolo"),
                "text": hit.payload.get("text"),
                "score": hit.score,
            }

            # Optionally add graph context
            if include_graph_context and self._falkordb:
                try:
                    context = await self._get_graph_context(hit.payload.get("urn"))
                    result["graph_context"] = context
                except Exception as e:
                    logger.warning(f"Could not fetch graph context: {e}")

            formatted.append(result)

        return formatted

    async def _get_graph_context(self, urn: str) -> Dict[str, Any]:
        """Fetch graph context for a URN (neighbors, hierarchy)."""
        if not self._falkordb or not urn:
            return {}

        # Get parent and related nodes
        result = await self._falkordb.query(
            """
            MATCH (n:Norma {URN: $urn})
            OPTIONAL MATCH (parent)-[:contiene]->(n)
            OPTIONAL MATCH (n)-[:contiene]->(child)
            OPTIONAL MATCH (modifier)-[:modifica|abroga|sostituisce|inserisce]->(n)
            RETURN
                parent.URN as parent_urn,
                parent.titolo as parent_title,
                collect(DISTINCT child.numero_articolo) as children,
                collect(DISTINCT modifier.estremi) as modifiers
            """,
            {"urn": urn}
        )

        if result.result_set:
            row = result.result_set[0]
            return {
                "parent_urn": row[0],
                "parent_title": row[1],
                "children": row[2] or [],
                "modifiers": row[3] or [],
            }

        return {}

    @property
    def is_connected(self) -> bool:
        """Check if connected to backends."""
        return self._connected

    @property
    def falkordb(self) -> Optional[FalkorDBClient]:
        """Access FalkorDB client directly."""
        return self._falkordb

    @property
    def qdrant(self) -> Optional[Any]:
        """Access Qdrant client directly."""
        return self._qdrant

    @property
    def bridge_table(self) -> Optional[BridgeTable]:
        """Access Bridge Table directly."""
        return self._bridge_table


__all__ = [
    "LegalKnowledgeGraph",
    "MerltConfig",
    "UnifiedIngestionResult",
]
