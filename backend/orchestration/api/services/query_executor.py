"""
Query Executor Service

Wraps the LangGraph workflow execution and converts between API schemas and workflow state.
"""

import asyncio
import logging
import time
import uuid
from datetime import datetime
from typing import Dict, Any, Optional

from ..schemas.query import (
    QueryRequest,
    QueryResponse,
    Answer,
    ExecutionTrace,
    AnswerMetadata,
    LegalBasis,
    AlternativeInterpretation,
)
from ...langgraph_workflow import create_merlt_workflow

logger = logging.getLogger(__name__)


class QueryExecutor:
    """
    Service for executing legal queries via LangGraph workflow.

    Handles conversion between API request/response schemas and LangGraph state.
    """

    def __init__(self):
        """Initialize Query Executor."""
        self.workflow_app = None
        logger.info("QueryExecutor initialized")

    async def _get_workflow_app(self):
        """Lazy-load workflow app (compiled LangGraph)."""
        if self.workflow_app is None:
            logger.info("Creating LangGraph workflow app...")
            self.workflow_app = create_merlt_workflow()
            logger.info("LangGraph workflow app created successfully")
        return self.workflow_app

    def _generate_trace_id(self) -> str:
        """Generate unique trace ID for query execution."""
        timestamp = datetime.utcnow().strftime("%Y%m%d%H%M%S")
        unique_id = str(uuid.uuid4())[:8]
        return f"QRY-{timestamp}-{unique_id}"

    def _build_initial_state(
        self,
        request: QueryRequest,
        trace_id: str
    ) -> Dict[str, Any]:
        """
        Convert QueryRequest to initial MEGLTState.

        Args:
            request: QueryRequest from API
            trace_id: Generated trace ID

        Returns:
            Initial state dict compatible with MEGLTState TypedDict
        """
        # Build query_context from request
        query_context = {
            "query": request.query,
            "intent": "unknown",  # Will be determined by preprocessing
            "complexity": 0.5,    # Will be calculated by preprocessing
            "temporal_reference": None,
            "jurisdiction": "nazionale",
        }

        # Add user-provided context if available
        if request.context:
            if request.context.temporal_reference:
                query_context["temporal_reference"] = request.context.temporal_reference
            if request.context.jurisdiction:
                query_context["jurisdiction"] = request.context.jurisdiction
            if request.context.user_role:
                query_context["user_role"] = request.context.user_role
            if request.context.previous_queries:
                query_context["previous_queries"] = request.context.previous_queries

        # Build enriched_context (placeholder - preprocessing will populate)
        enriched_context = {
            "concepts": [],
            "entities": [],
            "norms": [],
        }

        # Build initial MEGLTState
        initial_state = {
            # Identifiers
            "trace_id": trace_id,
            "session_id": request.session_id,

            # Input
            "original_query": request.query,
            "query_context": query_context,
            "enriched_context": enriched_context,

            # Router output (will be populated by router_node)
            "execution_plan": None,

            # Retrieval results (will be populated by retrieval_node)
            "agent_results": {},

            # Expert reasoning (will be populated by experts_node)
            "expert_context": None,
            "expert_opinions": [],  # Accumulator

            # Synthesis (will be populated by synthesis_node)
            "provisional_answer": None,

            # Iteration control (will be populated by iteration_node)
            "iteration_context": None,
            "current_iteration": 1,
            "should_continue": True,
            "stop_reason": None,

            # Refinement (will be populated by refinement_node)
            "refinement_instructions": None,

            # Metadata
            "execution_time_ms": 0.0,
            "tokens_used": 0,
            "errors": [],  # Accumulator
        }

        # Override max_iterations if provided in options
        if request.options and request.options.max_iterations:
            # Note: This will be used by iteration_node to initialize IterationContext
            query_context["max_iterations"] = request.options.max_iterations

        return initial_state

    def _extract_answer_from_state(self, final_state: Dict[str, Any]) -> Answer:
        """
        Extract Answer schema from provisional_answer in final state.

        Args:
            final_state: MEGLTState after workflow completion

        Returns:
            Answer schema with primary answer, confidence, legal basis, etc.
        """
        provisional_answer = final_state.get("provisional_answer", {})

        # Extract primary answer and confidence
        primary_answer = provisional_answer.get("final_answer", "No answer generated.")
        confidence = provisional_answer.get("confidence", 0.0)
        consensus_level = provisional_answer.get("consensus_level")

        # Extract legal basis from supporting_norms
        legal_basis = []
        supporting_norms = provisional_answer.get("supporting_norms", [])
        for norm in supporting_norms:
            legal_basis.append(
                LegalBasis(
                    norm_id=norm.get("norm_id", "unknown"),
                    norm_title=norm.get("norm_title", "Unknown norm"),
                    article=norm.get("article"),
                    relevance=norm.get("relevance", 0.5),
                    excerpt=norm.get("excerpt"),
                )
            )

        # Extract alternative interpretations (if synthesis was divergent)
        alternative_interpretations = None
        if provisional_answer.get("alternative_views"):
            alternative_interpretations = []
            for alt_view in provisional_answer["alternative_views"]:
                alternative_interpretations.append(
                    AlternativeInterpretation(
                        position=alt_view.get("position", ""),
                        support_level=alt_view.get("support_level", "minority"),
                        supporting_norms=alt_view.get("supporting_norms", []),
                        supporting_jurisprudence=alt_view.get("supporting_jurisprudence"),
                        reasoning=alt_view.get("reasoning"),
                    )
                )

        # Check if uncertainty was preserved (Shannon entropy > threshold)
        uncertainty_preserved = provisional_answer.get("uncertainty_score", 0.0) > 0.3

        return Answer(
            primary_answer=primary_answer,
            confidence=confidence,
            legal_basis=legal_basis,
            jurisprudence=provisional_answer.get("jurisprudence"),
            alternative_interpretations=alternative_interpretations,
            uncertainty_preserved=uncertainty_preserved,
            consensus_level=consensus_level,
        )

    def _extract_execution_trace(
        self,
        final_state: Dict[str, Any],
        trace_id: str,
        return_trace: bool
    ) -> Optional[ExecutionTrace]:
        """
        Extract ExecutionTrace from final state.

        Args:
            final_state: MEGLTState after workflow completion
            trace_id: Query trace ID
            return_trace: Whether to include full trace

        Returns:
            ExecutionTrace if return_trace=True, else None
        """
        if not return_trace:
            return None

        # Determine stages executed (all nodes that completed)
        stages_executed = ["router", "retrieval", "experts", "synthesis", "iteration"]
        if final_state.get("refinement_instructions"):
            stages_executed.append("refinement")

        # Extract experts consulted
        execution_plan = final_state.get("execution_plan", {})
        experts_consulted = execution_plan.get("experts", [])

        # Extract agents used
        agent_results = final_state.get("agent_results", {})
        agents_used = [
            agent_name
            for agent_name, result in agent_results.items()
            if result.get("success", False)
        ]

        return ExecutionTrace(
            trace_id=trace_id,
            stages_executed=stages_executed,
            iterations=final_state.get("current_iteration", 1),
            stop_reason=final_state.get("stop_reason"),
            experts_consulted=experts_consulted,
            agents_used=agents_used,
            total_time_ms=final_state.get("execution_time_ms", 0.0),
            stage_timings=None,  # TODO: Extract per-stage timings if available
            tokens_used=final_state.get("tokens_used"),
            errors=final_state.get("errors", []),
        )

    def _extract_metadata(self, final_state: Dict[str, Any]) -> AnswerMetadata:
        """
        Extract AnswerMetadata from final state.

        Args:
            final_state: MEGLTState after workflow completion

        Returns:
            AnswerMetadata with complexity, intent, concepts, etc.
        """
        query_context = final_state.get("query_context", {})
        enriched_context = final_state.get("enriched_context", {})
        provisional_answer = final_state.get("provisional_answer", {})
        agent_results = final_state.get("agent_results", {})

        # Count norms consulted across all agents
        norms_consulted = 0
        jurisprudence_consulted = 0

        # KG Agent results
        kg_data = agent_results.get("kg_agent", {}).get("data", [])
        norms_consulted += sum(
            1 for item in kg_data
            if item.get("type") in ["norm", "article"]
        )
        jurisprudence_consulted += sum(
            1 for item in kg_data
            if item.get("type") == "sentenza"
        )

        # API Agent results
        api_data = agent_results.get("api_agent", {}).get("data", [])
        norms_consulted += len(api_data)

        # VectorDB Agent results
        vectordb_data = agent_results.get("vectordb_agent", {}).get("data", [])
        for doc in vectordb_data:
            doc_type = doc.get("metadata", {}).get("document_type", "")
            if doc_type in ["norm", "article"]:
                norms_consulted += 1
            elif doc_type == "sentenza":
                jurisprudence_consulted += 1

        return AnswerMetadata(
            complexity_score=query_context.get("complexity", 0.5),
            intent_detected=query_context.get("intent", "unknown"),
            concepts_identified=enriched_context.get("concepts", []),
            entities_identified=enriched_context.get("entities"),
            norms_consulted=norms_consulted,
            jurisprudence_consulted=jurisprudence_consulted,
            synthesis_mode=provisional_answer.get("synthesis_mode"),
        )

    async def execute_query(self, request: QueryRequest) -> QueryResponse:
        """
        Execute complete MERL-T pipeline for a legal query.

        Args:
            request: QueryRequest from API

        Returns:
            QueryResponse with answer, trace, and metadata

        Raises:
            asyncio.TimeoutError: If query exceeds timeout
            Exception: If workflow execution fails
        """
        # Generate trace ID
        trace_id = self._generate_trace_id()
        logger.info(f"[{trace_id}] Starting query execution: {request.query[:50]}...")

        start_time = time.time()

        try:
            # Get compiled workflow app
            app = await self._get_workflow_app()

            # Build initial state
            initial_state = self._build_initial_state(request, trace_id)

            # Execute workflow with timeout
            timeout_ms = request.options.timeout_ms if request.options else 30000
            timeout_seconds = timeout_ms / 1000.0

            logger.info(f"[{trace_id}] Invoking LangGraph workflow (timeout: {timeout_seconds}s)...")

            final_state = await asyncio.wait_for(
                app.ainvoke(initial_state),
                timeout=timeout_seconds
            )

            logger.info(f"[{trace_id}] Workflow completed successfully")

            # Extract components from final state
            answer = self._extract_answer_from_state(final_state)
            execution_trace = self._extract_execution_trace(
                final_state,
                trace_id,
                request.options.return_trace if request.options else True
            )
            metadata = self._extract_metadata(final_state)

            # Build response
            response = QueryResponse(
                trace_id=trace_id,
                session_id=request.session_id,
                answer=answer,
                execution_trace=execution_trace,
                metadata=metadata,
                timestamp=datetime.utcnow(),
            )

            elapsed_ms = (time.time() - start_time) * 1000
            logger.info(
                f"[{trace_id}] Query executed successfully in {elapsed_ms:.0f}ms "
                f"(confidence: {answer.confidence:.2f})"
            )

            return response

        except asyncio.TimeoutError:
            elapsed_ms = (time.time() - start_time) * 1000
            logger.error(f"[{trace_id}] Query execution timeout after {elapsed_ms:.0f}ms")
            raise

        except Exception as e:
            elapsed_ms = (time.time() - start_time) * 1000
            logger.error(
                f"[{trace_id}] Query execution failed after {elapsed_ms:.0f}ms: {str(e)}",
                exc_info=True
            )
            raise
