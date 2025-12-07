"""
Comprehensive tests for export functionality.

Tests SFT and Preference formatters for all task types, ensuring
proper data transformation for fine-tuning dataset export.

Coverage:
- All 9 SFT formatters
- Preference formatters
- get_export_data() with filters
- Edge cases and error handling
"""

import pytest
from sqlalchemy.ext.asyncio import AsyncSession

from merlt.rlcf_framework import models, export_dataset
from merlt.rlcf_framework.models import TaskType


class TestSFTFormatters:
    """Tests for Supervised Fine-Tuning formatters."""

    @pytest.mark.asyncio
    async def test_format_sft_qa(self, db: AsyncSession):
        """Test QA task SFT formatting."""
        task = models.LegalTask(
            task_type=TaskType.QA.value,
            input_data={
                "question": "What is contract law?",
                "context": "Contract law governs agreements between parties."
            }
        )
        db.add(task)
        await db.flush()

        response = models.Response(
            task_id=task.id,
            output_data={"answer": "Contract law is..."},
            model_version="v1"
        )
        db.add(response)
        await db.flush()

        user = models.User(username="evaluator")
        db.add(user)
        await db.flush()

        feedback = models.Feedback(
            user_id=user.id,
            response_id=response.id,
            accuracy_score=0.9,
            utility_score=0.9,
            transparency_score=0.9,
            feedback_data={
                "validated_answer": "Contract law governs legally binding agreements."
            }
        )
        db.add(feedback)
        await db.commit()

        # Test formatter
        result = export_dataset.format_sft_qa(task, response, feedback)

        assert "instruction" in result
        assert "input" in result
        assert "output" in result
        assert result["input"] == "Contract law governs agreements between parties."
        assert result["output"] == "Contract law governs legally binding agreements."

    @pytest.mark.asyncio
    async def test_format_sft_classification(self, db: AsyncSession):
        """Test CLASSIFICATION task SFT formatting."""
        task = models.LegalTask(
            task_type=TaskType.CLASSIFICATION.value,
            input_data={
                "text": "This is a contract dispute case.",
                "unit": "document"
            }
        )
        db.add(task)
        await db.flush()

        response = models.Response(
            task_id=task.id,
            output_data={"labels": ["Contract Law"]},
            model_version="v1"
        )
        db.add(response)
        await db.flush()

        user = models.User(username="evaluator")
        db.add(user)
        await db.flush()

        feedback = models.Feedback(
            user_id=user.id,
            response_id=response.id,
            accuracy_score=0.9,
            utility_score=0.9,
            transparency_score=0.9,
            feedback_data={
                "validated_labels": ["Contract Law", "Dispute Resolution"]
            }
        )
        db.add(feedback)
        await db.commit()

        result = export_dataset.format_sft_classification(task, response, feedback)

        assert result["output"] == "Contract Law, Dispute Resolution"
        assert "document" in result["instruction"]

    @pytest.mark.asyncio
    async def test_format_sft_summarization(self, db: AsyncSession):
        """Test SUMMARIZATION task SFT formatting."""
        task = models.LegalTask(
            task_type=TaskType.SUMMARIZATION.value,
            input_data={
                "document": "Long legal document about property rights..."
            }
        )
        db.add(task)
        await db.flush()

        response = models.Response(
            task_id=task.id,
            output_data={"summary": "Summary about property rights"},
            model_version="v1"
        )
        db.add(response)
        await db.flush()

        user = models.User(username="evaluator")
        db.add(user)
        await db.flush()

        feedback = models.Feedback(
            user_id=user.id,
            response_id=response.id,
            accuracy_score=0.9,
            utility_score=0.9,
            transparency_score=0.9,
            feedback_data={
                "revised_summary": "Improved summary covering key property rights."
            }
        )
        db.add(feedback)
        await db.commit()

        result = export_dataset.format_sft_summarization(task, response, feedback)

        assert result["input"] == "Long legal document about property rights..."
        assert result["output"] == "Improved summary covering key property rights."

    @pytest.mark.asyncio
    async def test_format_sft_prediction(self, db: AsyncSession):
        """Test PREDICTION task SFT formatting."""
        task = models.LegalTask(
            task_type=TaskType.PREDICTION.value,
            input_data={
                "facts": "Defendant breached contract terms."
            }
        )
        db.add(task)
        await db.flush()

        response = models.Response(
            task_id=task.id,
            output_data={"outcome": "Plaintiff wins"},
            model_version="v1"
        )
        db.add(response)
        await db.flush()

        user = models.User(username="evaluator")
        db.add(user)
        await db.flush()

        feedback = models.Feedback(
            user_id=user.id,
            response_id=response.id,
            accuracy_score=0.9,
            utility_score=0.9,
            transparency_score=0.9,
            feedback_data={
                "chosen_outcome": "Plaintiff likely to prevail with damages"
            }
        )
        db.add(feedback)
        await db.commit()

        result = export_dataset.format_sft_prediction(task, response, feedback)

        assert result["input"] == "Defendant breached contract terms."
        assert result["output"] == "Plaintiff likely to prevail with damages"

    @pytest.mark.asyncio
    async def test_format_sft_nli(self, db: AsyncSession):
        """Test NLI task SFT formatting."""
        task = models.LegalTask(
            task_type=TaskType.NLI.value,
            input_data={
                "premise": "The contract is valid.",
                "hypothesis": "All parties agreed to terms."
            }
        )
        db.add(task)
        await db.flush()

        response = models.Response(
            task_id=task.id,
            output_data={"label": "entailment"},
            model_version="v1"
        )
        db.add(response)
        await db.flush()

        user = models.User(username="evaluator")
        db.add(user)
        await db.flush()

        feedback = models.Feedback(
            user_id=user.id,
            response_id=response.id,
            accuracy_score=0.9,
            utility_score=0.9,
            transparency_score=0.9,
            feedback_data={
                "chosen_label": "neutral"
            }
        )
        db.add(feedback)
        await db.commit()

        result = export_dataset.format_sft_nli(task, response, feedback)

        assert result["output"] == "neutral"
        assert "premise" in result["instruction"]

    @pytest.mark.asyncio
    async def test_format_sft_ner(self, db: AsyncSession):
        """Test NER task SFT formatting."""
        task = models.LegalTask(
            task_type=TaskType.NER.value,
            input_data={
                "tokens": ["Apple", "Inc", "filed", "lawsuit"],
                "text": "Apple Inc filed lawsuit"
            }
        )
        db.add(task)
        await db.flush()

        response = models.Response(
            task_id=task.id,
            output_data={"tags": ["B-ORG", "I-ORG", "O", "O"]},
            model_version="v1"
        )
        db.add(response)
        await db.flush()

        user = models.User(username="evaluator")
        db.add(user)
        await db.flush()

        feedback = models.Feedback(
            user_id=user.id,
            response_id=response.id,
            accuracy_score=0.9,
            utility_score=0.9,
            transparency_score=0.9,
            feedback_data={
                "validated_tags": ["B-ORG", "I-ORG", "O", "B-ACTION"]
            }
        )
        db.add(feedback)
        await db.commit()

        result = export_dataset.format_sft_ner(task, response, feedback)

        assert result["input"] == "Apple Inc filed lawsuit"
        assert result["output"] == "B-ORG I-ORG O B-ACTION"

    @pytest.mark.asyncio
    async def test_format_sft_drafting(self, db: AsyncSession):
        """Test DRAFTING task SFT formatting."""
        task = models.LegalTask(
            task_type=TaskType.DRAFTING.value,
            input_data={
                "source": "Original contract clause",
                "instruction": "Improve clarity",
                "task": "revise"
            }
        )
        db.add(task)
        await db.flush()

        response = models.Response(
            task_id=task.id,
            output_data={"target": "Revised clause"},
            model_version="v1"
        )
        db.add(response)
        await db.flush()

        user = models.User(username="evaluator")
        db.add(user)
        await db.flush()

        feedback = models.Feedback(
            user_id=user.id,
            response_id=response.id,
            accuracy_score=0.9,
            utility_score=0.9,
            transparency_score=0.9,
            feedback_data={
                "revised_target": "Clearly revised clause with legal precision"
            }
        )
        db.add(feedback)
        await db.commit()

        result = export_dataset.format_sft_drafting(task, response, feedback)

        assert result["input"] == "Original contract clause"
        assert result["output"] == "Clearly revised clause with legal precision"

    @pytest.mark.asyncio
    async def test_format_sft_risk_spotting(self, db: AsyncSession):
        """Test RISK_SPOTTING task SFT formatting."""
        task = models.LegalTask(
            task_type=TaskType.RISK_SPOTTING.value,
            input_data={
                "text": "Contract lacks termination clause"
            }
        )
        db.add(task)
        await db.flush()

        response = models.Response(
            task_id=task.id,
            output_data={"risks": ["Compliance"]},
            model_version="v1"
        )
        db.add(response)
        await db.flush()

        user = models.User(username="evaluator")
        db.add(user)
        await db.flush()

        feedback = models.Feedback(
            user_id=user.id,
            response_id=response.id,
            accuracy_score=0.9,
            utility_score=0.9,
            transparency_score=0.9,
            feedback_data={
                "validated_risk_labels": ["Compliance", "Legal Liability"],
                "validated_severity": 8
            }
        )
        db.add(feedback)
        await db.commit()

        result = export_dataset.format_sft_risk_spotting(task, response, feedback)

        assert "Compliance, Legal Liability" in result["output"]
        assert "Severity: 8" in result["output"]

    @pytest.mark.asyncio
    async def test_format_sft_doctrine_application(self, db: AsyncSession):
        """Test DOCTRINE_APPLICATION task SFT formatting."""
        task = models.LegalTask(
            task_type=TaskType.DOCTRINE_APPLICATION.value,
            input_data={
                "facts": "Party A breached fiduciary duty",
                "question": "What doctrine applies?"
            }
        )
        db.add(task)
        await db.flush()

        response = models.Response(
            task_id=task.id,
            output_data={"label": "Breach of Trust"},
            model_version="v1"
        )
        db.add(response)
        await db.flush()

        user = models.User(username="evaluator")
        db.add(user)
        await db.flush()

        feedback = models.Feedback(
            user_id=user.id,
            response_id=response.id,
            accuracy_score=0.9,
            utility_score=0.9,
            transparency_score=0.9,
            feedback_data={
                "chosen_label": "Fiduciary Duty Breach"
            }
        )
        db.add(feedback)
        await db.commit()

        result = export_dataset.format_sft_doctrine_application(task, response, feedback)

        assert result["input"] == "Party A breached fiduciary duty"
        assert result["output"] == "Fiduciary Duty Breach"


class TestPreferenceFormatters:
    """Tests for Preference (RLHF) formatters."""

    @pytest.mark.asyncio
    async def test_format_preference_drafting_better(self, db: AsyncSession):
        """Test preference formatting when revised is better."""
        task = models.LegalTask(
            task_type=TaskType.DRAFTING.value,
            input_data={
                "source": "Original text",
                "instruction": "Improve clarity",
                "task": "revise"
            }
        )
        db.add(task)
        await db.flush()

        response = models.Response(
            task_id=task.id,
            output_data={"target": "AI generated text"},
            model_version="v1"
        )
        db.add(response)
        await db.flush()

        user = models.User(username="evaluator")
        db.add(user)
        await db.flush()

        feedback = models.Feedback(
            user_id=user.id,
            response_id=response.id,
            accuracy_score=0.9,
            utility_score=0.9,
            transparency_score=0.9,
            feedback_data={
                "revised_target": "Human improved text",
                "rating": "better"
            }
        )
        db.add(feedback)
        await db.commit()

        result = export_dataset.format_preference_drafting(task, response, feedback)

        assert result is not None
        assert result["chosen"] == "Human improved text"
        assert result["rejected"] == "AI generated text"

    @pytest.mark.asyncio
    async def test_format_preference_drafting_worse(self, db: AsyncSession):
        """Test preference formatting when revised is worse."""
        task = models.LegalTask(
            task_type=TaskType.DRAFTING.value,
            input_data={
                "source": "Original text",
                "instruction": "Improve",
                "task": "revise"
            }
        )
        db.add(task)
        await db.flush()

        response = models.Response(
            task_id=task.id,
            output_data={"target": "AI generated text"},
            model_version="v1"
        )
        db.add(response)
        await db.flush()

        user = models.User(username="evaluator")
        db.add(user)
        await db.flush()

        feedback = models.Feedback(
            user_id=user.id,
            response_id=response.id,
            accuracy_score=0.5,
            utility_score=0.5,
            transparency_score=0.5,
            feedback_data={
                "revised_target": "Worse revision",
                "rating": "worse"
            }
        )
        db.add(feedback)
        await db.commit()

        result = export_dataset.format_preference_drafting(task, response, feedback)

        assert result is not None
        assert result["chosen"] == "AI generated text"
        assert result["rejected"] == "Worse revision"


class TestGetExportData:
    """Tests for get_export_data() function."""

    @pytest.mark.asyncio
    async def test_export_qa_tasks_sft(self, db: AsyncSession):
        """Test exporting QA tasks in SFT format."""
        # Create task with response and feedback
        task = models.LegalTask(
            task_type=TaskType.QA.value,
            input_data={"question": "Q1", "context": "C1"}
        )
        db.add(task)
        await db.flush()

        response = models.Response(
            task_id=task.id,
            output_data={"answer": "A1"},
            model_version="v1"
        )
        db.add(response)
        await db.flush()

        user = models.User(username="eval1")
        db.add(user)
        await db.flush()

        feedback = models.Feedback(
            user_id=user.id,
            response_id=response.id,
            accuracy_score=0.9,
            utility_score=0.9,
            transparency_score=0.9,
            feedback_data={"validated_answer": "Validated A1"}
        )
        db.add(feedback)
        await db.commit()

        # Export
        result = await export_dataset.get_export_data(db, TaskType.QA, "sft")

        assert len(result) == 1
        assert result[0]["output"] == "Validated A1"

    @pytest.mark.asyncio
    async def test_export_empty_dataset(self, db: AsyncSession):
        """Test exporting when no tasks exist."""
        result = await export_dataset.get_export_data(db, TaskType.QA, "sft")
        assert result == []

    @pytest.mark.asyncio
    async def test_export_task_without_response(self, db: AsyncSession):
        """Test exporting task without response is skipped."""
        task = models.LegalTask(
            task_type=TaskType.QA.value,
            input_data={"question": "Q", "context": "C"}
        )
        db.add(task)
        await db.commit()

        result = await export_dataset.get_export_data(db, TaskType.QA, "sft")
        assert result == []

    @pytest.mark.asyncio
    async def test_export_multiple_feedback_per_task(self, db: AsyncSession):
        """Test exporting creates one record per feedback."""
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

        # Create 3 users with 3 feedbacks
        for i in range(3):
            user = models.User(username=f"eval{i}")
            db.add(user)
            await db.flush()

            feedback = models.Feedback(
                user_id=user.id,
                response_id=response.id,
                accuracy_score=0.9,
                utility_score=0.9,
                transparency_score=0.9,
                feedback_data={"validated_answer": f"Answer {i}"}
            )
            db.add(feedback)

        await db.commit()

        result = await export_dataset.get_export_data(db, TaskType.QA, "sft")
        assert len(result) == 3
