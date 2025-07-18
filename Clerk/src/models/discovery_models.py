"""
Discovery processing models for real-time fact extraction and review.
Extends existing fact models with source tracking and edit capabilities.
"""

from typing import List, Optional, Dict, Any
from datetime import datetime
from pydantic import BaseModel, Field
import uuid

from src.models.fact_models import CaseFact, FactCategory
from src.models.unified_document_models import DocumentType


class FactSource(BaseModel):
    """Source location for an extracted fact"""

    doc_id: str = Field(..., description="Document ID in the system")
    doc_title: str = Field(..., description="Human-readable document title")
    page: int = Field(..., description="Page number (1-indexed)")
    bbox: List[float] = Field(
        ..., description="Bounding box coordinates [x1, y1, x2, y2]"
    )
    text_snippet: str = Field(..., description="Surrounding text context")
    bates_number: Optional[str] = Field(None, description="Bates stamp if available")


class FactEditHistory(BaseModel):
    """History entry for fact edits"""

    timestamp: datetime = Field(default_factory=datetime.utcnow)
    user_id: str
    old_content: str
    new_content: str
    edit_reason: Optional[str] = None


class ExtractedFactWithSource(CaseFact):
    """Enhanced fact model with source tracking and edit history"""

    source: FactSource
    is_edited: bool = Field(default=False)
    edit_history: List[FactEditHistory] = Field(default_factory=list)
    is_deleted: bool = Field(default=False)
    deleted_at: Optional[datetime] = None
    deleted_by: Optional[str] = None

    # Review metadata
    reviewed: bool = Field(default=False)
    reviewed_by: Optional[str] = None
    reviewed_at: Optional[datetime] = None
    review_notes: Optional[str] = None


class DiscoveryProcessingRequest(BaseModel):
    """Request model for discovery processing - case context from headers"""

    # Note: case_id and case_name extracted from request context via middleware
    discovery_files: List[str] = Field(
        default_factory=list, description="Files to process"
    )
    box_folder_id: Optional[str] = Field(None, description="Box folder ID if using Box")
    rfp_file: Optional[str] = Field(None, description="Request for Production document")

    # Processing options
    enable_ocr: bool = Field(
        default=True, description="Enable OCR for scanned documents"
    )
    confidence_threshold: float = Field(default=0.7, ge=0.0, le=1.0)
    max_facts_per_document: Optional[int] = Field(
        None, description="Limit facts per document"
    )


class DiscoveryProcessingStatus(BaseModel):
    """Real-time status updates for discovery processing"""

    processing_id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    case_id: str
    case_name: str
    total_documents: int
    processed_documents: int = 0
    total_facts: int = 0
    current_document: Optional[str] = None
    current_document_id: Optional[str] = None
    status: str = Field(
        default="initializing"
    )  # initializing, processing, completed, error
    started_at: datetime = Field(default_factory=datetime.utcnow)
    completed_at: Optional[datetime] = None
    error_message: Optional[str] = None

    # Document tracking
    documents: Dict[str, Dict[str, Any]] = Field(default_factory=dict)
    # Format: {doc_id: {"title": str, "pages": int, "facts": int, "status": str}}
    
    # RFP and Defense Response file storage (temporary)
    rfp_content: Optional[bytes] = Field(None, exclude=True)  # Exclude from API responses
    rfp_filename: Optional[str] = None
    rfp_document_id: Optional[str] = None
    defense_content: Optional[bytes] = Field(None, exclude=True)  # Exclude from API responses
    defense_filename: Optional[str] = None
    defense_response_id: Optional[str] = None
    
    # Deficiency report storage (temporary)
    deficiency_report: Optional[Any] = Field(None, exclude=True)  # Exclude from API responses


class FactDeleteRequest(BaseModel):
    """Request to delete a fact"""

    fact_id: str
    delete_reason: Optional[str] = None


class DocumentProcessingEvent(BaseModel):
    """WebSocket event for document processing updates"""

    event_type: str  # document_found, fact_extracted, processing_complete, error
    processing_id: str
    case_id: str
    timestamp: datetime = Field(default_factory=datetime.utcnow)
    data: Dict[str, Any]


class DiscoveryDocument(BaseModel):
    """Represents a document found during discovery processing"""

    doc_id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    processing_id: str
    case_id: str
    title: str
    document_type: DocumentType
    page_count: int
    file_path: str

    # Processing state
    status: str = Field(default="pending")  # pending, processing, completed, error
    facts_extracted: int = Field(default=0)
    processing_started: Optional[datetime] = None
    processing_completed: Optional[datetime] = None

    # Boundaries (for split documents)
    start_page: int
    end_page: int
    is_continuation: bool = Field(default=False)
    parent_doc_id: Optional[str] = None


class FactReviewStatus(BaseModel):
    """Track review status of facts by document"""

    case_id: str
    document_id: str
    total_facts: int
    reviewed_facts: int = 0
    edited_facts: int = 0
    deleted_facts: int = 0
    reviewer_id: Optional[str] = None
    review_started: Optional[datetime] = None
    review_completed: Optional[datetime] = None

    @property
    def is_complete(self) -> bool:
        """Check if all facts have been reviewed"""
        return self.reviewed_facts >= self.total_facts

    @property
    def review_percentage(self) -> float:
        """Calculate review completion percentage"""
        if self.total_facts == 0:
            return 100.0
        return (self.reviewed_facts / self.total_facts) * 100


class FactSearchFilter(BaseModel):
    """Filters for searching facts within a case"""

    case_id: str  # From case context
    query: Optional[str] = None
    categories: List[FactCategory] = Field(default_factory=list)
    document_ids: List[str] = Field(default_factory=list)
    date_range: Optional[Dict[str, datetime]] = None
    confidence_min: float = Field(default=0.0, ge=0.0, le=1.0)
    include_deleted: bool = Field(default=False)
    include_unreviewed: bool = Field(default=True)
    limit: int = Field(default=100, ge=1, le=500)
    offset: int = Field(default=0, ge=0)


class FactBulkUpdateRequest(BaseModel):
    """Request to update multiple facts at once"""

    fact_ids: List[str]
    action: str  # "mark_reviewed", "delete", "change_category"
    category: Optional[FactCategory] = None
    reason: Optional[str] = None


class DiscoveryProcessingResult(BaseModel):
    """Final result of discovery processing"""

    processing_id: str
    case_id: str
    case_name: str

    # Summary statistics
    total_documents: int
    total_pages: int
    total_facts: int
    processing_duration: float  # seconds

    # Quality metrics
    average_confidence: float
    facts_below_threshold: int
    documents_with_errors: List[str] = Field(default_factory=list)

    # Detailed results
    documents: List[DiscoveryDocument]
    processing_errors: List[Dict[str, Any]] = Field(default_factory=list)

    # Timestamps
    started_at: datetime
    completed_at: datetime


class DiscoveryProcessingResponse(BaseModel):
    """Response from discovery processing endpoint"""

    processing_id: str
    status: str
    message: str
    websocket_url: Optional[str] = None
    production_batch: Optional[str] = None
    rfp_file_id: Optional[str] = None
    defense_response_file_id: Optional[str] = None


class FactSearchRequest(BaseModel):
    """Request model for searching facts"""

    case_name: str
    query: Optional[str] = None
    category: Optional[FactCategory] = None
    confidence_min: Optional[float] = Field(None, ge=0.0, le=1.0)
    confidence_max: Optional[float] = Field(None, ge=0.0, le=1.0)
    document_ids: Optional[List[str]] = None
    review_status: Optional[str] = None  # "reviewed", "unreviewed", "all"
    is_edited: Optional[bool] = None
    limit: Optional[int] = Field(100, ge=1, le=500)
    offset: Optional[int] = Field(0, ge=0)


class FactSearchResponse(BaseModel):
    """Response from fact search"""

    facts: List[ExtractedFactWithSource]
    total: int
    limit: int
    offset: int


class FactUpdateRequest(BaseModel):
    """Request to update a fact"""

    content: str
    category: Optional[FactCategory] = None
    reason: Optional[str] = None


class FactBulkOperation(BaseModel):
    """Bulk operation on facts"""

    fact_ids: List[str]
    operation: str  # "mark_reviewed", "delete", "change_category"
    category: Optional[FactCategory] = None
