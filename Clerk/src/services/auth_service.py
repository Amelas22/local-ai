"""
JWT Authentication Service for Clerk Legal AI System.

Handles user authentication, password hashing, and JWT token management.
"""

import logging
import secrets
from datetime import datetime, timedelta, timezone
from typing import Optional, Dict, Any

from jose import JWTError, jwt
from passlib.context import CryptContext
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from config.settings import settings
from src.database.models import User, RefreshToken

logger = logging.getLogger(__name__)

JWT_SECRET_KEY = settings.auth.jwt_secret_key
JWT_ALGORITHM = settings.auth.jwt_algorithm
ACCESS_TOKEN_EXPIRE_MINUTES = settings.auth.access_token_expire_minutes
REFRESH_TOKEN_EXPIRE_DAYS = settings.auth.refresh_token_expire_days

# Password hashing context
pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")


class AuthService:
    """Service for handling authentication operations."""

    @staticmethod
    def hash_password(password: str) -> str:
        """
        Hash a password using bcrypt.

        Args:
            password: Plain text password to hash.

        Returns:
            str: Hashed password.
        """
        return pwd_context.hash(password)

    @staticmethod
    def verify_password(plain_password: str, hashed_password: str) -> bool:
        """
        Verify a password against its hash.

        Args:
            plain_password: Plain text password to verify.
            hashed_password: Hashed password to check against.

        Returns:
            bool: True if password matches, False otherwise.
        """
        return pwd_context.verify(plain_password, hashed_password)

    @staticmethod
    def create_access_token(
        data: Dict[str, Any], expires_delta: Optional[timedelta] = None
    ) -> str:
        """
        Create a JWT access token.

        Args:
            data: Data to encode in the token.
            expires_delta: Optional custom expiration time.

        Returns:
            str: Encoded JWT token.
        """
        to_encode = data.copy()

        if expires_delta:
            expire = datetime.now(timezone.utc) + expires_delta
        else:
            expire = datetime.now(timezone.utc) + timedelta(
                minutes=ACCESS_TOKEN_EXPIRE_MINUTES
            )

        to_encode.update(
            {"exp": expire, "iat": datetime.now(timezone.utc), "type": "access"}
        )

        encoded_jwt = jwt.encode(to_encode, JWT_SECRET_KEY, algorithm=JWT_ALGORITHM)
        return encoded_jwt

    @staticmethod
    def create_refresh_token(data: Dict[str, Any]) -> str:
        """
        Create a JWT refresh token.

        Args:
            data: Data to encode in the token.

        Returns:
            str: Encoded JWT refresh token.
        """
        to_encode = data.copy()
        expire = datetime.now(timezone.utc) + timedelta(days=REFRESH_TOKEN_EXPIRE_DAYS)

        to_encode.update(
            {
                "exp": expire,
                "iat": datetime.now(timezone.utc),
                "type": "refresh",
                "jti": str(secrets.token_urlsafe(32)),  # Unique token ID
            }
        )

        encoded_jwt = jwt.encode(to_encode, JWT_SECRET_KEY, algorithm=JWT_ALGORITHM)
        return encoded_jwt

    @staticmethod
    def decode_token(token: str) -> Dict[str, Any]:
        """
        Decode and validate a JWT token.

        Args:
            token: JWT token to decode.

        Returns:
            Dict[str, Any]: Decoded token payload.

        Raises:
            JWTError: If token is invalid or expired.
        """
        try:
            payload = jwt.decode(token, JWT_SECRET_KEY, algorithms=[JWT_ALGORITHM])
            return payload
        except JWTError as e:
            logger.error(f"JWT decode error: {e}")
            raise

    @staticmethod
    async def authenticate_user(
        db: AsyncSession, email: str, password: str
    ) -> Optional[User]:
        """
        Authenticate a user by email and password.

        Args:
            db: Database session.
            email: User's email address.
            password: Plain text password.

        Returns:
            Optional[User]: User object if authentication successful, None otherwise.
        """
        # Query user with law firm data
        result = await db.execute(
            select(User).options(selectinload(User.law_firm)).where(User.email == email)
        )
        user = result.scalar_one_or_none()

        if not user:
            return None

        if not AuthService.verify_password(password, user.password_hash):
            return None

        if not user.is_active:
            logger.warning(f"Inactive user attempted login: {email}")
            return None

        # Update last login
        user.last_login = datetime.now(timezone.utc)
        await db.commit()

        return user

    @staticmethod
    async def get_user_by_id(db: AsyncSession, user_id: str) -> Optional[User]:
        """
        Get a user by ID.

        Args:
            db: Database session.
            user_id: User's ID.

        Returns:
            Optional[User]: User object if found, None otherwise.
        """
        result = await db.execute(
            select(User).options(selectinload(User.law_firm)).where(User.id == user_id)
        )
        return result.scalar_one_or_none()

    @staticmethod
    async def save_refresh_token(
        db: AsyncSession, user_id: str, token: str
    ) -> RefreshToken:
        """
        Save a refresh token to the database.

        Args:
            db: Database session.
            user_id: User's ID.
            token: Refresh token to save.

        Returns:
            RefreshToken: Saved refresh token object.
        """
        # Decode token to get expiration
        payload = AuthService.decode_token(token)
        expires_at = datetime.fromtimestamp(payload["exp"], tz=timezone.utc)

        refresh_token = RefreshToken(
            user_id=user_id, token=token, expires_at=expires_at
        )

        db.add(refresh_token)
        await db.commit()
        await db.refresh(refresh_token)

        return refresh_token

    @staticmethod
    async def validate_refresh_token(
        db: AsyncSession, token: str
    ) -> Optional[RefreshToken]:
        """
        Validate a refresh token.

        Args:
            db: Database session.
            token: Refresh token to validate.

        Returns:
            Optional[RefreshToken]: Refresh token object if valid, None otherwise.
        """
        result = await db.execute(
            select(RefreshToken)
            .where(RefreshToken.token == token)
            .where(RefreshToken.revoked_at.is_(None))
            .where(RefreshToken.expires_at > datetime.now(timezone.utc))
        )

        return result.scalar_one_or_none()

    @staticmethod
    async def revoke_refresh_token(db: AsyncSession, token: str) -> bool:
        """
        Revoke a refresh token.

        Args:
            db: Database session.
            token: Refresh token to revoke.

        Returns:
            bool: True if revoked successfully, False otherwise.
        """
        result = await db.execute(
            select(RefreshToken).where(RefreshToken.token == token)
        )
        refresh_token = result.scalar_one_or_none()

        if refresh_token and not refresh_token.revoked_at:
            refresh_token.revoked_at = datetime.now(timezone.utc)
            await db.commit()
            return True

        return False

    @staticmethod
    async def revoke_all_user_tokens(db: AsyncSession, user_id: str) -> int:
        """
        Revoke all refresh tokens for a user.

        Args:
            db: Database session.
            user_id: User's ID.

        Returns:
            int: Number of tokens revoked.
        """
        result = await db.execute(
            select(RefreshToken)
            .where(RefreshToken.user_id == user_id)
            .where(RefreshToken.revoked_at.is_(None))
        )
        tokens = result.scalars().all()

        count = 0
        for token in tokens:
            token.revoked_at = datetime.now(timezone.utc)
            count += 1

        if count > 0:
            await db.commit()

        return count

    @staticmethod
    def create_token_pair(user: User) -> Dict[str, str]:
        """
        Create access and refresh token pair for a user.

        Args:
            user: User object.

        Returns:
            Dict[str, str]: Dictionary with access_token and refresh_token.
        """
        # Token payload
        token_data = {
            "sub": user.id,
            "email": user.email,
            "name": user.name,
            "law_firm_id": user.law_firm_id,
            "is_admin": user.is_admin,
        }

        access_token = AuthService.create_access_token(token_data)
        refresh_token = AuthService.create_refresh_token(token_data)

        return {
            "access_token": access_token,
            "refresh_token": refresh_token,
            "token_type": "bearer",
        }

    @staticmethod
    async def get_current_user_from_token(
        db: AsyncSession, token: str
    ) -> Optional[User]:
        """
        Get current user from JWT token.

        Args:
            db: Database session.
            token: JWT access token.

        Returns:
            Optional[User]: User object if token valid, None otherwise.
        """
        try:
            payload = AuthService.decode_token(token)

            # Verify token type
            if payload.get("type") != "access":
                return None

            user_id = payload.get("sub")
            if not user_id:
                return None

            return await AuthService.get_user_by_id(db, user_id)

        except JWTError:
            return None
