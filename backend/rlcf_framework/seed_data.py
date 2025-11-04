"""
Seed Data Generator for RLCF Framework.

Generates realistic test data for development and testing:
- Users with diverse credentials
- Tasks across all task types
- Responses from AI models
- Feedback from evaluators with varied positions
- Bias reports for analysis

Usage:
    python -m rlcf_framework.seed_data [--reset]
"""

import asyncio
import argparse
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
import random
from datetime import datetime, timedelta

from .database import SessionLocal, Base, engine
from . import models
from .models import TaskType, TaskStatus


# Sample data for realistic generation
SAMPLE_USERS = [
    {"username": "alice_lawyer", "degree": "JD", "experience": "15"},
    {"username": "bob_professor", "degree": "PhD", "experience": "20"},
    {"username": "carol_paralegal", "degree": "Bachelor", "experience": "5"},
    {"username": "david_judge", "degree": "JD", "experience": "25"},
    {"username": "eve_researcher", "degree": "PhD", "experience": "10"},
    {"username": "frank_attorney", "degree": "LLM", "experience": "8"},
    {"username": "grace_clerk", "degree": "Bachelor", "experience": "3"},
    {"username": "henry_counsel", "degree": "JD", "experience": "12"},
    {"username": "iris_consultant", "degree": "LLM", "experience": "7"},
    {"username": "jack_advocate", "degree": "JD", "experience": "18"},
]

SAMPLE_QA_TASKS = [
    {
        "question": "What constitutes a valid contract?",
        "context": "A contract requires offer, acceptance, and consideration.",
        "validated_answer": "A valid contract requires mutual assent (offer and acceptance), consideration, capacity, and legality of purpose."
    },
    {
        "question": "Can a minor enter into a binding contract?",
        "context": "Minors are generally protected from contractual obligations.",
        "validated_answer": "Generally no, contracts with minors are voidable at the minor's option, except for necessaries."
    },
    {
        "question": "What is the statute of limitations for breach of contract?",
        "context": "Time limits vary by jurisdiction and contract type.",
        "validated_answer": "Typically 3-6 years for written contracts, 1-3 years for oral contracts, varying by jurisdiction."
    },
]

SAMPLE_STATUTORY_RULE_QA = [
    {
        "question": "What are the requirements for corporate formation?",
        "rule_id": "CORP-001",
        "context_full": "Corporate formation requires filing articles of incorporation...",
        "relevant_articles": "Article 101, Article 102",
        "category": "Corporate Law",
        "validated_answer": "Must file articles of incorporation, appoint directors, issue stock, and adopt bylaws."
    },
    {
        "question": "When is a search warrant required?",
        "rule_id": "CRIM-042",
        "context_full": "Fourth Amendment protections against unreasonable search...",
        "relevant_articles": "Amendment IV",
        "category": "Criminal Law",
        "validated_answer": "A warrant is required unless an exception applies (consent, exigent circumstances, plain view, etc.)."
    },
]


async def create_users(db: AsyncSession) -> list:
    """Create sample users with credentials."""
    users = []

    for user_data in SAMPLE_USERS:
        user = models.User(
            username=user_data["username"],
            authority_score=random.uniform(0.5, 0.9),
            track_record_score=random.uniform(0.6, 0.95),
            baseline_credential_score=random.uniform(0.5, 0.8)
        )
        db.add(user)
        await db.flush()

        # Add academic degree credential
        degree_cred = models.Credential(
            user_id=user.id,
            type="ACADEMIC_DEGREE",
            value=user_data["degree"],
            weight=0.3
        )
        db.add(degree_cred)

        # Add professional experience credential
        exp_cred = models.Credential(
            user_id=user.id,
            type="PROFESSIONAL_EXPERIENCE",
            value=user_data["experience"],
            weight=0.4
        )
        db.add(exp_cred)

        users.append(user)

    await db.commit()
    print(f"✅ Created {len(users)} users with credentials")
    return users


async def create_qa_tasks(db: AsyncSession) -> list:
    """Create QA tasks with responses and feedback."""
    tasks = []

    for task_data in SAMPLE_QA_TASKS:
        task = models.LegalTask(
            task_type=TaskType.QA.value,
            input_data={
                "question": task_data["question"],
                "context": task_data["context"]
            },
            ground_truth_data={
                "validated_answer": task_data["validated_answer"]
            },
            status=TaskStatus.BLIND_EVALUATION
        )
        db.add(task)
        await db.flush()

        # Create AI response
        response = models.Response(
            task_id=task.id,
            output_data={"answer": f"AI response to: {task_data['question']}"},
            model_version="gpt-3.5-turbo-seed"
        )
        db.add(response)
        await db.flush()

        # Create feedback from multiple users
        result = await db.execute(select(models.User))
        all_users = result.scalars().all()

        # Select 3-5 random evaluators
        evaluators = random.sample(all_users, random.randint(3, 5))

        for evaluator in evaluators:
            # Vary the feedback positions
            positions = ["agree", "partially_agree", "disagree"]
            feedback = models.Feedback(
                user_id=evaluator.id,
                response_id=response.id,
                is_blind_phase=True,
                accuracy_score=random.uniform(0.6, 0.95),
                utility_score=random.uniform(0.6, 0.9),
                transparency_score=random.uniform(0.7, 0.95),
                feedback_data={
                    "validated_answer": task_data["validated_answer"] if random.random() > 0.3 else "Alternative answer",
                    "position": random.choice(positions),
                    "reasoning": f"Evaluation by {evaluator.username}",
                    "confidence": random.choice(["high", "medium", "low"])
                },
                community_helpfulness_rating=random.randint(3, 5),
                consistency_score=random.uniform(0.7, 0.95)
            )
            db.add(feedback)

        tasks.append(task)

    await db.commit()
    print(f"✅ Created {len(tasks)} QA tasks with responses and feedback")
    return tasks


async def create_statutory_rule_qa_tasks(db: AsyncSession) -> list:
    """Create STATUTORY_RULE_QA tasks."""
    tasks = []

    for task_data in SAMPLE_STATUTORY_RULE_QA:
        task = models.LegalTask(
            task_type=TaskType.STATUTORY_RULE_QA.value,
            input_data={
                "question": task_data["question"],
                "rule_id": task_data["rule_id"],
                "context_full": task_data["context_full"],
                "context_count": 1,
                "relevant_articles": task_data["relevant_articles"],
                "category": task_data["category"],
                "tags": "legal, statute",
                "metadata_full": "{}"
            },
            ground_truth_data={
                "validated_answer": task_data["validated_answer"]
            },
            status=TaskStatus.BLIND_EVALUATION
        )
        db.add(task)
        await db.flush()

        # Create response
        response = models.Response(
            task_id=task.id,
            output_data={"answer": f"Legal analysis of {task_data['rule_id']}"},
            model_version="legal-llm-v1"
        )
        db.add(response)
        await db.flush()

        # Create feedback
        result = await db.execute(select(models.User))
        all_users = result.scalars().all()
        evaluators = random.sample(all_users, random.randint(4, 6))

        for evaluator in evaluators:
            feedback = models.Feedback(
                user_id=evaluator.id,
                response_id=response.id,
                is_blind_phase=True,
                accuracy_score=random.uniform(0.7, 0.95),
                utility_score=random.uniform(0.6, 0.9),
                transparency_score=random.uniform(0.7, 0.95),
                feedback_data={
                    "validated_answer": task_data["validated_answer"],
                    "position": random.choice(["agree", "partially_agree"]),
                    "reasoning": f"Legal assessment by {evaluator.username}",
                    "legal_accuracy": random.choice(["high", "medium"]),
                    "citation_quality": random.choice(["excellent", "good"])
                },
                community_helpfulness_rating=random.randint(4, 5)
            )
            db.add(feedback)

        tasks.append(task)

    await db.commit()
    print(f"✅ Created {len(tasks)} STATUTORY_RULE_QA tasks")
    return tasks


async def create_bias_reports(db: AsyncSession) -> list:
    """Create sample bias reports for analysis."""
    result = await db.execute(select(models.LegalTask))
    tasks = result.scalars().all()

    result = await db.execute(select(models.User))
    users = result.scalars().all()

    reports = []
    bias_types = [
        "PROFESSIONAL_CLUSTERING",
        "DEMOGRAPHIC",
        "TEMPORAL_DRIFT",
        "CONFIRMATION_BIAS",
        "ANCHORING_BIAS"
    ]

    # Create bias reports for some tasks
    for task in random.sample(tasks, min(5, len(tasks))):
        for user in random.sample(users, 2):
            bias_type = random.choice(bias_types)
            bias_report = models.BiasReport(
                task_id=task.id,
                user_id=user.id,
                bias_type=bias_type,
                bias_score=random.uniform(0.1, 0.7),
                analysis_details={
                    "detected_at": datetime.now().isoformat(),
                    "severity": random.choice(["low", "medium", "high"]),
                    "recommendation": "Monitor evaluator diversity"
                }
            )
            db.add(bias_report)
            reports.append(bias_report)

    await db.commit()
    print(f"✅ Created {len(reports)} bias reports")
    return reports


async def seed_database(reset: bool = False):
    """
    Seed the database with sample data.

    Args:
        reset: If True, drop all tables and recreate
    """
    print("🌱 Starting database seeding...")

    if reset:
        print("⚠️  Resetting database (dropping all tables)...")
        async with engine.begin() as conn:
            await conn.run_sync(Base.metadata.drop_all)
            await conn.run_sync(Base.metadata.create_all)
        print("✅ Database reset complete")

    async with SessionLocal() as db:
        # Check if database already has data
        result = await db.execute(select(models.User))
        existing_users = result.scalars().all()

        if existing_users and not reset:
            print(f"⚠️  Database already contains {len(existing_users)} users.")
            print("   Use --reset to clear and reseed.")
            return

        # Create seed data
        users = await create_users(db)
        qa_tasks = await create_qa_tasks(db)
        statutory_tasks = await create_statutory_rule_qa_tasks(db)
        bias_reports = await create_bias_reports(db)

        # Summary
        print("\n📊 Seed Data Summary:")
        print(f"   Users: {len(users)}")
        print(f"   QA Tasks: {len(qa_tasks)}")
        print(f"   Statutory Rule QA Tasks: {len(statutory_tasks)}")
        print(f"   Bias Reports: {len(bias_reports)}")
        print("\n🎉 Database seeding complete!")


def main():
    """CLI entry point for seed data generation."""
    parser = argparse.ArgumentParser(description="Seed RLCF database with sample data")
    parser.add_argument(
        "--reset",
        action="store_true",
        help="Reset database before seeding (WARNING: deletes all data)"
    )
    args = parser.parse_args()

    asyncio.run(seed_database(reset=args.reset))


if __name__ == "__main__":
    main()
