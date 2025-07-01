"""
Enhanced document processor that emits WebSocket events during processing
"""
import asyncio
import logging
from typing import Dict, Any, Optional, List
from datetime import datetime
import uuid

from src.document_injector_unified import UnifiedDocumentInjector
from src.models.unified_document_models import DiscoveryProcessingRequest
from src.websocket import (
    emit_discovery_started,
    emit_document_found,
    emit_chunking_progress,
    emit_embedding_progress,
    emit_document_stored,
    emit_processing_completed,
    emit_processing_error
)

logger = logging.getLogger(__name__)

class WebSocketDocumentProcessor:
    """Document processor that emits real-time updates via WebSocket"""
    
    def __init__(self, document_injector: UnifiedDocumentInjector):
        self.injector = document_injector
        self.processing_jobs: Dict[str, Dict[str, Any]] = {}
    
    async def process_discovery_with_updates(
        self,
        request: DiscoveryProcessingRequest
    ) -> Dict[str, Any]:
        """
        Process discovery documents with real-time WebSocket updates
        """
        processing_id = str(uuid.uuid4())
        start_time = datetime.utcnow()
        
        # Store job metadata
        self.processing_jobs[processing_id] = {
            'request': request,
            'start_time': start_time,
            'status': 'started',
            'documents_found': 0,
            'documents_processed': 0,
            'errors': []
        }
        
        try:
            # Emit processing started event
            await emit_discovery_started(
                processing_id=processing_id,
                case_id=request.case_name,
                total_files=0  # Will be updated as we discover files
            )
            
            # Get Box folder contents
            folder_items = await self._get_folder_items(request.folder_id)
            total_files = len([item for item in folder_items if item['type'] == 'file'])
            
            # Update with actual file count
            await emit_discovery_started(
                processing_id=processing_id,
                case_id=request.case_name,
                total_files=total_files
            )
            
            # Process each document
            for item in folder_items:
                if item['type'] == 'file' and item['name'].endswith('.pdf'):
                    await self._process_document_with_updates(
                        processing_id=processing_id,
                        file_item=item,
                        request=request
                    )
            
            # Calculate summary
            summary = self._create_processing_summary(processing_id)
            
            # Emit completion event
            await emit_processing_completed(
                processing_id=processing_id,
                summary=summary
            )
            
            # Update job status
            self.processing_jobs[processing_id]['status'] = 'completed'
            self.processing_jobs[processing_id]['end_time'] = datetime.utcnow()
            self.processing_jobs[processing_id]['summary'] = summary
            
            return {
                'processing_id': processing_id,
                'status': 'completed',
                'summary': summary
            }
            
        except Exception as e:
            logger.error(f"Error in discovery processing: {str(e)}")
            await emit_processing_error(
                processing_id=processing_id,
                error=str(e),
                stage='processing'
            )
            
            self.processing_jobs[processing_id]['status'] = 'error'
            self.processing_jobs[processing_id]['error'] = str(e)
            
            raise
    
    async def _get_folder_items(self, folder_id: str) -> List[Dict[str, Any]]:
        """Get items from Box folder"""
        # This would normally use the Box API
        # For now, return mock data for testing
        return [
            {
                'id': f'doc_{i}',
                'type': 'file',
                'name': f'discovery_document_{i}.pdf',
                'size': 1024 * 1024 * (i + 1)
            }
            for i in range(5)
        ]
    
    async def _process_document_with_updates(
        self,
        processing_id: str,
        file_item: Dict[str, Any],
        request: DiscoveryProcessingRequest
    ):
        """Process a single document with WebSocket updates"""
        document_id = file_item['id']
        
        try:
            # Emit document found event
            await emit_document_found(
                processing_id=processing_id,
                document_id=document_id,
                title=file_item['name'],
                doc_type='unknown',  # Will be classified later
                page_count=50,  # Mock value
                bates_range={'start': 'DEF000001', 'end': 'DEF000050'},
                confidence=0.95
            )
            
            # Simulate document classification
            await asyncio.sleep(0.5)
            doc_type = self._classify_document(file_item['name'])
            
            # Simulate chunking with progress updates
            total_chunks = 10
            for i in range(total_chunks):
                await asyncio.sleep(0.2)
                progress = ((i + 1) / total_chunks) * 100
                await emit_chunking_progress(
                    processing_id=processing_id,
                    document_id=document_id,
                    progress=progress,
                    chunks_created=i + 1
                )
            
            # Simulate embedding generation
            for i in range(total_chunks):
                await asyncio.sleep(0.1)
                chunk_id = f"chunk_{document_id}_{i}"
                progress = ((i + 1) / total_chunks) * 100
                await emit_embedding_progress(
                    processing_id=processing_id,
                    document_id=document_id,
                    chunk_id=chunk_id,
                    progress=progress
                )
            
            # Emit storage confirmation
            await emit_document_stored(
                processing_id=processing_id,
                document_id=document_id,
                vectors_stored=total_chunks
            )
            
            # Update job stats
            self.processing_jobs[processing_id]['documents_processed'] += 1
            
        except Exception as e:
            logger.error(f"Error processing document {document_id}: {str(e)}")
            await emit_processing_error(
                processing_id=processing_id,
                error=str(e),
                stage='document_processing',
                document_id=document_id
            )
            self.processing_jobs[processing_id]['errors'].append({
                'document_id': document_id,
                'error': str(e)
            })
    
    def _classify_document(self, filename: str) -> str:
        """Simple document classification based on filename"""
        filename_lower = filename.lower()
        
        if 'deposition' in filename_lower:
            return 'deposition'
        elif 'motion' in filename_lower:
            return 'motion'
        elif 'interrogatory' in filename_lower:
            return 'interrogatory'
        elif 'request' in filename_lower:
            return 'request_for_production'
        elif 'report' in filename_lower:
            return 'expert_report'
        else:
            return 'unknown'
    
    def _create_processing_summary(self, processing_id: str) -> Dict[str, Any]:
        """Create processing summary"""
        job = self.processing_jobs[processing_id]
        processing_time = (datetime.utcnow() - job['start_time']).total_seconds()
        
        return {
            'totalDocuments': job['documents_processed'],
            'processedDocuments': job['documents_processed'],
            'totalChunks': job['documents_processed'] * 10,  # Mock value
            'totalVectors': job['documents_processed'] * 10,  # Mock value
            'totalErrors': len(job['errors']),
            'processingTime': processing_time,
            'averageConfidence': 0.92  # Mock value
        }
    
    def get_job_status(self, processing_id: str) -> Optional[Dict[str, Any]]:
        """Get status of a processing job"""
        return self.processing_jobs.get(processing_id)

# Create a global instance that can be used by the API
websocket_processor = None

def get_websocket_processor() -> WebSocketDocumentProcessor:
    """Get or create the WebSocket document processor instance"""
    global websocket_processor
    if websocket_processor is None:
        # This would normally use the actual document injector
        # For now, we'll create a mock processor
        websocket_processor = WebSocketDocumentProcessor(None)
    return websocket_processor