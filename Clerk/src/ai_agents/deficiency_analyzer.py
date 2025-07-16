"""
Discovery Deficiency Analyzer

This module analyzes discovery productions to identify gaps between what was
requested in RFPs and what was actually produced. It uses AI agents to:
1. Parse RFP requests and defense responses
2. Search ONLY within the current production batch
3. Determine production status with evidence
4. Generate comprehensive deficiency reports
"""

import asyncio
from typing import List, Dict, Any, Optional, Set
from datetime import datetime
from pydantic_ai import Agent
from pydantic import BaseModel
import hashlib

from ..models.deficiency_models import (
    ProductionStatus,
    EvidenceItem,
    RequestAnalysis,
    DeficiencyReport
)
from ..models.unified_document_models import UnifiedDocument
from ..vector_storage.qdrant_store import QdrantVectorStore
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
            system_prompt="""You are a legal discovery expert. Given a Request for Production (RFP), 
            generate effective search queries to find responsive documents. Consider:
            - Key terms and concepts
            - Document types mentioned
            - Date ranges
            - Parties involved
            - Legal terminology variations
            
            DO NOT make assumptions. Only search for what is explicitly requested."""
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
        
        # Extract RFP requests
        rfp_requests = await self._extract_rfp_requests(rfp_document_id)
        
        # Extract defense responses if provided
        defense_responses = {}
        if defense_response_id:
            defense_responses = await self._extract_defense_responses(defense_response_id)
        
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
    ) -> List[UnifiedDocument]:
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
        from qdrant_client import models
        
        # CRITICAL: Filter to current production only
        production_filter = models.Filter(
            must=[
                models.FieldCondition(
                    key="case_name",
                    match=models.MatchValue(value=self.case_name)
                ),
                models.FieldCondition(
                    key="metadata.production_batch",
                    match=models.MatchValue(value=production_batch)
                )
            ]
        )
        
        logger.info(f"Searching production {production_batch} with query: {query}")
        
        # Perform hybrid search
        results = await self.vector_store.hybrid_search(
            collection_name=self.case_name,
            query_text=query,
            query_filter=production_filter,
            limit=limit,
            vector_weight=0.7,
            text_weight=0.3
        )
        
        logger.info(f"Found {len(results)} documents in production {production_batch}")
        return results
    
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
        
        # Get document content from vector store
        document = await self.vector_store.get_document_by_id(
            collection_name=self.case_name,
            document_id=document_id
        )
        
        if not document:
            raise ValueError(f"RFP document {document_id} not found")
        
        # Use AI to parse requests
        result = await self.parser_agent.run(
            f"Extract all numbered requests from this Request for Production:\n\n{document.content}"
        )
        
        logger.info(f"Extracted {len(result.data.requests)} requests from RFP")
        return result.data.requests
    
    async def _extract_defense_responses(self, document_id: str) -> Dict[int, str]:
        """Extract defense responses mapped to request numbers.
        
        Args:
            document_id: ID of the defense response document
            
        Returns:
            Dictionary mapping request numbers to response text
        """
        logger.info(f"Extracting defense responses from document {document_id}")
        
        # Get document content
        document = await self.vector_store.get_document_by_id(
            collection_name=self.case_name,
            document_id=document_id
        )
        
        if not document:
            logger.warning(f"Defense response document {document_id} not found")
            return {}
        
        # Use AI to parse responses
        result = await self.parser_agent.run(
            f"Extract numbered responses from this defense response document:\n\n{document.content}"
        )
        
        logger.info(f"Extracted {len(result.data.requests)} responses")
        return result.data.requests
    
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
    
    def _deduplicate_results(self, documents: List[UnifiedDocument]) -> List[UnifiedDocument]:
        """Remove duplicate documents based on document hash.
        
        Args:
            documents: List of documents that may contain duplicates
            
        Returns:
            List of unique documents
        """
        seen_hashes: Set[str] = set()
        unique_documents = []
        
        for doc in documents:
            if doc.document_hash not in seen_hashes:
                seen_hashes.add(doc.document_hash)
                unique_documents.append(doc)
        
        return unique_documents
    
    def _format_documents_for_analysis(self, documents: List[UnifiedDocument]) -> str:
        """Format documents for AI analysis.
        
        Args:
            documents: List of documents to format
            
        Returns:
            Formatted string representation
        """
        if not documents:
            return "No documents found"
        
        formatted = []
        for doc in documents[:10]:  # Limit to first 10 for context window
            metadata = doc.metadata or {}
            bates_range = metadata.get('bates_range', 'No bates numbers')
            
            formatted.append(f"""
Document: {doc.title or doc.file_name}
Bates: {bates_range}
Type: {doc.document_type}
Content excerpt: {doc.content[:500]}...
---""")
        
        if len(documents) > 10:
            formatted.append(f"\n... and {len(documents) - 10} more documents")
        
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