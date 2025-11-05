"""
Neo4j Connection Manager

Centralized singleton for managing Neo4j async driver connections.
Provides connection pooling, health checks, and graceful shutdown.

Usage:
    driver = await Neo4jConnectionManager.get_driver()
    async with driver.session() as session:
        result = await session.run("MATCH (n) RETURN count(n)")
"""

import os
import logging
from typing import Optional
from neo4j import AsyncGraphDatabase, AsyncDriver
from contextlib import asynccontextmanager

logger = logging.getLogger(__name__)


class Neo4jConnectionManager:
    """
    Singleton connection manager for Neo4j.

    Manages a single AsyncDriver instance shared across the application,
    with configurable connection pooling and automatic health checks.
    """

    _instance: Optional['Neo4jConnectionManager'] = None
    _driver: Optional[AsyncDriver] = None
    _is_initialized: bool = False

    def __new__(cls):
        if cls._instance is None:
            cls._instance = super().__new__(cls)
        return cls._instance

    @classmethod
    async def initialize(
        cls,
        uri: Optional[str] = None,
        username: Optional[str] = None,
        password: Optional[str] = None,
        database: Optional[str] = None,
        max_connection_pool_size: int = 50,
        **kwargs
    ) -> AsyncDriver:
        """
        Initialize Neo4j driver with connection pooling.

        Args:
            uri: Neo4j connection URI (default: from NEO4J_URI env var)
            username: Neo4j username (default: from NEO4J_USER env var)
            password: Neo4j password (default: from NEO4J_PASSWORD env var)
            database: Database name (default: from NEO4J_DATABASE env var or "neo4j")
            max_connection_pool_size: Maximum connections in pool
            **kwargs: Additional driver configuration options

        Returns:
            AsyncDriver instance

        Raises:
            ValueError: If password is not provided
        """
        if cls._is_initialized and cls._driver is not None:
            logger.info("Neo4j driver already initialized, returning existing driver")
            return cls._driver

        # Load configuration from environment variables
        uri = uri or os.getenv("NEO4J_URI", "bolt://localhost:7687")
        username = username or os.getenv("NEO4J_USER", "neo4j")
        password = password or os.getenv("NEO4J_PASSWORD")
        database = database or os.getenv("NEO4J_DATABASE", "neo4j")

        if not password:
            raise ValueError(
                "Neo4j password is required. "
                "Provide via NEO4J_PASSWORD environment variable or password parameter."
            )

        logger.info(f"Initializing Neo4j driver: {uri} (database: {database})")

        try:
            cls._driver = AsyncGraphDatabase.driver(
                uri,
                auth=(username, password),
                max_connection_pool_size=max_connection_pool_size,
                connection_timeout=30,  # 30 seconds
                **kwargs
            )

            # Verify connectivity
            await cls._driver.verify_connectivity()

            cls._is_initialized = True
            logger.info("Neo4j driver initialized successfully")

            return cls._driver

        except Exception as e:
            logger.error(f"Failed to initialize Neo4j driver: {str(e)}", exc_info=True)
            cls._driver = None
            cls._is_initialized = False
            raise

    @classmethod
    async def get_driver(cls) -> AsyncDriver:
        """
        Get the Neo4j driver instance.

        Returns:
            AsyncDriver instance

        Raises:
            RuntimeError: If driver not initialized
        """
        if not cls._is_initialized or cls._driver is None:
            raise RuntimeError(
                "Neo4j driver not initialized. "
                "Call Neo4jConnectionManager.initialize() first."
            )

        return cls._driver

    @classmethod
    async def close(cls):
        """
        Close the Neo4j driver and cleanup resources.

        Should be called during application shutdown.
        """
        if cls._driver is not None:
            logger.info("Closing Neo4j driver...")
            await cls._driver.close()
            cls._driver = None
            cls._is_initialized = False
            logger.info("Neo4j driver closed")
        else:
            logger.debug("Neo4j driver not initialized, nothing to close")

    @classmethod
    async def health_check(cls) -> dict:
        """
        Perform health check on Neo4j connection.

        Returns:
            dict with status, message, and optional details
        """
        if not cls._is_initialized or cls._driver is None:
            return {
                "status": "unhealthy",
                "message": "Neo4j driver not initialized",
                "details": None
            }

        try:
            # Try to verify connectivity
            await cls._driver.verify_connectivity()

            # Run a simple query to verify database access
            async with cls._driver.session() as session:
                result = await session.run("RETURN 1 as test")
                record = await result.single()

                if record and record["test"] == 1:
                    return {
                        "status": "healthy",
                        "message": "Neo4j connection is healthy",
                        "details": {
                            "uri": cls._driver._uri,
                            "pool_size": cls._driver._pool.size if hasattr(cls._driver, '_pool') else "unknown"
                        }
                    }
                else:
                    return {
                        "status": "unhealthy",
                        "message": "Neo4j query returned unexpected result",
                        "details": None
                    }

        except Exception as e:
            logger.error(f"Neo4j health check failed: {str(e)}", exc_info=True)
            return {
                "status": "unhealthy",
                "message": f"Neo4j health check failed: {str(e)}",
                "details": {"error": str(e)}
            }

    @classmethod
    @asynccontextmanager
    async def session(cls, database: Optional[str] = None):
        """
        Context manager for Neo4j sessions.

        Usage:
            async with Neo4jConnectionManager.session() as session:
                result = await session.run("MATCH (n) RETURN n")

        Args:
            database: Optional database name override

        Yields:
            AsyncSession
        """
        driver = await cls.get_driver()
        async with driver.session(database=database) as session:
            yield session

    @classmethod
    async def execute_query(cls, query: str, parameters: Optional[dict] = None, database: Optional[str] = None):
        """
        Execute a Cypher query and return results.

        Convenience method for simple queries.

        Args:
            query: Cypher query string
            parameters: Query parameters dict
            database: Optional database name

        Returns:
            List of record dictionaries
        """
        async with cls.session(database=database) as session:
            result = await session.run(query, parameters or {})
            records = [record.data() async for record in result]
            return records

    @classmethod
    async def get_database_info(cls) -> dict:
        """
        Get Neo4j database information.

        Returns:
            dict with database metadata
        """
        try:
            async with cls.session() as session:
                # Get database name
                db_result = await session.run("CALL db.info()")
                db_info = await db_result.single()

                # Get node count
                count_result = await session.run("MATCH (n) RETURN count(n) as node_count")
                count_record = await count_result.single()

                # Get relationship count
                rel_count_result = await session.run("MATCH ()-[r]->() RETURN count(r) as rel_count")
                rel_count_record = await rel_count_result.single()

                return {
                    "database_name": db_info.get("name") if db_info else "unknown",
                    "node_count": count_record["node_count"] if count_record else 0,
                    "relationship_count": rel_count_record["rel_count"] if rel_count_record else 0,
                }

        except Exception as e:
            logger.error(f"Failed to get database info: {str(e)}", exc_info=True)
            return {
                "database_name": "error",
                "node_count": -1,
                "relationship_count": -1,
                "error": str(e)
            }


# Convenience function for simple usage
async def get_neo4j_driver() -> AsyncDriver:
    """
    Get the initialized Neo4j driver.

    Convenience function wrapping Neo4jConnectionManager.get_driver()

    Returns:
        AsyncDriver instance
    """
    return await Neo4jConnectionManager.get_driver()
