#!/usr/bin/env python3
"""
Check which database we're actually connected to.
"""

import asyncio
import os
import logging
from sqlalchemy import text
from src.database.connection import AsyncSessionLocal

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

async def check_connection():
    """Check database connection details"""
    logger.info(f"DATABASE_URL from env: {os.getenv('DATABASE_URL')}")
    
    async with AsyncSessionLocal() as db:
        try:
            # Check current database
            result = await db.execute(text("SELECT current_database()"))
            current_db = result.scalar()
            logger.info(f"Connected to database: {current_db}")
            
            # Check all tables
            result = await db.execute(
                text("""
                    SELECT table_name 
                    FROM information_schema.tables 
                    WHERE table_schema = 'public'
                    ORDER BY table_name
                """)
            )
            tables = result.fetchall()
            
            logger.info("\nAll tables in public schema:")
            for table in tables:
                logger.info(f"  - {table[0]}")
                
            # Look for Clerk-specific tables
            clerk_tables = ['cases', 'case_permissions', 'case_facts', 'motion_outlines']
            logger.info("\nChecking for Clerk-specific tables:")
            for table_name in clerk_tables:
                result = await db.execute(
                    text("""
                        SELECT EXISTS (
                            SELECT 1 FROM information_schema.tables 
                            WHERE table_name = :table_name
                        )
                    """),
                    {"table_name": table_name}
                )
                exists = result.scalar()
                status = "✓" if exists else "✗"
                logger.info(f"  {status} {table_name}")
                
        except Exception as e:
            logger.error(f"Failed to check connection: {e}")

if __name__ == "__main__":
    asyncio.run(check_connection())