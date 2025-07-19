"""
Models package for Clerk Legal AI System
"""

from .fact_models import (
    CaseFact,
    FactCategory,
    EntityType,
    DateReference,
    CaseFactCollection,
    FactExtractionRequest,
    ExhibitIndex,
    DepositionCitation,
    SharedKnowledgeEntry,
    CaseIsolationConfig,
)
from .source_document_models import (
    DocumentType,
    DocumentRelevance,
    SourceDocument,
    EvidenceSearchQuery,
    EvidenceSearchResult,
    DocumentClassificationRequest,
    DocumentClassificationResult,
)
from .deficiency_models import (
    DeficiencyReport,
    DeficiencyItem,
)

__all__ = [
    # Fact models
    "CaseFact",
    "FactCategory",
    "EntityType",
    "DateReference",
    "CaseFactCollection",
    "FactExtractionRequest",
    "ExhibitIndex",
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
