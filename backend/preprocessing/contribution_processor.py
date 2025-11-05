"""
Community Contribution Processor
=================================

Processes community contributions through voting workflow:

Workflow:
1. Contribution uploaded → Status: PENDING
2. System validates format/content
3. Enter voting window (7 days) → Status: VOTING
4. Community votes (up/down/skip)
5. Auto-decision:
   - >= 10 net upvotes → Auto-APPROVED → Add to Neo4j
   - < 0 net votes → Auto-REJECTED
   - 0-9 net votes after 7 days → Manual EXPERT_REVIEW
6. If APPROVED: create Contribution node in Neo4j + Author reputation tracking
7. Track citation count, view count

Features:
- 7-day voting window management
- Threshold checking
- Expert review escalation
- Plagiarism detection (optional)
- Author reputation system
- Neo4j ingestion
"""

import asyncio
import logging
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Tuple
from enum import Enum

from sqlalchemy import select, func, and_
from sqlalchemy.ext.asyncio import AsyncSession
from neo4j import AsyncDriver

from backend.preprocessing.models_kg import Contribution, ContributionTypeEnum
from backend.preprocessing.config.kg_config import KGConfig

logger = logging.getLogger(__name__)


class ContributionStatus(str, Enum):
    """Contribution status in workflow."""
    PENDING = "pending"  # Just uploaded, awaiting format validation
    VOTING = "voting"  # In 7-day voting window
    EXPERT_REVIEW = "expert_review"  # Awaiting expert decision
    APPROVED = "approved"  # Added to Neo4j
    REJECTED = "rejected"  # Deleted or archived
    ARCHIVED = "archived"  # Old contribution, archived


class ContributionProcessor:
    """
    Processes community contributions through voting and approval workflow.

    Responsibilities:
    - Validate contribution format
    - Manage voting windows
    - Auto-approve/reject based on thresholds
    - Escalate to expert review
    - Ingest approved contributions to Neo4j
    - Track author reputation
    """

    def __init__(
        self,
        neo4j_driver: AsyncDriver,
        db_session: AsyncSession,
        config: KGConfig
    ):
        """
        Initialize processor.

        Args:
            neo4j_driver: Neo4j async driver
            db_session: PostgreSQL async session
            config: KG configuration
        """
        self.neo4j_driver = neo4j_driver
        self.db_session = db_session
        self.config = config
        self.logger = logger

        self.voting_window_days = config.contributions.get("voting_window_days", 7)
        self.auto_approve_threshold = config.contributions.get("auto_approve_threshold", 10)
        self.expert_review_sla_days = config.contributions.get("expert_review_sla_days", 14)

    # ==========================================
    # Main Processing Methods
    # ==========================================

    async def process_new_contribution(
        self,
        contribution_id: str,
        author_id: str,
        title: str,
        content_type: ContributionTypeEnum,
        content_text: str
    ) -> Tuple[bool, Dict]:
        """
        Process newly uploaded contribution.

        Workflow:
        1. Validate format & content
        2. Check for plagiarism (optional)
        3. Create in PENDING status
        4. Set voting window
        5. Return result

        Args:
            contribution_id: Unique contribution ID
            author_id: Author user ID
            title: Contribution title
            content_type: Type of contribution
            content_text: Full content text

        Returns:
            (success, metadata) tuple
        """
        try:
            # Validate format
            validation_result = self._validate_contribution(content_text)
            if not validation_result["valid"]:
                self.logger.warning(f"Contribution {contribution_id} failed validation: {validation_result['reason']}")
                return False, {"error": validation_result["reason"]}

            # Optional: plagiarism check
            if self.config.contributions.get("enable_plagiarism_check"):
                plagiarism_score = await self._check_plagiarism(content_text)
                if plagiarism_score > self.config.contributions.get("plagiarism_threshold", 0.85):
                    self.logger.warning(f"Contribution {contribution_id} flagged for plagiarism: {plagiarism_score}")
                    return False, {"error": f"Plagiarism detected (score: {plagiarism_score:.2f})"}

            # Create contribution record
            voting_end_date = datetime.utcnow() + timedelta(days=self.voting_window_days)

            contribution = Contribution(
                id=contribution_id,
                author_id=author_id,
                titolo=title,
                tipo=content_type,
                content_text=content_text,
                status=ContributionStatus.VOTING.value,
                confidence=0.5,  # Initial confidence from content quality
                submission_date=datetime.utcnow(),
                voting_end_date=voting_end_date,
                upvote_count=0,
                downvote_count=0
            )

            self.db_session.add(contribution)
            await self.db_session.commit()

            self.logger.info(f"Created contribution {contribution_id} in VOTING status")

            return True, {
                "contribution_id": contribution_id,
                "status": "voting",
                "voting_end_date": voting_end_date.isoformat(),
                "days_remaining": self.voting_window_days
            }

        except Exception as e:
            self.logger.error(f"Error processing contribution: {str(e)}", exc_info=True)
            await self.db_session.rollback()
            return False, {"error": str(e)}

    async def process_vote(
        self,
        contribution_id: str,
        voter_id: str,
        vote: int,  # -1, 0, 1
        comment: Optional[str] = None
    ) -> Tuple[bool, Dict]:
        """
        Process user vote on contribution.

        Args:
            contribution_id: Contribution ID
            voter_id: User voting
            vote: -1 (down), 0 (skip), 1 (up)
            comment: Optional comment

        Returns:
            (success, result) tuple
        """
        try:
            # Get contribution
            query = select(Contribution).where(Contribution.id == contribution_id)
            result = await self.db_session.execute(query)
            contribution = result.scalar()

            if not contribution:
                return False, {"error": "Contribution not found"}

            # Check voting window still open
            if datetime.utcnow() > contribution.voting_end_date:
                return False, {"error": "Voting window closed"}

            # Register vote
            if vote == 1:
                contribution.upvote_count += 1
            elif vote == -1:
                contribution.downvote_count += 1

            contribution.net_votes = contribution.upvote_count - contribution.downvote_count

            # Check for auto-approval/rejection
            auto_action = await self._check_auto_decision(contribution)
            if auto_action:
                self.logger.info(f"Contribution {contribution_id}: {auto_action['action']}")
                contribution.status = auto_action["new_status"]
                contribution.approval_date = datetime.utcnow()

            await self.db_session.commit()

            return True, {
                "contribution_id": contribution_id,
                "new_upvotes": contribution.upvote_count,
                "new_downvotes": contribution.downvote_count,
                "net_votes": contribution.net_votes,
                "auto_approved": auto_action is not None
            }

        except Exception as e:
            self.logger.error(f"Error processing vote: {str(e)}")
            await self.db_session.rollback()
            return False, {"error": str(e)}

    async def process_voting_window_closures(self) -> Dict:
        """
        Process contributions with closed voting windows.

        Runs daily to:
        - Find contributions where voting_end_date passed
        - Apply auto-approval/rejection rules
        - Escalate ambiguous to expert review

        Returns:
            Statistics dict
        """
        stats = {
            "processed": 0,
            "auto_approved": 0,
            "auto_rejected": 0,
            "escalated_to_expert": 0,
            "errors": 0
        }

        try:
            # Find contributions with closed voting windows
            now = datetime.utcnow()
            query = select(Contribution).where(
                and_(
                    Contribution.voting_end_date <= now,
                    Contribution.status == ContributionStatus.VOTING.value
                )
            )

            result = await self.db_session.execute(query)
            contributions = result.scalars().all()

            self.logger.info(f"Processing {len(contributions)} closed voting windows")

            for contribution in contributions:
                try:
                    auto_action = await self._check_auto_decision(contribution)

                    if auto_action:
                        contribution.status = auto_action["new_status"]
                        contribution.approval_date = datetime.utcnow()

                        if auto_action["action"] == "approved":
                            stats["auto_approved"] += 1
                            # Ingest to Neo4j
                            await self._ingest_to_neo4j(contribution)
                        elif auto_action["action"] == "rejected":
                            stats["auto_rejected"] += 1
                    else:
                        # Escalate to expert review
                        contribution.status = ContributionStatus.EXPERT_REVIEW.value
                        stats["escalated_to_expert"] += 1

                    stats["processed"] += 1

                except Exception as e:
                    self.logger.error(f"Error processing contribution {contribution.id}: {str(e)}")
                    stats["errors"] += 1

            await self.db_session.commit()

        except Exception as e:
            self.logger.error(f"Error in voting window closures: {str(e)}", exc_info=True)
            await self.db_session.rollback()

        self.logger.info(f"Voting window closure stats: {stats}")
        return stats

    # ==========================================
    # Decision Logic
    # ==========================================

    async def _check_auto_decision(self, contribution: Contribution) -> Optional[Dict]:
        """
        Check if contribution should auto-approve/reject.

        Decision rules:
        - If net_votes >= auto_approve_threshold (10) → APPROVED
        - If net_votes < 0 → REJECTED
        - Otherwise → None (escalate to expert)

        Args:
            contribution: Contribution to evaluate

        Returns:
            {action, new_status} dict or None
        """
        net_votes = contribution.upvote_count - contribution.downvote_count

        if net_votes >= self.auto_approve_threshold:
            return {"action": "approved", "new_status": ContributionStatus.APPROVED.value}
        elif net_votes < 0:
            return {"action": "rejected", "new_status": ContributionStatus.REJECTED.value}
        else:
            return None  # Escalate to expert review

    # ==========================================
    # Validation Methods
    # ==========================================

    def _validate_contribution(self, content: str) -> Dict:
        """
        Validate contribution format and content quality.

        Checks:
        - Minimum content length (e.g., 100 words)
        - Maximum content length (e.g., 50,000 words)
        - Acceptable file types (inferred from content)
        - No obvious errors (formatting, etc)

        Args:
            content: Contribution text

        Returns:
            {valid: bool, reason: str} dict
        """
        if not content:
            return {"valid": False, "reason": "Content is empty"}

        word_count = len(content.split())

        min_words = self.config.contributions.get("min_content_length_words", 100)
        max_words = self.config.contributions.get("max_content_length_words", 50000)

        if word_count < min_words:
            return {"valid": False, "reason": f"Content too short ({word_count} < {min_words} words)"}

        if word_count > max_words:
            return {"valid": False, "reason": f"Content too long ({word_count} > {max_words} words)"}

        return {"valid": True}

    async def _check_plagiarism(self, content: str) -> float:
        """
        Check contribution for plagiarism.

        Returns:
            Plagiarism score (0-1, where 1 is complete plagiarism)
        """
        # In production: call plagiarism detection API (Turnitin, Copyscape, etc)
        # For now: return 0 (no plagiarism detected)
        return 0.0

    # ==========================================
    # Neo4j Ingestion
    # ==========================================

    async def _ingest_to_neo4j(self, contribution: Contribution) -> bool:
        """
        Add approved contribution to Neo4j graph.

        Creates:
        - Contribution node
        - Author node (if not exists)
        - Links to relevant norms/concepts

        Args:
            contribution: Approved contribution

        Returns:
            True if successful
        """
        try:
            async with self.neo4j_driver.session() as session:
                # Create Contribution node
                query = """
                CREATE (c:Contribution {
                    node_id: $node_id,
                    titolo: $titolo,
                    tipo: $tipo,
                    author_id: $author_id,
                    upvote_count: $upvotes,
                    downvote_count: $downvotes,
                    submission_date: datetime($submission_date),
                    confidence: $confidence,
                    expert_reviewed: false,
                    created_at: datetime()
                })
                RETURN c.node_id as id
                """

                await session.run(
                    query,
                    node_id=contribution.id,
                    titolo=contribution.titolo,
                    tipo=contribution.tipo.value,
                    author_id=contribution.author_id,
                    upvotes=contribution.upvote_count,
                    downvotes=contribution.downvote_count,
                    submission_date=contribution.submission_date.isoformat(),
                    confidence=contribution.confidence
                )

                # Set Neo4j node ID
                contribution.neo4j_node_id = contribution.id

                self.logger.info(f"Ingested contribution {contribution.id} to Neo4j")
                return True

        except Exception as e:
            self.logger.error(f"Error ingesting to Neo4j: {str(e)}", exc_info=True)
            return False

    # ==========================================
    # Author Reputation Tracking
    # ==========================================

    async def update_author_reputation(
        self,
        author_id: str,
        contribution_result: str  # "approved", "rejected"
    ) -> float:
        """
        Update author reputation score based on contribution outcome.

        Reputation:
        - Approved contribution: +1.0
        - Rejected contribution: -0.5
        - Expert review passed: +0.75
        - Plagiarism detected: -2.0

        Args:
            author_id: Author user ID
            contribution_result: Outcome of contribution

        Returns:
            New reputation score
        """
        # In production: implement author reputation system
        # For now: return placeholder
        return 1.0

    # ==========================================
    # Statistics Methods
    # ==========================================

    async def get_contribution_stats(self) -> Dict:
        """Get contribution statistics."""
        try:
            query_pending = select(func.count()).select_from(Contribution).where(
                Contribution.status == ContributionStatus.PENDING.value
            )
            query_voting = select(func.count()).select_from(Contribution).where(
                Contribution.status == ContributionStatus.VOTING.value
            )
            query_approved = select(func.count()).select_from(Contribution).where(
                Contribution.status == ContributionStatus.APPROVED.value
            )

            result_pending = await self.db_session.execute(query_pending)
            result_voting = await self.db_session.execute(query_voting)
            result_approved = await self.db_session.execute(query_approved)

            return {
                "pending": result_pending.scalar(),
                "voting": result_voting.scalar(),
                "approved": result_approved.scalar(),
                "total": (result_pending.scalar() + result_voting.scalar() + result_approved.scalar())
            }

        except Exception as e:
            self.logger.error(f"Error getting stats: {str(e)}")
            return {}


# ==========================================
# Scheduler Integration
# ==========================================

async def schedule_voting_closure_processor(
    processor: ContributionProcessor,
    interval_hours: int = 24
) -> None:
    """
    Schedule periodic voting window closure processing.

    Args:
        processor: ContributionProcessor instance
        interval_hours: How often to process (default: daily)
    """
    while True:
        try:
            await asyncio.sleep(interval_hours * 3600)
            stats = await processor.process_voting_window_closures()
            logger.info(f"Voting closure processing complete: {stats}")
        except Exception as e:
            logger.error(f"Error in scheduled processor: {str(e)}", exc_info=True)
