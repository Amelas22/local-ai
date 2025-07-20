"""
Security and case isolation module for BMad framework.

This module provides security middleware and permission checks for agent operations,
ensuring proper case isolation and access control.
"""

import logging
from typing import Optional, Dict, Any, List, Callable
from functools import wraps
from datetime import datetime
from fastapi import Request, HTTPException, Depends
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials

from src.middleware.case_context import get_case_context, require_case_context
from src.models.case_models import CaseContext, PermissionLevel
from .exceptions import ValidationError

logger = logging.getLogger("clerk_api")

# Security scheme for API endpoints
security = HTTPBearer(auto_error=False)


class AgentSecurityContext:
    """
    Security context for agent operations.
    
    Wraps case context with agent-specific security features.
    """
    
    def __init__(self, case_context: CaseContext, agent_id: str):
        """
        Initialize agent security context.
        
        Args:
            case_context: The case context from middleware.
            agent_id: The ID of the agent performing operations.
        """
        self.case_context = case_context
        self.agent_id = agent_id
        self.operation_log: List[Dict[str, Any]] = []
    
    @property
    def case_id(self) -> str:
        """Get case ID from context."""
        return self.case_context.case_id
    
    @property
    def case_name(self) -> str:
        """Get case name from context."""
        return self.case_context.case_name
    
    @property
    def user_id(self) -> str:
        """Get user ID from context."""
        return self.case_context.user_id
    
    @property
    def law_firm_id(self) -> str:
        """Get law firm ID from context."""
        return self.case_context.law_firm_id
    
    def has_permission(self, permission: str) -> bool:
        """
        Check if context has required permission.
        
        Args:
            permission: Permission level (read/write/admin).
            
        Returns:
            True if permission granted, False otherwise.
        """
        return self.case_context.has_permission(permission)
    
    def require_permission(self, permission: str) -> None:
        """
        Require specific permission level.
        
        Args:
            permission: Required permission level.
            
        Raises:
            HTTPException: If permission not granted.
        """
        if not self.has_permission(permission):
            self.log_operation("permission_denied", {"required": permission})
            raise HTTPException(
                status_code=403,
                detail=f"{permission.capitalize()} permission required for agent {self.agent_id}"
            )
    
    def log_operation(self, operation: str, details: Optional[Dict[str, Any]] = None) -> None:
        """
        Log an agent operation for audit trail.
        
        Args:
            operation: Operation name.
            details: Additional operation details.
        """
        timestamp = datetime.utcnow()
        log_entry = {
            "timestamp": timestamp.isoformat(),
            "timestamp_unix": timestamp.timestamp(),
            "operation": operation,
            "agent_id": self.agent_id,
            "case_id": self.case_id,
            "case_name": self.case_name,
            "user_id": self.user_id,
            "law_firm_id": self.law_firm_id,
            "details": details or {}
        }
        self.operation_log.append(log_entry)
        
        # Structured logging for better searchability
        logger.info(
            f"BMad Agent Operation: {operation}",
            extra={
                "bmad_agent_id": self.agent_id,
                "bmad_operation": operation,
                "case_id": self.case_id,
                "case_name": self.case_name,
                "user_id": self.user_id,
                "law_firm_id": self.law_firm_id,
                "details": details,
                "log_type": "bmad_audit"
            }
        )


def get_agent_security_context(
    agent_id: str,
    required_permission: str = "read"
) -> Callable:
    """
    Dependency to get agent security context with permission check.
    
    Args:
        agent_id: The agent performing operations.
        required_permission: Required permission level.
        
    Returns:
        Dependency function that returns AgentSecurityContext.
    """
    def dependency(
        request: Request,
        case_context: CaseContext = Depends(require_case_context(required_permission))
    ) -> AgentSecurityContext:
        """Get security context with case isolation."""
        security_context = AgentSecurityContext(case_context, agent_id)
        security_context.log_operation("agent_access", {"permission": required_permission})
        return security_context
    
    return dependency


def validate_case_isolation(func: Callable) -> Callable:
    """
    Decorator to ensure case isolation in agent operations.
    
    Validates that case_name parameter matches security context.
    """
    @wraps(func)
    async def wrapper(*args, **kwargs):
        # Extract security context and case_name from kwargs
        security_context = kwargs.get("security_context")
        case_name = kwargs.get("case_name")
        
        if security_context and case_name:
            # Validate case name matches context
            if case_name != security_context.case_name:
                raise ValidationError(
                    "Case isolation",
                    f"Case name mismatch: {case_name} != {security_context.case_name}",
                    {"provided": case_name, "context": security_context.case_name}
                )
        
        # Call original function
        return await func(*args, **kwargs)
    
    return wrapper


class AgentPermissionChecker:
    """
    Permission checker for agent operations.
    
    Maps agent commands to required permissions.
    """
    
    # Default permission mappings
    DEFAULT_PERMISSIONS = {
        # Read operations
        "search": "read",
        "analyze": "read",
        "list": "read",
        "view": "read",
        "get": "read",
        
        # Write operations  
        "create": "write",
        "update": "write",
        "generate": "write",
        "draft": "write",
        "save": "write",
        
        # Admin operations
        "delete": "admin",
        "configure": "admin",
        "manage": "admin",
    }
    
    def __init__(self, custom_permissions: Optional[Dict[str, str]] = None):
        """
        Initialize permission checker.
        
        Args:
            custom_permissions: Custom command to permission mappings.
        """
        self.permissions = self.DEFAULT_PERMISSIONS.copy()
        if custom_permissions:
            self.permissions.update(custom_permissions)
    
    def get_required_permission(self, command: str) -> str:
        """
        Get required permission for a command.
        
        Args:
            command: Command name (without * prefix).
            
        Returns:
            Required permission level.
        """
        # Remove * prefix if present
        command = command.lstrip("*")
        
        # Check exact match first
        if command in self.permissions:
            return self.permissions[command]
        
        # Check if command starts with known operation
        for operation, permission in self.permissions.items():
            if command.startswith(operation):
                return permission
        
        # Default to read permission
        return "read"
    
    def validate_command_access(
        self, 
        command: str, 
        security_context: AgentSecurityContext
    ) -> None:
        """
        Validate access to execute a command.
        
        Args:
            command: Command to execute.
            security_context: Agent security context.
            
        Raises:
            HTTPException: If access denied.
        """
        required = self.get_required_permission(command)
        security_context.require_permission(required)