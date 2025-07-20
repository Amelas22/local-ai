"""
Unit tests for BMad framework security module.
"""

import pytest
from unittest.mock import Mock, AsyncMock, patch
from datetime import datetime
from fastapi import Request, HTTPException

from src.ai_agents.bmad_framework.security import (
    AgentSecurityContext,
    get_agent_security_context,
    validate_case_isolation,
    AgentPermissionChecker
)
from src.ai_agents.bmad_framework.exceptions import ValidationError
from src.models.case_models import CaseContext, PermissionLevel


class TestAgentSecurityContext:
    """Test agent security context functionality."""
    
    def test_init_and_properties(self):
        """Test initialization and property access."""
        case_context = Mock(spec=CaseContext)
        case_context.case_id = "case-123"
        case_context.case_name = "Test Case"
        case_context.user_id = "user-456"
        case_context.law_firm_id = "firm-789"
        
        security_context = AgentSecurityContext(case_context, "test-agent")
        
        assert security_context.case_id == "case-123"
        assert security_context.case_name == "Test Case"
        assert security_context.user_id == "user-456"
        assert security_context.law_firm_id == "firm-789"
        assert security_context.agent_id == "test-agent"
        assert security_context.operation_log == []
    
    def test_has_permission(self):
        """Test permission checking."""
        case_context = Mock(spec=CaseContext)
        case_context.has_permission = Mock(return_value=True)
        
        security_context = AgentSecurityContext(case_context, "test-agent")
        
        assert security_context.has_permission("read") is True
        case_context.has_permission.assert_called_once_with("read")
    
    def test_require_permission_granted(self):
        """Test requiring permission when granted."""
        case_context = Mock(spec=CaseContext)
        case_context.has_permission = Mock(return_value=True)
        
        security_context = AgentSecurityContext(case_context, "test-agent")
        
        # Should not raise exception
        security_context.require_permission("write")
        case_context.has_permission.assert_called_with("write")
    
    def test_require_permission_denied(self):
        """Test requiring permission when denied."""
        case_context = Mock(spec=CaseContext)
        case_context.has_permission = Mock(return_value=False)
        case_context.case_id = "case-123"
        case_context.user_id = "user-456"
        
        security_context = AgentSecurityContext(case_context, "test-agent")
        
        with pytest.raises(HTTPException) as exc_info:
            security_context.require_permission("admin")
        
        assert exc_info.value.status_code == 403
        assert "Admin permission required" in str(exc_info.value.detail)
        assert "test-agent" in str(exc_info.value.detail)
    
    @patch('src.ai_agents.bmad_framework.security.logger')
    def test_log_operation(self, mock_logger):
        """Test operation logging."""
        case_context = Mock(spec=CaseContext)
        case_context.case_id = "case-123"
        case_context.user_id = "user-456"
        
        security_context = AgentSecurityContext(case_context, "test-agent")
        
        # Log an operation
        security_context.log_operation("test_op", {"key": "value"})
        
        # Check internal log
        assert len(security_context.operation_log) == 1
        log_entry = security_context.operation_log[0]
        assert log_entry["operation"] == "test_op"
        assert log_entry["agent_id"] == "test-agent"
        assert log_entry["case_id"] == "case-123"
        assert log_entry["user_id"] == "user-456"
        assert log_entry["details"] == {"key": "value"}
        assert "timestamp" in log_entry
        
        # Check logger was called
        mock_logger.info.assert_called_once()


class TestGetAgentSecurityContext:
    """Test agent security context dependency."""
    
    @pytest.mark.asyncio
    async def test_dependency_creation(self):
        """Test creating security context dependency."""
        # Create mock case context
        case_context = Mock(spec=CaseContext)
        case_context.case_id = "case-123"
        case_context.case_name = "Test Case"
        case_context.user_id = "user-456"
        case_context.law_firm_id = "firm-789"
        
        # Create dependency
        dependency = get_agent_security_context("test-agent", "write")
        
        # Mock request
        request = Mock(spec=Request)
        
        # Call dependency with mocked case context
        with patch(
            'src.ai_agents.bmad_framework.security.require_case_context',
            return_value=lambda req: case_context
        ):
            result = dependency(request, case_context)
        
        assert isinstance(result, AgentSecurityContext)
        assert result.agent_id == "test-agent"
        assert result.case_id == "case-123"
        
        # Check that access was logged
        assert len(result.operation_log) == 1
        assert result.operation_log[0]["operation"] == "agent_access"


class TestValidateCaseIsolation:
    """Test case isolation decorator."""
    
    @pytest.mark.asyncio
    async def test_case_isolation_valid(self):
        """Test decorator with matching case names."""
        @validate_case_isolation
        async def test_func(case_name: str, security_context: AgentSecurityContext):
            return f"Success: {case_name}"
        
        # Create mock security context
        case_context = Mock(spec=CaseContext)
        case_context.case_name = "Test_Case"
        security_context = AgentSecurityContext(case_context, "test-agent")
        
        result = await test_func(case_name="Test_Case", security_context=security_context)
        assert result == "Success: Test_Case"
    
    @pytest.mark.asyncio
    async def test_case_isolation_mismatch(self):
        """Test decorator with mismatched case names."""
        @validate_case_isolation
        async def test_func(case_name: str, security_context: AgentSecurityContext):
            return f"Success: {case_name}"
        
        # Create mock security context
        case_context = Mock(spec=CaseContext)
        case_context.case_name = "Test_Case"
        security_context = AgentSecurityContext(case_context, "test-agent")
        
        with pytest.raises(ValidationError) as exc_info:
            await test_func(case_name="Different_Case", security_context=security_context)
        
        assert "Case isolation" in str(exc_info.value)
        assert "Case name mismatch" in str(exc_info.value)
        assert exc_info.value.details["provided"] == "Different_Case"
        assert exc_info.value.details["context"] == "Test_Case"
    
    @pytest.mark.asyncio
    async def test_case_isolation_missing_params(self):
        """Test decorator when parameters are missing."""
        @validate_case_isolation
        async def test_func(**kwargs):
            return "Success"
        
        # Should work fine without security_context or case_name
        result = await test_func(other_param="value")
        assert result == "Success"


class TestAgentPermissionChecker:
    """Test agent permission checker."""
    
    def test_default_permissions(self):
        """Test default permission mappings."""
        checker = AgentPermissionChecker()
        
        # Read operations
        assert checker.get_required_permission("search") == "read"
        assert checker.get_required_permission("analyze") == "read"
        assert checker.get_required_permission("list") == "read"
        
        # Write operations
        assert checker.get_required_permission("create") == "write"
        assert checker.get_required_permission("update") == "write"
        assert checker.get_required_permission("generate") == "write"
        
        # Admin operations
        assert checker.get_required_permission("delete") == "admin"
        assert checker.get_required_permission("configure") == "admin"
    
    def test_custom_permissions(self):
        """Test custom permission mappings."""
        custom = {"custom_command": "admin", "special": "write"}
        checker = AgentPermissionChecker(custom_permissions=custom)
        
        # Custom permissions
        assert checker.get_required_permission("custom_command") == "admin"
        assert checker.get_required_permission("special") == "write"
        
        # Default still works
        assert checker.get_required_permission("search") == "read"
    
    def test_command_prefix_removal(self):
        """Test removal of * prefix from commands."""
        checker = AgentPermissionChecker()
        
        assert checker.get_required_permission("*search") == "read"
        assert checker.get_required_permission("*create") == "write"
        assert checker.get_required_permission("*delete") == "admin"
    
    def test_command_prefix_matching(self):
        """Test matching commands by prefix."""
        checker = AgentPermissionChecker()
        
        # Commands starting with known operations
        assert checker.get_required_permission("search_documents") == "read"
        assert checker.get_required_permission("create_report") == "write"
        assert checker.get_required_permission("delete_all") == "admin"
    
    def test_unknown_command_default(self):
        """Test default permission for unknown commands."""
        checker = AgentPermissionChecker()
        
        assert checker.get_required_permission("unknown") == "read"
        assert checker.get_required_permission("random_command") == "read"
    
    def test_validate_command_access_granted(self):
        """Test validating command access when granted."""
        case_context = Mock(spec=CaseContext)
        case_context.has_permission = Mock(return_value=True)
        security_context = AgentSecurityContext(case_context, "test-agent")
        
        checker = AgentPermissionChecker()
        
        # Should not raise exception
        checker.validate_command_access("create", security_context)
        case_context.has_permission.assert_called_with("write")
    
    def test_validate_command_access_denied(self):
        """Test validating command access when denied."""
        case_context = Mock(spec=CaseContext)
        case_context.has_permission = Mock(return_value=False)
        case_context.case_id = "case-123"
        case_context.user_id = "user-123"
        security_context = AgentSecurityContext(case_context, "test-agent")
        
        checker = AgentPermissionChecker()
        
        with pytest.raises(HTTPException) as exc_info:
            checker.validate_command_access("delete", security_context)
        
        assert exc_info.value.status_code == 403
        case_context.has_permission.assert_called_with("admin")