## FEATURE:

Complete the backend integration of document splitting and per-document processing for the discovery feature. The frontend is fully implemented with tab-based document processing, but the backend needs to integrate the NormalizedDiscoveryProductionProcessor to split concatenated PDFs into individual documents and emit granular WebSocket events for each document's processing stages.

What's Missing - The Integration:

The gap is in the discovery endpoint (discovery_endpoints.py). Currently it:

# Current flow in discovery_endpoints.py:
async def _process_discovery_async(...):
      # 1. Saves the PDF file
      # 2. Processes it as ONE document
      # 3. Extracts ALL text at once
      # 4. Creates chunks from entire PDF
      # 5. Extracts facts from entire PDF

But it should do:

# What it needs to do:
async def _process_discovery_async(...):
      # 1. Save the PDF file
      # 2. Call the splitter we built:
      processor = DiscoveryProductionProcessor(case_name)
      result = processor.process_discovery_production(pdf_path, metadata)
      # result.segments_found contains our 18+ documents!

      # 3. Process EACH segment separately:
      for segment in result.segments_found:
          # Emit "document_found" for THIS segment
          # Extract text from ONLY pages segment.start_page to segment.end_page
          # Create chunks for THIS segment
          # Extract facts for THIS segment
          # Emit progress events for THIS segment

The Missing Integration Code:

The discovery endpoint needs to:

1. Import and use our splitter:
from src.document_processing.discovery_splitter import DiscoveryProductionProcessor
2. Call it to get segments:
processor = DiscoveryProductionProcessor(case_name)
result = processor.process_discovery_production(pdf_path, metadata)
3. Loop through segments instead of processing the whole PDF:
for segment in result.segments_found:
     # Process this segment as its own document

Why This Matters:

Without this integration:
- Frontend shows only ONE tab (for the entire PDF)
- ALL facts appear in that single tab
- No way to see which facts came from which document

## EXAMPLES:

Current Discovery Endpoint (Needs Enhancement)

# src/api/discovery_endpoints.py - Current implementation treats PDF as single document
@router.post("/process")
async def process_discovery(
      request: Request,
      background_tasks: BackgroundTasks,
      case_context: CaseContext = Depends(get_case_context),
  ):
      # Currently processes entire PDF as one document
      # NEEDS: Integration with NormalizedDiscoveryProductionProcessor

Working Document Splitter Implementation

# src/document_processing/discovery_splitter_normalized.py
class NormalizedDiscoveryProductionProcessor:
      def process_production_normalized(self, pdf_path: str, production_metadata: Dict) -> DiscoveryProductionResult:
          """Process discovery PDF and return normalized segments"""
          # This already implements AI-powered boundary detection
          # Returns: DiscoveryProductionResult with segments_found list

WebSocket Event Pattern from Frontend

// Frontend expects these events per document:
socket.on('discovery:document_found', (data) => {
      // data: { document_id, title, type, bates_range, confidence }
  });

socket.on('discovery:document_processing', (data) => {
      // data: { document_id, stage: 'chunking'|'embedding'|'extracting_facts', progress }
  });

socket.on('discovery:fact_extracted', (data) => {
      // data: { document_id, fact: { fact_id, text, category, confidence } }
  });

## Fact Storage Pattern

# src/ai_agents/fact_extractor.py
  class FactExtractor:
      async def extract_facts_from_document(
          self,
          document_id: str,
          document_content: str,
          document_type: str = "general"
      ) -> List[CaseFact]:
          # Already extracts facts - needs to be called per segment

## Required Processing Flow

# Pseudo-code for the needed implementation
async def _process_discovery_async(...):
      # 1. Initialize processor
      processor = NormalizedDiscoveryProductionProcessor(case_name)

      # 2. Process PDF to get segments
      result = processor.process_production_normalized(pdf_path, metadata)

      # 3. For each segment found:
      for segment in result.segments_found:
          # Emit document found
          await sio.emit("discovery:document_found", {
              "document_id": f"doc_{segment.start_page}",
              "title": segment.title,
              "type": segment.document_type.value,
              "bates_range": segment.bates_range,
              "confidence": segment.confidence_score
          })

          # Process segment as individual document
          # Extract text from segment pages
          # Chunk, embed, extract facts
          # Emit progress events for THIS document

## DOCUMENTATION:

### Available MCP Tools:

  - mcp__brave-search__brave_web_search: For searching implementation examples and best practices
  - mcp__context7__get-library-docs: For library documentation (FastAPI, pdfplumber, etc.)

### Key Source Files to Reference:

  1. /app/src/api/discovery_endpoints.py - Main endpoint needing integration
  2. /app/src/document_processing/discovery_splitter_normalized.py - Document splitter to integrate
  3. /app/src/models/discovery_models.py - Data models for discovery processing
  4. /app/src/websocket/socket_server.py - WebSocket event emission
  5. /app/src/ai_agents/fact_extractor.py - Fact extraction per document
  6. /app/CLAUDE.md - Project conventions and patterns
  7. /app/PRPs/discovery-processing-feature.md - Original feature specification

### Frontend Implementation Reference:

  1. /app/frontend/src/components/discovery/DocumentProcessingTab.tsx - Shows expected events
  2. /app/frontend/src/hooks/useEnhancedDiscoverySocket.ts - WebSocket event handlers
  3. /app/frontend/src/store/slices/discoverySlice.ts - State management for documents

### Libraries Documentation Needed:

  - pdfplumber: For PDF page extraction and text reading
  - FastAPI BackgroundTasks: For async processing
  - python-socketio: For WebSocket event emission patterns

## OTHER CONSIDERATIONS:

### Critical Implementation Details:

1. Model Name: Use gpt-4.1-mini for boundary detection
2. Environment Variables:
DISCOVERY_BOUNDARY_MODEL=gpt-4.1-mini
DISCOVERY_WINDOW_SIZE=5
DISCOVERY_WINDOW_OVERLAP=1
DISCOVERY_CONFIDENCE_THRESHOLD=0.7

### Docker Container Context:

- Run all commands inside the Clerk container: docker-compose -p localai exec clerk bash
- The container name is clerk (not localai-clerk-1)
- Test with actual PDF from /app/tesdoc_Redacted_ocr.pdf

### Testing Requirements:

1. Run tests early and often:
docker-compose -p localai exec clerk python -m pytest src/api/tests/test_discovery_endpoints.py -v
2. Verify WebSocket events:
    - Use logging to confirm each document emits its own events
    - Check that facts are attributed to correct document_id
3. Test with multi-document PDF:
    - Use /app/tesdoc_Redacted_ocr.pdf which contains multiple documents
    - Should create 18+ separate document tabs based on previous testing

### Common Pitfalls to Avoid:

  1. Don't process entire PDF as one document - Must split first
  2. Don't emit all facts at once - Stream them as extracted per document
  3. Don't forget document-level progress - Each document needs its own progress events
  4. Don't use mock PDFs - Test with real OCR'd PDFs that have extractable text
  5. Maintain backward compatibility - Existing single-document processing should still work

### State Management:

- Track processing state per document, not just globally
- Ensure document IDs are consistent throughout processing
- Handle partial failures (one document fails, others continue)

### Performance Considerations:

- Process documents in parallel where possible
- Emit events immediately, don't batch
- Use streaming for large PDFs to avoid memory issues

### Success Criteria:

1. Multi-document PDFs create multiple tabs in the UI
2. Each tab shows its own processing progress
3. Facts appear in the correct document's tab
4. WebSocket events follow the expected pattern
5. All existing tests pass plus new document-splitting tests
