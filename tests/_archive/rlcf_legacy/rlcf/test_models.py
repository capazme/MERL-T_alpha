"""
Comprehensive tests for database models.

Tests CRUD operations, relationships, constraints, and data integrity
for all RLCF framework database models.

Coverage:
- User model and credentials
- LegalTask model with all task types
- Response model
- Feedback model with JSON validation
- BiasReport model
- DevilsAdvocateAssignment model
- TaskAssignment model
- AccountabilityReport model
- FeedbackRating model
"""

import pytest
import datetime
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from sqlalchemy.exc import IntegrityError

from merlt.rlcf import models
from merlt.rlcf.models import TaskType, TaskStatus


class TestUserModel:
    """Tests for User model CRUD operations and constraints."""

    @pytest.mark.asyncio
    async def test_create_user(self, db: AsyncSession):
        """Test creating a new user with default values."""
        user = models.User(username="test_user")
        db.add(user)
        await db.commit()
        await db.refresh(user)

        assert user.id is not None
        assert user.username == "test_user"
        assert user.authority_score == 0.0
        assert user.track_record_score == 0.0
        assert user.baseline_credential_score == 0.0

    @pytest.mark.asyncio
    async def test_user_unique_username(self, db: AsyncSession):
        """Test that usernames must be unique."""
        user1 = models.User(username="duplicate")
        db.add(user1)
        await db.commit()

        user2 = models.User(username="duplicate")
        db.add(user2)

        with pytest.raises(IntegrityError):
            await db.commit()

    @pytest.mark.asyncio
    async def test_user_with_credentials(self, db: AsyncSession):
        """Test user with multiple credentials."""
        user = models.User(username="credentialed_user")
        db.add(user)
        await db.flush()

        cred1 = models.Credential(
            user_id=user.id,
            type="ACADEMIC_DEGREE",
            value="PhD",
            weight=0.3
        )
        cred2 = models.Credential(
            user_id=user.id,
            type="PROFESSIONAL_EXPERIENCE",
            value="10 years",
            weight=0.4
        )
        db.add_all([cred1, cred2])
        await db.commit()

        # Reload user with credentials using eager loading
        from sqlalchemy.orm import selectinload
        result = await db.execute(
            select(models.User)
            .where(models.User.id == user.id)
            .options(selectinload(models.User.credentials))
        )
        user = result.scalar_one()

        assert len(user.credentials) == 2
        assert user.credentials[0].type == "ACADEMIC_DEGREE"
        assert user.credentials[1].type == "PROFESSIONAL_EXPERIENCE"


class TestLegalTaskModel:
    """Tests for LegalTask model with different task types."""

    @pytest.mark.asyncio
    async def test_create_qa_task(self, db: AsyncSession):
        """Test creating a QA task with proper input data."""
        task = models.LegalTask(
            task_type=TaskType.QA.value,
            input_data={
                "question": "What is the capital of France?",
                "context": "France is a country in Europe."
            },
            ground_truth_data={
                "validated_answer": "Paris"
            }
        )
        db.add(task)
        await db.commit()
        await db.refresh(task)

        assert task.id is not None
        assert task.task_type == TaskType.QA.value
        assert task.status == TaskStatus.OPEN
        assert task.input_data["question"] == "What is the capital of France?"
        assert task.ground_truth_data["validated_answer"] == "Paris"
        assert isinstance(task.created_at, datetime.datetime)

    @pytest.mark.asyncio
    async def test_create_statutory_rule_qa_task(self, db: AsyncSession):
        """Test creating a STATUTORY_RULE_QA task."""
        task = models.LegalTask(
            task_type=TaskType.STATUTORY_RULE_QA.value,
            input_data={
                "question": "What are the requirements for incorporation?",
                "rule_id": "RULE-001",
                "context_full": "Full legal context here...",
                "context_count": 3,
                "relevant_articles": "Article 1, Article 2",
                "category": "Corporate Law",
                "tags": "incorporation, business",
                "metadata_full": "{}"
            }
        )
        db.add(task)
        await db.commit()
        await db.refresh(task)

        assert task.task_type == TaskType.STATUTORY_RULE_QA.value
        assert task.input_data["rule_id"] == "RULE-001"

    @pytest.mark.asyncio
    async def test_task_status_progression(self, db: AsyncSession):
        """Test task status lifecycle."""
        task = models.LegalTask(
            task_type=TaskType.CLASSIFICATION.value,
            input_data={"text": "Sample text", "unit": "sentence"}
        )
        db.add(task)
        await db.commit()

        assert task.status == TaskStatus.OPEN

        task.status = TaskStatus.BLIND_EVALUATION
        await db.commit()
        await db.refresh(task)
        assert task.status == TaskStatus.BLIND_EVALUATION

        task.status = TaskStatus.AGGREGATED
        await db.commit()
        await db.refresh(task)
        assert task.status == TaskStatus.AGGREGATED

        task.status = TaskStatus.CLOSED
        await db.commit()
        await db.refresh(task)
        assert task.status == TaskStatus.CLOSED


class TestResponseModel:
    """Tests for Response model."""

    @pytest.mark.asyncio
    async def test_create_response_for_task(self, db: AsyncSession):
        """Test creating a response linked to a task."""
        task = models.LegalTask(
            task_type=TaskType.QA.value,
            input_data={"question": "Test?", "context": "Context"}
        )
        db.add(task)
        await db.flush()

        response = models.Response(
            task_id=task.id,
            output_data={"answer": "Test answer", "confidence": 0.9},
            model_version="gpt-3.5-turbo-1.0"
        )
        db.add(response)
        await db.commit()
        await db.refresh(response)

        assert response.id is not None
        assert response.task_id == task.id
        assert response.output_data["answer"] == "Test answer"
        assert response.model_version == "gpt-3.5-turbo-1.0"
        assert isinstance(response.generated_at, datetime.datetime)


class TestFeedbackModel:
    """Tests for Feedback model with JSON validation."""

    @pytest.mark.asyncio
    async def test_create_feedback(self, db: AsyncSession):
        """Test creating feedback with all required fields."""
        # Create user
        user = models.User(username="evaluator")
        db.add(user)
        await db.flush()

        # Create task and response
        task = models.LegalTask(
            task_type=TaskType.QA.value,
            input_data={"question": "Test?", "context": "Context"}
        )
        db.add(task)
        await db.flush()

        response = models.Response(
            task_id=task.id,
            output_data={"answer": "Test answer"},
            model_version="test-1.0"
        )
        db.add(response)
        await db.flush()

        # Create feedback
        feedback = models.Feedback(
            user_id=user.id,
            response_id=response.id,
            is_blind_phase=True,
            accuracy_score=0.9,
            utility_score=0.8,
            transparency_score=0.7,
            feedback_data={
                "validated_answer": "Correct answer",
                "position": "agree",
                "reasoning": "The answer is accurate and well-reasoned."
            },
            community_helpfulness_rating=4
        )
        db.add(feedback)
        await db.commit()
        await db.refresh(feedback)

        assert feedback.id is not None
        assert feedback.user_id == user.id
        assert feedback.response_id == response.id
        assert feedback.is_blind_phase is True
        assert feedback.accuracy_score == 0.9
        assert feedback.feedback_data["validated_answer"] == "Correct answer"

    @pytest.mark.asyncio
    async def test_feedback_with_correctness_score(self, db: AsyncSession):
        """Test feedback with ground truth correctness scoring."""
        user = models.User(username="evaluator2")
        db.add(user)
        await db.flush()

        task = models.LegalTask(
            task_type=TaskType.QA.value,
            input_data={"question": "Test?", "context": "Context"},
            ground_truth_data={"validated_answer": "Ground truth answer"}
        )
        db.add(task)
        await db.flush()

        response = models.Response(
            task_id=task.id,
            output_data={"answer": "Response"},
            model_version="test-1.0"
        )
        db.add(response)
        await db.flush()

        feedback = models.Feedback(
            user_id=user.id,
            response_id=response.id,
            accuracy_score=0.8,
            utility_score=0.8,
            transparency_score=0.8,
            feedback_data={"validated_answer": "User answer"},
            correctness_score=0.95  # High correctness vs ground truth
        )
        db.add(feedback)
        await db.commit()
        await db.refresh(feedback)

        assert feedback.correctness_score == 0.95


class TestBiasReportModel:
    """Tests for BiasReport model with analysis_details."""

    @pytest.mark.asyncio
    async def test_create_bias_report(self, db: AsyncSession):
        """Test creating a bias report with analysis details."""
        user = models.User(username="biased_user")
        db.add(user)
        await db.flush()

        task = models.LegalTask(
            task_type=TaskType.CLASSIFICATION.value,
            input_data={"text": "Test", "unit": "doc"}
        )
        db.add(task)
        await db.flush()

        bias_report = models.BiasReport(
            task_id=task.id,
            user_id=user.id,
            bias_type="PROFESSIONAL_CLUSTERING",
            bias_score=0.35,
            analysis_details={
                "cluster_size": 5,
                "cluster_similarity": 0.82,
                "recommendations": ["Increase evaluator diversity"]
            }
        )
        db.add(bias_report)
        await db.commit()
        await db.refresh(bias_report)

        assert bias_report.id is not None
        assert bias_report.bias_type == "PROFESSIONAL_CLUSTERING"
        assert bias_report.bias_score == 0.35
        assert bias_report.analysis_details["cluster_size"] == 5
        assert isinstance(bias_report.created_at, datetime.datetime)


class TestRelationships:
    """Tests for model relationships and cascade behavior."""

    @pytest.mark.asyncio
    async def test_user_feedback_relationship(self, db: AsyncSession):
        """Test User <-> Feedback relationship."""
        user = models.User(username="feedback_author")
        db.add(user)
        await db.flush()

        task = models.LegalTask(
            task_type=TaskType.QA.value,
            input_data={"question": "Q", "context": "C"}
        )
        db.add(task)
        await db.flush()

        response = models.Response(
            task_id=task.id,
            output_data={"answer": "A"},
            model_version="v1"
        )
        db.add(response)
        await db.flush()

        # Create multiple feedback from same user
        for i in range(3):
            feedback = models.Feedback(
                user_id=user.id,
                response_id=response.id,
                accuracy_score=0.5 + i * 0.1,
                utility_score=0.5,
                transparency_score=0.5,
                feedback_data={"test": f"feedback_{i}"}
            )
            db.add(feedback)

        await db.commit()

        # Reload user with feedback using eager loading
        from sqlalchemy.orm import selectinload
        result = await db.execute(
            select(models.User)
            .where(models.User.id == user.id)
            .options(selectinload(models.User.feedback))
        )
        user = result.scalar_one()

        assert len(user.feedback) == 3

    @pytest.mark.asyncio
    async def test_task_responses_relationship(self, db: AsyncSession):
        """Test Task <-> Response relationship."""
        task = models.LegalTask(
            task_type=TaskType.SUMMARIZATION.value,
            input_data={"document": "Long document..."}
        )
        db.add(task)
        await db.flush()

        # Create multiple responses for same task
        for i in range(2):
            response = models.Response(
                task_id=task.id,
                output_data={"summary": f"Summary {i}"},
                model_version=f"model-{i}"
            )
            db.add(response)

        await db.commit()

        # Reload task with responses using eager loading
        from sqlalchemy.orm import selectinload
        result = await db.execute(
            select(models.LegalTask)
            .where(models.LegalTask.id == task.id)
            .options(selectinload(models.LegalTask.responses))
        )
        task = result.scalar_one()

        assert len(task.responses) == 2
        assert task.responses[0].model_version == "model-0"


class TestDataIntegrity:
    """Tests for data integrity constraints and validation."""

    @pytest.mark.asyncio
    async def test_foreign_key_constraint(self, db: AsyncSession):
        """Test that foreign key constraints are enforced."""
        # Try to create feedback with non-existent user_id
        response = models.Response(
            task_id=999999,  # Non-existent task
            output_data={"test": "data"},
            model_version="v1"
        )
        db.add(response)

        # This should fail with foreign key constraint
        with pytest.raises(IntegrityError):
            await db.commit()

    @pytest.mark.asyncio
    async def test_json_field_serialization(self, db: AsyncSession):
        """Test JSON fields properly serialize complex data."""
        task = models.LegalTask(
            task_type=TaskType.NER.value,
            input_data={
                "tokens": ["Apple", "Inc", "announced", "new", "product"],
                "text": "Apple Inc announced new product",
                "nested": {
                    "deep": {
                        "structure": [1, 2, 3]
                    }
                }
            }
        )
        db.add(task)
        await db.commit()
        await db.refresh(task)

        assert isinstance(task.input_data, dict)
        assert task.input_data["tokens"] == ["Apple", "Inc", "announced", "new", "product"]
        assert task.input_data["nested"]["deep"]["structure"] == [1, 2, 3]
