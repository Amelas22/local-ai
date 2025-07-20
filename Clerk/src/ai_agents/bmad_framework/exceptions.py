"""
Exception classes for the BMad framework.

This module defines all custom exceptions used throughout the BMad framework
for legal AI agents.
"""

from typing import Optional, Dict, Any


class BMadFrameworkError(Exception):
    """
    Base exception class for all BMad framework errors.
    
    All other exceptions in this module inherit from this base class.
    """
    
    def __init__(self, message: str, details: Optional[Dict[str, Any]] = None):
        """
        Initialize the BMad framework error.
        
        Args:
            message: Human-readable error message.
            details: Optional dictionary with additional error context.
        """
        super().__init__(message)
        self.message = message
        self.details = details or {}
    
    def __str__(self) -> str:
        """String representation includes details if available."""
        if self.details:
            return f"{self.message} | Details: {self.details}"
        return self.message


class AgentLoadError(BMadFrameworkError):
    """
    Raised when an agent definition cannot be loaded.
    
    This includes YAML parsing errors, missing files, or invalid structure.
    """
    
    def __init__(self, agent_id: str, message: str, details: Optional[Dict[str, Any]] = None):
        """
        Initialize agent load error.
        
        Args:
            agent_id: The ID of the agent that failed to load.
            message: Specific error message.
            details: Additional error context.
        """
        super().__init__(f"Failed to load agent '{agent_id}': {message}", details)
        self.agent_id = agent_id


class TaskExecutionError(BMadFrameworkError):
    """
    Raised when a task execution fails.
    
    This includes task not found, execution errors, or dependency failures.
    """
    
    def __init__(self, task_name: str, message: str, details: Optional[Dict[str, Any]] = None):
        """
        Initialize task execution error.
        
        Args:
            task_name: Name of the task that failed.
            message: Specific error message.
            details: Additional error context.
        """
        super().__init__(f"Task '{task_name}' execution failed: {message}", details)
        self.task_name = task_name


class APIMappingError(BMadFrameworkError):
    """
    Raised when API mapping fails.
    
    This includes invalid command mappings or endpoint resolution failures.
    """
    
    def __init__(self, command: str, message: str, details: Optional[Dict[str, Any]] = None):
        """
        Initialize API mapping error.
        
        Args:
            command: The command that failed to map.
            message: Specific error message.
            details: Additional error context.
        """
        super().__init__(f"API mapping for command '{command}' failed: {message}", details)
        self.command = command


class DependencyNotFoundError(BMadFrameworkError):
    """
    Raised when a required dependency is not found.
    
    This includes missing tasks, templates, checklists, or data files.
    """
    
    def __init__(self, 
                 dependency_type: str, 
                 dependency_name: str, 
                 message: str = "", 
                 details: Optional[Dict[str, Any]] = None):
        """
        Initialize dependency not found error.
        
        Args:
            dependency_type: Type of dependency (task, template, checklist, data).
            dependency_name: Name of the missing dependency.
            message: Additional error message.
            details: Additional error context.
        """
        error_msg = f"{dependency_type.capitalize()} dependency '{dependency_name}' not found"
        if message:
            error_msg += f": {message}"
        super().__init__(error_msg, details)
        self.dependency_type = dependency_type
        self.dependency_name = dependency_name


class ValidationError(BMadFrameworkError):
    """
    Raised when validation fails.
    
    This includes invalid agent definitions, parameter validation, or schema violations.
    """
    
    def __init__(self, 
                 validation_type: str, 
                 message: str, 
                 details: Optional[Dict[str, Any]] = None):
        """
        Initialize validation error.
        
        Args:
            validation_type: Type of validation that failed.
            message: Specific validation error message.
            details: Additional error context including field names and values.
        """
        super().__init__(f"{validation_type} validation failed: {message}", details)
        self.validation_type = validation_type