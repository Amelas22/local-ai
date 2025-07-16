"""
Mock User Middleware for MVP Development

WARNING: This middleware is for MVP development only and MUST NOT be used in production.
It bypasses all authentication and injects a mock user into every request.

To re-enable authentication:
1. Remove this middleware from main.py
2. Uncomment AuthMiddleware import and registration
3. Remove MVP_MODE environment variable
"""

import os
from types import SimpleNamespace
from typing import Callable

from fastapi import Request, Response
from starlette.middleware.base import BaseHTTPMiddleware
from loguru import logger


class MockUserMiddleware(BaseHTTPMiddleware):
    """
    Inject mock user for MVP development - REMOVE IN PRODUCTION

    This middleware bypasses all authentication and injects a consistent
    mock user into every request. It ensures case isolation still works
    while eliminating auth-related debugging friction during MVP development.
    """

    # Mock user matching the dev user in the system
    MOCK_USER = SimpleNamespace(
        id="123e4567-e89b-12d3-a456-426614174001",
        email="dev@clerk.ai",
        name="Development User",
        law_firm_id="123e4567-e89b-12d3-a456-426614174000",
        law_firm_name="Development Law Firm",
        is_active=True,
        is_admin=True,
        permissions={"read": True, "write": True, "delete": True},
        # Additional fields for compatibility
        created_at="2024-01-01T00:00:00Z",
        updated_at="2024-01-01T00:00:00Z",
        auth_provider="local",
        metadata={
            "mvp_mode": True,
            "warning": "This is a mock user for MVP development only",
        },
    )

    def __init__(self, app):
        """
        Initialize the middleware and log MVP mode warning

        Args:
            app: The FastAPI application
        """
        super().__init__(app)
        logger.warning("🚨 MVP MODE ACTIVE - NO AUTHENTICATION 🚨")
        logger.warning(f"All requests will use mock user: {self.MOCK_USER.email}")
        logger.warning("DO NOT USE IN PRODUCTION!")

    async def dispatch(self, request: Request, call_next: Callable) -> Response:
        """
        Process the request and inject mock user

        Args:
            request: The incoming request
            call_next: The next middleware/endpoint in the chain

        Returns:
            Response: The response from the next handler
        """
        # Check if MVP mode is enabled
        if os.getenv("MVP_MODE", "false").lower() != "true":
            logger.error(
                "MockUserMiddleware is active but MVP_MODE is not set to 'true'"
            )
            logger.error(
                "This is a security risk! Set MVP_MODE=true or remove this middleware"
            )

        # Inject all user attributes into request.state
        # These match what AuthMiddleware would set
        request.state.user_id = self.MOCK_USER.id
        request.state.user_email = self.MOCK_USER.email
        request.state.user_name = self.MOCK_USER.name
        request.state.law_firm_id = self.MOCK_USER.law_firm_id
        request.state.is_admin = self.MOCK_USER.is_admin
        request.state.user = self.MOCK_USER

        # Add MVP mode indicator to request state
        request.state.mvp_mode = True

        # Log request with mock user (only in debug mode to avoid spam)
        logger.debug(
            f"MVP Mode: {request.method} {request.url.path} "
            f"with mock user {self.MOCK_USER.email}"
        )

        # Call the next middleware/endpoint
        response = await call_next(request)

        # Optionally add MVP mode header to response
        response.headers["X-MVP-Mode"] = "true"
        response.headers["X-Mock-User-Id"] = self.MOCK_USER.id

        return response

    @classmethod
    def get_mock_user(cls) -> SimpleNamespace:
        """
        Get the mock user object

        Returns:
            SimpleNamespace: The mock user object
        """
        return cls.MOCK_USER

    @classmethod
    def get_mock_user_id(cls) -> str:
        """
        Get the mock user ID

        Returns:
            str: The mock user ID
        """
        return cls.MOCK_USER.id

    @classmethod
    def get_mock_law_firm_id(cls) -> str:
        """
        Get the mock law firm ID

        Returns:
            str: The mock law firm ID
        """
        return cls.MOCK_USER.law_firm_id
