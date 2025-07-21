"""
Rate limiting middleware for API endpoints.

Provides simple in-memory rate limiting to prevent API abuse.
"""

from typing import Dict, List, Optional
from collections import defaultdict
from datetime import datetime, timedelta
import asyncio
from fastapi import HTTPException, Request, status

from src.utils.logger import get_logger
from src.utils.audit_logger import security_audit_logger

logger = get_logger("rate_limiter")


class RateLimiter:
    """
    Simple in-memory rate limiter.

    Tracks requests per identifier (IP address) and enforces
    rate limits over a sliding window.
    """

    def __init__(self, requests_per_minute: int = 60):
        """
        Initialize rate limiter.

        Args:
            requests_per_minute: Maximum requests allowed per minute
        """
        self.requests_per_minute = requests_per_minute
        self.requests: Dict[str, List[datetime]] = defaultdict(list)
        self._cleanup_task: Optional[asyncio.Task] = None
        self._lock = asyncio.Lock()

    async def check_rate_limit(self, identifier: str) -> bool:
        """
        Check if request is within rate limit.

        Args:
            identifier: Unique identifier (e.g., IP address)

        Returns:
            bool: True if within limit, False otherwise
        """
        async with self._lock:
            now = datetime.utcnow()
            minute_ago = now - timedelta(minutes=1)

            # Clean old requests
            self.requests[identifier] = [
                req_time
                for req_time in self.requests[identifier]
                if req_time > minute_ago
            ]

            # Check limit
            if len(self.requests[identifier]) >= self.requests_per_minute:
                logger.warning(f"Rate limit exceeded for {identifier}")
                return False

            # Record request
            self.requests[identifier].append(now)
            return True

    async def __aenter__(self):
        """Start cleanup task on context entry."""
        self._cleanup_task = asyncio.create_task(self._cleanup_loop())
        return self

    async def __aexit__(self, exc_type, exc_val, exc_tb):
        """Stop cleanup task on context exit."""
        if self._cleanup_task:
            self._cleanup_task.cancel()
            try:
                await self._cleanup_task
            except asyncio.CancelledError:
                pass

    async def _cleanup_loop(self):
        """Periodically clean old entries to prevent memory leak."""
        while True:
            try:
                await asyncio.sleep(300)  # Every 5 minutes
                await self._cleanup_old_entries()
            except asyncio.CancelledError:
                break
            except Exception as e:
                logger.error(f"Cleanup loop error: {e}")

    async def _cleanup_old_entries(self):
        """Remove old request entries."""
        async with self._lock:
            cutoff = datetime.utcnow() - timedelta(minutes=5)

            # Remove old entries
            empty_keys = []
            for key, timestamps in self.requests.items():
                self.requests[key] = [t for t in timestamps if t > cutoff]
                if not self.requests[key]:
                    empty_keys.append(key)

            # Remove empty keys
            for key in empty_keys:
                del self.requests[key]

            if empty_keys:
                logger.info(f"Cleaned up {len(empty_keys)} empty rate limit entries")


# Global rate limiter instances for different endpoints
letter_generation_limiter = RateLimiter(requests_per_minute=30)  # 30 letters per minute
general_api_limiter = RateLimiter(
    requests_per_minute=120
)  # 120 general requests per minute


async def check_letter_generation_limit(request: Request):
    """
    FastAPI dependency for letter generation rate limiting.

    Args:
        request: FastAPI request object

    Raises:
        HTTPException: If rate limit exceeded
    """
    # Use IP address as identifier
    identifier = request.client.host if request.client else "unknown"

    # Add user ID if authenticated
    if hasattr(request.state, "user_id") and request.state.user_id:
        identifier = f"{identifier}:{request.state.user_id}"

    if not await letter_generation_limiter.check_rate_limit(identifier):
        # Log rate limit exceeded
        security_audit_logger.log_rate_limit_exceeded(
            user_id=request.state.user_id
            if hasattr(request.state, "user_id")
            else "anonymous",
            endpoint=str(request.url),
            ip_address=request.client.host if request.client else "unknown",
        )

        raise HTTPException(
            status_code=status.HTTP_429_TOO_MANY_REQUESTS,
            detail="Rate limit exceeded for letter generation. Please try again in a minute.",
            headers={"Retry-After": "60"},
        )


async def check_general_api_limit(request: Request):
    """
    FastAPI dependency for general API rate limiting.

    Args:
        request: FastAPI request object

    Raises:
        HTTPException: If rate limit exceeded
    """
    # Use IP address as identifier
    identifier = request.client.host if request.client else "unknown"

    # Add user ID if authenticated
    if hasattr(request.state, "user_id") and request.state.user_id:
        identifier = f"{identifier}:{request.state.user_id}"

    if not await general_api_limiter.check_rate_limit(identifier):
        # Log rate limit exceeded
        security_audit_logger.log_rate_limit_exceeded(
            user_id=request.state.user_id
            if hasattr(request.state, "user_id")
            else "anonymous",
            endpoint=str(request.url),
            ip_address=request.client.host if request.client else "unknown",
        )

        raise HTTPException(
            status_code=status.HTTP_429_TOO_MANY_REQUESTS,
            detail="Rate limit exceeded. Please try again in a minute.",
            headers={"Retry-After": "60"},
        )


async def init_rate_limiters():
    """Initialize rate limiters on application startup."""
    await letter_generation_limiter.__aenter__()
    await general_api_limiter.__aenter__()
    logger.info("Rate limiters initialized")


async def shutdown_rate_limiters():
    """Shutdown rate limiters on application shutdown."""
    await letter_generation_limiter.__aexit__(None, None, None)
    await general_api_limiter.__aexit__(None, None, None)
    logger.info("Rate limiters shut down")
