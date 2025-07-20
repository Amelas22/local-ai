"""
Unit tests for BMad framework exceptions.
"""

from src.ai_agents.bmad_framework.exceptions import (
    BMadFrameworkError,
    AgentLoadError,
    TaskExecutionError,
    APIMappingError,
    DependencyNotFoundError,
    ValidationError,
)


class TestBMadFrameworkError:
    """Test the base BMad framework error class."""

    def test_basic_error(self):
        """Test basic error creation."""
        error = BMadFrameworkError("Test error message")
        assert str(error) == "Test error message"
        assert error.message == "Test error message"
        assert error.details == {}

    def test_error_with_details(self):
        """Test error creation with details."""
        details = {"key": "value", "code": 123}
        error = BMadFrameworkError("Test error", details)
        assert error.message == "Test error"
        assert error.details == details
        assert error.details["key"] == "value"
        assert error.details["code"] == 123


class TestAgentLoadError:
    """Test agent load error handling."""

    def test_agent_load_error(self):
        """Test agent load error creation."""
        error = AgentLoadError("test-agent", "Invalid YAML format")
        assert "Failed to load agent 'test-agent': Invalid YAML format" in str(error)
        assert error.agent_id == "test-agent"
        assert error.message.startswith("Failed to load agent")

    def test_agent_load_error_with_details(self):
        """Test agent load error with additional details."""
        details = {"line": 42, "column": 10}
        error = AgentLoadError("discovery-analyzer", "Syntax error", details)
        assert error.agent_id == "discovery-analyzer"
        assert error.details["line"] == 42
        assert error.details["column"] == 10


class TestTaskExecutionError:
    """Test task execution error handling."""

    def test_task_execution_error(self):
        """Test task execution error creation."""
        error = TaskExecutionError("analyze-rtp", "Missing required parameter")
        assert "Task 'analyze-rtp' execution failed" in str(error)
        assert error.task_name == "analyze-rtp"

    def test_task_execution_error_with_context(self):
        """Test task execution error with context."""
        details = {"parameter": "case_name", "received": None}
        error = TaskExecutionError("search-production", "Invalid parameters", details)
        assert error.task_name == "search-production"
        assert error.details["parameter"] == "case_name"
        assert error.details["received"] is None


class TestAPIMappingError:
    """Test API mapping error handling."""

    def test_api_mapping_error(self):
        """Test API mapping error creation."""
        error = APIMappingError("*analyze", "No endpoint configured")
        assert "API mapping for command '*analyze' failed" in str(error)
        assert error.command == "*analyze"

    def test_api_mapping_error_with_suggestions(self):
        """Test API mapping error with suggestions."""
        details = {
            "available_commands": ["*help", "*search"],
            "closest_match": "*search",
        }
        error = APIMappingError("*serch", "Command not found", details)
        assert error.command == "*serch"
        assert error.details["closest_match"] == "*search"
        assert "*help" in error.details["available_commands"]


class TestDependencyNotFoundError:
    """Test dependency not found error handling."""

    def test_task_dependency_not_found(self):
        """Test task dependency not found error."""
        error = DependencyNotFoundError("task", "analyze-rtp.md")
        assert "Task dependency 'analyze-rtp.md' not found" in str(error)
        assert error.dependency_type == "task"
        assert error.dependency_name == "analyze-rtp.md"

    def test_template_dependency_not_found_with_message(self):
        """Test template dependency error with custom message."""
        error = DependencyNotFoundError(
            "template", "legal-doc-tmpl.yaml", "Check templates directory"
        )
        assert (
            "Template dependency 'legal-doc-tmpl.yaml' not found: Check templates directory"
            in str(error)
        )
        assert error.dependency_type == "template"

    def test_checklist_dependency_with_search_paths(self):
        """Test checklist dependency error with search paths."""
        details = {"searched_paths": ["/path1", "/path2"], "cwd": "/current"}
        error = DependencyNotFoundError("checklist", "pre-analysis.md", details=details)
        assert error.dependency_type == "checklist"
        assert error.details["searched_paths"] == ["/path1", "/path2"]
        assert error.details["cwd"] == "/current"


class TestValidationError:
    """Test validation error handling."""

    def test_schema_validation_error(self):
        """Test schema validation error."""
        error = ValidationError("Schema", "Missing required field 'agent.id'")
        assert "Schema validation failed: Missing required field" in str(error)
        assert error.validation_type == "Schema"

    def test_parameter_validation_error(self):
        """Test parameter validation error with details."""
        details = {
            "field": "case_name",
            "expected_type": "str",
            "received_type": "int",
            "value": 123,
        }
        error = ValidationError("Parameter", "Invalid type for case_name", details)
        assert error.validation_type == "Parameter"
        assert error.details["field"] == "case_name"
        assert error.details["expected_type"] == "str"
        assert error.details["received_type"] == "int"
        assert error.details["value"] == 123

    def test_agent_definition_validation_error(self):
        """Test agent definition validation error."""
        details = {
            "missing_sections": ["commands", "dependencies"],
            "invalid_fields": {"agent.icon": "Expected emoji, got string"},
        }
        error = ValidationError(
            "Agent definition", "Multiple validation failures", details
        )
        assert "Agent definition validation failed" in str(error)
        assert "commands" in error.details["missing_sections"]
        assert "dependencies" in error.details["missing_sections"]
        assert "agent.icon" in error.details["invalid_fields"]


class TestExceptionInheritance:
    """Test that all exceptions properly inherit from BMadFrameworkError."""

    def test_all_exceptions_inherit_from_base(self):
        """Verify inheritance hierarchy."""
        assert issubclass(AgentLoadError, BMadFrameworkError)
        assert issubclass(TaskExecutionError, BMadFrameworkError)
        assert issubclass(APIMappingError, BMadFrameworkError)
        assert issubclass(DependencyNotFoundError, BMadFrameworkError)
        assert issubclass(ValidationError, BMadFrameworkError)

    def test_exception_instances_are_base_type(self):
        """Verify instances are of base type."""
        errors = [
            AgentLoadError("test", "msg"),
            TaskExecutionError("test", "msg"),
            APIMappingError("test", "msg"),
            DependencyNotFoundError("task", "test"),
            ValidationError("test", "msg"),
        ]

        for error in errors:
            assert isinstance(error, BMadFrameworkError)
            assert isinstance(error, Exception)
