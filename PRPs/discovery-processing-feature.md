# Discovery Processing Feature Implementation PRP

## Overview
This PRP guides the implementation of the missing integration between the discovery processing endpoint and the document splitting functionality. The core issue is that `/api/discovery/process` currently treats each uploaded PDF as a single document instead of splitting concatenated discovery response PDFs into individual documents.

## Context and Background

### Current State
- **Working**: Discovery endpoints accept uploads, extract text, extract facts, emit WebSocket events
- **Not Working**: Document splitting, segment processing, proper document storage in Qdrant
- **Critical Gap**: The `NormalizedDiscoveryProductionProcessor` exists but is never called

### Key Files to Reference
1. **Discovery Endpoint**: `/mnt/c/Users/jlemr/Test2/local-ai-package/Clerk/src/api/discovery_endpoints.py` (lines 162-317)
2. **Discovery Splitter**: `/mnt/c/Users/jlemr/Test2/local-ai-package/Clerk/src/document_processing/discovery_splitter_normalized.py`
3. **Document Injector Pattern**: `/mnt/c/Users/jlemr/Test2/local-ai-package/Clerk/src/document_injector_unified.py`
4. **WebSocket Patterns**: `/mnt/c/Users/jlemr/Test2/local-ai-package/Clerk/src/document_processing/websocket_document_processor.py`

## Implementation Blueprint

### Phase 1: Update Imports and Dependencies
In `/Clerk/src/api/discovery_endpoints.py`, add these imports:
```python
from src.document_processing.discovery_splitter_normalized import (
    NormalizedDiscoveryProductionProcessor,
    NormalizedDiscoveryDocumentProcessor,
    DiscoverySegment,
)
from src.document_processing.unified_document_manager import UnifiedDocumentManager
from src.document_processing.enhanced_chunker import EnhancedChunker
from src.vector_storage.embeddings import EmbeddingGenerator
from src.models.unified_document_models import DocumentType, UnifiedDocument
import tempfile
import os
```

### Phase 2: Refactor _process_discovery_async Function

Replace the current implementation (lines 162-317) with the following pseudocode approach:

```python
async def _process_discovery_async(
    case_name: str,
    processing_id: str,
    discovery_files: List[Dict[str, Any]],
    producing_party: Optional[str] = None,
    production_batch: Optional[str] = None,
    enable_fact_extraction: bool = True,
):
    # Initialize processors
    discovery_processor = NormalizedDiscoveryProductionProcessor(case_name)
    document_manager = UnifiedDocumentManager(case_name, vector_store)
    fact_extractor = FactExtractor() if enable_fact_extraction else None
    chunker = EnhancedChunker(chunk_size=1400, chunk_overlap=200)
    embedding_generator = EmbeddingGenerator()
    
    # Track processing status
    processing_status = {
        "processing_id": processing_id,
        "status": "in_progress",
        "total_documents_found": 0,
        "documents_processed": 0,
        "facts_extracted": 0,
        "errors": []
    }
    
    try:
        # Emit start event
        await sio.emit("discovery:started", {
            "processing_id": processing_id,
            "case_name": case_name,
            "total_files": len(discovery_files or [])
        })
        
        # Process each uploaded PDF
        for idx, file_data in enumerate(discovery_files or []):
            filename = file_data.get("filename", f"discovery_{idx}.pdf")
            content = file_data.get("content", b"")
            
            # Save PDF temporarily
            with tempfile.NamedTemporaryFile(suffix='.pdf', delete=False) as tmp_file:
                tmp_file.write(content)
                temp_pdf_path = tmp_file.name
            
            try:
                # Create discovery request
                discovery_request = DiscoveryProcessingRequest(
                    production_batch=production_batch or f"batch_{idx}",
                    producing_party=producing_party or "Unknown",
                    bates_prefix=f"PROD{idx:04d}",
                    enable_boundary_detection=True,
                    enable_classification=True,
                    enable_fact_extraction=enable_fact_extraction,
                )
                
                # Process with discovery splitter
                logger.info(f"Processing discovery production: {filename}")
                production_result = await discovery_processor.process_production_normalized(
                    pdf_path=temp_pdf_path,
                    case_id=case_name,
                    discovery_request=discovery_request
                )
                
                # Update total documents found
                processing_status["total_documents_found"] += len(production_result.segments_found)
                
                # Process each segment as a separate document
                for segment_idx, segment in enumerate(production_result.segments_found):
                    try:
                        # Emit document found event
                        await sio.emit("discovery:document_found", {
                            "processing_id": processing_id,
                            "document_id": f"{processing_id}_seg_{segment_idx}",
                            "title": segment.title or f"Document {segment.document_type}",
                            "type": segment.document_type.value,
                            "pages": f"{segment.start_page}-{segment.end_page}",
                            "bates_range": segment.bates_range,
                            "confidence": segment.confidence_score
                        })
                        
                        # Extract text for this segment
                        pdf_extractor = PDFExtractor()
                        segment_text = pdf_extractor.extract_text_from_pages(
                            temp_pdf_path, 
                            segment.start_page, 
                            segment.end_page
                        )
                        
                        # Check for duplicates
                        doc_hash = document_manager.generate_document_hash(segment_text)
                        if await document_manager.is_duplicate(doc_hash):
                            logger.info(f"Skipping duplicate document: {segment.title}")
                            continue
                        
                        # Create unified document
                        unified_doc = UnifiedDocument(
                            case_name=case_name,
                            source_path=f"discovery/{production_batch}/{segment.title}",
                            filename=f"{segment.title}.pdf",
                            file_type="pdf",
                            title=segment.title or f"{segment.document_type} Document",
                            text=segment_text,
                            metadata={
                                "document_type": segment.document_type.value,
                                "producing_party": producing_party,
                                "production_batch": production_batch,
                                "bates_range": segment.bates_range,
                                "page_range": f"{segment.start_page}-{segment.end_page}",
                                "confidence_score": segment.confidence_score,
                                "processing_id": processing_id,
                            },
                            document_hash=doc_hash,
                            processing_status="completed",
                            created_at=datetime.utcnow()
                        )
                        
                        # Store document metadata
                        doc_id = await document_manager.add_document(unified_doc)
                        
                        # Create chunks with context
                        await sio.emit("discovery:chunking", {
                            "processing_id": processing_id,
                            "document_id": doc_id,
                            "status": "started"
                        })
                        
                        chunks = chunker.create_chunks_with_context(
                            text=segment_text,
                            document_id=doc_id,
                            metadata=unified_doc.metadata
                        )
                        
                        # Generate embeddings and store chunks
                        await sio.emit("discovery:embedding", {
                            "processing_id": processing_id,
                            "document_id": doc_id,
                            "total_chunks": len(chunks)
                        })
                        
                        for chunk_idx, chunk in enumerate(chunks):
                            # Generate embedding
                            embedding = await embedding_generator.generate_embedding(chunk.text)
                            
                            # Store in Qdrant
                            await vector_store.upsert_chunk(
                                case_name=case_name,
                                chunk_id=chunk.chunk_id,
                                text=chunk.text,
                                embedding=embedding,
                                metadata={
                                    **chunk.metadata,
                                    "chunk_index": chunk_idx,
                                    "total_chunks": len(chunks)
                                }
                            )
                        
                        # Extract facts if enabled
                        if enable_fact_extraction and fact_extractor:
                            facts = await fact_extractor.extract_facts_from_document(
                                document_id=doc_id,
                                document_content=segment_text,
                                document_type=segment.document_type.value,
                                metadata={
                                    "bates_range": segment.bates_range,
                                    "producing_party": producing_party,
                                    "production_batch": production_batch
                                }
                            )
                            
                            # Stream facts as they're extracted
                            for fact in facts:
                                await sio.emit("discovery:fact_extracted", {
                                    "processing_id": processing_id,
                                    "document_id": doc_id,
                                    "fact": fact.dict()
                                })
                                processing_status["facts_extracted"] += 1
                        
                        # Update processed count
                        processing_status["documents_processed"] += 1
                        
                    except Exception as segment_error:
                        logger.error(f"Error processing segment {segment_idx}: {str(segment_error)}")
                        processing_status["errors"].append({
                            "segment": segment_idx,
                            "error": str(segment_error)
                        })
                        
                        await sio.emit("discovery:error", {
                            "processing_id": processing_id,
                            "document_id": f"{processing_id}_seg_{segment_idx}",
                            "error": str(segment_error)
                        })
                        
            finally:
                # Clean up temp file
                if os.path.exists(temp_pdf_path):
                    os.unlink(temp_pdf_path)
        
        # Update final status
        processing_status["status"] = "completed"
        processing_status["completed_at"] = datetime.utcnow().isoformat()
        
        # Emit completion event
        await sio.emit("discovery:completed", processing_status)
        
        # Store processing result
        await store_processing_result(processing_id, processing_status)
        
    except Exception as e:
        logger.error(f"Error in discovery processing: {str(e)}")
        processing_status["status"] = "failed"
        processing_status["error"] = str(e)
        
        await sio.emit("discovery:error", {
            "processing_id": processing_id,
            "error": str(e)
        })
```

### Phase 3: Add Helper Functions

Add these helper functions to support the main processing:

```python
def extract_text_from_pages(pdf_path: str, start_page: int, end_page: int) -> str:
    """Extract text from specific page range in PDF."""
    text = ""
    with pdfplumber.open(pdf_path) as pdf:
        for page_num in range(start_page - 1, min(end_page, len(pdf.pages))):
            page = pdf.pages[page_num]
            page_text = page.extract_text() or ""
            text += page_text + "\n"
    return text

async def store_processing_result(processing_id: str, result: Dict[str, Any]):
    """Store processing result for retrieval."""
    # Implementation depends on your storage mechanism
    # Could use Redis, database, or in-memory cache
    pass
```

### Phase 4: Update WebSocket Event Structure

Ensure WebSocket events follow this structure:

```python
# discovery:started
{
    "processing_id": str,
    "case_name": str,
    "total_files": int
}

# discovery:document_found  
{
    "processing_id": str,
    "document_id": str,
    "title": str,
    "type": str,  # DocumentType enum value
    "pages": str,  # "1-10"
    "bates_range": str,  # "PROD0001-PROD0010"
    "confidence": float
}

# discovery:fact_extracted
{
    "processing_id": str,
    "document_id": str,
    "fact": {
        "fact_id": str,
        "text": str,
        "category": str,
        "confidence": float,
        "entities": List[str],
        "dates": List[str],
        "source_metadata": dict
    }
}

# discovery:completed
{
    "processing_id": str,
    "status": "completed",
    "total_documents_found": int,
    "documents_processed": int,
    "facts_extracted": int,
    "errors": List[dict]
}
```

## Implementation Tasks (In Order)

1. **Update imports in discovery_endpoints.py**
   - Add all required imports listed in Phase 1
   - Ensure all dependencies are available

2. **Create temporary file handling utility**
   - Safe temporary file creation and cleanup
   - Error handling for file operations

3. **Implement extract_text_from_pages helper**
   - Extract text from specific page ranges
   - Handle PDF reading errors gracefully

4. **Refactor _process_discovery_async function**
   - Replace current implementation with new flow
   - Maintain backward compatibility with existing parameters

5. **Integrate document storage**
   - Use UnifiedDocumentManager for deduplication
   - Store documents and chunks in Qdrant

6. **Enhance WebSocket events**
   - Add new event types for document discovery
   - Include progress tracking at segment level

7. **Add error handling and recovery**
   - Continue processing other documents on segment failure
   - Collect and report all errors at the end

8. **Create unit tests**
   - Test document splitting with multi-document PDFs
   - Test fact extraction per segment
   - Test WebSocket event emission
   - Test error handling scenarios
   - Always test from inside the docker tech stack, even if its just launching qdrant, clerk, and postgres

9. **Update environment variables**
   - Add configuration for discovery processing
   - Document new settings in README

## Validation Gates

Execute these commands to validate the implementation:

```bash
# 1. Syntax and style check
cd /mnt/c/Users/jlemr/Test2/local-ai-package/Clerk
ruff check src/api/discovery_endpoints.py --fix
ruff format src/api/discovery_endpoints.py

# 2. Type checking
mypy src/api/discovery_endpoints.py

# 3. Run unit tests for discovery
pytest src/api/tests/test_discovery_endpoints.py -v

# 4. Integration test with Docker
# First rebuild the container
cd /mnt/c/Users/jlemr/Test2/local-ai-package
docker compose -p localai --profile cpu -f docker-compose.yml -f docker-compose.clerk.yml build clerk

# Then run the container and test
docker compose -p localai --profile cpu -f docker-compose.yml -f docker-compose.clerk.yml up clerk

# 5. Test with a sample multi-document PDF
# Create a test script to upload a concatenated PDF and verify:
# - Multiple documents are found
# - Facts are extracted per document
# - WebSocket events are emitted correctly
# - Documents are stored in Qdrant
```

## External Documentation References

1. **Python SocketIO Async Documentation**: https://python-socketio.readthedocs.io/en/latest/server.html
   - Reference for async event emission patterns
   - Best practices for real-time updates

2. **Memory-Efficient PDF Processing**: https://dev.to/josethz00/partitioning-large-pdf-files-with-python-and-unstructuredio-3bkg
   - Techniques for handling large PDFs
   - Chunking strategies to avoid memory issues

3. **FastAPI WebSocket Integration**: https://fastapi.tiangolo.com/advanced/websockets/
   - WebSocket handling in FastAPI
   - Error handling patterns

4. **PDF Chunking for RAG**: https://medium.com/@mahedi154/automated-pdf-content-extraction-and-chunking-with-python-d8f8012defda
   - Best practices for maintaining context
   - Overlap strategies for better retrieval

## Common Pitfalls to Avoid

1. **Memory Management**: Process PDFs in chunks, don't load entire file into memory
2. **Case Isolation**: Always filter by case_name in all operations
3. **Duplicate Handling**: Check document hash before processing
4. **Error Recovery**: Don't fail entire batch if one document fails
5. **WebSocket Buffering**: Stream events as they occur, don't batch
6. **Temporary Files**: Always clean up temp files in finally blocks
7. **Bates Numbering**: Preserve original Bates numbers from discovery

## Testing Data Requirements

For proper testing, you'll need:
1. A concatenated PDF with 3-5 different documents
2. Documents with clear boundaries (headers, page numbers)
3. Documents with unclear boundaries to test confidence scoring
4. A large PDF (100+ pages) to test memory efficiency
5. PDFs with various document types (depositions, emails, reports)

## Performance Considerations

1. **Parallel Processing**: Consider processing segments in parallel using asyncio.gather()
2. **Streaming**: Emit facts as soon as extracted, not after all processing
3. **Chunking**: Use sliding window for boundary detection to avoid loading entire PDF
4. **Caching**: Cache embeddings for duplicate text segments
5. **Progress Tracking**: Report progress at segment level, not just file level

## Success Criteria

The implementation is successful when:
1. Multi-document PDFs are properly split into segments
2. Each segment is processed as a separate document
3. Facts are extracted per segment, not per PDF
4. Documents and chunks are stored in Qdrant
5. WebSocket events provide real-time progress updates
6. Duplicate documents are detected and skipped
7. Errors in one segment don't stop processing of others
8. All tests pass and code follows project conventions

## Confidence Score: 8.5/10

This PRP provides comprehensive context and clear implementation steps. The score is not 10 because:
- Some integration details with the existing WebSocket infrastructure may require minor adjustments
- The exact structure of some models might need verification during implementation
- Performance optimization for very large PDFs might require additional tuning

However, with the provided context, patterns, and validation gates, a one-pass implementation should be achievable.