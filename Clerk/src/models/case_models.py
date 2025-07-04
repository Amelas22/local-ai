"""
Data models for case management in the multi-tenant legal AI system.
"""

from pydantic import BaseModel, Field, validator
from datetime import datetime
from typing import Optional, Dict, Any, List
from enum import Enum
from uuid import UUID


class CaseStatus(str, Enum):
    """Case lifecycle status"""
    ACTIVE = "active"
    ARCHIVED = "archived"
    CLOSED = "closed"


class PermissionLevel(str, Enum):
    """User permission levels for cases"""
    READ = "read"
    WRITE = "write"
    ADMIN = "admin"


class Case(BaseModel):
    """Core case model for Supabase storage"""
    id: str = Field(..., description="UUID")
    name: str = Field(..., max_length=50, description="User-friendly case name")
    law_firm_id: str = Field(..., description="Law firm UUID")
    collection_name: str = Field(..., max_length=63, description="Hashed name for Qdrant")
    status: CaseStatus = Field(default=CaseStatus.ACTIVE)
    created_by: str = Field(..., description="User UUID")
    created_at: datetime
    updated_at: datetime
    metadata: Dict[str, Any] = Field(default_factory=dict)
    
    @validator('name')
    def validate_case_name(cls, v):
        """Ensure case name is valid"""
        if not v or len(v.strip()) == 0:
            raise ValueError("Case name cannot be empty")
        
        # Remove extra whitespace
        v = ' '.join(v.split())
        
        if len(v) > 50:
            raise ValueError(f"Case name too long ({len(v)} chars). Maximum 50 characters allowed.")
        
        return v
    
    @validator('collection_name')
    def validate_collection_name(cls, v):
        """Ensure collection name meets Qdrant requirements"""
        if not v or len(v) == 0:
            raise ValueError("Collection name cannot be empty")
        
        if len(v) > 63:
            raise ValueError(f"Collection name too long ({len(v)} chars). Maximum 63 characters allowed.")
        
        # Check for valid characters (alphanumeric and underscore)
        if not all(c.isalnum() or c == '_' for c in v):
            raise ValueError("Collection name can only contain alphanumeric characters and underscores")
        
        return v

    class Config:
        json_encoders = {
            datetime: lambda v: v.isoformat()
        }


class CaseContext(BaseModel):
    """Request-scoped case context for middleware"""
    case_id: str
    case_name: str
    law_firm_id: str
    user_id: str
    permissions: List[str] = Field(default_factory=list)
    
    def has_permission(self, required: PermissionLevel) -> bool:
        """Check if context has required permission level"""
        if required == PermissionLevel.READ:
            return any(p in ["read", "write", "admin"] for p in self.permissions)
        elif required == PermissionLevel.WRITE:
            return any(p in ["write", "admin"] for p in self.permissions)
        elif required == PermissionLevel.ADMIN:
            return "admin" in self.permissions
        return False


class UserCasePermission(BaseModel):
    """User permission for a specific case"""
    id: str = Field(..., description="UUID")
    user_id: str = Field(..., description="User UUID")
    case_id: str = Field(..., description="Case UUID")
    permission_level: PermissionLevel
    granted_by: str = Field(..., description="User UUID who granted permission")
    granted_at: datetime
    expires_at: Optional[datetime] = None
    
    @validator('expires_at')
    def validate_expiration(cls, v, values):
        """Ensure expiration is in the future if set"""
        if v and 'granted_at' in values:
            if v <= values['granted_at']:
                raise ValueError("Expiration must be after granted time")
        return v


class CaseAuditLog(BaseModel):
    """Audit log entry for case-related actions"""
    id: str = Field(..., description="UUID")
    case_id: str = Field(..., description="Case UUID")
    user_id: str = Field(..., description="User UUID")
    action: str = Field(..., max_length=50, description="Action performed")
    resource_type: Optional[str] = Field(None, max_length=50)
    resource_id: Optional[str] = Field(None, max_length=255)
    metadata: Dict[str, Any] = Field(default_factory=dict)
    ip_address: Optional[str] = None
    user_agent: Optional[str] = None
    created_at: datetime


class CaseCreateRequest(BaseModel):
    """Request model for creating a new case"""
    name: str = Field(..., max_length=50, description="Case name")
    metadata: Optional[Dict[str, Any]] = None
    
    @validator('name')
    def validate_name(cls, v):
        """Validate case name"""
        v = v.strip()
        if not v:
            raise ValueError("Case name cannot be empty")
        if len(v) > 50:
            raise ValueError("Case name too long (max 50 characters)")
        return v


class CaseUpdateRequest(BaseModel):
    """Request model for updating a case"""
    name: Optional[str] = Field(None, max_length=50)
    status: Optional[CaseStatus] = None
    metadata: Optional[Dict[str, Any]] = None
    
    @validator('name')
    def validate_name(cls, v):
        """Validate case name if provided"""
        if v is not None:
            v = v.strip()
            if not v:
                raise ValueError("Case name cannot be empty")
            if len(v) > 50:
                raise ValueError("Case name too long (max 50 characters)")
        return v


class CaseListResponse(BaseModel):
    """Response model for case listing"""
    cases: List[Case]
    total: int
    page: int = 1
    page_size: int = 50
    has_more: bool = False


class CasePermissionRequest(BaseModel):
    """Request model for granting case permissions"""
    user_id: str = Field(..., description="User to grant permission to")
    permission_level: PermissionLevel
    expires_at: Optional[datetime] = None
    
    @validator('expires_at')
    def validate_expiration(cls, v):
        """Ensure expiration is in the future"""
        if v and v <= datetime.utcnow():
            raise ValueError("Expiration must be in the future")
        return v