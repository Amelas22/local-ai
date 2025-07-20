"""
Pytest fixtures for API integration tests.
"""

import pytest
from httpx import AsyncClient
from unittest.mock import AsyncMock


@pytest.fixture
async def client():
    """Create test client for FastAPI application."""
    from main import app
    from httpx import ASGITransport
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as ac:
        yield ac


@pytest.fixture
async def async_session():
    """Create mock async database session."""
    session = AsyncMock()
    session.execute = AsyncMock()
    session.commit = AsyncMock()
    session.rollback = AsyncMock()
    yield session