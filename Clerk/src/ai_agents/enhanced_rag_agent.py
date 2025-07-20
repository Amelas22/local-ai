"""
Enhanced RAG Research Agent with Case Isolation and Shared Knowledge Integration
Searches case-specific evidence and shared legal knowledge while maintaining strict boundaries
"""

import logging
from typing import List, Dict, Any, Optional
from dataclasses import dataclass, field
from enum import Enum

from pydantic_ai import Agent
from pydantic_ai.models.openai import OpenAIModel
from pydantic import BaseModel, Field

from src.vector_storage.qdrant_store import QdrantVectorStore
from src.vector_storage.embeddings import EmbeddingGenerator
from src.models.fact_models import CaseIsolationConfig
from src.ai_agents.fact_extractor import FactExtractor
from src.document_processing.deposition_parser import DepositionParser
from src.document_processing.exhibit_indexer import ExhibitIndexer
from src.data_loaders.florida_statutes_loader import FloridaStatutesLoader
from src.data_loaders.fmcsr_loader import FMCSRLoader
from config.settings import settings

logger = logging.getLogger("clerk_api")


class EnhancedDatabaseType(Enum):
    """Enhanced database types with granular options"""

    # Case-specific databases
    CASE_DOCUMENTS = "case_documents"  # Original case documents
    CASE_FACTS = "case_facts"  # Extracted facts
    CASE_DEPOSITIONS = "case_depositions"  # Deposition testimony
    CASE_EXHIBITS = "case_exhibits"  # Exhibit index
    CASE_TIMELINE = "case_timeline"  # Chronological events

    # Shared knowledge bases
    FLORIDA_STATUTES = "florida_statutes"  # Florida law
    FMCSR_REGULATIONS = "fmcsr_regulations"  # Federal motor carrier regs
    CASE_LAW_PRECEDENTS = "case_law_precedents"  # Important cases
    LEGAL_STANDARDS = "legal_standards"  # Legal tests and standards

    # Legacy/compatibility
    FIRM_KNOWLEDGE = "firm_knowledge"  # Firm's knowledge base
    ALL_CASE_DATA = "all_case_data"  # All case-specific collections
    ALL_SHARED = "all_shared"  # All shared collections


@dataclass
class EnhancedResearchQuery:
    """Enhanced research query with case isolation"""

    query_text: str
    case_name: str  # Required for case isolation
    query_type: str
    target_databases: List[EnhancedDatabaseType]
    priority: int = 3
    include_shared_knowledge: bool = True
    metadata: Dict[str, Any] = field(default_factory=dict)


@dataclass
class EnhancedResearchResult:
    """Enhanced research result with source tracking"""

    content: str
    source_type: str  # fact, deposition, exhibit, statute, regulation, etc.
    source_identifier: str  # Specific ID or citation
    source_collection: str  # Which collection it came from
    case_name: Optional[str]  # None for shared knowledge
    score: float
    metadata: Dict[str, Any]
    suggested_citation: str


class EnhancedResearchRequest(BaseModel):
    """Request model for enhanced RAG research"""

    questions: List[str] = Field(..., description="Questions to research")
    case_name: str = Field(..., description="Case name for isolation")
    research_context: str = Field(..., description="Context about research needs")
    section_type: str = Field(default="argument", description="Section being drafted")
    include_facts: bool = Field(True, description="Search case facts")
    include_depositions: bool = Field(True, description="Search depositions")
    include_exhibits: bool = Field(True, description="Search exhibits")
    include_statutes: bool = Field(True, description="Search Florida statutes")
    include_regulations: bool = Field(True, description="Search FMCSR")
    max_results_per_type: int = Field(5, description="Max results per evidence type")


class EnhancedResearchResponse(BaseModel):
    """Response model for enhanced RAG research"""

    case_facts: List[Dict[str, Any]] = Field(default_factory=list)
    deposition_testimony: List[Dict[str, Any]] = Field(default_factory=list)
    exhibits: List[Dict[str, Any]] = Field(default_factory=list)
    florida_statutes: List[Dict[str, Any]] = Field(default_factory=list)
    fmcsr_regulations: List[Dict[str, Any]] = Field(default_factory=list)
    case_documents: List[Dict[str, Any]] = Field(default_factory=list)
    research_summary: str = ""
    total_results: int = 0
    search_strategy: Dict[str, Any] = Field(default_factory=dict)
    case_isolation_verified: bool = True


class EnhancedRAGResearchAgent:
    """
    Enhanced RAG agent with case isolation and shared knowledge integration
    """

    def __init__(self):
        """Initialize enhanced RAG research agent"""
        self.vector_store = QdrantVectorStore()
        self.embedding_generator = EmbeddingGenerator()

        # Initialize models
        self.rag_model = OpenAIModel(settings.ai.rag_agent_model)

        # Initialize agents
        self.query_optimizer = self._create_enhanced_query_optimizer()
        self.result_synthesizer = self._create_result_synthesizer()

        # Initialize shared knowledge loaders lazily
        self._florida_statutes_loader = None
        self._fmcsr_loader = None

        logger.info("EnhancedRAGResearchAgent initialized")

    @property
    def florida_statutes_loader(self):
        """Lazy load Florida statutes loader."""
        if self._florida_statutes_loader is None:
            self._florida_statutes_loader = FloridaStatutesLoader()
        return self._florida_statutes_loader

    @property
    def fmcsr_loader(self):
        """Lazy load FMCSR loader."""
        if self._fmcsr_loader is None:
            self._fmcsr_loader = FMCSRLoader()
        return self._fmcsr_loader

    def _create_enhanced_query_optimizer(self) -> Agent:
        """Create enhanced query optimizer with case awareness"""
        return Agent(
            self.rag_model,
            system_prompt="""You are an expert legal research query optimizer with case isolation awareness.

## YOUR ROLE
Transform questions into targeted search queries while respecting case boundaries.

## QUERY OPTIMIZATION STRATEGY
1. **Case-Specific Queries**: Focus on case facts, evidence, testimony
2. **Legal Authority Queries**: Target statutes, regulations, precedents
3. **Evidence-Focused**: Prioritize concrete, citable evidence

## OUTPUT FORMAT
For each question, generate 2-3 optimized queries targeting different evidence types:

Example:
Input: "What evidence shows the driver was fatigued?"
Output:
1. "driver fatigue hours service logbook violation" (for facts/documents)
2. "tired sleepy exhausted deposition testimony" (for depositions)
3. "395.8 hours of service violation FMCSR" (for regulations)

## EVIDENCE KEYWORDS TO INCLUDE
- Facts: "incident", "occurred", "timeline", specific dates
- Depositions: "testified", "deposition", "page line", deponent names
- Exhibits: "exhibit", "Ex.", exhibit numbers, "photo", "video"
- Statutes: "Fla. Stat.", section numbers, "negligence", "liability"
- Regulations: "CFR", "FMCSR", "Part 395", "violation"

Generate targeted, evidence-specific queries.""",
        )

    def _create_result_synthesizer(self) -> Agent:
        """Create agent to synthesize results from multiple sources"""
        return Agent(
            self.rag_model,
            system_prompt="""You are a legal research synthesizer who combines evidence from multiple sources.

## YOUR ROLE
Synthesize research results while maintaining clear source attribution.

## SYNTHESIS PRINCIPLES
1. **Source Attribution**: Always indicate where information came from
2. **Evidence Hierarchy**: Prioritize direct evidence over general principles
3. **Citation Format**: Provide proper legal citations
4. **Coherent Narrative**: Create logical flow between different evidence types

## SOURCE TYPES TO SYNTHESIZE
- Case Facts: Specific events, timeline, parties involved
- Deposition Testimony: Witness statements with page:line citations
- Exhibits: Physical evidence, documents, photos
- Florida Statutes: Applicable state law
- FMCSR: Federal regulations for commercial vehicles
- Case Documents: Original filings, reports, communications

Create concise, well-attributed summaries that support legal arguments.""",
        )

    async def research(
        self, request: EnhancedResearchRequest
    ) -> EnhancedResearchResponse:
        """Perform enhanced research with case isolation"""
        logger.info(f"Starting enhanced research for case: {request.case_name}")

        # Initialize case isolation
        isolation_config = CaseIsolationConfig(
            case_name=request.case_name, enable_shared_knowledge=True, audit_access=True
        )

        # Initialize response
        response = EnhancedResearchResponse(
            case_name=request.case_name,
            search_strategy={"questions": request.questions, "databases_searched": []},
        )

        # Optimize queries for each question
        all_results = []

        for question in request.questions:
            # Generate optimized queries
            optimized_queries = await self._optimize_query(
                question, request.research_context
            )

            # Search case-specific databases
            if any(
                [
                    request.include_facts,
                    request.include_depositions,
                    request.include_exhibits,
                ]
            ):
                case_results = await self._search_case_databases(
                    request.case_name, optimized_queries, request
                )
                all_results.extend(case_results)

            # Search shared knowledge bases
            if request.include_statutes or request.include_regulations:
                shared_results = await self._search_shared_knowledge(
                    optimized_queries, request
                )
                all_results.extend(shared_results)

        # Organize results by type
        response = self._organize_results(all_results, response)

        # Generate research summary
        response.research_summary = await self._synthesize_results(
            all_results, request.questions
        )
        response.total_results = len(all_results)

        # Verify case isolation
        response.case_isolation_verified = self._verify_case_isolation(
            all_results, request.case_name
        )

        logger.info(f"Research completed: {response.total_results} results found")
        return response

    async def _optimize_query(self, question: str, context: str) -> List[str]:
        """Optimize a single question into multiple search queries"""
        prompt = f"Question: {question}\nContext: {context}"

        try:
            result = await self.query_optimizer.run(prompt)
            # Split result into individual queries
            queries = [q.strip() for q in result.data.split("\n") if q.strip()]
            return queries[:3]  # Limit to 3 queries per question
        except Exception as e:
            logger.error(f"Query optimization failed: {e}")
            return [question]  # Fallback to original question

    async def _search_case_databases(
        self, case_name: str, queries: List[str], request: EnhancedResearchRequest
    ) -> List[EnhancedResearchResult]:
        """Search case-specific databases"""
        results = []

        # Initialize case-specific extractors
        fact_extractor = FactExtractor(case_name)
        deposition_parser = DepositionParser(case_name)
        exhibit_indexer = ExhibitIndexer(case_name)

        for query in queries:
            # Search facts
            if request.include_facts:
                facts = await fact_extractor.search_facts(
                    query, limit=request.max_results_per_type
                )
                for fact in facts:
                    results.append(
                        EnhancedResearchResult(
                            content=fact.content,
                            source_type="fact",
                            source_identifier=fact.id,
                            source_collection=f"{case_name}_facts",
                            case_name=case_name,
                            score=fact.confidence_score,
                            metadata={
                                "category": fact.category,
                                "source_document": fact.source_document,
                                "extraction_date": fact.extraction_timestamp.isoformat(),
                            },
                            suggested_citation=f"Case Fact from {fact.source_document}",
                        )
                    )

            # Search depositions
            if request.include_depositions:
                depositions = await deposition_parser.search_testimony(
                    query, limit=request.max_results_per_type
                )
                for depo in depositions:
                    results.append(
                        EnhancedResearchResult(
                            content=depo.testimony_excerpt,
                            source_type="deposition",
                            source_identifier=depo.id,
                            source_collection=f"{case_name}_depositions",
                            case_name=case_name,
                            score=0.8,  # Default score
                            metadata={
                                "deponent": depo.deponent_name,
                                "page": depo.page_start,
                                "line": depo.line_start,
                            },
                            suggested_citation=depo.citation_format,
                        )
                    )

            # Search exhibits
            if request.include_exhibits:
                exhibits = await exhibit_indexer.search_exhibits(
                    query, limit=request.max_results_per_type
                )
                for exhibit in exhibits:
                    results.append(
                        EnhancedResearchResult(
                            content=exhibit.description,
                            source_type="exhibit",
                            source_identifier=exhibit.id,
                            source_collection=f"{case_name}_exhibits",
                            case_name=case_name,
                            score=exhibit.relevance_score,
                            metadata={
                                "exhibit_number": exhibit.exhibit_number,
                                "document_type": exhibit.document_type,
                                "pages": exhibit.page_references,
                            },
                            suggested_citation=exhibit.exhibit_number,
                        )
                    )

        return results

    async def _search_shared_knowledge(
        self, queries: List[str], request: EnhancedResearchRequest
    ) -> List[EnhancedResearchResult]:
        """Search shared knowledge bases"""
        results = []

        for query in queries:
            # Search Florida statutes
            if request.include_statutes:
                statutes = await self.florida_statutes_loader.search_statutes(
                    query, limit=request.max_results_per_type
                )
                for statute in statutes:
                    results.append(
                        EnhancedResearchResult(
                            content=statute.content,
                            source_type="statute",
                            source_identifier=statute.identifier,
                            source_collection="florida_statutes",
                            case_name=None,  # Shared knowledge
                            score=0.9,  # High confidence for statutes
                            metadata={"title": statute.title, "topics": statute.topics},
                            suggested_citation=statute.identifier,
                        )
                    )

            # Search FMCSR
            if request.include_regulations:
                regulations = await self.fmcsr_loader.search_regulations(
                    query, limit=request.max_results_per_type
                )
                for reg in regulations:
                    results.append(
                        EnhancedResearchResult(
                            content=reg.content,
                            source_type="regulation",
                            source_identifier=reg.identifier,
                            source_collection="fmcsr_regulations",
                            case_name=None,  # Shared knowledge
                            score=0.9,  # High confidence for regulations
                            metadata={"title": reg.title, "topics": reg.topics},
                            suggested_citation=reg.identifier,
                        )
                    )

        return results

    def _organize_results(
        self, results: List[EnhancedResearchResult], response: EnhancedResearchResponse
    ) -> EnhancedResearchResponse:
        """Organize results by type"""
        for result in results:
            result_dict = {
                "content": result.content,
                "citation": result.suggested_citation,
                "score": result.score,
                "metadata": result.metadata,
            }

            if result.source_type == "fact":
                response.case_facts.append(result_dict)
            elif result.source_type == "deposition":
                response.deposition_testimony.append(result_dict)
            elif result.source_type == "exhibit":
                response.exhibits.append(result_dict)
            elif result.source_type == "statute":
                response.florida_statutes.append(result_dict)
            elif result.source_type == "regulation":
                response.fmcsr_regulations.append(result_dict)
            else:
                response.case_documents.append(result_dict)

        # Update search strategy
        response.search_strategy["databases_searched"] = list(
            set([r.source_collection for r in results])
        )

        return response

    async def _synthesize_results(
        self, results: List[EnhancedResearchResult], questions: List[str]
    ) -> str:
        """Synthesize results into coherent summary"""
        if not results:
            return "No relevant results found for the research questions."

        # Group results by source type
        by_type = {}
        for result in results:
            if result.source_type not in by_type:
                by_type[result.source_type] = []
            by_type[result.source_type].append(result)

        # Create synthesis prompt
        synthesis_parts = []

        if "fact" in by_type:
            synthesis_parts.append(
                f"CASE FACTS ({len(by_type['fact'])} found):\n"
                + "\n".join([f"- {r.content[:200]}..." for r in by_type["fact"][:3]])
            )

        if "deposition" in by_type:
            synthesis_parts.append(
                f"DEPOSITION TESTIMONY ({len(by_type['deposition'])} found):\n"
                + "\n".join(
                    [
                        f"- {r.suggested_citation}: {r.content[:150]}..."
                        for r in by_type["deposition"][:3]
                    ]
                )
            )

        if "exhibit" in by_type:
            synthesis_parts.append(
                f"EXHIBITS ({len(by_type['exhibit'])} found):\n"
                + "\n".join(
                    [
                        f"- {r.suggested_citation}: {r.content}"
                        for r in by_type["exhibit"][:3]
                    ]
                )
            )

        if "statute" in by_type or "regulation" in by_type:
            synthesis_parts.append(
                "LEGAL AUTHORITIES:\n"
                + "\n".join(
                    [
                        f"- {r.suggested_citation}: {r.metadata.get('title', '')}"
                        for r in results
                        if r.source_type in ["statute", "regulation"]
                    ][:5]
                )
            )

        prompt = f"""Synthesize these research results to answer the questions:
Questions: {", ".join(questions)}

Results:
{chr(10).join(synthesis_parts)}

Create a concise summary that connects the evidence to answer the questions."""

        try:
            result = await self.result_synthesizer.run(prompt)
            return result.data
        except Exception as e:
            logger.error(f"Result synthesis failed: {e}")
            return f"Found {len(results)} relevant results across multiple sources."

    def _verify_case_isolation(
        self, results: List[EnhancedResearchResult], expected_case: str
    ) -> bool:
        """Verify all case-specific results are from the correct case"""
        for result in results:
            if result.case_name is not None and result.case_name != expected_case:
                logger.error(
                    f"Case isolation violation: Expected {expected_case}, got {result.case_name}"
                )
                return False
        return True


# Create singleton instance for backward compatibility
# Use lazy initialization to avoid connecting during import
_enhanced_rag_agent = None


def get_enhanced_rag_agent():
    """Get the singleton instance of EnhancedRAGResearchAgent."""
    global _enhanced_rag_agent
    if _enhanced_rag_agent is None:
        _enhanced_rag_agent = EnhancedRAGResearchAgent()
    return _enhanced_rag_agent


# For backward compatibility, create a property-based access
class _LazyRAGAgent:
    def __getattr__(self, name):
        return getattr(get_enhanced_rag_agent(), name)


enhanced_rag_agent = _LazyRAGAgent()
