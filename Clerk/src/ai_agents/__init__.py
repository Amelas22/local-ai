"""
AI Agents package for Clerk Legal AI System
"""

from .motion_drafter import EnhancedMotionDraftingAgent as MotionDrafter
from .case_researcher import CaseResearcher
from .legal_document_agent import LegalDocumentAgent
from .fact_extractor import FactExtractor
from .evidence_mapper import EvidenceMapper
from .enhanced_rag_agent import EnhancedRAGResearchAgent
from .evidence_discovery_agent import EvidenceDiscoveryAgent, ExhibitSuggestion, ArgumentEvidence

__all__ = [
    'MotionDrafter',
    'CaseResearcher', 
    'LegalDocumentAgent', 
    'FactExtractor',
    'EvidenceMapper', 
    'EnhancedRAGResearchAgent', 
    'EvidenceDiscoveryAgent',
    'ExhibitSuggestion', 
    'ArgumentEvidence'
]