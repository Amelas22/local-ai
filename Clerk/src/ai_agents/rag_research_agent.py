"""
RAG Research Agent - Intelligent intermediary for database search and context retrieval
Optimizes queries and selects appropriate databases for motion drafting research
"""

import asyncio
import logging
from typing import List, Dict, Any, Optional, Tuple
from dataclasses import dataclass
from enum import Enum

from pydantic_ai import Agent
from pydantic_ai.models.openai import OpenAIModel
from pydantic import BaseModel, Field

from src.vector_storage.qdrant_store import QdrantVectorStore
from src.vector_storage.embeddings import EmbeddingGenerator
from config.settings import settings

# Use the same logger as the main API
logger = logging.getLogger("clerk_api")


class DatabaseType(Enum):
    """Types of databases available for search"""
    CASE_DATABASE = "case_database"
    FIRM_KNOWLEDGE = "firm_knowledge"
    BOTH = "both"


class QueryType(Enum):
    """Types of research queries"""
    LEGAL_PRECEDENTS = "legal_precedents"
    CASE_FACTS = "case_facts"
    EXPERT_EVIDENCE = "expert_evidence"
    REGULATORY_COMPLIANCE = "regulatory_compliance"
    PROCEDURAL_HISTORY = "procedural_history"
    ARGUMENT_STRATEGIES = "argument_strategies"


@dataclass
class ResearchQuery:
    """Optimized research query with metadata"""
    query_text: str
    query_type: QueryType
    database_type: DatabaseType
    priority: int  # 1-5, 5 being highest
    expected_result_type: str
    original_question: str


@dataclass
class ResearchResult:
    """Structured research result with attribution"""
    content: str
    source_document: str
    score: float
    query_type: QueryType
    database_source: DatabaseType
    metadata: Dict[str, Any]


class ResearchRequest(BaseModel):
    """Input request for RAG research"""
    questions: List[str] = Field(..., description="Questions generated from outline")
    database_name: str = Field(..., description="Case database name")
    research_context: str = Field(..., description="Context about what type of research is needed")
    section_type: str = Field(default="argument", description="Type of section being drafted")


class ResearchResponse(BaseModel):
    """Structured response from RAG research"""
    legal_precedents: List[Dict[str, Any]] = Field(default_factory=list)
    case_facts: List[Dict[str, Any]] = Field(default_factory=list)
    expert_evidence: List[Dict[str, Any]] = Field(default_factory=list)
    regulatory_compliance: List[Dict[str, Any]] = Field(default_factory=list)
    procedural_history: List[Dict[str, Any]] = Field(default_factory=list)
    argument_strategies: List[Dict[str, Any]] = Field(default_factory=list)
    research_summary: str = ""
    total_results: int = 0
    search_strategy: Dict[str, Any] = Field(default_factory=dict)


class RAGResearchAgent:
    """
    Intelligent agent that processes outline questions and performs optimized database searches
    """
    
    def __init__(self):
        """Initialize the RAG research agent with separate model"""
        self.vector_store = QdrantVectorStore()
        self.embedding_generator = EmbeddingGenerator()
        
        # Use the dedicated RAG agent model
        self.rag_model = OpenAIModel(settings.ai.rag_agent_model)
        
        # Initialize query optimization agent
        self.query_optimizer = self._create_query_optimizer()
        self.database_selector = self._create_database_selector()
        
        logger.info(f"RAGResearchAgent initialized with model: {settings.ai.rag_agent_model}")

    def _create_query_optimizer(self) -> Agent:
        """Create agent for optimizing search queries"""
        try:
            agent = Agent(
                self.rag_model,
                system_prompt="""You are an expert legal research specialist who optimizes database search queries.

## YOUR ROLE
Transform outline-generated questions into multiple targeted search queries that will find the most relevant information in legal databases.

## QUERY OPTIMIZATION PRINCIPLES
1. **Specificity**: Convert general questions into specific, targeted searches
2. **Keyword Optimization**: Use legal terminology and case-specific terms
3. **Multiple Angles**: Generate 2-3 different query approaches per question
4. **Evidence Focus**: Prioritize queries that find concrete evidence and documentation

## INPUT FORMAT
You'll receive questions like:
- "What dispatch records show about telematics overrides?"
- "How do successful motions argue negligent hiring claims?"
- "What evidence supports the fact that brake failures occurred?"

## OUTPUT FORMAT
For each input question, generate 2-3 optimized search queries:

Example:
Input: "What dispatch records show about telematics overrides?"
Output:
1. "telematics override dispatch communications emails instructions"
2. "driver monitoring system disable fleet management"
3. "safety technology bypass company policy violation"

## GUIDELINES
- Use short, keyword-focused queries for better semantic matching
- Include synonyms and related terms
- Focus on evidence, documentation, and concrete facts
- Remove unnecessary words like "what", "how", "the"
- Prioritize terms that would appear in legal documents

Generate concise, targeted search queries that maximize database retrieval effectiveness.""",
                result_type=str
            )
            logger.info("Query optimizer agent created successfully")
            return agent
        except Exception as e:
            logger.error(f"Failed to create query optimizer agent: {str(e)}")
            raise

    def _create_database_selector(self) -> Agent:
        """Create agent for selecting appropriate databases"""
        try:
            agent = Agent(
                self.rag_model,
                system_prompt="""You are a database selection expert for legal research.

## YOUR ROLE
Analyze research questions and determine which database(s) to search for optimal results.

## DATABASE OPTIONS
1. **CASE_DATABASE**: Contains case-specific facts, evidence, documents, expert reports, depositions
2. **FIRM_KNOWLEDGE**: Contains successful legal arguments, motion strategies, winning approaches
3. **BOTH**: Search both databases when comprehensive coverage is needed

## SELECTION CRITERIA

**Use CASE_DATABASE for:**
- Factual questions about the incident, timeline, evidence
- Document searches (emails, reports, logs, recordings)
- Expert testimony and opinions specific to this case
- Regulatory violations and compliance issues
- Medical records and injury documentation

**Use FIRM_KNOWLEDGE for:**
- Legal argument strategies and structures
- How to cite and apply case law effectively
- Successful motion templates and approaches
- Argument sequencing and persuasive techniques
- How similar cases were won

**Use BOTH for:**
- Complex legal arguments that need both strategy and facts
- Questions that could benefit from multiple perspectives
- When unsure which database has the information

## INPUT FORMAT
Questions like:
- "What dispatch records show about telematics overrides?" → CASE_DATABASE
- "How do successful motions argue negligent hiring?" → FIRM_KNOWLEDGE
- "What evidence supports negligent supervision claims?" → BOTH

## OUTPUT FORMAT
Respond with only: CASE_DATABASE, FIRM_KNOWLEDGE, or BOTH

Make decisions quickly and confidently based on the question type.""",
                result_type=str
            )
            logger.info("Database selector agent created successfully")
            return agent
        except Exception as e:
            logger.error(f"Failed to create database selector agent: {str(e)}")
            raise

    async def research_questions(
        self,
        request: ResearchRequest
    ) -> ResearchResponse:
        """
        Main research method that processes questions and returns structured results
        """
        logger.info(f"[RAG_RESEARCH] Starting research for {len(request.questions)} questions")
        
        response = ResearchResponse()
        response.search_strategy["total_questions"] = len(request.questions)
        response.search_strategy["section_type"] = request.section_type
        
        try:
            # Step 1: Process and optimize all questions
            research_queries = await self._process_questions(request.questions)
            logger.info(f"[RAG_RESEARCH] Generated {len(research_queries)} optimized queries")
            
            # Step 2: Execute searches
            search_results = await self._execute_searches(
                research_queries, 
                request.database_name
            )
            logger.info(f"[RAG_RESEARCH] Executed searches, got {len(search_results)} results")
            
            # Step 3: Categorize and structure results
            response = self._categorize_results(search_results, response)
            
            # Step 4: Generate research summary
            response.research_summary = self._generate_summary(response)
            response.total_results = len(search_results)
            
            logger.info(f"[RAG_RESEARCH] Research completed: {response.total_results} total results")
            
        except Exception as e:
            logger.error(f"[RAG_RESEARCH] Error in research process: {str(e)}", exc_info=True)
            response.research_summary = f"Research partially failed: {str(e)}"
            
        return response

    async def _process_questions(self, questions: List[str]) -> List[ResearchQuery]:
        """Process questions into optimized research queries"""
        research_queries = []
        
        for i, question in enumerate(questions[:10]):  # Limit to 10 questions
            try:
                logger.info(f"[RAG_RESEARCH] Processing question {i+1}: {question[:80]}...")
                
                # Step 1: Optimize the query
                optimized_queries = await self._optimize_query(question)
                
                # Step 2: Select database
                database_type = await self._select_database(question)
                
                # Step 3: Determine query type
                query_type = self._classify_query_type(question)
                
                # Create research queries
                for j, opt_query in enumerate(optimized_queries):
                    research_query = ResearchQuery(
                        query_text=opt_query,
                        query_type=query_type,
                        database_type=database_type,
                        priority=5 - j,  # First query gets highest priority
                        expected_result_type=self._get_expected_result_type(query_type),
                        original_question=question
                    )
                    research_queries.append(research_query)
                    
            except Exception as e:
                logger.error(f"[RAG_RESEARCH] Error processing question '{question[:50]}': {str(e)}")
                continue
        
        # Sort by priority
        research_queries.sort(key=lambda x: x.priority, reverse=True)
        logger.info(f"[RAG_RESEARCH] Created {len(research_queries)} research queries")
        return research_queries[:20]  # Limit total queries

    async def _optimize_query(self, question: str) -> List[str]:
        """Optimize a single question into multiple search queries"""
        try:
            result = await asyncio.wait_for(
                self.query_optimizer.run(f"Optimize this question for database search: {question}"),
                timeout=10.0
            )
            
            optimized_text = str(result.data) if hasattr(result, 'data') else str(result)
            
            # Parse the optimized queries (expecting numbered list or line-separated)
            queries = []
            for line in optimized_text.split('\n'):
                line = line.strip()
                if line and not line.startswith('#'):
                    # Remove numbering if present
                    if line[0].isdigit() and '.' in line[:5]:
                        line = line.split('.', 1)[1].strip()
                    if line and len(line) > 5:
                        queries.append(line.strip('"').strip())
            
            if not queries:
                # Fallback: use the original question
                queries = [question]
            
            logger.info(f"[RAG_RESEARCH] Optimized '{question[:30]}...' into {len(queries)} queries")
            return queries[:3]  # Max 3 optimized queries per question
            
        except Exception as e:
            logger.error(f"[RAG_RESEARCH] Error optimizing query: {str(e)}")
            return [question]  # Fallback to original

    async def _select_database(self, question: str) -> DatabaseType:
        """Select appropriate database for the question"""
        try:
            result = await asyncio.wait_for(
                self.database_selector.run(question),
                timeout=5.0
            )
            
            selection = str(result.data) if hasattr(result, 'data') else str(result)
            selection = selection.strip().upper()
            
            if "CASE_DATABASE" in selection:
                return DatabaseType.CASE_DATABASE
            elif "FIRM_KNOWLEDGE" in selection:
                return DatabaseType.FIRM_KNOWLEDGE
            elif "BOTH" in selection:
                return DatabaseType.BOTH
            else:
                # Default based on question content
                return self._default_database_selection(question)
                
        except Exception as e:
            logger.error(f"[RAG_RESEARCH] Error selecting database: {str(e)}")
            return self._default_database_selection(question)

    def _default_database_selection(self, question: str) -> DatabaseType:
        """Default database selection based on question keywords"""
        question_lower = question.lower()
        
        firm_keywords = ["successful", "motion", "argument", "strategy", "how do", "effective"]
        case_keywords = ["evidence", "document", "record", "fact", "incident", "what happened"]
        
        firm_score = sum(1 for kw in firm_keywords if kw in question_lower)
        case_score = sum(1 for kw in case_keywords if kw in question_lower)
        
        if firm_score > case_score:
            return DatabaseType.FIRM_KNOWLEDGE
        elif case_score > firm_score:
            return DatabaseType.CASE_DATABASE
        else:
            return DatabaseType.BOTH

    def _classify_query_type(self, question: str) -> QueryType:
        """Classify the type of query based on content"""
        question_lower = question.lower()
        
        if any(kw in question_lower for kw in ["precedent", "case", "court", "ruling", "law"]):
            return QueryType.LEGAL_PRECEDENTS
        elif any(kw in question_lower for kw in ["expert", "opinion", "analysis", "reconstruction"]):
            return QueryType.EXPERT_EVIDENCE
        elif any(kw in question_lower for kw in ["regulation", "fmcsr", "dot", "compliance", "violation"]):
            return QueryType.REGULATORY_COMPLIANCE
        elif any(kw in question_lower for kw in ["motion", "filed", "ruling", "discovery", "procedural"]):
            return QueryType.PROCEDURAL_HISTORY
        elif any(kw in question_lower for kw in ["argument", "strategy", "successful", "effective"]):
            return QueryType.ARGUMENT_STRATEGIES
        else:
            return QueryType.CASE_FACTS

    def _get_expected_result_type(self, query_type: QueryType) -> str:
        """Get expected result type for query categorization"""
        mapping = {
            QueryType.LEGAL_PRECEDENTS: "case_law",
            QueryType.CASE_FACTS: "evidence",
            QueryType.EXPERT_EVIDENCE: "expert_opinion",
            QueryType.REGULATORY_COMPLIANCE: "regulation",
            QueryType.PROCEDURAL_HISTORY: "court_filing",
            QueryType.ARGUMENT_STRATEGIES: "legal_strategy"
        }
        return mapping.get(query_type, "general")

    async def _execute_searches(
        self,
        research_queries: List[ResearchQuery],
        case_database_name: str
    ) -> List[ResearchResult]:
        """Execute all research queries against appropriate databases"""
        search_results = []
        
        for i, query in enumerate(research_queries):
            try:
                logger.info(f"[RAG_RESEARCH] Executing query {i+1}/{len(research_queries)}: {query.query_text[:50]}...")
                
                # Generate embedding
                query_embedding, _ = await asyncio.wait_for(
                    self.embedding_generator.generate_embedding_async(query.query_text),
                    timeout=5.0
                )
                
                # Determine which databases to search
                databases_to_search = self._get_databases_to_search(query, case_database_name)
                
                # Execute searches
                for db_name, db_type in databases_to_search:
                    try:
                        results = await asyncio.wait_for(
                            self.vector_store.hybrid_search(
                                collection_name=db_name,
                                query=query.query_text,
                                query_embedding=query_embedding,
                                limit=3,  # Limit per database
                                enable_reranking=False
                            ),
                            timeout=8.0
                        )
                        
                        # Convert to ResearchResult objects
                        for result in results:
                            if result.score > 0.2:  # Reasonable threshold
                                research_result = ResearchResult(
                                    content=result.content[:1000],  # Limit content length
                                    source_document=result.metadata.get("document_name", "Unknown"),
                                    score=result.score,
                                    query_type=query.query_type,
                                    database_source=db_type,
                                    metadata={
                                        **result.metadata,
                                        "original_question": query.original_question,
                                        "optimized_query": query.query_text
                                    }
                                )
                                search_results.append(research_result)
                                logger.info(f"[RAG_RESEARCH] Found result (score: {result.score:.3f}) from {db_name}")
                        
                    except Exception as e:
                        logger.error(f"[RAG_RESEARCH] Error searching {db_name}: {str(e)}")
                        continue
                        
            except Exception as e:
                logger.error(f"[RAG_RESEARCH] Error executing query '{query.query_text[:30]}': {str(e)}")
                continue
        
        logger.info(f"[RAG_RESEARCH] Collected {len(search_results)} total search results")
        return search_results

    def _get_databases_to_search(
        self,
        query: ResearchQuery,
        case_database_name: str
    ) -> List[Tuple[str, DatabaseType]]:
        """Get list of databases to search for this query"""
        databases = []
        
        if query.database_type == DatabaseType.CASE_DATABASE:
            databases.append((case_database_name, DatabaseType.CASE_DATABASE))
        elif query.database_type == DatabaseType.FIRM_KNOWLEDGE:
            databases.append(("firm_knowledge", DatabaseType.FIRM_KNOWLEDGE))
        elif query.database_type == DatabaseType.BOTH:
            databases.append((case_database_name, DatabaseType.CASE_DATABASE))
            databases.append(("firm_knowledge", DatabaseType.FIRM_KNOWLEDGE))
        
        return databases

    def _categorize_results(
        self,
        search_results: List[ResearchResult],
        response: ResearchResponse
    ) -> ResearchResponse:
        """Categorize search results into structured response"""
        
        for result in search_results:
            result_dict = {
                "content": result.content,
                "source": result.source_document,
                "score": result.score,
                "database": result.database_source.value,
                "metadata": result.metadata
            }
            
            # Categorize based on query type
            if result.query_type == QueryType.LEGAL_PRECEDENTS:
                response.legal_precedents.append(result_dict)
            elif result.query_type == QueryType.CASE_FACTS:
                response.case_facts.append(result_dict)
            elif result.query_type == QueryType.EXPERT_EVIDENCE:
                response.expert_evidence.append(result_dict)
            elif result.query_type == QueryType.REGULATORY_COMPLIANCE:
                response.regulatory_compliance.append(result_dict)
            elif result.query_type == QueryType.PROCEDURAL_HISTORY:
                response.procedural_history.append(result_dict)
            elif result.query_type == QueryType.ARGUMENT_STRATEGIES:
                response.argument_strategies.append(result_dict)
        
        # Sort each category by score
        for category in [response.legal_precedents, response.case_facts, response.expert_evidence,
                        response.regulatory_compliance, response.procedural_history, response.argument_strategies]:
            category.sort(key=lambda x: x["score"], reverse=True)
        
        return response

    def _generate_summary(self, response: ResearchResponse) -> str:
        """Generate a summary of research findings"""
        total_results = response.total_results
        
        categories = [
            ("Legal Precedents", len(response.legal_precedents)),
            ("Case Facts", len(response.case_facts)),
            ("Expert Evidence", len(response.expert_evidence)),
            ("Regulatory Compliance", len(response.regulatory_compliance)),
            ("Procedural History", len(response.procedural_history)),
            ("Argument Strategies", len(response.argument_strategies))
        ]
        
        summary_parts = [f"Research completed with {total_results} total results."]
        
        for category_name, count in categories:
            if count > 0:
                summary_parts.append(f"{category_name}: {count} results")
        
        return " | ".join(summary_parts)


# Create global instance
rag_research_agent = RAGResearchAgent()