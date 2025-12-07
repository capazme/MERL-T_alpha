"""
Database configuration for RLCF Framework.

Provides SQLAlchemy base class and session management for
RLCF models (Tasks, Feedback, Users, etc.).

References:
    RLCF.md Section 4 - Data Storage
    docs/02-methodology/rlcf/technical/database-schema.md
"""

from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker, declarative_base
from typing import Optional
import os

# SQLAlchemy declarative base for all RLCF models
Base = declarative_base()

# Default database URL (SQLite for development)
DEFAULT_DATABASE_URL = "sqlite:///rlcf.db"

# Module-level engine and session factory
_engine = None
_SessionLocal = None


def get_database_url() -> str:
    """
    Get database URL from environment or use default.

    Returns:
        Database connection URL
    """
    return os.environ.get("RLCF_DATABASE_URL", DEFAULT_DATABASE_URL)


def init_db(database_url: Optional[str] = None) -> None:
    """
    Initialize database engine and create all tables.

    Args:
        database_url: Optional database URL override
    """
    global _engine, _SessionLocal

    url = database_url or get_database_url()
    _engine = create_engine(url, echo=False)
    _SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=_engine)

    # Create all tables
    Base.metadata.create_all(bind=_engine)


def get_session():
    """
    Get a database session.

    Yields:
        Database session that auto-closes

    Raises:
        RuntimeError: If database not initialized
    """
    if _SessionLocal is None:
        init_db()

    session = _SessionLocal()
    try:
        yield session
    finally:
        session.close()


def get_engine():
    """
    Get the database engine.

    Returns:
        SQLAlchemy engine

    Raises:
        RuntimeError: If database not initialized
    """
    if _engine is None:
        init_db()
    return _engine
