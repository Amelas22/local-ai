"""
Quick script to check database state for debugging.
"""

import asyncio
import logging
from sqlalchemy import select
from src.database.connection import AsyncSessionLocal
from src.database.models import User, LawFirm

logging.basicConfig(level=logging.INFO)


async def check_database():
    """Check database for users and law firms."""
    async with AsyncSessionLocal() as db:
        # Check law firms
        result = await db.execute(select(LawFirm))
        law_firms = result.scalars().all()

        print("\n=== LAW FIRMS ===")
        for firm in law_firms:
            print(f"ID: {firm.id}")
            print(f"Name: {firm.name}")
            print(f"Domain: {firm.domain}")
            print(f"Is Active: {firm.is_active}")
            print("-" * 40)

        # Check users
        result = await db.execute(select(User))
        users = result.scalars().all()

        print("\n=== USERS ===")
        for user in users:
            print(f"ID: {user.id}")
            print(f"Email: {user.email}")
            print(f"Law Firm ID: {user.law_firm_id}")
            print(f"Is Active: {user.is_active}")
            print("-" * 40)


if __name__ == "__main__":
    asyncio.run(check_database())
