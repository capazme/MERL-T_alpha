"""
Tests for Iteration Controller.

This module tests:
- IterationContext data models and state management
- Stopping criteria evaluation (all 6 conditions)
- Feedback integration (user and RLCF)
- IterationController workflow
- Refinement instructions generation
"""

import pytest
import uuid
from datetime import datetime
from typing import Dict, Any

from merlt.orchestration.iteration import (
    IterationContext,
    IterationController,
    UserFeedback,
    RLCFQualityScore,
    IterationMetrics,
    StoppingCriteria
)


# ============================================================================
# Fixtures
# ============================================================================

@pytest.fixture
def sample_query_context() -> Dict[str, Any]:
    """Sample query context for testing."""
    return {
        "intent": "legal_validity",
        "complexity": 0.7,
        "norm_references": ["Art. 1350 c.c."],
        "entities": {"contratto_type": "vendita", "oggetto": "immobile"}
    }


@pytest.fixture
def sample_execution_plan() -> Dict[str, Any]:
    """Sample execution plan."""
    return {
        "trace_id": "trace-123",
        "agents": [
            {"agent_type": "kg", "task_type": "expand_related_concepts"},
            {"agent_type": "vectordb", "search_pattern": "semantic"}
        ],
        "experts": ["literal_interpreter", "systemic_teleological"],
        "synthesis_mode": "convergent"
    }


@pytest.fixture
def sample_provisional_answer() -> Dict[str, Any]:
    """Sample provisional answer with metrics."""
    return {
        "trace_id": "trace-123",
        "final_answer": "Il contratto verbale è nullo per difetto di forma (Art. 1350 c.c.).",
        "synthesis_mode": "convergent",
        "confidence": 0.82,
        "consensus_level": 0.78,
        "experts_consulted": ["literal_interpreter", "systemic_teleological"],
        "provenance": []
    }


@pytest.fixture
def iteration_controller() -> IterationController:
    """IterationController with default config."""
    config = {
        "confidence_threshold": 0.85,
        "consensus_threshold": 0.80,
        "quality_threshold": 0.80,
        "user_rating_threshold": 4.0,
        "min_improvement_delta": 0.05,
        "convergence_window": 2
    }
    return IterationController(config=config)


# ============================================================================
# Test: IterationContext Model
# ============================================================================

def test_iteration_context_creation(sample_query_context):
    """Test IterationContext creation."""
    context = IterationContext(
        session_id="sess-123",
        trace_id="trace-123",
        original_query="Test query",
        query_context=sample_query_context,
        max_iterations=3
    )

    assert context.session_id == "sess-123"
    assert context.trace_id == "trace-123"
    assert context.original_query == "Test query"
    assert context.current_iteration == 1
    assert context.max_iterations == 3
    assert context.status == "PENDING"
    assert len(context.history) == 0


def test_iteration_context_add_history(
    sample_query_context,
    sample_execution_plan,
    sample_provisional_answer
):
    """Test adding iteration to history."""
    context = IterationContext(
        session_id="sess-123",
        trace_id="trace-123",
        original_query="Test query",
        query_context=sample_query_context
    )

    metrics = IterationMetrics(
        iteration_number=1,
        confidence=0.82,
        consensus_level=0.78,
        execution_time_ms=5420.0
    )

    context.add_history(
        execution_plan=sample_execution_plan,
        provisional_answer=sample_provisional_answer,
        metrics=metrics
    )

    assert len(context.history) == 1
    assert context.history[0].iteration_number == 1
    assert context.current_answer == sample_provisional_answer
    assert context.current_metrics == metrics


def test_iteration_context_add_user_feedback(sample_query_context):
    """Test adding user feedback."""
    context = IterationContext(
        session_id="sess-123",
        trace_id="trace-123",
        original_query="Test query",
        query_context=sample_query_context
    )

    feedback = UserFeedback(
        feedback_id="fb-123",
        iteration_number=1,
        quality_rating=3.5,
        missing_information=["Giurisprudenza recente"],
        suggested_improvements="Aggiungere casi recenti"
    )

    context.add_user_feedback(feedback)

    assert len(context.all_feedback) == 1
    assert context.all_feedback[0].quality_rating == 3.5


def test_iteration_context_add_rlcf_evaluation(sample_query_context):
    """Test adding RLCF evaluation."""
    context = IterationContext(
        session_id="sess-123",
        trace_id="trace-123",
        original_query="Test query",
        query_context=sample_query_context
    )

    rlcf_score = RLCFQualityScore(
        answer_id="trace-123",
        aggregated_score=0.85,
        consensus_level=0.88
    )

    context.add_rlcf_evaluation(rlcf_score)

    assert len(context.all_rlcf_scores) == 1
    assert context.all_rlcf_scores[0].aggregated_score == 0.85


# ============================================================================
# Test: Stopping Criteria - Individual Conditions
# ============================================================================

def test_stopping_criteria_max_iterations(iteration_controller, sample_query_context):
    """Test MAX_ITERATIONS stopping condition."""
    context = IterationContext(
        session_id="sess-123",
        trace_id="trace-123",
        original_query="Test query",
        query_context=sample_query_context,
        max_iterations=3
    )

    # Reach max iterations
    context.current_iteration = 3

    should_stop, reason = iteration_controller._evaluate_stopping_criteria(context)

    assert should_stop is True
    assert reason == "MAX_ITERATIONS_REACHED"


def test_stopping_criteria_high_confidence(
    iteration_controller,
    sample_query_context,
    sample_execution_plan,
    sample_provisional_answer
):
    """Test HIGH_CONFIDENCE stopping condition."""
    context = IterationContext(
        session_id="sess-123",
        trace_id="trace-123",
        original_query="Test query",
        query_context=sample_query_context
    )

    # Add iteration with high confidence + consensus
    metrics = IterationMetrics(
        iteration_number=1,
        confidence=0.90,  # Above 0.85 threshold
        consensus_level=0.85,  # Above 0.80 threshold
        execution_time_ms=5000.0
    )

    context.add_history(
        execution_plan=sample_execution_plan,
        provisional_answer=sample_provisional_answer,
        metrics=metrics
    )

    should_stop, reason = iteration_controller._evaluate_stopping_criteria(context)

    assert should_stop is True
    assert reason == "HIGH_CONFIDENCE_AND_CONSENSUS"


def test_stopping_criteria_rlcf_approved(
    iteration_controller,
    sample_query_context,
    sample_execution_plan,
    sample_provisional_answer
):
    """Test RLCF_APPROVED stopping condition."""
    context = IterationContext(
        session_id="sess-123",
        trace_id="trace-123",
        original_query="Test query",
        query_context=sample_query_context
    )

    # Add iteration with RLCF score above threshold
    metrics = IterationMetrics(
        iteration_number=1,
        confidence=0.75,
        consensus_level=0.70,
        rlcf_quality_score=0.85,  # Above 0.80 threshold
        execution_time_ms=5000.0
    )

    context.add_history(
        execution_plan=sample_execution_plan,
        provisional_answer=sample_provisional_answer,
        metrics=metrics
    )

    should_stop, reason = iteration_controller._evaluate_stopping_criteria(context)

    assert should_stop is True
    assert reason == "RLCF_QUALITY_APPROVED"


def test_stopping_criteria_user_satisfied(
    iteration_controller,
    sample_query_context,
    sample_execution_plan,
    sample_provisional_answer
):
    """Test USER_SATISFIED stopping condition."""
    context = IterationContext(
        session_id="sess-123",
        trace_id="trace-123",
        original_query="Test query",
        query_context=sample_query_context
    )

    # Add iteration with high user rating
    metrics = IterationMetrics(
        iteration_number=1,
        confidence=0.75,
        consensus_level=0.70,
        user_rating=4.5,  # Above 4.0 threshold
        execution_time_ms=5000.0
    )

    context.add_history(
        execution_plan=sample_execution_plan,
        provisional_answer=sample_provisional_answer,
        metrics=metrics
    )

    should_stop, reason = iteration_controller._evaluate_stopping_criteria(context)

    assert should_stop is True
    assert reason == "USER_SATISFIED"


def test_stopping_criteria_no_improvement(
    iteration_controller,
    sample_query_context,
    sample_execution_plan,
    sample_provisional_answer
):
    """Test NO_IMPROVEMENT stopping condition."""
    context = IterationContext(
        session_id="sess-123",
        trace_id="trace-123",
        original_query="Test query",
        query_context=sample_query_context
    )

    # Iteration 1: confidence=0.70, consensus=0.65
    metrics1 = IterationMetrics(
        iteration_number=1,
        confidence=0.70,
        consensus_level=0.65,
        execution_time_ms=5000.0
    )
    context.add_history(sample_execution_plan, sample_provisional_answer, metrics1)
    context.current_iteration = 2

    # Iteration 2: confidence=0.71, consensus=0.66 (improvement < 0.05)
    metrics2 = IterationMetrics(
        iteration_number=2,
        confidence=0.71,
        consensus_level=0.66,
        execution_time_ms=5000.0
    )
    context.add_history(sample_execution_plan, sample_provisional_answer, metrics2)

    should_stop, reason = iteration_controller._evaluate_stopping_criteria(context)

    assert should_stop is True
    assert reason == "NO_SIGNIFICANT_IMPROVEMENT"


def test_stopping_criteria_converged(
    iteration_controller,
    sample_query_context,
    sample_execution_plan,
    sample_provisional_answer
):
    """Test CONVERGED stopping condition."""
    context = IterationContext(
        session_id="sess-123",
        trace_id="trace-123",
        original_query="Test query",
        query_context=sample_query_context
    )

    # Iteration 1: confidence=0.75, consensus=0.70
    metrics1 = IterationMetrics(
        iteration_number=1,
        confidence=0.75,
        consensus_level=0.70,
        execution_time_ms=5000.0
    )
    context.add_history(sample_execution_plan, sample_provisional_answer, metrics1)
    context.current_iteration = 2

    # Iteration 2: confidence=0.76, consensus=0.71 (variance < 0.05)
    metrics2 = IterationMetrics(
        iteration_number=2,
        confidence=0.76,
        consensus_level=0.71,
        execution_time_ms=5000.0
    )
    context.add_history(sample_execution_plan, sample_provisional_answer, metrics2)

    should_stop, reason = iteration_controller._evaluate_stopping_criteria(context)

    # Should converge because variance < 0.05 over window=2
    assert should_stop is True
    assert reason == "METRICS_CONVERGED"


def test_stopping_criteria_continue(
    iteration_controller,
    sample_query_context,
    sample_execution_plan,
    sample_provisional_answer
):
    """Test CONTINUE condition (no stop criteria met)."""
    context = IterationContext(
        session_id="sess-123",
        trace_id="trace-123",
        original_query="Test query",
        query_context=sample_query_context,
        max_iterations=3
    )

    # Low confidence, low consensus, no RLCF, no user feedback
    metrics = IterationMetrics(
        iteration_number=1,
        confidence=0.65,  # Below 0.85
        consensus_level=0.60,  # Below 0.80
        execution_time_ms=5000.0
    )

    context.add_history(sample_execution_plan, sample_provisional_answer, metrics)

    should_stop, reason = iteration_controller._evaluate_stopping_criteria(context)

    assert should_stop is False
    assert reason == "CONTINUE_REFINEMENT"


# ============================================================================
# Test: Improvement Calculation
# ============================================================================

def test_calculate_improvement_positive(iteration_controller):
    """Test improvement calculation with positive delta."""
    context = IterationContext(
        session_id="sess-123",
        trace_id="trace-123",
        original_query="Test query",
        query_context={}
    )

    # Iteration 1
    metrics1 = IterationMetrics(
        iteration_number=1,
        confidence=0.70,
        consensus_level=0.65,
        execution_time_ms=5000.0
    )
    context.add_history({}, {}, metrics1)
    context.current_iteration = 2

    # Iteration 2 (improved)
    metrics2 = IterationMetrics(
        iteration_number=2,
        confidence=0.80,  # +0.10
        consensus_level=0.75,  # +0.10
        execution_time_ms=5000.0
    )
    context.add_history({}, {}, metrics2)

    improvement = iteration_controller._calculate_improvement(context)

    # Expected: (0.10 + 0.10) / 2 = 0.10
    assert improvement == pytest.approx(0.10, abs=0.001)


def test_calculate_improvement_negative(iteration_controller):
    """Test improvement calculation with negative delta (regression)."""
    context = IterationContext(
        session_id="sess-123",
        trace_id="trace-123",
        original_query="Test query",
        query_context={}
    )

    # Iteration 1
    metrics1 = IterationMetrics(
        iteration_number=1,
        confidence=0.80,
        consensus_level=0.75,
        execution_time_ms=5000.0
    )
    context.add_history({}, {}, metrics1)
    context.current_iteration = 2

    # Iteration 2 (regressed)
    metrics2 = IterationMetrics(
        iteration_number=2,
        confidence=0.75,  # -0.05
        consensus_level=0.70,  # -0.05
        execution_time_ms=5000.0
    )
    context.add_history({}, {}, metrics2)

    improvement = iteration_controller._calculate_improvement(context)

    # Expected: (-0.05 + -0.05) / 2 = -0.05
    assert improvement == pytest.approx(-0.05, abs=0.001)


# ============================================================================
# Test: Convergence Detection
# ============================================================================

def test_is_converged_true(iteration_controller):
    """Test convergence detection when metrics are stable."""
    context = IterationContext(
        session_id="sess-123",
        trace_id="trace-123",
        original_query="Test query",
        query_context={}
    )

    # Two iterations with very similar metrics
    metrics1 = IterationMetrics(
        iteration_number=1,
        confidence=0.75,
        consensus_level=0.70,
        execution_time_ms=5000.0
    )
    context.add_history({}, {}, metrics1)

    metrics2 = IterationMetrics(
        iteration_number=2,
        confidence=0.76,  # Variance: 0.01
        consensus_level=0.71,  # Variance: 0.01
        execution_time_ms=5000.0
    )
    context.add_history({}, {}, metrics2)

    is_converged = iteration_controller._is_converged(context)

    # Variance < 0.05 for both metrics
    assert is_converged is True


def test_is_converged_false(iteration_controller):
    """Test convergence detection when metrics vary."""
    context = IterationContext(
        session_id="sess-123",
        trace_id="trace-123",
        original_query="Test query",
        query_context={}
    )

    # Two iterations with different metrics
    metrics1 = IterationMetrics(
        iteration_number=1,
        confidence=0.70,
        consensus_level=0.65,
        execution_time_ms=5000.0
    )
    context.add_history({}, {}, metrics1)

    metrics2 = IterationMetrics(
        iteration_number=2,
        confidence=0.85,  # Variance: 0.15 > 0.05
        consensus_level=0.80,  # Variance: 0.15 > 0.05
        execution_time_ms=5000.0
    )
    context.add_history({}, {}, metrics2)

    is_converged = iteration_controller._is_converged(context)

    # Variance > 0.05 for both metrics
    assert is_converged is False


# ============================================================================
# Test: IterationController Workflow
# ============================================================================

@pytest.mark.asyncio
async def test_start_iteration_session(
    iteration_controller,
    sample_query_context
):
    """Test starting new iteration session."""
    context = await iteration_controller.start_iteration_session(
        query="È valido un contratto verbale?",
        query_context=sample_query_context,
        max_iterations=3
    )

    assert context.session_id.startswith("sess-")
    assert context.trace_id.startswith("trace-")
    assert context.original_query == "È valido un contratto verbale?"
    assert context.max_iterations == 3
    assert context.status == "PENDING"


@pytest.mark.asyncio
async def test_process_iteration(
    iteration_controller,
    sample_query_context,
    sample_execution_plan,
    sample_provisional_answer
):
    """Test processing single iteration."""
    context = await iteration_controller.start_iteration_session(
        query="Test query",
        query_context=sample_query_context
    )

    context = await iteration_controller.process_iteration(
        context=context,
        provisional_answer=sample_provisional_answer,
        execution_plan=sample_execution_plan,
        execution_time_ms=5420.0
    )

    assert context.status == "IN_PROGRESS"
    assert len(context.history) == 1
    assert context.current_answer == sample_provisional_answer
    assert context.current_metrics.confidence == 0.82


@pytest.mark.asyncio
async def test_should_continue_iteration_yes(
    iteration_controller,
    sample_query_context,
    sample_execution_plan,
    sample_provisional_answer
):
    """Test should_continue when criteria not met."""
    context = await iteration_controller.start_iteration_session(
        query="Test query",
        query_context=sample_query_context,
        max_iterations=3
    )

    # Process iteration with low confidence
    answer_low_confidence = {**sample_provisional_answer, "confidence": 0.65}
    context = await iteration_controller.process_iteration(
        context=context,
        provisional_answer=answer_low_confidence,
        execution_plan=sample_execution_plan,
        execution_time_ms=5000.0
    )

    should_continue, reason = await iteration_controller.should_continue_iteration(context)

    assert should_continue is True
    assert reason == "CONTINUE_REFINEMENT"


@pytest.mark.asyncio
async def test_should_continue_iteration_no(
    iteration_controller,
    sample_query_context,
    sample_execution_plan,
    sample_provisional_answer
):
    """Test should_continue when criteria met (high confidence)."""
    context = await iteration_controller.start_iteration_session(
        query="Test query",
        query_context=sample_query_context,
        max_iterations=3
    )

    # Process iteration with high confidence + consensus
    answer_high_confidence = {
        **sample_provisional_answer,
        "confidence": 0.90,
        "consensus_level": 0.85
    }
    context = await iteration_controller.process_iteration(
        context=context,
        provisional_answer=answer_high_confidence,
        execution_plan=sample_execution_plan,
        execution_time_ms=5000.0
    )

    should_continue, reason = await iteration_controller.should_continue_iteration(context)

    assert should_continue is False
    assert reason == "HIGH_CONFIDENCE_AND_CONSENSUS"


# ============================================================================
# Test: Feedback Integration
# ============================================================================

@pytest.mark.asyncio
async def test_incorporate_user_feedback(
    iteration_controller,
    sample_query_context,
    sample_execution_plan,
    sample_provisional_answer
):
    """Test incorporating user feedback."""
    context = await iteration_controller.start_iteration_session(
        query="Test query",
        query_context=sample_query_context
    )

    context = await iteration_controller.process_iteration(
        context, sample_provisional_answer, sample_execution_plan, 5000.0
    )

    feedback = UserFeedback(
        feedback_id="fb-123",
        iteration_number=1,
        quality_rating=3.5,
        missing_information=["Giurisprudenza recente"],
        suggested_improvements="Aggiungere casi recenti"
    )

    context = await iteration_controller.incorporate_user_feedback(context, feedback)

    assert len(context.all_feedback) == 1
    assert context.current_metrics.user_rating == 3.5


@pytest.mark.asyncio
async def test_evaluate_answer_quality_rlcf(
    iteration_controller,
    sample_query_context,
    sample_execution_plan,
    sample_provisional_answer
):
    """Test RLCF quality evaluation."""
    context = await iteration_controller.start_iteration_session(
        query="Test query",
        query_context=sample_query_context
    )

    context = await iteration_controller.process_iteration(
        context, sample_provisional_answer, sample_execution_plan, 5000.0
    )

    rlcf_score = await iteration_controller.evaluate_answer_quality_rlcf(
        context, sample_provisional_answer
    )

    assert isinstance(rlcf_score, RLCFQualityScore)
    assert 0.0 <= rlcf_score.aggregated_score <= 1.0
    assert len(context.all_rlcf_scores) == 1


# ============================================================================
# Test: Refinement Instructions
# ============================================================================

@pytest.mark.asyncio
async def test_generate_refinement_instructions(
    iteration_controller,
    sample_query_context,
    sample_execution_plan,
    sample_provisional_answer
):
    """Test refinement instructions generation."""
    context = await iteration_controller.start_iteration_session(
        query="Test query",
        query_context=sample_query_context
    )

    context = await iteration_controller.process_iteration(
        context, sample_provisional_answer, sample_execution_plan, 5000.0
    )

    # Add user feedback
    feedback = UserFeedback(
        feedback_id="fb-123",
        iteration_number=1,
        quality_rating=3.0,
        missing_information=["Eccezioni", "Casi recenti"],
        suggested_improvements="Analizzare eccezioni"
    )
    context = await iteration_controller.incorporate_user_feedback(context, feedback)

    # Generate instructions
    refinement_context = await iteration_controller.generate_refinement_instructions(context)

    assert "iteration_number" in refinement_context
    assert refinement_context["iteration_number"] == 2
    assert "user_feedback_summary" in refinement_context
    assert "Eccezioni" in refinement_context["user_feedback_summary"]
    assert "missing_information" in refinement_context
    assert "Eccezioni" in refinement_context["missing_information"]


# ============================================================================
# Test: Full Multi-Iteration Workflow
# ============================================================================

@pytest.mark.asyncio
async def test_full_iteration_workflow(
    iteration_controller,
    sample_query_context,
    sample_execution_plan
):
    """
    Test full multi-iteration workflow:
    1. Start session
    2. Iteration 1 (low confidence) → Continue
    3. User feedback → Refinement
    4. Iteration 2 (high confidence) → Stop
    """
    # 1. Start session
    context = await iteration_controller.start_iteration_session(
        query="È valido un contratto verbale?",
        query_context=sample_query_context,
        max_iterations=3
    )

    # 2. Iteration 1 (low confidence)
    answer_1 = {
        "trace_id": "trace-123",
        "final_answer": "Risposta iniziale...",
        "confidence": 0.70,
        "consensus_level": 0.65,
        "synthesis_mode": "convergent",
        "experts_consulted": ["literal_interpreter"]
    }

    context = await iteration_controller.process_iteration(
        context, answer_1, sample_execution_plan, 5000.0
    )

    # Check should continue
    should_continue, reason = await iteration_controller.should_continue_iteration(context)
    assert should_continue is True

    # 3. User feedback
    feedback = UserFeedback(
        feedback_id="fb-1",
        iteration_number=1,
        quality_rating=3.0,
        missing_information=["Ratio legis"],
        suggested_improvements="Spiegare ratio"
    )
    context = await iteration_controller.incorporate_user_feedback(context, feedback)

    # Generate refinement instructions
    refinement = await iteration_controller.generate_refinement_instructions(context)
    assert "Ratio legis" in str(refinement)

    # 4. Iteration 2 (high confidence after refinement)
    context.current_iteration = 2
    answer_2 = {
        "trace_id": "trace-123",
        "final_answer": "Risposta migliorata con ratio legis...",
        "confidence": 0.90,  # High confidence
        "consensus_level": 0.85,  # High consensus
        "synthesis_mode": "convergent",
        "experts_consulted": ["literal_interpreter", "systemic_teleological"]
    }

    context = await iteration_controller.process_iteration(
        context, answer_2, sample_execution_plan, 4500.0
    )

    # Check should stop
    should_continue, reason = await iteration_controller.should_continue_iteration(context)
    assert should_continue is False
    assert reason == "HIGH_CONFIDENCE_AND_CONSENSUS"

    # Verify final state
    assert len(context.history) == 2
    assert context.current_metrics.confidence == 0.90


# ============================================================================
# Test: Edge Cases
# ============================================================================

def test_stopping_criteria_first_iteration(iteration_controller, sample_query_context):
    """Test stopping criteria with no previous iterations."""
    context = IterationContext(
        session_id="sess-123",
        trace_id="trace-123",
        original_query="Test query",
        query_context=sample_query_context
    )

    # No history yet
    should_stop, reason = iteration_controller._evaluate_stopping_criteria(context)

    assert should_stop is False
    assert reason == "FIRST_ITERATION_PENDING"


def test_get_session_summary(
    iteration_controller,
    sample_query_context,
    sample_execution_plan,
    sample_provisional_answer
):
    """Test session summary generation."""
    context = IterationContext(
        session_id="sess-123",
        trace_id="trace-123",
        original_query="Test query",
        query_context=sample_query_context
    )

    metrics = IterationMetrics(
        iteration_number=1,
        confidence=0.82,
        consensus_level=0.78,
        execution_time_ms=5000.0
    )
    context.add_history(sample_execution_plan, sample_provisional_answer, metrics)

    summary = iteration_controller.get_session_summary(context)

    assert summary["session_id"] == "sess-123"
    assert summary["current_iteration"] == 1
    assert summary["current_confidence"] == 0.82
    assert summary["total_iterations"] == 1
