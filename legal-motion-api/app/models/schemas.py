from pydantic import BaseModel, Field, validator
from typing import List, Optional, Dict, Any, Union
from datetime import datetime
from enum import Enum
from pydantic import ConfigDict

class MotionType(str, Enum):
    MOTION_TO_DISMISS = "Motion to Dismiss"
    SUMMARY_JUDGMENT = "Motion for Summary Judgment"
    MOTION_IN_LIMINE = "Motion in Limine"
    MOTION_TO_COMPEL = "Motion to Compel"
    PROTECTIVE_ORDER = "Motion for Protective Order"
    EXCLUDE_EXPERT = "Motion to Exclude Expert"
    SANCTIONS = "Motion for Sanctions"
    DISCOVERY_MOTION = "Discovery Motion"
    JURISDICTIONAL_MOTION = "Jurisdictional Motion"
    OTHER = "Other"

# Expanded and more flexible categories
class ArgumentCategory(str, Enum):
    # Negligence Elements
    NEGLIGENCE_DUTY = "negligence_duty"
    NEGLIGENCE_BREACH = "negligence_breach"
    NEGLIGENCE_CAUSATION = "negligence_causation"
    NEGLIGENCE_DAMAGES = "negligence_damages"
    
    # Liability Categories
    LIABILITY_VICARIOUS = "liability_vicarious"
    LIABILITY_DERIVATIVE = "liability_derivative"
    LIABILITY_DIRECT = "liability_direct"
    LIABILITY_JOINT = "liability_joint"
    LIABILITY_COMPARATIVE = "liability_comparative"
    LIABILITY_IMMUNITY = "liability_immunity"
    
    # Causation Categories
    CAUSATION_PROXIMATE = "causation_proximate"
    CAUSATION_FACTUAL = "causation_factual"
    CAUSATION_INTERVENING = "causation_intervening"
    CAUSATION_SUPERSEDING = "causation_superseding"
    
    # Damages Categories
    DAMAGES_ECONOMIC = "damages_economic"
    DAMAGES_NONECONOMIC = "damages_noneconomic"
    DAMAGES_PUNITIVE = "damages_punitive"
    DAMAGES_MITIGATION = "damages_mitigation"
    DAMAGES_CALCULATION = "damages_calculation"
    
    # Procedural Categories
    PROCEDURAL_JURISDICTION = "procedural_jurisdiction"
    PROCEDURAL_VENUE = "procedural_venue"
    PROCEDURAL_SERVICE = "procedural_service"
    PROCEDURAL_STATUTE_LIMITATIONS = "procedural_statute_limitations"
    PROCEDURAL_STANDING = "procedural_standing"
    PROCEDURAL_PLEADING_DEFICIENCY = "procedural_pleading_deficiency"
    PROCEDURAL_DISCOVERY = "procedural_discovery"
    
    # Evidence Categories
    EVIDENCE_ADMISSIBILITY = "evidence_admissibility"
    EVIDENCE_RELEVANCE = "evidence_relevance"
    EVIDENCE_PREJUDICE = "evidence_prejudice"
    EVIDENCE_HEARSAY = "evidence_hearsay"
    EVIDENCE_AUTHENTICATION = "evidence_authentication"
    EVIDENCE_PRIVILEGE = "evidence_privilege"
    
    # Expert Witness Categories
    EXPERT_QUALIFICATION = "expert_qualification"
    EXPERT_METHODOLOGY = "expert_methodology"
    EXPERT_RELIABILITY = "expert_reliability"
    EXPERT_RELEVANCE = "expert_relevance"
    EXPERT_DAUBERT = "expert_daubert"
    
    # Contract/Business Categories
    CONTRACT_BREACH = "contract_breach"
    CONTRACT_FORMATION = "contract_formation"
    CONTRACT_INTERPRETATION = "contract_interpretation"
    
    # Insurance Categories
    INSURANCE_COVERAGE = "insurance_coverage"
    INSURANCE_BAD_FAITH = "insurance_bad_faith"
    INSURANCE_EXCLUSION = "insurance_exclusion"
    
    # Constitutional Categories
    CONSTITUTIONAL_DUE_PROCESS = "constitutional_due_process"
    CONSTITUTIONAL_EQUAL_PROTECTION = "constitutional_equal_protection"
    
    # Other
    OTHER = "other"
    CUSTOM = "custom"  # For AI-determined categories

class StrengthLevel(str, Enum):
    VERY_WEAK = "very_weak"
    WEAK = "weak"
    MODERATE = "moderate"
    STRONG = "strong"
    VERY_STRONG = "very_strong"

class ArgumentResearchPriority(BaseModel):
    """Research priority specific to an individual argument"""
    research_question: str = Field(..., description="Specific question to research")
    suggested_search_terms: List[str] = Field(..., description="Keywords for research")
    case_law_focus: Optional[str] = Field(None, description="Specific area of case law to explore")
    factual_investigation: Optional[str] = Field(None, description="Facts to investigate in case file")
    
class AnalysisOptions(BaseModel):
    include_citations: bool = Field(True, description="Include case law citations analysis")
    verify_citations: bool = Field(False, description="Verify citation accuracy (slower)")
    extract_all_arguments: bool = Field(True, description="Extract every argument, even minor ones")
    allow_custom_categories: bool = Field(True, description="Allow AI to create custom categories")
    min_argument_confidence: float = Field(0.3, description="Minimum confidence to include argument (0-1)")

class LegalCitation(BaseModel):
    full_citation: str = Field(..., description="Complete legal citation")
    case_name: str = Field(..., description="Primary case name")
    legal_principle: str = Field(..., description="Legal principle or holding")
    application: str = Field(..., description="How citation applies to current case")
    jurisdiction: str = Field(..., description="Court jurisdiction")
    year: int = Field(..., description="Year of decision")
    is_binding: bool = Field(..., description="Whether citation is binding authority")
    citation_strength: StrengthLevel = Field(..., description="Strength of citation support")

class ExtractedArgument(BaseModel):
    """Individual argument extracted from the motion - enhanced for research guidance"""
    argument_id: str = Field(..., description="Unique identifier for this argument")
    argument_text: str = Field(..., description="Direct quote or close paraphrase from motion")
    detailed_summary: str = Field(..., description="Comprehensive summary including context and implications")
    excerpts_from_motion: List[str] = Field(..., description="Direct quotes from the motion supporting this argument")
    category: Union[ArgumentCategory, str] = Field(..., description="Primary category (can be custom)")
    subcategories: List[str] = Field(default_factory=list, description="Additional relevant categories")
    location_in_motion: str = Field(..., description="Where in motion this appears (section/paragraph)")
    legal_basis: str = Field(..., description="Legal foundation for argument")
    factual_basis: Optional[str] = Field(None, description="Factual assertions supporting argument")
    strength_indicators: List[str] = Field(..., description="Factors indicating argument strength")
    weaknesses: List[str] = Field(default_factory=list, description="Potential weaknesses identified")
    cited_cases: List[LegalCitation] = Field(default_factory=list, description="Supporting case law")
    cited_statutes: List[str] = Field(default_factory=list, description="Statutes or rules cited")
    counterarguments: List[str] = Field(default_factory=list, description="Potential counterarguments")
    strength_assessment: StrengthLevel = Field(..., description="Overall argument strength")
    confidence_score: float = Field(..., ge=0, le=1, description="AI confidence in extraction (0-1)")
    requires_expert_response: bool = Field(False, description="Whether expert testimony needed to counter")
    priority_level: int = Field(..., ge=1, le=5, description="Priority for response (1-5)")
    research_priorities: List[ArgumentResearchPriority] = Field(..., description="Specific research tasks for this argument")
    required_evidence: List[str] = Field(..., description="Evidence needed from case file to counter this argument")
    suggested_case_facts_to_find: List[str] = Field(..., description="Specific facts to look for in depositions/discovery")

class ArgumentGroup(BaseModel):
    """Groups of related arguments"""
    group_name: str = Field(..., description="Name for this group of arguments")
    theme: str = Field(..., description="Common theme or strategy")
    arguments: List[str] = Field(..., description="List of argument IDs in this group")
    combined_strength: StrengthLevel = Field(..., description="Overall strength of grouped arguments")
    strategic_importance: str = Field(..., description="Why this group matters strategically")

class ResearchPriority(BaseModel):
    research_area: str = Field(..., description="Area requiring research")
    priority_level: int = Field(..., ge=1, le=5, description="Priority level (1-5)")
    suggested_sources: List[str] = Field(..., description="Recommended research sources")
    key_questions: List[str] = Field(..., description="Key questions to investigate")
    related_arguments: List[str] = Field(..., description="Argument IDs this research supports")

class MotionAnalysisRequest(BaseModel):
    motion_text: str = Field(..., min_length=100, max_length=50000, description="Full text of the motion")
    case_context: Optional[str] = Field(None, max_length=2000, description="Additional case context")
    analysis_options: AnalysisOptions = Field(default_factory=AnalysisOptions)
    
    @validator('motion_text')
    def validate_motion_text(cls, v):
        if not v.strip():
            raise ValueError('Motion text cannot be empty')
        return v.strip()

class ComprehensiveMotionAnalysis(BaseModel):
    """Comprehensive analysis extracting ALL arguments"""
    motion_type: str = Field(..., description="Type of legal motion")
    case_number: Optional[str] = Field(None, description="Case identification number")
    parties: List[str] = Field(default_factory=list, description="Parties involved")
    filing_date: Optional[datetime] = Field(None, description="Motion filing date")
    # All extracted arguments
    all_arguments: List[ExtractedArgument] = Field(..., description="Every argument found in motion")
    # Metadata
    total_arguments_found: int = Field(..., description="Total number of distinct arguments")
    categories_used: List[str] = Field(..., description="All categories identified")
    custom_categories_created: List[str] = Field(default_factory=list, description="Any custom categories AI created")

class ComprehensiveMotionAnalysisResponse(ComprehensiveMotionAnalysis):
    request_id: str = Field(..., description="Unique request identifier")
    processing_time: float = Field(..., description="Processing time in seconds")
    timestamp: datetime = Field(default_factory=datetime.utcnow, description="Analysis timestamp")

    model_config = ConfigDict(
        json_schema_extra={
            "example": {
                "motion_type": "Motion in Limine",
                "case_number": "2024-CV-12345",
                "parties": ["Plaintiff Corp", "Defendant LLC"],
                "all_arguments": [
                    {
                        "argument_id": "arg_001",
                        "argument_text": "Count II imposes no additional liability beyond Count III...",
                        "argument_summary": "Active negligence claim is redundant to vicarious liability",
                        "category": "liability_derivative",
                        "location_in_motion": "Section I.A, Paragraphs 3-5",
                        "strength_assessment": "strong",
                        "confidence_score": 0.95,
                        "priority_level": 1
                    }
                ],
                "total_arguments_found": 7,
                "categories_used": ["liability_derivative", "liability_vicarious"],
                "custom_categories_created": ["liability_joint"]
            }
        }
    )

class HealthCheck(BaseModel):
    status: str = Field(..., description="Service status")
    timestamp: datetime = Field(..., description="Check timestamp")
    version: str = Field(..., description="API version")