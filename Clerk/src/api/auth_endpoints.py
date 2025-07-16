"""
Authentication API endpoints for Clerk Legal AI System.

Provides OAuth2-compatible endpoints for user registration, login, and token refresh.
"""

from typing import Dict, Optional
from fastapi import APIRouter, Depends, HTTPException, status, Request
from fastapi.security import OAuth2PasswordRequestForm, OAuth2PasswordBearer
from sqlalchemy.ext.asyncio import AsyncSession
from pydantic import BaseModel, Field
import logging

# Using str instead of EmailStr to avoid email-validator dependency
# TODO: Replace with EmailStr after installing email-validator
EmailStr = str

from src.database.connection import get_db
from src.services.auth_service import AuthService
from src.services.user_service import UserService
from src.database.models import User

logger = logging.getLogger(__name__)

# MVP Mode imports
import os

if os.getenv("MVP_MODE", "false").lower() == "true":
    from src.utils.mock_auth import get_mock_user as get_current_user_mvp

    logger.warning("Auth endpoints using MVP mode - authentication bypassed")

# OAuth2 scheme for token extraction
oauth2_scheme = OAuth2PasswordBearer(tokenUrl="/api/auth/login", auto_error=False)

# Create router
router = APIRouter(prefix="/api/auth", tags=["authentication"])


# Pydantic schemas
class UserRegister(BaseModel):
    """User registration request schema."""

    email: EmailStr
    password: str = Field(..., min_length=8)
    name: str = Field(..., min_length=1)
    law_firm_id: str


class UserResponse(BaseModel):
    """User response schema."""

    id: str
    email: str
    name: str
    law_firm_id: str
    is_admin: bool
    is_active: bool

    class Config:
        from_attributes = True


class TokenResponse(BaseModel):
    """Token response schema for OAuth2 compatibility."""

    access_token: str
    refresh_token: str
    token_type: str = "bearer"


class RefreshTokenRequest(BaseModel):
    """Refresh token request schema."""

    refresh_token: str


class PasswordChangeRequest(BaseModel):
    """Password change request schema."""

    current_password: str
    new_password: str = Field(..., min_length=8)


async def get_current_user(
    request: Request,
    token: Optional[str] = Depends(oauth2_scheme),
    db: AsyncSession = Depends(get_db),
) -> User:
    """
    Dependency to get current authenticated user.

    First checks if user was already authenticated by middleware (in development mode),
    otherwise validates JWT token.

    Args:
        request: FastAPI request object.
        token: JWT token from Authorization header.
        db: Database session.

    Returns:
        User: Current authenticated user.

    Raises:
        HTTPException: If authentication fails.
    """
    # MVP Mode: Return mock user
    if os.getenv("MVP_MODE", "false").lower() == "true":
        return get_current_user_mvp()

    # Check if user was already authenticated by middleware
    if hasattr(request.state, "user") and request.state.user:
        return request.state.user
    
    # No token provided
    if not token:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Not authenticated",
            headers={"WWW-Authenticate": "Bearer"},
        )

    # Otherwise, validate token normally
    user = await AuthService.get_current_user_from_token(db, token)
    if not user:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Could not validate credentials",
            headers={"WWW-Authenticate": "Bearer"},
        )
    return user


@router.post(
    "/register", response_model=UserResponse, status_code=status.HTTP_201_CREATED
)
async def register(
    user_data: UserRegister, db: AsyncSession = Depends(get_db)
) -> UserResponse:
    """
    Register a new user.

    Args:
        user_data: User registration data.
        db: Database session.

    Returns:
        UserResponse: Created user information.

    Raises:
        HTTPException: If registration fails.
    """
    try:
        user = await UserService.create_user(
            db=db,
            email=user_data.email,
            password=user_data.password,
            name=user_data.name,
            law_firm_id=user_data.law_firm_id,
        )

        logger.info(f"New user registered: {user.email}")
        return UserResponse.model_validate(user)

    except ValueError as e:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))
    except Exception as e:
        logger.error(f"Registration error: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Registration failed",
        )


@router.post("/login", response_model=TokenResponse)
async def login(
    form_data: OAuth2PasswordRequestForm = Depends(), db: AsyncSession = Depends(get_db)
) -> TokenResponse:
    """
    Login user and return JWT tokens.

    OAuth2 compatible endpoint using form data.

    Args:
        form_data: OAuth2 form with username (email) and password.
        db: Database session.

    Returns:
        TokenResponse: Access and refresh tokens.

    Raises:
        HTTPException: If authentication fails.
    """
    # OAuth2PasswordRequestForm uses 'username' field, but we use email
    user = await AuthService.authenticate_user(
        db, form_data.username, form_data.password
    )

    if not user:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Incorrect email or password",
            headers={"WWW-Authenticate": "Bearer"},
        )

    # Create token pair
    tokens = AuthService.create_token_pair(user)

    # Save refresh token
    await AuthService.save_refresh_token(db, user.id, tokens["refresh_token"])

    logger.info(f"User logged in: {user.email}")
    return TokenResponse(**tokens)


@router.post("/refresh", response_model=TokenResponse)
async def refresh_token(
    token_request: RefreshTokenRequest, db: AsyncSession = Depends(get_db)
) -> TokenResponse:
    """
    Refresh access token using refresh token.

    Args:
        token_request: Request with refresh token.
        db: Database session.

    Returns:
        TokenResponse: New access and refresh tokens.

    Raises:
        HTTPException: If refresh token is invalid.
    """
    # Validate refresh token
    refresh_token_obj = await AuthService.validate_refresh_token(
        db, token_request.refresh_token
    )

    if not refresh_token_obj:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid refresh token"
        )

    # Get user
    user = await AuthService.get_user_by_id(db, refresh_token_obj.user_id)
    if not user or not user.is_active:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="User not found or inactive",
        )

    # Revoke old refresh token
    await AuthService.revoke_refresh_token(db, token_request.refresh_token)

    # Create new token pair
    tokens = AuthService.create_token_pair(user)

    # Save new refresh token
    await AuthService.save_refresh_token(db, user.id, tokens["refresh_token"])

    logger.info(f"Tokens refreshed for user: {user.email}")
    return TokenResponse(**tokens)


@router.post("/logout")
async def logout(
    current_user: User = Depends(get_current_user), db: AsyncSession = Depends(get_db)
) -> Dict[str, str]:
    """
    Logout user by revoking all refresh tokens.

    Args:
        current_user: Current authenticated user.
        db: Database session.

    Returns:
        Dict[str, str]: Success message.
    """
    count = await AuthService.revoke_all_user_tokens(db, current_user.id)
    logger.info(f"User logged out: {current_user.email}, {count} tokens revoked")

    return {"message": "Logged out successfully"}


@router.get("/me", response_model=UserResponse)
async def get_current_user_info(
    current_user: User = Depends(get_current_user),
) -> UserResponse:
    """
    Get current user information.

    Args:
        current_user: Current authenticated user.

    Returns:
        UserResponse: User information.
    """
    return UserResponse.model_validate(current_user)


@router.post("/change-password")
async def change_password(
    password_data: PasswordChangeRequest,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> Dict[str, str]:
    """
    Change user's password.

    Args:
        password_data: Current and new password.
        current_user: Current authenticated user.
        db: Database session.

    Returns:
        Dict[str, str]: Success message.

    Raises:
        HTTPException: If current password is incorrect.
    """
    # Verify current password
    if not AuthService.verify_password(
        password_data.current_password, current_user.password_hash
    ):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Current password is incorrect",
        )

    # Update password
    success = await UserService.update_password(
        db, current_user.id, password_data.new_password
    )

    if not success:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to update password",
        )

    logger.info(f"Password changed for user: {current_user.email}")
    return {"message": "Password changed successfully"}
