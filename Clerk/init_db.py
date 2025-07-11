#!/usr/bin/env python3
"""
Database initialization script for Clerk Legal AI System.

This script:
1. Creates all database tables using SQLAlchemy
2. Runs Alembic migrations
3. Seeds initial data (admin user, default law firm)
4. Configures shared resources
"""

import asyncio
import os
import sys
import logging
from pathlib import Path

# Add src to path
sys.path.append(str(Path(__file__).parent))

from sqlalchemy import text
from src.database.connection import test_connection, AsyncSessionLocal
from src.services.user_service import UserService
from src.config.shared_resources import shared_resources
from config.settings import settings
from alembic.config import Config
from alembic import command

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


def run_migrations():
    """Run Alembic migrations."""
    try:
        logger.info("Running database migrations...")

        # Create Alembic configuration
        alembic_ini_path = Path(__file__).parent / "src" / "migrations" / "alembic.ini"

        if not alembic_ini_path.exists():
            logger.warning(
                f"Alembic config not found at {alembic_ini_path}, skipping migrations"
            )
            return True

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

        # Run migrations
        command.upgrade(alembic_cfg, "head")

        logger.info("Database migrations completed successfully")
        return True

    except Exception as e:
        logger.error(f"Migration failed: {e}")
        import traceback

        traceback.print_exc()
        return False


async def seed_initial_data():
    """Seed initial data into the database."""
    logger.info("Seeding initial data...")

    async with AsyncSessionLocal() as db:
        try:
            # Check if data already exists
            existing_firms = await db.execute(text("SELECT COUNT(*) FROM law_firms"))
            count = existing_firms.scalar()

            if count > 0:
                logger.info("Database already contains data, skipping seed")
                return True

            # Create default law firm
            # In MVP mode, create the specific law firm expected by MockUserMiddleware
            if os.getenv("MVP_MODE", "false").lower() == "true":
                from sqlalchemy import text
                # Create law firm with specific ID for MVP mode
                firm_id = "123e4567-e89b-12d3-a456-426614174000"
                await db.execute(
                    text("""
                        INSERT INTO law_firms (id, name, domain, is_active, created_at, updated_at)
                        VALUES (:id, :name, :domain, true, NOW(), NOW())
                    """),
                    {"id": firm_id, "name": "Development Law Firm", "domain": "dev.clerk.ai"}
                )
                await db.commit()
                # Fetch the created firm
                result = await db.execute(
                    text("SELECT * FROM law_firms WHERE id = :id"),
                    {"id": firm_id}
                )
                firm_row = result.first()
                from src.models.user_models import LawFirm
                default_firm = LawFirm(**firm_row._asdict())
                logger.info(f"Created MVP law firm with ID: {firm_id}")
            else:
                default_firm = await UserService.create_law_firm(
                    db=db, name="Demo Law Firm", domain="demo.example.com"
                )
                logger.info(f"Created default law firm: {default_firm.name}")

            # Create admin user
            admin_password = settings.admin.admin_password
            admin_email = settings.admin.admin_email

            admin_user = await UserService.create_user(
                db=db,
                email=admin_email,
                password=admin_password,
                name="System Administrator",
                law_firm_id=default_firm.id,
                is_admin=True,
            )
            logger.info(f"Created admin user: {admin_user.email}")
            
            # In MVP mode, also create the mock user
            if os.getenv("MVP_MODE", "false").lower() == "true":
                mock_user_id = "123e4567-e89b-12d3-a456-426614174001"
                await db.execute(
                    text("""
                        INSERT INTO users (id, email, name, law_firm_id, is_admin, is_active, 
                                         created_at, updated_at, password_hash)
                        VALUES (:id, :email, :name, :law_firm_id, true, true, 
                                NOW(), NOW(), :password_hash)
                        ON CONFLICT (id) DO NOTHING
                    """),
                    {
                        "id": mock_user_id,
                        "email": "dev@clerk.ai",
                        "name": "Development User",
                        "law_firm_id": firm_id,
                        "password_hash": "$2b$12$dummy.hash.for.mvp.mode"  # Dummy hash, won't be used
                    }
                )
                await db.commit()
                logger.info(f"Created MVP user with ID: {mock_user_id}")

            # Configure shared resources
            shared_collections = settings.shared_collections.split(",")

            for collection in shared_collections:
                shared_resources.add_shared_collection(collection.strip())

            logger.info(f"Configured shared resources: {shared_collections}")

            # Create some demo cases (optional)
            if os.getenv("CREATE_DEMO_DATA", "false").lower() == "true":
                from src.services.case_service import CaseService

                demo_cases = [
                    "Smith v Jones 2024",
                    "Estate of Johnson",
                    "ABC Corp Litigation",
                ]

                for case_name in demo_cases:
                    case = await CaseService.create_case(
                        db=db,
                        name=case_name,
                        law_firm_id=default_firm.id,
                        created_by=admin_user.id,
                        description=f"Demo case: {case_name}",
                    )
                    logger.info(f"Created demo case: {case.name}")

            logger.info("Initial data seeded successfully")
            return True

        except Exception as e:
            logger.error(f"Failed to seed data: {e}")
            await db.rollback()
            return False


async def main():
    """Main initialization function."""
    logger.info("Starting database initialization...")

    # Test database connection
    logger.info("Testing database connection...")
    if not await test_connection():
        logger.error("Failed to connect to database. Check your DATABASE_URL")
        sys.exit(1)

    # Check if alembic_version table exists
    async with AsyncSessionLocal() as db:
        try:
            result = await db.execute(
                text(
                    "SELECT EXISTS (SELECT 1 FROM information_schema.tables WHERE table_name = 'alembic_version')"
                )
            )
            alembic_exists = result.scalar()

            if alembic_exists:
                # Check if migrations have been run
                result = await db.execute(
                    text("SELECT version_num FROM alembic_version")
                )
                version = result.scalar()
                if version:
                    logger.info(f"Database already initialized with version: {version}")
                    logger.info("Skipping table creation and migrations")
                else:
                    # Alembic table exists but no version, run migrations
                    logger.info("Running database migrations...")
                    if not run_migrations():
                        logger.error("Failed to run migrations")
                        sys.exit(1)
            else:
                # No alembic table, this is a fresh database
                # Don't create tables with SQLAlchemy, let Alembic do it
                logger.info("Fresh database detected, running migrations...")
                if not run_migrations():
                    logger.error("Failed to run migrations")
                    sys.exit(1)

        except Exception:
            # If tables don't exist at all, run migrations
            logger.info("Database appears empty, running migrations...")
            if not run_migrations():
                logger.error("Failed to run migrations")
                sys.exit(1)

    # Seed initial data
    if not await seed_initial_data():
        logger.error("Failed to seed initial data")
        sys.exit(1)

    # Also ensure dev data exists in development mode
    if not settings.auth.auth_enabled:
        logger.info("Development mode detected, ensuring dev data exists...")
        try:
            from scripts.fix_dev_database import ensure_dev_data

            await ensure_dev_data()
            logger.info("Development data ensured")
        except Exception as e:
            logger.warning(f"Failed to ensure dev data: {e}")
            # Don't fail the entire init if dev data creation fails

    logger.info("Database initialization completed successfully!")

    # Print access information
    print("\n" + "=" * 50)
    print("Database initialized successfully!")
    print("=" * 50)
    print("\nDefault admin credentials:")
    print(f"Email: {settings.admin.admin_email}")
    print(f"Password: {settings.admin.admin_password}")
    print("\nIMPORTANT: Change these credentials after first login!")
    print("=" * 50 + "\n")


if __name__ == "__main__":
    asyncio.run(main())
