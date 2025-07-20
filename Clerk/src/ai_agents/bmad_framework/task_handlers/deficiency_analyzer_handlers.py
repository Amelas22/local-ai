"""
Task handlers for deficiency analyzer agent.

This module provides the actual implementation for deficiency analyzer tasks,
integrating with Clerk's existing services.
"""

import logging
from typing import Dict, Any, List, Optional
from pathlib import Path
from uuid import uuid4
import asyncio

from src.document_processing.rtp_parser import RTPParser
from src.vector_storage.qdrant_store import QdrantVectorStore
from src.vector_storage.embeddings import EmbeddingGenerator
from src.services.deficiency_service import DeficiencyService
from src.models.deficiency_models import DeficiencyItem, DeficiencyReport
from src.document_processing.pdf_extractor import PDFExtractor
from src.models.unified_document_models import UnifiedDocument

from ..agent_executor import ExecutionContext
from ..exceptions import TaskExecutionError, ValidationError

logger = logging.getLogger("clerk_api")


class DeficiencyAnalyzerHandlers:
    """
    Handles task execution for deficiency analyzer agent.
    
    Provides actual implementations that integrate with Clerk services.
    """
    
    def __init__(self):
        self.vector_store = QdrantVectorStore()
        self.deficiency_service = DeficiencyService()
        self.pdf_extractor = PDFExtractor()
        self.embedding_generator = EmbeddingGenerator()
    
    async def handle_analyze_rtp(self, context: ExecutionContext) -> Dict[str, Any]:
        """
        Handle the analyze command to parse RTP documents.
        
        Args:
            context: Execution context with parameters.
            
        Returns:
            Analysis results with parsed RTP requests.
        """
        # Validate required parameters
        rtp_path = context.parameters.get("rtp_path")
        if not rtp_path:
            raise ValidationError("rtp_path", "RTP document path is required")
        
        # Ensure case isolation
        case_name = context.case_name
        
        try:
            # Initialize RTP parser with case name
            rtp_parser = RTPParser(case_name=case_name)
            
            # Emit progress event
            if context.websocket_channel:
                await self._emit_progress(
                    context,
                    "Parsing RTP document...",
                    10
                )
            
            # Parse the RTP document
            rtp_requests = await rtp_parser.parse_rtp_document(rtp_path)
            
            # Emit progress
            if context.websocket_channel:
                await self._emit_progress(
                    context,
                    f"Found {len(rtp_requests)} RTP requests",
                    50
                )
            
            # Format results
            results = {
                "rtp_document_path": rtp_path,
                "case_name": case_name,
                "total_requests": len(rtp_requests),
                "requests": [
                    {
                        "request_number": req.request_number,
                        "request_text": req.request_text,
                        "category": req.category,
                        "page_range": req.page_range
                    }
                    for req in rtp_requests
                ],
                "summary": {
                    "by_category": {},
                    "complex_requests": [],
                    "total_pages": 0
                }
            }
            
            # Calculate summary statistics
            for req in rtp_requests:
                cat = req.category or "uncategorized"
                results["summary"]["by_category"][cat] = (
                    results["summary"]["by_category"].get(cat, 0) + 1
                )
            
            # Complete
            if context.websocket_channel:
                await self._emit_progress(
                    context,
                    "RTP analysis complete",
                    100
                )
            
            return results
            
        except Exception as e:
            logger.error(f"Failed to analyze RTP: {str(e)}")
            raise TaskExecutionError("analyze-rtp", str(e))
    
    async def handle_search_production(self, context: ExecutionContext) -> Dict[str, Any]:
        """
        Handle the search command to search production documents.
        
        Args:
            context: Execution context with parameters.
            
        Returns:
            Search results from vector store.
        """
        # Validate parameters
        query = context.parameters.get("query")
        if not query:
            raise ValidationError("query", "Search query is required")
        
        case_name = context.case_name
        
        try:
            # Emit progress
            if context.websocket_channel:
                await self._emit_progress(
                    context,
                    "Searching production documents...",
                    20
                )
            
            # Generate query embedding first
            embeddings, _ = await self.embedding_generator.generate_embeddings_batch_async([query])
            query_embedding = embeddings[0] if embeddings else []
            
            # Perform hybrid search
            search_results = await self.vector_store.hybrid_search(
                collection_name=case_name,
                query=query,
                query_embedding=query_embedding,
                limit=context.parameters.get("limit", 50),
                final_limit=context.parameters.get("limit", 50),
                enable_reranking=False
            )
            
            # Emit progress
            if context.websocket_channel:
                await self._emit_progress(
                    context,
                    f"Found {len(search_results)} relevant documents",
                    80
                )
            
            # Format results
            results = {
                "query": query,
                "case_name": case_name,
                "total_results": len(search_results),
                "results": [
                    {
                        "document_id": str(result.id),
                        "chunk_text": result.text,
                        "relevance_score": result.relevance_score,
                        "metadata": {
                            "document_name": result.metadata.get("document_name"),
                            "page_number": result.metadata.get("page_number"),
                            "bates_number": result.metadata.get("bates_number"),
                            "document_type": result.metadata.get("document_type")
                        }
                    }
                    for result in search_results
                ]
            }
            
            # Complete
            if context.websocket_channel:
                await self._emit_progress(
                    context,
                    "Search complete",
                    100
                )
            
            return results
            
        except Exception as e:
            logger.error(f"Search failed: {str(e)}")
            raise TaskExecutionError("search-production", str(e))
    
    async def handle_categorize_compliance(self, context: ExecutionContext) -> Dict[str, Any]:
        """
        Handle the categorize command to categorize RTP compliance.
        
        Args:
            context: Execution context with parameters.
            
        Returns:
            Categorization results with deficiency classification.
        """
        # Validate parameters
        request_number = context.parameters.get("request_number")
        request_text = context.parameters.get("request_text")
        oc_response_text = context.parameters.get("oc_response_text", "")
        
        if not request_number or not request_text:
            raise ValidationError(
                "parameters",
                "request_number and request_text are required"
            )
        
        try:
            # Emit progress
            if context.websocket_channel:
                await self._emit_progress(
                    context,
                    f"Categorizing request {request_number}...",
                    30
                )
            
            # Get search results if provided
            search_results = context.parameters.get("search_results", [])
            
            # Determine classification based on search results and OC response
            classification = self._determine_classification(
                search_results,
                oc_response_text
            )
            
            # Calculate confidence score
            confidence_score = self._calculate_confidence(
                classification,
                search_results,
                oc_response_text
            )
            
            # Generate evidence summary
            evidence_summary = self._generate_evidence_summary(
                classification,
                search_results,
                oc_response_text
            )
            
            # Build recommendation
            recommendation = self._generate_recommendation(
                classification,
                confidence_score,
                evidence_summary
            )
            
            # Emit progress
            if context.websocket_channel:
                await self._emit_progress(
                    context,
                    f"Categorized as {classification}",
                    90
                )
            
            result = {
                "request_number": request_number,
                "classification": classification,
                "confidence_score": confidence_score,
                "evidence_summary": evidence_summary,
                "recommendation": recommendation,
                "metadata": {
                    "search_result_count": len(search_results),
                    "has_oc_response": bool(oc_response_text),
                    "case_name": context.case_name
                }
            }
            
            # Complete
            if context.websocket_channel:
                await self._emit_progress(
                    context,
                    "Categorization complete",
                    100
                )
            
            return result
            
        except Exception as e:
            logger.error(f"Categorization failed: {str(e)}")
            raise TaskExecutionError("categorize-compliance", str(e))
    
    async def handle_full_analysis(self, context: ExecutionContext) -> Dict[str, Any]:
        """
        Handle the analyze command for full deficiency analysis.
        
        Args:
            context: Execution context with parameters.
            
        Returns:
            Processing information for async analysis.
        """
        # Validate parameters
        production_id = context.parameters.get("production_id")
        rtp_document_id = context.parameters.get("rtp_document_id")
        
        if not production_id or not rtp_document_id:
            raise ValidationError(
                "parameters",
                "production_id and rtp_document_id are required"
            )
        
        try:
            # Create processing ID
            processing_id = str(uuid4())
            
            # Initialize deficiency report
            report = await self.deficiency_service.create_deficiency_report(
                case_name=context.case_name,
                production_id=production_id,
                rtp_document_id=rtp_document_id,
                oc_response_document_id=context.parameters.get("oc_response_id")
            )
            
            # Return async processing info
            result = {
                "processing_id": processing_id,
                "report_id": str(report.id),
                "websocket_channel": f"agent:{context.agent_def.id}:{processing_id}",
                "estimated_duration_seconds": 300,
                "status": "initiated",
                "message": "Full deficiency analysis has been initiated"
            }
            
            # Start async processing in background
            asyncio.create_task(
                self._process_full_analysis(
                    context,
                    report,
                    processing_id
                )
            )
            
            return result
            
        except Exception as e:
            logger.error(f"Failed to initiate analysis: {str(e)}")
            raise TaskExecutionError("analyze", str(e))
    
    def _determine_classification(
        self,
        search_results: List[Dict],
        oc_response: str
    ) -> str:
        """Determine compliance classification."""
        if not search_results and "no responsive documents" in oc_response.lower():
            return "no_responsive_docs"
        elif not search_results:
            return "not_produced"
        elif len(search_results) > 10:
            return "fully_produced"
        else:
            return "partially_produced"
    
    def _calculate_confidence(
        self,
        classification: str,
        search_results: List[Dict],
        oc_response: str
    ) -> float:
        """Calculate confidence score for classification."""
        base_confidence = 0.7
        
        # Adjust based on search results
        if search_results:
            avg_score = sum(r.get("relevance_score", 0) for r in search_results) / len(search_results)
            base_confidence = max(base_confidence, avg_score)
        
        # Adjust based on OC response clarity
        if oc_response and len(oc_response) > 50:
            base_confidence += 0.1
        
        return min(base_confidence, 0.95)
    
    def _generate_evidence_summary(
        self,
        classification: str,
        search_results: List[Dict],
        oc_response: str
    ) -> str:
        """Generate evidence summary for classification."""
        if classification == "fully_produced":
            return f"Found {len(search_results)} highly relevant documents"
        elif classification == "partially_produced":
            return f"Found {len(search_results)} documents, but gaps identified"
        elif classification == "not_produced":
            return "No responsive documents found in production"
        else:
            return "Opposing counsel claims no responsive documents exist"
    
    def _generate_recommendation(
        self,
        classification: str,
        confidence: float,
        evidence_summary: str
    ) -> str:
        """Generate recommendation based on classification."""
        if classification == "not_produced":
            return "Request meet and confer regarding missing documents"
        elif classification == "partially_produced":
            return "Request supplemental production for identified gaps"
        elif confidence < 0.7:
            return "Manual review recommended due to low confidence"
        else:
            return "No action required"
    
    async def _emit_progress(
        self,
        context: ExecutionContext,
        message: str,
        percentage: int
    ) -> None:
        """Emit progress update via websocket."""
        from ..websocket_progress import emit_progress_update
        
        await emit_progress_update(
            case_id=context.security_context.case_id,
            agent_id=context.agent_def.id,
            task_name=context.command,
            message=message,
            percentage=percentage
        )
    
    async def _process_full_analysis(
        self,
        context: ExecutionContext,
        report: DeficiencyReport,
        processing_id: str
    ) -> None:
        """
        Process full deficiency analysis in background.
        
        This would implement the complete analysis workflow.
        """
        # This is a placeholder for the full implementation
        # In production, this would:
        # 1. Parse RTP document
        # 2. Search for each request
        # 3. Categorize compliance
        # 4. Generate report
        # 5. Save results
        
        await asyncio.sleep(1)  # Simulate processing
        
        # Update report status
        await self.deficiency_service.update_analysis_status(
            report_id=str(report.id),
            status="completed"
        )


# Create singleton instance
deficiency_handlers = DeficiencyAnalyzerHandlers()


# Export handler functions
async def handle_analyze_rtp(context: ExecutionContext) -> Dict[str, Any]:
    """Handle analyze-rtp task."""
    return await deficiency_handlers.handle_analyze_rtp(context)


async def handle_search_production(context: ExecutionContext) -> Dict[str, Any]:
    """Handle search-production task."""
    return await deficiency_handlers.handle_search_production(context)


async def handle_categorize_compliance(context: ExecutionContext) -> Dict[str, Any]:
    """Handle categorize-compliance task."""
    return await deficiency_handlers.handle_categorize_compliance(context)


async def handle_full_analysis(context: ExecutionContext) -> Dict[str, Any]:
    """Handle full analysis command."""
    return await deficiency_handlers.handle_full_analysis(context)