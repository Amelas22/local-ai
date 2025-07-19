"""
Pydantic models for deficiency analysis data structures.

This module defines the data models used for RTP deficiency analysis,
including DeficiencyReport and DeficiencyItem models with appropriate
validation and case isolation support.
"""

from datetime import datetime
from typing import Dict, List, Optional
from uuid import UUID, uuid4

from pydantic import BaseModel, Field, field_validator


class DeficiencyItem(BaseModel):
    """
    Represents a single RTP item analysis result.
    
    Tracks the analysis of individual Request to Produce items,
    their opposing counsel responses, and evidence classification.
    """
    
    id: UUID = Field(default_factory=uuid4, description="Unique identifier")
    report_id: UUID = Field(..., description="Parent DeficiencyReport reference")
    request_number: str = Field(..., description="RTP item number (e.g., 'RFP No. 12')")
    request_text: str = Field(..., description="Full text of the RTP request")
    oc_response_text: str = Field(..., description="Opposing counsel's response")
    classification: str = Field(
        ..., 
        description="Production classification",
        pattern="^(fully_produced|partially_produced|not_produced|no_responsive_docs)$"
    )
    confidence_score: float = Field(
        ..., 
        ge=0.0, 
        le=1.0,
        description="AI confidence in classification (0-1)"
    )
    evidence_chunks: List[Dict] = Field(
        default_factory=list,
        description="Array of matched document chunks with metadata (JSON field)"
    )
    reviewer_notes: Optional[str] = Field(
        None,
        description="Legal team annotations"
    )
    modified_by: Optional[str] = Field(
        None,
        description="User who made changes"
    )
    modified_at: Optional[datetime] = Field(
        None,
        description="Last modification time"
    )
    
    @field_validator('classification')
    @classmethod
    def validate_classification(cls, v: str) -> str:
        """Validate classification is one of allowed values."""
        allowed_values = {
            'fully_produced',
            'partially_produced', 
            'not_produced',
            'no_responsive_docs'
        }
        if v not in allowed_values:
            raise ValueError(f"Classification must be one of: {allowed_values}")
        return v
    
    @field_validator('confidence_score')
    @classmethod
    def validate_confidence_score(cls, v: float) -> float:
        """Ensure confidence score is between 0 and 1."""
        if not 0 <= v <= 1:
            raise ValueError("Confidence score must be between 0 and 1")
        return v
    
    class Config:
        json_schema_extra = {
            "example": {
                "id": "123e4567-e89b-12d3-a456-426614174000",
                "report_id": "456e7890-e89b-12d3-a456-426614174000",
                "request_number": "RFP No. 12",
                "request_text": "All emails between parties regarding the contract",
                "oc_response_text": "No responsive documents exist",
                "classification": "not_produced",
                "confidence_score": 0.85,
                "evidence_chunks": [
                    {
                        "document_id": "doc123",
                        "chunk_text": "Email thread discussing contract terms",
                        "relevance_score": 0.92
                    }
                ],
                "reviewer_notes": "Found emails in production PROD_001",
                "modified_by": "user@lawfirm.com",
                "modified_at": "2024-01-15T10:30:00Z"
            }
        }


class DeficiencyReport(BaseModel):
    """
    Represents a complete deficiency analysis report.
    
    Contains the overall analysis results for a set of RTP requests
    compared against a discovery production, with case isolation.
    """
    
    id: UUID = Field(default_factory=uuid4, description="Unique identifier")
    case_name: str = Field(..., description="Case identifier for isolation")
    production_id: UUID = Field(..., description="Links to discovery production")
    rtp_document_id: UUID = Field(..., description="Reference to uploaded RTP document")
    oc_response_document_id: UUID = Field(..., description="Reference to OC response document")
    analysis_status: str = Field(
        default="pending",
        description="Analysis status",
        pattern="^(pending|processing|completed|failed)$"
    )
    created_at: datetime = Field(
        default_factory=datetime.utcnow,
        description="Analysis start time"
    )
    completed_at: Optional[datetime] = Field(
        None,
        description="Analysis completion time"
    )
    total_requests: int = Field(
        default=0,
        ge=0,
        description="Number of RTP items analyzed"
    )
    summary_statistics: Dict = Field(
        default_factory=lambda: {
            "fully_produced": 0,
            "partially_produced": 0,
            "not_produced": 0,
            "no_responsive_docs": 0,
            "total_analyzed": 0
        },
        description="Breakdown by category (JSON field)"
    )
    
    @field_validator('analysis_status')
    @classmethod
    def validate_analysis_status(cls, v: str) -> str:
        """Validate analysis status is one of allowed values."""
        allowed_values = {'pending', 'processing', 'completed', 'failed'}
        if v not in allowed_values:
            raise ValueError(f"Analysis status must be one of: {allowed_values}")
        return v
    
    @field_validator('case_name')
    @classmethod
    def validate_case_name(cls, v: str) -> str:
        """Validate case name is not empty."""
        if not v or not v.strip():
            raise ValueError("Case name cannot be empty")
        return v.strip()
    
    @field_validator('summary_statistics')
    @classmethod
    def validate_summary_statistics(cls, v: Dict) -> Dict:
        """Ensure summary statistics has expected structure."""
        # Allow empty dict for initial state
        if not v:
            return {
                "fully_produced": 0,
                "partially_produced": 0,
                "not_produced": 0,
                "no_responsive_docs": 0,
                "total_analyzed": 0
            }
        return v
    
    class Config:
        json_schema_extra = {
            "example": {
                "id": "789e0123-e89b-12d3-a456-426614174000",
                "case_name": "Smith_v_Jones_2024",
                "production_id": "prod-456e7890-e89b-12d3-a456-426614174000",
                "rtp_document_id": "doc-123e4567-e89b-12d3-a456-426614174000",
                "oc_response_document_id": "doc-234e5678-e89b-12d3-a456-426614174000",
                "analysis_status": "completed",
                "created_at": "2024-01-15T09:00:00Z",
                "completed_at": "2024-01-15T09:15:00Z",
                "total_requests": 25,
                "summary_statistics": {
                    "fully_produced": 10,
                    "partially_produced": 5,
                    "not_produced": 8,
                    "no_responsive_docs": 2,
                    "total_analyzed": 25
                }
            }
        }