"""
Source Document Models for Legal Evidence Discovery
Tracks original source documents that can be used as exhibits in motions
"""

from enum import Enum
from datetime import datetime
from typing import List, Optional, Dict, Any
from pydantic import BaseModel, Field


class DocumentType(str, Enum):
    """Types of legal source documents"""
    DEPOSITION = "deposition"
    MEDICAL_RECORD = "medical_record"
    POLICE_REPORT = "police_report"
    EXPERT_REPORT = "expert_report"
    PHOTOGRAPH = "photograph"
    VIDEO = "video"
    INVOICE = "invoice"
    CONTRACT = "contract"
    CORRESPONDENCE = "correspondence"
    INTERROGATORY = "interrogatory"
    REQUEST_FOR_ADMISSION = "request_for_admission"
    REQUEST_FOR_PRODUCTION = "request_for_production"
    FINANCIAL_RECORD = "financial_record"
    EMPLOYMENT_RECORD = "employment_record"
    INSURANCE_POLICY = "insurance_policy"
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


class SourceDocument(BaseModel):
    """Represents a source document that could become an exhibit"""
    id: str
    case_name: str
    document_type: DocumentType
    title: str
    description: str
    
    # Source information
    source_path: str  # Original file path in Box
    upload_date: datetime
    document_date: Optional[datetime] = None  # Date of the document itself
    
    # Key metadata
    author: Optional[str] = None  # Who created this document
    recipient: Optional[str] = None  # Who received it (for correspondence)
    witness: Optional[str] = None  # For depositions/statements
    
    # Content analysis
    key_facts: List[str] = Field(default_factory=list)
    relevance_tags: List[DocumentRelevance] = Field(default_factory=list)
    mentioned_parties: List[str] = Field(default_factory=list)
    mentioned_dates: List[str] = Field(default_factory=list)
    
    # Page-specific information
    total_pages: Optional[int] = None
    key_pages: List[int] = Field(default_factory=list)  # Most relevant pages
    
    # Search and retrieval
    summary: Optional[str] = None  # AI-generated summary
    search_text: str  # Full searchable text
    embedding_id: Optional[str] = None  # Reference to vector embedding
    
    # Quality and verification
    ocr_quality: Optional[float] = None  # 0-1 score for OCR quality
    verified: bool = False
    verification_notes: Optional[str] = None


class EvidenceSearchQuery(BaseModel):
    """Query for searching source documents for evidence"""
    case_name: str
    query_text: str
    document_types: Optional[List[DocumentType]] = None
    relevance_tags: Optional[List[DocumentRelevance]] = None
    date_range: Optional[Dict[str, datetime]] = None
    parties: Optional[List[str]] = None
    limit: int = Field(default=20, ge=1, le=100)


class EvidenceSearchResult(BaseModel):
    """Result from evidence search"""
    document: SourceDocument
    relevance_score: float
    matching_excerpts: List[Dict[str, Any]]  # Page number and text excerpts
    suggested_use: Optional[str] = None  # AI suggestion for how to use this


class DocumentClassificationRequest(BaseModel):
    """Request to classify a document"""
    case_name: str
    document_path: str
    document_content: str
    document_metadata: Optional[Dict[str, Any]] = None


class DocumentClassificationResult(BaseModel):
    """Result of document classification"""
    document_type: DocumentType
    confidence: float
    detected_parties: List[str]
    detected_dates: List[str]
    key_topics: List[str]
    suggested_relevance: List[DocumentRelevance]
    summary: str