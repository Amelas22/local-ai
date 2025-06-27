"""
Pydantic models for motion drafting system
"""

from typing import List, Dict, Any, Optional
from datetime import datetime
from enum import Enum
from pydantic import BaseModel, Field, validator


class MotionType(str, Enum):
    """Types of legal motions"""
    DISMISS = "Motion to Dismiss"
    SUMMARY_JUDGMENT = "Motion for Summary Judgment"
    DISCOVERY = "Discovery Motion"
    PROTECTIVE_ORDER = "Motion for Protective Order"
    SANCTIONS = "Motion for Sanctions"
    COMPEL = "Motion to Compel"
    LIMINE = "Motion in Limine"
    RECONSIDERATION = "Motion for Reconsideration"
    OTHER = "Other Motion"


class OutlineSectionInput(BaseModel):
    """Input model for outline sections"""
    title: str = Field(..., description="Section title")
    section_type: str = Field(..., description="Type of section")
    points: List[str] = Field(default_factory=list, description="Content points to cover")
    authorities: List[str] = Field(default_factory=list, description="Legal authorities to cite")
    subsections: Optional[List['OutlineSectionInput']] = Field(default=None, description="Subsections")


class MotionOutlineInput(BaseModel):
    """Input model for motion outline"""
    title: Optional[str] = Field(None, description="Motion title")
    motion_type: MotionType = Field(MotionType.OTHER, description="Type of motion")
    case_name: str = Field(..., description="Case name for document retrieval")
    sections: List[OutlineSectionInput] = Field(..., description="Outline sections")
    target_pages: int = Field(25, ge=15, le=40, description="Target page count")
    jurisdiction: Optional[str] = Field(None, description="Legal jurisdiction")
    filing_deadline: Optional[datetime] = Field(None, description="Filing deadline")


class DraftingRequest(BaseModel):
    """Request model for motion drafting"""
    outline: MotionOutlineInput = Field(..., description="Motion outline")
    case_name: str = Field(..., description="Case name for document retrieval")
    target_length: str = Field("MEDIUM", description="Target length: SHORT, MEDIUM, or LONG")
    enable_case_research: bool = Field(True, description="Enable case document retrieval")
    expansion_cycles: int = Field(3, ge=1, le=5, description="Maximum expansion cycles")
    use_citations: bool = Field(True, description="Include legal citations")
    

class DraftingProgress(BaseModel):
    """Progress update model for drafting status"""
    status: str = Field(..., description="Current status")
    current_section: Optional[str] = Field(None, description="Section being drafted")
    sections_completed: int = Field(0, description="Number of sections completed")
    total_sections: int = Field(0, description="Total number of sections")
    current_word_count: int = Field(0, description="Current total word count")
    estimated_pages: int = Field(0, description="Estimated page count")
    messages: List[str] = Field(default_factory=list, description="Progress messages")


class SectionDraftResponse(BaseModel):
    """Response model for individual section draft"""
    section_id: str = Field(..., description="Section identifier")
    title: str = Field(..., description="Section title")
    content: str = Field(..., description="Drafted content")
    word_count: int = Field(..., description="Word count")
    citations: List[str] = Field(default_factory=list, description="Citations used")
    confidence_score: float = Field(..., ge=0.0, le=1.0, description="Confidence score")
    expansion_cycles: int = Field(..., description="Number of expansion cycles")
    needs_revision: bool = Field(False, description="Whether section needs revision")


class MotionDraftResponse(BaseModel):
    """Response model for complete motion draft"""
    title: str = Field(..., description="Motion title")
    case_name: str = Field(..., description="Case name")
    sections: List[SectionDraftResponse] = Field(..., description="Drafted sections")
    total_word_count: int = Field(..., description="Total word count")
    total_pages: int = Field(..., description="Estimated page count")
    creation_timestamp: datetime = Field(..., description="Creation timestamp")
    coherence_score: float = Field(0.0, ge=0.0, le=1.0, description="Document coherence score")
    review_notes: List[str] = Field(default_factory=list, description="Review feedback")
    export_links: Dict[str, str] = Field(default_factory=dict, description="Links to exported formats")


class RevisionRequest(BaseModel):
    """Request model for motion revision"""
    motion_id: str = Field(..., description="Motion draft ID")
    section_ids: List[str] = Field(..., description="Sections to revise")
    revision_instructions: Dict[str, str] = Field(..., description="Section-specific instructions")
    maintain_length: bool = Field(True, description="Maintain current length")


class ExportRequest(BaseModel):
    """Request model for motion export"""
    motion_id: str = Field(..., description="Motion draft ID")
    format: str = Field("docx", description="Export format: docx, pdf, txt")
    include_metadata: bool = Field(True, description="Include metadata page")
    include_citations_list: bool = Field(True, description="Include citations appendix")
    box_folder_id: Optional[str] = Field(None, description="Box folder ID for upload")


class QualityMetrics(BaseModel):
    """Quality metrics for drafted motion"""
    coherence_score: float = Field(..., ge=0.0, le=1.0)
    citation_accuracy: float = Field(..., ge=0.0, le=1.0)
    argument_strength: float = Field(..., ge=0.0, le=1.0)
    factual_consistency: float = Field(..., ge=0.0, le=1.0)
    readiness_score: int = Field(..., ge=1, le=10)
    issues_found: List[Dict[str, Any]] = Field(default_factory=list)
    suggestions: List[str] = Field(default_factory=list)


# Update forward references
OutlineSectionInput.model_rebuild()


# Validation functions
def validate_outline_structure(outline: MotionOutlineInput) -> bool:
    """Validate outline has proper structure"""
    if not outline.sections:
        return False
    
    # Check for required sections based on motion type
    required_sections = {
        MotionType.DISMISS: ["introduction", "facts", "legal standard", "argument"],
        MotionType.SUMMARY_JUDGMENT: ["introduction", "undisputed facts", "legal standard", "argument"],
        MotionType.DISCOVERY: ["introduction", "meet and confer", "argument", "relief"]
    }
    
    if outline.motion_type in required_sections:
        section_titles_lower = [s.title.lower() for s in outline.sections]
        for required in required_sections[outline.motion_type]:
            if not any(required in title for title in section_titles_lower):
                return False
    
    return True


def estimate_pages_from_outline(outline: MotionOutlineInput) -> int:
    """Estimate page count from outline structure"""
    # Base calculation
    sections_count = len(outline.sections)
    subsections_count = sum(len(s.subsections) if s.subsections else 0 for s in outline.sections)
    
    # Rough estimates
    pages_per_section = 3
    pages_per_subsection = 1.5
    
    estimated = (sections_count * pages_per_section) + (subsections_count * pages_per_subsection)
    
    # Adjust for motion type
    if outline.motion_type == MotionType.SUMMARY_JUDGMENT:
        estimated *= 1.5  # These tend to be longer
    elif outline.motion_type in [MotionType.DISCOVERY, MotionType.COMPEL]:
        estimated *= 0.8  # These tend to be shorter
    
    return max(15, min(40, int(estimated)))