"""
Evidence-to-Argument Mapper with Case Isolation
Maps facts, depositions, and exhibits to legal arguments while maintaining strict case boundaries
"""

import logging
from typing import List, Dict, Any, Optional, Tuple, Set
from dataclasses import dataclass, field
from datetime import datetime
import json

from pydantic_ai import Agent
from pydantic_ai.models.openai import OpenAIModel

from src.models.fact_models import (
    CaseFact, DepositionCitation, ExhibitIndex,
    FactCategory, CaseIsolationConfig
)
from src.vector_storage.qdrant_store import QdrantVectorStore
from src.vector_storage.embeddings import EmbeddingGenerator
from src.ai_agents.fact_extractor import FactExtractor
from src.document_processing.deposition_parser import DepositionParser
from src.document_processing.exhibit_indexer import ExhibitIndexer
from config.settings import settings

logger = logging.getLogger("clerk_api")


@dataclass
class EvidenceItem:
    """Represents a piece of evidence"""
    id: str
    case_name: str
    evidence_type: str  # "fact", "deposition", "exhibit"
    content: str
    source: str
    relevance_score: float
    citation_format: str
    metadata: Dict[str, Any] = field(default_factory=dict)


@dataclass
class ArgumentSection:
    """Represents a legal argument section from an outline"""
    id: str
    title: str
    points: List[str]
    legal_authorities: List[str]
    required_evidence_types: List[str] = field(default_factory=list)


@dataclass
class EvidenceMapping:
    """Maps evidence to an argument section"""
    argument_id: str
    argument_title: str
    evidence_items: List[EvidenceItem]
    total_relevance_score: float
    evidence_summary: str
    suggested_usage: Dict[str, str]  # evidence_id -> usage suggestion


class EvidenceMapper:
    """
    Maps case evidence to legal arguments with strict case isolation.
    Prioritizes strongest evidence and generates usage recommendations.
    """
    
    def __init__(self, case_name: str):
        """Initialize evidence mapper for specific case"""
        self.case_name = case_name
        self.vector_store = QdrantVectorStore()
        self.embedding_generator = EmbeddingGenerator()
        
        # Initialize case-specific extractors
        self.fact_extractor = FactExtractor(case_name)
        self.deposition_parser = DepositionParser(case_name)
        self.exhibit_indexer = ExhibitIndexer(case_name)
        
        # Initialize LLM for relevance scoring
        self.llm_model = OpenAIModel(settings.ai.default_model)
        self.relevance_scorer = self._create_relevance_scorer()
        
        # Case isolation config
        self.isolation_config = CaseIsolationConfig(
            case_name=case_name,
            enable_shared_knowledge=True,
            audit_access=True
        )
        
        logger.info(f"EvidenceMapper initialized for case: {case_name}")
    
    def _create_relevance_scorer(self) -> Agent:
        """Create AI agent for scoring evidence relevance"""
        return Agent(
            self.llm_model,
            system_prompt="""You are a legal evidence analyst. Score the relevance of evidence to legal arguments.
            Consider:
            1. Direct support for the argument point
            2. Credibility and strength of the evidence
            3. Legal admissibility concerns
            4. Potential counter-arguments
            
            Provide a relevance score from 0.0 to 1.0 and a brief explanation."""
        )
    
    async def map_evidence_to_outline(
        self,
        outline_sections: List[ArgumentSection],
        evidence_limit_per_section: int = 10
    ) -> List[EvidenceMapping]:
        """Map all available evidence to outline sections"""
        logger.info(f"Mapping evidence for {len(outline_sections)} argument sections")
        
        mappings = []
        
        for section in outline_sections:
            # Find relevant evidence for this section
            evidence_items = await self._find_evidence_for_argument(
                section,
                limit=evidence_limit_per_section * 2  # Get extra to filter
            )
            
            # Score and rank evidence
            scored_evidence = await self._score_evidence_relevance(
                section,
                evidence_items
            )
            
            # Select top evidence
            top_evidence = sorted(
                scored_evidence,
                key=lambda x: x.relevance_score,
                reverse=True
            )[:evidence_limit_per_section]
            
            # Generate usage suggestions
            usage_suggestions = await self._generate_usage_suggestions(
                section,
                top_evidence
            )
            
            # Create mapping
            mapping = EvidenceMapping(
                argument_id=section.id,
                argument_title=section.title,
                evidence_items=top_evidence,
                total_relevance_score=sum(e.relevance_score for e in top_evidence) / len(top_evidence) if top_evidence else 0,
                evidence_summary=self._summarize_evidence(top_evidence),
                suggested_usage=usage_suggestions
            )
            
            mappings.append(mapping)
        
        return mappings
    
    async def _find_evidence_for_argument(
        self,
        section: ArgumentSection,
        limit: int
    ) -> List[EvidenceItem]:
        """Find all types of evidence relevant to an argument"""
        evidence_items = []
        
        # Create search query from argument points
        search_query = f"{section.title} {' '.join(section.points[:3])}"
        
        # Search facts
        facts = await self.fact_extractor.search_facts(
            query=search_query,
            limit=limit // 3
        )
        
        for fact in facts:
            evidence_items.append(EvidenceItem(
                id=fact.id,
                case_name=self.case_name,
                evidence_type="fact",
                content=fact.content,
                source=fact.source_document,
                relevance_score=0.0,  # Will be scored later
                citation_format=f"Case Fact: {fact.source_document}",
                metadata={"category": fact.category, "confidence": fact.confidence_score}
            ))
        
        # Search depositions
        depositions = await self.deposition_parser.search_testimony(
            query=search_query,
            limit=limit // 3
        )
        
        for depo in depositions:
            evidence_items.append(EvidenceItem(
                id=depo.id,
                case_name=self.case_name,
                evidence_type="deposition",
                content=depo.testimony_excerpt,
                source=depo.source_document,
                relevance_score=0.0,
                citation_format=depo.citation_format,
                metadata={"deponent": depo.deponent_name, "page": depo.page_start}
            ))
        
        # Search exhibits
        exhibits = await self.exhibit_indexer.search_exhibits(
            query=search_query,
            limit=limit // 3
        )
        
        for exhibit in exhibits:
            evidence_items.append(EvidenceItem(
                id=exhibit.id,
                case_name=self.case_name,
                evidence_type="exhibit",
                content=exhibit.description,
                source=exhibit.source_document,
                relevance_score=0.0,
                citation_format=f"{exhibit.exhibit_number}",
                metadata={"type": exhibit.document_type, "status": exhibit.authenticity_status}
            ))
        
        return evidence_items
    
    async def _score_evidence_relevance(
        self,
        section: ArgumentSection,
        evidence_items: List[EvidenceItem]
    ) -> List[EvidenceItem]:
        """Score evidence relevance to argument using LLM"""
        scored_items = []
        
        for item in evidence_items:
            prompt = f"""Score the relevance of this evidence to the legal argument.

Argument: {section.title}
Key Points: {', '.join(section.points[:3])}

Evidence Type: {item.evidence_type}
Evidence Content: {item.content}

Provide:
1. Relevance score (0.0-1.0)
2. Brief explanation (1-2 sentences)

Format: SCORE: X.X | REASON: explanation"""

            try:
                response = await self.relevance_scorer.run(prompt)
                
                # Parse response
                if "SCORE:" in response.data and "|" in response.data:
                    parts = response.data.split("|")
                    score_part = parts[0].split("SCORE:")[1].strip()
                    score = float(score_part)
                    
                    item.relevance_score = min(max(score, 0.0), 1.0)
                else:
                    item.relevance_score = 0.5  # Default
                    
            except Exception as e:
                logger.warning(f"Failed to score evidence: {e}")
                item.relevance_score = 0.5
            
            scored_items.append(item)
        
        return scored_items
    
    async def _generate_usage_suggestions(
        self,
        section: ArgumentSection,
        evidence_items: List[EvidenceItem]
    ) -> Dict[str, str]:
        """Generate suggestions for how to use each piece of evidence"""
        suggestions = {}
        
        for item in evidence_items:
            if item.relevance_score < 0.3:
                continue  # Skip low-relevance evidence
            
            # Generate usage based on evidence type
            if item.evidence_type == "fact":
                if item.metadata.get("category") == FactCategory.TIMELINE:
                    suggestion = f"Use to establish chronology: {item.citation_format}"
                elif item.metadata.get("category") == FactCategory.DAMAGES:
                    suggestion = f"Cite to support damages claim: {item.citation_format}"
                else:
                    suggestion = f"Reference to support factual assertion: {item.citation_format}"
            
            elif item.evidence_type == "deposition":
                deponent = item.metadata.get("deponent", "witness")
                suggestion = f"Quote {deponent}'s testimony: {item.citation_format}"
            
            elif item.evidence_type == "exhibit":
                doc_type = item.metadata.get("type", "document")
                suggestion = f"Reference {doc_type}: {item.citation_format}"
            
            suggestions[item.id] = suggestion
        
        return suggestions
    
    def _summarize_evidence(self, evidence_items: List[EvidenceItem]) -> str:
        """Create summary of available evidence"""
        if not evidence_items:
            return "No supporting evidence found."
        
        # Count by type
        type_counts = {}
        for item in evidence_items:
            type_counts[item.evidence_type] = type_counts.get(item.evidence_type, 0) + 1
        
        # Build summary
        summary_parts = []
        
        if "fact" in type_counts:
            summary_parts.append(f"{type_counts['fact']} supporting facts")
        if "deposition" in type_counts:
            summary_parts.append(f"{type_counts['deposition']} deposition citations")
        if "exhibit" in type_counts:
            summary_parts.append(f"{type_counts['exhibit']} exhibits")
        
        avg_relevance = sum(e.relevance_score for e in evidence_items) / len(evidence_items)
        
        return f"Found {', '.join(summary_parts)} with {avg_relevance:.0%} average relevance"
    
    async def find_supporting_evidence(
        self,
        argument_text: str,
        evidence_types: Optional[List[str]] = None,
        min_relevance: float = 0.5,
        limit: int = 5
    ) -> List[EvidenceItem]:
        """Find evidence supporting a specific argument statement"""
        all_evidence = []
        
        # Search each evidence type
        if not evidence_types or "fact" in evidence_types:
            facts = await self.fact_extractor.search_facts(argument_text, limit=limit)
            all_evidence.extend([
                EvidenceItem(
                    id=f.id,
                    case_name=self.case_name,
                    evidence_type="fact",
                    content=f.content,
                    source=f.source_document,
                    relevance_score=0.0,
                    citation_format=f"Fact from {f.source_document}",
                    metadata={"category": f.category}
                ) for f in facts
            ])
        
        if not evidence_types or "deposition" in evidence_types:
            depositions = await self.deposition_parser.search_testimony(argument_text, limit=limit)
            all_evidence.extend([
                EvidenceItem(
                    id=d.id,
                    case_name=self.case_name,
                    evidence_type="deposition",
                    content=d.testimony_excerpt,
                    source=d.source_document,
                    relevance_score=0.0,
                    citation_format=d.citation_format,
                    metadata={"deponent": d.deponent_name}
                ) for d in depositions
            ])
        
        if not evidence_types or "exhibit" in evidence_types:
            exhibits = await self.exhibit_indexer.search_exhibits(argument_text, limit=limit)
            all_evidence.extend([
                EvidenceItem(
                    id=e.id,
                    case_name=self.case_name,
                    evidence_type="exhibit",
                    content=e.description,
                    source=e.source_document,
                    relevance_score=0.0,
                    citation_format=e.exhibit_number,
                    metadata={"type": e.document_type}
                ) for e in exhibits
            ])
        
        # Score relevance
        dummy_section = ArgumentSection(
            id="search",
            title=argument_text,
            points=[argument_text],
            legal_authorities=[]
        )
        
        scored_evidence = await self._score_evidence_relevance(dummy_section, all_evidence)
        
        # Filter by minimum relevance and sort
        filtered = [e for e in scored_evidence if e.relevance_score >= min_relevance]
        filtered.sort(key=lambda x: x.relevance_score, reverse=True)
        
        return filtered[:limit]
    
    async def create_evidence_report(
        self,
        mappings: List[EvidenceMapping]
    ) -> str:
        """Create a formatted report of evidence mappings"""
        lines = [
            f"# Evidence Mapping Report for {self.case_name}",
            f"Generated: {datetime.now().strftime('%Y-%m-%d %H:%M')}",
            "",
            "## Summary",
            f"- Total Arguments: {len(mappings)}",
            f"- Total Evidence Items: {sum(len(m.evidence_items) for m in mappings)}",
            f"- Average Relevance Score: {sum(m.total_relevance_score for m in mappings) / len(mappings) if mappings else 0:.0%}",
            ""
        ]
        
        # Detail each argument's evidence
        for mapping in mappings:
            lines.extend([
                f"## {mapping.argument_title}",
                f"*Relevance Score: {mapping.total_relevance_score:.0%}*",
                "",
                mapping.evidence_summary,
                "",
                "### Supporting Evidence:",
                ""
            ])
            
            # Group by type
            by_type = {}
            for item in mapping.evidence_items:
                if item.evidence_type not in by_type:
                    by_type[item.evidence_type] = []
                by_type[item.evidence_type].append(item)
            
            # List evidence by type
            for evidence_type, items in by_type.items():
                lines.append(f"**{evidence_type.title()}s:**")
                for item in items:
                    usage = mapping.suggested_usage.get(item.id, "Use as supporting evidence")
                    lines.append(f"- {item.citation_format} ({item.relevance_score:.0%})")
                    lines.append(f"  - {usage}")
                lines.append("")
        
        return "\n".join(lines)
    
    def validate_case_isolation(self, evidence_item: EvidenceItem) -> bool:
        """Ensure evidence item belongs to the correct case"""
        return evidence_item.case_name == self.case_name