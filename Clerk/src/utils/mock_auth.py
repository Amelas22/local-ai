"""
Mock Authentication Dependencies for MVP Development

WARNING: These mock auth functions are for MVP development only and MUST NOT be used in production.
They bypass all authentication and return a consistent mock user.

To re-enable authentication:
1. Remove all imports of this module
2. Restore imports from src.utils.auth
3. Remove MVP_MODE environment variable
"""

from typing import Optional
from types import SimpleNamespace
from fastapi import Header
from loguru import logger

from src.middleware.mock_user_middleware import MockUserMiddleware


def get_mock_user() -> SimpleNamespace:
    """
    Get the mock user object for MVP development

    This replaces get_current_user from auth.py

    Returns:
        SimpleNamespace: The mock user object
    """
    return MockUserMiddleware.get_mock_user()


def get_mock_user_id() -> str:
    """
    Get the mock user ID for MVP development

    This replaces get_current_user_id from auth.py

    Returns:
        str: The mock user ID
    """
    return MockUserMiddleware.get_mock_user_id()


def mock_require_admin() -> SimpleNamespace:
    """
    Mock admin requirement check for MVP development

    This replaces require_admin from auth.py
    Always returns the mock user (who is an admin)

    Returns:
        SimpleNamespace: The mock user object
    """
    return MockUserMiddleware.get_mock_user()


def get_mock_case_context(
    case_id: Optional[str] = Header(None, alias="X-Case-ID"),
    x_case_name: Optional[str] = Header(None, alias="X-Case-Name"),
) -> SimpleNamespace:
    """
    Get mock case context for MVP development

    This provides a simplified version of case context that bypasses
    permission checks while maintaining case isolation.

    Args:
        case_id: Case ID from header
        x_case_name: Case name from header (fallback)

    Returns:
        SimpleNamespace: Mock case context with full permissions
    """
    # Use case_id if provided, otherwise fall back to x_case_name
    case_identifier = case_id or x_case_name

    if not case_identifier:
        logger.warning("No case identifier provided in MVP mode - using default")
        case_identifier = "default-mvp-case"

    # Return mock case context with full permissions
    return SimpleNamespace(
        case_id=case_identifier,
        case_name=case_identifier,
        user_id=MockUserMiddleware.get_mock_user_id(),
        law_firm_id=MockUserMiddleware.get_mock_law_firm_id(),
        permissions={"read": True, "write": True, "admin": True},
        is_admin=True,
        mvp_mode=True,
    )


def mock_require_case_context(permission: str = "read"):
    """
    Mock case context requirement for MVP development

    This replaces require_case_context from case_context.py
    Always returns a mock case context with full permissions

    Args:
        permission: Required permission level (ignored in MVP mode)

    Returns:
        Callable: Dependency function that returns mock case context
    """

    def _get_mock_case_context(
        case_id: Optional[str] = Header(None, alias="X-Case-ID"),
        x_case_name: Optional[str] = Header(None, alias="X-Case-Name"),
    ) -> SimpleNamespace:
        """Inner function for FastAPI dependency injection"""
        return get_mock_case_context(case_id, x_case_name)

    return _get_mock_case_context


# Convenience aliases to match original auth.py names
get_current_user = get_mock_user
get_current_user_id = get_mock_user_id
require_admin = mock_require_admin
require_case_context = mock_require_case_context


# MVP Mode indicator function
def is_mvp_mode() -> bool:
    """
    Check if MVP mode is active

    Returns:
        bool: True if MVP_MODE environment variable is set to 'true'
    """
    import os

    return os.getenv("MVP_MODE", "false").lower() == "true"


# Log warning when this module is imported
logger.warning("🚨 Mock auth module imported - MVP MODE ACTIVE 🚨")
logger.warning("Authentication is disabled. DO NOT USE IN PRODUCTION!")
