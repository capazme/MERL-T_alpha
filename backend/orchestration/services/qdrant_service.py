"""
Qdrant Service for Vector Database Management

This service provides utilities for managing Qdrant collections for legal document retrieval.

Key Features:
- Collection initialization with legal corpus schema
- Payload index creation for filtered search
- Idempotent operations (safe to run multiple times)
- Comprehensive metadata structure for legal documents

Collection Schema:
- Vector size: 1024 (E5-large embeddings)
- Distance metric: Cosine similarity
- Payload fields: document_type, temporal_metadata, classification, authority_metadata, entities_extracted

Reference: docs/02-methodology/vector-database.md
"""

import logging
import os
from typing import Optional, Dict, Any, List
from datetime import datetime

try:
    from qdrant_client import QdrantClient
    from qdrant_client.models import (
        Distance,
        VectorParams,
        PayloadSchemaType,
        PointStruct,
        CollectionInfo
    )
except ImportError:
    raise ImportError(
        "qdrant-client is required for QdrantService. "
        "Install with: pip install qdrant-client"
    )

logger = logging.getLogger(__name__)


class QdrantService:
    """
    Service for managing Qdrant vector database collections.

    Usage:
        # Initialize service
        service = QdrantService(
            host="localhost",
            port=6333,
            collection_name="legal_corpus"
        )

        # Create collection (idempotent)
        service.initialize_collection()

        # Insert documents
        service.insert_documents([
            {
                "id": "art_1321_cc",
                "vector": [0.1, 0.2, ...],  # 1024 dimensions
                "payload": {
                    "text": "Art. 1321 c.c. - Il contratto è...",
                    "document_type": "norm",
                    ...
                }
            }
        ])
    """

    def __init__(
        self,
        host: Optional[str] = None,
        port: Optional[int] = None,
        grpc_port: Optional[int] = None,
        collection_name: Optional[str] = None,
        api_key: Optional[str] = None,
        timeout: int = 30
    ):
        """
        Initialize QdrantService.

        Args:
            host: Qdrant host (default: from QDRANT_HOST env var or 'localhost')
            port: Qdrant HTTP port (default: from QDRANT_PORT env var or 6333)
            grpc_port: Qdrant gRPC port (default: from QDRANT_GRPC_PORT env var or 6334)
            collection_name: Collection name (default: from QDRANT_COLLECTION_NAME env var or 'legal_corpus')
            api_key: Qdrant API key (optional, for cloud deployment)
            timeout: Request timeout in seconds
        """
        self.host = host or os.getenv("QDRANT_HOST", "localhost")
        self.port = int(os.getenv("QDRANT_PORT", str(port or 6333)))
        self.grpc_port = int(os.getenv("QDRANT_GRPC_PORT", str(grpc_port or 6334)))
        self.collection_name = collection_name or os.getenv("QDRANT_COLLECTION_NAME", "legal_corpus")
        self.api_key = api_key or os.getenv("QDRANT_API_KEY")
        self.timeout = timeout

        # Initialize Qdrant client
        self.client = self._create_client()

        logger.info(
            f"QdrantService initialized",
            extra={
                "host": self.host,
                "port": self.port,
                "collection": self.collection_name
            }
        )

    def _create_client(self) -> QdrantClient:
        """Create Qdrant client with configuration."""
        try:
            client = QdrantClient(
                host=self.host,
                port=self.port,
                grpc_port=self.grpc_port,
                api_key=self.api_key,
                timeout=self.timeout
            )
            logger.info(f"Connected to Qdrant at {self.host}:{self.port}")
            return client
        except Exception as e:
            logger.error(f"Failed to connect to Qdrant: {e}", exc_info=True)
            raise

    def collection_exists(self) -> bool:
        """
        Check if collection exists.

        Returns:
            True if collection exists, False otherwise
        """
        try:
            collections = self.client.get_collections().collections
            return any(c.name == self.collection_name for c in collections)
        except Exception as e:
            logger.error(f"Error checking collection existence: {e}")
            return False

    def initialize_collection(
        self,
        vector_size: int = 1024,
        distance: Distance = Distance.COSINE,
        recreate: bool = False
    ) -> bool:
        """
        Initialize Qdrant collection with legal corpus schema.

        This operation is idempotent - safe to run multiple times.
        If collection exists and recreate=False, does nothing.

        Args:
            vector_size: Embedding vector size (default: 1024 for E5-large)
            distance: Distance metric (default: COSINE)
            recreate: If True, delete and recreate collection if it exists

        Returns:
            True if collection was created/recreated, False if already exists

        Schema:
            - Vectors: 1024 dimensions, cosine distance
            - Payload indexes for filtering:
                - document_type (keyword): "norm" | "jurisprudence" | "doctrine"
                - temporal_metadata.is_current (bool): Current version flag
                - classification.legal_area (keyword): Civil, criminal, etc.
                - classification.complexity_level (integer): 1-5 scale
        """
        try:
            exists = self.collection_exists()

            if exists:
                if recreate:
                    logger.info(f"Recreating collection: {self.collection_name}")
                    self.client.delete_collection(self.collection_name)
                else:
                    logger.info(f"Collection '{self.collection_name}' already exists")
                    return False

            # Create collection
            logger.info(f"Creating collection: {self.collection_name}")
            self.client.create_collection(
                collection_name=self.collection_name,
                vectors_config=VectorParams(
                    size=vector_size,
                    distance=distance
                )
            )

            # Create payload indexes for efficient filtering
            self._create_payload_indexes()

            logger.info(f"Collection '{self.collection_name}' created successfully")
            return True

        except Exception as e:
            logger.error(f"Error initializing collection: {e}", exc_info=True)
            raise

    def _create_payload_indexes(self):
        """
        Create payload indexes for filtered search.

        Indexes created:
        - document_type: Keyword index for filtering by document type
        - temporal_metadata.is_current: Boolean index for current versions
        - classification.legal_area: Keyword index for legal domain
        - classification.complexity_level: Integer index for complexity
        """
        indexes = [
            ("document_type", PayloadSchemaType.KEYWORD),
            ("temporal_metadata.is_current", PayloadSchemaType.BOOL),
            ("classification.legal_area", PayloadSchemaType.KEYWORD),
            ("classification.complexity_level", PayloadSchemaType.INTEGER),
        ]

        for field_name, field_schema in indexes:
            try:
                self.client.create_payload_index(
                    collection_name=self.collection_name,
                    field_name=field_name,
                    field_schema=field_schema
                )
                logger.info(f"Created payload index: {field_name}")
            except Exception as e:
                logger.warning(f"Could not create index for {field_name}: {e}")

    def get_collection_info(self) -> Optional[CollectionInfo]:
        """
        Get collection information.

        Returns:
            CollectionInfo object or None if collection doesn't exist
        """
        try:
            if not self.collection_exists():
                return None
            return self.client.get_collection(self.collection_name)
        except Exception as e:
            logger.error(f"Error getting collection info: {e}")
            return None

    def insert_documents(
        self,
        documents: List[Dict[str, Any]],
        batch_size: int = 100
    ) -> int:
        """
        Insert documents into collection.

        Args:
            documents: List of documents with 'id', 'vector', and 'payload' keys
            batch_size: Batch size for bulk insert

        Returns:
            Number of documents inserted

        Example document:
            {
                "id": "art_1321_cc",
                "vector": [0.1, 0.2, ..., 0.9],  # 1024 floats
                "payload": {
                    "text": "Art. 1321 c.c. - Il contratto è...",
                    "document_type": "norm",
                    "temporal_metadata": {
                        "is_current": true,
                        "date_effective": "1942-03-16",
                        "date_end": null
                    },
                    "classification": {
                        "legal_area": "civil",
                        "legal_domain_tags": ["contract_law"],
                        "complexity_level": 2
                    },
                    "authority_metadata": {
                        "source_type": "normattiva",
                        "hierarchical_level": "codice",
                        "authority_score": 1.0
                    },
                    "entities_extracted": {
                        "norm_references": [],
                        "legal_concepts": ["contratto", "accordo"]
                    }
                }
            }
        """
        if not documents:
            return 0

        try:
            points = [
                PointStruct(
                    id=doc["id"],
                    vector=doc["vector"],
                    payload=doc["payload"]
                )
                for doc in documents
            ]

            # Insert in batches
            total_inserted = 0
            for i in range(0, len(points), batch_size):
                batch = points[i:i+batch_size]
                self.client.upsert(
                    collection_name=self.collection_name,
                    points=batch
                )
                total_inserted += len(batch)
                logger.info(f"Inserted batch: {total_inserted}/{len(points)} documents")

            logger.info(f"Successfully inserted {total_inserted} documents")
            return total_inserted

        except Exception as e:
            logger.error(f"Error inserting documents: {e}", exc_info=True)
            raise

    def delete_collection(self) -> bool:
        """
        Delete collection.

        Returns:
            True if collection was deleted, False if it didn't exist
        """
        try:
            if not self.collection_exists():
                logger.info(f"Collection '{self.collection_name}' does not exist")
                return False

            self.client.delete_collection(self.collection_name)
            logger.info(f"Deleted collection: {self.collection_name}")
            return True

        except Exception as e:
            logger.error(f"Error deleting collection: {e}", exc_info=True)
            raise

    def get_collection_stats(self) -> Dict[str, Any]:
        """
        Get collection statistics.

        Returns:
            Dictionary with collection stats (points_count, vectors_count, etc.)
        """
        try:
            info = self.get_collection_info()
            if info is None:
                return {"error": "Collection does not exist"}

            return {
                "collection_name": self.collection_name,
                "points_count": info.points_count,
                "vectors_count": info.vectors_count,
                "indexed_vectors_count": info.indexed_vectors_count,
                "status": info.status.value
            }

        except Exception as e:
            logger.error(f"Error getting collection stats: {e}")
            return {"error": str(e)}

    def __repr__(self) -> str:
        """String representation."""
        return (
            f"QdrantService("
            f"host={self.host}:{self.port}, "
            f"collection={self.collection_name})"
        )
