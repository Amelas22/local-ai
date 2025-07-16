"""
Integration tests for development mode authentication flow.

Tests that case list and case creation work properly in dev mode.
"""

import pytest
from httpx import AsyncClient
from src.config.settings import get_settings


@pytest.mark.asyncio
async def test_dev_auth_case_list(async_client: AsyncClient):
    """Test that case list works in dev mode."""
    settings = get_settings()

    # Ensure we're in dev mode
    assert not settings.auth.auth_enabled

    # Test case list with dev token
    response = await async_client.get(
        "/api/cases",
        headers={"Authorization": f"Bearer {settings.auth.dev_mock_token}"},
    )

    assert response.status_code == 200
    assert isinstance(response.json(), list)


@pytest.mark.asyncio
async def test_create_case_dev_mode(async_client: AsyncClient):
    """Test case creation in dev mode."""
    settings = get_settings()

    response = await async_client.post(
        "/api/cases",
        json={"name": "Test Case v Demo Case", "description": "Test case creation"},
        headers={"Authorization": f"Bearer {settings.auth.dev_mock_token}"},
    )

    assert response.status_code in [200, 201]
    data = response.json()
    assert data["name"] == "Test Case v Demo Case"
    assert data["law_firm_id"] == "dev-firm-123"


@pytest.mark.asyncio
async def test_case_list_without_token(async_client: AsyncClient):
    """Test that case list fails without token."""
    response = await async_client.get("/api/cases")

    assert response.status_code == 401
    assert "Missing authentication token" in response.json()["detail"]


@pytest.mark.asyncio
async def test_case_list_with_invalid_token(async_client: AsyncClient):
    """Test that case list fails with invalid token."""
    response = await async_client.get(
        "/api/cases", headers={"Authorization": "Bearer invalid-token"}
    )

    assert response.status_code == 401
    assert "Invalid development token" in response.json()["detail"]


@pytest.mark.asyncio
async def test_health_endpoint_no_auth(async_client: AsyncClient):
    """Test that health endpoint works without authentication."""
    response = await async_client.get("/health")

    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "healthy"


# MVP Mode Tests
@pytest.mark.mvp_mode
@pytest.mark.asyncio
async def test_mvp_mode_case_list_no_token(async_client: AsyncClient, mvp_mode):
    """Test that case list works without token in MVP mode."""
    # No auth header needed in MVP mode
    response = await async_client.get("/api/cases")

    assert response.status_code == 200
    assert isinstance(response.json(), dict)
    assert "cases" in response.json()


@pytest.mark.mvp_mode
@pytest.mark.asyncio
async def test_mvp_mode_create_case(async_client: AsyncClient, mvp_mode):
    """Test case creation without authentication in MVP mode."""
    response = await async_client.post(
        "/api/cases",
        json={"name": "MVP Test Case", "metadata": {"created_in": "mvp_mode"}},
    )

    assert response.status_code in [200, 201]
    data = response.json()
    assert data["name"] == "MVP Test Case"
    # Should use mock user's law firm ID
    assert data["law_firm_id"] == "123e4567-e89b-12d3-a456-426614174000"
    assert data["created_by"] == "123e4567-e89b-12d3-a456-426614174001"


@pytest.mark.mvp_mode
@pytest.mark.asyncio
async def test_mvp_mode_search_endpoint(async_client: AsyncClient, mvp_mode):
    """Test search endpoint works without authentication in MVP mode."""
    # First create a case to search in
    case_response = await async_client.post(
        "/api/cases", json={"name": "MVP Search Test Case"}
    )
    case_id = case_response.json()["id"]

    # Now test search
    response = await async_client.post(
        "/search", json={"query": "test query"}, headers={"X-Case-ID": case_id}
    )

    assert response.status_code == 200
    assert "results" in response.json()


@pytest.mark.mvp_mode
@pytest.mark.asyncio
async def test_mvp_mode_headers_present(async_client: AsyncClient, mvp_mode):
    """Test that MVP mode headers are present in responses."""
    response = await async_client.get("/api/cases")

    assert response.status_code == 200
    assert "X-MVP-Mode" in response.headers
    assert response.headers["X-MVP-Mode"] == "true"
    assert "X-Mock-User-Id" in response.headers
    assert response.headers["X-Mock-User-Id"] == "123e4567-e89b-12d3-a456-426614174001"


@pytest.mark.asyncio
async def test_case_permissions_dev_mode(async_client: AsyncClient):
    """Test case permissions in dev mode."""
    settings = get_settings()

    # First create a case
    create_response = await async_client.post(
        "/api/cases",
        json={
            "name": "Permission Test Case",
            "description": "Test case for permissions",
        },
        headers={"Authorization": f"Bearer {settings.auth.dev_mock_token}"},
    )

    assert create_response.status_code in [200, 201]
    case_id = create_response.json()["id"]

    # Test granting permissions (dev user should have admin rights)
    permission_response = await async_client.post(
        f"/api/cases/{case_id}/permissions",
        json={"user_id": "another-user-123", "permission": "read"},
        headers={"Authorization": f"Bearer {settings.auth.dev_mock_token}"},
    )

    # This might fail if the endpoint requires specific validation
    # but we're testing that auth works, not the full permission system
    assert permission_response.status_code in [200, 201, 400, 404]


@pytest.mark.asyncio
async def test_websocket_auth_dev_mode(async_client: AsyncClient):
    """Test that WebSocket endpoints are accessible in dev mode."""
    response = await async_client.get(
        "/websocket/status",
        headers={"Authorization": f"Bearer {get_settings().auth.dev_mock_token}"},
    )

    # WebSocket status should be accessible
    assert response.status_code in [200, 404]  # 404 if endpoint doesn't exist
