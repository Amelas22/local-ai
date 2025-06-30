"""
Normalized Database Schema for Legal Document Management System

This module provides a normalized database schema that separates the complex UnifiedDocument
model into multiple related tables for better performance, maintainability, and query optimization.

Key Design Principles:
1. Separation of immutable vs mutable data
2. Hierarchical case management (Matter → Case → Document)
3. Support for document-to-document relationships
4. Optimized chunk-document linking
5. Enhanced query performance through strategic indexing
"""

from enum import Enum
from datetime import datetime
from typing import List, Optional, Dict, Any, Set
from pydantic import BaseModel, Field
import uuid

# Import existing enums from unified models
from .unified_document_models import (
    DocumentType, 
    DocumentRelevance, 
    DocumentStatus,
    LargeDocumentProcessingStrategy
)


class RelationshipType(str, Enum):
    """Types of relationships between documents"""
    EXHIBIT = "exhibit"  # Document A is an exhibit to Document B
    AMENDMENT = "amendment"  # Document A amends Document B
    SUPERSEDES = "supersedes"  # Document A supersedes Document B
    REFERENCES = "references"  # Document A references Document B
    RESPONDS_TO = "responds_to"  # Document A responds to Document B
    CONTINUATION = "continuation"  # Document A continues Document B
    ATTACHMENT = "attachment"  # Document A is attached to Document B
    RELATED = "related"  # Generic relationship
    CITES = "cites"  # Document A cites Document B as authority


class AccessLevel(str, Enum):
    """Access levels for documents and cases"""
    PUBLIC = "public"
    INTERNAL = "internal"
    CONFIDENTIAL = "confidential"
    PRIVILEGED = "privileged"
    HIGHLY_CONFIDENTIAL = "highly_confidential"


class MatterType(str, Enum):
    """Types of legal matters"""
    LITIGATION = "litigation"
    TRANSACTIONAL = "transactional"
    REGULATORY = "regulatory"
    COMPLIANCE = "compliance"
    CORPORATE = "corporate"
    EMPLOYMENT = "employment"
    INTELLECTUAL_PROPERTY = "intellectual_property"
    REAL_ESTATE = "real_estate"


class CaseStatus(str, Enum):
    """Status of cases"""
    ACTIVE = "active"
    CLOSED = "closed"
    SUSPENDED = "suspended"
    SETTLED = "settled"
    DISMISSED = "dismissed"
    APPEALED = "appealed"


# Core normalized tables

class Matter(BaseModel):
    """Top-level matter containing multiple related cases"""
    id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    matter_number: str  # Firm's matter numbering system
    client_name: str
    matter_name: str
    matter_type: MatterType
    description: Optional[str] = None
    
    # Key personnel
    partner_in_charge: Optional[str] = None
    associate_attorneys: List[str] = Field(default_factory=list)
    
    # Dates
    opened_date: datetime
    closed_date: Optional[datetime] = None
    
    # Access control
    access_level: AccessLevel = AccessLevel.INTERNAL
    authorized_users: Set[str] = Field(default_factory=set)
    
    # Metadata
    practice_area: Optional[str] = None
    industry: Optional[str] = None
    created_at: datetime = Field(default_factory=datetime.now)
    updated_at: datetime = Field(default_factory=datetime.now)


class Case(BaseModel):
    """Individual case within a matter"""
    id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    matter_id: str  # Foreign key to Matter
    case_number: str  # Court case number or internal identifier
    case_name: str  # Traditional case name format (e.g., "Smith v. Jones")
    
    # Court information
    court_name: Optional[str] = None
    judge_name: Optional[str] = None
    case_type: Optional[str] = None  # Civil, Criminal, etc.
    
    # Parties
    plaintiffs: List[str] = Field(default_factory=list)
    defendants: List[str] = Field(default_factory=list)
    third_parties: List[str] = Field(default_factory=list)
    
    # Status and dates
    status: CaseStatus = CaseStatus.ACTIVE
    filed_date: Optional[datetime] = None
    statute_limitations: Optional[datetime] = None
    trial_date: Optional[datetime] = None
    
    # Inheritance from matter
    inherited_access_level: Optional[AccessLevel] = None
    case_specific_access: AccessLevel = AccessLevel.INTERNAL
    
    # Metadata
    description: Optional[str] = None
    created_at: datetime = Field(default_factory=datetime.now)
    updated_at: datetime = Field(default_factory=datetime.now)
    
    @property
    def effective_access_level(self) -> AccessLevel:
        """Get the effective access level (more restrictive of matter vs case)"""
        if self.inherited_access_level:
            # Return more restrictive level
            access_hierarchy = [
                AccessLevel.PUBLIC,
                AccessLevel.INTERNAL, 
                AccessLevel.CONFIDENTIAL,
                AccessLevel.PRIVILEGED,
                AccessLevel.HIGHLY_CONFIDENTIAL
            ]
            matter_idx = access_hierarchy.index(self.inherited_access_level)
            case_idx = access_hierarchy.index(self.case_specific_access)
            return access_hierarchy[max(matter_idx, case_idx)]
        return self.case_specific_access


class DocumentCore(BaseModel):
    """Core immutable document properties"""
    id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    document_hash: str  # SHA-256 hash for deduplication
    metadata_hash: str  # Hash of key metadata for fuzzy deduplication
    
    # File information (immutable)
    file_name: str
    original_file_path: str  # Original path when first ingested
    file_size: int
    mime_type: Optional[str] = None
    total_pages: int
    
    # Creation timestamps (immutable)
    first_ingested_at: datetime = Field(default_factory=datetime.now)
    file_created_at: Optional[datetime] = None
    file_modified_at: Optional[datetime] = None
    
    # External system references
    box_file_id: Optional[str] = None
    original_source_system: Optional[str] = None  # Box, SharePoint, etc.
    
    # Content integrity
    content_validated: bool = False
    content_hash_verified_at: Optional[datetime] = None


class DocumentMetadata(BaseModel):
    """Mutable document classification and analysis data"""
    document_id: str  # Foreign key to DocumentCore
    
    # Classification (can change with re-analysis)
    document_type: DocumentType
    title: str
    description: str
    summary: str
    
    # Temporal analysis
    document_date: Optional[datetime] = None  # Date of document content
    date_confidence: float = Field(ge=0.0, le=1.0, default=1.0)
    
    # Content analysis
    key_facts: List[str] = Field(default_factory=list)
    relevance_tags: List[DocumentRelevance] = Field(default_factory=list)
    mentioned_parties: List[str] = Field(default_factory=list)
    mentioned_dates: List[str] = Field(default_factory=list)
    
    # Key people
    author: Optional[str] = None
    recipient: Optional[str] = None
    witness: Optional[str] = None
    
    # Key content indicators
    key_pages: List[int] = Field(default_factory=list)
    key_phrases: List[str] = Field(default_factory=list)
    
    # AI analysis results
    ai_classification_confidence: float = Field(ge=0.0, le=1.0, default=1.0)
    ai_model_used: Optional[str] = None
    ai_analysis_date: datetime = Field(default_factory=datetime.now)
    
    # Human verification
    human_verified: bool = False
    verified_by: Optional[str] = None
    verification_date: Optional[datetime] = None
    verification_notes: Optional[str] = None
    
    # Version control for metadata
    metadata_version: int = 1
    last_updated: datetime = Field(default_factory=datetime.now)
    updated_by: Optional[str] = None


class DocumentCaseJunction(BaseModel):
    """Many-to-many relationship between documents and cases"""
    id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    document_id: str  # Foreign key to DocumentCore
    case_id: str  # Foreign key to Case
    
    # Case-specific metadata
    case_specific_title: Optional[str] = None  # Different title in this case context
    case_relevance_tags: List[DocumentRelevance] = Field(default_factory=list)
    case_specific_notes: Optional[str] = None
    
    # Discovery metadata
    production_batch: Optional[str] = None
    production_date: Optional[datetime] = None
    bates_number_start: Optional[str] = None
    bates_number_end: Optional[str] = None
    confidentiality_designation: Optional[str] = None
    producing_party: Optional[str] = None
    responsive_to_requests: List[str] = Field(default_factory=list)
    custodian: Optional[str] = None
    
    # Discovery segmentation metadata
    is_segment_of_production: bool = False
    segment_id: Optional[str] = None  # References DiscoverySegment.segment_id
    segment_number: Optional[int] = None
    total_segments: Optional[int] = None
    
    # Usage tracking in this case
    times_accessed_in_case: int = 0
    last_accessed_in_case: Optional[datetime] = None
    used_in_motions: List[str] = Field(default_factory=list)
    used_in_briefs: List[str] = Field(default_factory=list)
    
    # Relationship metadata
    added_to_case_at: datetime = Field(default_factory=datetime.now)
    added_by: Optional[str] = None
    removal_date: Optional[datetime] = None  # If document removed from case
    removal_reason: Optional[str] = None


class DocumentRelationship(BaseModel):
    """Relationships between documents"""
    id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    source_document_id: str  # Document A
    target_document_id: str  # Document B
    relationship_type: RelationshipType
    
    # Relationship strength and context
    confidence: float = Field(ge=0.0, le=1.0, default=1.0)
    context: Optional[str] = None  # Description of the relationship
    
    # Discovery context
    discovered_by: Optional[str] = None  # AI, human, rule
    discovered_at: datetime = Field(default_factory=datetime.now)
    
    # Bidirectional flag
    is_bidirectional: bool = False  # If true, relationship applies both ways
    
    # Quality control
    verified: bool = False
    verified_by: Optional[str] = None
    verification_date: Optional[datetime] = None


class ChunkMetadata(BaseModel):
    """Enhanced chunk storage with better document linking"""
    id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    document_id: str  # Foreign key to DocumentCore
    
    # Chunk content and position
    chunk_text: str
    chunk_index: int  # Position within document
    chunk_hash: str  # For deduplication at chunk level
    
    # Position information
    start_page: Optional[int] = None
    end_page: Optional[int] = None
    start_char: Optional[int] = None
    end_char: Optional[int] = None
    
    # Context and semantics
    section_title: Optional[str] = None
    semantic_type: Optional[str] = None  # paragraph, table, list, etc.
    context_summary: Optional[str] = None
    
    # Vector embeddings
    dense_vector: Optional[List[float]] = None
    sparse_vector: Optional[Dict[str, float]] = None
    embedding_model: Optional[str] = None
    
    # Quality metrics
    text_quality_score: float = Field(ge=0.0, le=1.0, default=1.0)
    extraction_confidence: float = Field(ge=0.0, le=1.0, default=1.0)
    
    # Usage and access
    access_count: int = 0
    last_accessed: Optional[datetime] = None
    
    # Metadata
    created_at: datetime = Field(default_factory=datetime.now)


class DeduplicationRecord(BaseModel):
    """Enhanced deduplication tracking"""
    id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    content_hash: str  # SHA-256 of document content
    metadata_hash: str  # Hash of key identifying metadata
    
    # Primary document (first occurrence)
    primary_document_id: str
    primary_case_id: str
    primary_discovered_at: datetime
    
    # Duplicate tracking
    duplicate_document_ids: List[str] = Field(default_factory=list)
    duplicate_count: int = 0
    
    # Fuzzy matching information
    similar_documents: List[Dict[str, Any]] = Field(default_factory=list)
    similarity_threshold_used: float = 0.95
    
    # Quality control
    deduplication_verified: bool = False
    false_positive_flag: bool = False  # Mark if not actually duplicate
    verification_notes: Optional[str] = None


# Query optimization models

class IndexStrategy(BaseModel):
    """Configuration for database indexing strategy"""
    table_name: str
    index_name: str
    columns: List[str]
    index_type: str = "btree"  # btree, hash, gin, gist
    partial_condition: Optional[str] = None  # For partial indexes
    created_at: datetime = Field(default_factory=datetime.now)
    
    # Performance metrics
    size_mb: Optional[float] = None
    usage_count: Optional[int] = None
    last_used: Optional[datetime] = None


class QueryPattern(BaseModel):
    """Track common query patterns for optimization"""
    pattern_id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    query_signature: str  # Normalized query pattern
    frequency: int = 0
    avg_execution_time_ms: float = 0.0
    
    # Query components frequently used together
    filter_columns: List[str] = Field(default_factory=list)
    sort_columns: List[str] = Field(default_factory=list)
    
    # Optimization suggestions
    suggested_indexes: List[str] = Field(default_factory=list)
    optimization_applied: bool = False
    
    # Tracking
    first_seen: datetime = Field(default_factory=datetime.now)
    last_seen: datetime = Field(default_factory=datetime.now)


# Database migration and versioning

class SchemaVersion(BaseModel):
    """Track database schema versions"""
    version: str
    description: str
    applied_at: datetime = Field(default_factory=datetime.now)
    migration_scripts: List[str] = Field(default_factory=list)
    rollback_available: bool = False


# Performance monitoring

class TableStats(BaseModel):
    """Table performance statistics"""
    table_name: str
    record_count: int
    size_mb: float
    avg_query_time_ms: float
    hot_queries: List[str] = Field(default_factory=list)
    
    # Partitioning information
    is_partitioned: bool = False
    partition_strategy: Optional[str] = None  # time, size, hash
    partition_count: Optional[int] = None
    
    # Index statistics
    total_indexes: int = 0
    unused_indexes: List[str] = Field(default_factory=list)
    
    collected_at: datetime = Field(default_factory=datetime.now)


# Request/Response models for the normalized system

class NormalizedDocumentCreateRequest(BaseModel):
    """Request to create a document in the normalized system"""
    # Core document info
    file_name: str
    file_path: str
    file_content: bytes
    
    # Case association
    case_id: str
    
    # Optional metadata
    document_type_hint: Optional[DocumentType] = None
    title_hint: Optional[str] = None
    
    # Processing options
    force_reprocessing: bool = False
    skip_deduplication: bool = False


class NormalizedDocumentResponse(BaseModel):
    """Response for document operations"""
    document_core: DocumentCore
    document_metadata: DocumentMetadata
    case_associations: List[DocumentCaseJunction]
    relationships: List[DocumentRelationship] = Field(default_factory=list)
    
    # Processing information
    is_duplicate: bool = False
    deduplication_info: Optional[DeduplicationRecord] = None
    chunks_created: int = 0
    processing_time_seconds: float = 0.0
    
    # Warnings and recommendations
    warnings: List[str] = Field(default_factory=list)
    recommendations: List[str] = Field(default_factory=list)


class HierarchicalSearchRequest(BaseModel):
    """Search request supporting matter/case hierarchy"""
    query: str
    
    # Scope
    matter_ids: Optional[List[str]] = None
    case_ids: Optional[List[str]] = None
    
    # Filters
    document_types: Optional[List[DocumentType]] = None
    relevance_tags: Optional[List[DocumentRelevance]] = None
    date_range: Optional[Dict[str, datetime]] = None
    access_level_required: AccessLevel = AccessLevel.INTERNAL
    
    # Search configuration
    include_relationships: bool = False
    include_similar_documents: bool = False
    max_results: int = 50
    
    # Cross-case analysis (requires special permissions)
    enable_cross_case_analysis: bool = False
    anonymize_results: bool = True


class HierarchicalSearchResponse(BaseModel):
    """Search response with hierarchical context"""
    results: List[Dict[str, Any]] = Field(default_factory=list)
    total_matches: int = 0
    
    # Hierarchical context
    matters_searched: List[str] = Field(default_factory=list)
    cases_searched: List[str] = Field(default_factory=list)
    
    # Performance metrics
    search_time_ms: float = 0.0
    indexes_used: List[str] = Field(default_factory=list)
    
    # Cross-case insights (if enabled)
    cross_case_patterns: List[Dict[str, Any]] = Field(default_factory=list)
    anonymized_similar_cases: List[Dict[str, Any]] = Field(default_factory=list)