"""
Tests for Good Faith letter template API endpoints.

Tests the template management endpoints added to deficiency_endpoints.py.
"""

import pytest
from unittest.mock import Mock, patch, AsyncMock
from uuid import uuid4

from fastapi.testclient import TestClient
from fastapi import FastAPI


@pytest.fixture
def app(mock_case_context):
    """Create FastAPI app with router."""
    with patch("src.middleware.case_context.require_case_context") as mock_require:
        # Make require_case_context return a function that returns the mock context
        def _create_dependency(permission: str = "read"):
            return lambda: mock_case_context

        mock_require.side_effect = _create_dependency

        # Import router after mocking
        from src.api.deficiency_endpoints import router

        app = FastAPI()
        app.include_router(router)
        return app


@pytest.fixture
def client(app):
    """Create test client."""
    return TestClient(app)


@pytest.fixture
def mock_case_context():
    """Mock case context."""
    context = Mock()
    context.case_id = str(uuid4())
    context.case_name = "Test_Case_2024"
    context.user_id = "test-user"
    context.permissions = ["read", "write"]
    return context


class TestTemplateEndpoints:
    """Test suite for template management endpoints."""

    @patch("src.api.deficiency_endpoints.LetterTemplateService")
    def test_list_good_faith_templates(
        self, mock_service_class, client, mock_case_context
    ):
        """Test listing available templates."""
        # Setup mocks
        mock_service = Mock()
        mock_service.list_available_templates = AsyncMock(
            return_value=[
                {
                    "jurisdiction": "federal",
                    "title": "Federal Template",
                    "version": "1.0",
                    "description": "Federal court template",
                    "compliance_rules": ["frcp_37"],
                },
                {
                    "jurisdiction": "california",
                    "title": "California Template",
                    "version": "1.0",
                    "description": "California state template",
                    "compliance_rules": ["ccp_2031.310"],
                },
            ]
        )
        mock_service_class.return_value = mock_service

        # Make request
        response = client.get(
            "/api/deficiency/templates/good-faith-letters",
            headers={"X-Case-ID": mock_case_context.case_id},
        )

        # Verify response
        if response.status_code != 200:
            print(f"Response status: {response.status_code}")
            print(f"Response body: {response.text}")
            print(f"Response headers: {response.headers}")
        assert response.status_code == 200
        data = response.json()
        assert len(data) == 2
        assert data[0]["jurisdiction"] == "federal"
        assert data[0]["compliance_rules"] == ["frcp_37"]
        assert data[1]["jurisdiction"] == "california"

    @patch("src.api.deficiency_endpoints.LetterTemplateService")
    def test_get_template_requirements(
        self, mock_service_class, client, mock_case_context
    ):
        """Test getting template requirements."""
        # Setup mocks

        mock_service = Mock()
        mock_service.get_template_requirements = AsyncMock(
            return_value={
                "jurisdiction": "federal",
                "template_version": "1.0",
                "required_variables": ["COURT_NAME", "CASE_NUMBER"],
                "all_variables": ["COURT_NAME", "CASE_NUMBER", "PLAINTIFF_NAME"],
                "sections": [
                    {"name": "caption", "required": True},
                    {"name": "body", "required": True},
                ],
                "compliance_requirements": {
                    "rule_id": "frcp_37",
                    "required_sections": ["caption", "body"],
                },
            }
        )
        mock_service_class.return_value = mock_service

        # Make request
        response = client.get(
            "/api/deficiency/templates/good-faith-letters/federal",
            headers={"X-Case-ID": mock_case_context.case_id},
        )

        # Verify response
        assert response.status_code == 200
        data = response.json()
        assert data["jurisdiction"] == "federal"
        assert "COURT_NAME" in data["required_variables"]
        assert len(data["sections"]) == 2
        assert data["compliance_requirements"]["rule_id"] == "frcp_37"

    @patch("src.api.deficiency_endpoints.LetterTemplateService")
    def test_get_template_requirements_not_found(
        self, mock_service_class, client, mock_case_context
    ):
        """Test getting requirements for non-existent template."""
        # Setup mocks

        mock_service = Mock()
        mock_service.get_template_requirements = AsyncMock(
            side_effect=ValueError("Template not found")
        )
        mock_service_class.return_value = mock_service

        # Make request
        response = client.get(
            "/api/deficiency/templates/good-faith-letters/invalid",
            headers={"X-Case-ID": mock_case_context.case_id},
        )

        # Verify response
        assert response.status_code == 404
        assert "Template not found" in response.json()["detail"]

    def test_create_custom_template_not_implemented(self, client, mock_case_context):
        """Test creating custom template returns not implemented."""
        # Setup mocks

        # Make request
        response = client.post(
            "/api/deficiency/templates/good-faith-letters",
            json={
                "jurisdiction": "custom",
                "template_yaml": "metadata:\n  type: legal_document",
                "override_existing": False,
            },
            headers={"X-Case-ID": mock_case_context.case_id},
        )

        # Verify response
        assert response.status_code == 501
        assert "will be implemented in a future story" in response.json()["detail"]

    def test_update_template_not_implemented(self, client, mock_case_context):
        """Test updating template returns not implemented."""
        # Setup mocks

        # Make request
        response = client.put(
            "/api/deficiency/templates/good-faith-letters/federal",
            json={"template_yaml": "updated content", "increment_version": True},
            headers={"X-Case-ID": mock_case_context.case_id},
        )

        # Verify response
        assert response.status_code == 501
        assert "will be implemented in a future story" in response.json()["detail"]

    @patch("src.api.deficiency_endpoints.LetterTemplateService")
    def test_list_templates_error_handling(
        self, mock_service_class, client, mock_case_context
    ):
        """Test error handling in list templates."""
        # Setup mocks

        mock_service = Mock()
        mock_service.list_available_templates = AsyncMock(
            side_effect=Exception("Service error")
        )
        mock_service_class.return_value = mock_service

        # Make request
        response = client.get(
            "/api/deficiency/templates/good-faith-letters",
            headers={"X-Case-ID": mock_case_context.case_id},
        )

        # Verify response
        assert response.status_code == 500
        assert "Failed to list templates" in response.json()["detail"]
