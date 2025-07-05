"""
Case Management Service for multi-tenant legal AI system.
Handles case CRUD operations, validation, and access control.
"""

import hashlib
import logging
import time
from typing import List, Optional, Dict, Any
from datetime import datetime
from uuid import UUID, uuid4

from supabase import create_client, Client
from supabase.lib.client_options import ClientOptions
from pydantic import BaseModel, Field, validator

from config.settings import settings
from src.models.case_models import Case, CaseStatus, CaseContext, CaseCreateRequest, CaseUpdateRequest
from src.utils.logger import log_case_access

logger = logging.getLogger(__name__)


class CaseManager:
    """Manages case operations with Supabase backend"""
    
    def __init__(self):
        """Initialize Supabase client for case management"""
        self._client: Optional[Client] = None
        self._initialize_client()
    
    def _initialize_client(self) -> None:
        """Initialize Supabase client with retry logic"""
        if not settings.supabase.url or not settings.supabase.anon_key:
            logger.warning("Supabase credentials not configured. Case management will not work.")
            return
        
        # Use service role key if available for server-side operations
        auth_key = settings.supabase.service_role_key or settings.supabase.anon_key
        
        # Retry logic with exponential backoff
        max_retries = 3
        for attempt in range(max_retries):
            try:
                logger.info(f"Attempting to initialize Supabase client (attempt {attempt + 1}/{max_retries})")
                
                options = ClientOptions(
                    postgrest_client_timeout=30,
                    storage_client_timeout=30,
                )
                
                self._client = create_client(
                    settings.supabase.url,
                    auth_key,
                    options=options
                )
                
                # Test the connection by making a simple query
                # This helps verify the client is truly initialized
                try:
                    self._client.auth.get_session()
                except Exception:
                    # It's okay if session check fails - we just want to verify client is created
                    pass
                
                logger.info("Supabase client initialized successfully")
                return
                
            except Exception as e:
                logger.warning(f"Attempt {attempt + 1} failed to initialize Supabase client: {str(e)}")
                if attempt < max_retries - 1:
                    wait_time = 2 ** attempt  # Exponential backoff: 1s, 2s, 4s
                    logger.info(f"Retrying in {wait_time} seconds...")
                    time.sleep(wait_time)
                else:
                    logger.error(f"Failed to initialize Supabase client after {max_retries} attempts")
                    # Don't raise the error - allow the service to start but log the issue
                    # Operations using the client will fail with a more descriptive error
    
    @property
    def client(self) -> Client:
        """Get Supabase client, ensuring it's initialized"""
        if not self._client:
            raise RuntimeError("Supabase client not initialized. Check your configuration.")
        return self._client
    
    def case_name_to_collection(self, case_name: str, law_firm_id: str) -> str:
        """
        Convert case name to a valid Qdrant collection name.
        
        Args:
            case_name: User-friendly case name
            law_firm_id: Law firm UUID for uniqueness
            
        Returns:
            Sanitized collection name (max 63 chars)
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
    
    async def create_case(
        self,
        name: str,
        law_firm_id: str,
        created_by: str,
        metadata: Optional[Dict[str, Any]] = None
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
        try:
            # Validate case name
            if not name or len(name.strip()) == 0:
                raise ValueError("Case name cannot be empty")
            
            name = name.strip()
            if len(name) > 50:
                raise ValueError(f"Case name too long ({len(name)} chars). Maximum 50 characters allowed.")
            
            # Generate collection name
            collection_name = self.case_name_to_collection(name, law_firm_id)
            
            # Check if case already exists
            existing = await self.get_case_by_name(name, law_firm_id)
            if existing:
                raise ValueError(f"Case '{name}' already exists for this law firm")
            
            # Create case in Supabase
            case_data = {
                "name": name,
                "law_firm_id": str(law_firm_id),
                "collection_name": collection_name,
                "status": CaseStatus.ACTIVE.value,
                "created_by": str(created_by),
                "metadata": metadata or {}
            }
            
            result = self.client.table("cases").insert(case_data).execute()
            
            if not result.data:
                raise RuntimeError("Failed to create case")
            
            case = Case(**result.data[0])
            
            # Create initial permission for creator
            await self._grant_case_permission(
                user_id=created_by,
                case_id=case.id,
                permission_level="admin",
                granted_by=created_by
            )
            
            # Log case creation
            log_case_access(
                case_id=case.id,
                user_id=created_by,
                action="case_created",
                metadata={"case_name": name, "law_firm_id": str(law_firm_id)}
            )
            
            logger.info(f"Created case '{name}' with collection '{collection_name}'")
            return case
            
        except Exception as e:
            logger.error(f"Failed to create case: {str(e)}")
            raise
    
    async def get_user_cases(
        self,
        user_id: str,
        law_firm_id: Optional[str] = None,
        status: Optional[CaseStatus] = None,
        include_archived: bool = False
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
        try:
            # Build query using the user_active_cases view
            query = self.client.table("user_active_cases").select("*")
            
            # Note: The view already filters by user_id using auth.uid()
            # For service role key, we need to use the cases table directly
            if settings.supabase.service_role_key:
                query = self.client.table("cases").select(
                    """
                    *,
                    law_firms!inner(name),
                    user_case_permissions!inner(
                        permission_level,
                        granted_at,
                        expires_at
                    )
                    """
                ).eq("user_case_permissions.user_id", str(user_id))
            
            if law_firm_id:
                query = query.eq("law_firm_id", str(law_firm_id))
            
            if status:
                query = query.eq("status", status.value)
            elif not include_archived:
                query = query.neq("status", CaseStatus.ARCHIVED.value)
            
            result = query.execute()
            
            cases = [Case(**case_data) for case_data in result.data]
            
            logger.info(f"Retrieved {len(cases)} cases for user {user_id}")
            return cases
            
        except Exception as e:
            logger.error(f"Failed to get user cases: {str(e)}")
            return []
    
    async def get_case_by_name(self, name: str, law_firm_id: str) -> Optional[Case]:
        """
        Get case by name and law firm.
        
        Args:
            name: Case name
            law_firm_id: Law firm UUID
            
        Returns:
            Case if found, None otherwise
        """
        try:
            result = self.client.table("cases").select("*").eq(
                "name", name
            ).eq(
                "law_firm_id", str(law_firm_id)
            ).execute()
            
            if result.data:
                return Case(**result.data[0])
            
            return None
            
        except Exception as e:
            logger.error(f"Failed to get case by name: {str(e)}")
            return None
    
    async def get_case_by_id(self, case_id: str) -> Optional[Case]:
        """
        Get case by ID.
        
        Args:
            case_id: Case UUID
            
        Returns:
            Case if found, None otherwise
        """
        try:
            result = self.client.table("cases").select("*").eq(
                "id", str(case_id)
            ).single().execute()
            
            if result.data:
                return Case(**result.data)
            
            return None
            
        except Exception as e:
            logger.error(f"Failed to get case by ID: {str(e)}")
            return None
    
    async def update_case_status(
        self,
        case_id: str,
        status: CaseStatus,
        user_id: str
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
        try:
            # Verify user has write permission
            if not await self.validate_case_access(case_id, user_id, "write"):
                raise PermissionError("User does not have write access to this case")
            
            result = self.client.table("cases").update({
                "status": status.value
            }).eq("id", str(case_id)).execute()
            
            if result.data:
                case = Case(**result.data[0])
                
                # Log status change
                log_case_access(
                    case_id=case_id,
                    user_id=user_id,
                    action="case_status_updated",
                    metadata={"new_status": status.value}
                )
                
                return case
            
            return None
            
        except Exception as e:
            logger.error(f"Failed to update case status: {str(e)}")
            raise
    
    async def validate_case_access(
        self,
        case_id: str,
        user_id: str,
        required_permission: str = "read"
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
        try:
            result = self.client.table("user_case_permissions").select("*").eq(
                "case_id", str(case_id)
            ).eq(
                "user_id", str(user_id)
            ).execute()
            
            if not result.data:
                return False
            
            permission = result.data[0]
            
            # Check expiration
            if permission.get("expires_at"):
                expires_at = datetime.fromisoformat(permission["expires_at"].replace("Z", "+00:00"))
                if expires_at < datetime.now(expires_at.tzinfo):
                    return False
            
            # Check permission level
            user_level = permission["permission_level"]
            if required_permission == "read":
                return user_level in ["read", "write", "admin"]
            elif required_permission == "write":
                return user_level in ["write", "admin"]
            elif required_permission == "admin":
                return user_level == "admin"
            
            return False
            
        except Exception as e:
            logger.error(f"Failed to validate case access: {str(e)}")
            return False
    
    async def _grant_case_permission(
        self,
        user_id: str,
        case_id: str,
        permission_level: str,
        granted_by: str,
        expires_at: Optional[datetime] = None
    ) -> bool:
        """
        Grant case permission to a user.
        
        Args:
            user_id: User to grant permission to
            case_id: Case UUID
            permission_level: Permission level (read/write/admin)
            granted_by: User granting permission
            expires_at: Optional expiration time
            
        Returns:
            True if successful
        """
        try:
            permission_data = {
                "user_id": str(user_id),
                "case_id": str(case_id),
                "permission_level": permission_level,
                "granted_by": str(granted_by)
            }
            
            if expires_at:
                permission_data["expires_at"] = expires_at.isoformat()
            
            result = self.client.table("user_case_permissions").upsert(
                permission_data
            ).execute()
            
            return bool(result.data)
            
        except Exception as e:
            logger.error(f"Failed to grant case permission: {str(e)}")
            return False
    
    async def get_case_context(self, case_id: str, user_id: str) -> Optional[CaseContext]:
        """
        Get case context for request processing.
        
        Args:
            case_id: Case UUID
            user_id: User UUID
            
        Returns:
            CaseContext if user has access
        """
        try:
            # Get case with law firm info
            case_result = self.client.table("cases").select(
                """
                *,
                law_firms!inner(id, name)
                """
            ).eq("id", str(case_id)).single().execute()
            
            if not case_result.data:
                return None
            
            case_data = case_result.data
            
            # Get user permissions
            perm_result = self.client.table("user_case_permissions").select("*").eq(
                "case_id", str(case_id)
            ).eq(
                "user_id", str(user_id)
            ).execute()
            
            if not perm_result.data:
                return None
            
            permissions = [p["permission_level"] for p in perm_result.data]
            
            return CaseContext(
                case_id=case_data["id"],
                case_name=case_data["name"],
                law_firm_id=case_data["law_firm_id"],
                user_id=user_id,
                permissions=permissions
            )
            
        except Exception as e:
            logger.error(f"Failed to get case context: {str(e)}")
            return None


# Global instance
case_manager = CaseManager()