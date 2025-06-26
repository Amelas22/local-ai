"""
Motion Drafter AI Agent using PydanticAI
Provides intelligent motion drafting capabilities with hybrid search for legal research.
"""

import logging
import asyncio
from typing import List, Dict, Any, Optional, Union
from datetime import datetime
from dataclasses import dataclass

from pydantic import BaseModel, Field
from pydantic_ai import Agent, RunContext
from pydantic_ai.models.openai import OpenAIModel
from src.vector_storage.qdrant_store import QdrantVectorStore
from src.vector_storage.embeddings import EmbeddingGenerator
from src.utils.logger import get_logger
from config import settings

logger = get_logger(__name__)

# Pydantic models for motion drafting
class MotionSection(BaseModel):
    """A section of a legal motion"""
    heading: str = Field(..., description="Section heading")
    content: str = Field(..., description="Section content")
    citations: List[str] = Field(default_factory=list, description="Legal citations for this section")
    supporting_documents: List[str] = Field(default_factory=list, description="Supporting document references")

class MotionOutline(BaseModel):
    """Complete motion outline structure"""
    motion_type: str = Field(..., description="Type of motion (e.g., Summary Judgment, Motion to Dismiss)")
    title: str = Field(..., description="Full motion title")
    sections: List[MotionSection] = Field(..., description="Motion sections in order")
    key_arguments: List[str] = Field(default_factory=list, description="Key legal arguments")
    supporting_evidence: List[str] = Field(default_factory=list, description="Key evidence references")
    estimated_length: int = Field(..., description="Estimated pages for full motion")

class MotionDraft(BaseModel):
    """Complete motion draft"""
    outline: MotionOutline = Field(..., description="Motion outline")
    full_text: str = Field(..., description="Complete motion text")
    word_count: int = Field(..., description="Total word count")
    legal_standard: str = Field(..., description="Legal standard applied")
    research_notes: List[str] = Field(default_factory=list, description="Research notes and considerations")

@dataclass
class MotionContext:
    """Context for motion drafting"""
    database_name: str
    user_id: str
    motion_type: str
    query_timestamp: datetime
    vector_store: QdrantVectorStore
    embedding_generator: EmbeddingGenerator

# System prompt for motion drafting agent
MOTION_DRAFTER_SYSTEM_PROMPT = """
You are an expert legal motion drafter specializing in creating comprehensive legal motions with proper research and citations.

CRITICAL REQUIREMENTS:
1. ONLY use information from the provided document sources
2. Create well-structured motions following standard legal format
3. Include proper legal citations in Bluebook format
4. Base all arguments on factual evidence from case documents
5. Follow jurisdiction-specific procedural rules
6. Include relevant legal standards and precedents

MOTION STRUCTURE:
- Caption and case information
- Introduction and procedural history
- Statement of facts
- Legal standard
- Argument sections with supporting law
- Conclusion and prayer for relief

RESEARCH GUIDELINES:
- Search for relevant case documents first
- Identify key facts and legal issues
- Find supporting evidence and precedents
- Analyze opposing counsel's arguments
- Develop counterarguments based on evidence

Always maintain the highest standards of legal writing and ethical practice.
"""

# Initialize the motion drafting agent
motion_agent = Agent(
    model=OpenAIModel('gpt-4o'),  # Use more powerful model for complex legal drafting
    result_type=MotionDraft,
    system_prompt=MOTION_DRAFTER_SYSTEM_PROMPT,
    deps_type=MotionContext
)

@motion_agent.tool
async def research_case_law(
    ctx: RunContext[MotionContext],
    legal_query: str,
    motion_focus: Optional[str] = None
) -> str:
    """
    Research case law and precedents relevant to the motion.
    
    Args:
        ctx: Motion context
        legal_query: Legal research query
        motion_focus: Specific focus area for the motion
        
    Returns:
        Formatted research results with case law and precedents
    """
    try:
        logger.info(f"Researching case law for: {legal_query}")
        
        # Generate embedding for legal research
        query_embedding, _ = ctx.deps.embedding_generator.generate_embedding(legal_query)
        
        # Use hybrid search to find relevant legal documents
        search_results = await ctx.deps.vector_store.hybrid_search(
            collection_name="documents",
            query=legal_query,
            query_embedding=query_embedding,
            limit=15,
            final_limit=8,
            enable_reranking=True
        )
        
        if not search_results:
            return f"No relevant case law found for query: '{legal_query}'"
        
        # Format research results
        research_summary = []
        for i, result in enumerate(search_results):
            research_info = f"""
RESEARCH SOURCE {i+1} ({result.search_type.upper()}):
Document: {result.metadata.get('document_name', 'Unknown')}
Document Type: {result.metadata.get('document_type', 'Unknown')}
Relevance: {result.score:.3f}
Content: {result.content}

Legal Analysis:
- Citations Found: {result.metadata.get('has_citations', False)}
- Monetary Values: {result.metadata.get('has_monetary', False)}
- Date References: {result.metadata.get('has_dates', False)}

---
"""
            research_summary.append(research_info)
        
        return "\n".join(research_summary)
        
    except Exception as e:
        logger.error(f"Error in case law research: {str(e)}")
        return f"Error occurred during legal research: {str(e)}"

@motion_agent.tool
async def analyze_opposing_motion(
    ctx: RunContext[MotionContext],
    opposing_motion_text: str
) -> str:
    """
    Analyze opposing counsel's motion to identify key arguments and weaknesses.
    
    Args:
        ctx: Motion context
        opposing_motion_text: Text of opposing motion to analyze
        
    Returns:
        Analysis of opposing motion with counterargument opportunities
    """
    try:
        logger.info("Analyzing opposing motion for counterarguments")
        
        # Search for documents that contradict or support opposing arguments
        contradiction_query = f"evidence contradicting: {opposing_motion_text[:500]}"
        query_embedding, _ = ctx.deps.embedding_generator.generate_embedding(contradiction_query)
        
        contradictory_evidence = await ctx.deps.vector_store.hybrid_search(
            collection_name="documents",
            query=contradiction_query,
            query_embedding=query_embedding,
            limit=10,
            final_limit=5,
            enable_reranking=True
        )
        
        # Search for supporting evidence for our position
        support_query = f"evidence supporting our position against: {opposing_motion_text[:500]}"
        support_embedding, _ = ctx.deps.embedding_generator.generate_embedding(support_query)
        
        supporting_evidence = await ctx.deps.vector_store.hybrid_search(
            collection_name="documents",
            query=support_query,
            query_embedding=support_embedding,
            limit=10,
            final_limit=5,
            enable_reranking=True
        )
        
        # Format analysis
        analysis_sections = []
        
        if contradictory_evidence:
            analysis_sections.append("CONTRADICTORY EVIDENCE FOUND:")
            for i, result in enumerate(contradictory_evidence):
                analysis_sections.append(f"""
Evidence {i+1}:
Source: {result.metadata.get('document_name', 'Unknown')}
Type: {result.search_type}
Relevance: {result.score:.3f}
Content: {result.content}
""")
        
        if supporting_evidence:
            analysis_sections.append("\nSUPPORTING EVIDENCE FOR OUR POSITION:")
            for i, result in enumerate(supporting_evidence):
                analysis_sections.append(f"""
Support {i+1}:
Source: {result.metadata.get('document_name', 'Unknown')}
Type: {result.search_type}
Relevance: {result.score:.3f}
Content: {result.content}
""")
        
        return "\n".join(analysis_sections) if analysis_sections else "No specific contradictory or supporting evidence found in case documents."
        
    except Exception as e:
        logger.error(f"Error analyzing opposing motion: {str(e)}")
        return f"Error occurred while analyzing opposing motion: {str(e)}"

@motion_agent.tool
async def gather_factual_evidence(
    ctx: RunContext[MotionContext],
    fact_pattern: str,
    evidence_type: Optional[str] = None
) -> str:
    """
    Gather factual evidence from case documents to support motion arguments.
    
    Args:
        ctx: Motion context
        fact_pattern: Pattern of facts to search for
        evidence_type: Type of evidence needed (e.g., "medical", "financial", "witness")
        
    Returns:
        Factual evidence with document references
    """
    try:
        logger.info(f"Gathering factual evidence for: {fact_pattern}")
        
        # Create targeted search query
        evidence_query = fact_pattern
        if evidence_type:
            evidence_query = f"{evidence_type} evidence: {fact_pattern}"
        
        query_embedding, _ = ctx.deps.embedding_generator.generate_embedding(evidence_query)
        
        # Search for factual evidence
        evidence_results = await ctx.deps.vector_store.hybrid_search(
            collection_name="documents",
            query=evidence_query,
            query_embedding=query_embedding,
            limit=12,
            final_limit=6,
            enable_reranking=True
        )
        
        if not evidence_results:
            return f"No factual evidence found for: {fact_pattern}"
        
        # Format evidence findings
        evidence_summary = []
        for i, result in enumerate(evidence_results):
            evidence_info = f"""
EVIDENCE {i+1} ({result.search_type.upper()}):
Document: {result.metadata.get('document_name', 'Unknown')}
Document Type: {result.metadata.get('document_type', 'Unknown')}
Page: {result.metadata.get('page_number', 'N/A')}
Strength: {result.score:.3f}
Factual Content: {result.content}

Document Metadata:
- Has Citations: {result.metadata.get('has_citations', False)}
- Has Dates: {result.metadata.get('has_dates', False)}
- Has Monetary Values: {result.metadata.get('has_monetary', False)}

---
"""
            evidence_summary.append(evidence_info)
        
        return "\n".join(evidence_summary)
        
    except Exception as e:
        logger.error(f"Error gathering evidence: {str(e)}")
        return f"Error occurred while gathering evidence: {str(e)}"

class MotionDrafter:
    """Main Motion Drafting Agent"""
    
    def __init__(self, database_name: str):
        """
        Initialize motion drafter for specific database.
        
        Args:
            database_name: Database name for case-specific document access
        """
        self.database_name = database_name
        self.vector_store = QdrantVectorStore(database_name=database_name)
        self.embedding_generator = EmbeddingGenerator()
        logger.info(f"Motion Drafter initialized for database: {database_name}")
    
    async def create_motion_outline(
        self,
        motion_type: str,
        opposing_motion_text: Optional[str] = None,
        key_issues: Optional[List[str]] = None,
        user_id: str = "motion_drafter"
    ) -> MotionOutline:
        """
        Create a comprehensive motion outline.
        
        Args:
            motion_type: Type of motion to draft
            opposing_motion_text: Text of opposing motion (if responding)
            key_issues: Key legal issues to address
            user_id: ID of user requesting the motion
            
        Returns:
            Structured motion outline
        """
        try:
            # Create motion context
            motion_context = MotionContext(
                database_name=self.database_name,
                user_id=user_id,
                motion_type=motion_type,
                query_timestamp=datetime.now(),
                vector_store=self.vector_store,
                embedding_generator=self.embedding_generator
            )
            
            # Build motion prompt
            motion_prompt = f"""
Create a comprehensive outline for a {motion_type}.

Motion Requirements:
- Motion Type: {motion_type}
- Opposing Motion: {'Yes' if opposing_motion_text else 'No'}
- Key Issues: {', '.join(key_issues) if key_issues else 'To be determined from research'}

Please:
1. Research relevant case law and precedents
2. Analyze any opposing arguments (if provided)
3. Gather supporting factual evidence
4. Create a well-structured motion outline
5. Identify key arguments and supporting evidence
6. Estimate the complexity and length of the full motion

Use the research tools to gather evidence and legal precedents before creating the outline.
"""
            
            # Execute with motion agent
            result = await motion_agent.run(
                user_prompt=motion_prompt,
                deps=motion_context
            )
            
            logger.info(f"Motion outline created for {motion_type}")
            return result.data.outline
            
        except Exception as e:
            logger.error(f"Error creating motion outline: {str(e)}")
            raise
    
    async def draft_full_motion(
        self,
        outline: MotionOutline,
        case_caption: str,
        user_id: str = "motion_drafter"
    ) -> MotionDraft:
        """
        Draft a complete motion from an outline.
        
        Args:
            outline: Motion outline to expand into full draft
            case_caption: Case caption for the motion
            user_id: ID of user requesting the motion
            
        Returns:
            Complete motion draft
        """
        try:
            motion_context = MotionContext(
                database_name=self.database_name,
                user_id=user_id,
                motion_type=outline.motion_type,
                query_timestamp=datetime.now(),
                vector_store=self.vector_store,
                embedding_generator=self.embedding_generator
            )
            
            drafting_prompt = f"""
Draft a complete {outline.motion_type} based on the provided outline.

Case Caption: {case_caption}
Motion Type: {outline.motion_type}
Title: {outline.title}

Outline Sections:
{chr(10).join([f"- {section.heading}: {section.content}" for section in outline.sections])}

Key Arguments:
{chr(10).join([f"- {arg}" for arg in outline.key_arguments])}

Requirements:
1. Use proper legal motion format
2. Include comprehensive factual and legal research
3. Cite all sources appropriately
4. Create persuasive legal arguments
5. Follow professional legal writing standards
6. Include proper procedural elements

Research all necessary legal precedents and factual evidence using the available tools.
"""
            
            result = await motion_agent.run(
                user_prompt=drafting_prompt,
                deps=motion_context
            )
            
            logger.info(f"Full motion draft completed: {result.data.word_count} words")
            return result.data
            
        except Exception as e:
            logger.error(f"Error drafting motion: {str(e)}")
            raise
    
    def get_health_status(self) -> Dict[str, Any]:
        """Get health status of the motion drafter"""
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
                    "motion_outline_creation",
                    "full_motion_drafting", 
                    "legal_research",
                    "opposing_motion_analysis",
                    "factual_evidence_gathering"
                ],
                "timestamp": datetime.now().isoformat()
            }
            
        except Exception as e:
            logger.error(f"Motion drafter health check failed: {str(e)}")
            return {
                "status": "error",
                "error": str(e),
                "timestamp": datetime.now().isoformat()
            }

# Default instance
motion_drafter = MotionDrafter("cerrtio_v_test")