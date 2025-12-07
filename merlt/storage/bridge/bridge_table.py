"""
Bridge Table Service
=====================

Service class for managing vector-to-graph mappings.

Features:
- Insert/update/delete mappings
- Query by chunk_id or graph_node_urn
- Batch operations for ingestion
- Async/await for performance
"""

import logging
from typing import List, Optional, Dict, Any
from uuid import UUID
from dataclasses import dataclass

from sqlalchemy import select, delete, update
from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine, async_sessionmaker
from sqlalchemy.orm import selectinload

from .models import BridgeTableEntry, Base

logger = logging.getLogger(__name__)


@dataclass
class BridgeTableConfig:
    """Configuration for Bridge Table connection."""
    host: str = "localhost"
    port: int = 5433  # Dev container port (avoiding conflict with native PostgreSQL)
    database: str = "rlcf_dev"
    user: str = "dev"
    password: str = "devpassword"
    pool_size: int = 10
    max_overflow: int = 20

    def get_connection_string(self) -> str:
        """Get async PostgreSQL connection string."""
        return f"postgresql+asyncpg://{self.user}:{self.password}@{self.host}:{self.port}/{self.database}"


class BridgeTable:
    """
    Service for managing chunk-to-graph mappings.

    Example:
        bridge = BridgeTable(config)
        await bridge.connect()

        # Add mapping
        await bridge.add_mapping(
            chunk_id=uuid4(),
            graph_node_urn="https://www.normattiva.it/...",
            node_type="Norma",
            relation_type="contained_in",
            confidence=1.0
        )

        # Query by chunk
        nodes = await bridge.get_nodes_for_chunk(chunk_id)

        await bridge.close()
    """

    def __init__(self, config: Optional[BridgeTableConfig] = None):
        self.config = config or BridgeTableConfig()
        self._engine = None
        self._session_maker = None
        self._connected = False

        logger.info(
            f"BridgeTable initialized - "
            f"host={self.config.host}:{self.config.port}, "
            f"database={self.config.database}"
        )

    async def connect(self):
        """Establish connection pool to PostgreSQL."""
        if self._connected:
            logger.debug("Already connected to PostgreSQL")
            return

        connection_string = self.config.get_connection_string()
        self._engine = create_async_engine(
            connection_string,
            pool_size=self.config.pool_size,
            max_overflow=self.config.max_overflow,
            echo=False  # Set to True for SQL debugging
        )

        self._session_maker = async_sessionmaker(
            self._engine,
            class_=AsyncSession,
            expire_on_commit=False
        )

        self._connected = True
        logger.info(f"Connected to PostgreSQL at {self.config.host}:{self.config.port}")

    async def close(self):
        """Close connection pool."""
        if not self._connected:
            return

        await self._engine.dispose()
        self._connected = False
        logger.info("Disconnected from PostgreSQL")

    async def add_mapping(
        self,
        chunk_id: UUID,
        graph_node_urn: str,
        node_type: str,
        relation_type: Optional[str] = None,
        confidence: Optional[float] = None,
        chunk_text: Optional[str] = None,
        source: Optional[str] = None,
        metadata: Optional[Dict[str, Any]] = None
    ) -> int:
        """
        Add a single chunk-to-node mapping.

        Args:
            chunk_id: UUID of the text chunk in Qdrant
            graph_node_urn: URN of the graph node in FalkorDB
            node_type: Type of node (Norma, ConcettoGiuridico, etc.)
            relation_type: Semantic relation (contained_in, references, etc.)
            confidence: Confidence score [0-1]
            chunk_text: Optional cached text for debugging
            source: Data source (visualex, manual, etc.)
            metadata: Additional metadata as JSON

        Returns:
            ID of the created entry

        Raises:
            IntegrityError: If mapping already exists (unique constraint violation)
        """
        if not self._connected:
            raise RuntimeError("Not connected to PostgreSQL. Call connect() first.")

        async with self._session_maker() as session:
            entry = BridgeTableEntry(
                chunk_id=chunk_id,
                graph_node_urn=graph_node_urn,
                node_type=node_type,
                relation_type=relation_type,
                confidence=confidence,
                chunk_text=chunk_text,
                source=source,
                extra_metadata=metadata
            )

            session.add(entry)
            await session.commit()
            await session.refresh(entry)

            logger.debug(
                f"Added mapping: chunk_id={chunk_id} -> "
                f"node_urn={graph_node_urn[:50]}..."
            )

            return entry.id

    async def add_mappings_batch(
        self,
        mappings: List[Dict[str, Any]]
    ) -> int:
        """
        Add multiple mappings in a batch (faster for ingestion).

        Args:
            mappings: List of mapping dicts with keys:
                - chunk_id (required)
                - graph_node_urn (required)
                - node_type (required)
                - relation_type (optional)
                - confidence (optional)
                - chunk_text (optional)
                - source (optional)
                - metadata (optional)

        Returns:
            Number of mappings inserted

        Example:
            await bridge.add_mappings_batch([
                {
                    "chunk_id": uuid4(),
                    "graph_node_urn": "urn:...",
                    "node_type": "Norma",
                    "confidence": 1.0
                },
                ...
            ])
        """
        if not self._connected:
            raise RuntimeError("Not connected to PostgreSQL. Call connect() first.")

        if not mappings:
            return 0

        async with self._session_maker() as session:
            entries = [
                BridgeTableEntry(**mapping)
                for mapping in mappings
            ]

            session.add_all(entries)
            await session.commit()

            logger.info(f"Batch inserted {len(entries)} mappings")
            return len(entries)

    async def get_nodes_for_chunk(
        self,
        chunk_id: UUID,
        node_type: Optional[str] = None
    ) -> List[Dict[str, Any]]:
        """
        Get all graph nodes linked to a chunk.

        Args:
            chunk_id: UUID of the chunk
            node_type: Optional filter by node type

        Returns:
            List of node dicts with fields:
                - graph_node_urn
                - node_type
                - relation_type
                - confidence
                - metadata
        """
        if not self._connected:
            raise RuntimeError("Not connected to PostgreSQL. Call connect() first.")

        async with self._session_maker() as session:
            query = select(BridgeTableEntry).where(
                BridgeTableEntry.chunk_id == chunk_id
            )

            if node_type:
                query = query.where(BridgeTableEntry.node_type == node_type)

            result = await session.execute(query)
            entries = result.scalars().all()

            logger.debug(f"Found {len(entries)} nodes for chunk_id={chunk_id}")

            return [
                {
                    "graph_node_urn": entry.graph_node_urn,
                    "node_type": entry.node_type,
                    "relation_type": entry.relation_type,
                    "confidence": entry.confidence,
                    "metadata": entry.extra_metadata
                }
                for entry in entries
            ]

    async def get_chunks_for_node(
        self,
        graph_node_urn: str
    ) -> List[Dict[str, Any]]:
        """
        Get all chunks linked to a graph node.

        Args:
            graph_node_urn: URN of the graph node

        Returns:
            List of chunk dicts with fields:
                - chunk_id
                - chunk_text
                - relation_type
                - confidence
        """
        if not self._connected:
            raise RuntimeError("Not connected to PostgreSQL. Call connect() first.")

        async with self._session_maker() as session:
            query = select(BridgeTableEntry).where(
                BridgeTableEntry.graph_node_urn == graph_node_urn
            )

            result = await session.execute(query)
            entries = result.scalars().all()

            logger.debug(f"Found {len(entries)} chunks for node_urn={graph_node_urn[:50]}...")

            return [
                {
                    "chunk_id": str(entry.chunk_id),
                    "chunk_text": entry.chunk_text,
                    "relation_type": entry.relation_type,
                    "confidence": entry.confidence
                }
                for entry in entries
            ]

    async def delete_mappings_for_chunk(self, chunk_id: UUID) -> int:
        """
        Delete all mappings for a chunk.

        Args:
            chunk_id: UUID of the chunk

        Returns:
            Number of mappings deleted
        """
        if not self._connected:
            raise RuntimeError("Not connected to PostgreSQL. Call connect() first.")

        async with self._session_maker() as session:
            stmt = delete(BridgeTableEntry).where(
                BridgeTableEntry.chunk_id == chunk_id
            )

            result = await session.execute(stmt)
            await session.commit()

            count = result.rowcount
            logger.debug(f"Deleted {count} mappings for chunk_id={chunk_id}")
            return count

    async def health_check(self) -> bool:
        """
        Check if PostgreSQL connection is healthy.

        Returns:
            True if healthy, False otherwise
        """
        try:
            if not self._connected:
                await self.connect()

            async with self._session_maker() as session:
                result = await session.execute(select(1))
                result.scalar()

            return True

        except Exception as e:
            logger.error(f"Health check failed: {e}")
            return False
