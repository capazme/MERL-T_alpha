from sqlalchemy.ext.asyncio import create_async_engine, async_sessionmaker, AsyncSession
from sqlalchemy.orm import declarative_base

from .config import app_settings

# Convert SQLite URL to async version
SQLALCHEMY_DATABASE_URL = app_settings.DATABASE_URL.replace(
    "sqlite:///", "sqlite+aiosqlite:///"
)

engine = create_async_engine(
    SQLALCHEMY_DATABASE_URL,
    connect_args={"check_same_thread": False},
    # Enable foreign key constraints and optimize for performance
    pool_pre_ping=True,
    echo=False
)

# Event listener to enable foreign keys for each connection
from sqlalchemy import event
from sqlalchemy.engine import Engine

@event.listens_for(Engine, "connect")
def set_sqlite_pragma(dbapi_conn, connection_record):
    """Enable foreign keys and performance settings for SQLite."""
    cursor = dbapi_conn.cursor()
    cursor.execute("PRAGMA foreign_keys=ON")
    cursor.execute("PRAGMA journal_mode=WAL")  # Write-Ahead Logging for better concurrency
    cursor.close()

SessionLocal = async_sessionmaker(
    bind=engine,
    class_=AsyncSession,
    autocommit=False,
    autoflush=False,
    expire_on_commit=False,
)

Base = declarative_base()


# Dependency injection for FastAPI
async def get_db():
    """Yield database session for FastAPI dependencies."""
    async with SessionLocal() as session:
        yield session
