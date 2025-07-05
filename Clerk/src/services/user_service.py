"""
User Management Service for Clerk Legal AI System.

Handles user CRUD operations and law firm management.
"""
from typing import Optional, List
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, and_
from sqlalchemy.orm import selectinload
import logging

from src.database.models import User, LawFirm
from src.services.auth_service import AuthService

logger = logging.getLogger(__name__)


class UserService:
    """Service for user management operations."""
    
    @staticmethod
    async def create_user(
        db: AsyncSession,
        email: str,
        password: str,
        name: str,
        law_firm_id: str,
        is_admin: bool = False
    ) -> User:
        """
        Create a new user.
        
        Args:
            db: Database session.
            email: User's email address.
            password: Plain text password.
            name: User's full name.
            law_firm_id: ID of the law firm.
            is_admin: Whether user is an admin.
            
        Returns:
            User: Created user object.
            
        Raises:
            ValueError: If email already exists or law firm not found.
        """
        # Check if email already exists
        existing = await db.execute(
            select(User).where(User.email == email)
        )
        if existing.scalar_one_or_none():
            raise ValueError("Email already registered")
        
        # Verify law firm exists
        law_firm = await db.get(LawFirm, law_firm_id)
        if not law_firm or not law_firm.is_active:
            raise ValueError("Invalid or inactive law firm")
        
        # Create user
        user = User(
            email=email,
            password_hash=AuthService.hash_password(password),
            name=name,
            law_firm_id=law_firm_id,
            is_admin=is_admin
        )
        
        db.add(user)
        await db.commit()
        await db.refresh(user)
        
        # Load relationships
        await db.execute(
            select(User)
            .options(selectinload(User.law_firm))
            .where(User.id == user.id)
        )
        
        logger.info(f"Created user: {email} for law firm: {law_firm.name}")
        return user
    
    @staticmethod
    async def get_user_by_email(db: AsyncSession, email: str) -> Optional[User]:
        """
        Get a user by email address.
        
        Args:
            db: Database session.
            email: User's email address.
            
        Returns:
            Optional[User]: User object if found, None otherwise.
        """
        result = await db.execute(
            select(User)
            .options(selectinload(User.law_firm))
            .where(User.email == email)
        )
        return result.scalar_one_or_none()
    
    @staticmethod
    async def get_users_by_law_firm(db: AsyncSession, law_firm_id: str) -> List[User]:
        """
        Get all users for a law firm.
        
        Args:
            db: Database session.
            law_firm_id: ID of the law firm.
            
        Returns:
            List[User]: List of users in the law firm.
        """
        result = await db.execute(
            select(User)
            .where(and_(
                User.law_firm_id == law_firm_id,
                User.is_active == True
            ))
            .order_by(User.name)
        )
        return list(result.scalars().all())
    
    @staticmethod
    async def update_user(
        db: AsyncSession,
        user_id: str,
        name: Optional[str] = None,
        is_active: Optional[bool] = None,
        is_admin: Optional[bool] = None
    ) -> Optional[User]:
        """
        Update user information.
        
        Args:
            db: Database session.
            user_id: ID of the user to update.
            name: New name (optional).
            is_active: New active status (optional).
            is_admin: New admin status (optional).
            
        Returns:
            Optional[User]: Updated user object if found, None otherwise.
        """
        user = await db.get(User, user_id)
        if not user:
            return None
        
        if name is not None:
            user.name = name
        if is_active is not None:
            user.is_active = is_active
        if is_admin is not None:
            user.is_admin = is_admin
        
        await db.commit()
        await db.refresh(user)
        
        return user
    
    @staticmethod
    async def update_password(
        db: AsyncSession,
        user_id: str,
        new_password: str
    ) -> bool:
        """
        Update user's password.
        
        Args:
            db: Database session.
            user_id: ID of the user.
            new_password: New plain text password.
            
        Returns:
            bool: True if updated successfully, False otherwise.
        """
        user = await db.get(User, user_id)
        if not user:
            return False
        
        user.password_hash = AuthService.hash_password(new_password)
        await db.commit()
        
        # Revoke all refresh tokens when password changes
        await AuthService.revoke_all_user_tokens(db, user_id)
        
        logger.info(f"Password updated for user: {user.email}")
        return True
    
    @staticmethod
    async def delete_user(db: AsyncSession, user_id: str) -> bool:
        """
        Soft delete a user (set inactive).
        
        Args:
            db: Database session.
            user_id: ID of the user to delete.
            
        Returns:
            bool: True if deleted successfully, False otherwise.
        """
        user = await db.get(User, user_id)
        if not user:
            return False
        
        user.is_active = False
        await db.commit()
        
        # Revoke all refresh tokens
        await AuthService.revoke_all_user_tokens(db, user_id)
        
        logger.info(f"User soft deleted: {user.email}")
        return True
    
    @staticmethod
    async def create_law_firm(db: AsyncSession, name: str, domain: Optional[str] = None) -> LawFirm:
        """
        Create a new law firm.
        
        Args:
            db: Database session.
            name: Law firm name.
            domain: Optional email domain for the firm.
            
        Returns:
            LawFirm: Created law firm object.
            
        Raises:
            ValueError: If name already exists.
        """
        # Check if name already exists
        existing = await db.execute(
            select(LawFirm).where(LawFirm.name == name)
        )
        if existing.scalar_one_or_none():
            raise ValueError("Law firm name already exists")
        
        law_firm = LawFirm(name=name, domain=domain)
        db.add(law_firm)
        await db.commit()
        await db.refresh(law_firm)
        
        logger.info(f"Created law firm: {name}")
        return law_firm
    
    @staticmethod
    async def get_law_firm(db: AsyncSession, law_firm_id: str) -> Optional[LawFirm]:
        """
        Get a law firm by ID.
        
        Args:
            db: Database session.
            law_firm_id: ID of the law firm.
            
        Returns:
            Optional[LawFirm]: Law firm object if found, None otherwise.
        """
        return await db.get(LawFirm, law_firm_id)