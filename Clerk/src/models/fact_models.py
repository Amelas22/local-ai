"""
Fact extraction models with case isolation for the Clerk legal AI system.
Ensures complete data separation between different legal matters.
"""

from typing import List, Dict, Any, Optional, Tuple
from datetime import datetime
from enum import Enum
from dataclasses import dataclass, field
from pydantic import BaseModel, Field, validator


class FactCategory(str, Enum):
    """Categories for classifying extracted facts"""

    PROCEDURAL = "procedural"  # Court filings, motions, orders
    SUBSTANTIVE = "substantive"  # Core case facts
    EVIDENTIARY = "evidentiary"  # Evidence, exhibits, testimony
    MEDICAL = "medical"  # Medical records, diagnoses
    DAMAGES = "damages"  # Financial losses, injuries
    TIMELINE = "timeline"  # Date-specific events
    PARTY = "party"  # Information about parties
    EXPERT = "expert"  # Expert opinions and reports
    REGULATORY = "regulatory"  # Regulatory violations or compliance


class EntityType(str, Enum):
    """Types of entities that can be extracted"""

    PERSON = "person"
    ORGANIZATION = "organization"
    LOCATION = "location"
    DATE = "date"
    TIME = "time"
    VEHICLE = "vehicle"
    MEDICAL_CONDITION = "medical_condition"
    LEGAL_CITATION = "legal_citation"
    MONETARY_AMOUNT = "monetary_amount"


@dataclass
class DateReference:
    """Represents a date or date range in a fact"""

    date_text: str  # Original text
    start_date: Optional[datetime] = None
    end_date: Optional[datetime] = None
    is_range: bool = False
    is_approximate: bool = False
    confidence: float = 1.0


@dataclass
class CaseFact:
    """
    Represents a single fact extracted from case documents.
    Includes case isolation through mandatory case_name field.
    """

    id: str
    case_name: str  # REQUIRED: Ensures case isolation
    content: str  # The fact text
    category: FactCategory
    source_document: str  # Document ID or path
    page_references: List[int]  # Page numbers where fact appears
    extraction_timestamp: datetime
    confidence_score: float  # 0.0 to 1.0

    # Entity information
    entities: Dict[EntityType, List[str]] = field(default_factory=dict)

    # Temporal information
    date_references: List[DateReference] = field(default_factory=list)

    # Relationships
    related_facts: List[str] = field(default_factory=list)  # IDs of related facts
    supporting_exhibits: List[str] = field(default_factory=list)  # Exhibit IDs

    # Quality metadata
    verification_status: str = "unverified"  # unverified, verified, disputed
    extraction_method: str = "automated"  # automated, manual, hybrid

    # For legal analysis
    legal_significance: Optional[str] = None
    argument_relevance: Dict[str, float] = field(
        default_factory=dict
    )  # argument_id -> relevance


@dataclass
class DepositionCitation:
    """Represents a parsed deposition citation"""

    id: str
    case_name: str  # REQUIRED: Case isolation
    deponent_name: str
    page_start: int
    testimony_excerpt: str
    citation_format: str  # e.g., "Smith Dep. 45:12-23"
    source_document: str
    deposition_date: Optional[datetime] = None
    page_end: Optional[int] = None
    line_start: Optional[int] = None
    line_end: Optional[int] = None
    related_facts: List[str] = field(default_factory=list)
    topics: List[str] = field(default_factory=list)


@dataclass
class ExhibitIndex:
    """Represents an exhibit in a case"""

    id: str
    case_name: str  # REQUIRED: Case isolation
    exhibit_number: str  # e.g., "Exhibit A", "Plaintiff's Ex. 12"
    description: str
    document_type: str  # photo, email, contract, medical_record, etc.
    source_document: str
    date_created: Optional[datetime] = None
    date_admitted: Optional[datetime] = None
    page_references: List[int] = field(default_factory=list)
    related_facts: List[str] = field(default_factory=list)
    related_depositions: List[str] = field(default_factory=list)
    authenticity_status: str = "pending"  # pending, admitted, objected, excluded
    relevance_score: float = 0.0


@dataclass
class FactTimeline:
    """Chronological organization of facts for a case"""

    case_name: str  # REQUIRED: Case isolation
    timeline_events: List[Tuple[datetime, CaseFact]]
    date_ranges: List[Tuple[datetime, datetime, str]]  # start, end, description
    key_dates: Dict[str, datetime]  # event_name -> date

    def add_fact(self, fact: CaseFact):
        """Add a fact to the timeline if it has date references"""
        if fact.date_references:
            for date_ref in fact.date_references:
                if date_ref.start_date:
                    self.timeline_events.append((date_ref.start_date, fact))

    def get_chronological_facts(self) -> List[CaseFact]:
        """Return facts in chronological order"""
        sorted_events = sorted(self.timeline_events, key=lambda x: x[0])
        return [fact for _, fact in sorted_events]


@dataclass
class CaseFactCollection:
    """Collection of all facts for a specific case"""

    case_name: str
    facts: List[CaseFact] = field(default_factory=list)
    depositions: List[DepositionCitation] = field(default_factory=list)
    exhibits: List[ExhibitIndex] = field(default_factory=list)
    timeline: Optional[FactTimeline] = None

    # Metadata
    total_documents_processed: int = 0
    extraction_start_time: Optional[datetime] = None
    extraction_end_time: Optional[datetime] = None

    # Statistics
    fact_count_by_category: Dict[FactCategory, int] = field(default_factory=dict)
    entity_count_by_type: Dict[EntityType, int] = field(default_factory=dict)

    def add_fact(self, fact: CaseFact):
        """Add a fact with validation"""
        if fact.case_name != self.case_name:
            raise ValueError(
                f"Case name mismatch: {fact.case_name} != {self.case_name}"
            )
        self.facts.append(fact)
        self.fact_count_by_category[fact.category] = (
            self.fact_count_by_category.get(fact.category, 0) + 1
        )


# Pydantic models for API interaction


class FactExtractionRequest(BaseModel):
    """Request model for fact extraction"""

    case_name: str = Field(..., description="Case name for isolation")
    document_id: str = Field(..., description="Document to extract facts from")
    document_content: str = Field(..., description="Document text content")
    extraction_options: Dict[str, Any] = Field(default_factory=dict)

    @validator("case_name")
    def validate_case_name(cls, v):
        """Ensure case name is valid and safe"""
        if not v or not v.strip():
            raise ValueError("Case name cannot be empty")
        # Prevent injection attacks
        if any(char in v for char in ["*", "?", "[", "]", "{", "}"]):
            raise ValueError("Case name contains invalid characters")
        return v.strip()


class FactSearchRequest(BaseModel):
    """Request model for searching facts"""

    case_name: str = Field(..., description="Case to search within")
    query: str = Field(..., description="Search query")
    categories: List[FactCategory] = Field(default_factory=list)
    date_range: Optional[Tuple[datetime, datetime]] = Field(None)
    include_shared_knowledge: bool = Field(
        True, description="Include statutes and regulations"
    )
    limit: int = Field(50, ge=1, le=200)


class SharedKnowledgeEntry(BaseModel):
    """Model for shared legal knowledge (statutes, regulations)"""

    id: str
    knowledge_type: str  # "florida_statute", "fmcsr_regulation", "case_law"
    identifier: str  # e.g., "Fla. Stat. § 768.81", "49 CFR § 395.8"
    title: str
    content: str
    effective_date: Optional[datetime] = None
    topics: List[str] = Field(default_factory=list)
    citations: List[str] = Field(default_factory=list)
    last_updated: datetime = Field(default_factory=datetime.now)


class CaseIsolationConfig(BaseModel):
    """Configuration for case isolation enforcement"""

    case_name: str
    allowed_collections: List[str] = Field(default_factory=list)
    enable_shared_knowledge: bool = True
    audit_access: bool = True

    def get_case_collections(self) -> List[str]:
        """Get all collections for this case"""
        return [
            f"{self.case_name}_facts",
            f"{self.case_name}_timeline",
            f"{self.case_name}_exhibits",
            f"{self.case_name}_depositions",
        ]

    def validate_collection_access(self, collection_name: str) -> bool:
        """Check if access to collection is allowed"""
        # Case-specific collections
        if collection_name.startswith(f"{self.case_name}_"):
            return True

        # Shared knowledge collections
        shared_collections = [
            "florida_statutes",
            "fmcsr_regulations",
            "case_law_precedents",
            "legal_standards",
        ]

        if self.enable_shared_knowledge and collection_name in shared_collections:
            return True

        # Check explicit allowlist
        return collection_name in self.allowed_collections
