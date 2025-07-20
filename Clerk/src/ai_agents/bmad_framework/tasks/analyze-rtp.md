# Analyze RTP Document

## Purpose
Parse and analyze Request to Produce (RTP) documents to extract individual requests, categorize them, and prepare for deficiency analysis.

## Task Execution

### 1. Validate Input Parameters
- Ensure case_name is provided for case isolation
- Verify RTP document ID or file path
- Check user has read permission for the case
- Validate document exists in case context

### 2. Load RTP Document
- Retrieve document from storage (Box or local)
- Verify document is associated with correct case
- Check document format (PDF expected)
- Log document access for audit trail

### 3. Initialize RTP Parser
- Import RTPParser from document_processing.rtp_parser
- Configure parser with case-specific settings
- Set confidence threshold for request extraction
- Enable detailed logging for parsing process

### 4. Parse RTP Document
- Extract all requests using pattern matching
- Identify request numbers and sub-requests
- Categorize requests by type:
  - Documents
  - Communications (emails, letters)
  - Electronically stored information
  - Tangible things
  - Other/General
- Track page ranges for each request
- Calculate confidence scores

### 5. Process Extracted Requests
For each extracted request:
- Clean and normalize request text
- Identify cross-references to other requests
- Detect date ranges mentioned
- Extract specific document types requested
- Note any conditional language or exceptions

### 6. Generate Analysis Summary
- Total number of requests found
- Breakdown by category
- List of complex/compound requests
- Requests with low confidence scores
- Cross-reference map
- Date range summary

### 7. Store Results
- Save parsed requests to database
- Update case document index
- Create searchable index for requests
- Link requests to source RTP document
- Generate unique IDs for each request

### 8. Prepare for Deficiency Analysis
- Format requests for comparison with production
- Create request checklist structure
- Flag high-priority requests
- Note requests requiring special handling

## Elicitation Required
elicit: false

## WebSocket Events
- agent:task_started - RTP parsing started
- agent:task_progress - Request extraction progress
- agent:request_found - Individual request parsed
- agent:parsing_complete - All requests extracted
- agent:task_completed - Analysis saved

## Error Handling
- Invalid document format
- No requests found
- Parser configuration errors
- Case isolation violations
- Storage/database errors

## Integration Points
- PDFExtractor for text extraction
- RTPParser for request identification
- Case management for validation
- Vector store for indexing
- Database for persistent storage

## Output Format
```json
{
  "rtp_document_id": "doc-123",
  "case_name": "Smith_v_Jones_2024",
  "total_requests": 25,
  "requests": [
    {
      "request_number": "1",
      "request_text": "All documents relating to...",
      "category": "documents",
      "page_range": [2, 3],
      "confidence_score": 0.95,
      "date_range": "2020-01-01 to 2023-12-31",
      "document_types": ["contracts", "agreements"]
    }
  ],
  "summary": {
    "by_category": {
      "documents": 15,
      "communications": 8,
      "electronically_stored": 2
    },
    "complex_requests": ["5", "12", "18"],
    "low_confidence": ["23"]
  }
}
```