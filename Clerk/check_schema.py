#!/usr/bin/env python3
"""
Check the actual database schema to understand the structure.
"""

import asyncio
import logging
from sqlalchemy import text
from src.database.connection import AsyncSessionLocal

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

async def check_schema():
    """Check database schema"""
    async with AsyncSessionLocal() as db:
        try:
            # Check users table columns
            result = await db.execute(
                text("""
                    SELECT column_name, data_type 
                    FROM information_schema.columns 
                    WHERE table_name = 'users'
                    ORDER BY ordinal_position
                """)
            )
            columns = result.fetchall()
            
            logger.info("Users table columns:")
            for col in columns:
                logger.info(f"  - {col[0]}: {col[1]}")
            
            # Check law_firms table columns
            result = await db.execute(
                text("""
                    SELECT column_name, data_type 
                    FROM information_schema.columns 
                    WHERE table_name = 'law_firms'
                    ORDER BY ordinal_position
                """)
            )
            columns = result.fetchall()
            
            logger.info("\nLaw firms table columns:")
            for col in columns:
                logger.info(f"  - {col[0]}: {col[1]}")
                
            # Check if there's a user_law_firms table (many-to-many relationship)
            result = await db.execute(
                text("""
                    SELECT table_name 
                    FROM information_schema.tables 
                    WHERE table_schema = 'public' 
                    AND table_name LIKE '%law_firm%'
                """)
            )
            tables = result.fetchall()
            
            logger.info("\nTables with 'law_firm' in name:")
            for table in tables:
                logger.info(f"  - {table[0]}")
                
        except Exception as e:
            logger.error(f"Failed to check schema: {e}")

if __name__ == "__main__":
    asyncio.run(check_schema())