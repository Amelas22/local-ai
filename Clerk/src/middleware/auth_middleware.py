"""
JWT Authentication Middleware for Clerk Legal AI System.

Validates JWT tokens and injects user information into request state.
"""

from typing import Optional, List, Callable
from fastapi import Request, HTTPException, status
from fastapi.responses import JSONResponse
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.types import ASGIApp
import logging
import re

from src.database.connection import AsyncSessionLocal
from src.services.auth_service import AuthService
from config.settings import settings

logger = logging.getLogger(__name__)


class AuthMiddleware(BaseHTTPMiddleware):
    """
    Middleware for JWT authentication.

    Validates JWT tokens from Authorization header and injects user info
    into request.state for downstream handlers.
    """

    def __init__(
        self,
        app: ASGIApp,
        exempt_paths: Optional[List[str]] = None,
        exempt_patterns: Optional[List[str]] = None,
    ):
        """
        Initialize authentication middleware.

        Args:
            app: FastAPI application.
            exempt_paths: List of exact paths to exempt from authentication.
            exempt_patterns: List of regex patterns for paths to exempt.
        """
        super().__init__(app)

        # Default exempt paths
        self.exempt_paths = exempt_paths or [
            "/health",
            "/api/auth/login",
            "/api/auth/register",
            "/api/auth/refresh",
            "/docs",
            "/redoc",
            "/openapi.json",
            "/ws/socket.io",  # WebSocket paths
        ]

        # Compile regex patterns
        self.exempt_patterns = [
            re.compile(pattern) for pattern in (exempt_patterns or [])
        ]

        # Add default patterns
        self.exempt_patterns.extend(
            [
                re.compile(r"^/static/.*"),  # Static files
                re.compile(r"^/websocket/.*"),  # WebSocket endpoints
            ]
        )

    def is_exempt(self, path: str) -> bool:
        """
        Check if a path is exempt from authentication.

        Args:
            path: Request path.

        Returns:
            bool: True if path is exempt, False otherwise.
        """
        # Check exact paths
        if path in self.exempt_paths:
            return True

        # Check patterns
        for pattern in self.exempt_patterns:
            if pattern.match(path):
                return True

        return False

    async def dispatch(self, request: Request, call_next: Callable) -> JSONResponse:
        """
        Process the request and validate authentication.

        Args:
            request: FastAPI request object.
            call_next: Next middleware or endpoint handler.

        Returns:
            JSONResponse: Response from the endpoint or error response.
        """
        # Debug logging
        logger.info(f"Auth middleware processing: {request.url.path}")
        logger.info(f"AUTH_ENABLED: {settings.auth.auth_enabled}")
        logger.info(f"Is Development: {settings.is_development}")
        logger.info(
            f"Headers: Authorization={request.headers.get('Authorization', 'None')}"
        )

        # Check if path is exempt
        if self.is_exempt(request.url.path):
            logger.info(f"Path {request.url.path} is exempt from auth")
            return await call_next(request)

        # Extract token from Authorization header
        authorization = request.headers.get("Authorization")
        if not authorization:
            return JSONResponse(
                status_code=status.HTTP_401_UNAUTHORIZED,
                content={"detail": "Missing authentication token"},
                headers={"WWW-Authenticate": "Bearer"},
            )

        # Parse Bearer token
        try:
            scheme, token = authorization.split()
            if scheme.lower() != "bearer":
                raise ValueError("Invalid authentication scheme")
        except ValueError:
            return JSONResponse(
                status_code=status.HTTP_401_UNAUTHORIZED,
                content={"detail": "Invalid authentication header format"},
                headers={"WWW-Authenticate": "Bearer"},
            )

        # Check if auth is disabled in development mode
        if not settings.auth.auth_enabled and settings.is_development:
            logger.info(
                f"Dev mode auth check: token={token[:20]}... expected={settings.auth.dev_mock_token[:20]}..."
            )
            # Check if it's the development mock token
            if token == settings.auth.dev_mock_token:
                # Fetch the actual dev user from the database
                logger.info("Development mode: Fetching dev user from database")
                try:
                    async with AsyncSessionLocal() as db:
                        # Get the dev user by ID
                        from sqlalchemy import select
                        from sqlalchemy.orm import selectinload
                        from src.database.models import User

                        result = await db.execute(
                            select(User)
                            .options(selectinload(User.law_firm))
                            .where(User.id == "123e4567-e89b-12d3-a456-426614174001")
                        )
                        dev_user = result.scalar_one_or_none()

                        if dev_user:
                            # Use the actual user from the database
                            request.state.user_id = dev_user.id
                            request.state.user_email = dev_user.email
                            request.state.user_name = dev_user.name
                            request.state.law_firm_id = dev_user.law_firm_id
                            request.state.is_admin = dev_user.is_admin
                            request.state.user = dev_user
                            logger.info(
                                f"Development mode: Authenticated as {dev_user.email} with law_firm_id {dev_user.law_firm_id}"
                            )
                        else:
                            # Fallback to mock user if dev user doesn't exist
                            logger.warning(
                                "Development mode: Dev user not found in database, using mock user"
                            )
                            request.state.user_id = (
                                "123e4567-e89b-12d3-a456-426614174001"
                            )
                            request.state.user_email = "dev@clerk.ai"
                            request.state.user_name = "Dev User"
                            request.state.law_firm_id = (
                                "123e4567-e89b-12d3-a456-426614174000"
                            )
                            request.state.is_admin = True

                            # Create a mock user object with law firm for compatibility
                            from src.database.models import User, LawFirm

                            mock_law_firm = LawFirm(
                                id="123e4567-e89b-12d3-a456-426614174000",
                                name="Development Law Firm",
                                domain="dev.clerk.ai",
                                is_active=True,
                            )
                            mock_user = User(
                                id="123e4567-e89b-12d3-a456-426614174001",
                                email="dev@clerk.ai",
                                name="Dev User",
                                law_firm_id="123e4567-e89b-12d3-a456-426614174000",
                                law_firm=mock_law_firm,
                                is_active=True,
                                is_admin=True,
                                password_hash="$2b$12$LQv3c1yqBWVHxkd0LHAkCOYz6TtxMQJqhN8/LewKyNiGHTGpFyNBC",
                            )
                            request.state.user = mock_user
                except Exception as e:
                    logger.error(f"Database error in dev mode: {e}")
                    # Fallback to mock user on any database error
                    request.state.user_id = "dev-user-123"
                    request.state.user_email = "dev@clerk.ai"
                    request.state.user_name = "Development User"
                    request.state.law_firm_id = "dev-firm-123"
                    request.state.is_admin = True

                    # Return minimal mock user on database error
                    from types import SimpleNamespace

                    request.state.user = SimpleNamespace(
                        id="dev-user-123",
                        email="dev@clerk.ai",
                        name="Development User",
                        law_firm_id="dev-firm-123",
                        is_active=True,
                        is_admin=True,
                    )
            else:
                logger.warning(
                    f"Development mode: Invalid mock token provided: {token[:20]}..."
                )
                return JSONResponse(
                    status_code=status.HTTP_401_UNAUTHORIZED,
                    content={
                        "detail": "Invalid development token. Use the configured DEV_MOCK_TOKEN."
                    },
                    headers={"WWW-Authenticate": "Bearer"},
                )
        else:
            # Production mode or auth enabled - validate token normally
            try:
                async with AsyncSessionLocal() as db:
                    user = await AuthService.get_current_user_from_token(db, token)

                    if not user:
                        return JSONResponse(
                            status_code=status.HTTP_401_UNAUTHORIZED,
                            content={"detail": "Invalid or expired token"},
                            headers={"WWW-Authenticate": "Bearer"},
                        )

                    if not user.is_active:
                        return JSONResponse(
                            status_code=status.HTTP_403_FORBIDDEN,
                            content={"detail": "User account is disabled"},
                        )

                    # Inject user info into request state
                    request.state.user_id = user.id
                    request.state.user_email = user.email
                    request.state.user_name = user.name
                    request.state.law_firm_id = user.law_firm_id
                    request.state.is_admin = user.is_admin
                    request.state.user = user  # Full user object

                    logger.debug(f"Authenticated request from user: {user.email}")

            except Exception as e:
                logger.error(f"Authentication error: {e}")
                return JSONResponse(
                    status_code=status.HTTP_401_UNAUTHORIZED,
                    content={"detail": "Authentication failed"},
                    headers={"WWW-Authenticate": "Bearer"},
                )

        # Process request
        response = await call_next(request)

        # Add user context to response headers (optional)
        if hasattr(request.state, "user_id"):
            response.headers["X-User-ID"] = request.state.user_id

        return response


def get_current_user_id(request: Request) -> str:
    """
    Get current user ID from request state.

    Args:
        request: FastAPI request object.

    Returns:
        str: User ID.

    Raises:
        HTTPException: If user not authenticated.
    """
    if not hasattr(request.state, "user_id"):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED, detail="Not authenticated"
        )
    return request.state.user_id


def get_current_law_firm_id(request: Request) -> str:
    """
    Get current user's law firm ID from request state.

    Args:
        request: FastAPI request object.

    Returns:
        str: Law firm ID.

    Raises:
        HTTPException: If user not authenticated.
    """
    if not hasattr(request.state, "law_firm_id"):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED, detail="Not authenticated"
        )
    return request.state.law_firm_id


def require_admin(request: Request) -> None:
    """
    Require admin privileges for the current user.

    Args:
        request: FastAPI request object.

    Raises:
        HTTPException: If user is not an admin.
    """
    if not hasattr(request.state, "is_admin") or not request.state.is_admin:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN, detail="Admin privileges required"
        )
