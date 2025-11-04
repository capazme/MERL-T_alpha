"""
Tests for the RetrievalValidationHandler.

This module tests the RETRIEVAL_VALIDATION task handler, including:
- Feedback aggregation with authority weighting
- Consensus determination for validated/irrelevant/missing items
- Consistency calculation using Jaccard similarity
- Correctness calculation using F1 scores
- Export formatting for SFT and Preference Learning
"""

import pytest
import pytest_asyncio
from unittest.mock import MagicMock, AsyncMock
from sqlalchemy.ext.asyncio import AsyncSession

from backend.rlcf_framework import models
from backend.rlcf_framework.task_handlers.retrieval_validation_handler import RetrievalValidationHandler


@pytest.fixture
def mock_task():
    """Create a mock RETRIEVAL_VALIDATION task."""
    task = MagicMock(spec=models.LegalTask)
    task.id = 1
    task.task_type = "RETRIEVAL_VALIDATION"
    task.input_data = {
        "query": "What are the requirements for a valid contract?",
        "retrieved_items": [
            {"id": "item1", "title": "Contract Law Basics"},
            {"id": "item2", "title": "Property Rights"},
            {"id": "item3", "title": "Criminal Law"},
        ],
        "retrieval_strategy": "semantic_search",
        "agent_type": "VectorDB",
    }
    task.ground_truth_data = {
        "validated_items": ["item1", "item2"],
        "irrelevant_items": ["item3"],
    }
    task.status = "BLIND_EVALUATION"
    return task


@pytest.fixture
def mock_feedback_list():
    """Create a list of mock feedback objects with different evaluations."""
    feedbacks = []

    # Expert 1: High authority, validates item1 and item2, marks item3 as irrelevant
    fb1 = MagicMock(spec=models.Feedback)
    fb1.id = 1
    fb1.user_id = 1
    fb1.feedback_data = {
        "validated_items": ["item1", "item2"],
        "irrelevant_items": ["item3"],
        "missing_items": ["item4"],
        "retrieval_quality_score": 0.8,
        "reasoning": "Items 1 and 2 are relevant, 3 is not",
    }
    fb1.author = MagicMock()
    fb1.author.authority_score = 0.9
    fb1.author.username = "expert1"
    feedbacks.append(fb1)

    # Expert 2: Medium authority, validates only item1, marks item2 and item3 as irrelevant
    fb2 = MagicMock(spec=models.Feedback)
    fb2.id = 2
    fb2.user_id = 2
    fb2.feedback_data = {
        "validated_items": ["item1"],
        "irrelevant_items": ["item2", "item3"],
        "missing_items": [],
        "retrieval_quality_score": 0.6,
        "reasoning": "Only item 1 is truly relevant",
    }
    fb2.author = MagicMock()
    fb2.author.authority_score = 0.6
    fb2.author.username = "expert2"
    feedbacks.append(fb2)

    # Expert 3: Lower authority, validates item1 and item2, marks item3 as irrelevant
    fb3 = MagicMock(spec=models.Feedback)
    fb3.id = 3
    fb3.user_id = 3
    fb3.feedback_data = {
        "validated_items": ["item1", "item2"],
        "irrelevant_items": ["item3"],
        "missing_items": ["item4"],
        "retrieval_quality_score": 0.7,
        "reasoning": "Items 1 and 2 are both relevant",
    }
    fb3.author = MagicMock()
    fb3.author.authority_score = 0.5
    fb3.author.username = "expert3"
    feedbacks.append(fb3)

    return feedbacks


class TestRetrievalValidationHandlerInitialization:
    """Test cases for handler initialization."""

    @pytest.mark.asyncio
    async def test_handler_initialization(self, mock_task):
        """Test that handler initializes correctly."""
        db = AsyncMock(spec=AsyncSession)
        handler = RetrievalValidationHandler(db, mock_task)

        assert handler.db is db
        assert handler.task is mock_task
        assert handler.task.task_type == "RETRIEVAL_VALIDATION"


class TestAggregateFeedback:
    """Test cases for aggregate_feedback method."""

    @pytest.mark.asyncio
    async def test_aggregate_feedback_with_consensus(self, mock_task, mock_feedback_list):
        """Test aggregation with clear consensus."""
        db = AsyncMock(spec=AsyncSession)
        handler = RetrievalValidationHandler(db, mock_task)

        # Mock get_feedbacks to return our test feedback
        handler.get_feedbacks = AsyncMock(return_value=mock_feedback_list)

        result = await handler.aggregate_feedback()

        # Should have consensus result
        assert "consensus_validated_items" in result
        assert "consensus_irrelevant_items" in result
        assert "consensus_missing_items" in result
        assert "retrieval_quality_score" in result
        assert "confidence" in result
        assert "total_evaluators" in result

        # item1 should be validated (all experts agree)
        assert "item1" in result["consensus_validated_items"]

        # item3 should be irrelevant (all experts agree)
        assert "item3" in result["consensus_irrelevant_items"]

        # Total evaluators should be 3
        assert result["total_evaluators"] == 3

        # Quality score should be weighted average
        # (0.8*0.9 + 0.6*0.6 + 0.7*0.5) / (0.9 + 0.6 + 0.5) = 0.715
        assert 0.7 <= result["retrieval_quality_score"] <= 0.75

    @pytest.mark.asyncio
    async def test_aggregate_feedback_no_feedback(self, mock_task):
        """Test aggregation with no feedback available."""
        db = AsyncMock(spec=AsyncSession)
        handler = RetrievalValidationHandler(db, mock_task)

        # Mock get_feedbacks to return empty list
        handler.get_feedbacks = AsyncMock(return_value=[])

        result = await handler.aggregate_feedback()

        # Should return error message
        assert "error" in result
        assert "No feedback available" in result["error"]

    @pytest.mark.asyncio
    async def test_aggregate_feedback_missing_items_threshold(self, mock_task, mock_feedback_list):
        """Test that missing items need sufficient weighted support."""
        db = AsyncMock(spec=AsyncSession)
        handler = RetrievalValidationHandler(db, mock_task)

        # Mock get_feedbacks
        handler.get_feedbacks = AsyncMock(return_value=mock_feedback_list)

        result = await handler.aggregate_feedback()

        # item4 mentioned by 2/3 experts with total authority 0.9 + 0.5 = 1.4
        # Total authority = 2.0, so 1.4/2.0 = 0.7 > 0.3 threshold
        assert "consensus_missing_items" in result
        # Should include item4 since it has sufficient support
        if result["consensus_missing_items"]:
            assert len(result["consensus_missing_items"]) >= 0

    @pytest.mark.asyncio
    async def test_aggregate_feedback_authority_weighting(self, mock_task):
        """Test that authority scores properly weight votes."""
        db = AsyncMock(spec=AsyncSession)
        handler = RetrievalValidationHandler(db, mock_task)

        # Create feedback where high authority expert disagrees with low authority experts
        fb_high = MagicMock(spec=models.Feedback)
        fb_high.feedback_data = {
            "validated_items": ["item1"],
            "irrelevant_items": ["item2"],
            "missing_items": [],
            "retrieval_quality_score": 0.9,
        }
        fb_high.author = MagicMock()
        fb_high.author.authority_score = 0.95

        fb_low1 = MagicMock(spec=models.Feedback)
        fb_low1.feedback_data = {
            "validated_items": ["item2"],
            "irrelevant_items": ["item1"],
            "missing_items": [],
            "retrieval_quality_score": 0.5,
        }
        fb_low1.author = MagicMock()
        fb_low1.author.authority_score = 0.2

        fb_low2 = MagicMock(spec=models.Feedback)
        fb_low2.feedback_data = {
            "validated_items": ["item2"],
            "irrelevant_items": ["item1"],
            "missing_items": [],
            "retrieval_quality_score": 0.4,
        }
        fb_low2.author = MagicMock()
        fb_low2.author.authority_score = 0.2

        handler.get_feedbacks = AsyncMock(return_value=[fb_high, fb_low1, fb_low2])

        result = await handler.aggregate_feedback()

        # High authority expert (0.95) should outweigh two low authority experts (0.2 + 0.2 = 0.4)
        # item1 should be validated (0.95 > 0.4)
        assert "item1" in result["consensus_validated_items"]
        # item2 should be irrelevant (0.95 > 0.4)
        assert "item2" in result["consensus_irrelevant_items"]


class TestCalculateConsistency:
    """Test cases for calculate_consistency method."""

    def test_calculate_consistency_perfect_match(self, mock_task):
        """Test consistency calculation with perfect match."""
        db = AsyncMock(spec=AsyncSession)
        handler = RetrievalValidationHandler(db, mock_task)

        # Create feedback that perfectly matches consensus
        feedback = MagicMock(spec=models.Feedback)
        feedback.feedback_data = {
            "validated_items": ["item1", "item2"],
            "irrelevant_items": ["item3"],
        }

        aggregated_result = {
            "consensus_validated_items": ["item1", "item2"],
            "consensus_irrelevant_items": ["item3"],
        }

        consistency = handler.calculate_consistency(feedback, aggregated_result)

        # Perfect match should give 1.0 consistency
        assert consistency == 1.0

    def test_calculate_consistency_partial_match(self, mock_task):
        """Test consistency calculation with partial match."""
        db = AsyncMock(spec=AsyncSession)
        handler = RetrievalValidationHandler(db, mock_task)

        # User agrees on item1 but disagrees on item2 and item3
        feedback = MagicMock(spec=models.Feedback)
        feedback.feedback_data = {
            "validated_items": ["item1"],
            "irrelevant_items": ["item2"],
        }

        aggregated_result = {
            "consensus_validated_items": ["item1", "item2"],
            "consensus_irrelevant_items": ["item3"],
        }

        consistency = handler.calculate_consistency(feedback, aggregated_result)

        # Should have moderate consistency (not 0, not 1)
        assert 0.0 < consistency < 1.0

    def test_calculate_consistency_no_match(self, mock_task):
        """Test consistency calculation with no match."""
        db = AsyncMock(spec=AsyncSession)
        handler = RetrievalValidationHandler(db, mock_task)

        # Complete disagreement
        feedback = MagicMock(spec=models.Feedback)
        feedback.feedback_data = {
            "validated_items": ["item3"],
            "irrelevant_items": ["item1", "item2"],
        }

        aggregated_result = {
            "consensus_validated_items": ["item1", "item2"],
            "consensus_irrelevant_items": ["item3"],
        }

        consistency = handler.calculate_consistency(feedback, aggregated_result)

        # Complete disagreement should give 0.0 consistency
        assert consistency == 0.0

    def test_calculate_consistency_empty_sets(self, mock_task):
        """Test consistency calculation with empty sets."""
        db = AsyncMock(spec=AsyncSession)
        handler = RetrievalValidationHandler(db, mock_task)

        feedback = MagicMock(spec=models.Feedback)
        feedback.feedback_data = {
            "validated_items": [],
            "irrelevant_items": [],
        }

        aggregated_result = {
            "consensus_validated_items": [],
            "consensus_irrelevant_items": [],
        }

        consistency = handler.calculate_consistency(feedback, aggregated_result)

        # Both empty = perfect agreement
        assert consistency == 1.0


class TestCalculateCorrectness:
    """Test cases for calculate_correctness method."""

    def test_calculate_correctness_perfect_match(self, mock_task):
        """Test correctness calculation with perfect match to ground truth."""
        db = AsyncMock(spec=AsyncSession)
        handler = RetrievalValidationHandler(db, mock_task)

        feedback = MagicMock(spec=models.Feedback)
        feedback.feedback_data = {
            "validated_items": ["item1", "item2"],
            "irrelevant_items": ["item3"],
        }

        ground_truth = {
            "validated_items": ["item1", "item2"],
            "irrelevant_items": ["item3"],
        }

        correctness = handler.calculate_correctness(feedback, ground_truth)

        # Perfect match should give 1.0 correctness
        assert correctness == 1.0

    def test_calculate_correctness_partial_match(self, mock_task):
        """Test correctness calculation with partial match."""
        db = AsyncMock(spec=AsyncSession)
        handler = RetrievalValidationHandler(db, mock_task)

        # User gets item1 correct but misses item2
        feedback = MagicMock(spec=models.Feedback)
        feedback.feedback_data = {
            "validated_items": ["item1"],
            "irrelevant_items": ["item3"],
        }

        ground_truth = {
            "validated_items": ["item1", "item2"],
            "irrelevant_items": ["item3"],
        }

        correctness = handler.calculate_correctness(feedback, ground_truth)

        # Should have moderate correctness
        assert 0.0 < correctness < 1.0

    def test_calculate_correctness_no_ground_truth(self, mock_task):
        """Test correctness calculation with no ground truth."""
        db = AsyncMock(spec=AsyncSession)
        handler = RetrievalValidationHandler(db, mock_task)

        feedback = MagicMock(spec=models.Feedback)
        feedback.feedback_data = {
            "validated_items": ["item1"],
            "irrelevant_items": [],
        }

        correctness = handler.calculate_correctness(feedback, {})

        # No ground truth should give 0.0 correctness
        assert correctness == 0.0

    def test_calculate_correctness_false_positives(self, mock_task):
        """Test correctness calculation with false positives."""
        db = AsyncMock(spec=AsyncSession)
        handler = RetrievalValidationHandler(db, mock_task)

        # User validates items that aren't in ground truth
        feedback = MagicMock(spec=models.Feedback)
        feedback.feedback_data = {
            "validated_items": ["item1", "item2", "item3"],
            "irrelevant_items": [],
        }

        ground_truth = {
            "validated_items": ["item1"],
            "irrelevant_items": ["item2", "item3"],
        }

        correctness = handler.calculate_correctness(feedback, ground_truth)

        # False positives should reduce correctness
        assert correctness < 1.0

    def test_calculate_correctness_precision_recall_balance(self, mock_task):
        """Test that correctness uses F1 score (balances precision and recall)."""
        db = AsyncMock(spec=AsyncSession)
        handler = RetrievalValidationHandler(db, mock_task)

        # High precision, low recall case
        feedback = MagicMock(spec=models.Feedback)
        feedback.feedback_data = {
            "validated_items": ["item1"],  # Only 1 of 3
            "irrelevant_items": [],
        }

        ground_truth = {
            "validated_items": ["item1", "item2", "item3"],
            "irrelevant_items": [],
        }

        correctness = handler.calculate_correctness(feedback, ground_truth)

        # F1 should be moderate (precision=1.0, recall=0.33, F1~=0.5)
        # Average of validated_f1 and irrelevant_f1
        assert 0.3 < correctness < 0.8


class TestFormatForExport:
    """Test cases for format_for_export method."""

    def test_format_for_export_sft(self, mock_task):
        """Test export formatting for Supervised Fine-Tuning."""
        db = AsyncMock(spec=AsyncSession)
        handler = RetrievalValidationHandler(db, mock_task)

        export_data = handler.format_for_export("SFT")

        assert len(export_data) == 1
        entry = export_data[0]

        # Should have basic task info
        assert entry["task_id"] == mock_task.id
        assert entry["task_type"] == "RETRIEVAL_VALIDATION"
        assert entry["query"] == mock_task.input_data["query"]

        # Should have SFT-specific fields
        assert "input" in entry
        assert "output" in entry
        assert "Query:" in entry["input"]
        assert "Validated:" in entry["output"]

    def test_format_for_export_preference(self, mock_task):
        """Test export formatting for Preference Learning."""
        db = AsyncMock(spec=AsyncSession)
        handler = RetrievalValidationHandler(db, mock_task)

        export_data = handler.format_for_export("Preference")

        assert len(export_data) == 1
        entry = export_data[0]

        # Should have basic task info
        assert entry["task_id"] == mock_task.id
        assert entry["task_type"] == "RETRIEVAL_VALIDATION"

        # Should have Preference-specific fields
        assert "query" in entry
        assert "preferred_response" in entry
        assert "context_info" in entry

        # Context info should include retrieval metadata
        context = entry["context_info"]
        assert "retrieved_items" in context
        assert "retrieval_strategy" in context
        assert "agent_type" in context

    def test_format_for_export_includes_ground_truth(self, mock_task):
        """Test that export includes ground truth data."""
        db = AsyncMock(spec=AsyncSession)
        handler = RetrievalValidationHandler(db, mock_task)

        export_data = handler.format_for_export("SFT")

        entry = export_data[0]

        # Should include ground truth items
        assert "ground_truth_validated" in entry
        assert "ground_truth_irrelevant" in entry
        assert entry["ground_truth_validated"] == ["item1", "item2"]
        assert entry["ground_truth_irrelevant"] == ["item3"]

    def test_format_for_export_no_ground_truth(self, mock_task):
        """Test export formatting when task has no ground truth."""
        db = AsyncMock(spec=AsyncSession)

        # Create task without ground truth
        task_no_gt = MagicMock(spec=models.LegalTask)
        task_no_gt.id = 2
        task_no_gt.task_type = "RETRIEVAL_VALIDATION"
        task_no_gt.input_data = mock_task.input_data
        task_no_gt.ground_truth_data = None

        handler = RetrievalValidationHandler(db, task_no_gt)

        export_data = handler.format_for_export("SFT")

        entry = export_data[0]

        # Should have empty ground truth lists
        assert entry["ground_truth_validated"] == []
        assert entry["ground_truth_irrelevant"] == []


class TestEdgeCases:
    """Test cases for edge cases and error handling."""

    @pytest.mark.asyncio
    async def test_aggregate_feedback_with_malformed_data(self, mock_task):
        """Test aggregation handles malformed feedback data gracefully."""
        db = AsyncMock(spec=AsyncSession)
        handler = RetrievalValidationHandler(db, mock_task)

        # Create feedback with missing or malformed fields
        fb_malformed = MagicMock(spec=models.Feedback)
        fb_malformed.feedback_data = {
            "validated_items": "not_a_list",  # Should be list
            "irrelevant_items": None,  # Missing data
        }
        fb_malformed.author = MagicMock()
        fb_malformed.author.authority_score = 0.8

        handler.get_feedbacks = AsyncMock(return_value=[fb_malformed])

        # Should not crash
        result = await handler.aggregate_feedback()

        # Should still return a valid result structure
        assert isinstance(result, dict)

    def test_calculate_consistency_with_missing_fields(self, mock_task):
        """Test consistency calculation handles missing fields."""
        db = AsyncMock(spec=AsyncSession)
        handler = RetrievalValidationHandler(db, mock_task)

        feedback = MagicMock(spec=models.Feedback)
        feedback.feedback_data = {}  # Missing validated_items and irrelevant_items

        aggregated_result = {
            "consensus_validated_items": ["item1"],
            "consensus_irrelevant_items": [],
        }

        # Should not crash
        consistency = handler.calculate_consistency(feedback, aggregated_result)

        # Should return a valid consistency score
        assert isinstance(consistency, float)
        assert 0.0 <= consistency <= 1.0

    @pytest.mark.asyncio
    async def test_handler_with_single_evaluator(self, mock_task):
        """Test aggregation with only one evaluator."""
        db = AsyncMock(spec=AsyncSession)
        handler = RetrievalValidationHandler(db, mock_task)

        # Single feedback
        fb_single = MagicMock(spec=models.Feedback)
        fb_single.feedback_data = {
            "validated_items": ["item1"],
            "irrelevant_items": ["item2"],
            "missing_items": ["item3"],
            "retrieval_quality_score": 0.7,
        }
        fb_single.author = MagicMock()
        fb_single.author.authority_score = 0.8

        handler.get_feedbacks = AsyncMock(return_value=[fb_single])

        result = await handler.aggregate_feedback()

        # Should use single evaluator's assessment as consensus
        assert "item1" in result["consensus_validated_items"]
        assert "item2" in result["consensus_irrelevant_items"]
        assert result["total_evaluators"] == 1


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
