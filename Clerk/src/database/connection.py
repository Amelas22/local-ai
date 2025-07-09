"""
Database connection management for PostgreSQL using SQLAlchemy async.

This module provides async database session management and connection pooling
for the Clerk Legal AI System.
"""
import os
from typing import AsyncGenerator
from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine, async_sessionmaker
from sqlalchemy.orm import declarative_base
from sqlalchemy.pool import NullPool
from sqlalchemy import text
import logging

logger = logging.getLogger(__name__)

# Database URL from environment, with fallback to local PostgreSQL
DATABASE_URL = os.getenv(
    "DATABASE_URL",
    "postgresql+asyncpg://postgres:password@localhost:5432/postgres"
)

# Convert postgresql:// to postgresql+asyncpg:// for async support
if DATABASE_URL.startswith("postgresql://"):
    DATABASE_URL = DATABASE_URL.replace("postgresql://", "postgresql+asyncpg://", 1)

# Create async engine with connection pooling
engine = create_async_engine(
    DATABASE_URL,
    echo=os.getenv("DATABASE_ECHO", "false").lower() == "true",
    pool_pre_ping=True,  # Verify connections before using
    pool_size=20,        # Number of connections to maintain
    max_overflow=10,     # Maximum overflow connections
    pool_recycle=3600,   # Recycle connections after 1 hour
)

# Create async session factory
AsyncSessionLocal = async_sessionmaker(
    engine,
    class_=AsyncSession,
    expire_on_commit=False,
    autocommit=False,
    autoflush=False,
)

# Base class for SQLAlchemy models
Base = declarative_base()


async def get_db() -> AsyncGenerator[AsyncSession, None]:
    """
    Dependency to get database session.
    
    Yields:
        AsyncSession: Database session for the request.
        
    Example:
        @app.get("/users")
        async def get_users(db: AsyncSession = Depends(get_db)):
            result = await db.execute(select(User))
            return result.scalars().all()
    """
    async with AsyncSessionLocal() as session:
        try:
            yield session
            await session.commit()
        except Exception:
            await session.rollback()
            raise
        finally:
            await session.close()


async def init_db() -> None:
    """
    Initialize database by creating all tables.
    
    This should be called once on application startup.
    """
    async with engine.begin() as conn:
        # Import all models to ensure they're registered
        from src.database.models import User, LawFirm, Case, UserCasePermission
        
        # Create all tables
        await conn.run_sync(Base.metadata.create_all)
        logger.info("Database tables created successfully")


async def close_db() -> None:
    """
    Close database connections.
    
    This should be called on application shutdown.
    """
    await engine.dispose()
    logger.info("Database connections closed")


async def test_connection() -> bool:
    """
    Test database connection.
    
    Returns:
        bool: True if connection successful, False otherwise.
    """
    try:
        async with AsyncSessionLocal() as session:
            await session.execute(text("SELECT 1"))
            await session.commit()
        logger.info("Database connection test successful")
        return True
    except Exception as e:
        logger.error(f"Database connection test failed: {e}")
        return False