"""
Intent Type Mapping

Maps between QueryIntentType (query_understanding) and IntentType (intent_classifier/cypher_queries).
Provides bidirectional conversion for pipeline integration.

Background:
- QueryIntentType: Used by query understanding module (6 types)
- IntentType: Used by intent classifier and Cypher queries (4 types + UNKNOWN)

This module provides standardized mapping between the two systems.
"""

import logging
from typing import Dict
from enum import Enum

# Conditional imports to handle circular dependencies
try:
    from backend.preprocessing.query_understanding import QueryIntentType
except ImportError:
    QueryIntentType = None

try:
    from backend.orchestration.intent_classifier import IntentType as OrchestratorIntentType
except ImportError:
    OrchestratorIntentType = None

try:
    from backend.preprocessing.cypher_queries import IntentType as CypherIntentType
except ImportError:
    CypherIntentType = None


logger = logging.getLogger(__name__)


# ===========================================
# Mapping Tables
# ===========================================

# QueryIntentType → IntentType (for Cypher queries)
QUERY_INTENT_TO_INTENT_TYPE: Dict[str, str] = {
    "norm_search": "norm_explanation",           # Norm search → Norm explanation
    "interpretation": "contract_interpretation",  # Interpretation → Contract interpretation
    "compliance_check": "compliance_question",    # Compliance check → Compliance question
    "document_drafting": "precedent_search",     # Document drafting → Precedent search
    "risk_spotting": "compliance_question",      # Risk spotting → Compliance question
    "unknown": "precedent_search"                # Unknown → Default to precedent search
}

# Reverse mapping: IntentType → QueryIntentType (for completeness)
INTENT_TYPE_TO_QUERY_INTENT: Dict[str, str] = {
    "norm_explanation": "norm_search",
    "contract_interpretation": "interpretation",
    "compliance_question": "compliance_check",
    "precedent_search": "document_drafting"
}


# ===========================================
# Conversion Functions
# ===========================================

def convert_query_intent_to_intent_type(query_intent: "QueryIntentType") -> str:
    """
    Convert QueryIntentType to IntentType string value.

    Args:
        query_intent: QueryIntentType enum value

    Returns:
        IntentType string value for Cypher queries

    Examples:
        >>> convert_query_intent_to_intent_type(QueryIntentType.NORM_SEARCH)
        'norm_explanation'
        >>> convert_query_intent_to_intent_type(QueryIntentType.COMPLIANCE_CHECK)
        'compliance_question'
    """
    if QueryIntentType is None:
        raise ImportError("QueryIntentType not available. Check imports.")

    query_intent_value = query_intent.value if isinstance(query_intent, Enum) else str(query_intent)

    intent_type = QUERY_INTENT_TO_INTENT_TYPE.get(
        query_intent_value,
        "precedent_search"  # Default fallback
    )

    logger.debug(f"Converted query intent '{query_intent_value}' to intent type '{intent_type}'")

    return intent_type


def convert_intent_type_to_query_intent(intent_type: str) -> str:
    """
    Convert IntentType string to QueryIntentType string value.

    Args:
        intent_type: IntentType string value

    Returns:
        QueryIntentType string value

    Examples:
        >>> convert_intent_type_to_query_intent("norm_explanation")
        'norm_search'
        >>> convert_intent_type_to_query_intent("compliance_question")
        'compliance_check'
    """
    query_intent = INTENT_TYPE_TO_QUERY_INTENT.get(
        intent_type,
        "unknown"  # Default fallback
    )

    logger.debug(f"Converted intent type '{intent_type}' to query intent '{query_intent}'")

    return query_intent


def get_cypher_intent_from_query_understanding(query_intent: "QueryIntentType") -> "CypherIntentType":
    """
    Get CypherIntentType enum from QueryIntentType.

    Args:
        query_intent: QueryIntentType enum value

    Returns:
        CypherIntentType enum value for Cypher query selection

    Raises:
        ImportError: If CypherIntentType not available
    """
    if CypherIntentType is None:
        raise ImportError("CypherIntentType not available. Check imports.")

    intent_str = convert_query_intent_to_intent_type(query_intent)

    # Convert string to CypherIntentType enum
    try:
        return CypherIntentType(intent_str)
    except ValueError:
        logger.warning(f"Unknown intent type '{intent_str}', falling back to PRECEDENT_SEARCH")
        return CypherIntentType.PRECEDENT_SEARCH


def get_orchestrator_intent_from_query_understanding(query_intent: "QueryIntentType") -> "OrchestratorIntentType":
    """
    Get OrchestratorIntentType enum from QueryIntentType.

    Args:
        query_intent: QueryIntentType enum value

    Returns:
        OrchestratorIntentType enum value for pipeline orchestration

    Raises:
        ImportError: If OrchestratorIntentType not available
    """
    if OrchestratorIntentType is None:
        raise ImportError("OrchestratorIntentType not available. Check imports.")

    intent_str = convert_query_intent_to_intent_type(query_intent)

    # Convert string to OrchestratorIntentType enum
    try:
        return OrchestratorIntentType(intent_str)
    except ValueError:
        logger.warning(f"Unknown intent type '{intent_str}', falling back to UNKNOWN")
        return OrchestratorIntentType.UNKNOWN


# ===========================================
# Mapping Validation
# ===========================================

def validate_intent_mapping() -> bool:
    """
    Validate that intent mapping is complete and bidirectional.

    Returns:
        True if mapping is valid, False otherwise
    """
    issues = []

    # Check for unmapped QueryIntentType values
    if QueryIntentType is not None:
        for query_intent in QueryIntentType:
            if query_intent.value not in QUERY_INTENT_TO_INTENT_TYPE:
                issues.append(f"Missing mapping for QueryIntentType.{query_intent.name}")

    # Check for unmapped IntentType values
    if CypherIntentType is not None:
        for intent_type in CypherIntentType:
            if intent_type.value not in INTENT_TYPE_TO_QUERY_INTENT:
                # This is okay - not all IntentType values need reverse mapping
                logger.debug(f"No reverse mapping for IntentType.{intent_type.name} (not critical)")

    if issues:
        for issue in issues:
            logger.error(f"Intent mapping validation issue: {issue}")
        return False

    logger.info("Intent mapping validation passed")
    return True


# ===========================================
# Intent Type Info
# ===========================================

def get_intent_mapping_info() -> Dict[str, any]:
    """
    Get information about intent type mappings.

    Returns:
        dict with mapping statistics and details
    """
    return {
        "query_intent_types_count": len(QUERY_INTENT_TO_INTENT_TYPE),
        "intent_types_count": len(set(QUERY_INTENT_TO_INTENT_TYPE.values())),
        "reverse_mappings_count": len(INTENT_TYPE_TO_QUERY_INTENT),
        "mappings": {
            "query_to_intent": QUERY_INTENT_TO_INTENT_TYPE,
            "intent_to_query": INTENT_TYPE_TO_QUERY_INTENT
        }
    }


# ===========================================
# Convenience Functions for Common Workflows
# ===========================================

def prepare_query_understanding_for_kg_enrichment(query_understanding_result: Dict) -> Dict:
    """
    Prepare query understanding result for KG enrichment service.

    Converts QueryIntentType to IntentType and formats for enrichment.

    Args:
        query_understanding_result: Result from query understanding module

    Returns:
        dict formatted for KG enrichment service
    """
    # Extract query intent
    query_intent_str = query_understanding_result.get("intent", "unknown")

    # Convert to IntentType for Cypher queries
    intent_type_str = QUERY_INTENT_TO_INTENT_TYPE.get(query_intent_str, "precedent_search")

    # Prepare enrichment input
    enrichment_input = {
        "query_id": query_understanding_result.get("query_id"),
        "original_query": query_understanding_result.get("original_query"),
        "intent": intent_type_str,  # Converted intent
        "norm_references": query_understanding_result.get("norm_references", []),
        "legal_concepts": query_understanding_result.get("legal_concepts", []),
        "entities": query_understanding_result.get("extracted_entities", []),
        "confidence": query_understanding_result.get("confidence", 0.0),
        "next_stage": "kg_enrichment"
    }

    logger.debug(
        f"Prepared query understanding result for KG enrichment: "
        f"original_intent={query_intent_str}, converted_intent={intent_type_str}"
    )

    return enrichment_input
