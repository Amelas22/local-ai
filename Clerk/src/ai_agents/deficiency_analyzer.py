"""
Discovery Deficiency Analyzer

This module analyzes discovery productions to identify gaps between what was
requested in RFPs and what was actually produced. It uses AI agents to:
1. Parse RFP requests and defense responses
2. Search ONLY within the current production batch
3. Determine production status with evidence
4. Generate comprehensive deficiency reports
"""

from typing import List, Dict, Optional, Set
from datetime import datetime
from pydantic_ai import Agent
from pydantic import BaseModel

from ..models.deficiency_models import (
    ProductionStatus,
    RequestAnalysis,
    DeficiencyReport
)
from ..vector_storage.qdrant_store import QdrantVectorStore, SearchResult
from ..utils.logger import setup_logger
from ..websocket.socket_server import sio

logger = setup_logger(__name__)


class SearchStrategy(BaseModel):
    """AI-generated search strategy for finding responsive documents."""
    queries: List[str]
    search_approach: str  # e.g., "keyword", "semantic", "date_range"
    reasoning: str


class ParsedRequests(BaseModel):
    """Parsed RFP requests."""
    requests: Dict[int, str]


class DeficiencyAnalyzer:
    """Analyzes discovery productions for deficiencies against RFP requests."""
    
    def __init__(self, case_name: str):
        """Initialize the deficiency analyzer.
        
        Args:
            case_name: Name of the case to analyze
        """
        self._validate_case_name(case_name)
        self.case_name = case_name
        self.vector_store = QdrantVectorStore()
        
        # Agent for generating search strategies
        self.search_agent = Agent(
            'gpt-4.1-mini',
            result_type=SearchStrategy,
            system_prompt="""You are a legal discovery expert generating semantic search queries for a vector database using natural language processing.
            
            CRITICAL: Generate queries as if you're asking a question or describing what you need to a colleague.
            The vector database understands MEANING and CONTEXT, not just keywords.
            
            EXCELLENT semantic query examples:
            - "What safety procedures were in place for commercial truck drivers before the accident?"
            - "Show me all maintenance and inspection records for the vehicle involved in the crash"
            - "Find communications between the trucking company and drivers about safety violations"
            - "Documents showing the driver's training history and medical certification status"
            - "Any reports or complaints about vehicle defects or maintenance issues"
            
            TERRIBLE query examples (NEVER DO THIS):
            - "safety AND training AND truck" (Boolean operators)
            - "documents maintenance records" (keyword soup)
            - driver qualification medical (disconnected terms)
            - "truck" AND "crash" AND "documents" (Boolean search)
            
            Remember:
            1. Write queries as complete thoughts or questions
            2. Include context about WHY you want the documents
            3. Use natural, conversational language
            4. Think about the MEANING behind what you're searching for
            5. Consider different ways someone might describe the same concept
            
            Generate 3-5 semantic queries that explore different aspects of the request."""
        )
        
        # Agent for analyzing completeness
        self.analysis_agent = Agent(
            'gpt-4.1-mini',
            result_type=RequestAnalysis,
            system_prompt="""You are a discovery deficiency analyst. Analyze whether documents 
            produced satisfy the request. Be precise and evidence-based:
            
            1. FULLY PRODUCED: Clear evidence all requested items were provided
            2. PARTIALLY PRODUCED: Some but not all items found
            3. NOT PRODUCED: No responsive documents found
            
            Always cite specific evidence with quotes and bates numbers, when able.
            Never assume documents exist without finding them."""
        )
        
        # Agent for parsing RFP requests
        self.parser_agent = Agent(
            'gpt-4.1-mini',
            result_type=ParsedRequests,
            system_prompt="""Extract numbered requests from Request for Production documents.
            Return a dictionary mapping request numbers to request text.
            Example: {1: "All documents relating to...", 2: "All communications between..."}
            
            Look for patterns like:
            - REQUEST NO. 1:
            - Request 1:
            - 1.
            - (1)
            
            Extract the complete request text, including any subparts."""
        )
    
    def _validate_case_name(self, case_name: str):
        """Validate case name is provided."""
        if not case_name or not isinstance(case_name, str):
            raise ValueError("Case name must be a non-empty string")
    
    async def analyze_discovery_deficiencies(
        self,
        rfp_document_id: str,
        defense_response_id: Optional[str],
        production_batch: str,
        processing_id: str
    ) -> DeficiencyReport:
        """Main entry point for deficiency analysis.
        
        Args:
            rfp_document_id: ID of the RFP document
            defense_response_id: Optional ID of defense response document
            production_batch: Batch identifier for this production
            processing_id: Processing session ID
            
        Returns:
            DeficiencyReport with analysis results
        """
        logger.info(f"Starting deficiency analysis for case {self.case_name}, batch {production_batch}")
        
        try:
            # Extract RFP requests - MUST succeed or we stop
            rfp_requests = await self._extract_rfp_requests(rfp_document_id)
            logger.info(f"Successfully extracted {len(rfp_requests)} RFP requests")
        except Exception as e:
            logger.error(f"Failed to extract RFP requests: {str(e)}")
            raise  # Re-raise to stop the analysis
        
        # Extract defense responses if provided
        defense_responses = {}
        if defense_response_id:
            try:
                defense_responses = await self._extract_defense_responses(defense_response_id)
                logger.info(f"Successfully extracted {len(defense_responses)} defense responses")
            except Exception as e:
                logger.warning(f"Failed to extract defense responses: {str(e)}")
                # Continue without defense responses - not critical
        
        # Analyze each request
        analyses = []
        total_requests = len(rfp_requests)
        
        for idx, (request_num, request_text) in enumerate(rfp_requests.items()):
            # Emit progress
            await self._emit_progress(processing_id, idx + 1, total_requests)
            
            # Analyze single request
            analysis = await self._analyze_single_request(
                request_number=request_num,
                request_text=request_text,
                response_text=defense_responses.get(request_num),
                production_batch=production_batch,
                processing_id=processing_id
            )
            analyses.append(analysis)
        
        # Generate report
        report = DeficiencyReport(
            id=f"deficiency_{processing_id}",
            case_name=self.case_name,
            processing_id=processing_id,
            production_batch=production_batch,
            rfp_document_id=rfp_document_id,
            defense_response_id=defense_response_id,
            analyses=analyses,
            overall_completeness=self._calculate_completeness(analyses),
            generated_at=datetime.utcnow()
        )
        
        return report
    
    async def _search_production_documents(
        self,
        query: str,
        production_batch: str,
        limit: int = 20
    ) -> List[SearchResult]:
        """Search ONLY within current production batch.
        
        CRITICAL: This method enforces production-scoped search to prevent
        cross-production contamination.
        
        Args:
            query: Search query text
            production_batch: Production batch to search within
            limit: Maximum results to return
            
        Returns:
            List of documents from the specified production only
        """
        logger.info(f"Searching production {production_batch} with query: {query}")
        
        # Generate embeddings for the query
        from ..vector_storage.embeddings import EmbeddingGenerator
        embedding_generator = EmbeddingGenerator()
        
        try:
            query_embedding, token_count = embedding_generator.generate_embedding(query)
        except Exception as e:
            logger.error(f"Failed to generate embedding for query: {str(e)}")
            return []
        
        # Validate embedding was generated
        if not query_embedding or not isinstance(query_embedding, list):
            logger.error(f"Invalid embedding generated for query: {query}")
            return []
        
        try:
            # Log search parameters for debugging
            logger.debug(f"Search parameters:")
            logger.debug(f"  - Collection: {self.case_name}")
            logger.debug(f"  - Query: '{query}'")
            logger.debug(f"  - Embedding length: {len(query_embedding)}")
            logger.debug(f"  - Filters: {{'production_batch': '{production_batch}'}}")
            logger.debug(f"  - Limit: {limit}, Threshold: 0.0")
            
            # Perform vector search with production filter
            # Note: hybrid_search doesn't support filters, so we'll use search_documents instead
            results = self.vector_store.search_documents(
                collection_name=self.case_name,
                query_embedding=query_embedding,
                limit=limit,
                threshold=0.0,  # Lower threshold to get more results
                filters={"production_batch": production_batch}
            )
            
            logger.info(f"Found {len(results)} documents in production {production_batch}")
            
            # Log details about results
            if results:
                logger.debug(f"Top result scores: {[r.score for r in results[:3]]}")
                logger.debug(f"First result metadata: {results[0].metadata if results else 'No results'}")
            else:
                logger.warning(f"No results found! Debugging info:")
                logger.warning(f"  - Query: '{query}'")
                logger.warning(f"  - Production batch filter: '{production_batch}'")
                logger.warning(f"  - Collection name: '{self.case_name}'")
                
                # Try a search without filters to see if documents exist
                try:
                    unfiltered_results = self.vector_store.search_documents(
                        collection_name=self.case_name,
                        query_embedding=query_embedding,
                        limit=5,
                        threshold=0.0,
                        filters=None  # No filters
                    )
                    logger.warning(f"  - Unfiltered search found {len(unfiltered_results)} documents")
                    if unfiltered_results:
                        logger.warning(f"  - Sample metadata from unfiltered results:")
                        for i, res in enumerate(unfiltered_results[:2]):
                            logger.warning(f"    Result {i+1}: {res.metadata}")
                except Exception as debug_e:
                    logger.error(f"  - Debug unfiltered search failed: {str(debug_e)}")
            
            return results
        except Exception as e:
            logger.error(f"Error searching production documents: {str(e)}")
            logger.error(f"Full exception details:", exc_info=True)
            return []
    
    async def _analyze_single_request(
        self,
        request_number: int,
        request_text: str,
        response_text: Optional[str],
        production_batch: str,
        processing_id: str
    ) -> RequestAnalysis:
        """Analyze if a single request was satisfied.
        
        Args:
            request_number: RFP request number
            request_text: Full text of the request
            response_text: Defense response if available
            production_batch: Current production batch
            processing_id: Processing session ID
            
        Returns:
            RequestAnalysis with production status and evidence
        """
        logger.info(f"Analyzing request {request_number}")
        
        # Generate search strategy
        search_strategy = await self.search_agent.run(
            f"Generate search queries for this RFP request: {request_text}"
        )
        
        # Execute searches
        all_results = []
        for query in search_strategy.data.queries:
            results = await self._search_production_documents(
                query=query,
                production_batch=production_batch
            )
            all_results.extend(results)
        
        # Deduplicate results
        unique_results = self._deduplicate_results(all_results)
        
        # Analyze completeness
        analysis_prompt = f"""
        Request Number: {request_number}
        Request: {request_text}
        Defense Response: {response_text or 'No response provided'}
        
        Found Documents ({len(unique_results)}):
        {self._format_documents_for_analysis(unique_results)}
        
        Analyze if the request was satisfied by these documents.
        Provide specific evidence with quotes and document references.
        """
        
        analysis_result = await self.analysis_agent.run(analysis_prompt)
        
        # Add search queries used
        analysis_result.data.search_queries_used = search_strategy.data.queries
        analysis_result.data.request_number = request_number
        analysis_result.data.request_text = request_text
        analysis_result.data.response_text = response_text
        
        return analysis_result.data
    
    async def _extract_rfp_requests(self, document_id: str) -> Dict[int, str]:
        """Extract individual requests from RFP document.
        
        Args:
            document_id: ID of the RFP document
            
        Returns:
            Dictionary mapping request numbers to request text
        """
        logger.info(f"Extracting RFP requests from document {document_id}")
        
        # Get the RFP content from processing status
        from src.api.discovery_endpoints import processing_status
        from src.document_processing.pdf_extractor import PDFExtractor
        
        logger.info(f"Looking for RFP document with ID: {document_id}")
        logger.info(f"Current processing status entries: {list(processing_status.keys())}")
        
        # Find the processing status that has this RFP document ID
        rfp_content = None
        found_status = None
        for proc_id, status in processing_status.items():
            logger.debug(f"Checking processing ID {proc_id}")
            if hasattr(status, 'rfp_document_id'):
                logger.debug(f"  - Has rfp_document_id: {status.rfp_document_id}")
                if status.rfp_document_id == document_id:
                    rfp_content = getattr(status, 'rfp_content', None)
                    found_status = status
                    logger.info(f"Found RFP in processing ID {proc_id}, content size: {len(rfp_content) if rfp_content else 0} bytes")
                    break
            else:
                logger.debug(f"  - No rfp_document_id attribute")
        
        if not rfp_content:
            error_msg = f"CRITICAL ERROR: RFP document {document_id} not found in processing status. Cannot proceed with deficiency analysis."
            logger.error(error_msg)
            raise ValueError(error_msg)
        
        # Extract text from PDF
        pdf_extractor = PDFExtractor()
        extracted_doc = pdf_extractor.extract_text(rfp_content, filename="rfp.pdf")
        extracted_text = extracted_doc.text
        
        if not extracted_text or extracted_text.strip() == "":
            error_msg = f"CRITICAL ERROR: No text extracted from RFP document {document_id}. PDF extraction failed completely."
            logger.error(error_msg)
            raise ValueError(error_msg)
        
        try:
            # Use AI to parse requests
            result = await self.parser_agent.run(
                f"Extract all numbered requests from this Request for Production:\n\n{extracted_text}"
            )
            
            if not result.data.requests:
                error_msg = "CRITICAL ERROR: AI agent failed to extract any requests from the RFP document"
                logger.error(error_msg)
                logger.error(f"Extracted text preview: {extracted_text[:500]}...")
                raise ValueError(error_msg)
            
            logger.info(f"Successfully extracted {len(result.data.requests)} requests from RFP")
            
            # Log the actual requests for debugging
            for num, req in result.data.requests.items():
                logger.info(f"RFP Request {num}: {req[:200]}...")
                
            return result.data.requests
        except Exception as e:
            error_msg = f"CRITICAL ERROR: Failed to parse RFP requests: {str(e)}"
            logger.error(error_msg)
            logger.error(f"Full exception:", exc_info=True)
            raise ValueError(error_msg)
    
    async def _extract_defense_responses(self, document_id: str) -> Dict[int, str]:
        """Extract defense responses mapped to request numbers.
        
        Args:
            document_id: ID of the defense response document
            
        Returns:
            Dictionary mapping request numbers to response text
        """
        logger.info(f"Extracting defense responses from document {document_id}")
        
        # Get the defense response content from processing status
        from src.api.discovery_endpoints import processing_status
        from src.document_processing.pdf_extractor import PDFExtractor
        
        # Find the processing status that has this defense response document ID
        defense_content = None
        for proc_id, status in processing_status.items():
            if hasattr(status, 'defense_response_id') and status.defense_response_id == document_id:
                defense_content = getattr(status, 'defense_content', None)
                break
        
        if not defense_content:
            logger.warning(f"Defense response document {document_id} not found in processing status")
            return {}
        
        # Extract text from PDF
        pdf_extractor = PDFExtractor()
        extracted_doc = pdf_extractor.extract_text(defense_content, filename="defense_response.pdf")
        extracted_text = extracted_doc.text
        
        if not extracted_text or extracted_text.strip() == "":
            logger.warning(f"No text extracted from defense response document {document_id}")
            return {}
        
        try:
            # Use AI to parse responses
            result = await self.parser_agent.run(
                f"Extract numbered responses from this defense response document:\n\n{extracted_text}"
            )
            
            logger.info(f"Extracted {len(result.data.requests)} responses")
            return result.data.requests
        except Exception as e:
            logger.error(f"Failed to parse defense responses: {str(e)}")
            # Return empty dict if parsing fails
            return {}
    
    async def _emit_progress(self, processing_id: str, current: int, total: int):
        """Emit WebSocket progress event.
        
        Args:
            processing_id: Processing session ID
            current: Current request number being processed
            total: Total number of requests
        """
        progress_percent = (current / total) * 100 if total > 0 else 0
        
        await sio.emit(
            'discovery:deficiency_analysis_progress',
            {
                'processingId': processing_id,
                'currentRequest': current,
                'totalRequests': total,
                'progressPercent': progress_percent
            },
            room=f'case_{self.case_name}'
        )
    
    def _deduplicate_results(self, results: List[SearchResult]) -> List[SearchResult]:
        """Remove duplicate documents based on document ID.
        
        Args:
            results: List of search results that may contain duplicates
            
        Returns:
            List of unique search results
        """
        seen_ids: Set[str] = set()
        unique_results = []
        
        for result in results:
            if result.document_id not in seen_ids:
                seen_ids.add(result.document_id)
                unique_results.append(result)
        
        return unique_results
    
    def _format_documents_for_analysis(self, results: List[SearchResult]) -> str:
        """Format search results for AI analysis.
        
        Args:
            results: List of search results to format
            
        Returns:
            Formatted string representation
        """
        if not results:
            return "No documents found"
        
        formatted = []
        for result in results[:10]:  # Limit to first 10 for context window
            metadata = result.metadata or {}
            bates_range = metadata.get('bates_range', 'No bates numbers')
            document_type = metadata.get('document_type', 'Unknown')
            title = metadata.get('title', metadata.get('document_name', f'Document {result.document_id}'))
            
            formatted.append(f"""
Document: {title}
Bates: {bates_range}
Type: {document_type}
Score: {result.score:.3f}
Content excerpt: {result.content[:500]}...
---""")
        
        if len(results) > 10:
            formatted.append(f"\n... and {len(results) - 10} more documents")
        
        return "\n".join(formatted)
    
    def _calculate_completeness(self, analyses: List[RequestAnalysis]) -> float:
        """Calculate overall completeness percentage.
        
        Args:
            analyses: List of request analyses
            
        Returns:
            Percentage of requests that were fully or partially produced
        """
        if not analyses:
            return 0.0
        
        produced_count = sum(
            1 for a in analyses 
            if a.status in [ProductionStatus.FULLY_PRODUCED, ProductionStatus.PARTIALLY_PRODUCED]
        )
        
        return (produced_count / len(analyses)) * 100