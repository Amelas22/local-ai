"""
Models package for Clerk Legal AI System
"""

from .fact_models import *
from .source_document_models import *
from .deficiency_models import *

__all__ = [
    # Fact models
    "CaseFact",
    "FactCategory",
    "EntityType",
    "DateReference",
    "CaseFactCollection",
    "FactExtractionRequest",
    "ExhibitIndex",
    "ExhibitReference",
    "DepositionCitation",
    "SharedKnowledgeEntry",
    "CaseIsolationConfig",
    # Source document models
    "DocumentType",
    "DocumentRelevance",
    "SourceDocument",
    "EvidenceSearchQuery",
    "EvidenceSearchResult",
    "DocumentClassificationRequest",
    "DocumentClassificationResult",
    # Deficiency models
    "DeficiencyReport",
    "DeficiencyItem",
]
