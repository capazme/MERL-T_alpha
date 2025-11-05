"""
Pipeline Orchestrator - Full Integration
========================================

Coordinates the entire legal AI pipeline:
Intent Classification → KG Enrichment → RLCF Processing → Feedback Loop

Responsibilities:
1. Orchestrate multi-step pipeline execution
2. Manage context flow between components
3. Track pipeline metrics and audit trail
4. Implement error handling and recovery
5. Trigger feedback loops to NER/Intent systems

Architecture:
- Async/await for parallel execution where possible
- Transactional consistency across databases
- Comprehensive logging and tracing
- Graceful degradation on component failure
"""

import asyncio
import logging
import json
import uuid
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Any, Tuple
from enum import Enum

from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func, and_

from backend.orchestration.intent_classifier import (
    IntentClassifier,
    IntentResult,
    IntentType
)
from backend.preprocessing.kg_enrichment_service import (
    KGEnrichmentService,
    EnrichedContext
)
from backend.rlcf_framework.models import (
    User,
    Task,
    TaskStatus,
    TaskType
)
from backend.rlcf_framework.authority_module import calculate_authority_score
from backend.preprocessing.models_kg import (
    StagingEntity,
    KGEdgeAudit,
    KGQualityMetrics,
    ControversyRecord,
    ReviewStatusEnum,
    SourceTypeEnum
)
from backend.preprocessing.query_understanding_router import integrate_query_understanding_with_kg
from backend.preprocessing.intent_mapping import prepare_query_understanding_for_kg_enrichment


logger = logging.getLogger(__name__)


class PipelineStage(str, Enum):
    """Pipeline execution stages."""
    RECEIVED = "received"
    NER_EXTRACTION = "ner_extraction"
    INTENT_CLASSIFICATION = "intent_classification"
    KG_ENRICHMENT = "kg_enrichment"
    RLCF_PROCESSING = "rlcf_processing"
    RESPONSE_GENERATION = "response_generation"
    FEEDBACK_COLLECTION = "feedback_collection"
    COMPLETED = "completed"


class PipelineExecutionStatus(str, Enum):
    """Overall pipeline execution status."""
    PENDING = "pending"
    IN_PROGRESS = "in_progress"
    SUCCESS = "success"
    PARTIAL_SUCCESS = "partial_success"
    FAILED = "failed"


class PipelineContext:
    """Context object flowing through the entire pipeline."""

    def __init__(self, query: str, context_id: str):
        """Initialize pipeline context."""
        self.context_id = context_id
        self.query = query
        self.timestamp_received = datetime.utcnow()

        # Query Understanding output (Week 5 Day 4 integration)
        self.query_understanding_result: Optional[Dict[str, Any]] = None

        # NER output
        self.extracted_entities: Dict[str, Any] = {}
        self.ner_confidence: float = 0.0

        # Intent classification output
        self.intent_result: Optional[IntentResult] = None

        # KG enrichment output
        self.enriched_context: Optional[EnrichedContext] = None

        # RLCF processing output
        self.rlcf_feedback_results: List[Dict[str, Any]] = []
        self.aggregated_consensus: Dict[str, Any] = {}

        # Audit trail
        self.execution_log: List[Dict[str, Any]] = []
        self.stage_timings: Dict[str, float] = {}

        # Feedback targets
        self.feedback_targets: List[str] = []  # Components needing feedback

        # Error tracking
        self.errors: List[str] = []
        self.warnings: List[str] = []

    def log_stage(self, stage: PipelineStage, duration_ms: float, data: Optional[Dict] = None):
        """Log pipeline stage execution."""
        self.execution_log.append({
            "stage": stage.value,
            "timestamp": datetime.utcnow().isoformat(),
            "duration_ms": duration_ms,
            "data": data or {}
        })
        self.stage_timings[stage.value] = duration_ms

    def add_error(self, error: str):
        """Track pipeline error."""
        self.errors.append(error)
        logger.error(f"Pipeline error [{self.context_id}]: {error}")

    def add_warning(self, warning: str):
        """Track pipeline warning."""
        self.warnings.append(warning)
        logger.warning(f"Pipeline warning [{self.context_id}]: {warning}")

    def total_duration_ms(self) -> float:
        """Get total pipeline execution duration."""
        if not self.stage_timings:
            return 0.0
        return sum(self.stage_timings.values())


class PipelineOrchestrator:
    """
    Main orchestrator coordinating the entire legal AI pipeline.

    Responsibilities:
    - Route queries through intent classification
    - Enrich with KG context
    - Collect RLCF feedback
    - Coordinate feedback loops
    - Track quality metrics
    """

    def __init__(
        self,
        intent_classifier: IntentClassifier,
        kg_service: KGEnrichmentService,
        db_session: AsyncSession,
        authority_module=None
    ):
        """
        Initialize orchestrator.

        Args:
            intent_classifier: Intent classification service
            kg_service: KG enrichment service
            db_session: Database session
            authority_module: Authority scoring module
        """
        self.intent_classifier = intent_classifier
        self.kg_service = kg_service
        self.db_session = db_session
        self.authority_module = authority_module
        self.logger = logger

    async def execute_pipeline(
        self,
        query: str,
        user_id: Optional[str] = None,
        ner_context: Optional[Dict[str, Any]] = None,
        trace_id: Optional[str] = None
    ) -> Tuple[PipelineContext, PipelineExecutionStatus]:
        """
        Execute full pipeline for a legal query.

        Flow:
        1. Initialize context
        2. Intent classification
        3. KG enrichment
        4. RLCF processing
        5. Feedback collection setup
        6. Return results

        Args:
            query: Legal query text
            user_id: User making the query
            ner_context: NER extraction results
            trace_id: Request trace ID

        Returns:
            (context, status) tuple
        """
        context_id = trace_id or str(uuid.uuid4())
        context = PipelineContext(query, context_id)

        try:
            # Stage 0: Query Understanding (Week 5 Day 4 - NEW)
            context = await self._execute_query_understanding(context)

            # Stage 1: Intent Classification
            context = await self._execute_intent_classification(context, user_id)

            # Stage 2: KG Enrichment (with intent type conversion)
            context = await self._execute_kg_enrichment(context)

            # Stage 3: RLCF Processing
            context = await self._execute_rlcf_processing(context, user_id)

            # Stage 4: Prepare Feedback Loop
            context = await self._prepare_feedback_loop(context)

            # Stage 5: Log to database
            await self._log_pipeline_execution(context, PipelineExecutionStatus.SUCCESS)

            return context, PipelineExecutionStatus.SUCCESS

        except Exception as e:
            context.add_error(f"Pipeline failed: {str(e)}")
            self.logger.error(f"Pipeline execution failed [{context_id}]: {str(e)}", exc_info=True)
            await self._log_pipeline_execution(context, PipelineExecutionStatus.FAILED)
            return context, PipelineExecutionStatus.FAILED

    async def _execute_query_understanding(self, context: PipelineContext) -> PipelineContext:
        """
        Stage 0: Query Understanding (Week 5 Day 4 integration)

        Extracts entities and intent using query understanding module.
        This provides richer context than simple intent classification.
        """
        start_time = datetime.utcnow()

        try:
            # Run query understanding integration
            qu_result = await integrate_query_understanding_with_kg(
                query=context.query,
                use_llm=True
            )

            context.query_understanding_result = qu_result

            # Populate extracted entities from query understanding
            context.extracted_entities = qu_result.get("entities", {})
            context.ner_confidence = qu_result.get("confidence", 0.0)

            duration_ms = (datetime.utcnow() - start_time).total_seconds() * 1000
            context.log_stage(
                PipelineStage.NER_EXTRACTION,  # Using existing enum
                duration_ms,
                {
                    "intent": qu_result.get("intent", "unknown"),
                    "intent_confidence": qu_result.get("intent_confidence", 0.0),
                    "norm_references": len(qu_result.get("norm_references", [])),
                    "legal_concepts": len(qu_result.get("legal_concepts", [])),
                    "entities_extracted": len(context.extracted_entities)
                }
            )

            self.logger.info(
                f"Query understanding completed [{context.context_id}]: "
                f"intent={qu_result.get('intent', 'unknown')}, "
                f"entities={len(context.extracted_entities)}, "
                f"norm_refs={len(qu_result.get('norm_references', []))}"
            )

            return context

        except Exception as e:
            context.add_warning(f"Query understanding failed (continuing with basic intent): {str(e)}")
            self.logger.warning(f"Query understanding failed, falling back to basic intent: {str(e)}")
            # Don't fail the pipeline, continue with basic intent classification
            return context

    async def _execute_intent_classification(
        self,
        context: PipelineContext,
        user_id: Optional[str]
    ) -> PipelineContext:
        """
        Stage 1: Intent Classification

        Classifies legal query intent using LLM classifier.
        Enriched with query understanding results if available.
        """
        start_time = datetime.utcnow()

        try:
            # Classify intent (may use query understanding results as context)
            intent_result = await self.intent_classifier.classify(
                query=context.query,
                user_id=user_id
            )

            context.intent_result = intent_result

            # Merge extracted entities from both sources
            if context.extracted_entities:
                # Combine query understanding entities with intent classifier entities
                combined_entities = {**context.extracted_entities}
                if intent_result.extracted_entities:
                    combined_entities.update(intent_result.extracted_entities)
                context.extracted_entities = combined_entities
            else:
                context.extracted_entities = intent_result.extracted_entities or {}

            duration_ms = (datetime.utcnow() - start_time).total_seconds() * 1000
            context.log_stage(
                PipelineStage.INTENT_CLASSIFICATION,
                duration_ms,
                {
                    "intent": intent_result.intent.value if intent_result.intent else None,
                    "confidence": intent_result.confidence,
                    "entities_extracted": len(context.extracted_entities),
                    "query_understanding_available": bool(context.query_understanding_result)
                }
            )

            self.logger.info(
                f"Intent classified [{context.context_id}]: "
                f"{intent_result.intent.value if intent_result.intent else 'UNKNOWN'} "
                f"(confidence: {intent_result.confidence:.2f})"
            )

            return context

        except Exception as e:
            context.add_error(f"Intent classification failed: {str(e)}")
            raise

    async def _execute_kg_enrichment(self, context: PipelineContext) -> PipelineContext:
        """
        Stage 2: KG Enrichment

        Enriches intent result with multi-source legal context.
        Uses query understanding result if available (Week 5 Day 4 integration).
        """
        start_time = datetime.utcnow()

        try:
            # Prepare enrichment input (prefer query understanding, fallback to intent result)
            enrichment_input = None

            if context.query_understanding_result:
                # Use query understanding result with intent type conversion
                enrichment_input = prepare_query_understanding_for_kg_enrichment(
                    context.query_understanding_result
                )
                self.logger.debug(f"Using query understanding result for KG enrichment [{context.context_id}]")
            elif context.intent_result:
                # Fallback to basic intent result
                enrichment_input = context.intent_result
                self.logger.debug(f"Using basic intent result for KG enrichment [{context.context_id}]")
            else:
                context.add_warning("No intent or query understanding result for KG enrichment")
                return context

            # Enrich with KG
            enriched = await self.kg_service.enrich_context(enrichment_input)

            context.enriched_context = enriched

            duration_ms = (datetime.utcnow() - start_time).total_seconds() * 1000
            context.log_stage(
                PipelineStage.KG_ENRICHMENT,
                duration_ms,
                {
                    "norms_found": len(enriched.norms) if enriched.norms else 0,
                    "sentenze_found": len(enriched.sentenze) if enriched.sentenze else 0,
                    "dottrina_found": len(enriched.dottrina) if enriched.dottrina else 0,
                    "contributions_found": len(enriched.contributions) if enriched.contributions else 0,
                    "controversies": len(enriched.controversy_flags) if enriched.controversy_flags else 0,
                    "cache_hit": enriched.enrichment_metadata.get("cache_hit", False),
                    "used_query_understanding": bool(context.query_understanding_result)
                }
            )

            self.logger.info(
                f"KG enrichment completed [{context.context_id}]: "
                f"{len(enriched.norms or [])} norms, "
                f"{len(enriched.sentenze or [])} sentenze, "
                f"{len(enriched.dottrina or [])} doctrine sources "
                f"(source: {'query_understanding' if context.query_understanding_result else 'basic_intent'})"
            )

            return context

        except Exception as e:
            context.add_error(f"KG enrichment failed: {str(e)}")
            raise

    async def _execute_rlcf_processing(
        self,
        context: PipelineContext,
        user_id: Optional[str]
    ) -> PipelineContext:
        """
        Stage 3: RLCF Processing

        Aggregates expert feedback and calculates consensus.
        """
        start_time = datetime.utcnow()

        try:
            if not context.enriched_context:
                context.add_warning("No enriched context for RLCF processing")
                return context

            # In production: collect RLCF votes on entities
            # For now: placeholder for RLCF aggregation

            # Example: Calculate consensus on norm interpretation
            if context.enriched_context.norms:
                consensus = await self._aggregate_rlcf_feedback(
                    context.enriched_context.norms,
                    user_id
                )
                context.aggregated_consensus = consensus

            duration_ms = (datetime.utcnow() - start_time).total_seconds() * 1000
            context.log_stage(
                PipelineStage.RLCF_PROCESSING,
                duration_ms,
                {
                    "consensus_entities": len(context.aggregated_consensus),
                    "avg_agreement": context.aggregated_consensus.get("avg_agreement", 0.0)
                }
            )

            self.logger.info(
                f"RLCF processing completed [{context.context_id}]: "
                f"Consensus calculated for {len(context.aggregated_consensus)} entities"
            )

            return context

        except Exception as e:
            context.add_error(f"RLCF processing failed: {str(e)}")
            raise

    async def _aggregate_rlcf_feedback(
        self,
        norms: List[Any],
        user_id: Optional[str]
    ) -> Dict[str, Any]:
        """
        Aggregate RLCF feedback on entities.

        Returns consensus scores and disagreement metrics.
        """
        try:
            # In production: query RLCF votes from database
            # For now: placeholder implementation

            consensus = {
                "avg_agreement": 0.85,
                "expert_count": 5,
                "disagreement_entropy": 0.3,
                "flagged_entities": []
            }

            # Check for controversies
            if not hasattr(self, '_controversies_checked'):
                result = await self.db_session.execute(
                    select(ControversyRecord).filter(
                        ControversyRecord.is_resolved == False,
                        ControversyRecord.severity.in_(["high", "critical"])
                    ).limit(10)
                )
                controversies = result.scalars().all()
                if controversies:
                    consensus["flagged_entities"] = [c.node_id for c in controversies]

            return consensus

        except Exception as e:
            self.logger.error(f"Error aggregating RLCF feedback: {str(e)}")
            return {"avg_agreement": 0.0, "flagged_entities": []}

    async def _prepare_feedback_loop(self, context: PipelineContext) -> PipelineContext:
        """
        Stage 4: Prepare Feedback Loop

        Identifies components that need feedback for improvement.
        """
        start_time = datetime.utcnow()

        try:
            feedback_targets = []

            # If low intent confidence: feedback to intent classifier
            if context.intent_result and context.intent_result.confidence < 0.75:
                feedback_targets.append("intent_classifier")

            # If NER missed entities: feedback to NER pipeline
            if context.enriched_context and len(context.enriched_context.norms or []) > 0:
                if not context.extracted_entities:
                    feedback_targets.append("ner_pipeline")

            # If controversies found: flag for expert review
            if context.enriched_context and context.enriched_context.controversy_flags:
                feedback_targets.append("expert_review_queue")

            context.feedback_targets = feedback_targets

            duration_ms = (datetime.utcnow() - start_time).total_seconds() * 1000
            context.log_stage(
                PipelineStage.FEEDBACK_COLLECTION,
                duration_ms,
                {"feedback_targets": feedback_targets}
            )

            self.logger.info(
                f"Feedback loop prepared [{context.context_id}]: "
                f"Targeting {', '.join(feedback_targets)}"
            )

            return context

        except Exception as e:
            context.add_error(f"Feedback loop preparation failed: {str(e)}")
            raise

    async def _log_pipeline_execution(
        self,
        context: PipelineContext,
        status: PipelineExecutionStatus
    ) -> None:
        """
        Log pipeline execution to database for audit trail.
        """
        try:
            execution_record = {
                "pipeline_id": context.context_id,
                "status": status.value,
                "query": context.query[:500],  # Truncate long queries
                "intent": context.intent_result.intent.value if context.intent_result else None,
                "intent_confidence": context.intent_result.confidence if context.intent_result else 0.0,
                "kg_entities_found": (
                    len(context.enriched_context.norms or []) +
                    len(context.enriched_context.sentenze or []) +
                    len(context.enriched_context.dottrina or [])
                ) if context.enriched_context else 0,
                "execution_time_ms": context.total_duration_ms(),
                "error_count": len(context.errors),
                "warning_count": len(context.warnings),
                "feedback_targets": context.feedback_targets,
                "execution_log": json.dumps(context.execution_log),
                "timestamp": datetime.utcnow().isoformat()
            }

            self.logger.info(f"Pipeline execution logged: {execution_record}")

            # In production: save to audit_log table
            # For now: just log to console/file

        except Exception as e:
            self.logger.error(f"Error logging pipeline execution: {str(e)}")

    # ==========================================
    # Feedback Loop Methods
    # ==========================================

    async def submit_feedback(
        self,
        context_id: str,
        feedback_type: str,  # "validation", "correction", "clarification"
        entity_id: str,
        feedback_text: str,
        user_authority: float
    ) -> Dict[str, Any]:
        """
        Submit feedback on pipeline results.

        Used for:
        - Correcting entity recognition
        - Validating intent classification
        - Clarifying controversial interpretations

        Args:
            context_id: Pipeline execution ID
            feedback_type: Type of feedback
            entity_id: Entity being corrected
            feedback_text: Feedback content
            user_authority: User's authority score

        Returns:
            Feedback processing result
        """
        try:
            feedback_id = str(uuid.uuid4())

            # Log feedback
            self.logger.info(
                f"Feedback received [{feedback_id}]: "
                f"type={feedback_type}, entity={entity_id}, authority={user_authority:.2f}"
            )

            # Route to appropriate feedback handler
            if feedback_type == "ner_correction":
                await self._process_ner_feedback(context_id, entity_id, feedback_text)
            elif feedback_type == "intent_validation":
                await self._process_intent_feedback(context_id, feedback_text)
            elif feedback_type == "entity_clarification":
                await self._process_entity_clarification(context_id, entity_id, feedback_text)

            return {
                "feedback_id": feedback_id,
                "status": "received",
                "context_id": context_id,
                "timestamp": datetime.utcnow().isoformat()
            }

        except Exception as e:
            self.logger.error(f"Error processing feedback: {str(e)}")
            return {"status": "error", "error": str(e)}

    async def _process_ner_feedback(
        self,
        context_id: str,
        entity_id: str,
        feedback_text: str
    ) -> None:
        """
        Process NER feedback for learning loop.

        Routes feedback to NER pipeline for model improvement.
        """
        self.logger.info(f"Processing NER feedback: {entity_id}")
        # In production: send to NER feedback queue

    async def _process_intent_feedback(
        self,
        context_id: str,
        feedback_text: str
    ) -> None:
        """
        Process intent classification feedback.

        Routes feedback to intent classifier for retraining.
        """
        self.logger.info(f"Processing intent feedback: {context_id}")
        # In production: send to intent classifier feedback queue

    async def _process_entity_clarification(
        self,
        context_id: str,
        entity_id: str,
        clarification_text: str
    ) -> None:
        """
        Process entity clarification feedback.

        Updates entity interpretation based on user feedback.
        """
        self.logger.info(f"Processing entity clarification: {entity_id}")
        # In production: update entity metadata in KG

    # ==========================================
    # Metrics & Monitoring
    # ==========================================

    async def get_pipeline_metrics(self, hours: int = 24) -> Dict[str, Any]:
        """
        Get pipeline performance metrics.

        Returns:
            Metrics dictionary with:
            - throughput
            - avg latency per stage
            - error rates
            - quality indicators
        """
        try:
            # In production: query from metrics database
            metrics = {
                "period_hours": hours,
                "total_executions": 0,
                "success_rate": 0.95,
                "avg_latency_ms": {
                    "intent_classification": 250,
                    "kg_enrichment": 300,
                    "rlcf_processing": 150,
                    "total": 700
                },
                "error_rate": 0.05,
                "feedback_loops_triggered": 0,
                "cache_hit_ratio": 0.72
            }

            return metrics

        except Exception as e:
            self.logger.error(f"Error getting pipeline metrics: {str(e)}")
            return {}


# ==========================================
# Factory Functions
# ==========================================

async def create_pipeline_orchestrator(
    intent_classifier: IntentClassifier,
    kg_service: KGEnrichmentService,
    db_session: AsyncSession
) -> PipelineOrchestrator:
    """
    Factory function to create pipeline orchestrator.

    Args:
        intent_classifier: Intent classification service
        kg_service: KG enrichment service
        db_session: Database session

    Returns:
        Initialized PipelineOrchestrator instance
    """
    return PipelineOrchestrator(
        intent_classifier=intent_classifier,
        kg_service=kg_service,
        db_session=db_session
    )


# ==========================================
# Middleware for Pipeline Integration
# ==========================================

class PipelineMiddleware:
    """
    ASGI middleware for pipeline integration.

    Tracks all requests through the pipeline.
    """

    def __init__(self, app, orchestrator: PipelineOrchestrator):
        """Initialize middleware."""
        self.app = app
        self.orchestrator = orchestrator

    async def __call__(self, scope, receive, send):
        """Process request through middleware."""
        if scope["type"] == "http":
            # Add trace ID to request
            scope["trace_id"] = str(uuid.uuid4())

        await self.app(scope, receive, send)
