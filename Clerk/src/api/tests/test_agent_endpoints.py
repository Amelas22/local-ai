"""
Tests for agent API endpoints.
"""

import pytest
from unittest.mock import Mock, AsyncMock, patch
from fastapi.testclient import TestClient
from uuid import uuid4
import json

from src.api.agent_endpoints import (
    router,
)


class TestAgentEndpoints:
    """Test suite for agent API endpoints."""

    @pytest.fixture
    def client(self):
        """Create test client."""
        from fastapi import FastAPI

        app = FastAPI()
        app.include_router(router)
        return TestClient(app)

    @pytest.fixture
    def mock_case_context(self):
        """Create mock case context."""
        context = Mock()
        context.case_id = "case-123"
        context.case_name = "Smith_v_Jones_2024"
        context.user_id = "user-456"
        context.permissions = ["read", "write"]
        return context

    @pytest.fixture
    def auth_headers(self):
        """Create auth headers for requests."""
        return {"X-Case-ID": "case-123", "Authorization": "Bearer mock-token"}

    def test_analyze_endpoint_success(self, client, mock_case_context, auth_headers):
        """Test successful analysis initiation."""
        # Mock dependencies
        with patch("src.api.agent_endpoints.require_case_context") as mock_auth:
            mock_auth.return_value = lambda: mock_case_context

            with patch("src.ai_agents.bmad_framework.AgentLoader") as mock_loader:
                mock_agent_def = {
                    "commands": ["help", "analyze", "search"],
                    "agent": {"id": "deficiency-analyzer"},
                }
                mock_loader.return_value.load_agent = AsyncMock(
                    return_value=mock_agent_def
                )

                with patch(
                    "src.ai_agents.bmad_framework.AgentExecutor"
                ) as mock_executor:
                    mock_executor.return_value.execute_command_async = AsyncMock()

                    # Make request
                    response = client.post(
                        "/api/agents/deficiency-analyzer/analyze",
                        json={
                            "production_id": str(uuid4()),
                            "rtp_document_id": str(uuid4()),
                            "oc_response_id": None,
                            "options": {"confidence_threshold": 0.7},
                        },
                        headers=auth_headers,
                    )

                    # Verify response
                    assert response.status_code == 202
                    data = response.json()
                    assert "processing_id" in data
                    assert "websocket_channel" in data
                    assert data["estimated_duration_seconds"] == 300

    def test_analyze_endpoint_invalid_request(
        self, client, mock_case_context, auth_headers
    ):
        """Test analysis with invalid request data."""
        with patch("src.api.agent_endpoints.require_case_context") as mock_auth:
            mock_auth.return_value = lambda: mock_case_context

            # Missing required field
            response = client.post(
                "/api/agents/deficiency-analyzer/analyze",
                json={
                    "production_id": str(uuid4())
                    # Missing rtp_document_id
                },
                headers=auth_headers,
            )

            assert response.status_code == 422  # Validation error

    def test_analyze_endpoint_agent_not_found(
        self, client, mock_case_context, auth_headers
    ):
        """Test analysis with non-existent agent."""
        with patch("src.api.agent_endpoints.require_case_context") as mock_auth:
            mock_auth.return_value = lambda: mock_case_context

            with patch("src.ai_agents.bmad_framework.AgentLoader") as mock_loader:
                mock_loader.return_value.load_agent = AsyncMock(
                    side_effect=Exception("Agent not found")
                )

                response = client.post(
                    "/api/agents/non-existent-agent/analyze",
                    json={
                        "production_id": str(uuid4()),
                        "rtp_document_id": str(uuid4()),
                    },
                    headers=auth_headers,
                )

                assert response.status_code == 404
                assert "AGENT_NOT_FOUND" in response.json()["error"]["code"]

    def test_analyze_endpoint_no_permission(self, client, auth_headers):
        """Test analysis without required permissions."""
        # Mock context with read-only permission
        mock_context = Mock()
        mock_context.case_id = "case-123"
        mock_context.case_name = "Smith_v_Jones_2024"
        mock_context.permissions = ["read"]  # No write permission

        with patch("src.api.agent_endpoints.require_case_context") as mock_auth:
            mock_auth.return_value = lambda: mock_context

            response = client.post(
                "/api/agents/deficiency-analyzer/analyze",
                json={"production_id": str(uuid4()), "rtp_document_id": str(uuid4())},
                headers=auth_headers,
            )

            # Should fail permission check
            assert response.status_code in [403, 500]

    def test_search_endpoint_success(self, client, mock_case_context, auth_headers):
        """Test successful document search."""
        with patch("src.api.agent_endpoints.require_case_context") as mock_auth:
            mock_auth.return_value = lambda: mock_case_context

            with patch("src.ai_agents.bmad_framework.AgentLoader") as mock_loader:
                mock_agent_def = {"commands": ["search"]}
                mock_loader.return_value.load_agent = AsyncMock(
                    return_value=mock_agent_def
                )

                with patch(
                    "src.ai_agents.bmad_framework.AgentExecutor"
                ) as mock_executor:
                    mock_results = {
                        "success": True,
                        "results": [
                            {
                                "document_id": str(uuid4()),
                                "chunk_text": "Contract terms...",
                                "relevance_score": 0.92,
                                "metadata": {"page": 5},
                            }
                        ],
                        "total_count": 1,
                        "has_more": False,
                    }
                    mock_executor.return_value.execute_command = AsyncMock(
                        return_value=mock_results
                    )

                    response = client.post(
                        "/api/agents/deficiency-analyzer/search",
                        json={
                            "query": "contract negotiations",
                            "case_name": "Smith_v_Jones_2024",
                            "limit": 50,
                            "offset": 0,
                        },
                        headers=auth_headers,
                    )

                    assert response.status_code == 200
                    data = response.json()
                    assert len(data["results"]) == 1
                    assert data["results"][0]["relevance_score"] == 0.92
                    assert data["total_count"] == 1
                    assert data["has_more"] is False

    def test_search_endpoint_case_mismatch(
        self, client, mock_case_context, auth_headers
    ):
        """Test search with mismatched case name."""
        with patch("src.api.agent_endpoints.require_case_context") as mock_auth:
            mock_auth.return_value = lambda: mock_case_context

            response = client.post(
                "/api/agents/deficiency-analyzer/search",
                json={
                    "query": "test",
                    "case_name": "Different_Case_2024",  # Doesn't match context
                    "limit": 10,
                },
                headers=auth_headers,
            )

            assert response.status_code == 403
            assert "CASE_MISMATCH" in response.json()["error"]["code"]

    def test_categorize_endpoint_success(self, client, mock_case_context, auth_headers):
        """Test successful compliance categorization."""
        with patch("src.api.agent_endpoints.require_case_context") as mock_auth:
            mock_auth.return_value = lambda: mock_case_context

            with patch("src.ai_agents.bmad_framework.AgentLoader") as mock_loader:
                mock_agent_def = {"commands": ["categorize"]}
                mock_loader.return_value.load_agent = AsyncMock(
                    return_value=mock_agent_def
                )

                with patch(
                    "src.ai_agents.bmad_framework.AgentExecutor"
                ) as mock_executor:
                    mock_result = {
                        "classification": "partially_produced",
                        "confidence_score": 0.75,
                        "evidence_summary": "Found 3 relevant documents",
                        "recommendation": "Request clarification",
                    }
                    mock_executor.return_value.execute_command = AsyncMock(
                        return_value=mock_result
                    )

                    response = client.post(
                        "/api/agents/deficiency-analyzer/categorize",
                        json={
                            "request_number": "RFP No. 1",
                            "request_text": "All contracts...",
                            "search_results": ["result-1", "result-2"],
                            "oc_response_text": "Documents produced",
                        },
                        headers=auth_headers,
                    )

                    assert response.status_code == 200
                    data = response.json()
                    assert data["classification"] == "partially_produced"
                    assert data["confidence_score"] == 0.75

    def test_get_report_endpoint_json(self, client, mock_case_context, auth_headers):
        """Test report retrieval in JSON format."""
        with patch("src.api.agent_endpoints.require_case_context") as mock_auth:
            mock_auth.return_value = lambda: mock_case_context

            with patch("src.ai_agents.bmad_framework.AgentLoader") as mock_loader:
                mock_agent_def = {"commands": ["report"]}
                mock_loader.return_value.load_agent = AsyncMock(
                    return_value=mock_agent_def
                )

                with patch(
                    "src.ai_agents.bmad_framework.AgentExecutor"
                ) as mock_executor:
                    mock_report = {
                        "content": json.dumps(
                            {
                                "report_id": "report-123",
                                "case_name": "Smith_v_Jones_2024",
                                "summary": {"total_deficiencies": 5},
                            }
                        )
                    }
                    mock_executor.return_value.execute_command = AsyncMock(
                        return_value=mock_report
                    )

                    response = client.get(
                        "/api/agents/deficiency-analyzer/report/report-123?format=json",
                        headers=auth_headers,
                    )

                    assert response.status_code == 200
                    assert response.headers["content-type"] == "application/json"

    def test_get_report_endpoint_pdf(self, client, mock_case_context, auth_headers):
        """Test report retrieval in PDF format."""
        with patch("src.api.agent_endpoints.require_case_context") as mock_auth:
            mock_auth.return_value = lambda: mock_case_context

            with patch("src.ai_agents.bmad_framework.AgentLoader") as mock_loader:
                mock_agent_def = {"commands": ["report"]}
                mock_loader.return_value.load_agent = AsyncMock(
                    return_value=mock_agent_def
                )

                with patch(
                    "src.ai_agents.bmad_framework.AgentExecutor"
                ) as mock_executor:
                    mock_report = {"content": b"PDF content here"}
                    mock_executor.return_value.execute_command = AsyncMock(
                        return_value=mock_report
                    )

                    response = client.get(
                        "/api/agents/deficiency-analyzer/report/report-123?format=pdf",
                        headers=auth_headers,
                    )

                    assert response.status_code == 200
                    assert response.headers["content-type"] == "application/pdf"
                    assert "attachment" in response.headers.get(
                        "content-disposition", ""
                    )

    def test_rate_limiting(self, client, mock_case_context, auth_headers):
        """Test rate limiting on endpoints."""
        # This would require setting up the rate limiter in test mode
        # For now, just verify the limiter decorator is present
        from src.api.agent_endpoints import analyze_production

        # Check that rate limit decorator is applied
        assert hasattr(analyze_production, "__wrapped__")

    def test_health_endpoint(self, client):
        """Test agent health check endpoint."""
        response = client.get("/api/agents/health")

        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "healthy"
        assert "timestamp" in data
        assert data["version"] == "1.0.0"

    def test_websocket_event_emission(self, client, mock_case_context, auth_headers):
        """Test that endpoints emit WebSocket events."""
        with patch("src.api.agent_endpoints.require_case_context") as mock_auth:
            mock_auth.return_value = lambda: mock_case_context

            with patch("src.ai_agents.bmad_framework.AgentLoader") as mock_loader:
                mock_agent_def = {"commands": ["analyze"]}
                mock_loader.return_value.load_agent = AsyncMock(
                    return_value=mock_agent_def
                )

                with patch(
                    "src.ai_agents.bmad_framework.websocket_progress.track_progress"
                ) as mock_tracker:
                    # Mock the context manager
                    mock_progress = AsyncMock()
                    mock_tracker.return_value.__aenter__.return_value = mock_progress

                    with patch("src.ai_agents.bmad_framework.AgentExecutor"):
                        response = client.post(
                            "/api/agents/deficiency-analyzer/analyze",
                            json={
                                "production_id": str(uuid4()),
                                "rtp_document_id": str(uuid4()),
                            },
                            headers=auth_headers,
                        )

                        assert response.status_code == 202
                        # Verify progress tracking was initiated
                        mock_tracker.assert_called_once()
                        call_args = mock_tracker.call_args
                        assert call_args[1]["case_id"] == "case-123"
                        assert call_args[1]["agent_id"] == "deficiency-analyzer"
