from .base import BaseTaskHandler
from typing import Dict, Any, List
from sqlalchemy.ext.asyncio import AsyncSession
from .. import models
import numpy as np
from collections import Counter


class QAHandler(BaseTaskHandler):
    """
    Handler for Question Answering tasks.

    Implements the Strategy pattern for legal question answering, the most common
    task type in the RLCF framework. This handler provides sophisticated logic for
    aggregating textual answers using semantic similarity, authority weighting,
    and confidence estimation.
    
    The handler supports complex legal reasoning scenarios where multiple valid
    interpretations may exist, implementing uncertainty preservation through
    alternative answer tracking and reasoning pattern analysis.
    
    References:
        RLCF.md Section 3.6 - Dynamic Task Handler System
        RLCF.md Section 3.1 - Uncertainty-Preserving Aggregation Algorithm
    """

    def __init__(self, db: AsyncSession, task: models.LegalTask):
        """
        Initializes the QAHandler with a database session and a legal task.

        Args:
            db: The SQLAlchemy async session for database operations.
            task: The LegalTask instance associated with this handler.
        """
        super().__init__(db, task)

    async def aggregate_feedback(self) -> Dict[str, Any]:
        """
        Aggregates feedback for QA tasks.

        Implements sophisticated textual answer aggregation using normalized answer
        grouping and authority-weighted scoring. The algorithm:
        1. Normalizes answers for semantic grouping
        2. Applies authority weights A_u(t) from RLCF.md Section 2.1
        3. Preserves alternative interpretations for uncertainty analysis
        4. Calculates confidence based on weight distribution
        
        This approach maintains the dialectical nature of legal reasoning by
        preserving minority positions and reasoning patterns, implementing the
        Principle of Preserved Uncertainty.

        Returns:
            A dictionary containing the consensus answer, confidence score,
            alternative answers with support percentages, and detailed aggregation results.
            
        References:
            RLCF.md Section 2.1 - Dynamic Authority Scoring Model
            RLCF.md Section 1.2 - Principle of Preserved Uncertainty (Incertitudo Conservata)
        """
        feedbacks = await self.get_feedbacks()
        if not feedbacks:
            return {"error": "No feedback available for this QA task."}

        answer_scores = {}
        answer_details = {}

        for fb in feedbacks:
            answer = fb.feedback_data.get("validated_answer", "")
            if not answer:
                continue

            # Normalizza la risposta per aggregazione
            normalized_answer = answer.strip().lower()

            if normalized_answer not in answer_scores:
                answer_scores[normalized_answer] = 0
                answer_details[normalized_answer] = {
                    "original_answers": [],
                    "supporters": [],
                    "reasoning": [],
                }

            # Accumula peso basato sull'autorità
            weight = fb.author.authority_score
            answer_scores[normalized_answer] += weight

            # Colleziona dettagli
            answer_details[normalized_answer]["original_answers"].append(answer)
            answer_details[normalized_answer]["supporters"].append(
                {"username": fb.author.username, "authority": fb.author.authority_score}
            )

            if "reasoning" in fb.feedback_data:
                answer_details[normalized_answer]["reasoning"].append(
                    fb.feedback_data["reasoning"]
                )

        if not answer_scores:
            return {"error": "No valid answers found."}

        # Trova risposta con maggior peso
        sorted_answers = sorted(answer_scores.items(), key=lambda x: x[1], reverse=True)
        best_answer_key, best_score = sorted_answers[0]

        # Prepara alternative answers
        alternative_answers = []
        total_weight = sum(answer_scores.values())

        for answer_key, score in sorted_answers[1:4]:  # Top 3 alternative
            details = answer_details[answer_key]
            alternative_answers.append(
                {
                    "answer": (
                        details["original_answers"][0]
                        if details["original_answers"]
                        else answer_key
                    ),
                    "support_percentage": round((score / total_weight) * 100, 1),
                    "supporter_count": len(details["supporters"]),
                    "top_reasoning": (
                        details["reasoning"][0] if details["reasoning"] else ""
                    ),
                }
            )

        # Calcola confidence basato sulla distribuzione
        confidence = best_score / total_weight if total_weight > 0 else 0

        # Seleziona la migliore versione dell'answer vincente
        best_answer_details = answer_details[best_answer_key]
        consensus_answer = (
            best_answer_details["original_answers"][0]
            if best_answer_details["original_answers"]
            else best_answer_key
        )

        return {
            "consensus_answer": consensus_answer,
            "confidence": round(confidence, 3),
            "support_percentage": round((best_score / total_weight) * 100, 1),
            "alternative_answers": alternative_answers,
            "total_evaluators": len(feedbacks),
            "details": answer_scores,  # Per il calcolo del disagreement
        }

    def calculate_consistency(
        self, feedback: models.Feedback, aggregated_result: Dict[str, Any]
    ) -> float:
        """Calcola consistency per QA."""
        user_answer = feedback.feedback_data.get("validated_answer", "").strip().lower()
        consensus_answer = aggregated_result.get("consensus_answer", "").strip().lower()

        if not user_answer or not consensus_answer:
            return 0.0

        # Exact match
        if user_answer == consensus_answer:
            return 1.0

        # Partial match basato su parole chiave comuni
        user_words = set(user_answer.split())
        consensus_words = set(consensus_answer.split())

        if not user_words or not consensus_words:
            return 0.0

        # Jaccard similarity
        intersection = len(user_words & consensus_words)
        union = len(user_words | consensus_words)

        jaccard_similarity = intersection / union if union > 0 else 0

        # Bonus per semantica simile (semplificato)
        semantic_bonus = 0
        key_legal_terms = [
            "guilty",
            "liable",
            "breach",
            "violation",
            "compliance",
            "valid",
            "invalid",
        ]

        user_legal_terms = [term for term in key_legal_terms if term in user_answer]
        consensus_legal_terms = [
            term for term in key_legal_terms if term in consensus_answer
        ]

        if user_legal_terms and consensus_legal_terms:
            legal_match = len(set(user_legal_terms) & set(consensus_legal_terms))
            semantic_bonus = (
                legal_match
                / max(len(user_legal_terms), len(consensus_legal_terms))
                * 0.3
            )

        return min(1.0, jaccard_similarity + semantic_bonus)

    def calculate_correctness(
        self, feedback: models.Feedback, ground_truth: Dict[str, Any]
    ) -> float:
        """Calcola correctness rispetto al ground truth."""
        if not ground_truth:
            return 0.0

        user_answer = feedback.feedback_data.get("validated_answer", "").strip().lower()
        correct_answer = ground_truth.get("answer", "").strip().lower()

        if not user_answer or not correct_answer:
            return 0.0

        # Exact match
        if user_answer == correct_answer:
            return 1.0

        # Semantic similarity per risposte legali
        user_words = set(user_answer.split())
        correct_words = set(correct_answer.split())

        # Jaccard similarity with legal term weighting
        intersection = user_words & correct_words
        union = user_words | correct_words

        if not union:
            return 0.0

        # Peso maggiore per termini legali importanti
        legal_terms = {
            "yes",
            "no",
            "guilty",
            "not guilty",
            "liable",
            "not liable",
            "valid",
            "invalid",
            "breach",
            "no breach",
            "violation",
            "compliance",
        }

        legal_intersection = intersection & legal_terms
        legal_union = union & legal_terms

        if legal_union:
            # Se ci sono termini legali, pesali di più
            legal_score = len(legal_intersection) / len(legal_union)
            general_score = (
                len(intersection - legal_terms) / len(union - legal_terms)
                if (union - legal_terms)
                else 0
            )
            return min(1.0, legal_score * 0.8 + general_score * 0.2)
        else:
            # Altrimenti usa Jaccard standard
            return len(intersection) / len(union)

    def format_for_export(self, format_type: str) -> List[Dict[str, Any]]:
        """
        Format QA data for export in specified formats.

        Prepares question-answering task data for model training in either
        Supervised Fine-Tuning (SFT) or Preference Learning format.

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
            "question": self.task.input_data.get("question", ""),
            "context": self.task.input_data.get("context", ""),
            "ground_truth_answer": self.task.ground_truth_data.get("validated_answer", "") if self.task.ground_truth_data else ""
        }

        if format_type == "SFT":
            # Supervised Fine-Tuning format: simple input → output pairs
            export_entry.update({
                "input": f"Question: {export_entry['question']}\nContext: {export_entry['context']}",
                "output": export_entry["ground_truth_answer"]
            })
        elif format_type == "Preference":
            # Preference learning format: query + preferred/rejected responses
            export_entry.update({
                "query": export_entry["question"],
                "preferred_response": export_entry["ground_truth_answer"],
                "context_info": {
                    "context": export_entry["context"]
                }
            })

        export_data.append(export_entry)
        return export_data


class SummarizationHandler(BaseTaskHandler):
    """
    Handler for Summarization tasks.

    This handler implements the specific logic for aggregating feedback,
    calculating consistency, and formatting data for export related to
    summarization tasks.
    """

    def __init__(self, db: AsyncSession, task: models.LegalTask):
        """
        Initializes the SummarizationHandler with a database session and a legal task.

        Args:
            db: The SQLAlchemy async session for database operations.
            task: The LegalTask instance associated with this handler.
        """
        super().__init__(db, task)

    async def aggregate_feedback(self) -> Dict[str, Any]:
        """
        Aggregates feedback for Summarization tasks.

        Groups feedback by ratings and revisions, calculating weighted scores
        based on authority scores.

        Returns:
            A dictionary containing the consensus answer, confidence score,
            quality assessment, and revised summaries.
        """
        feedbacks = await self.get_feedbacks()
        if not feedbacks:
            return {"error": "No feedback available for this summarization task."}

        # Raggruppa per rating e revisioni
        rating_weights = {"good": 0, "bad": 0}
        revised_summaries = []

        for fb in feedbacks:
            rating = fb.feedback_data.get("rating")
            if rating in rating_weights:
                rating_weights[rating] += fb.author.authority_score

            revised_summary = fb.feedback_data.get("revised_summary")
            if revised_summary:
                revised_summaries.append(
                    {
                        "summary": revised_summary,
                        "author": fb.author.username,
                        "authority": fb.author.authority_score,
                        "rating": rating,
                    }
                )

        total_weight = sum(rating_weights.values())
        if total_weight == 0:
            return {"error": "No valid ratings found."}

        # Determina consensus su quality
        good_percentage = (rating_weights["good"] / total_weight) * 100

        # Trova le migliori revisioni (da utenti con alta autorità e rating "good")
        good_revisions = [r for r in revised_summaries if r["rating"] == "good"]
        good_revisions.sort(key=lambda x: x["authority"], reverse=True)

        consensus_answer = (
            "Summary quality acceptable"
            if good_percentage > 60
            else "Summary needs improvement"
        )

        if good_revisions and good_percentage <= 60:
            # Se la maggioranza dice "bad", usa la migliore revisione
            consensus_answer = good_revisions[0]["summary"]

        return {
            "consensus_answer": consensus_answer,
            "confidence": abs(good_percentage - 50) / 50,  # Higher when more extreme
            "quality_assessment": {
                "good_percentage": round(good_percentage, 1),
                "bad_percentage": round(100 - good_percentage, 1),
            },
            "revised_summaries": good_revisions[:3],  # Top 3
            "details": rating_weights,
        }

    def calculate_consistency(
        self, feedback: models.Feedback, aggregated_result: Dict[str, Any]
    ) -> float:
        """Calcola consistency per Summarization."""
        user_rating = feedback.feedback_data.get("rating")
        quality_assessment = aggregated_result.get("quality_assessment", {})

        if not user_rating or not quality_assessment:
            return 0.0

        good_percentage = quality_assessment.get("good_percentage", 50)

        if user_rating == "good" and good_percentage > 50:
            return 1.0
        elif user_rating == "bad" and good_percentage < 50:
            return 1.0
        else:
            # Partial consistency based on how close to the threshold
            distance_from_threshold = abs(good_percentage - 50) / 50
            return 1 - distance_from_threshold

    def calculate_correctness(
        self, feedback: models.Feedback, ground_truth: Dict[str, Any]
    ) -> float:
        """Calculate correctness for Summarization."""
        if not ground_truth:
            return 0.0
        user_summary = feedback.feedback_data.get("revised_summary", "").strip().lower()
        correct_summary = ground_truth.get("revised_summary", "").strip().lower()
        if not user_summary or not correct_summary:
            return 0.0
        # Jaccard similarity for summarization
        user_words = set(user_summary.split())
        correct_words = set(correct_summary.split())
        if not user_words or not correct_words:
            return 0.0
        intersection = len(user_words & correct_words)
        union = len(user_words | correct_words)
        return intersection / union if union > 0 else 0.0

    def format_for_export(self, format_type: str) -> List[Dict[str, Any]]:
        """Format Summarization data for export."""
        export_data = []
        export_entry = {
            "task_id": self.task.id,
            "task_type": self.task.task_type,
            "document": self.task.input_data.get("document", ""),
            "ground_truth_summary": self.task.ground_truth_data.get("revised_summary", "") if self.task.ground_truth_data else ""
        }
        if format_type == "SFT":
            export_entry.update({
                "input": f"Summarize the following document:\n{export_entry['document']}",
                "output": export_entry["ground_truth_summary"]
            })
        elif format_type == "Preference":
            export_entry.update({
                "query": "Summarize this document",
                "preferred_response": export_entry["ground_truth_summary"],
                "context_info": {"document": export_entry["document"]}
            })
        export_data.append(export_entry)
        return export_data


class PredictionHandler(BaseTaskHandler):
    """
    Handler for Prediction tasks (outcome prediction).

    This handler implements the specific logic for aggregating feedback,
    calculating consistency, and formatting data for export related to
    prediction tasks.
    """

    def __init__(self, db: AsyncSession, task: models.LegalTask):
        """
        Initializes the PredictionHandler with a database session and a legal task.

        Args:
            db: The SQLAlchemy async session for database operations.
            task: The LegalTask instance associated with this handler.
        """
        super().__init__(db, task)

    async def aggregate_feedback(self) -> Dict[str, Any]:
        """
        Aggregates feedback for Prediction tasks.

        Calculates weighted scores for predicted outcomes based on authority scores
        and determines the most likely outcome with confidence metrics.

        Returns:
            A dictionary containing the predicted outcome, confidence score,
            and outcome probabilities.
        """
        feedbacks = await self.get_feedbacks()
        if not feedbacks:
            return {"error": "No feedback available for this prediction task."}

        outcome_weights = {}

        for fb in feedbacks:
            outcome = fb.feedback_data.get("chosen_outcome")
            if outcome:
                if outcome not in outcome_weights:
                    outcome_weights[outcome] = 0
                outcome_weights[outcome] += fb.author.authority_score

        if not outcome_weights:
            return {"error": "No valid predictions found."}

        # Trova outcome più probabile
        sorted_outcomes = sorted(
            outcome_weights.items(), key=lambda x: x[1], reverse=True
        )
        predicted_outcome, max_weight = sorted_outcomes[0]

        total_weight = sum(outcome_weights.values())
        confidence = max_weight / total_weight if total_weight > 0 else 0

        # Calcola probabilità per ogni outcome
        outcome_probabilities = {
            outcome: round((weight / total_weight) * 100, 1)
            for outcome, weight in outcome_weights.items()
        }

        return {
            "consensus_answer": f"Predicted outcome: {predicted_outcome}",
            "confidence": round(confidence, 3),
            "predicted_outcome": predicted_outcome,
            "outcome_probabilities": outcome_probabilities,
            "details": outcome_weights,
        }

    def calculate_consistency(
        self, feedback: models.Feedback, aggregated_result: Dict[str, Any]
    ) -> float:
        """Calcola consistency per Prediction."""
        user_prediction = feedback.feedback_data.get("chosen_outcome")
        predicted_outcome = aggregated_result.get("predicted_outcome")

        if not user_prediction or not predicted_outcome:
            return 0.0

        return 1.0 if user_prediction == predicted_outcome else 0.0

    def calculate_correctness(
        self, feedback: models.Feedback, ground_truth: Dict[str, Any]
    ) -> float:
        """Calculate correctness for Prediction."""
        if not ground_truth:
            return 0.0
        user_outcome = feedback.feedback_data.get("chosen_outcome", "").strip().lower()
        correct_outcome = ground_truth.get("chosen_outcome", "").strip().lower()
        return 1.0 if user_outcome == correct_outcome else 0.0

    def format_for_export(self, format_type: str) -> List[Dict[str, Any]]:
        """Format Prediction data for export."""
        export_data = []
        export_entry = {
            "task_id": self.task.id,
            "task_type": self.task.task_type,
            "facts": self.task.input_data.get("facts", ""),
            "ground_truth_outcome": self.task.ground_truth_data.get("chosen_outcome", "") if self.task.ground_truth_data else ""
        }
        if format_type == "SFT":
            export_entry.update({
                "input": f"Predict the legal outcome given these facts:\n{export_entry['facts']}",
                "output": export_entry["ground_truth_outcome"]
            })
        elif format_type == "Preference":
            export_entry.update({
                "query": "Predict the legal outcome",
                "preferred_response": export_entry["ground_truth_outcome"],
                "context_info": {"facts": export_entry["facts"]}
            })
        export_data.append(export_entry)
        return export_data


class NLIHandler(BaseTaskHandler):
    """
    Handler for Natural Language Inference tasks.

    This handler implements the specific logic for aggregating feedback,
    calculating consistency, and formatting data for export related to
    natural language inference tasks.
    """

    def __init__(self, db: AsyncSession, task: models.LegalTask):
        """
        Initializes the NLIHandler with a database session and a legal task.

        Args:
            db: The SQLAlchemy async session for database operations.
            task: The LegalTask instance associated with this handler.
        """
        super().__init__(db, task)

    async def aggregate_feedback(self) -> Dict[str, Any]:
        """
        Aggregates feedback for NLI tasks.

        Calculates weighted scores for inference labels based on authority scores
        and determines the consensus relationship label.

        Returns:
            A dictionary containing the consensus label, confidence score,
            and label distribution.
        """
        feedbacks = await self.get_feedbacks()
        if not feedbacks:
            return {"error": "No feedback available for this NLI task."}

        label_weights = {}

        for fb in feedbacks:
            label = fb.feedback_data.get("chosen_label")
            if label:
                if label not in label_weights:
                    label_weights[label] = 0
                label_weights[label] += fb.author.authority_score

        if not label_weights:
            return {"error": "No valid labels found."}

        # Trova label più probabile
        sorted_labels = sorted(label_weights.items(), key=lambda x: x[1], reverse=True)
        consensus_label, max_weight = sorted_labels[0]

        total_weight = sum(label_weights.values())
        confidence = max_weight / total_weight if total_weight > 0 else 0

        return {
            "consensus_answer": f"Relationship: {consensus_label}",
            "confidence": round(confidence, 3),
            "consensus_label": consensus_label,
            "label_distribution": {
                label: round((weight / total_weight) * 100, 1)
                for label, weight in label_weights.items()
            },
            "details": label_weights,
        }

    def calculate_consistency(
        self, feedback: models.Feedback, aggregated_result: Dict[str, Any]
    ) -> float:
        """Calcola consistency per NLI."""
        user_label = feedback.feedback_data.get("chosen_label")
        consensus_label = aggregated_result.get("consensus_label")

        return 1.0 if user_label == consensus_label else 0.0

    def calculate_correctness(
        self, feedback: models.Feedback, ground_truth: Dict[str, Any]
    ) -> float:
        """Calculate correctness for NLI."""
        if not ground_truth:
            return 0.0
        user_label = feedback.feedback_data.get("chosen_label", "").strip().lower()
        correct_label = ground_truth.get("chosen_label", "").strip().lower()
        return 1.0 if user_label == correct_label else 0.0

    def format_for_export(self, format_type: str) -> List[Dict[str, Any]]:
        """Format NLI data for export."""
        export_data = []
        export_entry = {
            "task_id": self.task.id,
            "task_type": self.task.task_type,
            "premise": self.task.input_data.get("premise", ""),
            "hypothesis": self.task.input_data.get("hypothesis", ""),
            "ground_truth_label": self.task.ground_truth_data.get("chosen_label", "") if self.task.ground_truth_data else ""
        }
        if format_type == "SFT":
            export_entry.update({
                "input": f"Premise: {export_entry['premise']}\nHypothesis: {export_entry['hypothesis']}\nDetermine if the hypothesis entails, contradicts, or is neutral to the premise.",
                "output": export_entry["ground_truth_label"]
            })
        elif format_type == "Preference":
            export_entry.update({
                "query": f"Premise: {export_entry['premise']}\nHypothesis: {export_entry['hypothesis']}",
                "preferred_response": export_entry["ground_truth_label"],
                "context_info": {"premise": export_entry["premise"], "hypothesis": export_entry["hypothesis"]}
            })
        export_data.append(export_entry)
        return export_data


class StatutoryRuleQAHandler(BaseTaskHandler):
    """
    Handler for Statutory Rule Question Answering tasks.
    
    Specialized handler for legal Q&A tasks involving statutory rules and regulations.
    This handler processes feedback for complex legal questions requiring analysis of
    specific legal articles, contexts, and regulatory frameworks.
    """

    def __init__(self, db: AsyncSession, task: models.LegalTask):
        super().__init__(db, task)

    async def aggregate_feedback(self) -> Dict[str, Any]:
        """Aggregates feedback for Statutory Rule QA tasks."""
        feedbacks = await self.get_feedbacks()
        if not feedbacks:
            return {"error": "No feedback available for this statutory rule QA task."}

        answer_scores = {}
        answer_details = {}
        confidence_weights = {"high": 1.0, "medium": 0.7, "low": 0.4}

        for fb in feedbacks:
            answer = fb.feedback_data.get("validated_answer", "")
            confidence = fb.feedback_data.get("confidence", "medium")
            position = fb.feedback_data.get("position", "correct")
            
            if not answer:
                continue

            normalized_answer = answer.strip().lower()
            
            if normalized_answer not in answer_scores:
                answer_scores[normalized_answer] = 0
                answer_details[normalized_answer] = {
                    "original_answers": [],
                    "supporters": [],
                    "reasoning": [],
                    "confidence_distribution": {"high": 0, "medium": 0, "low": 0},
                    "position_distribution": {"correct": 0, "partially_correct": 0, "incorrect": 0}
                }

            # Weight by authority score and confidence
            base_weight = fb.author.authority_score
            confidence_multiplier = confidence_weights.get(confidence, 0.7)
            position_multiplier = 1.0 if position == "correct" else (0.7 if position == "partially_correct" else 0.3)
            
            final_weight = base_weight * confidence_multiplier * position_multiplier
            answer_scores[normalized_answer] += final_weight

            # Collect details
            answer_details[normalized_answer]["original_answers"].append(answer)
            answer_details[normalized_answer]["supporters"].append({
                "username": fb.author.username,
                "authority": fb.author.authority_score,
                "confidence": confidence,
                "position": position
            })
            answer_details[normalized_answer]["confidence_distribution"][confidence] += 1
            answer_details[normalized_answer]["position_distribution"][position] += 1

            if "reasoning" in fb.feedback_data:
                answer_details[normalized_answer]["reasoning"].append(fb.feedback_data["reasoning"])

        if not answer_scores:
            return {"error": "No valid answers found."}

        # Sort by weighted score
        sorted_answers = sorted(answer_scores.items(), key=lambda x: x[1], reverse=True)
        best_answer_key, best_score = sorted_answers[0]
        total_weight = sum(answer_scores.values())

        # Prepare consensus answer
        best_details = answer_details[best_answer_key]
        consensus_answer = best_details["original_answers"][0] if best_details["original_answers"] else best_answer_key

        # Calculate confidence based on agreement and position distribution
        confidence = best_score / total_weight if total_weight > 0 else 0
        
        # Prepare alternative answers
        alternative_answers = []
        for answer_key, score in sorted_answers[1:3]:  # Top 2 alternatives
            details = answer_details[answer_key]
            alternative_answers.append({
                "answer": details["original_answers"][0] if details["original_answers"] else answer_key,
                "support_percentage": round((score / total_weight) * 100, 1),
                "supporter_count": len(details["supporters"]),
                "confidence_distribution": details["confidence_distribution"],
                "top_reasoning": details["reasoning"][0] if details["reasoning"] else ""
            })

        return {
            "consensus_answer": consensus_answer,
            "confidence": round(confidence, 3),
            "support_percentage": round((best_score / total_weight) * 100, 1),
            "alternative_answers": alternative_answers,
            "total_evaluators": len(feedbacks),
            "confidence_distribution": best_details["confidence_distribution"],
            "position_distribution": best_details["position_distribution"],
            "details": answer_scores
        }

    def calculate_consistency(self, feedback: models.Feedback, aggregated_result: Dict[str, Any]) -> float:
        """Calculate consistency for Statutory Rule QA."""
        user_answer = feedback.feedback_data.get("validated_answer", "").strip().lower()
        consensus_answer = aggregated_result.get("consensus_answer", "").strip().lower()

        if not user_answer or not consensus_answer:
            return 0.0

        # Enhanced consistency calculation for legal terminology
        if user_answer == consensus_answer:
            return 1.0

        # Legal term matching with higher weights
        legal_terms = {
            "applicabile", "non applicabile", "valido", "invalido", "conforme", "non conforme",
            "legittimo", "illegittimo", "responsabile", "non responsabile", "dovuto", "non dovuto",
            "ammissibile", "inammissibile", "fondato", "infondato", "prescrivibile", "imprescrivibile"
        }

        user_words = set(user_answer.split())
        consensus_words = set(consensus_answer.split())

        # Calculate weighted similarity
        total_overlap = len(user_words & consensus_words)
        total_union = len(user_words | consensus_words)
        
        legal_overlap = len((user_words & consensus_words) & legal_terms)
        legal_union = len((user_words | consensus_words) & legal_terms)

        if total_union == 0:
            return 0.0

        base_similarity = total_overlap / total_union
        legal_bonus = (legal_overlap / legal_union * 0.4) if legal_union > 0 else 0

        return min(1.0, base_similarity + legal_bonus)

    def calculate_correctness(self, feedback: models.Feedback, ground_truth: Dict[str, Any]) -> float:
        """Calculate correctness against ground truth for Statutory Rule QA."""
        if not ground_truth or "answer_text" not in ground_truth:
            return 0.0

        user_answer = feedback.feedback_data.get("validated_answer", "").strip().lower()
        ground_truth_answer = ground_truth["answer_text"].strip().lower()
        position = feedback.feedback_data.get("position", "correct")

        if not user_answer:
            return 0.0

        # Position-based scoring
        position_multiplier = {"correct": 1.0, "partially_correct": 0.7, "incorrect": 0.3}
        base_multiplier = position_multiplier.get(position, 0.5)

        # Semantic similarity with legal focus
        user_words = set(user_answer.split())
        gt_words = set(ground_truth_answer.split())

        if not gt_words:
            return base_multiplier if user_answer else 0.0

        # Weighted similarity considering legal terminology
        intersection = user_words & gt_words
        union = user_words | gt_words

        similarity = len(intersection) / len(union) if union else 0.0
        
        return min(1.0, similarity * base_multiplier)
    
    def format_for_export(self, format_type: str) -> List[Dict[str, Any]]:
        """Format Statutory Rule QA data for export."""
        # Base implementation - can be enhanced based on specific requirements
        export_data = []
        
        # Create basic export entry with task data
        export_entry = {
            "task_id": self.task.id,
            "task_type": self.task.task_type,
            "question": self.task.input_data.get("question", ""),
            "context": self.task.input_data.get("context_full", ""),
            "relevant_articles": self.task.input_data.get("relevant_articles", ""),
            "category": self.task.input_data.get("category", ""),
            "ground_truth_answer": self.task.ground_truth_data.get("answer_text", "") if self.task.ground_truth_data else ""
        }
        
        if format_type == "SFT":
            # Supervised Fine-Tuning format
            export_entry.update({
                "input": f"Question: {export_entry['question']}\nContext: {export_entry['context']}\nRelevant Articles: {export_entry['relevant_articles']}",
                "output": export_entry["ground_truth_answer"]
            })
        elif format_type == "Preference":
            # Preference learning format would require multiple responses
            export_entry.update({
                "query": export_entry["question"],
                "preferred_response": export_entry["ground_truth_answer"],
                "context_info": {
                    "context": export_entry["context"],
                    "articles": export_entry["relevant_articles"],
                    "category": export_entry["category"]
                }
            })
        
        export_data.append(export_entry)
        return export_data


class NERHandler(BaseTaskHandler):
    """
    Handler for Named Entity Recognition tasks.

    This handler implements the specific logic for aggregating feedback,
    calculating consistency, and formatting data for export related to
    named entity recognition tasks.
    """

    def __init__(self, db: AsyncSession, task: models.LegalTask):
        """
        Initializes the NERHandler with a database session and a legal task.

        Args:
            db: The SQLAlchemy async session for database operations.
            task: The LegalTask instance associated with this handler.
        """
        super().__init__(db, task)

    async def aggregate_feedback(self) -> Dict[str, Any]:
        """
        Aggregates feedback for NER tasks.

        Aggregates entity tags by position based on authority-weighted scores
        and determines consensus tags for each token position.

        Returns:
            A dictionary containing the consensus tags, confidence scores,
            and position-specific confidence metrics.
        """
        feedbacks = await self.get_feedbacks()
        if not feedbacks:
            return {"error": "No feedback available for this NER task."}

        # Aggrega tags per posizione
        tag_positions = {}

        for fb in feedbacks:
            validated_tags = fb.feedback_data.get("validated_tags", [])
            if not isinstance(validated_tags, list):
                continue

            for i, tag in enumerate(validated_tags):
                if i not in tag_positions:
                    tag_positions[i] = {}

                if tag not in tag_positions[i]:
                    tag_positions[i][tag] = 0

                tag_positions[i][tag] += fb.author.authority_score

        if not tag_positions:
            return {"error": "No valid tags found."}

        # Determina consensus tags
        consensus_tags = []
        confidence_scores = []

        max_position = max(tag_positions.keys())

        for i in range(max_position + 1):
            if i in tag_positions:
                position_tags = tag_positions[i]
                total_weight = sum(position_tags.values())

                if total_weight > 0:
                    best_tag = max(position_tags.items(), key=lambda x: x[1])
                    consensus_tags.append(best_tag[0])
                    confidence_scores.append(best_tag[1] / total_weight)
                else:
                    consensus_tags.append("O")
                    confidence_scores.append(0.0)
            else:
                consensus_tags.append("O")
                confidence_scores.append(0.0)

        avg_confidence = np.mean(confidence_scores) if confidence_scores else 0

        return {
            "consensus_answer": f"NER tags: {' '.join(consensus_tags)}",
            "confidence": round(avg_confidence, 3),
            "consensus_tags": consensus_tags,
            "position_confidence": confidence_scores,
            "details": {str(i): tags for i, tags in tag_positions.items()},
        }

    def calculate_consistency(
        self, feedback: models.Feedback, aggregated_result: Dict[str, Any]
    ) -> float:
        """Calcola consistency per NER."""
        user_tags = feedback.feedback_data.get("validated_tags", [])
        consensus_tags = aggregated_result.get("consensus_tags", [])

        if not user_tags or not consensus_tags:
            return 0.0

        # Calcola accuracy per posizione
        min_length = min(len(user_tags), len(consensus_tags))
        if min_length == 0:
            return 0.0

        matches = sum(1 for i in range(min_length) if user_tags[i] == consensus_tags[i])
        return matches / max(len(user_tags), len(consensus_tags))

    def calculate_correctness(
        self, feedback: models.Feedback, ground_truth: Dict[str, Any]
    ) -> float:
        """Calculate correctness for NER."""
        if not ground_truth:
            return 0.0
        user_tags = feedback.feedback_data.get("validated_tags", [])
        correct_tags = ground_truth.get("validated_tags", [])
        if not isinstance(user_tags, list) or not isinstance(correct_tags, list):
            return 0.0
        if len(user_tags) != len(correct_tags):
            return 0.0
        matches = sum(1 for u, c in zip(user_tags, correct_tags) if u == c)
        return matches / len(correct_tags) if correct_tags else 0.0

    def format_for_export(self, format_type: str) -> List[Dict[str, Any]]:
        """Format NER data for export."""
        export_data = []
        export_entry = {
            "task_id": self.task.id,
            "task_type": self.task.task_type,
            "text": self.task.input_data.get("text", ""),
            "tokens": self.task.input_data.get("tokens", []),
            "ground_truth_tags": self.task.ground_truth_data.get("validated_tags", []) if self.task.ground_truth_data else []
        }
        if format_type == "SFT":
            export_entry.update({
                "input": f"Label the entities in the following text:\n{export_entry['text']}",
                "output": str(export_entry["ground_truth_tags"])
            })
        elif format_type == "Preference":
            export_entry.update({
                "query": f"Identify named entities in: {export_entry['text']}",
                "preferred_response": str(export_entry["ground_truth_tags"]),
                "context_info": {"tokens": export_entry["tokens"]}
            })
        export_data.append(export_entry)
        return export_data


class DraftingHandler(BaseTaskHandler):
    """
    Handler for Legal Drafting tasks.

    This handler implements the specific logic for aggregating feedback,
    calculating consistency, and formatting data for export related to
    legal drafting tasks.
    """

    def __init__(self, db: AsyncSession, task: models.LegalTask):
        """
        Initializes the DraftingHandler with a database session and a legal task.

        Args:
            db: The SQLAlchemy async session for database operations.
            task: The LegalTask instance associated with this handler.
        """
        super().__init__(db, task)

    async def aggregate_feedback(self) -> Dict[str, Any]:
        """
        Aggregates feedback for Drafting tasks.

        Groups feedback by ratings and revisions, calculating weighted scores
        based on authority scores to determine draft quality consensus.

        Returns:
            A dictionary containing the consensus answer, confidence score,
            quality assessment, and revised drafts.
        """
        feedbacks = await self.get_feedbacks()
        if not feedbacks:
            return {"error": "No feedback available for this drafting task."}

        # Raggruppa per rating e revisioni
        rating_weights = {"better": 0, "worse": 0}
        revised_drafts = []

        for fb in feedbacks:
            rating = fb.feedback_data.get("rating")
            if rating in rating_weights:
                rating_weights[rating] += fb.author.authority_score

            revised_target = fb.feedback_data.get("revised_target")
            reasoning = fb.feedback_data.get("reasoning", "")
            if revised_target:
                revised_drafts.append(
                    {
                        "draft": revised_target,
                        "author": fb.author.username,
                        "authority": fb.author.authority_score,
                        "rating": rating,
                        "reasoning": reasoning,
                    }
                )

        total_weight = sum(rating_weights.values())
        if total_weight == 0:
            return {"error": "No valid ratings found."}

        better_percentage = (rating_weights["better"] / total_weight) * 100

        # Trova le migliori revisioni
        better_revisions = [r for r in revised_drafts if r["rating"] == "better"]
        better_revisions.sort(key=lambda x: x["authority"], reverse=True)

        if better_percentage > 60:
            consensus_answer = "Draft quality is acceptable"
        else:
            consensus_answer = (
                better_revisions[0]["draft"]
                if better_revisions
                else "Draft needs significant improvement"
            )

        return {
            "consensus_answer": consensus_answer,
            "confidence": abs(better_percentage - 50) / 50,
            "quality_assessment": {
                "better_percentage": round(better_percentage, 1),
                "worse_percentage": round(100 - better_percentage, 1),
            },
            "revised_drafts": better_revisions[:3],
            "details": rating_weights,
        }

    def calculate_consistency(
        self, feedback: models.Feedback, aggregated_result: Dict[str, Any]
    ) -> float:
        """Calcola consistency per Drafting."""
        user_rating = feedback.feedback_data.get("rating")
        quality_assessment = aggregated_result.get("quality_assessment", {})

        if not user_rating or not quality_assessment:
            return 0.0

        better_percentage = quality_assessment.get("better_percentage", 50)

        if user_rating == "better" and better_percentage > 50:
            return 1.0
        elif user_rating == "worse" and better_percentage < 50:
            return 1.0
        else:
            distance_from_threshold = abs(better_percentage - 50) / 50
            return 1 - distance_from_threshold

    def calculate_correctness(
        self, feedback: models.Feedback, ground_truth: Dict[str, Any]
    ) -> float:
        """Calcola correctness per Drafting confrontando con il target ground truth."""
        if not ground_truth or "target" not in ground_truth:
            return 0.0

        user_revision = feedback.feedback_data.get("revised_target", "").strip()
        ground_truth_target = ground_truth["target"].strip()

        if not user_revision or not ground_truth_target:
            return 0.0

        # Semantic similarity semplificata per drafting legale
        user_words = set(user_revision.lower().split())
        gt_words = set(ground_truth_target.lower().split())

        # Jaccard similarity
        intersection = len(user_words & gt_words)
        union = len(user_words | gt_words)

        if union == 0:
            return 0.0

        # Bonus per preservare termini legali chiave
        legal_terms = {
            "shall",
            "agreement",
            "party",
            "hereby",
            "whereas",
            "pursuant",
            "notwithstanding",
        }
        gt_legal_terms = gt_words & legal_terms
        user_legal_terms = user_words & legal_terms

        legal_preservation = len(gt_legal_terms & user_legal_terms) / max(
            len(gt_legal_terms), 1
        )

        base_similarity = intersection / union
        return min(1.0, base_similarity * 0.7 + legal_preservation * 0.3)

    def format_for_export(self, format_type: str) -> List[Dict[str, Any]]:
        """Format Drafting data for export."""
        export_data = []
        export_entry = {
            "task_id": self.task.id,
            "task_type": self.task.task_type,
            "source": self.task.input_data.get("source", ""),
            "task_description": self.task.input_data.get("task", ""),
            "instruction": self.task.input_data.get("instruction", ""),
            "ground_truth_draft": self.task.ground_truth_data.get("revised_target", "") if self.task.ground_truth_data else ""
        }
        if format_type == "SFT":
            export_entry.update({
                "input": f"Task: {export_entry['task_description']}\nSource: {export_entry['source']}\nInstruction: {export_entry['instruction']}",
                "output": export_entry["ground_truth_draft"]
            })
        elif format_type == "Preference":
            export_entry.update({
                "query": f"Draft legal text: {export_entry['task_description']}",
                "preferred_response": export_entry["ground_truth_draft"],
                "context_info": {"source": export_entry["source"], "instruction": export_entry["instruction"]}
            })
        export_data.append(export_entry)
        return export_data


class RiskSpottingHandler(BaseTaskHandler):
    """
    Handler for Compliance Risk Spotting tasks.

    This handler implements the specific logic for aggregating feedback,
    calculating consistency, and formatting data for export related to
    risk spotting tasks.
    """

    def __init__(self, db: AsyncSession, task: models.LegalTask):
        """
        Initializes the RiskSpottingHandler with a database session and a legal task.

        Args:
            db: The SQLAlchemy async session for database operations.
            task: The LegalTask instance associated with this handler.
        """
        super().__init__(db, task)

    async def aggregate_feedback(self) -> Dict[str, Any]:
        """
        Aggregates feedback for Risk Spotting tasks.

        Aggregates risk labels and severity scores based on authority-weighted scores
        to determine consensus risk assessment.

        Returns:
            A dictionary containing the consensus risk labels, average severity,
            and confidence metrics.
        """
        feedbacks = await self.get_feedbacks()
        if not feedbacks:
            return {"error": "No feedback available for this risk spotting task."}

        # Aggregazione per le etichette di rischio
        label_weights = Counter()
        severity_scores = []

        for fb in feedbacks:
            labels = tuple(sorted(fb.feedback_data.get("validated_risk_labels", [])))
            severity = fb.feedback_data.get("validated_severity")
            weight = fb.author.authority_score

            if labels:
                label_weights[labels] += weight
            if severity is not None:
                severity_scores.append(severity * weight)

        if not label_weights:
            return {"error": "No valid risk labels found in feedback."}

        # Calcolo del consenso
        consensus_labels = list(label_weights.most_common(1)[0][0])
        total_weight = sum(label_weights.values())
        confidence = (
            label_weights.most_common(1)[0][1] / total_weight if total_weight > 0 else 0
        )

        # Calcolo della severity media ponderata
        avg_severity = sum(severity_scores) / total_weight if total_weight > 0 else 0

        return {
            "consensus_answer": f"Risks: {', '.join(consensus_labels)}, Severity: {avg_severity:.2f}",
            "confidence": round(confidence, 3),
            "consensus_labels": consensus_labels,
            "average_severity": round(avg_severity, 2),
            "details": {"labels": dict(label_weights), "severity_score": avg_severity},
        }

    def calculate_consistency(
        self, feedback: models.Feedback, aggregated_result: Dict[str, Any]
    ) -> float:
        """Calcola consistency per Risk Spotting."""
        user_labels = set(feedback.feedback_data.get("validated_risk_labels", []))
        consensus_labels = set(aggregated_result.get("consensus_labels", []))

        if not user_labels or not consensus_labels:
            return 0.0

        # Jaccard similarity for labels
        jaccard = len(user_labels & consensus_labels) / len(
            user_labels | consensus_labels
        )
        return jaccard

    def calculate_correctness(
        self, feedback: models.Feedback, ground_truth: Dict[str, Any]
    ) -> float:
        """Calcola correctness rispetto al ground truth per Risk Spotting."""
        if not ground_truth:
            return 0.0

        user_labels = set(feedback.feedback_data.get("validated_risk_labels", []))
        gt_labels = set(ground_truth.get("risk_labels", []))

        user_severity = feedback.feedback_data.get("validated_severity")
        gt_severity = ground_truth.get("severity")

        if user_labels is None or user_severity is None:
            return 0.0

        label_correctness = 1.0 if user_labels == gt_labels else 0.0
        # Severity correctness: 1 if equal, 0.5 if diff by 1, 0 otherwise
        severity_correctness = max(0, 1 - abs(user_severity - gt_severity) / 2)

        return (label_correctness * 0.7) + (severity_correctness * 0.3)

    def format_for_export(self, format_type: str) -> List[Dict[str, Any]]:
        """Format Risk Spotting data for export."""
        export_data = []
        export_entry = {
            "task_id": self.task.id,
            "task_type": self.task.task_type,
            "text": self.task.input_data.get("text", ""),
            "ground_truth_risks": self.task.ground_truth_data.get("validated_risk_labels", []) if self.task.ground_truth_data else [],
            "ground_truth_severity": self.task.ground_truth_data.get("validated_severity", 0) if self.task.ground_truth_data else 0
        }
        if format_type == "SFT":
            export_entry.update({
                "input": f"Identify compliance risks in the following text:\n{export_entry['text']}",
                "output": f"Risks: {export_entry['ground_truth_risks']}, Severity: {export_entry['ground_truth_severity']}"
            })
        elif format_type == "Preference":
            export_entry.update({
                "query": "Identify compliance risks",
                "preferred_response": f"Risks: {export_entry['ground_truth_risks']}, Severity: {export_entry['ground_truth_severity']}",
                "context_info": {"text": export_entry["text"]}
            })
        export_data.append(export_entry)
        return export_data


class DoctrineApplicationHandler(BaseTaskHandler):
    """
    Handler for Doctrine Application tasks.

    This handler implements the specific logic for aggregating feedback,
    calculating consistency, and formatting data for export related to
    doctrine application tasks.
    """

    def __init__(self, db: AsyncSession, task: models.LegalTask):
        """
        Initializes the DoctrineApplicationHandler with a database session and a legal task.

        Args:
            db: The SQLAlchemy async session for database operations.
            task: The LegalTask instance associated with this handler.
        """
        super().__init__(db, task)

    async def aggregate_feedback(self) -> Dict[str, Any]:
        """
        Aggregates feedback for Doctrine Application tasks.

        Calculates weighted scores for admissibility labels based on authority scores
        and determines consensus doctrine application.

        Returns:
            A dictionary containing the consensus label, confidence score,
            and label distribution.
        """
        feedbacks = await self.get_feedbacks()
        if not feedbacks:
            return {
                "error": "No feedback available for this doctrine application task."
            }

        label_weights = Counter()
        for fb in feedbacks:
            label = fb.feedback_data.get("chosen_label")
            if label in ["yes", "no"]:
                label_weights[label] += fb.author.authority_score

        if not label_weights:
            return {"error": "No valid labels ('yes'/'no') found."}

        consensus_label, max_weight = label_weights.most_common(1)[0]
        total_weight = sum(label_weights.values())
        confidence = max_weight / total_weight if total_weight > 0 else 0

        return {
            "consensus_answer": f"Admissible: {consensus_label.capitalize()}",
            "confidence": round(confidence, 3),
            "consensus_label": consensus_label,
            "label_distribution": {
                label: round((weight / total_weight) * 100, 1)
                for label, weight in label_weights.items()
            },
            "details": dict(label_weights),
        }

    def calculate_consistency(
        self, feedback: models.Feedback, aggregated_result: Dict[str, Any]
    ) -> float:
        """Calcola consistency per Doctrine Application."""
        user_label = feedback.feedback_data.get("chosen_label")
        consensus_label = aggregated_result.get("consensus_label")
        return 1.0 if user_label == consensus_label else 0.0

    def calculate_correctness(
        self, feedback: models.Feedback, ground_truth: Dict[str, Any]
    ) -> float:
        """Calcola correctness rispetto al ground truth per Doctrine Application."""
        if not ground_truth:
            return 0.0
        user_label = feedback.feedback_data.get("chosen_label")
        gt_label = ground_truth.get("label")
        return 1.0 if user_label == gt_label else 0.0

    def format_for_export(self, format_type: str) -> List[Dict[str, Any]]:
        """Format Doctrine Application data for export."""
        export_data = []
        export_entry = {
            "task_id": self.task.id,
            "task_type": self.task.task_type,
            "facts": self.task.input_data.get("facts", ""),
            "question": self.task.input_data.get("question", ""),
            "ground_truth_label": self.task.ground_truth_data.get("chosen_label", "") if self.task.ground_truth_data else ""
        }
        if format_type == "SFT":
            export_entry.update({
                "input": f"Facts: {export_entry['facts']}\nQuestion: {export_entry['question']}\nApply relevant legal doctrine.",
                "output": export_entry["ground_truth_label"]
            })
        elif format_type == "Preference":
            export_entry.update({
                "query": f"Apply doctrine to: {export_entry['question']}",
                "preferred_response": export_entry["ground_truth_label"],
                "context_info": {"facts": export_entry["facts"]}
            })
        export_data.append(export_entry)
        return export_data
