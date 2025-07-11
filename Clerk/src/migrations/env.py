"""
Alembic environment configuration for async SQLAlchemy.

This file configures Alembic to work with async SQLAlchemy and
includes all models for automatic migration generation.
"""

import asyncio
import os
import sys
from logging.config import fileConfig
from pathlib import Path

from sqlalchemy import pool
from sqlalchemy.engine import Connection
from sqlalchemy.ext.asyncio import async_engine_from_config
from alembic import context

# Add parent directory to path
sys.path.append(str(Path(__file__).parent.parent.parent))

# Import Base and all models
from src.database.connection import Base

# this is the Alembic Config object
config = context.config

# Interpret the config file for Python logging
if config.config_file_name is not None:
    fileConfig(config.config_file_name)

# Add your model's MetaData object here for 'autogenerate' support
target_metadata = Base.metadata


# Get database URL from environment
def get_database_url():
    """Get database URL from environment or use default."""
    url = os.getenv(
        "DATABASE_URL", "postgresql://postgres:password@localhost:5432/postgres"
    )
    # For async migrations, ensure we're using asyncpg
    # For sync migrations (called from alembic directly), keep it as-is
    if context.is_offline_mode():
        # Offline mode - use sync driver
        if "+asyncpg" in url:
            url = url.replace("+asyncpg", "")
        elif "postgresql+asyncpg://" in url:
            url = url.replace("postgresql+asyncpg://", "postgresql://")
    else:
        # Online mode - use async driver
        if url.startswith("postgresql://") and "+asyncpg" not in url:
            url = url.replace("postgresql://", "postgresql+asyncpg://", 1)
    return url


def run_migrations_offline() -> None:
    """Run migrations in 'offline' mode.

    This configures the context with just a URL
    and not an Engine, though an Engine is acceptable
    here as well. By skipping the Engine creation
    we don't even need a DBAPI to be available.

    Calls to context.execute() here emit the given string to the
    script output.
    """
    url = get_database_url()
    context.configure(
        url=url,
        target_metadata=target_metadata,
        literal_binds=True,
        dialect_opts={"paramstyle": "named"},
    )

    with context.begin_transaction():
        context.run_migrations()


def do_run_migrations(connection: Connection) -> None:
    """Run migrations using a connection."""
    context.configure(connection=connection, target_metadata=target_metadata)

    with context.begin_transaction():
        context.run_migrations()


async def run_async_migrations() -> None:
    """Run migrations in 'online' mode with async engine."""
    configuration = config.get_section(config.config_ini_section, {})
    configuration["sqlalchemy.url"] = get_database_url()

    connectable = async_engine_from_config(
        configuration,
        prefix="sqlalchemy.",
        poolclass=pool.NullPool,
    )

    async with connectable.connect() as connection:
        await connection.run_sync(do_run_migrations)

    await connectable.dispose()


def run_migrations_online() -> None:
    """Run migrations in 'online' mode."""
    # Get connection from config attributes if available
    connectable = config.attributes.get("connection", None)

    if connectable is not None:
        # Connection provided externally, use it directly
        do_run_migrations(connectable)
    else:
        # Create our own connection
        try:
            # Check if we're already in an event loop
            loop = asyncio.get_running_loop()
            # We're in an event loop, use run_sync instead
            from sqlalchemy import create_engine

            sync_url = get_database_url()
            # Ensure we use sync driver for this case
            if "+asyncpg" in sync_url:
                sync_url = sync_url.replace("+asyncpg", "")
            engine = create_engine(sync_url, poolclass=pool.NullPool)
            with engine.connect() as connection:
                do_run_migrations(connection)
            engine.dispose()
        except RuntimeError:
            # No event loop running, use async
            asyncio.run(run_async_migrations())


if context.is_offline_mode():
    run_migrations_offline()
else:
    run_migrations_online()
