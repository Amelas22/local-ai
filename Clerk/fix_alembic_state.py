#!/usr/bin/env python3
"""
Fix Alembic migration state when tables already exist.

This script stamps the database with the current migration version
without running the migrations, useful when tables were created
outside of Alembic.
"""

import os
import sys
from pathlib import Path

# Add src to path
sys.path.append(str(Path(__file__).parent))

from alembic.config import Config
from alembic import command


def main():
    """Stamp database with current migration version."""
    print("Stamping database with current Alembic migration version...")

    # Create Alembic configuration
    alembic_ini_path = Path(__file__).parent / "src" / "migrations" / "alembic.ini"

    if not alembic_ini_path.exists():
        print(f"Error: Alembic config not found at {alembic_ini_path}")
        sys.exit(1)

    alembic_cfg = Config(str(alembic_ini_path))

    # Override database URL from environment
    db_url = os.getenv(
        "DATABASE_URL", "postgresql://postgres:password@localhost:5432/postgres"
    )
    # Convert to sync URL for Alembic (remove asyncpg)
    if "+asyncpg" in db_url:
        db_url = db_url.replace("+asyncpg", "")
    elif "postgresql+asyncpg://" in db_url:
        db_url = db_url.replace("postgresql+asyncpg://", "postgresql://")

    alembic_cfg.set_main_option("sqlalchemy.url", db_url)

    try:
        # Stamp the database with the current head revision
        # This marks all migrations as applied without running them
        command.stamp(alembic_cfg, "head")
        print("Database successfully stamped with current migration version")
        print("You can now run future migrations normally")
        return True
    except Exception as e:
        print(f"Error stamping database: {e}")
        return False


if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)
