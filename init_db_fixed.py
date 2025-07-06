#!/usr/bin/env python3
"""
Fixed database initialization script that prioritizes environment variables
"""
import asyncio
import os
import sys
import logging
from pathlib import Path

# Add src to path
sys.path.append(str(Path(__file__).parent / "Clerk"))

# IMPORTANT: Set DATABASE_URL before importing settings
# This ensures environment variable takes precedence
database_url = os.getenv("DATABASE_URL")
if database_url:
    print(f"Using DATABASE_URL from environment: {database_url}")
    # Also set it in os.environ to ensure it's available
    os.environ["DATABASE_URL"] = database_url
else:
    print("WARNING: DATABASE_URL not set in environment")

# Now import the rest
from src.database.connection import init_db, test_connection
from config.settings import settings

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


async def init_database():
    """Initialize the database"""
    logger.info("Starting database initialization...")
    
    # Log the actual URL being used
    logger.info(f"Database URL: {settings.database.url}")
    
    # Test connection first
    logger.info("Testing database connection...")
    if not await test_connection():
        logger.error("Failed to connect to database. Check your DATABASE_URL")
        return False
    
    logger.info("Connection successful! Creating tables...")
    
    # Initialize database tables
    await init_db()
    
    logger.info("Database initialization completed successfully!")
    return True


if __name__ == "__main__":
    # Run the initialization
    success = asyncio.run(init_database())
    exit(0 if success else 1)