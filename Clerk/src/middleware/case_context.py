"""
Case Context Middleware for FastAPI.
Validates case access and injects case context into requests.
"""

import logging
import time
from typing import Optional, Dict, Callable

from fastapi import Request, HTTPException
from fastapi.responses import JSONResponse
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.types import ASGIApp

from src.database.connection import AsyncSessionLocal
from src.services.case_service import CaseService
from src.models.case_models import CaseContext
from src.utils.logger import log_case_access

logger = logging.getLogger(__name__)


class CaseContextMiddleware(BaseHTTPMiddleware):
    """
    Middleware to validate case access and inject case context into requests.
    """

    # Paths that don't require case context
    EXEMPT_PATHS = {
        "/",
        "/health",
        "/docs",
        "/openapi.json",
        "/api/auth",
        "/api/cases",  # List/create cases
        "/ws",  # WebSocket connections
        "/websocket",
    }

    # Paths that require case context
    CASE_REQUIRED_PATHS = {
        "/api/search",
        "/api/documents",
        "/api/process",
        "/api/generate",
        "/api/hybrid-search",
        "/api/discovery",
    }

    def __init__(self, app: ASGIApp):
        super().__init__(app)
        self._cache_ttl = 300  # 5 minutes cache
        self._access_cache: Dict[str, tuple[float, bool]] = {}

    async def dispatch(self, request: Request, call_next: Callable) -> JSONResponse:
        """
        Process request and inject case context if needed.
        """
        start_time = time.time()

        # Check if path is exempt
        if self._is_exempt_path(request.url.path):
            return await call_next(request)

        # Check if path requires case context
        if not self._requires_case_context(request.url.path):
            return await call_next(request)
        
        # MVP Mode: Skip all case validation
        import os
        if os.getenv("MVP_MODE", "false").lower() == "true":
            # In MVP mode, inject mock case context if case ID is provided
            case_id = request.headers.get("X-Case-ID") or request.query_params.get("case_id")
            if case_id:
                # Create a simple mock case context
                from types import SimpleNamespace
                mock_context = SimpleNamespace(
                    case_id=case_id,
                    case_name=case_id,
                    user_id=getattr(request.state, "user_id", "mvp-user"),
                    law_firm_id=getattr(request.state, "law_firm_id", "mvp-firm"),
                    permissions={"read": True, "write": True, "admin": True},
                    is_admin=True,
                    has_permission=lambda perm: True
                )
                request.state.case_context = mock_context
                request.state.case_id = case_id
                request.state.case_name = case_id
            return await call_next(request)

        try:
            # Extract case ID from header
            case_id = request.headers.get("X-Case-ID")
            if not case_id:
                # Try to extract from query params as fallback
                case_id = request.query_params.get("case_id")

            if not case_id:
                logger.warning(f"No case ID provided for path: {request.url.path}")
                return JSONResponse(
                    status_code=400,
                    content={
                        "detail": "Case ID required. Please provide X-Case-ID header."
                    },
                )

            # Extract user ID (this should come from auth middleware)
            user_id = await self._get_user_id(request)
            if not user_id:
                return JSONResponse(
                    status_code=401, content={"detail": "Authentication required"}
                )

            # Check cache first
            cache_key = f"{user_id}:{case_id}"
            if cache_key in self._access_cache:
                cached_time, cached_result = self._access_cache[cache_key]
                if time.time() - cached_time < self._cache_ttl:
                    if not cached_result:
                        return JSONResponse(
                            status_code=403,
                            content={"detail": "Access denied to this case"},
                        )
                else:
                    # Cache expired, remove it
                    del self._access_cache[cache_key]

            # Validate case access using PostgreSQL
            async with AsyncSessionLocal() as db:
                has_access = await CaseService.validate_case_access(
                    db=db, case_id=case_id, user_id=user_id, required_permission="read"
                )

                # Update cache
                self._access_cache[cache_key] = (time.time(), has_access)

                if not has_access:
                    logger.warning(f"User {user_id} denied access to case {case_id}")
                    log_case_access(
                        case_id=case_id,
                        user_id=user_id,
                        action="access_denied",
                        metadata={"path": request.url.path, "method": request.method},
                    )
                    return JSONResponse(
                        status_code=403,
                        content={"detail": "Access denied to this case"},
                    )

                # Get full case context
                case_context = await CaseService.get_case_context(db, case_id, user_id)
            if not case_context:
                return JSONResponse(
                    status_code=404, content={"detail": "Case not found"}
                )

            # Inject case context into request state
            request.state.case_context = case_context
            request.state.case_id = case_id
            request.state.case_name = case_context.case_name

            # Log successful access
            log_case_access(
                case_id=case_id,
                user_id=user_id,
                action="case_accessed",
                metadata={
                    "path": request.url.path,
                    "method": request.method,
                    "duration_ms": int((time.time() - start_time) * 1000),
                },
            )

            # Process request
            response = await call_next(request)

            # Add case context to response headers for client
            response.headers["X-Case-ID"] = case_id
            response.headers["X-Case-Name"] = case_context.case_name

            return response

        except HTTPException:
            raise
        except Exception as e:
            logger.error(f"Case context middleware error: {str(e)}", exc_info=True)
            return JSONResponse(
                status_code=500,
                content={"detail": "Internal server error processing case context"},
            )

    def _is_exempt_path(self, path: str) -> bool:
        """Check if path is exempt from case context."""
        # Exact match
        if path in self.EXEMPT_PATHS:
            return True

        # Prefix match for exempt paths
        for exempt_path in self.EXEMPT_PATHS:
            if path.startswith(exempt_path + "/"):
                return True

        # Static files and health checks
        if path.startswith("/static/") or path.startswith("/_next/"):
            return True

        return False

    def _requires_case_context(self, path: str) -> bool:
        """Check if path requires case context."""
        # Check specific paths
        for required_path in self.CASE_REQUIRED_PATHS:
            if path.startswith(required_path):
                return True

        # Check general API paths that need case context
        if path.startswith("/api/") and not self._is_exempt_path(path):
            # Most API endpoints need case context except auth and case management
            return not any(path.startswith(p) for p in ["/api/auth", "/api/cases"])

        return False

    async def _get_user_id(self, request: Request) -> Optional[str]:
        """
        Extract user ID from request.
        This should be set by authentication middleware.
        """
        # Check request state (set by auth middleware)
        if hasattr(request.state, "user_id"):
            return request.state.user_id

        # Check for user in request state
        if hasattr(request.state, "user") and hasattr(request.state.user, "id"):
            return str(request.state.user.id)

        # Fallback to header (for development/testing)
        user_id = request.headers.get("X-User-ID")
        if user_id:
            logger.warning("Using X-User-ID header for authentication (dev mode)")
            return user_id

        return None

    def _clean_cache(self) -> None:
        """Remove expired entries from cache."""
        current_time = time.time()
        expired_keys = [
            key
            for key, (cached_time, _) in self._access_cache.items()
            if current_time - cached_time > self._cache_ttl
        ]
        for key in expired_keys:
            del self._access_cache[key]


def get_case_context(request: Request) -> Optional[CaseContext]:
    """
    Helper function to get case context from request.

    Args:
        request: FastAPI request object

    Returns:
        CaseContext if available, None otherwise
    """
    if hasattr(request.state, "case_context"):
        return request.state.case_context
    return None


def require_case_context(required_permission: str = "read") -> Callable:
    """
    Dependency to require case context with specific permission.

    Args:
        required_permission: Required permission level (read/write/admin)

    Returns:
        Dependency function
    """

    def dependency(request: Request) -> CaseContext:
        context = get_case_context(request)
        if not context:
            raise HTTPException(status_code=400, detail="Case context required")

        # Check permission
        if required_permission == "write" and not context.has_permission("write"):
            raise HTTPException(status_code=403, detail="Write permission required")
        elif required_permission == "admin" and not context.has_permission("admin"):
            raise HTTPException(status_code=403, detail="Admin permission required")

        return context

    return dependency
