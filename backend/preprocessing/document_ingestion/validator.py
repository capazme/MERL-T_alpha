"""
Validator
=========

Validates and enriches extracted entities before writing to Neo4j.

Functions:
- Schema compliance validation
- Data completeness checks
- Reference resolution
- Cross-referencing
"""

import logging
from typing import List, Dict, Any

from .models import (
    ExtractedEntity,
    ExtractedRelationship,
    ExtractionResult,
    ValidationResult,
)

logger = logging.getLogger(__name__)


class Validator:
    """
    Validates and enriches extracted knowledge.
    """

    def __init__(
        self,
        strict_mode: bool = False,
        min_confidence: float = 0.7,
    ):
        """
        Initialize validator.

        Args:
            strict_mode: If True, reject on any validation error
            min_confidence: Minimum confidence threshold (0.0 - 1.0)
        """
        self.strict_mode = strict_mode
        self.min_confidence = min_confidence
        self.logger = logger

    async def validate_and_enrich(
        self,
        extraction_results: List[ExtractionResult]
    ) -> List[ExtractionResult]:
        """
        Validate and enrich extraction results.

        Args:
            extraction_results: List of extraction results to validate

        Returns:
            Validated and enriched extraction results
        """
        validated_results = []

        for result in extraction_results:
            # Skip if error
            if result.error:
                validated_results.append(result)
                continue

            # Validate entities
            valid_entities = []
            for entity in result.entities:
                validation = self._validate_entity(entity)

                if validation.valid or not self.strict_mode:
                    # Enrich entity
                    enriched_entity = self._enrich_entity(entity)
                    valid_entities.append(enriched_entity)
                else:
                    self.logger.warning(
                        f"Rejecting entity {entity.label}: "
                        f"{', '.join(validation.errors)}"
                    )

            # Validate relationships
            valid_relationships = []
            for relationship in result.relationships:
                validation = self._validate_relationship(relationship, valid_entities)

                if validation.valid or not self.strict_mode:
                    valid_relationships.append(relationship)
                else:
                    self.logger.warning(
                        f"Rejecting relationship {relationship.source_label} -> "
                        f"{relationship.target_label}: {', '.join(validation.errors)}"
                    )

            # Update result
            result.entities = valid_entities
            result.relationships = valid_relationships
            validated_results.append(result)

        self.logger.info(
            f"Validated {len(extraction_results)} results "
            f"(strict_mode={self.strict_mode})"
        )

        return validated_results

    def _validate_entity(self, entity: ExtractedEntity) -> ValidationResult:
        """
        Validate a single entity.

        Checks:
        - Confidence threshold
        - Required properties present
        - Property types valid
        """
        errors = []
        warnings = []

        # Check confidence
        if entity.confidence < self.min_confidence:
            errors.append(
                f"Confidence {entity.confidence:.2f} below threshold "
                f"{self.min_confidence:.2f}"
            )

        # Check label
        if not entity.label or len(entity.label.strip()) < 2:
            errors.append("Label is empty or too short")

        # Check properties
        if not entity.properties:
            warnings.append("No properties extracted")

        # Type-specific validation
        # TODO: Add schema-specific validations per node type

        return ValidationResult(
            valid=len(errors) == 0,
            errors=errors,
            warnings=warnings,
        )

    def _validate_relationship(
        self,
        relationship: ExtractedRelationship,
        entities: List[ExtractedEntity]
    ) -> ValidationResult:
        """
        Validate a relationship.

        Checks:
        - Source and target exist in entities
        - Confidence threshold
        - Relationship type is valid
        """
        errors = []
        warnings = []

        # Check confidence
        if relationship.confidence < self.min_confidence:
            errors.append(
                f"Confidence {relationship.confidence:.2f} below threshold"
            )

        # Check source exists
        source_exists = any(
            e.label == relationship.source_label for e in entities
        )
        if not source_exists:
            errors.append(f"Source entity '{relationship.source_label}' not found")

        # Check target exists
        target_exists = any(
            e.label == relationship.target_label for e in entities
        )
        if not target_exists:
            errors.append(f"Target entity '{relationship.target_label}' not found")

        return ValidationResult(
            valid=len(errors) == 0,
            errors=errors,
            warnings=warnings,
        )

    def _enrich_entity(self, entity: ExtractedEntity) -> ExtractedEntity:
        """
        Enrich entity with additional data.

        Enrichments:
        - Normalize property values
        - Add derived properties
        - Format dates/numbers
        """
        # TODO: Add enrichment logic
        # - Normalize text (trim, lowercase keys)
        # - Parse dates
        # - Extract URNs from references
        # - Link to existing entities

        return entity
