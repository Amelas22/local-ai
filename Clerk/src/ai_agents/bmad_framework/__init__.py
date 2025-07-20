"""
BMad Framework for Legal AI Agents.

This module provides a YAML-based framework for creating and executing
legal AI agents following BMad patterns.
"""

from .agent_loader import AgentLoader, AgentDefinition
from .agent_executor import AgentExecutor, ExecutionContext, ExecutionResult
from .api_mapper import APIMapper, APIMapping, HTTPMethod
from .exceptions import (
    BMadFrameworkError,
    AgentLoadError,
    TaskExecutionError,
    APIMappingError,
    DependencyNotFoundError,
    ValidationError
)
from .security import (
    AgentSecurityContext,
    get_agent_security_context,
    validate_case_isolation,
    AgentPermissionChecker
)

__all__ = [
    "AgentLoader",
    "AgentDefinition",
    "AgentExecutor",
    "ExecutionContext",
    "ExecutionResult",
    "APIMapper",
    "APIMapping",
    "HTTPMethod",
    "BMadFrameworkError",
    "AgentLoadError",
    "TaskExecutionError",
    "APIMappingError",
    "DependencyNotFoundError",
    "ValidationError",
    "AgentSecurityContext",
    "get_agent_security_context",
    "validate_case_isolation",
    "AgentPermissionChecker"
]

__version__ = "1.0.0"