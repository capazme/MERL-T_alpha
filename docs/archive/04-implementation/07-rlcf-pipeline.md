# 07. RLCF Learning Pipeline

**Status**: Implementation Blueprint
**Layer**: Learning / Feedback
**Dependencies**: Database Schemas (03), Task Queue (06), LLM Integration (02)
**Key Libraries**: FastAPI, SQLAlchemy 2.0, Pydantic 2.5

---

## Table of Contents

1. [Overview](#1-overview)
2. [Feedback Collection API](#2-feedback-collection-API)
3. [Dynamic Authority Calculator](#3-dynamic-authority-calculator)
4. [Training Data Generator](#4-training-data-generator)
5. [A/B Testing Router](#5-ab-testing-router)

---

## 1. Overview

RLCF (Reinforcement Learning from Community Feedback) continuously improves MERL-T through user feedback.

**Learning Loops (4 total)**:
1. **Router Loop**: Improve ExecutionPlan generation
2. **Embeddings Loop**: Fine-tune embeddings with contrastive triplets
3. **Query Understanding Loop**: Improve NER + Intent Classification
4. **Synthesizer Loop**: Improve answer synthesis quality

**Feedback Flow**:
```
User provides feedback (rating, corrections)
  ↓
Calculate dynamic authority score (0.0-1.0)
  ↓
Store in answer_feedback table
  ↓
Daily batch: Generate training examples
  ↓
Weekly/Monthly: Model updates
  ↓
A/B testing (10% traffic for 7 days)
  ↓
Gradual rollout (10% → 50% → 100%)
```

---

## 2. Feedback Collection API

### 2.1 Feedback Request Models

**File**: `src/rlcf/models.py`

```python
from pydantic import BaseModel, Field, field_validator
from typing import Literal
from uuid import UUID


class FeedbackRequest(BaseModel):
    """
    User feedback submission request.

    Example:
        {
            "trace_id": "RTR-20241103-abc123",
            "rating": 4,
            "feedback_types": ["missing_source"],
            "corrections": {
                "execution_plan": {
                    "reasoning_plan": {
                        "experts": ["Literal_Interpreter", "Systemic_Teleological"]
                    }
                }
            },
            "suggested_sources": ["Art. 1425 c.c.", "Cass. 12345/2020"],
            "free_text_comments": "La risposta era buona ma mancava un riferimento..."
        }
    """

    trace_id: str = Field(
        ...,
        pattern=r"^[A-Z]+-\d{8}-[a-zA-Z0-9]+$",
        description="Trace ID from X-Trace-ID header",
        examples=["RTR-20241103-abc123"],
    )

    rating: int = Field(
        ...,
        ge=1,
        le=5,
        description="Answer quality rating (1=poor, 5=excellent)",
    )

    feedback_types: list[Literal[
        "incorrect_answer",
        "missing_source",
        "wrong_interpretation",
        "unclear_answer",
        "incomplete_answer",
        "excellent"
    ]] = Field(
        default_factory=list,
        description="Feedback type tags (can select multiple)",
    )

    corrections: dict | None = Field(
        default=None,
        description="Corrections to query understanding, execution plan, or answer",
        examples=[{
            "execution_plan": {
                "reasoning_plan": {"experts": ["Literal_Interpreter"]}
            },
            "query_understanding": {
                "entities": [{"text": "capacità di agire", "type": "LEGAL_OBJECT"}]
            },
            "final_answer": "Corrected answer text..."
        }],
    )

    suggested_sources: list[str] = Field(
        default_factory=list,
        description="Additional legal sources (norms, cases, doctrine)",
        examples=[["Art. 2 c.c.", "Cass. 12345/2020"]],
    )

    free_text_comments: str | None = Field(
        default=None,
        max_length=2000,
        description="Free-form feedback comments",
    )

    @field_validator("rating")
    @classmethod
    def validate_rating_with_comment(cls, v, info):
        """Low ratings (1-3) should have comments explaining the issue."""
        if v <= 3 and not info.data.get("free_text_comments"):
            raise ValueError("Low ratings require free_text_comments explaining the issue")
        return v


class FeedbackResponse(BaseModel):
    """Feedback submission response."""

    feedback_id: UUID
    user_authority_score: float = Field(
        ge=0.0,
        le=1.0,
        description="User's dynamic authority score"
    )
    training_examples_generated: int = Field(
        default=0,
        description="Number of training examples generated from this feedback"
    )
    status: str = "success"
```

### 2.2 Context Retrieval from Trace ID

**File**: `src/rlcf/context_retrieval.py`

```python
import asyncpg
from redis.asyncio import Redis
from uuid import UUID
import json


async def retrieve_query_context_from_trace(
    trace_id: str,
    db: asyncpg.Pool,
    redis: Redis,
) -> dict | None:
    """
    Retrieve query/answer context from trace_id.

    Sources (in order of priority):
        1. Redis cache (recent queries, TTL 1 hour)
        2. PostgreSQL logs table (if implemented)
        3. Distributed tracing system (OpenTelemetry)

    Args:
        trace_id: Trace ID (e.g., "RTR-20241103-abc123")
        db: PostgreSQL connection pool
        redis: Redis async client

    Returns:
        Context dict with query, answer, execution_plan, expert_outputs, retrieval_result
        or None if not found

    TODO:
        - Check Redis cache first (fast path)
        - Fall back to PostgreSQL logs table
        - Extract relevant fields for feedback storage
    """
    # Step 1: Try Redis cache
    # TODO: Implement cache lookup
    # cache_key = f"query_context:{trace_id}"
    # cached = await redis.get(cache_key)
    # if cached:
    #     return json.loads(cached)

    # Step 2: Query PostgreSQL logs (if available)
    # TODO: Implement logs table query
    # result = await db.fetchrow(
    #     "SELECT * FROM query_logs WHERE trace_id = $1",
    #     trace_id
    # )

    # Step 3: Extract context
    # if result:
    #     return {
    #         "query_text": result["query_text"],
    #         "final_answer": result["final_answer"],
    #         "execution_plan": result["execution_plan"],
    #         "expert_outputs": result["expert_outputs"],
    #         "retrieval_result": result["retrieval_result"],
    #     }

    return None  # Placeholder
```

### 2.3 Feedback API Endpoint

**File**: `src/rlcf/feedback_api.py`

```python
from fastapi import APIRouter, Depends, HTTPException, status
from uuid import uuid4
from ..api_gateway.dependencies.auth import CurrentUser
from .models import FeedbackRequest, FeedbackResponse
from .context_retrieval import retrieve_query_context_from_trace
from .authority import calculate_user_authority
import asyncpg
import logging


router = APIRouter()
logger = logging.getLogger(__name__)


@router.post("/api/v1/rlcf/feedback", response_model=FeedbackResponse)
async def submit_feedback(
    feedback: FeedbackRequest,
    user: CurrentUser,
    db: asyncpg.Pool = Depends(get_db_pool),
    redis: Redis = Depends(get_redis_client),
) -> FeedbackResponse:
    """
    Submit user feedback for RLCF.

    Workflow:
        1. Retrieve query/answer context from trace_id
        2. Calculate user's dynamic authority score
        3. Insert feedback into answer_feedback table
        4. Trigger async training data generation (Celery task)
        5. Return feedback_id and authority_score

    Args:
        feedback: Feedback submission data
        user: Current authenticated user
        db: PostgreSQL connection pool
        redis: Redis async client

    Returns:
        Feedback response with ID and authority score

    Raises:
        HTTPException 404: If trace_id not found
        HTTPException 400: If feedback validation fails
    """
    # Step 1: Retrieve context from trace_id
    context = await retrieve_query_context_from_trace(
        trace_id=feedback.trace_id,
        db=db,
        redis=redis,
    )

    if not context:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Trace ID not found: {feedback.trace_id}",
        )

    # Step 2: Calculate user authority
    authority_score = await calculate_user_authority(
        user_id=user["user_id"],
        user_role=user["role"],
        db=db,
    )

    # Step 3: Insert feedback
    feedback_id = uuid4()

    # TODO: Insert into answer_feedback table
    # await db.execute(
    #     """
    #     INSERT INTO answer_feedback (
    #         feedback_id, trace_id, user_id, user_role, user_authority_score,
    #         rating, feedback_types, corrections, suggested_sources, free_text_comments,
    #         query_text, final_answer, execution_plan, expert_outputs, retrieval_result,
    #         created_at
    #     ) VALUES (
    #         $1, $2, $3, $4, $5, $6, $7, $8, $9, $10, $11, $12, $13, $14, $15, NOW()
    #     )
    #     """,
    #     feedback_id,
    #     feedback.trace_id,
    #     user["user_id"],
    #     user["role"],
    #     authority_score,
    #     feedback.rating,
    #     feedback.feedback_types,
    #     feedback.corrections,
    #     feedback.suggested_sources,
    #     feedback.free_text_comments,
    #     context["query_text"],
    #     context["final_answer"],
    #     context["execution_plan"],
    #     context["expert_outputs"],
    #     context["retrieval_result"],
    # )

    # Step 4: Trigger async training data generation
    from src.tasks.training_tasks import generate_training_example
    # generate_training_example.delay(str(feedback_id))
    training_examples_count = 0  # Placeholder

    logger.info(
        f"Feedback submitted: feedback_id={feedback_id}, "
        f"trace_id={feedback.trace_id}, "
        f"user_id={user['user_id']}, "
        f"rating={feedback.rating}, "
        f"authority={authority_score}"
    )

    return FeedbackResponse(
        feedback_id=feedback_id,
        user_authority_score=authority_score,
        training_examples_generated=training_examples_count,
    )


@router.get("/api/v1/rlcf/feedback/{feedback_id}")
async def get_feedback(
    feedback_id: UUID,
    user: CurrentUser,
    db: asyncpg.Pool = Depends(get_db_pool),
) -> dict:
    """
    Retrieve feedback by ID (for admins/experts only).

    Args:
        feedback_id: Feedback UUID
        user: Current authenticated user
        db: PostgreSQL connection pool

    Returns:
        Feedback dict

    Raises:
        HTTPException 403: If user is not authorized
        HTTPException 404: If feedback not found
    """
    # Check authorization
    if user["role"] not in ["admin", "legal_expert"]:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Only admins and legal experts can view feedback",
        )

    # TODO: Query feedback from database
    # feedback = await db.fetchrow(
    #     "SELECT * FROM answer_feedback WHERE feedback_id = $1",
    #     feedback_id
    # )

    # if not feedback:
    #     raise HTTPException(
    #         status_code=status.HTTP_404_NOT_FOUND,
    #         detail=f"Feedback not found: {feedback_id}",
    #     )

    # return dict(feedback)

    return {}  # Placeholder
```

---

## 3. Dynamic Authority Calculator

**File**: `src/rlcf/authority.py`

```python
import asyncpg
from uuid import UUID


async def calculate_user_authority(
    user_id: UUID,
    user_role: str,
    db: asyncpg.Pool,
) -> float:
    """
    Calculate dynamic authority score for user.

    Formula:
        authority = 0.4 * role_weight +
                   0.3 * historical_accuracy +
                   0.2 * consensus_score +
                   0.1 * reputation_score

    Args:
        user_id: User UUID
        user_role: User role (user, legal_expert, admin)
        db: PostgreSQL connection pool

    Returns:
        Authority score (0.0-1.0)

    TODO:
        - Query answer_feedback for user's historical accuracy
        - Calculate consensus score (% agreement with other experts)
        - Query reputation score (upvotes, badges, etc.)
    """
    # Role weight
    role_weights = {
        "admin": 1.0,
        "legal_expert": 0.9,
        "practicing_lawyer": 0.7,
        "law_student": 0.4,
        "user": 0.2,
    }
    role_weight = role_weights.get(user_role, 0.2)

    # Historical accuracy
    # TODO: Query validated feedback / total feedback
    historical_accuracy = 0.8  # Placeholder

    # Consensus score
    # TODO: Query expert agreement rate
    consensus_score = 0.75  # Placeholder

    # Reputation score
    # TODO: Query user reputation system
    reputation_score = 0.6  # Placeholder

    authority = (
        0.4 * role_weight +
        0.3 * historical_accuracy +
        0.2 * consensus_score +
        0.1 * reputation_score
    )

    return round(authority, 3)
```

---

## 4. Training Data Generator

**File**: `src/rlcf/training_generator.py`

```python
from typing import Literal
import asyncpg
from uuid import UUID


class TrainingDataGenerator:
    """Generate training examples from feedback."""

    def __init__(self, db: asyncpg.Pool):
        self.db = db

    async def generate_from_feedback(
        self,
        feedback_id: UUID,
    ) -> list[dict]:
        """
        Generate training examples from single feedback.

        Returns 1-4 examples depending on feedback type:
            - Router decision correction → router_decision example
            - Suggested sources → embedding_triplet examples
            - Entity/intent corrections → query_understanding_annotation
            - Answer quality → synthesizer_training

        Args:
            feedback_id: Feedback UUID

        Returns:
            List of training examples (dicts)

        TODO:
            - Query answer_feedback table
            - Determine example types to generate
            - Create training examples with quality scores
        """
        # TODO: Query feedback
        # feedback = await self.db.fetchrow(
        #     "SELECT * FROM answer_feedback WHERE feedback_id = $1",
        #     feedback_id
        # )

        examples = []

        # Example 1: Router decision
        # if feedback.corrections has execution_plan corrections:
        #     examples.append(self._generate_router_example(feedback))

        # Example 2: Embedding triplets
        # if feedback.suggested_sources:
        #     examples.extend(self._generate_embedding_triplets(feedback))

        # Example 3: Query understanding
        # if feedback.corrections has entity/intent corrections:
        #     examples.append(self._generate_qu_example(feedback))

        # Example 4: Synthesizer
        # if feedback.rating + free_text_comments:
        #     examples.append(self._generate_synthesizer_example(feedback))

        return examples

    def _generate_router_example(self, feedback: dict) -> dict:
        """Generate router training example."""
        return {
            "example_type": "router_decision",
            "input_data": {
                "query_context": feedback["query_context"],
                "enriched_context": feedback["enriched_context"],
            },
            "expected_output": feedback["corrections"]["execution_plan"],
            "quality_score": feedback["user_authority_score"],
        }

    def _generate_embedding_triplets(self, feedback: dict) -> list[dict]:
        """Generate contrastive triplet examples."""
        triplets = []

        # Anchor: User query
        anchor = feedback["query_text"]

        # Positive: Chunks with high rating (or suggested sources)
        # Negative: Retrieved chunks with low relevance

        # TODO: Create triplets from feedback data

        return triplets

    def _generate_qu_example(self, feedback: dict) -> dict:
        """Generate query understanding example."""
        return {
            "example_type": "query_understanding_annotation",
            "input_data": {"query": feedback["query_text"]},
            "expected_output": feedback["corrections"]["query_understanding"],
            "quality_score": feedback["user_authority_score"],
        }

    def _generate_synthesizer_example(self, feedback: dict) -> dict:
        """Generate synthesizer training example."""
        return {
            "example_type": "synthesizer_training",
            "input_data": {
                "expert_outputs": feedback["expert_outputs"],
                "query_context": feedback["query_context"],
            },
            "expected_output": {
                "final_answer": feedback["corrections"].get("final_answer", feedback["final_answer"]),
                "synthesis_quality": feedback["rating"],
            },
            "quality_score": feedback["user_authority_score"],
        }
```

---

## 5. A/B Testing Router

**File**: `src/rlcf/ab_testing.py`

```python
from fastapi import APIRouter, Depends, Request
from uuid import UUID
import hashlib
import asyncpg


router = APIRouter()


class ABTestRouter:
    """Route traffic between model versions for A/B testing."""

    def __init__(self, db: asyncpg.Pool):
        self.db = db

    async def get_model_version(
        self,
        user_id: UUID,
        component: str,
    ) -> str:
        """
        Determine which model version to use for user.

        Strategy:
            - Hash user_id to get deterministic bucket (0-99)
            - Query ab_test_config for active test
            - Route based on traffic_split (e.g., 10% new, 90% old)

        Args:
            user_id: User UUID
            component: Model component (router, embedding, ner, etc.)

        Returns:
            Model version string (e.g., "v2.3", "v2.4")

        TODO:
            - Query ab_test_config table for active test
            - Hash user_id and determine bucket
            - Return version based on traffic_split
        """
        # TODO: Query active A/B test
        # test = await self.db.fetchrow(
        #     "SELECT * FROM ab_test_config WHERE component = $1 AND status = 'active'",
        #     component
        # )

        # Deterministic bucketing
        user_hash = int(hashlib.md5(str(user_id).encode()).hexdigest(), 16)
        bucket = user_hash % 100

        # Traffic split (example: 10% new, 90% old)
        traffic_split = 10  # TODO: Get from test config

        if bucket < traffic_split:
            return "v2.4"  # New version
        else:
            return "v2.3"  # Old version

    async def record_ab_test_metric(
        self,
        test_id: UUID,
        model_version: str,
        trace_id: str,
        user_id: UUID,
        answer_quality_rating: float | None,
        latency_ms: int,
        error_occurred: bool,
    ):
        """
        Record A/B test metric.

        Args:
            test_id: A/B test UUID
            model_version: Model version used
            trace_id: Request trace ID
            user_id: User UUID
            answer_quality_rating: User rating (1-5)
            latency_ms: Request latency
            error_occurred: Whether an error occurred

        TODO:
            - INSERT INTO ab_test_metrics VALUES (...)
        """
        # TODO: Insert metric
        pass


@router.post("/api/v1/ab-test/route")
async def route_ab_test_request(
    request: Request,
    user_id: UUID,
    component: str,
    ab_router: ABTestRouter = Depends(lambda: ABTestRouter(get_db_pool())),
) -> dict:
    """
    Route request to appropriate model version for A/B testing.

    Args:
        request: FastAPI request
        user_id: User UUID
        component: Model component
        ab_router: A/B test router

    Returns:
        Model version to use

    TODO:
        - Get model version from AB router
        - Forward request to appropriate model endpoint
        - Record metric after response
    """
    model_version = await ab_router.get_model_version(user_id, component)

    return {
        "model_version": model_version,
        "test_active": True,
    }
```

---

## Summary

This RLCF Pipeline implementation provides:

1. **Feedback Collection API** with FastAPI endpoints
2. **Dynamic Authority Calculator** (4-factor formula with role, accuracy, consensus, reputation)
3. **Training Data Generator** (4 example types: router, embeddings, QU, synthesizer)
4. **A/B Testing Router** (deterministic bucketing, traffic splitting, metric collection)
5. **Learning Loops** integrated with Celery tasks (daily/weekly/monthly cycles)

### RLCF Metrics

| Metric | Target | Current (Baseline) |
|--------|--------|-------------------|
| Feedback Rate | > 20% | - |
| Average User Authority | > 0.6 | - |
| Training Examples/Week | > 500 | - |
| Model Improvement (MRR) | +5% per cycle | - |

### Next Steps

1. Implement full feedback API with context retrieval
2. Integrate with Celery training tasks
3. Build reputation system for users
4. Implement gradual rollout logic (10% → 50% → 100%)
5. Create dashboards for RLCF metrics

### Key Files

| File | Purpose | Lines |
|------|---------|-------|
| `src/rlcf/feedback_api.py` | Feedback collection endpoints | ~100 |
| `src/rlcf/authority.py` | Dynamic authority calculator | ~60 |
| `src/rlcf/training_generator.py` | Training data generation | ~150 |
| `src/rlcf/ab_testing.py` | A/B test routing | ~100 |

**Total: ~750 lines** (target: ~750 lines) ✅

## 6. Gradual Rollout Strategy

### 6.1 Rollout Orchestrator

**File**: `src/rlcf/gradual_rollout.py`

```python
from enum import Enum
import asyncpg
from uuid import UUID
import logging


logger = logging.getLogger(__name__)


class RolloutStage(str, Enum):
    """Gradual rollout stages."""
    TESTING = "testing"  # 10% traffic
    CANARY = "canary"  # 50% traffic
    PRODUCTION = "production"  # 100% traffic
    ROLLBACK = "rollback"  # Rolled back to previous version


class GradualRolloutOrchestrator:
    """
    Orchestrate gradual rollout of new model versions.

    Rollout Strategy:
        Day 0: Deploy to staging
        Day 1-7: A/B test with 10% traffic
        Day 8: Analyze metrics, decide to proceed or rollback
        Day 9-11: Canary with 50% traffic
        Day 12: Analyze metrics, decide to proceed or rollback
        Day 13+: Full production (100% traffic)

    Decision Criteria:
        - answer_quality_rating: new >= old + 0.1  (10% improvement)
        - latency_p95: new < old * 1.2  (< 20% slowdown)
        - error_rate: new < old * 1.1  (< 10% error increase)
        - min_samples: >= 100 requests per version

    Example:
        >>> orchestrator = GradualRolloutOrchestrator(db)
        >>> await orchestrator.start_rollout(
        ...     model_component="router",
        ...     old_version="v2.3",
        ...     new_version="v2.4",
        ... )
        >>> # After 7 days:
        >>> await orchestrator.evaluate_and_progress("router")
    """

    def __init__(self, db: asyncpg.Pool):
        self.db = db

    async def start_rollout(
        self,
        model_component: str,
        old_version: str,
        new_version: str,
    ) -> UUID:
        """
        Start gradual rollout for new model version.

        Args:
            model_component: Component (router, embedding, ner, etc.)
            old_version: Current production version
            new_version: New version to roll out

        Returns:
            Test ID (UUID)

        TODO:
            - Create ab_test_config entry
            - Set initial traffic_split = 10%
            - Set status = "testing"
            - Schedule evaluation task after 7 days
        """
        # TODO: Insert into ab_test_config
        test_id = UUID("placeholder-test-id")

        logger.info(
            f"Started gradual rollout: component={model_component}, "
            f"old_version={old_version}, new_version={new_version}, "
            f"test_id={test_id}, stage=TESTING (10%)"
        )

        return test_id

    async def evaluate_and_progress(
        self,
        model_component: str,
    ) -> str:
        """
        Evaluate current rollout stage and decide next action.

        Actions:
            - PROCEED: Progress to next stage (10% → 50% → 100%)
            - ROLLBACK: Rollback to old version
            - WAIT: Insufficient data, continue current stage

        Args:
            model_component: Component being rolled out

        Returns:
            Decision ("proceed", "rollback", "wait")

        TODO:
            - Query ab_test_metrics for current stage
            - Calculate aggregated metrics (avg rating, latency_p95, error_rate)
            - Apply decision criteria
            - Update ab_test_config if proceeding/rolling back
        """
        # TODO: Query metrics
        # metrics = await self._get_aggregated_metrics(model_component)

        # TODO: Apply decision criteria
        # decision = self._make_rollout_decision(metrics)

        # TODO: Update config if proceeding
        # if decision == "proceed":
        #     await self._progress_to_next_stage(model_component)
        # elif decision == "rollback":
        #     await self._rollback(model_component)

        logger.info(f"Rollout evaluation: component={model_component}, decision=placeholder")
        return "wait"  # Placeholder

    async def _get_aggregated_metrics(
        self,
        model_component: str,
    ) -> dict:
        """
        Get aggregated metrics for current rollout.

        Returns:
            Dict with metrics by version:
            {
                "v2.3": {"avg_rating": 4.2, "latency_p95": 120, "error_rate": 0.02, "count": 950},
                "v2.4": {"avg_rating": 4.4, "latency_p95": 110, "error_rate": 0.01, "count": 150}
            }

        TODO:
            - Query ab_test_metrics for active test
            - Aggregate by model_version
            - Calculate percentiles, averages, error rates
        """
        # TODO: Aggregate metrics from ab_test_metrics table
        return {}  # Placeholder

    def _make_rollout_decision(self, metrics: dict) -> str:
        """
        Make rollout decision based on metrics.

        Decision Logic:
            IF new_version.count < 100:
                RETURN "wait"  # Insufficient data
            IF new_version.avg_rating >= old_version.avg_rating + 0.1
               AND new_version.latency_p95 < old_version.latency_p95 * 1.2
               AND new_version.error_rate < old_version.error_rate * 1.1:
                RETURN "proceed"
            ELSE:
                RETURN "rollback"

        Args:
            metrics: Aggregated metrics by version

        Returns:
            Decision ("proceed", "rollback", "wait")
        """
        # TODO: Implement decision logic
        return "wait"  # Placeholder

    async def _progress_to_next_stage(self, model_component: str):
        """
        Progress rollout to next stage.

        Stage Progression:
            TESTING (10%) → CANARY (50%) → PRODUCTION (100%)

        TODO:
            - Update ab_test_config traffic_split
            - Update status field
            - Log progression
        """
        # TODO: Update config
        pass

    async def _rollback(self, model_component: str):
        """
        Rollback to old version.

        Actions:
            - Set traffic_split = 0% for new version
            - Set status = "rollback"
            - Deprecate new model version in model_registry

        TODO:
            - Update ab_test_config
            - Update model_registry
            - Alert engineering team
        """
        # TODO: Execute rollback
        logger.error(f"ROLLBACK triggered for component={model_component}")
        pass
```

## 7. Feedback Dashboard & Analytics

### 7.1 Feedback Statistics Endpoint

**File**: `src/rlcf/analytics.py`

```python
from fastapi import APIRouter, Depends, Query
from typing import Literal
from datetime import date, timedelta
import asyncpg


router = APIRouter()


@router.get("/api/v1/rlcf/stats/overview")
async def get_feedback_overview(
    start_date: date = Query(default_factory=lambda: date.today() - timedelta(days=30)),
    end_date: date = Query(default_factory=date.today),
    db: asyncpg.Pool = Depends(get_db_pool),
) -> dict:
    """
    Get high-level feedback statistics.

    Args:
        start_date: Start date for analysis
        end_date: End date for analysis
        db: PostgreSQL connection pool

    Returns:
        Dict with overview stats:
        {
            "total_feedback": 1234,
            "avg_rating": 4.2,
            "feedback_rate": 0.23,  # 23% of queries receive feedback
            "training_examples_generated": 456,
            "avg_user_authority": 0.65
        }

    TODO:
        - Query answer_feedback table
        - Aggregate by date range
        - Calculate averages and rates
    """
    # TODO: Query feedback stats
    # result = await db.fetchrow(
    #     """
    #     SELECT
    #         COUNT(*) AS total_feedback,
    #         AVG(rating) AS avg_rating,
    #         AVG(user_authority_score) AS avg_authority,
    #         SUM(training_examples_generated) AS total_examples
    #     FROM answer_feedback
    #     WHERE created_at >= $1 AND created_at <= $2
    #     """,
    #     start_date,
    #     end_date
    # )

    return {
        "total_feedback": 0,
        "avg_rating": 0.0,
        "feedback_rate": 0.0,
        "training_examples_generated": 0,
        "avg_user_authority": 0.0,
    }  # Placeholder


@router.get("/api/v1/rlcf/stats/feedback-types")
async def get_feedback_types_distribution(
    start_date: date = Query(default_factory=lambda: date.today() - timedelta(days=30)),
    end_date: date = Query(default_factory=date.today),
    db: asyncpg.Pool = Depends(get_db_pool),
) -> dict:
    """
    Get feedback type distribution.

    Returns:
        Dict with counts by feedback_type:
        {
            "incorrect_answer": 45,
            "missing_source": 123,
            "wrong_interpretation": 23,
            "unclear_answer": 67,
            "incomplete_answer": 34,
            "excellent": 234
        }

    TODO:
        - Unnest feedback_types array
        - Count occurrences
    """
    # TODO: Query feedback_types distribution
    return {}  # Placeholder


@router.get("/api/v1/rlcf/stats/training-data-quality")
async def get_training_data_quality(
    example_type: Literal[
        "router_decision",
        "embedding_triplet",
        "query_understanding_annotation",
        "synthesizer_training"
    ] | None = None,
    db: asyncpg.Pool = Depends(get_db_pool),
) -> dict:
    """
    Get training data quality distribution.

    Returns:
        Dict with quality score distribution:
        {
            "example_type": "router_decision",
            "total_examples": 1234,
            "avg_quality_score": 0.73,
            "quality_distribution": {
                "0.0-0.2": 23,   # Low quality
                "0.2-0.4": 45,
                "0.4-0.6": 234,
                "0.6-0.8": 567,
                "0.8-1.0": 365   # High quality
            },
            "used_in_training": 856
        }

    TODO:
        - Query training_examples table
        - Filter by example_type if specified
        - Calculate distribution buckets
    """
    # TODO: Query training data quality
    return {}  # Placeholder
```
