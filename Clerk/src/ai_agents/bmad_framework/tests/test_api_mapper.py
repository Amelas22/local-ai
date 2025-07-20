"""
Unit tests for BMad framework API mapper.
"""

import pytest
from src.ai_agents.bmad_framework.api_mapper import APIMapper, APIMapping, HTTPMethod
from src.ai_agents.bmad_framework.agent_loader import AgentDefinition
from src.ai_agents.bmad_framework.exceptions import APIMappingError, ValidationError


class TestAPIMapping:
    """Test APIMapping dataclass."""

    def test_basic_mapping(self):
        """Test creating basic API mapping."""
        mapping = APIMapping(
            command="test",
            method=HTTPMethod.POST,
            endpoint="/api/test",
            body_params=["param1", "param2"],
        )

        assert mapping.command == "test"
        assert mapping.method == HTTPMethod.POST
        assert mapping.endpoint == "/api/test"
        assert mapping.body_params == ["param1", "param2"]
        assert mapping.websocket_enabled is False

    def test_full_path_generation(self):
        """Test generating full path with parameters."""
        mapping = APIMapping(
            command="get",
            method=HTTPMethod.GET,
            endpoint="/api/agents/{agent_id}/resources",
            path_params=["agent_id", "resource_id"],
        )

        # Should add missing path param
        assert mapping.full_path == "/api/agents/{agent_id}/resources/{resource_id}"

    def test_format_endpoint(self):
        """Test formatting endpoint with values."""
        mapping = APIMapping(
            command="get",
            method=HTTPMethod.GET,
            endpoint="/api/agents/{agent_id}/resources/{resource_id}",
            path_params=["agent_id", "resource_id"],
        )

        formatted = mapping.format_endpoint(agent_id="test-agent", resource_id="123")

        assert formatted == "/api/agents/test-agent/resources/123"


class TestAPIMapper:
    """Test APIMapper functionality."""

    @pytest.fixture
    def mapper(self):
        """Create API mapper instance."""
        return APIMapper()

    def test_default_mappings(self, mapper):
        """Test default command mappings."""
        # Test analyze command
        mapping = mapper.get_mapping("analyze")
        assert mapping.command == "analyze"
        assert mapping.method == HTTPMethod.POST
        assert mapping.websocket_enabled is True
        assert "case_name" in mapping.body_params

        # Test search command
        mapping = mapper.get_mapping("search")
        assert mapping.method == HTTPMethod.POST
        assert "query" in mapping.body_params
        assert "limit" in mapping.query_params

        # Test CRUD operations
        assert mapper.get_mapping("create").method == HTTPMethod.POST
        assert mapper.get_mapping("list").method == HTTPMethod.GET
        assert mapper.get_mapping("update").method == HTTPMethod.PUT
        assert mapper.get_mapping("delete").method == HTTPMethod.DELETE

    def test_command_with_star_prefix(self, mapper):
        """Test handling commands with * prefix."""
        mapping = mapper.get_mapping("*analyze")
        assert mapping.command == "analyze"

    def test_unknown_command(self, mapper):
        """Test error for unknown command."""
        with pytest.raises(APIMappingError) as exc_info:
            mapper.get_mapping("unknown_command")

        assert "No API mapping found" in str(exc_info.value)
        assert exc_info.value.command == "unknown_command"

    def test_prefix_matching(self, mapper):
        """Test matching commands by prefix."""
        # Should match "create" mapping
        mapping = mapper.get_mapping("create_document")
        assert mapping.command == "create_document"
        assert mapping.method == HTTPMethod.POST
        assert mapping.endpoint == "/api/agents/{agent_id}/resources"

    def test_custom_mappings(self):
        """Test custom mappings override defaults."""
        custom = {
            "custom": APIMapping(
                command="custom",
                method=HTTPMethod.PATCH,
                endpoint="/api/custom/{id}",
                path_params=["id"],
            )
        }

        mapper = APIMapper(custom_mappings=custom)

        mapping = mapper.get_mapping("custom")
        assert mapping.method == HTTPMethod.PATCH
        assert mapping.endpoint == "/api/custom/{id}"

    def test_register_agent_mappings(self, mapper):
        """Test registering agent-specific mappings."""
        agent_def = AgentDefinition(
            id="test-agent",
            name="Test Agent",
            commands=[
                {"special_analyze": "Special analysis"},
                {"custom_report": "Custom report"},
            ],
        )

        mapper.register_agent_mappings(agent_def)

        # Should create agent-specific mappings
        mapping = mapper.get_mapping("special_analyze", agent_id="test-agent")
        assert mapping.command == "special_analyze"
        assert "test-agent" in mapping.endpoint

        # Should still work without agent_id for default commands
        default_mapping = mapper.get_mapping("analyze")
        assert default_mapping.command == "analyze"

    def test_infer_http_method(self, mapper):
        """Test HTTP method inference from command names."""
        # GET methods
        assert mapper._infer_http_method("get_user") == HTTPMethod.GET
        assert mapper._infer_http_method("list_items") == HTTPMethod.GET
        assert mapper._infer_http_method("search_docs") == HTTPMethod.GET
        assert mapper._infer_http_method("view_report") == HTTPMethod.GET

        # DELETE methods
        assert mapper._infer_http_method("delete_file") == HTTPMethod.DELETE
        assert mapper._infer_http_method("remove_user") == HTTPMethod.DELETE

        # PUT methods
        assert mapper._infer_http_method("update_profile") == HTTPMethod.PUT
        assert mapper._infer_http_method("edit_document") == HTTPMethod.PUT

        # POST methods (default)
        assert mapper._infer_http_method("create_user") == HTTPMethod.POST
        assert mapper._infer_http_method("analyze_data") == HTTPMethod.POST
        assert mapper._infer_http_method("process_file") == HTTPMethod.POST

    def test_websocket_inference(self, mapper):
        """Test WebSocket enablement inference."""
        # Should enable WebSocket
        assert mapper._should_enable_websocket("analyze_large_dataset") is True
        assert mapper._should_enable_websocket("generate_report") is True
        assert mapper._should_enable_websocket("process_documents") is True

        # Should not enable WebSocket
        assert mapper._should_enable_websocket("get_status") is False
        assert mapper._should_enable_websocket("list_items") is False

    def test_transform_parameters(self, mapper):
        """Test parameter transformation."""
        mapping = APIMapping(
            command="test",
            method=HTTPMethod.POST,
            endpoint="/api/test/{id}",
            path_params=["id"],
            query_params=["filter", "limit"],
            body_params=["data", "options"],
        )

        input_params = {
            "id": "123",
            "filter": "active",
            "limit": 10,
            "data": {"key": "value"},
            "options": {"opt1": True},
            "extra": "unknown",
        }

        path, query, body = mapper.transform_parameters(mapping, input_params)

        assert path == {"id": "123"}
        assert query == {"filter": "active", "limit": 10}
        assert body == {
            "data": {"key": "value"},
            "options": {"opt1": True},
            "extra": "unknown",  # Unknown params go to body
        }

    def test_transform_parameters_missing_required(self, mapper):
        """Test error when required parameters are missing."""
        mapping = APIMapping(
            command="test",
            method=HTTPMethod.GET,
            endpoint="/api/test/{id}/{type}",
            path_params=["id", "type"],
        )

        with pytest.raises(ValidationError) as exc_info:
            mapper.transform_parameters(mapping, {"id": "123"})

        assert "Missing required path parameters" in str(exc_info.value)
        assert "type" in exc_info.value.details["missing"]

    def test_numbered_options(self, mapper):
        """Test numbered options registration and retrieval."""
        options = [
            "1. Proceed to next step",
            "2. Edit current section",
            "3. Add more details",
            "4. Skip this section",
        ]

        mapper.register_numbered_options("review", options)

        retrieved = mapper.get_numbered_options("review")
        assert retrieved == options

        # Unknown command returns None
        assert mapper.get_numbered_options("unknown") is None

    def test_websocket_channel_format(self, mapper):
        """Test WebSocket channel formatting."""
        channel = mapper.format_websocket_channel(
            agent_id="discovery-analyzer", command="analyze", case_id="case-123"
        )

        assert channel == "agent:discovery-analyzer:analyze:case-123"

    def test_get_all_endpoints(self, mapper):
        """Test getting all available endpoints."""
        # Register some agent mappings
        agent_def = AgentDefinition(
            id="test-agent", commands=[{"custom_cmd": "Custom command"}]
        )
        mapper.register_agent_mappings(agent_def)

        # Get all endpoints
        endpoints = mapper.get_all_endpoints()

        # Should include default mappings
        analyze_endpoints = [e for e in endpoints if e["command"] == "analyze"]
        assert len(analyze_endpoints) == 1
        assert analyze_endpoints[0]["method"] == "POST"
        assert analyze_endpoints[0]["websocket"] == "Yes"

        # Get agent-specific endpoints
        agent_endpoints = mapper.get_all_endpoints(agent_id="test-agent")
        custom_endpoints = [e for e in agent_endpoints if e["command"] == "custom_cmd"]
        assert len(custom_endpoints) == 1

    def test_create_agent_mapping(self, mapper):
        """Test creating agent-specific mapping."""
        # Test various command types
        mapping = mapper._create_agent_mapping(
            "test-agent", "list_documents", "/api/agents"
        )
        assert mapping.method == HTTPMethod.GET
        assert mapping.endpoint == "/api/agents/test-agent/list_documents"
        assert "case_name" in mapping.query_params

        mapping = mapper._create_agent_mapping(
            "test-agent", "analyze_case", "/api/agents"
        )
        assert mapping.method == HTTPMethod.POST
        assert mapping.websocket_enabled is True
        assert "case_name" in mapping.body_params
