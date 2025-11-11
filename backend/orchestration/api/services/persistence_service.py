"""
Persistence Service for MERL-T Orchestration API.

This module provides CRUD operations for all database models:
- Query tracking
- Query results
- User feedback
- RLCF feedback
- NER corrections

All operations are async and use SQLAlchemy 2.0 patterns.
"""

from datetime import datetime, timedelta
from typing import Any, Dict, List, Optional

from sqlalchemy import func, select, and_, or_, desc
from sqlalchemy.ext.asyncio import AsyncSession

from ..database import SessionLocal
from ..models import (
    Query,
    QueryResult,
    UserFeedback,
    RLCFFeedback,
    NERCorrection,
)


class PersistenceService:
    """
    Singleton service for database persistence operations.

    Provides async CRUD methods for all orchestration models.
    """

    _instance: Optional["PersistenceService"] = None

    def __new__(cls) -> "PersistenceService":
        """Singleton pattern: ensure only one instance exists."""
        if cls._instance is None:
            cls._instance = super().__new__(cls)
        return cls._instance

    def __init__(self):
        """Initialize persistence service."""
        if not hasattr(self, "_initialized"):
            self._initialized = True

    # ========================================================================
    # Query Operations
    # ========================================================================

    async def save_query(
        self,
        trace_id: str,
        query_text: str,
        session_id: Optional[str] = None,
        user_id: Optional[str] = None,
        query_context: Optional[Dict[str, Any]] = None,
        enriched_context: Optional[Dict[str, Any]] = None,
        options: Optional[Dict[str, Any]] = None,
    ) -> Query:
        """
        Save a new query to the database.

        Args:
            trace_id: Unique query identifier
            query_text: The user's query text
            session_id: Optional session identifier
            user_id: Optional user identifier
            query_context: Optional query context data
            enriched_context: Optional enriched context data
            options: Optional execution options

        Returns:
            Query: The created query object
        """
        async with SessionLocal() as session:
            query = Query(
                trace_id=trace_id,
                query_text=query_text,
                session_id=session_id,
                user_id=user_id,
                query_context=query_context or {},
                enriched_context=enriched_context or {},
                options=options or {},
                status="pending",
                created_at=datetime.utcnow(),
            )
            session.add(query)
            await session.commit()
            await session.refresh(query)
            return query

    async def get_query(self, trace_id: str) -> Optional[Query]:
        """
        Get a query by trace_id.

        Args:
            trace_id: Query trace identifier

        Returns:
            Query or None if not found
        """
        async with SessionLocal() as session:
            result = await session.execute(
                select(Query).where(Query.trace_id == trace_id)
            )
            return result.scalars().first()

    async def update_query_status(
        self,
        trace_id: str,
        status: str,
        started_at: Optional[datetime] = None,
        completed_at: Optional[datetime] = None,
    ) -> Optional[Query]:
        """
        Update query execution status.

        Args:
            trace_id: Query trace identifier
            status: New status ('processing', 'completed', 'failed', 'timeout')
            started_at: Optional start timestamp
            completed_at: Optional completion timestamp

        Returns:
            Updated Query or None if not found
        """
        async with SessionLocal() as session:
            result = await session.execute(
                select(Query).where(Query.trace_id == trace_id)
            )
            query = result.scalars().first()

            if query:
                query.status = status
                if started_at:
                    query.started_at = started_at
                if completed_at:
                    query.completed_at = completed_at
                query.updated_at = datetime.utcnow()

                await session.commit()
                await session.refresh(query)

            return query

    async def get_query_history(
        self,
        session_id: Optional[str] = None,
        user_id: Optional[str] = None,
        limit: int = 50,
        offset: int = 0,
    ) -> tuple[List[Query], int]:
        """
        Get paginated query history.

        Args:
            session_id: Filter by session (optional)
            user_id: Filter by user (optional)
            limit: Maximum number of results
            offset: Pagination offset

        Returns:
            Tuple of (queries list, total count)
        """
        async with SessionLocal() as session:
            # Build filter conditions
            conditions = []
            if session_id:
                conditions.append(Query.session_id == session_id)
            if user_id:
                conditions.append(Query.user_id == user_id)

            # Count query
            count_stmt = select(func.count(Query.trace_id))
            if conditions:
                count_stmt = count_stmt.where(and_(*conditions))

            count_result = await session.execute(count_stmt)
            total = count_result.scalar() or 0

            # Data query
            data_stmt = select(Query).order_by(desc(Query.created_at)).limit(limit).offset(offset)
            if conditions:
                data_stmt = data_stmt.where(and_(*conditions))

            data_result = await session.execute(data_stmt)
            queries = list(data_result.scalars().all())

            return queries, total

    # ========================================================================
    # Query Result Operations
    # ========================================================================

    async def save_query_result(
        self,
        trace_id: str,
        primary_answer: str,
        confidence: float,
        legal_basis: Optional[List[Dict[str, Any]]] = None,
        alternatives: Optional[List[Dict[str, Any]]] = None,
        uncertainty_preserved: bool = False,
        sources_consulted: Optional[List[Dict[str, Any]]] = None,
        execution_trace: Optional[Dict[str, Any]] = None,
        metadata: Optional[Dict[str, Any]] = None,
    ) -> QueryResult:
        """
        Save query result (answer and execution trace).

        Args:
            trace_id: Query trace identifier
            primary_answer: The main answer text
            confidence: Answer confidence (0.0 to 1.0)
            legal_basis: List of supporting norms
            alternatives: List of alternative answers
            uncertainty_preserved: Whether uncertainty was preserved
            sources_consulted: List of consulted sources
            execution_trace: Execution trace data
            metadata: Additional metadata

        Returns:
            QueryResult: The created query result object
        """
        async with SessionLocal() as session:
            result = QueryResult(
                trace_id=trace_id,
                primary_answer=primary_answer,
                confidence=confidence,
                legal_basis=legal_basis or [],
                alternatives=alternatives or [],
                uncertainty_preserved=uncertainty_preserved,
                sources_consulted=sources_consulted or [],
                execution_trace=execution_trace or {},
                metadata=metadata or {},
                created_at=datetime.utcnow(),
            )
            session.add(result)
            await session.commit()
            await session.refresh(result)
            return result

    async def get_query_result(self, trace_id: str) -> Optional[QueryResult]:
        """
        Get query result by trace_id.

        Args:
            trace_id: Query trace identifier

        Returns:
            QueryResult or None if not found
        """
        async with SessionLocal() as session:
            result = await session.execute(
                select(QueryResult).where(QueryResult.trace_id == trace_id)
            )
            return result.scalars().first()

    # ========================================================================
    # User Feedback Operations
    # ========================================================================

    async def save_user_feedback(
        self,
        trace_id: str,
        rating: int,
        user_id: Optional[str] = None,
        feedback_text: Optional[str] = None,
        categories: Optional[Dict[str, Any]] = None,
    ) -> UserFeedback:
        """
        Save user feedback for a query.

        Args:
            trace_id: Query trace identifier
            rating: User rating (1-5)
            user_id: Optional user identifier
            feedback_text: Optional feedback text
            categories: Optional detailed category ratings

        Returns:
            UserFeedback: The created feedback object
        """
        async with SessionLocal() as session:
            feedback = UserFeedback(
                trace_id=trace_id,
                user_id=user_id,
                rating=rating,
                feedback_text=feedback_text,
                categories=categories or {},
                created_at=datetime.utcnow(),
            )
            session.add(feedback)
            await session.commit()
            await session.refresh(feedback)
            return feedback

    async def get_user_feedback_by_trace(self, trace_id: str) -> List[UserFeedback]:
        """
        Get all user feedback for a specific query.

        Args:
            trace_id: Query trace identifier

        Returns:
            List of UserFeedback objects
        """
        async with SessionLocal() as session:
            result = await session.execute(
                select(UserFeedback).where(UserFeedback.trace_id == trace_id)
            )
            return list(result.scalars().all())

    # ========================================================================
    # RLCF Feedback Operations
    # ========================================================================

    async def save_rlcf_feedback(
        self,
        trace_id: str,
        expert_id: str,
        authority_score: float,
        corrections: Dict[str, Any],
        overall_rating: int,
        training_examples_generated: int = 0,
        scheduled_for_retraining: bool = False,
    ) -> RLCFFeedback:
        """
        Save RLCF expert feedback.

        Args:
            trace_id: Query trace identifier
            expert_id: Expert identifier
            authority_score: Expert authority score (0.0 to 1.0)
            corrections: Correction data
            overall_rating: Overall rating (1-5)
            training_examples_generated: Number of training examples
            scheduled_for_retraining: Whether retraining is scheduled

        Returns:
            RLCFFeedback: The created feedback object
        """
        async with SessionLocal() as session:
            feedback = RLCFFeedback(
                trace_id=trace_id,
                expert_id=expert_id,
                authority_score=authority_score,
                corrections=corrections,
                overall_rating=overall_rating,
                training_examples_generated=training_examples_generated,
                scheduled_for_retraining=scheduled_for_retraining,
                created_at=datetime.utcnow(),
            )
            session.add(feedback)
            await session.commit()
            await session.refresh(feedback)
            return feedback

    async def get_rlcf_feedback_count(self) -> int:
        """
        Get total count of RLCF feedback.

        Returns:
            int: Total feedback count
        """
        async with SessionLocal() as session:
            result = await session.execute(
                select(func.count(RLCFFeedback.feedback_id))
            )
            return result.scalar() or 0

    async def get_rlcf_feedback_for_retraining(self, limit: int = 100) -> List[RLCFFeedback]:
        """
        Get RLCF feedback scheduled for retraining.

        Args:
            limit: Maximum number of results

        Returns:
            List of RLCFFeedback objects
        """
        async with SessionLocal() as session:
            result = await session.execute(
                select(RLCFFeedback)
                .where(RLCFFeedback.scheduled_for_retraining == True)
                .order_by(desc(RLCFFeedback.created_at))
                .limit(limit)
            )
            return list(result.scalars().all())

    # ========================================================================
    # NER Correction Operations
    # ========================================================================

    async def save_ner_correction(
        self,
        trace_id: str,
        expert_id: str,
        correction_type: str,
        correction_data: Dict[str, Any],
        training_example_generated: bool = True,
        scheduled_for_retraining: bool = False,
    ) -> NERCorrection:
        """
        Save NER correction.

        Args:
            trace_id: Query trace identifier
            expert_id: Expert identifier
            correction_type: Type of correction
            correction_data: Correction data
            training_example_generated: Whether training example was generated
            scheduled_for_retraining: Whether retraining is scheduled

        Returns:
            NERCorrection: The created correction object
        """
        async with SessionLocal() as session:
            correction = NERCorrection(
                trace_id=trace_id,
                expert_id=expert_id,
                correction_type=correction_type,
                correction_data=correction_data,
                training_example_generated=training_example_generated,
                scheduled_for_retraining=scheduled_for_retraining,
                created_at=datetime.utcnow(),
            )
            session.add(correction)
            await session.commit()
            await session.refresh(correction)
            return correction

    async def get_ner_corrections_count(self) -> int:
        """
        Get total count of NER corrections.

        Returns:
            int: Total corrections count
        """
        async with SessionLocal() as session:
            result = await session.execute(
                select(func.count(NERCorrection.correction_id))
            )
            return result.scalar() or 0

    async def get_ner_corrections_for_retraining(self, limit: int = 100) -> List[NERCorrection]:
        """
        Get NER corrections scheduled for retraining.

        Args:
            limit: Maximum number of results

        Returns:
            List of NERCorrection objects
        """
        async with SessionLocal() as session:
            result = await session.execute(
                select(NERCorrection)
                .where(NERCorrection.scheduled_for_retraining == True)
                .order_by(desc(NERCorrection.created_at))
                .limit(limit)
            )
            return list(result.scalars().all())

    # ========================================================================
    # Statistics & Analytics
    # ========================================================================

    async def get_pipeline_stats(self, days: int = 7) -> Dict[str, Any]:
        """
        Get pipeline performance statistics.

        Args:
            days: Number of days to include in stats

        Returns:
            Dict with pipeline metrics
        """
        async with SessionLocal() as session:
            since = datetime.utcnow() - timedelta(days=days)

            # Total queries
            total_result = await session.execute(
                select(func.count(Query.trace_id))
                .where(Query.created_at >= since)
            )
            total_queries = total_result.scalar() or 0

            # Completed queries
            completed_result = await session.execute(
                select(func.count(Query.trace_id))
                .where(and_(
                    Query.created_at >= since,
                    Query.status == "completed"
                ))
            )
            completed_queries = completed_result.scalar() or 0

            # Average confidence
            confidence_result = await session.execute(
                select(func.avg(QueryResult.confidence))
                .join(Query, Query.trace_id == QueryResult.trace_id)
                .where(Query.created_at >= since)
            )
            avg_confidence = float(confidence_result.scalar() or 0.0)

            # Success rate
            success_rate = (completed_queries / total_queries) if total_queries > 0 else 0.0

            return {
                "total_queries": total_queries,
                "completed_queries": completed_queries,
                "success_rate": success_rate,
                "avg_confidence": avg_confidence,
                "period_days": days,
            }

    async def get_feedback_stats(self, days: int = 30) -> Dict[str, Any]:
        """
        Get feedback statistics.

        Args:
            days: Number of days to include in stats

        Returns:
            Dict with feedback metrics
        """
        async with SessionLocal() as session:
            since = datetime.utcnow() - timedelta(days=days)

            # User feedback count
            user_feedback_result = await session.execute(
                select(func.count(UserFeedback.feedback_id))
                .where(UserFeedback.created_at >= since)
            )
            user_feedback_count = user_feedback_result.scalar() or 0

            # Average user rating
            avg_rating_result = await session.execute(
                select(func.avg(UserFeedback.rating))
                .where(UserFeedback.created_at >= since)
            )
            avg_user_rating = float(avg_rating_result.scalar() or 0.0)

            # RLCF feedback count
            rlcf_feedback_result = await session.execute(
                select(func.count(RLCFFeedback.feedback_id))
                .where(RLCFFeedback.created_at >= since)
            )
            rlcf_feedback_count = rlcf_feedback_result.scalar() or 0

            # NER corrections count
            ner_corrections_result = await session.execute(
                select(func.count(NERCorrection.correction_id))
                .where(NERCorrection.created_at >= since)
            )
            ner_corrections_count = ner_corrections_result.scalar() or 0

            return {
                "user_feedback_count": user_feedback_count,
                "avg_user_rating": avg_user_rating,
                "rlcf_feedback_count": rlcf_feedback_count,
                "ner_corrections_count": ner_corrections_count,
                "period_days": days,
            }


# ============================================================================
# Singleton Instance
# ============================================================================

# Global singleton instance
persistence_service = PersistenceService()
