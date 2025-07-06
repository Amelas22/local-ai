"""
Case Management Service using PostgreSQL.

Replaces Supabase-based case management with direct PostgreSQL operations.
"""
import hashlib
import logging
from typing import List, Optional, Dict, Any
from datetime import datetime, timezone
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, and_, or_, update
from sqlalchemy.orm import selectinload
import json

from src.database.models import Case, User, LawFirm, UserCasePermission, CaseStatus, PermissionLevel
from src.models.case_models import CaseContext
from src.utils.logger import log_case_access

logger = logging.getLogger(__name__)


class CaseService:
    """Service for case management operations using PostgreSQL."""
    
    @staticmethod
    def generate_collection_name(case_name: str, law_firm_id: str) -> str:
        """
        Convert case name to a valid Qdrant collection name.
        
        CRITICAL: This must exactly match the logic in case_manager.py
        
        Args:
            case_name: User-friendly case name.
            law_firm_id: Law firm UUID for uniqueness.
            
        Returns:
            str: Sanitized collection name (max 63 chars).
        """
        # Sanitize case name - remove special characters, convert to lowercase
        sanitized = ''.join(c if c.isalnum() or c in '_- ' else '_' for c in case_name.lower())
        sanitized = sanitized.replace(' ', '_').replace('-', '_')
        
        # Remove consecutive underscores
        while '__' in sanitized:
            sanitized = sanitized.replace('__', '_')
        
        # Create hash suffix for uniqueness
        hash_input = f"{law_firm_id}:{case_name}"
        hash_suffix = hashlib.md5(hash_input.encode()).hexdigest()[:8]
        
        # If name is too long, truncate and add hash
        if len(sanitized) > 50:
            sanitized = sanitized[:50]
        
        # Combine with hash
        collection_name = f"{sanitized}_{hash_suffix}"
        
        # Ensure it doesn't exceed 63 characters
        if len(collection_name) > 63:
            collection_name = collection_name[:63]
        
        return collection_name
    
    @staticmethod
    async def create_case(
        db: AsyncSession,
        name: str,
        law_firm_id: str,
        created_by: str,
        description: Optional[str] = None,
        metadata: Optional[Dict[str, Any]] = None
    ) -> Case:
        """
        Create a new case with validation.
        
        Args:
            db: Database session.
            name: Case name (max 50 chars).
            law_firm_id: Law firm UUID.
            created_by: User UUID who created the case.
            description: Optional case description.
            metadata: Optional metadata.
            
        Returns:
            Case: Created case object.
            
        Raises:
            ValueError: If validation fails.
            RuntimeError: If creation fails.
        """
        # Validate case name
        if not name or len(name.strip()) == 0:
            raise ValueError("Case name cannot be empty")
        
        name = name.strip()
        if len(name) > 50:
            raise ValueError(f"Case name too long ({len(name)} chars). Maximum 50 characters allowed.")
        
        # Generate collection name
        collection_name = CaseService.generate_collection_name(name, law_firm_id)
        
        # Check if case already exists
        existing = await CaseService.get_case_by_name(db, name, law_firm_id)
        if existing:
            raise ValueError(f"Case '{name}' already exists for this law firm")
        
        # Verify law firm exists
        law_firm = await db.get(LawFirm, law_firm_id)
        if not law_firm or not law_firm.is_active:
            raise ValueError("Invalid or inactive law firm")
        
        # Create case
        case = Case(
            name=name,
            collection_name=collection_name,
            description=description,
            law_firm_id=law_firm_id,
            status=CaseStatus.ACTIVE,
            created_by=created_by,
            case_metadata=json.dumps(metadata) if metadata else None
        )
        
        db.add(case)
        await db.commit()
        await db.refresh(case)
        
        # Create initial permission for creator
        await CaseService._grant_case_permission(
            db=db,
            user_id=created_by,
            case_id=case.id,
            permission_level=PermissionLevel.ADMIN,
            granted_by=created_by
        )
        
        # Log case creation
        log_case_access(
            logger=logger,
            user_id=created_by,
            case_name=name,
            action="case_created"
        )
        
        logger.info(f"Created case '{name}' with collection '{collection_name}'")
        return case
    
    @staticmethod
    async def get_user_cases(
        db: AsyncSession,
        user_id: str,
        law_firm_id: Optional[str] = None,
        status: Optional[CaseStatus] = None,
        include_archived: bool = False
    ) -> List[Case]:
        """
        Get cases accessible to a user.
        
        Args:
            db: Database session.
            user_id: User UUID.
            law_firm_id: Optional law firm filter.
            status: Optional status filter.
            include_archived: Whether to include archived cases.
            
        Returns:
            List[Case]: List of accessible cases.
        """
        query = select(Case).join(
            UserCasePermission,
            and_(
                UserCasePermission.case_id == Case.id,
                UserCasePermission.user_id == user_id
            )
        ).options(
            selectinload(Case.law_firm),
            selectinload(Case.permissions)
        )
        
        # Apply filters
        if law_firm_id:
            query = query.where(Case.law_firm_id == law_firm_id)
        
        if status:
            query = query.where(Case.status == status)
        elif not include_archived:
            query = query.where(Case.status != CaseStatus.ARCHIVED)
        
        # Filter out deleted cases unless explicitly requested
        query = query.where(Case.status != CaseStatus.DELETED)
        
        # Check permission expiration
        query = query.where(
            or_(
                UserCasePermission.expires_at.is_(None),
                UserCasePermission.expires_at > datetime.now(timezone.utc)
            )
        )
        
        result = await db.execute(query.order_by(Case.created_at.desc()))
        cases = list(result.scalars().unique())
        
        logger.info(f"Retrieved {len(cases)} cases for user {user_id}")
        return cases
    
    @staticmethod
    async def get_case_by_name(
        db: AsyncSession,
        name: str,
        law_firm_id: str
    ) -> Optional[Case]:
        """
        Get case by name and law firm.
        
        Args:
            db: Database session.
            name: Case name.
            law_firm_id: Law firm UUID.
            
        Returns:
            Optional[Case]: Case if found, None otherwise.
        """
        result = await db.execute(
            select(Case)
            .where(and_(
                Case.name == name,
                Case.law_firm_id == law_firm_id,
                Case.status != CaseStatus.DELETED
            ))
            .options(selectinload(Case.law_firm))
        )
        return result.scalar_one_or_none()
    
    @staticmethod
    async def get_case_by_id(db: AsyncSession, case_id: str) -> Optional[Case]:
        """
        Get case by ID.
        
        Args:
            db: Database session.
            case_id: Case UUID.
            
        Returns:
            Optional[Case]: Case if found, None otherwise.
        """
        result = await db.execute(
            select(Case)
            .where(Case.id == case_id)
            .options(
                selectinload(Case.law_firm),
                selectinload(Case.permissions)
            )
        )
        return result.scalar_one_or_none()
    
    @staticmethod
    async def update_case_status(
        db: AsyncSession,
        case_id: str,
        status: CaseStatus,
        user_id: str
    ) -> Optional[Case]:
        """
        Update case status.
        
        Args:
            db: Database session.
            case_id: Case UUID.
            status: New status.
            user_id: User making the update.
            
        Returns:
            Optional[Case]: Updated case if successful.
            
        Raises:
            PermissionError: If user lacks write permission.
        """
        # Verify user has write permission
        if not await CaseService.validate_case_access(db, case_id, user_id, "write"):
            raise PermissionError("User does not have write access to this case")
        
        case = await CaseService.get_case_by_id(db, case_id)
        if not case:
            return None
        
        case.status = status
        await db.commit()
        await db.refresh(case)
        
        # Log status change
        log_case_access(
            logger=logger,
            user_id=user_id,
            case_name=case.name,
            action="case_status_updated"
        )
        
        return case
    
    @staticmethod
    async def validate_case_access(
        db: AsyncSession,
        case_id: str,
        user_id: str,
        required_permission: str = "read"
    ) -> bool:
        """
        Validate user has access to a case.
        
        Args:
            db: Database session.
            case_id: Case UUID.
            user_id: User UUID.
            required_permission: Required permission level (read/write/admin).
            
        Returns:
            bool: True if user has access, False otherwise.
        """
        result = await db.execute(
            select(UserCasePermission)
            .where(and_(
                UserCasePermission.case_id == case_id,
                UserCasePermission.user_id == user_id
            ))
        )
        permission = result.scalar_one_or_none()
        
        if not permission:
            return False
        
        # Check expiration
        if permission.expires_at and permission.expires_at < datetime.now(timezone.utc):
            return False
        
        # Check permission level
        user_level = permission.permission_level
        if required_permission == "read":
            return user_level in [PermissionLevel.READ, PermissionLevel.WRITE, PermissionLevel.ADMIN]
        elif required_permission == "write":
            return user_level in [PermissionLevel.WRITE, PermissionLevel.ADMIN]
        elif required_permission == "admin":
            return user_level == PermissionLevel.ADMIN
        
        return False
    
    @staticmethod
    async def get_case_context(
        db: AsyncSession,
        case_id: str,
        user_id: str
    ) -> Optional[CaseContext]:
        """
        Get case context with user permissions.
        
        Args:
            db: Database session.
            case_id: Case UUID.
            user_id: User UUID.
            
        Returns:
            Optional[CaseContext]: Case context if user has access.
        """
        # Get case with permissions
        case = await CaseService.get_case_by_id(db, case_id)
        if not case:
            return None
        
        # Check user permission
        result = await db.execute(
            select(UserCasePermission)
            .where(and_(
                UserCasePermission.case_id == case_id,
                UserCasePermission.user_id == user_id
            ))
        )
        permission = result.scalar_one_or_none()
        
        if not permission:
            return None
        
        # Check expiration
        if permission.expires_at and permission.expires_at < datetime.now(timezone.utc):
            return None
        
        # Create case context
        permissions = ["read"]
        if permission.permission_level in [PermissionLevel.WRITE, PermissionLevel.ADMIN]:
            permissions.append("write")
        if permission.permission_level == PermissionLevel.ADMIN:
            permissions.append("admin")
        
        return CaseContext(
            case_id=case.id,
            case_name=case.name,
            collection_name=case.collection_name,
            law_firm_id=case.law_firm_id,
            permissions=permissions
        )
    
    @staticmethod
    async def grant_case_permission(
        db: AsyncSession,
        case_id: str,
        user_id: str,
        permission_level: str,
        granting_user_id: str,
        expires_at: Optional[datetime] = None
    ) -> bool:
        """
        Grant permission to a user for a case.
        
        Args:
            db: Database session.
            case_id: Case UUID.
            user_id: User to grant permission to.
            permission_level: Permission level (read/write/admin).
            granting_user_id: User granting the permission.
            expires_at: Optional expiration time.
            
        Returns:
            bool: True if successful.
            
        Raises:
            PermissionError: If granting user lacks admin permission.
        """
        # Verify granting user has admin permission
        if not await CaseService.validate_case_access(db, case_id, granting_user_id, "admin"):
            raise PermissionError("Only case admins can grant permissions")
        
        # Convert string permission to enum
        try:
            perm_level = PermissionLevel(permission_level)
        except ValueError:
            raise ValueError(f"Invalid permission level: {permission_level}")
        
        await CaseService._grant_case_permission(
            db=db,
            user_id=user_id,
            case_id=case_id,
            permission_level=perm_level,
            granted_by=granting_user_id,
            expires_at=expires_at
        )
        
        return True
    
    @staticmethod
    async def _grant_case_permission(
        db: AsyncSession,
        user_id: str,
        case_id: str,
        permission_level: PermissionLevel,
        granted_by: str,
        expires_at: Optional[datetime] = None
    ) -> None:
        """
        Internal method to grant case permission.
        
        Args:
            db: Database session.
            user_id: User ID.
            case_id: Case ID.
            permission_level: Permission level enum.
            granted_by: Granting user ID.
            expires_at: Optional expiration.
        """
        # Check if permission already exists
        result = await db.execute(
            select(UserCasePermission)
            .where(and_(
                UserCasePermission.case_id == case_id,
                UserCasePermission.user_id == user_id
            ))
        )
        existing = result.scalar_one_or_none()
        
        if existing:
            # Update existing permission
            existing.permission_level = permission_level
            existing.granted_by = granted_by
            existing.expires_at = expires_at
            existing.granted_at = datetime.now(timezone.utc)
        else:
            # Create new permission
            permission = UserCasePermission(
                user_id=user_id,
                case_id=case_id,
                permission_level=permission_level,
                granted_by=granted_by,
                expires_at=expires_at
            )
            db.add(permission)
        
        await db.commit()
        
        # Log permission grant
        # Need to get case name for logging
        case = await db.get(Case, case_id)
        if case:
            log_case_access(
                logger=logger,
                user_id=granted_by,
                case_name=case.name,
                action="permission_granted"
            )