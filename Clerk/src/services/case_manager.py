"""
Case Management Service - Compatibility adapter.

This module provides backward compatibility by wrapping the new PostgreSQL-based
case service with the original Supabase-style interface.
"""

import logging
from typing import List, Optional, Dict, Any
from datetime import datetime

from src.database.connection import AsyncSessionLocal
from src.services.case_service import CaseService
from src.models.case_models import Case, CaseStatus, CaseContext

logger = logging.getLogger(__name__)


class CaseManager:
    """
    Compatibility adapter for the original case_manager interface.

    This class wraps the new PostgreSQL-based CaseService to maintain
    backward compatibility with existing code.
    """

    def __init__(self):
        """Initialize the case manager adapter."""
        self._client = True  # Simulate having a client for compatibility
        logger.info("Initialized CaseManager compatibility adapter")

    def case_name_to_collection(self, case_name: str, law_firm_id: str) -> str:
        """
        Convert case name to a valid Qdrant collection name.

        Args:
            case_name: User-friendly case name
            law_firm_id: Law firm UUID for uniqueness

        Returns:
            Sanitized collection name (max 63 chars)
        """
        return CaseService.generate_collection_name(case_name, law_firm_id)

    async def create_case(
        self,
        name: str,
        law_firm_id: str,
        created_by: str,
        metadata: Optional[Dict[str, Any]] = None,
    ) -> Case:
        """
        Create a new case with validation.

        Args:
            name: Case name (max 50 chars)
            law_firm_id: Law firm UUID
            created_by: User UUID who created the case
            metadata: Optional metadata

        Returns:
            Created case object

        Raises:
            ValueError: If validation fails
            RuntimeError: If creation fails
        """
        async with AsyncSessionLocal() as db:
            return await CaseService.create_case(
                db=db,
                name=name,
                law_firm_id=law_firm_id,
                created_by=created_by,
                metadata=metadata,
            )

    async def get_user_cases(
        self,
        user_id: str,
        law_firm_id: Optional[str] = None,
        status: Optional[CaseStatus] = None,
        include_archived: bool = False,
    ) -> List[Case]:
        """
        Get cases accessible to a user.

        Args:
            user_id: User UUID
            law_firm_id: Optional law firm filter
            status: Optional status filter
            include_archived: Whether to include archived cases

        Returns:
            List of accessible cases
        """
        async with AsyncSessionLocal() as db:
            db_cases = await CaseService.get_user_cases(
                db=db,
                user_id=user_id,
                law_firm_id=law_firm_id,
                status=status,
                include_archived=include_archived,
            )

            # Convert to Pydantic models for compatibility
            cases = []
            for db_case in db_cases:
                # Parse metadata if it's JSON string
                metadata = {}
                if db_case.case_metadata:
                    try:
                        import json

                        metadata = json.loads(db_case.case_metadata)
                    except:
                        pass

                case = Case(
                    id=db_case.id,
                    name=db_case.name,
                    collection_name=db_case.collection_name,
                    description=db_case.description,
                    law_firm_id=db_case.law_firm_id,
                    status=db_case.status,
                    created_by=db_case.created_by,
                    metadata=metadata,
                    created_at=db_case.created_at,
                    updated_at=db_case.updated_at,
                )
                cases.append(case)

            return cases

    async def get_case_by_name(self, name: str, law_firm_id: str) -> Optional[Case]:
        """
        Get case by name and law firm.

        Args:
            name: Case name
            law_firm_id: Law firm UUID

        Returns:
            Case if found, None otherwise
        """
        async with AsyncSessionLocal() as db:
            db_case = await CaseService.get_case_by_name(db, name, law_firm_id)
            if not db_case:
                return None

            # Parse metadata
            metadata = {}
            if db_case.metadata:
                try:
                    import json

                    metadata = json.loads(db_case.metadata)
                except:
                    pass

            return Case(
                id=db_case.id,
                name=db_case.name,
                collection_name=db_case.collection_name,
                description=db_case.description,
                law_firm_id=db_case.law_firm_id,
                status=db_case.status,
                created_by=db_case.created_by,
                metadata=metadata,
                created_at=db_case.created_at,
                updated_at=db_case.updated_at,
            )

    async def get_case_by_id(self, case_id: str) -> Optional[Case]:
        """
        Get case by ID.

        Args:
            case_id: Case UUID

        Returns:
            Case if found, None otherwise
        """
        async with AsyncSessionLocal() as db:
            db_case = await CaseService.get_case_by_id(db, case_id)
            if not db_case:
                return None

            # Parse metadata
            metadata = {}
            if db_case.metadata:
                try:
                    import json

                    metadata = json.loads(db_case.metadata)
                except:
                    pass

            return Case(
                id=db_case.id,
                name=db_case.name,
                collection_name=db_case.collection_name,
                description=db_case.description,
                law_firm_id=db_case.law_firm_id,
                status=db_case.status,
                created_by=db_case.created_by,
                metadata=metadata,
                created_at=db_case.created_at,
                updated_at=db_case.updated_at,
            )

    async def update_case_status(
        self, case_id: str, status: CaseStatus, user_id: str
    ) -> Optional[Case]:
        """
        Update case status.

        Args:
            case_id: Case UUID
            status: New status
            user_id: User making the update

        Returns:
            Updated case if successful
        """
        async with AsyncSessionLocal() as db:
            db_case = await CaseService.update_case_status(
                db=db, case_id=case_id, status=status, user_id=user_id
            )

            if not db_case:
                return None

            # Parse metadata
            metadata = {}
            if db_case.metadata:
                try:
                    import json

                    metadata = json.loads(db_case.metadata)
                except:
                    pass

            return Case(
                id=db_case.id,
                name=db_case.name,
                collection_name=db_case.collection_name,
                description=db_case.description,
                law_firm_id=db_case.law_firm_id,
                status=db_case.status,
                created_by=db_case.created_by,
                metadata=metadata,
                created_at=db_case.created_at,
                updated_at=db_case.updated_at,
            )

    async def validate_case_access(
        self, case_id: str, user_id: str, required_permission: str = "read"
    ) -> bool:
        """
        Validate user has access to a case.

        Args:
            case_id: Case UUID
            user_id: User UUID
            required_permission: Required permission level (read/write/admin)

        Returns:
            True if user has access, False otherwise
        """
        async with AsyncSessionLocal() as db:
            return await CaseService.validate_case_access(
                db=db,
                case_id=case_id,
                user_id=user_id,
                required_permission=required_permission,
            )

    async def get_case_context(
        self, case_id: str, user_id: str
    ) -> Optional[CaseContext]:
        """
        Get case context with user permissions.

        Args:
            case_id: Case UUID
            user_id: User UUID

        Returns:
            Case context if user has access, None otherwise
        """
        async with AsyncSessionLocal() as db:
            return await CaseService.get_case_context(db, case_id, user_id)

    async def _grant_case_permission(
        self,
        user_id: str,
        case_id: str,
        permission_level: str,
        granted_by: str,
        expires_at: Optional[str] = None,
    ) -> bool:
        """
        Grant case permission (internal method for compatibility).

        Args:
            user_id: User to grant permission to
            case_id: Case UUID
            permission_level: Permission level (read/write/admin)
            granted_by: User granting the permission
            expires_at: Optional expiration ISO string

        Returns:
            True if successful
        """
        # Parse expiration if provided
        expires_datetime = None
        if expires_at:
            expires_datetime = datetime.fromisoformat(expires_at.replace("Z", "+00:00"))

        async with AsyncSessionLocal() as db:
            return await CaseService.grant_case_permission(
                db=db,
                case_id=case_id,
                user_id=user_id,
                permission_level=permission_level,
                granting_user_id=granted_by,
                expires_at=expires_datetime,
            )

    @property
    def client(self):
        """Compatibility property to simulate having a client."""
        return self._client


# Global instance for backward compatibility
case_manager = CaseManager()
