"""
Data models for discovery deficiency analysis.

This module defines the data structures used for analyzing gaps between
what was requested in discovery and what was actually produced.
"""

from pydantic import BaseModel, Field
from typing import List, Optional, Dict
from datetime import datetime
from enum import Enum


class ProductionStatus(str, Enum):
    """Status of document production for a request."""
    FULLY_PRODUCED = "fully_produced"
    PARTIALLY_PRODUCED = "partially_produced"
    NOT_PRODUCED = "not_produced"


class EvidenceItem(BaseModel):
    """Evidence supporting the production status determination."""
    document_id: str
    document_title: str
    bates_range: Optional[str] = None
    quoted_text: str
    confidence_score: float = Field(ge=0, le=100)
    page_numbers: Optional[List[int]] = None


class RequestAnalysis(BaseModel):
    """Analysis of a single RFP request."""
    request_number: int
    request_text: str
    response_text: Optional[str] = None
    status: ProductionStatus
    confidence: float = Field(ge=0, le=100)
    evidence: List[EvidenceItem] = []
    deficiencies: List[str] = []
    search_queries_used: List[str] = []


class DeficiencyReport(BaseModel):
    """Complete deficiency analysis report for a discovery production."""
    id: str
    case_name: str
    processing_id: str
    production_batch: str
    rfp_document_id: str
    defense_response_id: Optional[str] = None
    analyses: List[RequestAnalysis]
    overall_completeness: float = Field(ge=0, le=100)
    generated_at: datetime
    generated_by: str = "deficiency_analyzer"
    report_version: int = 1


class DeficiencyAnalysisRequest(BaseModel):
    """Request model for initiating deficiency analysis."""
    rfp_document_id: str
    defense_response_id: Optional[str] = None
    production_batch: str
    processing_id: str


class DeficiencyReportResponse(BaseModel):
    """Response model for deficiency analysis API."""
    analysis_id: str
    status: str
    message: str
    report_id: Optional[str] = None