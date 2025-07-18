# API Design and Integration

## API Integration Strategy
- **API Integration Strategy:** Extend existing discovery API with deficiency-specific endpoints
- **Authentication:** Reuse existing JWT authentication via case context middleware
- **Versioning:** No versioning needed - additive changes only

## New API Endpoints

**POST /api/discovery/process-with-deficiency**
- **Method:** POST
- **Endpoint:** /api/discovery/process-with-deficiency
- **Purpose:** Enhanced discovery processing that includes deficiency analysis
- **Integration:** Extends existing /process-folder endpoint with additional file uploads

**Request:**
```json
{
  "folder_id": "123456789",
  "case_name": "smith_v_jones_2024", 
  "max_documents": 100,
  "rtp_file": "base64_encoded_pdf",
  "oc_response_file": "base64_encoded_pdf",
  "enable_deficiency_analysis": true
}
```

**Response:**
```json
{
  "production_id": "uuid-here",
  "status": "processing",
  "message": "Discovery processing started with deficiency analysis",
  "websocket_channel": "discovery:uuid-here"
}
```

**GET /api/deficiency/report/{report_id}**
- **Method:** GET
- **Endpoint:** /api/deficiency/report/{report_id}
- **Purpose:** Retrieve complete deficiency analysis report
- **Integration:** Uses case context middleware for access control

**Request:** None (report_id in path)

**Response:**
```json
{
  "id": "uuid-here",
  "case_name": "smith_v_jones_2024",
  "production_id": "uuid-here",
  "analysis_status": "completed",
  "total_requests": 25,
  "summary_statistics": {
    "fully_produced": 10,
    "partially_produced": 8,
    "not_produced": 5,
    "no_responsive_docs": 2
  },
  "items": [
    {
      "request_number": "RFP No. 1",
      "request_text": "All medical records...",
      "classification": "fully_produced",
      "confidence_score": 0.92,
      "evidence_chunks": [...]
    }
  ]
}
```

**PUT /api/deficiency/item/{item_id}**
- **Method:** PUT
- **Endpoint:** /api/deficiency/item/{item_id}
- **Purpose:** Update deficiency item classification or add reviewer notes
- **Integration:** Tracks user modifications for audit trail

**Request:**
```json
{
  "classification": "partially_produced",
  "reviewer_notes": "Missing records from January 2023"
}
```

**Response:**
```json
{
  "id": "uuid-here",
  "classification": "partially_produced",
  "reviewer_notes": "Missing records from January 2023",
  "modified_by": "attorney@firm.com",
  "modified_at": "2024-01-18T10:30:00Z"
}
```

**POST /api/deficiency/letter/generate**
- **Method:** POST
- **Endpoint:** /api/deficiency/letter/generate
- **Purpose:** Generate Good Faith letter from deficiency report
- **Integration:** Uses approved templates and legal formatting

**Request:**
```json
{
  "report_id": "uuid-here",
  "template_name": "florida_10_day_standard",
  "custom_deadline": "2024-01-28"
}
```

**Response:**
```json
{
  "id": "uuid-here",
  "report_id": "uuid-here",
  "version": 1,
  "content": "# Good Faith Letter\n\n...",
  "created_at": "2024-01-18T11:00:00Z",
  "export_url": "/api/deficiency/letter/uuid-here/export"
}
```

## WebSocket Events

**deficiency:analysis_started**
```json
{
  "production_id": "uuid-here",
  "total_requests": 25,
  "timestamp": "2024-01-18T10:00:00Z"
}
```

**deficiency:item_analyzed**
```json
{
  "production_id": "uuid-here",
  "request_number": "RFP No. 12",
  "classification": "not_produced",
  "progress": "12/25",
  "timestamp": "2024-01-18T10:05:00Z"
}
```

**deficiency:analysis_completed**
```json
{
  "production_id": "uuid-here",
  "report_id": "uuid-here",
  "duration_seconds": 300,
  "timestamp": "2024-01-18T10:10:00Z"
}
```
