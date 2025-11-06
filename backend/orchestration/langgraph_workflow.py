"""
LangGraph Workflow for MERL-T Legal AI System.

This module implements the complete end-to-end workflow using LangGraph:
- State management across all components
- 6 nodes: Router, Retrieval, Experts, Synthesis, Iteration, Refinement
- Conditional routing for multi-turn iteration
- Full error handling and observability

Architecture:
    START → router → retrieval → experts → synthesis → iteration
             ↑                                           ↓
             |                                      (decision)
             |                                           ↓
             +---- refinement <-- (if continue)
                                  ↓
                             (if stop) → END
"""

import logging
import asyncio
import time
from typing import TypedDict, Annotated, Sequence, Optional, Dict, Any
from datetime import datetime
import operator

from langgraph.graph import StateGraph, END

# Import orchestration components
from backend.orchestration.llm_router import LLMRouter
from backend.orchestration.agents import KGAgent, APIAgent, VectorDBAgent
from backend.orchestration.experts import (
    LiteralInterpreter,
    SystemicTeleological,
    PrinciplesBalancer,
    PrecedentAnalyst
)
from backend.orchestration.experts.base import ExpertContext
from backend.orchestration.experts.synthesizer import Synthesizer
from backend.orchestration.iteration.controller import IterationController
from backend.orchestration.iteration.models import IterationContext

logger = logging.getLogger(__name__)


# ============================================================================
# State Schema
# ============================================================================

class MEGLTState(TypedDict):
    """
    Complete state flowing through LangGraph workflow.

    Field types:
    - Single-value fields: Replaced on each node (last write wins)
    - Annotated[Sequence, operator.add]: Accumulate values across nodes
    - Dict fields: Merged by default

    State flows through:
    router → retrieval → experts → synthesis → iteration → (refinement → router) → END
    """
    # ========== Identifiers ==========
    trace_id: str
    session_id: Optional[str]

    # ========== Input (immutable through workflow) ==========
    original_query: str
    query_context: Dict[str, Any]  # From preprocessing layer
    enriched_context: Dict[str, Any]  # From KG enrichment service

    # ========== Router Output ==========
    execution_plan: Optional[Dict[str, Any]]  # ExecutionPlan from Router

    # ========== Retrieval Results ==========
    agent_results: Dict[str, Any]  # {agent_name: AgentResult dict}

    # ========== Expert Reasoning ==========
    expert_context: Optional[Dict[str, Any]]  # ExpertContext for experts
    expert_opinions: Annotated[Sequence[Dict[str, Any]], operator.add]  # Accumulate

    # ========== Synthesis ==========
    provisional_answer: Optional[Dict[str, Any]]  # ProvisionalAnswer

    # ========== Iteration Control ==========
    iteration_context: Optional[Dict[str, Any]]  # IterationContext
    current_iteration: int
    should_continue: bool
    stop_reason: Optional[str]

    # ========== Refinement (for next iteration) ==========
    refinement_instructions: Optional[Dict[str, Any]]

    # ========== Metadata ==========
    execution_time_ms: float
    tokens_used: int
    errors: Annotated[Sequence[str], operator.add]  # Accumulate errors


# ============================================================================
# Node 1: Router Node
# ============================================================================

async def router_node(state: MEGLTState) -> MEGLTState:
    """
    Generate ExecutionPlan using LLM Router.

    Decides which agents to activate and which experts to consult
    based on query complexity and refinement context (if iterating).

    Input state fields:
    - query_context
    - enriched_context
    - refinement_instructions (if iteration > 1)

    Output state fields:
    - execution_plan (ExecutionPlan dict)
    - errors (if router fails)
    """
    logger.info(
        f"[{state['trace_id']}] Router node: iteration {state['current_iteration']}"
    )

    start_time = time.time()

    try:
        router = LLMRouter()

        # Build context with refinement instructions if iterating
        context = state["query_context"].copy()
        if state.get("refinement_instructions"):
            context["refinement_context"] = state["refinement_instructions"]
            logger.info(
                f"[{state['trace_id']}] Router: Including refinement context "
                f"for iteration {state['current_iteration']}"
            )

        # Generate execution plan
        execution_plan = await router.generate_execution_plan(
            query_context=context,
            enriched_context=state["enriched_context"]
        )

        elapsed_ms = (time.time() - start_time) * 1000

        logger.info(
            f"[{state['trace_id']}] Router completed in {elapsed_ms:.0f}ms: "
            f"agents={len([a for a in [execution_plan.get('kg_agent', {}), execution_plan.get('api_agent', {}), execution_plan.get('vectordb_agent', {})] if a.get('enabled')])}, "
            f"experts={len(execution_plan.get('experts', []))}"
        )

        return {
            **state,
            "execution_plan": execution_plan,
            "execution_time_ms": state.get("execution_time_ms", 0.0) + elapsed_ms
        }

    except Exception as e:
        elapsed_ms = (time.time() - start_time) * 1000
        logger.error(
            f"[{state['trace_id']}] Router node failed after {elapsed_ms:.0f}ms: {e}",
            exc_info=True
        )

        return {
            **state,
            "errors": [f"Router failed: {str(e)}"],
            "execution_time_ms": state.get("execution_time_ms", 0.0) + elapsed_ms
        }


# ============================================================================
# Node 2: Retrieval Node
# ============================================================================

async def retrieval_node(state: MEGLTState) -> MEGLTState:
    """
    Execute retrieval agents in parallel based on ExecutionPlan.

    Runs KG Agent, API Agent, and VectorDB Agent concurrently to
    retrieve relevant legal data.

    Input state fields:
    - execution_plan.kg_agent, api_agent, vectordb_agent

    Output state fields:
    - agent_results (dict of AgentResult dicts)
    - errors (if any agent fails)
    """
    logger.info(
        f"[{state['trace_id']}] Retrieval node: executing agents"
    )

    start_time = time.time()

    plan = state["execution_plan"]
    tasks = []
    agent_names = []

    try:
        # KG Agent
        if plan.get("kg_agent", {}).get("enabled", False):
            kg_agent = KGAgent()
            kg_tasks = plan["kg_agent"].get("tasks", [])
            logger.debug(f"[{state['trace_id']}] KG Agent: {len(kg_tasks)} tasks")
            tasks.append(kg_agent.execute(kg_tasks))
            agent_names.append("kg_agent")

        # API Agent
        if plan.get("api_agent", {}).get("enabled", False):
            api_agent = APIAgent()
            api_tasks = plan["api_agent"].get("tasks", [])
            logger.debug(f"[{state['trace_id']}] API Agent: {len(api_tasks)} tasks")
            tasks.append(api_agent.execute(api_tasks))
            agent_names.append("api_agent")

        # VectorDB Agent
        if plan.get("vectordb_agent", {}).get("enabled", False):
            vectordb_agent = VectorDBAgent()
            vectordb_tasks = plan["vectordb_agent"].get("tasks", [])
            logger.debug(f"[{state['trace_id']}] VectorDB Agent: {len(vectordb_tasks)} tasks")
            tasks.append(vectordb_agent.execute(vectordb_tasks))
            agent_names.append("vectordb_agent")

        # Execute in parallel
        if not tasks:
            logger.warning(f"[{state['trace_id']}] No agents enabled")
            return {
                **state,
                "agent_results": {},
                "execution_time_ms": state.get("execution_time_ms", 0.0)
            }

        results = await asyncio.gather(*tasks, return_exceptions=True)

        # Process results
        agent_results = {}
        errors = []

        for i, agent_name in enumerate(agent_names):
            result = results[i]

            if isinstance(result, Exception):
                logger.error(
                    f"[{state['trace_id']}] {agent_name} failed: {result}",
                    exc_info=result
                )
                agent_results[agent_name] = {
                    "success": False,
                    "error": str(result),
                    "data": []
                }
                errors.append(f"{agent_name} failed: {str(result)}")
            else:
                logger.debug(
                    f"[{state['trace_id']}] {agent_name} succeeded: "
                    f"{len(result.get('data', []))} results"
                )
                agent_results[agent_name] = result

        elapsed_ms = (time.time() - start_time) * 1000

        logger.info(
            f"[{state['trace_id']}] Retrieval completed in {elapsed_ms:.0f}ms: "
            f"agents={len(agent_results)}, errors={len(errors)}"
        )

        return {
            **state,
            "agent_results": agent_results,
            "errors": errors if errors else state.get("errors", []),
            "execution_time_ms": state.get("execution_time_ms", 0.0) + elapsed_ms
        }

    except Exception as e:
        elapsed_ms = (time.time() - start_time) * 1000
        logger.error(
            f"[{state['trace_id']}] Retrieval node failed after {elapsed_ms:.0f}ms: {e}",
            exc_info=True
        )

        return {
            **state,
            "agent_results": {},
            "errors": [f"Retrieval failed: {str(e)}"],
            "execution_time_ms": state.get("execution_time_ms", 0.0) + elapsed_ms
        }


# ============================================================================
# Node 3: Experts Node
# ============================================================================

async def experts_node(state: MEGLTState) -> MEGLTState:
    """
    Execute reasoning experts in parallel.

    Runs 4 legal experts (Literal Interpreter, Systemic-Teleological,
    Principles Balancer, Precedent Analyst) concurrently to analyze
    the query with different methodologies.

    Input state fields:
    - query_context
    - agent_results
    - execution_plan.experts

    Output state fields:
    - expert_opinions (list of ExpertOpinion dicts)
    - expert_context (ExpertContext dict)
    - errors (if any expert fails)
    """
    logger.info(
        f"[{state['trace_id']}] Experts node: executing experts"
    )

    start_time = time.time()

    try:
        # Build ExpertContext from state
        expert_context = ExpertContext(
            query_text=state["original_query"],
            intent=state["query_context"].get("intent", "unknown"),
            complexity=state["query_context"].get("complexity", 0.5),
            norm_references=state["query_context"].get("norm_references", []),
            legal_concepts=state["query_context"].get("legal_concepts", []),
            entities=state["query_context"].get("entities", {}),
            kg_results=state["agent_results"].get("kg_agent", {}).get("data", []),
            api_results=state["agent_results"].get("api_agent", {}).get("data", []),
            vectordb_results=state["agent_results"].get("vectordb_agent", {}).get("data", []),
            enriched_context=state.get("enriched_context"),
            refinement_context=state.get("refinement_instructions"),
            trace_id=state["trace_id"]
        )

        # Map expert types to classes
        expert_map = {
            "literal_interpreter": LiteralInterpreter,
            "systemic_teleological": SystemicTeleological,
            "principles_balancer": PrinciplesBalancer,
            "precedent_analyst": PrecedentAnalyst
        }

        # Get selected experts from execution plan
        selected_experts = state["execution_plan"].get("experts", [])

        if not selected_experts:
            logger.warning(f"[{state['trace_id']}] No experts selected")
            return {
                **state,
                "expert_opinions": [],
                "expert_context": expert_context.model_dump(),
                "execution_time_ms": state.get("execution_time_ms", 0.0)
            }

        # Create expert tasks
        tasks = []
        expert_types = []

        for expert_type in selected_experts:
            if expert_type in expert_map:
                expert = expert_map[expert_type]()
                tasks.append(expert.analyze(expert_context))
                expert_types.append(expert_type)
                logger.debug(f"[{state['trace_id']}] Queuing expert: {expert_type}")

        # Execute in parallel
        opinions = await asyncio.gather(*tasks, return_exceptions=True)

        # Process results
        opinion_dicts = []
        errors = []

        for i, expert_type in enumerate(expert_types):
            opinion = opinions[i]

            if isinstance(opinion, Exception):
                logger.error(
                    f"[{state['trace_id']}] Expert {expert_type} failed: {opinion}",
                    exc_info=opinion
                )
                errors.append(f"{expert_type} failed: {str(opinion)}")
            else:
                logger.debug(
                    f"[{state['trace_id']}] Expert {expert_type} succeeded: "
                    f"confidence={opinion.confidence:.2f}"
                )
                opinion_dicts.append(opinion.model_dump())

        elapsed_ms = (time.time() - start_time) * 1000

        logger.info(
            f"[{state['trace_id']}] Experts completed in {elapsed_ms:.0f}ms: "
            f"experts={len(opinion_dicts)}/{len(selected_experts)}, errors={len(errors)}"
        )

        return {
            **state,
            "expert_opinions": opinion_dicts,
            "expert_context": expert_context.model_dump(),
            "errors": errors if errors else state.get("errors", []),
            "execution_time_ms": state.get("execution_time_ms", 0.0) + elapsed_ms
        }

    except Exception as e:
        elapsed_ms = (time.time() - start_time) * 1000
        logger.error(
            f"[{state['trace_id']}] Experts node failed after {elapsed_ms:.0f}ms: {e}",
            exc_info=True
        )

        return {
            **state,
            "expert_opinions": [],
            "errors": [f"Experts failed: {str(e)}"],
            "execution_time_ms": state.get("execution_time_ms", 0.0) + elapsed_ms
        }


# ============================================================================
# Node 4: Synthesis Node
# ============================================================================

async def synthesis_node(state: MEGLTState) -> MEGLTState:
    """
    Synthesize expert opinions into provisional answer.

    Combines multiple expert opinions using either convergent mode
    (extract consensus) or divergent mode (preserve disagreement).

    Input state fields:
    - expert_opinions
    - execution_plan.synthesis_mode

    Output state fields:
    - provisional_answer (ProvisionalAnswer dict)
    - errors (if synthesis fails)
    """
    logger.info(
        f"[{state['trace_id']}] Synthesis node: synthesizing {len(state['expert_opinions'])} opinions"
    )

    start_time = time.time()

    try:
        from backend.orchestration.experts.base import ExpertOpinion

        synthesizer = Synthesizer()

        # Convert dicts back to ExpertOpinion objects
        opinions = [ExpertOpinion(**op) for op in state["expert_opinions"]]

        if not opinions:
            logger.warning(f"[{state['trace_id']}] No expert opinions to synthesize")
            # Return empty provisional answer
            return {
                **state,
                "provisional_answer": {
                    "trace_id": state["trace_id"],
                    "final_answer": "Nessuna opinione esperta disponibile.",
                    "synthesis_mode": "fallback",
                    "confidence": 0.0,
                    "consensus_level": 0.0,
                    "experts_consulted": [],
                    "provenance": []
                },
                "errors": ["No expert opinions to synthesize"],
                "execution_time_ms": state.get("execution_time_ms", 0.0)
            }

        synthesis_mode = state["execution_plan"].get("synthesis_mode", "convergent")

        logger.debug(
            f"[{state['trace_id']}] Synthesis mode: {synthesis_mode}"
        )

        provisional_answer = await synthesizer.synthesize(
            expert_opinions=opinions,
            synthesis_mode=synthesis_mode,
            query_text=state["original_query"],
            trace_id=state["trace_id"]
        )

        elapsed_ms = (time.time() - start_time) * 1000

        logger.info(
            f"[{state['trace_id']}] Synthesis completed in {elapsed_ms:.0f}ms: "
            f"confidence={provisional_answer.confidence:.2f}, "
            f"consensus={provisional_answer.consensus_level:.2f}"
        )

        return {
            **state,
            "provisional_answer": provisional_answer.model_dump(),
            "execution_time_ms": state.get("execution_time_ms", 0.0) + elapsed_ms
        }

    except Exception as e:
        elapsed_ms = (time.time() - start_time) * 1000
        logger.error(
            f"[{state['trace_id']}] Synthesis node failed after {elapsed_ms:.0f}ms: {e}",
            exc_info=True
        )

        return {
            **state,
            "provisional_answer": None,
            "errors": [f"Synthesis failed: {str(e)}"],
            "execution_time_ms": state.get("execution_time_ms", 0.0) + elapsed_ms
        }


# ============================================================================
# Node 5: Iteration Node
# ============================================================================

async def iteration_node(state: MEGLTState) -> MEGLTState:
    """
    Decide if iteration should continue.

    Evaluates 6 stopping criteria to determine if the workflow should
    continue refining or stop and return the answer.

    Input state fields:
    - iteration_context (or create new)
    - provisional_answer
    - execution_plan
    - execution_time_ms

    Output state fields:
    - iteration_context (updated)
    - should_continue (bool)
    - stop_reason (str)
    - current_iteration (int)
    """
    logger.info(
        f"[{state['trace_id']}] Iteration node: evaluating stopping criteria"
    )

    start_time = time.time()

    try:
        controller = IterationController()

        # Initialize or retrieve iteration context
        if not state.get("iteration_context"):
            logger.debug(f"[{state['trace_id']}] Initializing new iteration context")
            context = await controller.start_iteration_session(
                query=state["original_query"],
                query_context=state["query_context"],
                max_iterations=3,
                trace_id=state["trace_id"]
            )
        else:
            logger.debug(f"[{state['trace_id']}] Loading existing iteration context")
            context = IterationContext(**state["iteration_context"])

        # Process this iteration
        if state.get("provisional_answer"):
            context = await controller.process_iteration(
                context=context,
                provisional_answer=state["provisional_answer"],
                execution_plan=state["execution_plan"],
                execution_time_ms=state.get("execution_time_ms", 0.0)
            )
        else:
            logger.warning(f"[{state['trace_id']}] No provisional answer to process")

        # Evaluate stopping criteria
        should_continue, stop_reason = await controller.should_continue_iteration(context)

        elapsed_ms = (time.time() - start_time) * 1000

        logger.info(
            f"[{state['trace_id']}] Iteration evaluation completed in {elapsed_ms:.0f}ms: "
            f"should_continue={should_continue}, reason={stop_reason}, "
            f"iteration={context.current_iteration}/{context.max_iterations}"
        )

        return {
            **state,
            "iteration_context": context.model_dump(),
            "current_iteration": context.current_iteration,
            "should_continue": should_continue,
            "stop_reason": stop_reason,
            "execution_time_ms": state.get("execution_time_ms", 0.0) + elapsed_ms
        }

    except Exception as e:
        elapsed_ms = (time.time() - start_time) * 1000
        logger.error(
            f"[{state['trace_id']}] Iteration node failed after {elapsed_ms:.0f}ms: {e}",
            exc_info=True
        )

        # Default to stopping on error
        return {
            **state,
            "should_continue": False,
            "stop_reason": f"Error in iteration control: {str(e)}",
            "errors": [f"Iteration failed: {str(e)}"],
            "execution_time_ms": state.get("execution_time_ms", 0.0) + elapsed_ms
        }


# ============================================================================
# Node 6: Refinement Node
# ============================================================================

async def refinement_node(state: MEGLTState) -> MEGLTState:
    """
    Generate refinement instructions for next iteration.

    Analyzes user feedback and RLCF evaluations to generate structured
    instructions for the Router to use in the next iteration.

    Input state fields:
    - iteration_context

    Output state fields:
    - refinement_instructions (dict)
    - current_iteration (incremented)
    """
    logger.info(
        f"[{state['trace_id']}] Refinement node: generating refinement instructions"
    )

    start_time = time.time()

    try:
        controller = IterationController()
        context = IterationContext(**state["iteration_context"])

        # Generate refinement instructions
        refinement = await controller.generate_refinement_instructions(context)

        # Increment iteration counter
        next_iteration = state["current_iteration"] + 1

        elapsed_ms = (time.time() - start_time) * 1000

        logger.info(
            f"[{state['trace_id']}] Refinement completed in {elapsed_ms:.0f}ms: "
            f"next_iteration={next_iteration}, "
            f"instructions={len(refinement.get('refinement_instructions', ''))}"
        )

        return {
            **state,
            "refinement_instructions": refinement,
            "current_iteration": next_iteration,
            "execution_time_ms": state.get("execution_time_ms", 0.0) + elapsed_ms
        }

    except Exception as e:
        elapsed_ms = (time.time() - start_time) * 1000
        logger.error(
            f"[{state['trace_id']}] Refinement node failed after {elapsed_ms:.0f}ms: {e}",
            exc_info=True
        )

        return {
            **state,
            "refinement_instructions": None,
            "errors": [f"Refinement failed: {str(e)}"],
            "execution_time_ms": state.get("execution_time_ms", 0.0) + elapsed_ms
        }


# ============================================================================
# Conditional Routing Function
# ============================================================================

def should_iterate(state: MEGLTState) -> str:
    """
    Conditional edge: Continue iteration or end workflow?

    Returns:
    - "refinement" -> loop back for next iteration
    - "end" -> stop and return answer
    """
    should_continue = state.get("should_continue", False)
    trace_id = state.get("trace_id", "unknown")

    if should_continue:
        logger.info(
            f"[{trace_id}] Conditional routing: CONTINUE iteration "
            f"(current={state.get('current_iteration', 0)})"
        )
        return "refinement"
    else:
        logger.info(
            f"[{trace_id}] Conditional routing: STOP "
            f"(reason={state.get('stop_reason', 'unknown')})"
        )
        return "end"


# ============================================================================
# Workflow Construction
# ============================================================================

def create_merlt_workflow() -> StateGraph:
    """
    Build complete MERL-T workflow with LangGraph.

    Graph structure:
    START → router → retrieval → experts → synthesis → iteration
             ↑                                           ↓
             |                                      (decision)
             |                                           ↓
             +---- refinement <-- (if continue)
                                  ↓
                             (if stop) → END

    Returns:
        Compiled LangGraph StateGraph ready for execution
    """
    logger.info("Building MERL-T LangGraph workflow...")

    # Create graph
    workflow = StateGraph(MEGLTState)

    # Add all 6 nodes
    workflow.add_node("router", router_node)
    workflow.add_node("retrieval", retrieval_node)
    workflow.add_node("experts", experts_node)
    workflow.add_node("synthesis", synthesis_node)
    workflow.add_node("iteration", iteration_node)
    workflow.add_node("refinement", refinement_node)

    # Define linear edges (main flow)
    workflow.set_entry_point("router")
    workflow.add_edge("router", "retrieval")
    workflow.add_edge("retrieval", "experts")
    workflow.add_edge("experts", "synthesis")
    workflow.add_edge("synthesis", "iteration")

    # Conditional branching: Continue iteration or stop?
    workflow.add_conditional_edges(
        "iteration",
        should_iterate,
        {
            "refinement": "refinement",  # Continue → Refinement → Router
            "end": END                     # Stop → END
        }
    )

    # Loop back: Refinement → Router for next iteration
    workflow.add_edge("refinement", "router")

    # Compile
    app = workflow.compile()

    logger.info("MERL-T workflow compiled successfully")

    return app
