# Discovery Processing Feature Implementation Report

## FEATURE:

Comprehensive discovery document processing system that automatically splits concatenated discovery response PDFs, extracts case facts, and provides a real-time review interface for paralegals to verify and edit extracted information. The system provides real-time updates via WebSocket during processing.

### Current Implementation Status

#### ✅ Backend Components Built:
- **Document Splitter** (`discovery_splitter.py`): AI-powered boundary detection using sliding window approach with `DiscoveryProductionProcessor` class
- **Fact Extractor** (`fact_extractor.py`): NLP-based fact extraction with spaCy integration  
- **WebSocket Events**: Real-time event emission implemented
- **Discovery Endpoints** (`discovery_endpoints.py`): REST API accepts file uploads and processes them
- **Case Isolation**: Enforced throughout with case_name filtering

#### ✅ Frontend Components Built:
- **DiscoveryUpload.tsx**: Dual upload zones with Box integration
- **FactReviewPanel.tsx**: Tab-based review interface with filtering
- **FactCard.tsx**: Interactive fact cards with inline editing  
- **PDFViewer.tsx**: PDF rendering with bounding box highlighting
- **useDiscoverySocket.ts**: WebSocket hook for real-time updates

#### 🚨 Critical Implementation Gap Found:

**The current `/api/discovery/process` endpoint is NOT using the document splitting functionality at all!**

Current implementation flow:
1. Frontend uploads PDFs to `/api/discovery/process` ✅
2. Backend receives files and reads them ✅
3. Backend extracts text directly from each PDF ✅
4. Backend extracts facts from the full text ✅
5. WebSocket events are emitted ✅

**What's missing:**
- The `DiscoveryProductionProcessor` class that splits concatenated PDFs is never called
- Each uploaded PDF is treated as a single document
- No boundary detection occurs
- No document segmentation happens
- Facts are extracted from entire PDFs, not individual documents within them

## EXAMPLES:

### Current Implementation (Incorrect):
```python
# From /Clerk/src/api/discovery_endpoints.py - lines 200-278
async def _process_discovery_async(...):
    # Process uploaded files
    for idx, file_data in enumerate(discovery_files or []):
        # Extract text from PDF if it's a PDF file
        if filename.lower().endswith('.pdf'):
            extracted_doc = pdf_extractor.extract_text(content, filename)
            text_content = extracted_doc.text
            
        # Extract facts if enabled (from ENTIRE PDF)
        if enable_fact_extraction and text_content:
            facts = await fact_extractor.extract_facts_from_document(
                document_id=document_id,
                document_content=text_content,  # This is the ENTIRE PDF text!
            )
```

### What Should Be Happening:
```python
# The discovery splitter should be used:
from src.document_processing.discovery_splitter import DiscoveryProductionProcessor

async def _process_discovery_async(...):
    for idx, file_data in enumerate(discovery_files or []):
        if filename.lower().endswith('.pdf'):
            # Save PDF temporarily
            temp_pdf_path = save_temp_file(content)
            
            # Use the discovery splitter!
            processor = DiscoveryProductionProcessor(case_name)
            production_result = processor.process_discovery_production(
                pdf_path=temp_pdf_path,
                production_metadata={
                    "production_batch": production_batch,
                    "producing_party": producing_party,
                }
            )
            
            # Process each segmented document
            for segment in production_result.segments_found:
                # Extract text from this segment only
                segment_text = extract_segment_text(temp_pdf_path, segment)
                
                # Emit document found event
                await sio.emit("discovery:document_found", {
                    "document_type": segment.document_type,
                    "pages": f"{segment.start_page}-{segment.end_page}"
                })
                
                # Extract facts from this individual document
                facts = await fact_extractor.extract_facts_from_document(
                    document_id=f"{document_id}_segment_{segment.start_page}",
                    document_content=segment_text
                )
                
                # Stream facts after each document
                for fact in facts:
                    await sio.emit("discovery:fact_extracted", fact)
```

### Document Boundary Detection Implementation:
```python
# From /Clerk/src/document_processing/discovery_splitter.py
class BoundaryDetector:
    def _detect_boundaries_in_window(self, window_text, start_page, end_page):
        """Uses LLM to identify document boundaries"""
        prompt = f"""Analyze this text from a multi-document PDF...
        Look for indicators like:
        - Headers with document types
        - Date stamps
        - Page numbers restarting
        - Bates numbers
        - Signature blocks
        - Document titles"""
        
        response = self.client.chat.completions.create(
            model=self.model,
            messages=[{"role": "user", "content": prompt}],
            response_format={"type": "json_object"}
        )
```

### Fact Extraction After Splitting:
```python
# From /Clerk/src/ai_agents/fact_extractor.py
class FactExtractor:
    async def extract_facts_from_document(self, document_id, document_content):
        # Split into chunks (1000 chars)
        chunks = self._split_into_chunks(document_content)
        
        for chunk in chunks:
            # LLM extraction
            facts = await self._extract_facts_from_chunk(chunk)
            # NER with spaCy
            entities = self._extract_entities(chunk)
            # Date extraction
            dates = self._extract_dates(chunk)
            
            # Create fact objects with metadata
            for fact_text in facts:
                fact = await self._create_fact(
                    fact_text, document_id, chunk_index, 
                    dates, entities, citations
                )
                collection.add_fact(fact)
```


## DOCUMENTATION:

Use context7 mcp for any documentation that is needed
Use brave-search for any external search to look up best practices and information.

### PDF Document Boundary Detection:
- **Sliding Window Approach**: Process PDFs in overlapping windows to detect boundaries
- **AI-Powered Detection**: Use LLM to identify document separators
- **Boundary Indicators**: Headers, Bates numbers, page restarts, signature blocks
- **Confidence Scoring**: Each boundary has a confidence score for validation

### Document Classification:
```python
# Document types supported:
- DRIVER_QUALIFICATION_FILE
- EMPLOYMENT_APPLICATION  
- BILL_OF_LADING
- MAINTENANCE_RECORD
- HOS_LOG (Hours of Service)
- TRIP_REPORT
- EMAIL_CORRESPONDENCE
- ACCIDENT_INVESTIGATION_REPORT
- DEPOSITION
- MEDICAL_RECORD
- POLICE_REPORT
- INVOICE
- CONTRACT
- OTHER
```

### Fact Extraction Pipeline:
1. **Text Chunking**: Split documents into 1000-character chunks
2. **LLM Extraction**: Extract factual statements using GPT
3. **NER Processing**: Extract entities using spaCy (`en_core_web_sm`)
4. **Date Extraction**: Pattern matching + dateparser library
5. **Citation Extraction**: Legal citation patterns
6. **Fact Categorization**: Classify facts into categories (LIABILITY, DAMAGES, TIMELINE, etc.)

### WebSocket Event Flow:
```javascript
// Events emitted during processing:
socket.on('discovery:started', (data) => {/* Processing began */})
socket.on('discovery:document_found', (data) => {/* Individual doc found in PDF */})
socket.on('discovery:chunking', (data) => {/* Document being chunked */})
socket.on('discovery:fact_extracted', (data) => {/* Fact extracted and ready */})
socket.on('discovery:completed', (data) => {/* All processing done */})
```

### Key Libraries and APIs:
- **pdfplumber**: Extract text with layout preservation
- **PyPDF2**: PDF manipulation and page extraction
- **spaCy**: Named entity recognition for legal documents
- **python-socketio**: Real-time WebSocket communication
- **OpenAI API**: Document boundary detection and fact extraction
- **dateparser**: Flexible date extraction from text

## OTHER CONSIDERATIONS:

### Critical Fix Required:

The `/api/discovery/process` endpoint needs to be modified to use the discovery splitter:

```python
# In discovery_endpoints.py, replace lines 200-278 with:
async def _process_discovery_async(...):
    discovery_processor = DiscoveryProductionProcessor(case_name)
    
    for idx, file_data in enumerate(discovery_files or []):
        # Save PDF temporarily
        import tempfile
        with tempfile.NamedTemporaryFile(suffix='.pdf', delete=False) as tmp:
            tmp.write(file_data['content'])
            temp_path = tmp.name
        
        try:
            # Process with splitter
            result = discovery_processor.process_discovery_production(
                pdf_path=temp_path,
                production_metadata={...}
            )
            
            # Process each segment
            for segment in result.segments_found:
                # Emit events and extract facts per segment
                ...
        finally:
            os.unlink(temp_path)
```

### Performance Optimizations Needed:
1. **Parallel Processing**: Process document segments in parallel
2. **Streaming Facts**: Emit facts as soon as extracted, not after all processing
3. **Memory Management**: Process large PDFs in chunks to avoid memory issues
4. **Progress Tracking**: Report progress per document, not just per PDF

### Testing Considerations:
1. **Test Data**: Need concatenated PDFs with multiple documents
2. **Boundary Cases**: Test PDFs with unclear boundaries
3. **Large Files**: Test with 500+ page discovery productions
4. **Error Handling**: Test with corrupted or encrypted PDFs

### Docker and Deployment:
- Use `start_services_with_postgres.py --profile cpu` for local development. All testing should occur from inside the docker environment as local terminal testing is not needed.
- Docker compose from parent directory to rebuild: `docker compose -p localai --profile cpu -f docker-compose.yml -f docker-compose.clerk.yml -f docker-compose.override.private.yml -f docker-compose.postgres-expose.yml -f docker-compose.clerk-jwt.yml build clerk --no-cache`
- Ensure spaCy models are installed in Docker image: `RUN python -m spacy download en_core_web_sm`

### Security and Case Isolation:
- Every operation must include `case_name` filter
- Facts stored in case-specific collections: `{case_name}_facts`
- Validate case access through middleware
- No cross-case data leakage in WebSocket events

### Missing Environment Variables:
```bash
# Add to .env:
DISCOVERY_WINDOW_SIZE=10
DISCOVERY_WINDOW_OVERLAP=2
DISCOVERY_BOUNDARY_CONFIDENCE_THRESHOLD=0.8
DISCOVERY_BOUNDARY_DETECTION_MODEL=gpt-4
DISCOVERY_CLASSIFICATION_MODEL=gpt-4.1-mini
```

### Alternative Implementations Found:
- **Normalized Endpoints** (`/api/discovery/process/normalized`): Uses hierarchical document structure but not connected to main flow
- **Legacy Endpoints** (`/api/discovery/process/legacy`): Backward compatibility layer, also not in use
- **WebSocket Processor**: Uses `UnifiedDocumentInjector` instead of discovery splitter

### Immediate Action Items:
1. Integrate `DiscoveryProductionProcessor` into the main processing flow
2. Ensure facts are streamed after each document segment, not after entire PDF
3. Update WebSocket events to include document boundary information
4. Add progress tracking at the segment level
5. Test with real concatenated discovery PDFs