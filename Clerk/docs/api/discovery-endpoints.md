# Discovery Processing API Documentation

This document describes the discovery processing endpoints, including the new deficiency analysis capabilities.

## Endpoints

### 1. Process Discovery Documents

**Endpoint:** `POST /api/discovery/process`

Process discovery documents with document splitting and fact extraction.

**Request:**
```json
{
  "discovery_files": ["base64_encoded_pdf"],
  "box_folder_id": "optional_box_folder_id",
  "production_batch": "PROD_001",
  "producing_party": "Opposing Counsel",
  "production_date": "2024-01-15",
  "responsive_to_requests": ["RFP_001", "RFP_005"],
  "confidentiality_designation": "Confidential",
  "enable_fact_extraction": true
}
```

**Response:**
```json
{
  "processing_id": "uuid",
  "status": "started",
  "message": "Discovery processing started"
}
```

### 2. Process Discovery with Deficiency Analysis (NEW)

**Endpoint:** `POST /api/discovery/process-with-deficiency`

Process discovery documents with optional RTP and OC response documents for deficiency analysis.

**Request:**
```json
{
  "pdf_file": "base64_encoded_discovery_pdf",
  "case_name": "Smith_v_Jones_2024",
  "production_metadata": {
    "production_batch": "PROD_001",
    "producing_party": "Defendant ABC Corp",
    "production_date": "2024-01-15",
    "responsive_to_requests": ["RFP_001", "RFP_005"],
    "confidentiality_designation": "Confidential"
  },
  "rtp_file": "base64_encoded_rtp_pdf (optional)",
  "oc_response_file": "base64_encoded_oc_response_pdf (optional)",
  "enable_fact_extraction": true,
  "enable_deficiency_analysis": false
}
```

**Key Features:**
- Accepts RTP (Request to Produce) and OC (Opposing Counsel) response documents
- Stores RTP/OC documents in temporary storage with automatic cleanup
- Validates all PDF files (type checking, size limits)
- Extends production metadata with deficiency analysis references
- Backward compatible with discovery processing without RTP/OC files

**Response:**
```json
{
  "processing_id": "uuid",
  "status": "started",
  "message": "Discovery processing with deficiency analysis started"
}
```

### 3. Get Processing Status

**Endpoint:** `GET /api/discovery/status/{processing_id}`

Get the status of a discovery processing job.

**Response:**
```json
{
  "processing_id": "uuid",
  "case_id": "case_id",
  "case_name": "Smith_v_Jones_2024",
  "total_documents": 10,
  "processed_documents": 5,
  "total_facts": 150,
  "status": "processing",
  "started_at": "2024-01-15T10:00:00Z",
  "completed_at": null,
  "error_message": null
}
```

## WebSocket Events

The discovery processing endpoints emit real-time updates via WebSocket.

### Standard Events

1. **discovery:started** - Processing has begun
2. **discovery:document_found** - A document segment was identified
3. **discovery:chunking** - Document is being chunked for storage
4. **discovery:embedding** - Embeddings are being generated
5. **discovery:fact_extracted** - A fact was extracted from the document
6. **discovery:document_completed** - Document processing completed
7. **discovery:completed** - All processing completed
8. **discovery:error** - An error occurred

### New Events for Deficiency Analysis

1. **discovery:rtp_upload** - RTP document was uploaded
   ```json
   {
     "event_type": "discovery:rtp_upload",
     "production_id": "uuid",
     "case_name": "Smith_v_Jones_2024",
     "document_info": {
       "document_id": "uuid",
       "filename": "RTP_Document.pdf",
       "size_bytes": 2048576,
       "upload_timestamp": "2024-01-15T10:00:00Z",
       "status": "uploaded"
     }
   }
   ```

2. **discovery:oc_response_upload** - OC response document was uploaded
   ```json
   {
     "event_type": "discovery:oc_response_upload",
     "production_id": "uuid",
     "case_name": "Smith_v_Jones_2024",
     "document_info": {
       "document_id": "uuid",
       "filename": "OC_Response.pdf",
       "size_bytes": 1548576,
       "upload_timestamp": "2024-01-15T10:00:00Z",
       "status": "uploaded"
     }
   }
   ```

## File Validation

All PDF files are validated for:

1. **File Type** - Must be valid PDF (checks magic bytes)
2. **Size Limits** - Default 50MB per file (configurable via `DISCOVERY_MAX_FILE_SIZE_MB`)
3. **Structure** - Basic PDF structure validation
4. **Encryption** - Encrypted PDFs are rejected

Error responses include clear messages:
```json
{
  "detail": "Invalid discovery PDF: The file exceeds size limit (75.3MB > 50MB)"
}
```

## Temporary File Management

RTP and OC response documents are stored temporarily during processing:

1. Files are stored with UUID references in a dedicated temp directory
2. Automatic cleanup occurs after deficiency analysis completes
3. Background task cleans orphaned files older than 24 hours
4. Crash recovery on application startup

## Metadata Structure

Production metadata is extended for deficiency analysis:

```json
{
  "production_batch": "PROD_001",
  "producing_party": "Defendant ABC Corp",
  "production_date": "2024-01-15",
  "responsive_to_requests": ["RFP_001", "RFP_005"],
  "confidentiality_designation": "Confidential",
  "has_deficiency_analysis": true,
  "rtp_document_id": "uuid",
  "rtp_document_path": "/tmp/clerk_discovery_temp/rtp_uuid.pdf",
  "oc_response_document_id": "uuid",
  "oc_response_document_path": "/tmp/clerk_discovery_temp/oc_response_uuid.pdf"
}
```

## Error Handling

The API provides detailed error messages for common issues:

1. **400 Bad Request** - Invalid PDF, missing required fields, validation failures
2. **403 Forbidden** - Case access denied
3. **404 Not Found** - Processing ID not found
4. **500 Internal Server Error** - Processing failures, storage errors

## Usage Examples

### Basic Discovery Processing
```bash
curl -X POST http://localhost:8000/api/discovery/process \
  -H "Content-Type: application/json" \
  -H "X-Case-ID: case_123" \
  -d '{
    "pdf_file": "'$(base64 -w 0 discovery.pdf)'",
    "production_batch": "PROD_001",
    "enable_fact_extraction": true
  }'
```

### Discovery with Deficiency Analysis
```bash
curl -X POST http://localhost:8000/api/discovery/process-with-deficiency \
  -H "Content-Type: application/json" \
  -H "X-Case-ID: case_123" \
  -d '{
    "pdf_file": "'$(base64 -w 0 discovery.pdf)'",
    "rtp_file": "'$(base64 -w 0 rtp.pdf)'",
    "oc_response_file": "'$(base64 -w 0 oc_response.pdf)'",
    "production_metadata": {
      "production_batch": "PROD_001",
      "producing_party": "Defendant Corp"
    },
    "enable_deficiency_analysis": true
  }'
```

### Multipart Form Upload
```bash
curl -X POST http://localhost:8000/api/discovery/process-with-deficiency \
  -H "X-Case-ID: case_123" \
  -F "pdf_file=@discovery.pdf" \
  -F "rtp_file=@rtp.pdf" \
  -F "oc_response_file=@oc_response.pdf" \
  -F "production_batch=PROD_001" \
  -F "enable_deficiency_analysis=true"
```

## Integration with Deficiency Analysis

When both RTP and OC response documents are provided and `enable_deficiency_analysis` is true:

1. Documents are stored temporarily with UUID references
2. References are added to production metadata
3. Discovery documents are processed with hybrid storage for better search
4. Metadata includes all necessary references for subsequent deficiency analysis
5. Temporary files are automatically cleaned up after processing

The deficiency analysis service (implemented separately) can then:
- Retrieve the RTP and OC documents using the UUID references
- Compare discovery production against RTP requests
- Generate deficiency reports and good faith letters