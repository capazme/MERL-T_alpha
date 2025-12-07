from .base import BaseTaskHandler
from typing import Dict, Any, List
from sqlalchemy.ext.asyncio import AsyncSession
from .. import models
from collections import Counter


class RetrievalValidationHandler(BaseTaskHandler):
    """
    Handler for Retrieval Validation tasks.

    This handler implements the specific logic for aggregating feedback on
    retrieval quality validation from KG, API, and VectorDB agents in the
    MERL-T pipeline. It validates whether retrieved items (norms, documents,
    chunks) are relevant to the user's query, identifying both relevant and
    irrelevant retrievals as well as missing items.

    This is a critical RLCF entry point in the Orchestration Layer (Layer 2)
    where the community validates the quality of retrieval before reasoning
    begins, enabling continuous improvement of retrieval strategies.

    References:
        docs/02-methodology/legal-reasoning.md - RLCF integration points
        docs/03-architecture/02-orchestration-layer.md - Retrieval agents
        RLCF.md Section 3.6 - Dynamic Task Handler System
    """

    def __init__(self, db: AsyncSession, task: models.LegalTask):
        """
        Initializes the RetrievalValidationHandler with a database session and a legal task.

        Args:
            db: The SQLAlchemy async session for database operations.
            task: The LegalTask instance associated with this handler.
        """
        super().__init__(db, task)

    async def aggregate_feedback(self) -> Dict[str, Any]:
        """
        Aggregates feedback for Retrieval Validation tasks.

        Implements authority-weighted aggregation of retrieval quality assessments,
        determining consensus on which retrieved items are relevant, irrelevant, or
        missing. The algorithm:
        1. Counts votes for each item being validated/invalidated
        2. Applies authority weights A_u(t) from RLCF.md Section 2.1
        3. Determines consensus based on weighted majority
        4. Calculates overall retrieval quality score

        This aggregation directly informs the learning loop for retrieval agents,
        enabling the system to improve KG queries, API calls, and vector searches
        over time.

        Returns:
            A dictionary containing consensus validated/irrelevant/missing items,
            retrieval quality score, and confidence metrics.

        References:
            RLCF.md Section 2.1 - Dynamic Authority Scoring Model
            RLCF.md Section 3.1 - Uncertainty-Preserving Aggregation Algorithm
        """
        feedbacks = await self.get_feedbacks()
        if not feedbacks:
            return {"error": "No feedback available for this retrieval validation task."}

        # Track votes for each item being validated or marked as irrelevant
        validated_votes = Counter()  # item_id -> weighted vote count for "relevant"
        irrelevant_votes = Counter()  # item_id -> weighted vote count for "irrelevant"
        missing_items_votes = Counter()  # missing item description -> weighted vote count
        quality_scores = []  # List of (quality_score, authority_weight) tuples

        # Aggregate votes from all evaluators
        for fb in feedbacks:
            authority = fb.author.authority_score

            # Items marked as validated (relevant)
            validated_items = fb.feedback_data.get("validated_items", [])
            if isinstance(validated_items, list):
                for item_id in validated_items:
                    validated_votes[item_id] += authority

            # Items marked as irrelevant
            irrelevant_items = fb.feedback_data.get("irrelevant_items", [])
            if isinstance(irrelevant_items, list):
                for item_id in irrelevant_items:
                    irrelevant_votes[item_id] += authority

            # Missing items that should have been retrieved
            missing_items = fb.feedback_data.get("missing_items", [])
            if isinstance(missing_items, list):
                for item_desc in missing_items:
                    missing_items_votes[item_desc] += authority

            # Retrieval quality score (0.0 to 1.0)
            quality_score = fb.feedback_data.get("retrieval_quality_score")
            if quality_score is not None:
                quality_scores.append((quality_score, authority))

        # Determine consensus: items need majority weighted support to be classified
        all_items = set(validated_votes.keys()) | set(irrelevant_votes.keys())
        consensus_validated = []
        consensus_irrelevant = []

        total_authority = sum(fb.author.authority_score for fb in feedbacks)

        for item_id in all_items:
            validated_weight = validated_votes.get(item_id, 0)
            irrelevant_weight = irrelevant_votes.get(item_id, 0)

            # Item is validated if it has more validation votes than irrelevant votes
            if validated_weight > irrelevant_weight:
                consensus_validated.append(item_id)
            elif irrelevant_weight > validated_weight:
                consensus_irrelevant.append(item_id)
            # If tied, skip (uncertain case)

        # Consensus missing items (items with significant weighted support)
        consensus_missing = [
            item for item, weight in missing_items_votes.most_common()
            if weight >= total_authority * 0.3  # At least 30% weighted support
        ]

        # Calculate average retrieval quality score (authority-weighted)
        if quality_scores:
            weighted_sum = sum(score * weight for score, weight in quality_scores)
            weight_total = sum(weight for _, weight in quality_scores)
            avg_quality = weighted_sum / weight_total if weight_total > 0 else 0
        else:
            avg_quality = 0

        # Calculate confidence based on agreement level
        # Higher confidence when evaluators agree more on item classifications
        if all_items:
            avg_agreement = sum(
                max(validated_votes.get(item, 0), irrelevant_votes.get(item, 0))
                for item in all_items
            ) / (len(all_items) * total_authority) if total_authority > 0 else 0
        else:
            avg_agreement = 0

        return {
            "consensus_answer": f"Validated: {len(consensus_validated)} items, Irrelevant: {len(consensus_irrelevant)} items, Missing: {len(consensus_missing)} items",
            "confidence": round(avg_agreement, 3),
            "consensus_validated_items": consensus_validated,
            "consensus_irrelevant_items": consensus_irrelevant,
            "consensus_missing_items": consensus_missing[:5],  # Top 5 missing items
            "retrieval_quality_score": round(avg_quality, 3),
            "total_evaluators": len(feedbacks),
            "details": {
                "validated_votes": dict(validated_votes),
                "irrelevant_votes": dict(irrelevant_votes),
                "missing_votes": dict(missing_items_votes),
            },
        }

    def calculate_consistency(
        self, feedback: models.Feedback, aggregated_result: Dict[str, Any]
    ) -> float:
        """
        Calculates consistency for Retrieval Validation.

        Measures how well the user's item classifications align with the
        consensus classifications. Uses Jaccard similarity for set comparison.

        Args:
            feedback: The individual Feedback instance to evaluate.
            aggregated_result: The aggregated result for the task.

        Returns:
            A float representing the consistency score (0.0 to 1.0).
        """
        user_validated = set(feedback.feedback_data.get("validated_items", []))
        user_irrelevant = set(feedback.feedback_data.get("irrelevant_items", []))

        consensus_validated = set(aggregated_result.get("consensus_validated_items", []))
        consensus_irrelevant = set(aggregated_result.get("consensus_irrelevant_items", []))

        # Jaccard similarity for validated items
        if user_validated or consensus_validated:
            validated_jaccard = len(user_validated & consensus_validated) / len(
                user_validated | consensus_validated
            ) if (user_validated | consensus_validated) else 0
        else:
            validated_jaccard = 1.0  # Both empty = perfect agreement

        # Jaccard similarity for irrelevant items
        if user_irrelevant or consensus_irrelevant:
            irrelevant_jaccard = len(user_irrelevant & consensus_irrelevant) / len(
                user_irrelevant | consensus_irrelevant
            ) if (user_irrelevant | consensus_irrelevant) else 0
        else:
            irrelevant_jaccard = 1.0  # Both empty = perfect agreement

        # Average of both Jaccard scores (weighted equally)
        consistency = (validated_jaccard + irrelevant_jaccard) / 2
        return round(consistency, 3)

    def calculate_correctness(
        self, feedback: models.Feedback, ground_truth: Dict[str, Any]
    ) -> float:
        """
        Calculates correctness against ground truth for Retrieval Validation.

        Compares the user's item classifications against known correct
        classifications from ground truth data.

        Args:
            feedback: The individual Feedback instance to evaluate.
            ground_truth: The ground truth data for the task (must contain
                         "validated_items" and "irrelevant_items").

        Returns:
            A float representing the correctness score (0.0 to 1.0).
        """
        if not ground_truth:
            return 0.0

        user_validated = set(feedback.feedback_data.get("validated_items", []))
        user_irrelevant = set(feedback.feedback_data.get("irrelevant_items", []))

        gt_validated = set(ground_truth.get("validated_items", []))
        gt_irrelevant = set(ground_truth.get("irrelevant_items", []))

        # Calculate precision and recall for validated items
        if user_validated:
            validated_precision = len(user_validated & gt_validated) / len(user_validated)
        else:
            validated_precision = 1.0 if not gt_validated else 0.0

        if gt_validated:
            validated_recall = len(user_validated & gt_validated) / len(gt_validated)
        else:
            validated_recall = 1.0 if not user_validated else 0.0

        # F1 score for validated items
        if validated_precision + validated_recall > 0:
            validated_f1 = 2 * (validated_precision * validated_recall) / (
                validated_precision + validated_recall
            )
        else:
            validated_f1 = 0.0

        # Calculate precision and recall for irrelevant items
        if user_irrelevant:
            irrelevant_precision = len(user_irrelevant & gt_irrelevant) / len(user_irrelevant)
        else:
            irrelevant_precision = 1.0 if not gt_irrelevant else 0.0

        if gt_irrelevant:
            irrelevant_recall = len(user_irrelevant & gt_irrelevant) / len(gt_irrelevant)
        else:
            irrelevant_recall = 1.0 if not user_irrelevant else 0.0

        # F1 score for irrelevant items
        if irrelevant_precision + irrelevant_recall > 0:
            irrelevant_f1 = 2 * (irrelevant_precision * irrelevant_recall) / (
                irrelevant_precision + irrelevant_recall
            )
        else:
            irrelevant_f1 = 0.0

        # Average F1 scores (weighted equally)
        correctness = (validated_f1 + irrelevant_f1) / 2
        return round(correctness, 3)

    def format_for_export(self, format_type: str) -> List[Dict[str, Any]]:
        """
        Formats Retrieval Validation data for export.

        Prepares retrieval validation task data for model training in either
        Supervised Fine-Tuning (SFT) or Preference Learning format. This enables
        training retrieval agents to improve their query strategies.

        Args:
            format_type: "SFT" for supervised fine-tuning or "Preference" for preference learning

        Returns:
            List of dictionaries containing formatted data ready for export
        """
        export_data = []

        # Create basic export entry with task data
        export_entry = {
            "task_id": self.task.id,
            "task_type": self.task.task_type,
            "query": self.task.input_data.get("query", ""),
            "retrieved_items": self.task.input_data.get("retrieved_items", []),
            "retrieval_strategy": self.task.input_data.get("retrieval_strategy", ""),
            "agent_type": self.task.input_data.get("agent_type", ""),
            "ground_truth_validated": (
                self.task.ground_truth_data.get("validated_items", [])
                if self.task.ground_truth_data
                else []
            ),
            "ground_truth_irrelevant": (
                self.task.ground_truth_data.get("irrelevant_items", [])
                if self.task.ground_truth_data
                else []
            ),
        }

        if format_type == "SFT":
            # Supervised Fine-Tuning format: input → validated items
            export_entry.update(
                {
                    "input": f"Query: {export_entry['query']}\nRetrieved Items: {export_entry['retrieved_items']}\nValidate the relevance of retrieved items.",
                    "output": f"Validated: {export_entry['ground_truth_validated']}, Irrelevant: {export_entry['ground_truth_irrelevant']}",
                }
            )
        elif format_type == "Preference":
            # Preference learning format: query + preferred response
            export_entry.update(
                {
                    "query": f"Validate retrieval for: {export_entry['query']}",
                    "preferred_response": f"Validated: {export_entry['ground_truth_validated']}, Irrelevant: {export_entry['ground_truth_irrelevant']}",
                    "context_info": {
                        "retrieved_items": export_entry["retrieved_items"],
                        "retrieval_strategy": export_entry["retrieval_strategy"],
                        "agent_type": export_entry["agent_type"],
                    },
                }
            )

        export_data.append(export_entry)
        return export_data
