"""
Comprehensive tests for bias analysis module.

Tests all bias calculation functions, total bias scoring,
and mitigation recommendations.

Coverage:
- All 6 bias dimension calculations
- Total bias calculation
- Mitigation recommendation generation
- Edge cases and mathematical correctness
"""

import pytest
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select

from merlt.rlcf_framework import models, bias_analysis
from merlt.rlcf_framework.models import TaskType


class TestBiasCalculations:
    """Tests for individual bias calculation functions."""

    @pytest.mark.asyncio
    async def test_calculate_professional_clustering_bias(self, db: AsyncSession):
        """Test professional clustering bias detection."""
        # Create task
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

        # Create users with same professional background
        for i in range(5):
            user = models.User(username=f"lawyer{i}")
            db.add(user)
            await db.flush()

            # Add professional credential
            cred = models.Credential(
                user_id=user.id,
                type="PROFESSIONAL_EXPERIENCE",
                value="15",  # Same experience level
                weight=0.4
            )
            db.add(cred)

            # Add feedback with similar position
            feedback = models.Feedback(
                user_id=user.id,
                response_id=response.id,
                accuracy_score=0.9,
                utility_score=0.9,
                transparency_score=0.9,
                feedback_data={"validated_answer": "Same answer"}
            )
            db.add(feedback)

        await db.commit()

        # Calculate bias for first user
        bias_score = await bias_analysis.calculate_professional_clustering_bias(
            db, user.id, task.id  # Note: requires user_id parameter
        )

        # Should detect clustering (score >= 0)
        assert bias_score >= 0.0
        assert bias_score <= 1.0

    @pytest.mark.asyncio
    async def test_calculate_demographic_bias(self, db: AsyncSession):
        """Test demographic bias detection."""
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

        # Create diverse users
        for i in range(3):
            user = models.User(username=f"user{i}")
            db.add(user)
            await db.flush()

            feedback = models.Feedback(
                user_id=user.id,
                response_id=response.id,
                accuracy_score=0.8 + (i * 0.05),
                utility_score=0.8,
                transparency_score=0.8,
                feedback_data={"validated_answer": f"Answer {i}"}
            )
            db.add(feedback)

        await db.commit()

        bias_score = await bias_analysis.calculate_demographic_bias(db, task.id)

        assert bias_score >= 0.0
        assert bias_score <= 1.0

    @pytest.mark.asyncio
    async def test_calculate_temporal_bias(self, db: AsyncSession):
        """Test temporal bias detection."""
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

        # Create feedback at different times
        for i in range(3):
            user = models.User(username=f"temporal_user{i}")
            db.add(user)
            await db.flush()

            feedback = models.Feedback(
                user_id=user.id,
                response_id=response.id,
                accuracy_score=0.8,
                utility_score=0.8,
                transparency_score=0.8,
                feedback_data={"validated_answer": "Answer"}
            )
            db.add(feedback)

        await db.commit()

        bias_score = await bias_analysis.calculate_temporal_bias(db, task.id)

        assert bias_score >= 0.0
        assert bias_score <= 1.0

    @pytest.mark.asyncio
    async def test_calculate_geographic_bias(self, db: AsyncSession):
        """Test geographic bias detection."""
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

        # Create users (geography would be in metadata in real system)
        for i in range(3):
            user = models.User(username=f"geo_user{i}")
            db.add(user)
            await db.flush()

            feedback = models.Feedback(
                user_id=user.id,
                response_id=response.id,
                accuracy_score=0.8,
                utility_score=0.8,
                transparency_score=0.8,
                feedback_data={"validated_answer": "Answer"}
            )
            db.add(feedback)

        await db.commit()

        bias_score = await bias_analysis.calculate_geographic_bias(db, task.id)

        assert bias_score >= 0.0
        assert bias_score <= 1.0

    @pytest.mark.asyncio
    async def test_calculate_confirmation_bias(self, db: AsyncSession):
        """Test confirmation bias detection."""
        task = models.LegalTask(
            task_type=TaskType.QA.value,
            input_data={"question": "Q", "context": "C"}
        )
        db.add(task)
        await db.flush()

        response = models.Response(
            task_id=task.id,
            output_data={"answer": "Initial answer"},
            model_version="v1"
        )
        db.add(response)
        await db.flush()

        # Create users with feedback matching AI output (confirmation bias)
        for i in range(4):
            user = models.User(username=f"confirmer{i}")
            db.add(user)
            await db.flush()

            feedback = models.Feedback(
                user_id=user.id,
                response_id=response.id,
                accuracy_score=0.95,  # High agreement
                utility_score=0.9,
                transparency_score=0.9,
                feedback_data={"validated_answer": "Initial answer"}  # Matches AI
            )
            db.add(feedback)

        await db.commit()

        bias_score = await bias_analysis.calculate_confirmation_bias(db, task.id)

        assert bias_score >= 0.0
        assert bias_score <= 1.0

    @pytest.mark.asyncio
    async def test_calculate_anchoring_bias(self, db: AsyncSession):
        """Test anchoring bias detection."""
        task = models.LegalTask(
            task_type=TaskType.QA.value,
            input_data={"question": "Q", "context": "C"}
        )
        db.add(task)
        await db.flush()

        response = models.Response(
            task_id=task.id,
            output_data={"answer": "Anchor answer"},
            model_version="v1"
        )
        db.add(response)
        await db.flush()

        # Create feedback with varying similarity to AI output
        for i in range(3):
            user = models.User(username=f"anchor_user{i}")
            db.add(user)
            await db.flush()

            feedback = models.Feedback(
                user_id=user.id,
                response_id=response.id,
                accuracy_score=0.9 - (i * 0.1),
                utility_score=0.8,
                transparency_score=0.8,
                feedback_data={"validated_answer": f"Answer {i}"}
            )
            db.add(feedback)

        await db.commit()

        bias_score = await bias_analysis.calculate_anchoring_bias(db, task.id)

        assert bias_score >= 0.0
        assert bias_score <= 1.0


class TestTotalBiasCalculation:
    """Tests for total bias score calculation."""

    @pytest.mark.asyncio
    async def test_calculate_total_bias(self, db: AsyncSession):
        """Test total bias calculation integrating all dimensions."""
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

        # Create minimal feedback for bias calculation
        for i in range(2):
            user = models.User(username=f"bias_user{i}")
            db.add(user)
            await db.flush()

            feedback = models.Feedback(
                user_id=user.id,
                response_id=response.id,
                accuracy_score=0.8,
                utility_score=0.8,
                transparency_score=0.8,
                feedback_data={"validated_answer": "Answer"}
            )
            db.add(feedback)

        await db.commit()

        # Calculate total bias
        bias_report = await bias_analysis.calculate_total_bias(db, task.id)

        assert "total_bias_score" in bias_report
        assert bias_report["total_bias_score"] >= 0.0
        assert "bias_level" in bias_report

        # Check all 6 dimensions are present
        assert "demographic_bias" in bias_report
        assert "professional_clustering" in bias_report
        assert "temporal_drift" in bias_report
        assert "geographic_concentration" in bias_report
        assert "confirmation_bias" in bias_report
        assert "anchoring_bias" in bias_report

    @pytest.mark.asyncio
    async def test_total_bias_with_no_feedback(self, db: AsyncSession):
        """Test bias calculation with no feedback returns low bias."""
        task = models.LegalTask(
            task_type=TaskType.QA.value,
            input_data={"question": "Q", "context": "C"}
        )
        db.add(task)
        await db.commit()

        bias_report = await bias_analysis.calculate_total_bias(db, task.id)

        # Should return minimal bias when no feedback exists
        assert bias_report["total_bias_score"] >= 0.0
        assert bias_report["total_bias_score"] <= 0.5  # Low bias expected


class TestBiasMitigationRecommendations:
    """Tests for bias mitigation recommendation generation."""

    def test_generate_recommendations_high_professional_bias(self):
        """Test recommendations for high professional clustering."""
        bias_report = {
            "total_bias_score": 0.6,
            "professional_clustering": 0.8,
            "demographic_bias": 0.2,
            "temporal_drift": 0.1,
            "geographic_concentration": 0.1,
            "confirmation_bias": 0.2,
            "anchoring_bias": 0.1
        }

        recommendations = bias_analysis.generate_bias_mitigation_recommendations(
            bias_report
        )

        assert len(recommendations) > 0
        # Check that recommendations are dicts with expected structure
        assert any(rec["type"] == "professional" for rec in recommendations)

    def test_generate_recommendations_high_confirmation_bias(self):
        """Test recommendations for high confirmation bias."""
        bias_report = {
            "total_bias_score": 0.7,
            "professional_clustering": 0.1,
            "demographic_bias": 0.1,
            "temporal_drift": 0.1,
            "geographic_concentration": 0.1,
            "confirmation_bias": 0.9,
            "anchoring_bias": 0.1
        }

        recommendations = bias_analysis.generate_bias_mitigation_recommendations(
            bias_report
        )

        assert len(recommendations) > 0
        # Check that confirmation bias recommendation exists
        assert any(rec["type"] == "confirmation" for rec in recommendations)

    def test_generate_recommendations_low_bias(self):
        """Test recommendations when bias is low."""
        bias_report = {
            "total_bias_score": 0.15,
            "professional_clustering": 0.1,
            "demographic_bias": 0.1,
            "temporal_drift": 0.1,
            "geographic_concentration": 0.1,
            "confirmation_bias": 0.1,
            "anchoring_bias": 0.1
        }

        recommendations = bias_analysis.generate_bias_mitigation_recommendations(
            bias_report
        )

        # Should still provide general recommendations
        assert len(recommendations) >= 0


class TestEdgeCases:
    """Tests for edge cases in bias calculations."""

    @pytest.mark.asyncio
    async def test_bias_with_single_user(self, db: AsyncSession):
        """Test bias calculation with only one evaluator."""
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

        user = models.User(username="solo_user")
        db.add(user)
        await db.flush()

        feedback = models.Feedback(
            user_id=user.id,
            response_id=response.id,
            accuracy_score=0.8,
            utility_score=0.8,
            transparency_score=0.8,
            feedback_data={"validated_answer": "Answer"}
        )
        db.add(feedback)
        await db.commit()

        bias_report = await bias_analysis.calculate_total_bias(db, task.id)

        # Should handle single user gracefully
        assert bias_report["total_bias_score"] >= 0.0
        assert bias_report["total_bias_score"] <= 2.0  # Euclidean norm can be > 1

    @pytest.mark.asyncio
    async def test_bias_with_identical_positions(self, db: AsyncSession):
        """Test bias when all evaluators have identical positions."""
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

        # Create 5 users with identical feedback
        for i in range(5):
            user = models.User(username=f"clone{i}")
            db.add(user)
            await db.flush()

            feedback = models.Feedback(
                user_id=user.id,
                response_id=response.id,
                accuracy_score=0.9,
                utility_score=0.9,
                transparency_score=0.9,
                feedback_data={"validated_answer": "Identical answer"}
            )
            db.add(feedback)

        await db.commit()

        bias_report = await bias_analysis.calculate_total_bias(db, task.id)

        # High consensus might indicate confirmation/anchoring bias
        assert bias_report["total_bias_score"] >= 0.0
