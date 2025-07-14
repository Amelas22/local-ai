# Discovery Document Splitting Integration Verification

## FEATURE:

Verify and debug the existing discovery document splitting integration to ensure multi-document PDFs are properly split into individual documents with per-document processing and WebSocket events. The integration code exists but needs verification that:

1. Document boundaries are correctly detected using AI (gpt-4.1-mini)
2. Each segment is processed as a separate document
3. WebSocket events are emitted for each document (not just the entire PDF)
4. Frontend receives and displays tabs for each discovered document
5. Facts are correctly attributed to their source documents

**Current State**: The backend code already imports and uses `DiscoveryProductionProcessor`, but testing shows only one tab appearing in the frontend instead of 18+ for the test PDF.

## IMPLEMENTATION BLUEPRINT

The integration is already implemented at line 263 of `discovery_endpoints.py`:
```python
# Line 263-264: Already using the discovery processor!
from src.document_processing.discovery_splitter import DiscoveryProductionProcessor
discovery_processor = DiscoveryProductionProcessor(case_name=case_name)

# Line 319-322: Already calling the splitter!
production_result = discovery_processor.process_discovery_production(
    pdf_path=temp_pdf_path,
    production_metadata=production_metadata
)

# Line 328-339: Already processing each segment!
for segment_idx, segment in enumerate(production_result.segments_found):
    # Emits discovery:document_found for EACH segment
    await sio.emit("discovery:document_found", {
        "processing_id": processing_id,
        "document_id": f"{processing_id}_seg_{segment_idx}",
        "title": segment.title or f"Document {segment.document_type}",
        "type": segment.document_type.value,
        "pages": f"{segment.start_page}-{segment.end_page}",
        "bates_range": segment.bates_range,
        "confidence": segment.confidence_score
    })
```

**Verification Steps**:
1. Add detailed logging to trace document discovery
2. Verify WebSocket events are reaching the frontend
3. Check if the AI boundary detection is working
4. Test with the OCR'd PDF (`tesdoc_Redacted_ocr.pdf`)
5. Monitor WebSocket events in browser DevTools

## EXAMPLES

### Current Working Code (Already Implemented)
```python
# src/api/discovery_endpoints.py - Lines 319-476
# This code ALREADY splits documents and processes them individually!

# 1. Split the PDF into segments
production_result = discovery_processor.process_discovery_production(
    pdf_path=temp_pdf_path,
    production_metadata=production_metadata
)

# 2. Process EACH segment separately
for segment_idx, segment in enumerate(production_result.segments_found):
    # Emit document found event
    await sio.emit("discovery:document_found", {...})
    
    # Extract text for THIS segment only
    segment_text = extract_text_from_pages(
        temp_pdf_path, 
        segment.start_page, 
        segment.end_page
    )
    
    # Create chunks for THIS segment
    chunks = chunker.create_chunks_with_context(
        text=segment_text,
        document_id=doc_id,
        metadata=unified_doc.metadata
    )
    
    # Extract facts for THIS segment
    if enable_fact_extraction and fact_extractor:
        facts_result = await fact_extractor.extract_facts_from_document(
            document_id=doc_id,
            document_content=segment_text,
            document_type=segment.document_type.value
        )
```

### Debugging Additions Needed
```python
# Add logging to verify segments are found
logger.info(f"Discovery processor found {len(production_result.segments_found)} segments")
for idx, segment in enumerate(production_result.segments_found):
    logger.info(f"Segment {idx}: {segment.title} - Pages {segment.start_page}-{segment.end_page}")

# Add WebSocket event logging
logger.info(f"Emitting discovery:document_found for segment {segment_idx}: {segment.title}")
await sio.emit("discovery:document_found", event_data)

# Verify AI model is being used
logger.info(f"BoundaryDetector using model: {self.model}")
```

### Frontend WebSocket Handler (Should Already Work)
```typescript
// frontend/src/hooks/useEnhancedDiscoverySocket.ts
socket.on('discovery:document_found', (data) => {
    dispatch(addDocument({
        id: data.document_id,
        title: data.title,
        type: data.type,
        batesRange: data.bates_range,
        pageCount: parseInt(data.pages?.split('-')[1] || '0'),
        confidence: data.confidence,
        status: 'pending',
        progress: 0,
    }));
});
```

### Test Script to Verify WebSocket Events
```python
# test_websocket_events.py
import asyncio
import socketio

sio = socketio.AsyncClient()

@sio.on('discovery:document_found')
async def on_document_found(data):
    print(f"📄 Document Found: {data.get('title')} - ID: {data.get('document_id')}")

@sio.on('discovery:started')
async def on_started(data):
    print(f"🚀 Discovery Started: {data.get('processing_id')}")

async def main():
    await sio.connect('http://localhost:8000')
    print("Connected to WebSocket")
    await sio.wait()

if __name__ == '__main__':
    asyncio.run(main())
```

## DOCUMENTATION

### Key Source Files (All Already Have Integration!)
1. **`/app/src/api/discovery_endpoints.py`** (Lines 244-522)
   - Already imports DiscoveryProductionProcessor
   - Already processes segments individually
   - Already emits per-document events

2. **`/app/src/document_processing/discovery_splitter.py`**
   - BoundaryDetector class with AI integration
   - DiscoveryProductionProcessor.process_discovery_production()
   - Returns DiscoveryProductionResult with segments_found

3. **Frontend Components** (Ready to receive events)
   - `/app/frontend/src/components/discovery/EnhancedFactReviewPanel.tsx`
   - `/app/frontend/src/hooks/useEnhancedDiscoverySocket.ts`
   - `/app/frontend/src/store/slices/discoverySlice.ts`

### External Documentation
- **FastAPI BackgroundTasks**: https://fastapi.tiangolo.com/tutorial/background-tasks/
- **python-socketio Events**: https://python-socketio.readthedocs.io/en/latest/server.html#emitting-events
- **pdfplumber Page Extraction**: https://github.com/jsvine/pdfplumber#extracting-text

### MCP Tools Available
- `mcp__brave-search__brave_web_search` - For debugging WebSocket issues
- `mcp__context7__get-library-docs` - For library documentation

## TASKS TO COMPLETE

### 1. Add Comprehensive Logging
```python
# In discovery_endpoints.py, add after line 319:
logger.info(f"Processing PDF with discovery splitter: {filename}")
logger.info(f"Production metadata: {production_metadata}")

# After line 322:
logger.info(f"Discovery result: {len(production_result.segments_found)} segments found")
logger.info(f"Average confidence: {production_result.average_confidence}")
for idx, seg in enumerate(production_result.segments_found):
    logger.info(f"  Segment {idx}: {seg.document_type.value} '{seg.title}' pages {seg.start_page}-{seg.end_page}")

# Before line 331 (WebSocket emit):
logger.info(f"Emitting discovery:document_found for segment {segment_idx}")
```

### 2. Verify AI Model Configuration
```python
# In discovery_splitter.py, add to __init__:
logger.info(f"BoundaryDetector initialized with:")
logger.info(f"  Model: {self.model}")
logger.info(f"  Window size: {self.default_window_size}")
logger.info(f"  Window overlap: {self.default_window_overlap}")
logger.info(f"  Confidence threshold: {self.confidence_threshold}")
```

### 3. Create WebSocket Event Monitor
```python
# In websocket/socket_server.py or main.py, add:
@sio.on('*')
async def catch_all(event, data):
    logger.debug(f"WebSocket Event: {event} - Data keys: {list(data.keys()) if isinstance(data, dict) else type(data)}")
```

### 4. Test with Actual PDF
```bash
# Inside Docker container
cd /app
python -c "
from src.document_processing.discovery_splitter import DiscoveryProductionProcessor
processor = DiscoveryProductionProcessor('test_case')
result = processor.process_discovery_production(
    'tesdoc_Redacted_ocr.pdf',
    {'production_batch': 'TEST001'}
)
print(f'Found {len(result.segments_found)} segments')
for s in result.segments_found:
    print(f'  - {s.title}: pages {s.start_page}-{s.end_page}')
"
```

### 5. Frontend Console Logging
```javascript
// Add to useEnhancedDiscoverySocket.ts
const handleDocumentFound = useCallback((data: any) => {
    console.log('📄 Document Found Event:', data);
    // ... existing code
}, [dispatch]);
```

### 6. Verify Environment Variables
```bash
# Check these are set in .env:
echo $DISCOVERY_BOUNDARY_MODEL  # Should be: gpt-4.1-mini
echo $DISCOVERY_WINDOW_SIZE      # Should be: 5
echo $DISCOVERY_WINDOW_OVERLAP   # Should be: 1
echo $DISCOVERY_CONFIDENCE_THRESHOLD  # Should be: 0.7
```

### 7. Browser DevTools Monitoring
```javascript
// In browser console while on discovery page:
window.__SOCKET_IO__ = window.io.connect();
window.__SOCKET_IO__.on('discovery:document_found', (data) => {
    console.log('Document Found:', data);
});
window.__SOCKET_IO__.on('discovery:started', (data) => {
    console.log('Discovery Started:', data);
});
```

## OTHER CONSIDERATIONS

### Critical Debugging Points
1. **Model Name**: Verify `gpt-4.1-mini` is being used (NOT `gpt-4o-mini`)
2. **PDF Has OCR**: Test file must be `tesdoc_Redacted_ocr.pdf` (not the non-OCR version)
3. **WebSocket Connection**: Frontend must be connected before processing starts
4. **Case Context**: Ensure X-Case-ID header is present in requests

### Common Issues to Check
1. **WebSocket Not Connected**
   - Check browser console for connection errors
   - Verify CORS settings allow WebSocket connections

2. **AI Model Not Responding**
   - Check OpenAI API key is valid
   - Monitor for rate limiting
   - Check network connectivity from Docker

3. **Frontend Not Updating**
   - Check Redux DevTools for state changes
   - Verify event handlers are registered
   - Check for JavaScript errors

### Docker Commands
```bash
# Access container
docker-compose -p localai exec clerk bash

# View logs
docker-compose -p localai logs -f clerk | grep -i discovery

# Test WebSocket connection
docker-compose -p localai exec clerk python -c "
import socketio
sio = socketio.Client()
sio.connect('http://localhost:8000')
print('WebSocket connected:', sio.connected)
"
```

### Performance Monitoring
- Log processing time for each segment
- Monitor memory usage for large PDFs
- Track AI API response times

### Testing Sequence
1. Clear all logs
2. Upload `tesdoc_Redacted_ocr.pdf`
3. Monitor Docker logs for segment discovery
4. Check browser DevTools Network tab for WebSocket frames
5. Verify Redux state shows multiple documents
6. Check UI shows multiple tabs

## VALIDATION GATES

```bash
# 1. Verify splitter works standalone
docker-compose -p localai exec clerk python -m pytest src/document_processing/tests/test_discovery_splitter.py -xvs

# 2. Check WebSocket events
docker-compose -p localai exec clerk python test_websocket_events.py &
# Then upload a PDF and watch for events

# 3. Integration test
docker-compose -p localai exec clerk python -m pytest src/api/tests/test_discovery_integration.py -xvs

# 4. Check logs for segment discovery
docker-compose -p localai logs clerk | grep "segments found"

# 5. Verify frontend receives events
# Open browser DevTools > Network > WS tab
# Look for "discovery:document_found" messages
```

## SUCCESS CRITERIA

1. ✅ Logs show 18+ segments discovered from test PDF
2. ✅ WebSocket emits 18+ `discovery:document_found` events
3. ✅ Frontend Redux state contains 18+ documents
4. ✅ UI displays 18+ tabs (one per document)
5. ✅ Each tab shows its own processing progress
6. ✅ Facts appear in correct document tabs
7. ✅ No errors in Docker logs or browser console

## CONFIDENCE SCORE: 9/10

The integration code is already present and well-structured. The issue is likely a configuration or debugging problem rather than missing implementation. With proper logging and verification steps, this should be resolved quickly.