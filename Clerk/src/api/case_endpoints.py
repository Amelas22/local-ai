"""
Case Management API endpoints for Clerk Legal AI System.

Provides endpoints for case CRUD operations and permissions management.
"""
from typing import Optional, List, Dict, Any
from datetime import datetime
from fastapi import APIRouter, Depends, HTTPException, status, Request
from sqlalchemy.ext.asyncio import AsyncSession
from pydantic import BaseModel, Field
import logging

from src.database.connection import get_db
from src.services.case_service import CaseService
from src.services.auth_service import AuthService
from src.database.models import User, Case as DBCase, CaseStatus
from src.vector_storage.qdrant_store import QdrantVectorStore
from src.models.case_models import (
    Case,
    CaseCreateRequest,
    CaseUpdateRequest,
    CaseListResponse,
    CaseContext,
    CasePermissionRequest as PermissionGrantRequest
)
from src.api.auth_endpoints import get_current_user
from src.middleware.auth_middleware import get_current_user_id, get_current_law_firm_id

logger = logging.getLogger(__name__)

# Create router
router = APIRouter(prefix="/api/cases", tags=["cases"])


async def create_case_collections_with_events(
    vector_store,  # QdrantVectorStore instance
    collection_name: str,
    case_id: str
) -> bool:
    """
    Create Qdrant collections for a case with WebSocket progress events.
    
    Args:
        vector_store: QdrantVectorStore instance
        collection_name: Base collection name
        case_id: Case ID for event emission
        
    Returns:
        True if all collections created successfully
    """
    from src.websocket.socket_server import emit_case_event
    
    # Emit start event
    await emit_case_event("collections_started", case_id, {
        "totalCollections": 4,
        "message": "Creating vector storage collections"
    })
    
    # Create collections
    results = await vector_store.create_case_collections(collection_name)
    
    # Emit progress for each collection
    success_count = 0
    for idx, (coll_name, success) in enumerate(results.items()):
        collection_type = "main"
        if "_facts" in coll_name:
            collection_type = "facts"
        elif "_timeline" in coll_name:
            collection_type = "timeline"
        elif "_depositions" in coll_name:
            collection_type = "depositions"
            
        if success:
            success_count += 1
            await emit_case_event("collection_created", case_id, {
                "collectionName": coll_name,
                "collectionType": collection_type,
                "progress": (idx + 1) / 4
            })
        else:
            await emit_case_event("collection_failed", case_id, {
                "collectionName": coll_name,
                "collectionType": collection_type,
                "error": "Failed to create collection"
            })
    
    # Emit completion event
    if success_count == 4:
        await emit_case_event("collections_ready", case_id, {
            "message": "All collections created successfully",
            "collectionsCreated": success_count
        })
        return True
    else:
        await emit_case_event("collections_partial", case_id, {
            "message": f"Created {success_count} of 4 collections",
            "collectionsCreated": success_count,
            "collectionsFailed": 4 - success_count
        })
        return False


def get_case_context_dependency(required_permission: str = "read"):
    """
    Create a dependency that validates case access.
    
    Args:
        required_permission: Required permission level (read/write/admin).
        
    Returns:
        Dependency function for FastAPI.
    """
    async def _validate_case_context(
        case_id: str,
        current_user: User = Depends(get_current_user),
        db: AsyncSession = Depends(get_db)
    ) -> CaseContext:
        """Validate user has required permission for the case."""
        # Get case context
        case_context = await CaseService.get_case_context(db, case_id, current_user.id)
        
        if not case_context:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Case not found or access denied"
            )
        
        # Check permission
        if required_permission not in case_context.permissions:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail=f"Insufficient permissions. Required: {required_permission}"
            )
        
        return case_context
    
    return _validate_case_context


@router.get("", response_model=CaseListResponse)
async def list_user_cases(
    law_firm_id: Optional[str] = None,
    include_archived: bool = False,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
) -> CaseListResponse:
    """
    List cases accessible to the authenticated user.
    
    Args:
        law_firm_id: Optional filter by law firm.
        include_archived: Whether to include archived cases.
        current_user: Current authenticated user.
        db: Database session.
        
    Returns:
        CaseListResponse: List of accessible cases.
    """
    try:
        cases = await CaseService.get_user_cases(
            db=db,
            user_id=current_user.id,
            law_firm_id=law_firm_id,
            include_archived=include_archived
        )
        
        # Convert to Pydantic models
        case_models = []
        for case in cases:
            # Parse metadata if it's JSON string
            metadata = {}
            if case.case_metadata:
                try:
                    import json
                    metadata = json.loads(case.case_metadata)
                except:
                    pass
            
            case_model = Case(
                id=case.id,
                name=case.name,
                collection_name=case.collection_name,
                description=case.description,
                law_firm_id=case.law_firm_id,
                status=case.status,
                created_by=case.created_by,
                metadata=metadata,
                created_at=case.created_at,
                updated_at=case.updated_at or case.created_at  # Fallback to created_at if updated_at is NULL
            )
            case_models.append(case_model)
        
        return CaseListResponse(
            cases=case_models,
            total=len(case_models),
            has_more=False
        )
        
    except Exception as e:
        logger.error(f"Error listing cases: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to list cases"
        )


@router.post("", response_model=Case)
async def create_case(
    request: CaseCreateRequest,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
) -> Case:
    """
    Create a new case.
    
    Args:
        request: Case creation request.
        current_user: Current authenticated user.
        db: Database session.
        
    Returns:
        Case: Created case.
        
    Raises:
        HTTPException: If creation fails.
    """
    try:
        # Use current user's law firm ID
        law_firm_id = current_user.law_firm_id
        
        case = await CaseService.create_case(
            db=db,
            name=request.name,
            law_firm_id=law_firm_id,
            created_by=current_user.id,
            description=None,  # Description not part of CaseCreateRequest
            metadata=request.metadata
        )
        
        # Create Qdrant collections asynchronously
        try:
            vector_store = QdrantVectorStore()
            collections_created = await create_case_collections_with_events(
                vector_store,
                case.collection_name,
                case.id
            )
            
            if not collections_created:
                logger.warning(
                    f"Some collections failed to create for case {case.id}"
                )
                
        except Exception as e:
            # Log error but don't fail case creation
            logger.error(
                f"Failed to create Qdrant collections for case {case.id}: {e}"
            )
            # Emit error event
            try:
                from src.websocket.socket_server import emit_case_event
                await emit_case_event("collection_error", case.id, {
                    "error": str(e),
                    "message": "Collections will be created when first document is uploaded"
                })
            except:
                pass  # Don't fail on WebSocket error
        
        # Parse metadata for response
        metadata = {}
        if case.case_metadata:
            try:
                import json
                metadata = json.loads(case.case_metadata)
            except:
                pass
        
        return Case(
            id=case.id,
            name=case.name,
            collection_name=case.collection_name,
            description=case.description,
            law_firm_id=case.law_firm_id,
            status=case.status,
            created_by=case.created_by,
            metadata=metadata,
            created_at=case.created_at,
            updated_at=case.updated_at
        )
        
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e)
        )
    except Exception as e:
        logger.error(f"Error creating case: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to create case"
        )


@router.get("/{case_id}", response_model=Case)
async def get_case(
    case_context: CaseContext = Depends(get_case_context_dependency("read")),
    db: AsyncSession = Depends(get_db)
) -> Case:
    """
    Get case details.
    
    Args:
        case_context: Validated case context.
        db: Database session.
        
    Returns:
        Case: Case details.
    """
    case = await CaseService.get_case_by_id(db, case_context.case_id)
    if not case:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Case not found"
        )
    
    # Parse metadata
    metadata = {}
    if case.case_metadata:
        try:
            import json
            metadata = json.loads(case.case_metadata)
        except:
            pass
    
    return Case(
        id=case.id,
        name=case.name,
        collection_name=case.collection_name,
        description=case.description,
        law_firm_id=case.law_firm_id,
        status=case.status,
        created_by=case.created_by,
        metadata=metadata,
        created_at=case.created_at,
        updated_at=case.updated_at
    )


@router.put("/{case_id}", response_model=Case)
async def update_case(
    request: CaseUpdateRequest,
    case_context: CaseContext = Depends(get_case_context_dependency("admin")),
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
) -> Case:
    """
    Update case status.
    
    Args:
        request: Case update request.
        case_context: Validated case context (admin required).
        current_user: Current authenticated user.
        db: Database session.
        
    Returns:
        Case: Updated case.
        
    Raises:
        HTTPException: If update fails.
    """
    try:
        # Convert string status to enum
        status_enum = CaseStatus(request.status)
        
        case = await CaseService.update_case_status(
            db=db,
            case_id=case_context.case_id,
            status=status_enum,
            user_id=current_user.id
        )
        
        if not case:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Case not found"
            )
        
        # Parse metadata
        metadata = {}
        if case.case_metadata:
            try:
                import json
                metadata = json.loads(case.case_metadata)
            except:
                pass
        
        return Case(
            id=case.id,
            name=case.name,
            collection_name=case.collection_name,
            description=case.description,
            law_firm_id=case.law_firm_id,
            status=case.status,
            created_by=case.created_by,
            metadata=metadata,
            created_at=case.created_at,
            updated_at=case.updated_at
        )
        
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e)
        )
    except PermissionError as e:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail=str(e)
        )
    except Exception as e:
        logger.error(f"Error updating case: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to update case"
        )


@router.post("/{case_id}/permissions")
async def grant_case_permission(
    request: PermissionGrantRequest,
    case_context: CaseContext = Depends(get_case_context_dependency("admin")),
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
) -> Dict[str, str]:
    """
    Grant permission to a user for a case.
    
    Args:
        request: Permission grant request.
        case_context: Validated case context (admin required).
        current_user: Current authenticated user.
        db: Database session.
        
    Returns:
        Dict[str, str]: Success message.
        
    Raises:
        HTTPException: If grant fails.
    """
    try:
        # Parse expiration if provided
        expires_at = None
        if request.expires_at:
            expires_at = datetime.fromisoformat(request.expires_at.replace("Z", "+00:00"))
        
        success = await CaseService.grant_case_permission(
            db=db,
            case_id=case_context.case_id,
            user_id=request.user_id,
            permission_level=request.permission_level,
            granting_user_id=current_user.id,
            expires_at=expires_at
        )
        
        if not success:
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="Failed to grant permission"
            )
        
        return {"message": f"Permission granted successfully to user {request.user_id}"}
        
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e)
        )
    except PermissionError as e:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail=str(e)
        )
    except Exception as e:
        logger.error(f"Error granting permission: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to grant permission"
        )


@router.get("/{case_id}/context", response_model=CaseContext)
async def get_case_context(
    case_context: CaseContext = Depends(get_case_context_dependency("read"))
) -> CaseContext:
    """
    Get case context with user permissions.
    
    This endpoint is used by the frontend to validate case access
    and get permission information.
    
    Args:
        case_context: Validated case context.
        
    Returns:
        CaseContext: Case context with permissions.
    """
    return case_context