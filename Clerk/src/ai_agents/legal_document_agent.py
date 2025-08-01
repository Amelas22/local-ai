"""
Legal Document AI Agent using PydanticAI
Provides intelligent Q&A for legal documents with strict case isolation.
"""

from typing import List, Dict, Any, Optional, Tuple
from datetime import datetime
from dataclasses import dataclass

from pydantic import BaseModel, Field
from pydantic_ai import Agent, RunContext
from pydantic_ai.models.openai import OpenAIModel
from src.vector_storage.qdrant_store import QdrantVectorStore
from src.vector_storage.embeddings import EmbeddingGenerator
from src.utils.logger import get_logger

logger = get_logger(__name__)


# Pydantic models for structured data
class DocumentReference(BaseModel):
    """Reference to a source document"""

    document_id: str
    document_name: str
    page_number: Optional[int] = None
    excerpt: str = Field(..., description="Relevant excerpt from the document")
    relevance_score: float = Field(..., ge=0.0, le=1.0)


class LegalResponse(BaseModel):
    """Structured response from the legal AI agent"""

    answer: str = Field(..., description="The main answer to the user's question")
    confidence: float = Field(
        ..., ge=0.0, le=1.0, description="Confidence in the answer"
    )
    sources: List[DocumentReference] = Field(default_factory=list)
    legal_disclaimers: List[str] = Field(default_factory=list)
    suggested_follow_ups: List[str] = Field(default_factory=list)


@dataclass
class LegalContext:
    """Context for legal document queries"""

    database_name: str
    user_id: str
    query_timestamp: datetime
    vector_store: QdrantVectorStore
    embedding_generator: EmbeddingGenerator


# System prompt for the legal AI agent
LEGAL_AI_SYSTEM_PROMPT = """
You are an expert legal AI assistant specializing in analyzing case documents and providing accurate, well-sourced answers to legal questions.

CRITICAL REQUIREMENTS:
1. ONLY use information from the provided document sources
2. NEVER create fictional legal citations or make up case law
3. Always cite specific documents when making claims
4. If you don't have sufficient information, clearly state this
5. Include appropriate legal disclaimers
6. Format citations in proper Bluebook style when applicable

RESPONSE GUIDELINES:
- Provide clear, concise answers
- Include confidence levels for your responses
- Cite specific document excerpts
- Suggest relevant follow-up questions
- Always maintain attorney-client privilege considerations

CASE CONTEXT:
You are analyzing documents for a specific legal case. All responses must be based solely on the documents provided in the current case file.
"""

# Initialize the PydanticAI agent
legal_agent = Agent(
    model=OpenAIModel("gpt-4o-mini"),  # Using cost-effective model for production
    result_type=LegalResponse,
    system_prompt=LEGAL_AI_SYSTEM_PROMPT,
    deps_type=LegalContext,
)


@legal_agent.tool
async def search_case_documents(
    ctx: RunContext[LegalContext],
    query: str,
    document_type: Optional[str] = None,
    date_range: Optional[str] = None,
) -> str:
    """
    Search for relevant documents using hybrid search with semantic, keyword, and citation matching.

    Args:
        ctx: The run context containing database information
        query: The search query
        document_type: Optional filter for document type (e.g., "motion", "deposition", "medical_record")
        date_range: Optional date range filter (e.g., "2023-01-01 to 2023-12-31")

    Returns:
        Formatted search results with document excerpts and metadata
    """
    try:
        logger.info(
            f"Searching documents for database: {ctx.deps.database_name}, query: {query}"
        )

        # Generate embedding for the query
        query_embedding, token_count = ctx.deps.embedding_generator.generate_embedding(
            query
        )

        # Use hybrid search with reranking
        search_results = await ctx.deps.vector_store.hybrid_search(
            collection_name="documents",
            query=query,
            query_embedding=query_embedding,
            limit=20,
            final_limit=5,
            enable_reranking=True,
        )

        if not search_results:
            return f"No relevant documents found for query: '{query}' in database {ctx.deps.database_name}"

        # Format results for the AI
        formatted_results = []
        for i, result in enumerate(search_results):  # Already limited by final_limit
            source_info = f"""
SOURCE {i + 1} ({result.search_type.upper()} SEARCH):
Document: {result.metadata.get("document_name", "Unknown")}
Document ID: {result.document_id}
Case: {result.case_name}
Page: {result.metadata.get("page_number", "N/A")}
Relevance Score: {result.score:.3f}
Search Type: {result.search_type}
Content: {result.content}

---
"""
            formatted_results.append(source_info)

        return "\n".join(formatted_results)

    except Exception as e:
        logger.error(f"Error searching documents: {str(e)}")
        return f"Error occurred while searching documents: {str(e)}"


@legal_agent.tool
async def get_document_details(ctx: RunContext[LegalContext], document_id: str) -> str:
    """
    Get detailed information about a specific document.

    Args:
        ctx: The run context
        document_id: The ID of the document to retrieve

    Returns:
        Detailed document information
    """
    try:
        # Search for document by ID to get metadata
        search_results = await ctx.deps.vector_store.hybrid_search(
            collection_name="documents",
            query=f"document_id:{document_id}",
            query_embedding=ctx.deps.embedding_generator.generate_embedding(
                document_id
            ),
            limit=1,
            final_limit=1,
            enable_reranking=False,
        )

        if not search_results:
            return (
                f"Document {document_id} not found in database {ctx.deps.database_name}"
            )

        result = search_results[0]
        metadata = result.metadata

        return f"""
DOCUMENT DETAILS:
ID: {result.document_id}
Name: {metadata.get("document_name", "Unknown")}
Type: {metadata.get("document_type", "Unknown")}
Case: {result.case_name}
Date Filed: {metadata.get("date_filed", "Unknown")}
Pages: {metadata.get("page_count", "Unknown")}
Size: {metadata.get("file_size", "Unknown")}
Path: {metadata.get("document_path", "Unknown")}
Subfolder: {metadata.get("subfolder", "Unknown")}
Indexed: {metadata.get("indexed_at", "Unknown")}
"""

    except Exception as e:
        logger.error(f"Error getting document details: {str(e)}")
        return f"Error retrieving document details: {str(e)}"


class LegalDocumentAgent:
    """Main class for the Legal Document AI Agent"""

    def __init__(self, database_name: str = "cerrtio_v_test"):
        """
        Initialize the legal document agent with database-specific access.

        Args:
            database_name: The database name for case-specific collection access
        """
        self.database_name = database_name
        self.vector_store = QdrantVectorStore(database_name=database_name)
        self.embedding_generator = EmbeddingGenerator()
        logger.info(f"Legal Document Agent initialized for database: {database_name}")

    def index_document(self, document: Dict[str, Any], folder_name: str):
        """Index a document in the vector database with folder-based isolation"""
        # Generate embeddings
        embeddings = self.embedding_generator.generate_embedding([document["content"]])
        document["embedding"] = embeddings[0]

        # Index in vector store
        self.vector_store.index_document(folder_name, document)

        logger.info(f"Indexed document in folder '{folder_name}'")

    def generate_embedding(self, text: str) -> Tuple[List[float], int]:
        """Generate embedding for a single text"""
        return self.embedding_generator.generate_embedding(text)

    async def query_documents(
        self, user_query: str, user_id: str, context: Optional[Dict[str, Any]] = None
    ) -> LegalResponse:
        """
        Query the legal documents and get an AI-powered response.

        Args:
            user_query: The user's question about the case
            user_id: ID of the user making the query
            context: Optional additional context

        Returns:
            Structured legal response with sources and confidence
        """
        try:
            # Create legal context
            legal_context = LegalContext(
                database_name=self.database_name,
                user_id=user_id,
                query_timestamp=datetime.now(),
                vector_store=self.vector_store,
                embedding_generator=self.embedding_generator,
            )

            # Run the agent with the user query
            result = await legal_agent.run(user_prompt=user_query, deps=legal_context)

            # Add legal disclaimers
            if not result.data.legal_disclaimers:
                result.data.legal_disclaimers = [
                    "This AI analysis is for informational purposes only and does not constitute legal advice.",
                    "All information is based solely on the documents in this specific case file.",
                    "Please consult with a qualified attorney for legal guidance.",
                ]

            # Log the interaction for audit purposes
            logger.info(
                f"Query processed for user {user_id} in database {self.database_name}"
            )
            logger.debug(f"Query: {user_query[:100]}...")
            logger.debug(f"Sources found: {len(result.data.sources)}")

            return result.data

        except Exception as e:
            logger.error(f"Error processing query: {str(e)}")
            # Return error response in expected format
            return LegalResponse(
                answer=f"I encountered an error while processing your query: {str(e)}",
                confidence=0.0,
                sources=[],
                legal_disclaimers=[
                    "An error occurred while processing your request.",
                    "Please try rephrasing your question or contact support.",
                ],
                suggested_follow_ups=[],
            )

    async def get_case_summary(self, user_id: str) -> LegalResponse:
        """
        Get a comprehensive summary of the case.

        Args:
            user_id: ID of the user requesting the summary

        Returns:
            Case summary with key information
        """
        try:
            # Get case statistics first
            case_stats = self.vector_store.get_folder_statistics(self.database_name)

            summary_query = """
            Provide a comprehensive overview of this case including:
            1. Key parties involved
            2. Main legal issues and claims
            3. Important dates and timeline
            4. Current status
            5. Key documents filed
            """

            return await self.query_documents(summary_query, user_id)

        except Exception as e:
            logger.error(f"Error generating case summary: {str(e)}")
            return LegalResponse(
                answer="Unable to generate case summary at this time.",
                confidence=0.0,
                sources=[],
                legal_disclaimers=["Error occurred while generating summary."],
                suggested_follow_ups=[],
            )

    def get_health_status(self) -> Dict[str, Any]:
        """
        Get the health status of the agent and its dependencies.

        Returns:
            Health status information
        """
        try:
            # Check vector store connection by verifying we can get collections
            self.vector_store.client.get_collections()
            vector_store_healthy = True

            # Get database statistics
            db_stats = self.vector_store.get_folder_statistics(self.database_name)

            return {
                "status": "healthy" if vector_store_healthy else "unhealthy",
                "database_name": self.database_name,
                "vector_store_healthy": vector_store_healthy,
                "database_statistics": db_stats,
                "timestamp": datetime.now().isoformat(),
            }

        except Exception as e:
            logger.error(f"Health check failed: {str(e)}")
            return {
                "status": "error",
                "error": str(e),
                "timestamp": datetime.now().isoformat(),
            }


# Singleton instance for the default database
legal_document_agent = LegalDocumentAgent("cerrtio_v_test")
