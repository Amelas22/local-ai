"""
Mock discovery endpoint for frontend testing
This file can be added to main.py or run standalone
"""
import asyncio
import uuid
from datetime import datetime
from typing import Dict, Any
from fastapi import BackgroundTasks
from pydantic import BaseModel

# Mock processing function that simulates discovery processing
async def mock_process_discovery(processing_id: str, case_name: str):
    """Simulate discovery processing with WebSocket events"""
    
    # Import WebSocket emitters
    try:
        from src.websocket import (
            emit_discovery_started,
            emit_document_found,
            emit_chunking_progress,
            emit_embedding_progress,
            emit_document_stored,
            emit_processing_completed,
            emit_processing_error
        )
    except ImportError:
        print("WebSocket module not available, using print statements")
        # Define mock emitters
        async def emit_discovery_started(**kwargs):
            print(f"[WS] discovery:started - {kwargs}")
        
        async def emit_document_found(**kwargs):
            print(f"[WS] discovery:document_found - {kwargs}")
        
        async def emit_chunking_progress(**kwargs):
            print(f"[WS] discovery:chunking - {kwargs}")
        
        async def emit_embedding_progress(**kwargs):
            print(f"[WS] discovery:embedding - {kwargs}")
        
        async def emit_document_stored(**kwargs):
            print(f"[WS] discovery:stored - {kwargs}")
        
        async def emit_processing_completed(**kwargs):
            print(f"[WS] discovery:completed - {kwargs}")
        
        async def emit_processing_error(**kwargs):
            print(f"[WS] discovery:error - {kwargs}")
    
    # Emit start event
    await emit_discovery_started(
        processing_id=processing_id,
        case_id=case_name,
        total_files=5
    )
    
    # Simulate processing 5 documents
    mock_documents = [
        {
            "id": f"doc_{i}",
            "name": f"Discovery_Document_{i}.pdf",
            "type": ["motion", "deposition", "interrogatory", "request_for_production", "expert_report"][i],
            "pages": 20 + i * 10,
            "bates_start": f"DEF{str(i * 50 + 1).zfill(6)}",
            "bates_end": f"DEF{str((i + 1) * 50).zfill(6)}"
        }
        for i in range(5)
    ]
    
    for doc in mock_documents:
        # Document found
        await emit_document_found(
            processing_id=processing_id,
            document_id=doc["id"],
            title=doc["name"],
            doc_type=doc["type"],
            page_count=doc["pages"],
            bates_range={"start": doc["bates_start"], "end": doc["bates_end"]},
            confidence=0.85 + (0.03 * len(doc["name"]))
        )
        
        # Simulate chunking
        total_chunks = doc["pages"] // 5
        for chunk_idx in range(total_chunks):
            await asyncio.sleep(0.1)  # Simulate processing time
            progress = ((chunk_idx + 1) / total_chunks) * 100
            
            await emit_chunking_progress(
                processing_id=processing_id,
                document_id=doc["id"],
                progress=progress,
                chunks_created=chunk_idx + 1
            )
        
        # Simulate embedding
        for chunk_idx in range(total_chunks):
            await asyncio.sleep(0.05)  # Simulate processing time
            progress = ((chunk_idx + 1) / total_chunks) * 100
            
            await emit_embedding_progress(
                processing_id=processing_id,
                document_id=doc["id"],
                chunk_id=f"chunk_{doc['id']}_{chunk_idx}",
                progress=progress
            )
        
        # Document stored
        await emit_document_stored(
            processing_id=processing_id,
            document_id=doc["id"],
            vectors_stored=total_chunks
        )
        
        # Small delay between documents
        await asyncio.sleep(0.5)
    
    # Processing completed
    await emit_processing_completed(
        processing_id=processing_id,
        summary={
            "totalDocuments": len(mock_documents),
            "processedDocuments": len(mock_documents),
            "totalChunks": sum(doc["pages"] // 5 for doc in mock_documents),
            "totalVectors": sum(doc["pages"] // 5 for doc in mock_documents),
            "totalErrors": 0,
            "processingTime": 15.5,
            "averageConfidence": 0.91
        }
    )

# Add this endpoint to your main.py file:
"""
@app.post("/discovery/process/mock")
async def process_discovery_mock(
    request: DiscoveryProcessingRequest,
    background_tasks: BackgroundTasks
):
    '''Mock endpoint for testing frontend WebSocket integration'''
    
    processing_id = str(uuid.uuid4())
    
    # Run mock processing in background
    background_tasks.add_task(
        mock_process_discovery,
        processing_id,
        request.case_name
    )
    
    return {
        "processing_id": processing_id,
        "status": "started",
        "message": f"Mock discovery processing started for {request.case_name}",
        "websocket_url": "/ws/socket.io"
    }
"""

# For standalone testing
if __name__ == "__main__":
    async def test():
        await mock_process_discovery("test-123", "Smith_v_Jones_2024")
    
    asyncio.run(test())