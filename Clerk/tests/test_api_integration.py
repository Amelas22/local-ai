"""
API Integration Tests for Clerk Legal AI System

Tests the full API endpoints to ensure proper functionality
through the entire request/response cycle.
"""

import pytest
from httpx import AsyncClient, ASGITransport
from main import app


@pytest.mark.asyncio
async def test_case_creation_api():
    """Test case creation through API endpoint"""
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        # Test successful case creation
        response = await client.post(
            "/api/cases",
            json={"name": "Test Case v State"},
            headers={"X-User-ID": "test-user", "X-Law-Firm-ID": "test-firm"},
        )

        assert response.status_code == 200
        data = response.json()
        assert data["name"] == "Test Case v State"
        assert data["law_firm_id"] == "test-firm"
        assert data["created_by"] == "test-user"
        assert "id" in data
        assert data["status"] == "active"


@pytest.mark.asyncio
async def test_case_creation_with_metadata():
    """Test case creation with metadata"""
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        metadata = {
            "client_name": "John Smith",
            "case_type": "personal_injury",
            "court": "District Court",
        }

        response = await client.post(
            "/api/cases",
            json={"name": "Smith v Insurance Co", "metadata": metadata},
            headers={"X-User-ID": "test-user", "X-Law-Firm-ID": "test-firm"},
        )

        assert response.status_code == 200
        data = response.json()
        assert data["metadata"] == metadata


@pytest.mark.asyncio
async def test_case_creation_validation_errors():
    """Test case creation validation"""
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        # Test empty name
        response = await client.post(
            "/api/cases",
            json={"name": ""},
            headers={"X-User-ID": "test-user", "X-Law-Firm-ID": "test-firm"},
        )
        assert response.status_code == 422  # Validation error

        # Test name too long (> 50 chars)
        long_name = "A" * 51
        response = await client.post(
            "/api/cases",
            json={"name": long_name},
            headers={"X-User-ID": "test-user", "X-Law-Firm-ID": "test-firm"},
        )
        assert response.status_code == 422  # Validation error

        # Test whitespace-only name
        response = await client.post(
            "/api/cases",
            json={"name": "   "},
            headers={"X-User-ID": "test-user", "X-Law-Firm-ID": "test-firm"},
        )
        assert response.status_code == 422  # Validation error


@pytest.mark.asyncio
async def test_case_creation_duplicate_name():
    """Test case creation with duplicate name"""
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        # Create first case
        response = await client.post(
            "/api/cases",
            json={"name": "Duplicate Test Case"},
            headers={"X-User-ID": "test-user", "X-Law-Firm-ID": "test-firm"},
        )
        assert response.status_code == 200

        # Try to create duplicate
        response = await client.post(
            "/api/cases",
            json={"name": "Duplicate Test Case"},
            headers={"X-User-ID": "test-user", "X-Law-Firm-ID": "test-firm"},
        )
        assert response.status_code == 400  # Should fail due to duplicate


@pytest.mark.asyncio
async def test_list_cases_api():
    """Test listing cases through API endpoint"""
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        # Create a case first
        await client.post(
            "/api/cases",
            json={"name": "List Test Case"},
            headers={"X-User-ID": "test-user", "X-Law-Firm-ID": "test-firm"},
        )

        # List cases
        response = await client.get(
            "/api/cases",
            headers={"X-User-ID": "test-user", "X-Law-Firm-ID": "test-firm"},
        )

        assert response.status_code == 200
        data = response.json()
        assert isinstance(data, list)
        assert any(case["name"] == "List Test Case" for case in data)


@pytest.mark.asyncio
async def test_update_case_status():
    """Test updating case status"""
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        # Create a case
        create_response = await client.post(
            "/api/cases",
            json={"name": "Status Update Test"},
            headers={"X-User-ID": "test-user", "X-Law-Firm-ID": "test-firm"},
        )
        case_id = create_response.json()["id"]

        # Update status
        response = await client.put(
            f"/api/cases/{case_id}",
            json={"status": "archived"},
            headers={
                "X-User-ID": "test-user",
                "X-Law-Firm-ID": "test-firm",
                "X-Case-ID": case_id,
            },
        )

        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "archived"


@pytest.mark.asyncio
async def test_api_without_authentication():
    """Test API endpoints without authentication headers"""
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        # Test case creation without headers
        response = await client.post("/api/cases", json={"name": "No Auth Test"})

        # Should still work with default test values in development
        assert response.status_code == 200
        data = response.json()
        assert data["created_by"] == "test-user"  # Default value
        assert data["law_firm_id"] == "test-firm"  # Default value


@pytest.fixture(autouse=True)
async def cleanup_test_cases():
    """Cleanup test cases after each test"""
    yield
    # Cleanup logic could be added here if needed
    # For now, tests are isolated by using unique case names
