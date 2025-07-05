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
        exempt_patterns: Optional[List[str]] = None
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
        self.exempt_patterns.extend([
            re.compile(r"^/static/.*"),  # Static files
            re.compile(r"^/websocket/.*"),  # WebSocket endpoints
        ])
    
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
        # Check if path is exempt
        if self.is_exempt(request.url.path):
            return await call_next(request)
        
        # Extract token from Authorization header
        authorization = request.headers.get("Authorization")
        if not authorization:
            return JSONResponse(
                status_code=status.HTTP_401_UNAUTHORIZED,
                content={"detail": "Missing authentication token"},
                headers={"WWW-Authenticate": "Bearer"}
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
                headers={"WWW-Authenticate": "Bearer"}
            )
        
        # Validate token and get user
        try:
            async with AsyncSessionLocal() as db:
                user = await AuthService.get_current_user_from_token(db, token)
                
                if not user:
                    return JSONResponse(
                        status_code=status.HTTP_401_UNAUTHORIZED,
                        content={"detail": "Invalid or expired token"},
                        headers={"WWW-Authenticate": "Bearer"}
                    )
                
                if not user.is_active:
                    return JSONResponse(
                        status_code=status.HTTP_403_FORBIDDEN,
                        content={"detail": "User account is disabled"}
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
                headers={"WWW-Authenticate": "Bearer"}
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
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Not authenticated"
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
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Not authenticated"
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
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Admin privileges required"
        )