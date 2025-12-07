import json
from typing import List, Dict, Any
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from . import models
from .models import TaskType


def format_sft_summarization(
    task: models.LegalTask, response: models.Response, feedback: models.Feedback
) -> dict:
    # SFT for summarization: Instruction + Document -> Revised Summary
    # Assumes input_data and feedback_data are already validated by schemas
    instruction = "Summarize the following document accurately and concisely."
    return {
        "instruction": instruction,
        "input": task.input_data.get("document"),
        "output": feedback.feedback_data.get("revised_summary"),
    }


def format_sft_classification(
    task: models.LegalTask, response: models.Response, feedback: models.Feedback
) -> dict:
    # SFT for classification: Text + Unit -> Validated Labels
    instruction = f"Classify the following text unit: {task.input_data.get("unit")}"
    return {
        "instruction": instruction,
        "input": task.input_data.get("text"),
        "output": ", ".join(feedback.feedback_data.get("validated_labels", [])),
    }


def format_sft_qa(
    task: models.LegalTask, response: models.Response, feedback: models.Feedback
) -> dict:
    # SFT for QA: Context + Question -> Validated Answer
    instruction = f"Answer the following question based on the provided context: {task.input_data.get("question")}"
    return {
        "instruction": instruction,
        "input": task.input_data.get("context"),
        "output": feedback.feedback_data.get("validated_answer"),
    }


def format_sft_prediction(
    task: models.LegalTask, response: models.Response, feedback: models.Feedback
) -> dict:
    # SFT for Prediction: Facts -> Chosen Outcome
    instruction = "Predict the outcome based on the given facts."
    return {
        "instruction": instruction,
        "input": task.input_data.get("facts"),
        "output": feedback.feedback_data.get("chosen_outcome"),
    }


def format_sft_nli(
    task: models.LegalTask, response: models.Response, feedback: models.Feedback
) -> dict:
    # SFT for NLI: Premise + Hypothesis -> Chosen Label
    instruction = f"Determine the relationship between the premise and hypothesis (entailment, contradiction, or neutral). Premise: {task.input_data.get("premise")}"
    return {
        "instruction": instruction,
        "input": task.input_data.get("hypothesis"),
        "output": feedback.feedback_data.get("chosen_label"),
    }


def format_sft_ner(
    task: models.LegalTask, response: models.Response, feedback: models.Feedback
) -> dict:
    # SFT for NER: Tokens -> Validated Tags
    instruction = "Identify and tag named entities in the following sequence of tokens."
    return {
        "instruction": instruction,
        "input": " ".join(task.input_data.get("tokens", [])),
        "output": " ".join(feedback.feedback_data.get("validated_tags", [])),
    }


def format_sft_drafting(
    task: models.LegalTask, response: models.Response, feedback: models.Feedback
) -> dict:
    # SFT for Drafting: Source + Instruction -> Revised Target
    instruction = f"Revise the following text based on the instruction: {task.input_data.get("instruction")}"
    return {
        "instruction": instruction,
        "input": task.input_data.get("source"),
        "output": feedback.feedback_data.get("revised_target"),
    }


def format_sft_risk_spotting(
    task: models.LegalTask, response: models.Response, feedback: models.Feedback
) -> dict:
    # SFT for risk spotting: Text -> Validated Labels and Severity
    instruction = (
        "Identify compliance risks in the following text and assign a severity score."
    )
    labels = feedback.feedback_data.get("validated_risk_labels", [])
    severity = feedback.feedback_data.get("validated_severity", 0)
    return {
        "instruction": instruction,
        "input": task.input_data.get("text"),
        "output": f"Risks: {', '.join(labels)}, Severity: {severity}",
    }


def format_sft_doctrine_application(
    task: models.LegalTask, response: models.Response, feedback: models.Feedback
) -> dict:
    # SFT for doctrine application: Facts + Question -> Chosen Label
    instruction = f"Apply legal doctrine to answer the following question based on the facts: {task.input_data.get("question")}"
    return {
        "instruction": instruction,
        "input": task.input_data.get("facts"),
        "output": feedback.feedback_data.get("chosen_label"),
    }


SFT_FORMATTERS = {
    TaskType.SUMMARIZATION: format_sft_summarization,
    TaskType.CLASSIFICATION: format_sft_classification,
    TaskType.QA: format_sft_qa,
    TaskType.PREDICTION: format_sft_prediction,
    TaskType.NLI: format_sft_nli,
    TaskType.NER: format_sft_ner,
    TaskType.DRAFTING: format_sft_drafting,
    TaskType.RISK_SPOTTING: format_sft_risk_spotting,
    TaskType.DOCTRINE_APPLICATION: format_sft_doctrine_application,
}

# --- Preference (RLHF) Formatters ---


def format_preference_drafting(
    task: models.LegalTask, response: models.Response, feedback: models.Feedback
) -> dict:
    # Preference for drafting: Source + Instruction -> Chosen (revised_target) vs Rejected (original target)
    # Assumes input_data and feedback_data are already validated by schemas
    original_target = response.output_data.get("target")
    if not original_target:
        return None

    prompt = f"Revise the following text based on the instruction: {task.input_data.get("instruction")}\nSource: {task.input_data.get("source")}"

    if feedback.feedback_data.get("rating") == "better":
        return {
            "prompt": prompt,
            "chosen": feedback.feedback_data.get("revised_target"),
            "rejected": original_target,
        }
    elif feedback.feedback_data.get("rating") == "worse":
        return {
            "prompt": prompt,
            "chosen": original_target,
            "rejected": feedback.feedback_data.get("revised_target"),
        }
    return None


# Add more preference formatters as needed
PREFERENCE_FORMATTERS = {
    TaskType.DRAFTING: format_preference_drafting,
}

async def get_export_data(
    db: AsyncSession, task_type: TaskType, export_format: str
) -> List[Dict[str, Any]]:
    """Recupera e formatta i dati per l'esportazione senza scrivere su file."""
    query = select(models.LegalTask).filter(
        models.LegalTask.task_type == task_type.value
    )
    result = await db.execute(query)
    tasks = result.scalars().all()

    exported_records = []

    for task in tasks:
        response_result = await db.execute(
            select(models.Response).filter(models.Response.task_id == task.id)
        )
        response = response_result.scalars().first()
        if not response:
            continue

        feedback_result = await db.execute(
            select(models.Feedback).filter(models.Feedback.response_id == response.id)
        )
        feedbacks = feedback_result.scalars().all()

        for feedback in feedbacks:
            record = None
            if export_format == "sft":
                formatter = SFT_FORMATTERS.get(task_type)
                if formatter:
                    record = formatter(task, response, feedback)
            elif export_format == "preference":
                formatter = PREFERENCE_FORMATTERS.get(task_type)
                if formatter:
                    record = formatter(task, response, feedback)

            if record:
                exported_records.append(record)

    return exported_records

