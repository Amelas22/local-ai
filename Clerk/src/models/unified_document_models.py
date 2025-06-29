"""
Unified Document Models for Legal Document Management
Combines document registry (deduplication) and source documents (discovery) into one system
"""

from enum import Enum
from datetime import datetime
from typing import List, Optional, Dict, Any
from pydantic import BaseModel, Field
import uuid


class DocumentType(str, Enum):
    """Types of legal source documents"""
    # Legal filings
    MOTION = "motion"
    COMPLAINT = "complaint"
    ANSWER = "answer"
    MEMORANDUM = "memorandum"
    BRIEF = "brief"
    ORDER = "order"
    
    # Discovery documents
    DEPOSITION = "deposition"
    INTERROGATORY = "interrogatory"
    REQUEST_FOR_ADMISSION = "request_for_admission"
    REQUEST_FOR_PRODUCTION = "request_for_production"
    
    # Evidence documents
    MEDICAL_RECORD = "medical_record"
    POLICE_REPORT = "police_report"
    EXPERT_REPORT = "expert_report"
    PHOTOGRAPH = "photograph"
    VIDEO = "video"
    
    # Business/Financial documents
    INVOICE = "invoice"
    CONTRACT = "contract"
    FINANCIAL_RECORD = "financial_record"
    EMPLOYMENT_RECORD = "employment_record"
    INSURANCE_POLICY = "insurance_policy"
    
    # Other evidence
    CORRESPONDENCE = "correspondence"
    INCIDENT_REPORT = "incident_report"
    WITNESS_STATEMENT = "witness_statement"
    AFFIDAVIT = "affidavit"
    OTHER = "other"


class DocumentRelevance(str, Enum):
    """Relevance categories for source documents"""
    LIABILITY = "liability"
    DAMAGES = "damages"
    CAUSATION = "causation"
    CREDIBILITY = "credibility"
    PROCEDURE = "procedure"
    BACKGROUND = "background"
    IMPEACHMENT = "impeachment"
    AUTHENTICATION = "authentication"


class DocumentStatus(str, Enum):
    """Document processing status"""
    PROCESSING = "processing"
    ACTIVE = "active"
    REPLACED = "replaced"  # When a newer version exists
    DELETED = "deleted"


class DuplicateLocation(BaseModel):
    """Tracks where duplicates of a document exist"""
    case_name: str
    file_path: str
    folder_path: str
    found_at: datetime
    

class UnifiedDocument(BaseModel):
    """
    Unified model for document tracking, deduplication, and discovery
    Combines the best of DocumentRecord and SourceDocument
    """
    # Core identification
    id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    case_name: str
    document_hash: str  # SHA-256 hash for deduplication
    
    # File information
    file_name: str
    file_path: str  # Path in Box
    file_size: int
    mime_type: Optional[str] = None
    
    # Document classification
    document_type: DocumentType
    title: str  # Human-readable title
    description: str  # Brief description/summary
    
    # Temporal information
    first_seen_at: datetime = Field(default_factory=datetime.now)
    last_modified: datetime
    document_date: Optional[datetime] = None  # Date of the document itself
    
    # Deduplication tracking
    is_duplicate: bool = False
    original_document_id: Optional[str] = None  # If this is a duplicate, points to original
    duplicate_locations: List[DuplicateLocation] = Field(default_factory=list)
    duplicate_count: int = 0
    
    # Content analysis
    key_facts: List[str] = Field(default_factory=list)
    relevance_tags: List[DocumentRelevance] = Field(default_factory=list)
    mentioned_parties: List[str] = Field(default_factory=list)
    mentioned_dates: List[str] = Field(default_factory=list)
    
    # Key people
    author: Optional[str] = None
    recipient: Optional[str] = None
    witness: Optional[str] = None  # For depositions
    
    # Page information
    total_pages: int
    key_pages: List[int] = Field(default_factory=list)
    
    # Text and search
    summary: str  # AI-generated summary
    search_text: str  # Full searchable text
    
    # Vector embedding reference
    embedding_id: Optional[str] = None
    embedding_model: Optional[str] = None
    
    # External references
    box_file_id: Optional[str] = None
    box_shared_link: Optional[str] = None
    
    # Metadata
    folder_path: List[str] = Field(default_factory=list)
    subfolder: str = "root"
    metadata: Dict[str, Any] = Field(default_factory=dict)
    
    # Status and versioning
    status: DocumentStatus = DocumentStatus.ACTIVE
    version: int = 1
    replaced_by: Optional[str] = None  # ID of newer version
    
    # Quality indicators
    extraction_confidence: float = 1.0  # How confident we are in text extraction
    classification_confidence: float = 1.0  # How confident we are in document type
    verified: bool = False  # Has a human verified this classification
    
    # Usage tracking
    times_accessed: int = 0
    last_accessed: Optional[datetime] = None
    used_in_motions: List[str] = Field(default_factory=list)  # Motion IDs where used
    
    def to_storage_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for Qdrant storage"""
        return {
            "id": self.id,
            "case_name": self.case_name,
            "document_hash": self.document_hash,
            "file_name": self.file_name,
            "file_path": self.file_path,
            "file_size": self.file_size,
            "mime_type": self.mime_type,
            "document_type": self.document_type.value,
            "title": self.title,
            "description": self.description,
            "first_seen_at": self.first_seen_at.isoformat(),
            "last_modified": self.last_modified.isoformat(),
            "document_date": self.document_date.isoformat() if self.document_date else None,
            "is_duplicate": self.is_duplicate,
            "original_document_id": self.original_document_id,
            "duplicate_count": self.duplicate_count,
            "key_facts": self.key_facts,
            "relevance_tags": [tag.value for tag in self.relevance_tags],
            "mentioned_parties": self.mentioned_parties,
            "mentioned_dates": self.mentioned_dates,
            "author": self.author,
            "recipient": self.recipient,
            "witness": self.witness,
            "total_pages": self.total_pages,
            "key_pages": self.key_pages,
            "summary": self.summary,
            "embedding_id": self.embedding_id,
            "embedding_model": self.embedding_model,
            "box_file_id": self.box_file_id,
            "box_shared_link": self.box_shared_link,
            "folder_path": "/".join(self.folder_path),
            "subfolder": self.subfolder,
            "status": self.status.value,
            "version": self.version,
            "replaced_by": self.replaced_by,
            "extraction_confidence": self.extraction_confidence,
            "classification_confidence": self.classification_confidence,
            "verified": self.verified,
            "times_accessed": self.times_accessed,
            "last_accessed": self.last_accessed.isoformat() if self.last_accessed else None,
            "used_in_motions": self.used_in_motions
        }
    
    @classmethod
    def from_storage_dict(cls, data: Dict[str, Any]) -> "UnifiedDocument":
        """Create from Qdrant storage dictionary"""
        # Convert ISO strings back to datetime
        data["first_seen_at"] = datetime.fromisoformat(data["first_seen_at"])
        data["last_modified"] = datetime.fromisoformat(data["last_modified"])
        if data.get("document_date"):
            data["document_date"] = datetime.fromisoformat(data["document_date"])
        if data.get("last_accessed"):
            data["last_accessed"] = datetime.fromisoformat(data["last_accessed"])
        
        # Convert enums
        data["document_type"] = DocumentType(data["document_type"])
        data["relevance_tags"] = [DocumentRelevance(tag) for tag in data.get("relevance_tags", [])]
        data["status"] = DocumentStatus(data.get("status", "active"))
        
        # Convert folder path
        if isinstance(data.get("folder_path"), str):
            data["folder_path"] = data["folder_path"].split("/") if data["folder_path"] else []
        
        # Note: duplicate_locations would need separate handling
        data.pop("duplicate_locations", None)
        
        return cls(**data)


class DocumentProcessingRequest(BaseModel):
    """Request to process a new document"""
    case_name: str
    file_path: str
    file_content: bytes
    metadata: Dict[str, Any] = Field(default_factory=dict)


class DocumentProcessingResult(BaseModel):
    """Result of processing a document"""
    document_id: str
    is_duplicate: bool
    original_document_id: Optional[str] = None
    document_type: DocumentType
    title: str
    summary: str
    chunks_created: int
    processing_time: float
    confidence_scores: Dict[str, float] = Field(default_factory=dict)
    warnings: List[str] = Field(default_factory=list)


class DocumentSearchRequest(BaseModel):
    """Request to search for documents"""
    case_name: str
    query: str
    document_types: Optional[List[DocumentType]] = None
    relevance_tags: Optional[List[DocumentRelevance]] = None
    date_range: Optional[Dict[str, datetime]] = None
    limit: int = 20
    include_duplicates: bool = False


class DocumentSearchResult(BaseModel):
    """Result from document search"""
    document: UnifiedDocument
    score: float
    matched_chunks: List[Dict[str, Any]] = Field(default_factory=list)
    relevance_explanation: Optional[str] = None