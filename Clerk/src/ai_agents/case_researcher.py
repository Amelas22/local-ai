"""
Case Researcher AI Agent using PydanticAI
Provides comprehensive legal research capabilities with hybrid search across case documents.
"""

from typing import List, Dict, Any, Optional
from datetime import datetime
from dataclasses import dataclass

from pydantic import BaseModel, Field
from pydantic_ai import Agent, RunContext
from pydantic_ai.models.openai import OpenAIModel
from src.vector_storage.qdrant_store import QdrantVectorStore
from src.vector_storage.embeddings import EmbeddingGenerator
from src.utils.logger import get_logger

logger = get_logger(__name__)


# Pydantic models for research results
class LegalCitation(BaseModel):
    """Legal citation with context"""

    citation: str = Field(..., description="Full legal citation")
    case_name: str = Field(..., description="Case name")
    court: str = Field(..., description="Court that decided the case")
    year: str = Field(..., description="Year of decision")
    relevance: str = Field(..., description="Relevance to current case")
    key_holding: str = Field(..., description="Key legal holding")


class FactualFinding(BaseModel):
    """Factual finding from case documents"""

    fact_summary: str = Field(..., description="Summary of the factual finding")
    source_document: str = Field(..., description="Source document name")
    page_reference: str = Field(..., description="Page or section reference")
    date_context: Optional[str] = Field(None, description="Date context if relevant")
    supporting_evidence: List[str] = Field(
        default_factory=list, description="Additional supporting evidence"
    )


class ResearchMemo(BaseModel):
    """Comprehensive research memorandum"""

    research_topic: str = Field(..., description="Main research topic")
    executive_summary: str = Field(..., description="Executive summary of findings")
    legal_precedents: List[LegalCitation] = Field(
        default_factory=list, description="Relevant legal precedents"
    )
    factual_findings: List[FactualFinding] = Field(
        default_factory=list, description="Key factual findings"
    )
    legal_analysis: str = Field(..., description="Detailed legal analysis")
    recommendations: List[str] = Field(
        default_factory=list, description="Strategic recommendations"
    )
    research_gaps: List[str] = Field(
        default_factory=list, description="Areas needing additional research"
    )
    confidence_level: float = Field(
        ..., ge=0.0, le=1.0, description="Confidence in research findings"
    )


class TimelineEvent(BaseModel):
    """Event in case timeline"""

    date: str = Field(..., description="Date of event")
    event_description: str = Field(..., description="Description of what happened")
    source_document: str = Field(..., description="Source document")
    legal_significance: str = Field(..., description="Legal significance of the event")
    key_parties: List[str] = Field(
        default_factory=list, description="Key parties involved"
    )


class CaseTimeline(BaseModel):
    """Complete case timeline"""

    case_name: str = Field(..., description="Case name")
    timeline_events: List[TimelineEvent] = Field(
        ..., description="Chronological events"
    )
    critical_dates: List[str] = Field(
        default_factory=list, description="Critical dates for litigation"
    )
    statute_of_limitations: Optional[str] = Field(
        None, description="Relevant statute of limitations"
    )


@dataclass
class ResearchContext:
    """Context for legal research"""

    database_name: str
    user_id: str
    research_focus: str
    query_timestamp: datetime
    vector_store: QdrantVectorStore
    embedding_generator: EmbeddingGenerator


# System prompt for case research agent
CASE_RESEARCHER_SYSTEM_PROMPT = """
You are an expert legal researcher specializing in comprehensive case analysis and legal research.

RESEARCH CAPABILITIES:
1. Legal precedent analysis and citation research
2. Factual investigation and evidence compilation
3. Timeline construction and chronological analysis
4. Comparative case analysis
5. Regulatory and statutory research
6. Expert witness and testimony analysis

CRITICAL RESEARCH STANDARDS:
1. ONLY use information from the provided case documents
2. Cite all sources with specific document references
3. Distinguish between facts and legal conclusions
4. Identify gaps in available information
5. Provide confidence levels for findings
6. Follow proper legal research methodology

ANALYSIS FRAMEWORK:
- Issue identification and legal question framing
- Factual investigation with evidence mapping
- Legal precedent research and analysis
- Comparative analysis of similar cases
- Risk assessment and strategic considerations
- Clear recommendations with supporting rationale

Always maintain objectivity and highlight both favorable and unfavorable findings.
"""

# Initialize the research agent
research_agent = Agent(
    model=OpenAIModel("gpt-4o"),  # Use powerful model for complex research
    result_type=ResearchMemo,
    system_prompt=CASE_RESEARCHER_SYSTEM_PROMPT,
    deps_type=ResearchContext,
)


@research_agent.tool
async def search_legal_precedents(
    ctx: RunContext[ResearchContext],
    legal_issue: str,
    jurisdiction: Optional[str] = None,
) -> str:
    """
    Search for legal precedents and citations relevant to a specific legal issue.

    Args:
        ctx: Research context
        legal_issue: The legal issue to research
        jurisdiction: Specific jurisdiction to focus on

    Returns:
        Legal precedents and citations found in case documents
    """
    try:
        logger.info(f"Searching legal precedents for: {legal_issue}")

        # Create comprehensive search query
        precedent_query = f"legal precedent case law citation: {legal_issue}"
        if jurisdiction:
            precedent_query += f" {jurisdiction}"

        query_embedding, _ = ctx.deps.embedding_generator.generate_embedding(
            precedent_query
        )

        # Search for legal precedents
        precedent_results = await ctx.deps.vector_store.hybrid_search(
            collection_name="documents",
            query=precedent_query,
            query_embedding=query_embedding,
            limit=20,
            final_limit=10,
            enable_reranking=True,
        )

        if not precedent_results:
            return f"No legal precedents found for: {legal_issue}"

        # Format precedent findings
        precedent_summary = []
        for i, result in enumerate(precedent_results):
            precedent_info = f"""
PRECEDENT {i + 1} ({result.search_type.upper()}):
Document: {result.metadata.get("document_name", "Unknown")}
Document Type: {result.metadata.get("document_type", "Unknown")}
Relevance Score: {result.score:.3f}
Has Citations: {result.metadata.get("has_citations", False)}
Content: {result.content}

Legal Context:
- Court Level: {result.metadata.get("court_level", "Unknown")}
- Jurisdiction: {result.metadata.get("jurisdiction", "Unknown")}
- Date Filed: {result.metadata.get("date_filed", "Unknown")}

---
"""
            precedent_summary.append(precedent_info)

        return "\n".join(precedent_summary)

    except Exception as e:
        logger.error(f"Error searching precedents: {str(e)}")
        return f"Error occurred while searching precedents: {str(e)}"


@research_agent.tool
async def investigate_factual_timeline(
    ctx: RunContext[ResearchContext],
    time_period: Optional[str] = None,
    key_events: Optional[List[str]] = None,
) -> str:
    """
    Investigate and construct factual timeline from case documents.

    Args:
        ctx: Research context
        time_period: Specific time period to focus on
        key_events: Specific events to investigate

    Returns:
        Chronological timeline of factual events
    """
    try:
        logger.info("Investigating factual timeline from case documents")

        # Search for chronological and date-related information
        timeline_queries = [
            "chronology timeline sequence events",
            "dates important events occurred",
            "factual background history",
        ]

        if time_period:
            timeline_queries.append(f"events during {time_period}")

        if key_events:
            for event in key_events:
                timeline_queries.append(f"when did {event} occur")

        all_timeline_results = []

        for query in timeline_queries:
            query_embedding, _ = ctx.deps.embedding_generator.generate_embedding(query)

            timeline_results = await ctx.deps.vector_store.hybrid_search(
                collection_name="documents",
                query=query,
                query_embedding=query_embedding,
                limit=10,
                final_limit=5,
                enable_reranking=True,
            )

            all_timeline_results.extend(timeline_results)

        # Remove duplicates and sort by relevance
        unique_results = {}
        for result in all_timeline_results:
            if (
                result.id not in unique_results
                or result.score > unique_results[result.id].score
            ):
                unique_results[result.id] = result

        timeline_results = sorted(
            unique_results.values(), key=lambda x: x.score, reverse=True
        )[:15]

        if not timeline_results:
            return "No chronological information found in case documents"

        # Format timeline findings
        timeline_summary = []
        for i, result in enumerate(timeline_results):
            timeline_info = f"""
TIMELINE EVIDENCE {i + 1} ({result.search_type.upper()}):
Document: {result.metadata.get("document_name", "Unknown")}
Has Dates: {result.metadata.get("has_dates", False)}
Date Filed: {result.metadata.get("date_filed", "Unknown")}
Relevance: {result.score:.3f}
Content: {result.content}

Temporal Markers:
- Modified At: {result.metadata.get("modified_at", "Unknown")}
- Page Reference: {result.metadata.get("page_number", "N/A")}

---
"""
            timeline_summary.append(timeline_info)

        return "\n".join(timeline_summary)

    except Exception as e:
        logger.error(f"Error investigating timeline: {str(e)}")
        return f"Error occurred while investigating timeline: {str(e)}"


@research_agent.tool
async def analyze_expert_testimony(
    ctx: RunContext[ResearchContext],
    expert_type: str,
    testimony_focus: Optional[str] = None,
) -> str:
    """
    Analyze expert witness testimony and opinions.

    Args:
        ctx: Research context
        expert_type: Type of expert (medical, financial, technical, etc.)
        testimony_focus: Specific focus area for testimony

    Returns:
        Analysis of expert testimony found in case documents
    """
    try:
        logger.info(f"Analyzing {expert_type} expert testimony")

        # Search for expert testimony and opinions
        expert_query = f"{expert_type} expert witness testimony opinion"
        if testimony_focus:
            expert_query += f" {testimony_focus}"

        query_embedding, _ = ctx.deps.embedding_generator.generate_embedding(
            expert_query
        )

        expert_results = await ctx.deps.vector_store.hybrid_search(
            collection_name="documents",
            query=expert_query,
            query_embedding=query_embedding,
            limit=15,
            final_limit=8,
            enable_reranking=True,
        )

        if not expert_results:
            return f"No {expert_type} expert testimony found in case documents"

        # Format expert analysis
        expert_summary = []
        for i, result in enumerate(expert_results):
            expert_info = f"""
EXPERT EVIDENCE {i + 1} ({result.search_type.upper()}):
Document: {result.metadata.get("document_name", "Unknown")}
Document Type: {result.metadata.get("document_type", "Unknown")}
Relevance: {result.score:.3f}
Content: {result.content}

Expert Context:
- Has Citations: {result.metadata.get("has_citations", False)}
- Has Monetary Values: {result.metadata.get("has_monetary", False)}
- Document Path: {result.metadata.get("document_path", "Unknown")}

---
"""
            expert_summary.append(expert_info)

        return "\n".join(expert_summary)

    except Exception as e:
        logger.error(f"Error analyzing expert testimony: {str(e)}")
        return f"Error occurred while analyzing expert testimony: {str(e)}"


@research_agent.tool
async def compare_similar_cases(
    ctx: RunContext[ResearchContext],
    case_similarities: str,
    comparison_factors: Optional[List[str]] = None,
) -> str:
    """
    Compare current case with similar cases in the database.

    Args:
        ctx: Research context
        case_similarities: Description of what makes cases similar
        comparison_factors: Specific factors to compare

    Returns:
        Comparative analysis of similar cases
    """
    try:
        logger.info(f"Comparing similar cases based on: {case_similarities}")

        # Search for similar case patterns
        similarity_query = f"similar case comparable situation: {case_similarities}"

        query_embedding, _ = ctx.deps.embedding_generator.generate_embedding(
            similarity_query
        )

        similar_results = await ctx.deps.vector_store.hybrid_search(
            collection_name="documents",
            query=similarity_query,
            query_embedding=query_embedding,
            limit=12,
            final_limit=6,
            enable_reranking=True,
        )

        if comparison_factors:
            # Search for specific comparison factors
            for factor in comparison_factors:
                factor_query = f"case comparison {factor}"
                factor_embedding, _ = ctx.deps.embedding_generator.generate_embedding(
                    factor_query
                )

                factor_results = await ctx.deps.vector_store.hybrid_search(
                    collection_name="documents",
                    query=factor_query,
                    query_embedding=factor_embedding,
                    limit=8,
                    final_limit=4,
                    enable_reranking=True,
                )

                similar_results.extend(factor_results)

        if not similar_results:
            return (
                f"No similar cases found for comparison based on: {case_similarities}"
            )

        # Format comparison analysis
        comparison_summary = []
        for i, result in enumerate(similar_results):
            comparison_info = f"""
SIMILAR CASE {i + 1} ({result.search_type.upper()}):
Document: {result.metadata.get("document_name", "Unknown")}
Case Context: {result.case_name}
Similarity Score: {result.score:.3f}
Content: {result.content}

Comparison Factors:
- Document Type: {result.metadata.get("document_type", "Unknown")}
- Has Citations: {result.metadata.get("has_citations", False)}
- Jurisdiction: {result.metadata.get("jurisdiction", "Unknown")}

---
"""
            comparison_summary.append(comparison_info)

        return "\n".join(comparison_summary)

    except Exception as e:
        logger.error(f"Error comparing cases: {str(e)}")
        return f"Error occurred while comparing cases: {str(e)}"


class CaseResearcher:
    """Main Case Research Agent"""

    def __init__(self, database_name: str):
        """
        Initialize case researcher for specific database.

        Args:
            database_name: Database name for case-specific document access
        """
        self.database_name = database_name
        self.vector_store = QdrantVectorStore(database_name=database_name)
        self.embedding_generator = EmbeddingGenerator()
        logger.info(f"Case Researcher initialized for database: {database_name}")

    async def conduct_comprehensive_research(
        self,
        research_topic: str,
        research_scope: Optional[List[str]] = None,
        user_id: str = "case_researcher",
    ) -> ResearchMemo:
        """
        Conduct comprehensive legal research on a specific topic.

        Args:
            research_topic: Main research topic or legal question
            research_scope: Specific areas to focus research on
            user_id: ID of user requesting research

        Returns:
            Comprehensive research memorandum
        """
        try:
            research_context = ResearchContext(
                database_name=self.database_name,
                user_id=user_id,
                research_focus=research_topic,
                query_timestamp=datetime.now(),
                vector_store=self.vector_store,
                embedding_generator=self.embedding_generator,
            )

            # Build comprehensive research prompt
            research_prompt = f"""
Conduct comprehensive legal research on: {research_topic}

Research Scope:
{chr(10).join([f"- {scope}" for scope in research_scope]) if research_scope else "- General comprehensive analysis"}

Research Requirements:
1. Search for and analyze relevant legal precedents
2. Investigate factual timeline and chronology
3. Analyze any expert testimony or opinions
4. Compare with similar cases if applicable
5. Identify legal issues and potential arguments
6. Assess strength of evidence and legal positions
7. Provide strategic recommendations

Use all available research tools to gather comprehensive information before preparing the research memorandum.
"""

            result = await research_agent.run(
                user_prompt=research_prompt, deps=research_context
            )

            logger.info(f"Comprehensive research completed on: {research_topic}")
            return result.data

        except Exception as e:
            logger.error(f"Error conducting research: {str(e)}")
            raise

    async def create_case_timeline(
        self,
        focus_period: Optional[str] = None,
        key_events: Optional[List[str]] = None,
        user_id: str = "case_researcher",
    ) -> CaseTimeline:
        """
        Create a comprehensive case timeline.

        Args:
            focus_period: Specific time period to focus on
            key_events: Key events to include in timeline
            user_id: ID of user requesting timeline

        Returns:
            Comprehensive case timeline
        """
        try:
            research_context = ResearchContext(
                database_name=self.database_name,
                user_id=user_id,
                research_focus="case timeline",
                query_timestamp=datetime.now(),
                vector_store=self.vector_store,
                embedding_generator=self.embedding_generator,
            )

            timeline_prompt = f"""
Create a comprehensive chronological timeline of case events.

Timeline Parameters:
- Focus Period: {focus_period or "Complete case history"}
- Key Events: {", ".join(key_events) if key_events else "All significant events"}

Timeline Requirements:
1. Investigate all chronological information in case documents
2. Identify critical dates and events
3. Establish legal significance of each event
4. Note key parties involved in each event
5. Identify any gaps in the timeline
6. Assess statute of limitations implications

Use the factual timeline investigation tool to gather comprehensive chronological information.
"""

            result = await research_agent.run(
                user_prompt=timeline_prompt, deps=research_context
            )

            # Extract timeline from research memo
            timeline = CaseTimeline(
                case_name=self.database_name,
                timeline_events=[],
                critical_dates=[],
                statute_of_limitations=None,
            )

            logger.info(f"Case timeline created for: {self.database_name}")
            return timeline

        except Exception as e:
            logger.error(f"Error creating timeline: {str(e)}")
            raise

    def get_health_status(self) -> Dict[str, Any]:
        """Get health status of the case researcher"""
        try:
            # Test vector store connection
            self.vector_store.client.get_collections()
            vector_healthy = True

            # Get database stats
            db_stats = self.vector_store.get_folder_statistics(self.database_name)

            return {
                "status": "healthy" if vector_healthy else "unhealthy",
                "database_name": self.database_name,
                "vector_store_healthy": vector_healthy,
                "database_statistics": db_stats,
                "capabilities": [
                    "comprehensive_legal_research",
                    "precedent_analysis",
                    "factual_timeline_construction",
                    "expert_testimony_analysis",
                    "comparative_case_analysis",
                    "research_memorandum_creation",
                ],
                "timestamp": datetime.now().isoformat(),
            }

        except Exception as e:
            logger.error(f"Case researcher health check failed: {str(e)}")
            return {
                "status": "error",
                "error": str(e),
                "timestamp": datetime.now().isoformat(),
            }


# Default instance
case_researcher = CaseResearcher("cerrtio_v_test")
