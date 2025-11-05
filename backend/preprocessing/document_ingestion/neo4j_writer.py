"""
Neo4j Writer
============

Writes extracted knowledge to Neo4j Knowledge Graph.

Features:
- Creates nodes according to KG schema
- Creates typed relationships
- Adds provenance metadata
- Batch transactions for performance
- Duplicate detection (MERGE vs CREATE)
"""

import logging
from typing import List, Dict, Any
from neo4j import AsyncDriver

from .models import (
    ExtractedEntity,
    ExtractedRelationship,
    ExtractionResult,
    NodeType,
)

logger = logging.getLogger(__name__)


class Neo4jWriter:
    """
    Writes extracted entities and relationships to Neo4j.
    """

    def __init__(
        self,
        neo4j_driver: AsyncDriver,
        batch_size: int = 100,
        duplicate_strategy: str = "merge",
    ):
        """
        Initialize Neo4j writer.

        Args:
            neo4j_driver: Async Neo4j driver
            batch_size: Number of nodes per transaction
            duplicate_strategy: "merge" (default), "skip", or "error"
        """
        self.neo4j_driver = neo4j_driver
        self.batch_size = batch_size
        self.duplicate_strategy = duplicate_strategy
        self.logger = logger

    async def write_extraction_results(
        self,
        extraction_results: List[ExtractionResult],
        dry_run: bool = False
    ) -> Dict[str, Any]:
        """
        Write extraction results to Neo4j.

        Args:
            extraction_results: List of extraction results
            dry_run: If True, don't actually write to Neo4j

        Returns:
            Statistics dict with counts
        """
        stats = {
            "nodes_created": 0,
            "relationships_created": 0,
            "nodes_skipped": 0,
            "errors": [],
        }

        if dry_run:
            self.logger.info("DRY RUN - Not writing to Neo4j")
            # Just count what would be written
            for result in extraction_results:
                stats["nodes_created"] += len(result.entities)
                stats["relationships_created"] += len(result.relationships)
            return stats

        # Collect all entities and relationships
        all_entities = []
        all_relationships = []

        for result in extraction_results:
            all_entities.extend(result.entities)
            all_relationships.extend(result.relationships)

        self.logger.info(
            f"Writing {len(all_entities)} entities and "
            f"{len(all_relationships)} relationships to Neo4j"
        )

        # Write entities in batches
        for i in range(0, len(all_entities), self.batch_size):
            batch = all_entities[i:i + self.batch_size]
            batch_stats = await self._write_entities_batch(batch)
            stats["nodes_created"] += batch_stats["created"]
            stats["nodes_skipped"] += batch_stats["skipped"]
            stats["errors"].extend(batch_stats["errors"])

        # Write relationships
        rel_stats = await self._write_relationships(all_relationships)
        stats["relationships_created"] = rel_stats["created"]
        stats["errors"].extend(rel_stats["errors"])

        self.logger.info(
            f"Write complete: {stats['nodes_created']} nodes, "
            f"{stats['relationships_created']} relationships"
        )

        return stats

    async def _write_entities_batch(
        self,
        entities: List[ExtractedEntity]
    ) -> Dict[str, Any]:
        """Write a batch of entities to Neo4j."""
        stats = {"created": 0, "skipped": 0, "errors": []}

        async with self.neo4j_driver.session() as session:
            tx = await session.begin_transaction()
            try:
                for entity in entities:
                    try:
                        created = await self._write_entity(tx, entity)
                        if created:
                            stats["created"] += 1
                        else:
                            stats["skipped"] += 1
                    except Exception as e:
                        error_msg = f"Error writing entity {entity.label}: {e}"
                        self.logger.error(error_msg)
                        stats["errors"].append(error_msg)

                await tx.commit()
            except Exception as e:
                await tx.rollback()
                raise

        return stats

    async def _write_entity(self, tx, entity: ExtractedEntity) -> bool:
        """
        Write a single entity to Neo4j.

        Returns:
            True if created, False if skipped
        """
        # Get Cypher label from node type
        label = self._get_neo4j_label(entity.type)

        # Build properties dict
        properties = {
            "node_id": entity.entity_id,
            "label": entity.label,
            **entity.properties,
            # Provenance metadata
            "provenance_file": entity.provenance.source_file,
            "provenance_page": entity.provenance.page_number,
            "provenance_paragraph": entity.provenance.paragraph_index,
            "extraction_timestamp": entity.provenance.extraction_timestamp.isoformat(),
            "confidence": entity.confidence,
        }

        # Choose MERGE or CREATE based on strategy
        if self.duplicate_strategy == "merge":
            # MERGE on node_id to avoid duplicates
            query = f"""
            MERGE (n:{label} {{node_id: $node_id}})
            SET n += $properties
            RETURN n.node_id as id, 'created' as action
            """
        else:  # CREATE (will fail if duplicate exists with unique constraint)
            query = f"""
            CREATE (n:{label})
            SET n = $properties
            RETURN n.node_id as id, 'created' as action
            """

        result = await tx.run(query, node_id=entity.entity_id, properties=properties)
        record = await result.single()

        return record is not None

    async def _write_relationships(
        self,
        relationships: List[ExtractedRelationship]
    ) -> Dict[str, Any]:
        """Write relationships to Neo4j."""
        stats = {"created": 0, "errors": []}

        async with self.neo4j_driver.session() as session:
            for relationship in relationships:
                try:
                    created = await self._write_relationship(session, relationship)
                    if created:
                        stats["created"] += 1
                except Exception as e:
                    error_msg = (
                        f"Error writing relationship "
                        f"{relationship.source_label} -> {relationship.target_label}: {e}"
                    )
                    self.logger.error(error_msg)
                    stats["errors"].append(error_msg)

        return stats

    async def _write_relationship(
        self,
        session,
        relationship: ExtractedRelationship
    ) -> bool:
        """
        Write a single relationship to Neo4j.

        Matches nodes by label (not perfect, but works for initial version).
        """
        rel_type = relationship.type.value

        # MERGE to avoid duplicate relationships
        query = f"""
        MATCH (source {{label: $source_label}})
        MATCH (target {{label: $target_label}})
        MERGE (source)-[r:{rel_type}]->(target)
        SET r += $properties,
            r.confidence = $confidence,
            r.provenance_file = $provenance_file
        RETURN r
        """

        properties = relationship.properties or {}
        properties["created_at"] = "datetime()"

        result = await session.run(
            query,
            source_label=relationship.source_label,
            target_label=relationship.target_label,
            properties=properties,
            confidence=relationship.confidence,
            provenance_file=relationship.provenance.source_file if relationship.provenance else "",
        )

        record = await result.single()
        return record is not None

    def _get_neo4j_label(self, node_type: NodeType) -> str:
        """
        Map NodeType enum to Neo4j node label.

        Converts spaces to underscores and removes special chars.
        """
        # Use the enum value directly (already formatted)
        label = node_type.value

        # Replace spaces with nothing (or underscore if preferred)
        label = label.replace(" ", "")

        return label
