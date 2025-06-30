"""
Unified Document Models for Legal Document Management
Combines document registry (deduplication) and source documents (discovery) into one system
"""

from enum import Enum
from datetime import datetime
from typing import List, Optional, Dict, Any, Tuple
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
    
    # Discovery documents (requests)
    DEPOSITION = "deposition"
    INTERROGATORY = "interrogatory"
    REQUEST_FOR_ADMISSION = "request_for_admission"
    REQUEST_FOR_PRODUCTION = "request_for_production"
    
    # Discovery responses
    INTERROGATORY_RESPONSE = "interrogatory_response"
    ADMISSION_RESPONSE = "admission_response"
    
    # Driver/Employee Documentation
    DRIVER_QUALIFICATION_FILE = "driver_qualification_file"
    EMPLOYMENT_APPLICATION = "employment_application"
    DRIVER_INVESTIGATION_REPORT = "driver_investigation_report"
    DRIVING_RECORD_INQUIRY = "driving_record_inquiry"
    MEDICAL_EXAMINER_CERTIFICATE = "medical_examiner_certificate"
    DRIVER_TRAINING_CERTIFICATE = "driver_training_certificate"
    DRUG_TEST_RESULT = "drug_test_result"
    BACKGROUND_CHECK_REPORT = "background_check_report"
    PRE_EMPLOYMENT_SCREENING = "pre_employment_screening"
    
    # Vehicle/Equipment Records
    VEHICLE_TITLE = "vehicle_title"
    VEHICLE_REGISTRATION = "vehicle_registration"
    MAINTENANCE_RECORD = "maintenance_record"
    INSPECTION_REPORT = "inspection_report"
    REPAIR_RECORD = "repair_record"
    ECM_DATA = "ecm_data"  # Engine Control Module
    EDR_DATA = "edr_data"  # Event Data Recorder
    EOBR_DATA = "eobr_data"  # Electronic On-Board Recorder
    DVIR = "dvir"  # Driver Vehicle Inspection Report
    
    # Hours of Service Documentation
    HOS_LOG = "hos_log"  # Hours of Service Log
    TIME_SHEET = "time_sheet"
    TRIP_REPORT = "trip_report"
    BILL_OF_LADING = "bill_of_lading"
    FREIGHT_BILL = "freight_bill"
    FUEL_RECEIPT = "fuel_receipt"
    TOLL_RECEIPT = "toll_receipt"
    WEIGHT_TICKET = "weight_ticket"
    DISPATCH_RECORD = "dispatch_record"
    
    # Communication Records
    EMAIL_CORRESPONDENCE = "email_correspondence"
    SATELLITE_COMMUNICATION = "satellite_communication"
    CELLULAR_COMMUNICATION = "cellular_communication"
    DRIVER_CALL_IN_REPORT = "driver_call_in_report"
    TEXT_MESSAGE = "text_message"
    ONBOARD_SYSTEM_MESSAGE = "onboard_system_message"
    
    # Insurance/Financial Documents
    INSURANCE_DECLARATION = "insurance_declaration"
    RESERVATION_OF_RIGHTS_LETTER = "reservation_of_rights_letter"
    COMPENSATION_RECORD = "compensation_record"
    PAYROLL_RECORD = "payroll_record"
    LEASE_AGREEMENT = "lease_agreement"
    
    # Safety/Compliance Records
    SAFETY_VIOLATION_REPORT = "safety_violation_report"
    DISCIPLINARY_ACTION = "disciplinary_action"
    ACCIDENT_REGISTER = "accident_register"
    CSA_INTERVENTION_DOCUMENT = "csa_intervention_document"
    OUT_OF_SERVICE_REPORT = "out_of_service_report"
    CITATION = "citation"
    WARNING = "warning"
    COMPLAINT_RECORD = "complaint_record"
    
    # Company Documentation
    COMPANY_POLICY = "company_policy"
    EMPLOYEE_HANDBOOK = "employee_handbook"
    SAFETY_MANUAL = "safety_manual"
    TRAINING_MATERIAL = "training_material"
    COMPANY_NEWSLETTER = "company_newsletter"
    ORGANIZATIONAL_CHART = "organizational_chart"
    
    # Accident-Specific Documents
    ACCIDENT_INVESTIGATION_REPORT = "accident_investigation_report"
    ACCIDENT_REVIEW_BOARD_REPORT = "accident_review_board_report"
    PREVENTABILITY_DETERMINATION = "preventability_determination"
    DAMAGE_ESTIMATE = "damage_estimate"
    REPAIR_INVOICE = "repair_invoice"
    WITNESS_STATEMENT_TRANSCRIPT = "witness_statement_transcript"
    
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


class DiscoveryMetadata(BaseModel):
    """Metadata specific to discovery production"""
    production_batch: str  # e.g., "Production 1", "Supplemental Production 2"
    production_date: datetime
    bates_start: Optional[str] = None  # e.g., "DEF00001"
    bates_end: Optional[str] = None  # e.g., "DEF00100"
    responsive_to_requests: List[str] = Field(default_factory=list)  # e.g., ["RFP 1", "RFP 5-7"]
    producing_party: str  # e.g., "Defendant ABC Corp"
    custodian: Optional[str] = None  # Person/entity who had custody
    confidentiality_designation: Optional[str] = None  # e.g., "Confidential", "Highly Confidential"


class DiscoveryProcessingRequest(BaseModel):
    """Request to process discovery materials"""
    folder_id: str = Field(..., description="Box folder ID containing discovery materials")
    case_name: str = Field(..., description="Case name for isolation")
    production_batch: str = Field(..., description="Production batch identifier")
    producing_party: str = Field(..., description="Party producing the documents")
    production_date: Optional[datetime] = Field(default_factory=datetime.now)
    responsive_to_requests: List[str] = Field(default_factory=list)
    confidentiality_designation: Optional[str] = None
    override_fact_extraction: bool = Field(True, description="Force fact extraction for all documents")
    max_documents: Optional[int] = None


class LargeDocumentProcessingStrategy(str, Enum):
    """Strategy for processing documents larger than single window"""
    SINGLE_PASS = "single_pass"  # <= 50 pages
    CHUNKED = "chunked"  # > 50 pages, sequential chunks
    SUMMARY_DETAIL = "summary_detail"  # Summary + specific sections


class DocumentBoundary(BaseModel):
    """Represents a detected document boundary within a larger PDF"""
    start_page: int  # 0-indexed
    end_page: int  # 0-indexed, inclusive
    confidence: float = Field(ge=0.0, le=1.0)
    document_type_hint: Optional[DocumentType] = None
    boundary_indicators: List[str] = Field(default_factory=list)
    is_continuation: bool = False  # True if document continues from previous
    detection_window: Optional[Tuple[int, int]] = None  # Window where boundary was detected


class DiscoverySegment(BaseModel):
    """Represents a single document within a discovery production"""
    segment_id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    start_page: int  # First page of segment in original PDF
    end_page: int  # Last page of segment in original PDF
    document_type: DocumentType
    title: Optional[str] = None
    confidence_score: float = Field(ge=0.0, le=1.0)
    bates_range: Optional[Dict[str, str]] = None  # {"start": "DEF00001", "end": "DEF00010"}
    boundary_indicators: List[str] = Field(default_factory=list)
    
    # For multi-part documents
    is_complete: bool = True
    continuation_id: Optional[str] = None  # Links multi-part documents
    total_parts: int = 1
    part_number: int = 1
    
    # Processing metadata
    processing_strategy: LargeDocumentProcessingStrategy = LargeDocumentProcessingStrategy.SINGLE_PASS
    page_count: int = Field(default=0)
    extraction_successful: bool = False
    
    @property
    def needs_large_document_handling(self) -> bool:
        """Check if document needs special handling due to size"""
        return self.page_count > 50
    
    def model_post_init(self, __context) -> None:
        """Calculate page count after initialization"""
        self.page_count = self.end_page - self.start_page + 1


class DiscoveryProductionResult(BaseModel):
    """Result of processing an entire discovery production"""
    production_id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    case_name: str
    production_batch: str
    source_pdf_path: str
    total_pages: int
    
    # Segmentation results
    segments_found: List[DiscoverySegment] = Field(default_factory=list)
    processing_windows: int = 0  # Number of windows processed
    low_confidence_boundaries: List[DocumentBoundary] = Field(default_factory=list)
    
    # Processing metadata
    processing_started: datetime = Field(default_factory=datetime.now)
    processing_completed: Optional[datetime] = None
    processing_duration_seconds: Optional[float] = None
    
    # Quality metrics
    average_confidence: float = 0.0
    documents_requiring_review: int = 0
    pages_processed: int = 0
    pages_skipped: int = 0
    
    # Errors and warnings
    errors: List[str] = Field(default_factory=list)
    warnings: List[str] = Field(default_factory=list)
    
    def calculate_metrics(self) -> None:
        """Calculate quality metrics from segments"""
        if self.segments_found:
            confidences = [s.confidence_score for s in self.segments_found]
            self.average_confidence = sum(confidences) / len(confidences)
            self.documents_requiring_review = sum(
                1 for s in self.segments_found if s.confidence_score < 0.7
            )
        
        self.pages_processed = sum(s.page_count for s in self.segments_found)
        self.pages_skipped = self.total_pages - self.pages_processed
        
        if self.processing_completed and self.processing_started:
            self.processing_duration_seconds = (
                self.processing_completed - self.processing_started
            ).total_seconds()


class DocumentSegmentationRequest(BaseModel):
    """Request to segment a multi-document PDF"""
    pdf_path: str = Field(..., description="Path to PDF file")
    case_name: str
    window_size: int = Field(25, description="Pages per analysis window")
    window_overlap: int = Field(5, description="Overlap between windows")
    confidence_threshold: float = Field(0.7, description="Minimum confidence for boundaries")
    boundary_detection_model: str = Field("gpt-4.1-mini-2025-04-14")