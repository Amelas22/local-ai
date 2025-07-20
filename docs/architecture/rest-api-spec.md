# REST API Specification

## Overview

The Clerk Legal AI System exposes a RESTful API built with FastAPI. All endpoints follow REST conventions, use JSON for request/response bodies, and require authentication except for health checks.

## Base Information

### Base URL
```
https://api.clerk-legal.com
```

### API Version
```
v1 (included in base URL: /api/v1)
```

### Authentication
All endpoints except `/health` require JWT Bearer token authentication:
```
Authorization: Bearer <jwt_token>
```

### Common Headers
```
Content-Type: application/json
X-Case-ID: <uuid> (required for case-scoped operations)
X-Request-ID: <uuid> (optional, for request tracking)
```

## Response Format

### Success Response
```json
{
  "success": true,
  "data": {
    // Response data
  },
  "meta": {
    "timestamp": "2024-01-20T10:30:00Z",
    "request_id": "550e8400-e29b-41d4-a716-446655440000"
  }
}
```

### Error Response
```json
{
  "success": false,
  "error": {
    "code": "CASE_NOT_FOUND",
    "message": "Case with ID '123' not found",
    "details": {
      // Additional error context
    }
  },
  "meta": {
    "timestamp": "2024-01-20T10:30:00Z",
    "request_id": "550e8400-e29b-41d4-a716-446655440000"
  }
}
```

## API Endpoints

### Health & Status

#### GET /health
Check system health status.

**Response:**
```json
{
  "status": "healthy",
  "version": "1.0.0",
  "services": {
    "database": "connected",
    "vector_store": "connected",
    "websocket": "connected"
  }
}
```

### Case Management

#### GET /api/v1/cases
List cases accessible to the authenticated user.

**Query Parameters:**
- `status` (optional): Filter by status (active, archived, deleted)
- `limit` (optional): Number of results (default: 20, max: 100)
- `offset` (optional): Pagination offset

**Response:**
```json
{
  "success": true,
  "data": {
    "cases": [
      {
        "id": "550e8400-e29b-41d4-a716-446655440000",
        "name": "Smith_v_Jones_2024",
        "law_firm_id": "660e8400-e29b-41d4-a716-446655440000",
        "status": "active",
        "created_at": "2024-01-15T10:00:00Z",
        "updated_at": "2024-01-20T14:30:00Z",
        "permissions": ["read", "write"],
        "metadata": {
          "case_number": "2024-CV-001234",
          "jurisdiction": "Federal"
        }
      }
    ],
    "total": 15,
    "limit": 20,
    "offset": 0
  }
}
```

#### POST /api/v1/cases
Create a new case.

**Request Body:**
```json
{
  "name": "Smith_v_Jones_2024",
  "law_firm_id": "660e8400-e29b-41d4-a716-446655440000",
  "metadata": {
    "case_number": "2024-CV-001234",
    "jurisdiction": "Federal",
    "opposing_counsel": "Johnson & Associates"
  }
}
```

**Response:**
```json
{
  "success": true,
  "data": {
    "id": "550e8400-e29b-41d4-a716-446655440000",
    "name": "Smith_v_Jones_2024",
    "law_firm_id": "660e8400-e29b-41d4-a716-446655440000",
    "status": "active",
    "created_at": "2024-01-20T10:30:00Z",
    "created_by": "770e8400-e29b-41d4-a716-446655440000"
  }
}
```

#### PUT /api/v1/cases/{case_id}
Update case information.

**Request Body:**
```json
{
  "status": "archived",
  "metadata": {
    "closed_date": "2024-01-20",
    "outcome": "settled"
  }
}
```

#### POST /api/v1/cases/{case_id}/permissions
Grant permissions to a user for a case.

**Request Body:**
```json
{
  "user_id": "880e8400-e29b-41d4-a716-446655440000",
  "permission": "write"
}
```

### Document Processing

#### POST /api/v1/documents/process-folder
Process documents from a Box folder.

**Headers Required:**
- `X-Case-ID`: Target case for documents

**Request Body:**
```json
{
  "folder_id": "123456789",
  "max_documents": 50,
  "document_type": "discovery",
  "metadata": {
    "production_batch": "PROD_001",
    "producing_party": "Opposing Counsel"
  }
}
```

**Response:**
```json
{
  "success": true,
  "data": {
    "processing_id": "990e8400-e29b-41d4-a716-446655440000",
    "status": "processing",
    "documents_queued": 45,
    "estimated_time": 300
  }
}
```

#### GET /api/v1/documents/{document_id}
Retrieve document information.

**Response:**
```json
{
  "success": true,
  "data": {
    "id": "aa0e8400-e29b-41d4-a716-446655440000",
    "case_id": "550e8400-e29b-41d4-a716-446655440000",
    "file_name": "Contract_Amendment_2023.pdf",
    "document_type": "contract",
    "page_count": 15,
    "processing_status": "completed",
    "created_at": "2024-01-18T09:00:00Z",
    "chunks": [
      {
        "id": "bb0e8400-e29b-41d4-a716-446655440000",
        "chunk_index": 0,
        "page_number": 1,
        "content": "CONTRACT AMENDMENT...",
        "embedding_id": "vec_123456"
      }
    ]
  }
}
```

### Discovery Processing

#### POST /api/v1/discovery/process
Process discovery production with deficiency analysis.

**Headers Required:**
- `X-Case-ID`: Target case

**Request Body (Multipart Form Data):**
- `discovery_files`: Array of PDF files
- `rtp_document`: RTP PDF file
- `oc_response_document`: OC Response PDF file
- `metadata`: JSON string with production metadata

**Metadata Structure:**
```json
{
  "production_batch": "PROD_001",
  "producing_party": "Johnson & Associates",
  "production_date": "2024-01-15",
  "responsive_to_requests": ["RFP_001", "RFP_002", "RFP_005"],
  "confidentiality_designation": "Confidential",
  "enable_deficiency_analysis": true
}
```

**Response:**
```json
{
  "success": true,
  "data": {
    "production_id": "cc0e8400-e29b-41d4-a716-446655440000",
    "processing_status": "processing",
    "websocket_channel": "discovery:cc0e8400-e29b-41d4-a716-446655440000"
  }
}
```

#### GET /api/v1/discovery/productions/{production_id}
Get discovery production status and results.

**Response:**
```json
{
  "success": true,
  "data": {
    "id": "cc0e8400-e29b-41d4-a716-446655440000",
    "case_id": "550e8400-e29b-41d4-a716-446655440000",
    "production_batch": "PROD_001",
    "processing_status": "completed",
    "document_count": 150,
    "total_pages": 3500,
    "facts_extracted": 89,
    "deficiency_report_id": "dd0e8400-e29b-41d4-a716-446655440000",
    "created_at": "2024-01-20T08:00:00Z",
    "completed_at": "2024-01-20T08:45:00Z"
  }
}
```

### Deficiency Analysis

#### GET /api/v1/deficiency/reports/{report_id}
Retrieve deficiency analysis report.

**Response:**
```json
{
  "success": true,
  "data": {
    "id": "dd0e8400-e29b-41d4-a716-446655440000",
    "case_id": "550e8400-e29b-41d4-a716-446655440000",
    "production_id": "cc0e8400-e29b-41d4-a716-446655440000",
    "analysis_status": "completed",
    "summary": {
      "total_requests": 25,
      "fully_produced": 10,
      "partially_produced": 5,
      "not_produced": 8,
      "no_responsive_docs": 2
    },
    "items": [
      {
        "request_number": "RFP No. 1",
        "request_text": "All contracts related to...",
        "oc_response": "See attached documents",
        "classification": "fully_produced",
        "confidence_score": 0.92,
        "evidence": [
          {
            "document_name": "Master_Contract_2023.pdf",
            "page_numbers": [1, 5, 12],
            "relevance_score": 0.95
          }
        ]
      }
    ]
  }
}
```

#### PUT /api/v1/deficiency/items/{item_id}
Update deficiency item with reviewer notes.

**Request Body:**
```json
{
  "classification": "partially_produced",
  "reviewer_notes": "Missing amendments from Q4 2023"
}
```

### Search Operations

#### POST /api/v1/search
Perform hybrid search across case documents.

**Headers Required:**
- `X-Case-ID`: Case to search within

**Request Body:**
```json
{
  "query": "contract termination clause",
  "search_type": "hybrid",
  "filters": {
    "document_type": ["contract", "amendment"],
    "date_range": {
      "start": "2023-01-01",
      "end": "2023-12-31"
    }
  },
  "limit": 20,
  "include_shared_resources": true
}
```

**Response:**
```json
{
  "success": true,
  "data": {
    "results": [
      {
        "document_id": "aa0e8400-e29b-41d4-a716-446655440000",
        "document_name": "Contract_Amendment_2023.pdf",
        "chunk_index": 5,
        "page_number": 12,
        "score": 0.89,
        "content": "...termination of this agreement...",
        "highlights": [
          {"start": 10, "end": 32, "text": "termination clause"}
        ]
      }
    ],
    "total_results": 15,
    "search_time_ms": 145
  }
}
```

### Motion Generation

#### POST /api/v1/motions/generate-outline
Generate a motion outline based on case facts.

**Headers Required:**
- `X-Case-ID`: Source case

**Request Body:**
```json
{
  "motion_type": "summary_judgment",
  "party": "plaintiff",
  "claims": ["breach_of_contract", "unjust_enrichment"],
  "key_facts": [
    "Contract signed on January 15, 2023",
    "Defendant failed to deliver goods by agreed date"
  ]
}
```

**Response:**
```json
{
  "success": true,
  "data": {
    "outline_id": "ee0e8400-e29b-41d4-a716-446655440000",
    "motion_type": "summary_judgment",
    "title": "Plaintiff's Motion for Summary Judgment",
    "sections": [
      {
        "name": "Introduction",
        "content": "Plaintiff respectfully moves this Court..."
      },
      {
        "name": "Statement of Facts",
        "subsections": [
          {
            "name": "Contract Formation",
            "facts": ["Contract executed on January 15, 2023"]
          }
        ]
      }
    ]
  }
}
```

#### POST /api/v1/motions/generate-draft
Generate full motion draft from outline.

**Request Body:**
```json
{
  "outline_id": "ee0e8400-e29b-41d4-a716-446655440000",
  "style": "formal",
  "include_citations": true,
  "jurisdiction": "federal"
}
```

**Response:**
```json
{
  "success": true,
  "data": {
    "motion_id": "ff0e8400-e29b-41d4-a716-446655440000",
    "title": "Plaintiff's Motion for Summary Judgment",
    "content": "IN THE UNITED STATES DISTRICT COURT...",
    "word_count": 3500,
    "citations": [
      {
        "case": "Anderson v. Liberty Lobby, Inc.",
        "citation": "477 U.S. 242 (1986)",
        "pin_cite": "477 U.S. at 248"
      }
    ]
  }
}
```

### Good Faith Letters

#### POST /api/v1/letters/generate-good-faith
Generate Good Faith letter from deficiency report.

**Request Body:**
```json
{
  "deficiency_report_id": "dd0e8400-e29b-41d4-a716-446655440000",
  "template": "formal_federal",
  "deadline_days": 10,
  "include_meet_confer": true
}
```

**Response:**
```json
{
  "success": true,
  "data": {
    "letter_id": "gg0e8400-e29b-41d4-a716-446655440000",
    "content": "Dear Counsel:\n\nWe write regarding deficiencies...",
    "deadline_date": "2024-01-30",
    "deficiency_count": 13
  }
}
```

#### PUT /api/v1/letters/{letter_id}
Update Good Faith letter content.

**Request Body:**
```json
{
  "content": "Updated letter content...",
  "status": "final"
}
```

### WebSocket Endpoints

#### /ws/socket.io
Socket.io endpoint for real-time updates.

**Connection:**
```javascript
const socket = io('wss://api.clerk-legal.com', {
  auth: {
    token: 'jwt_token'
  }
});
```

**Events:**
```javascript
// Subscribe to case events
socket.emit('subscribe', { case_id: 'case_uuid' });

// Listen for updates
socket.on('discovery:progress', (data) => {
  console.log('Progress:', data.percentage);
});

socket.on('deficiency:completed', (data) => {
  console.log('Analysis done:', data.report_id);
});
```

#### GET /api/v1/websocket/status
Check WebSocket server status.

**Response:**
```json
{
  "success": true,
  "data": {
    "status": "connected",
    "active_connections": 45,
    "rooms": {
      "case:550e8400-e29b-41d4-a716-446655440000": 3
    }
  }
}
```

## Error Codes

### HTTP Status Codes
- `200`: Success
- `201`: Created
- `400`: Bad Request
- `401`: Unauthorized
- `403`: Forbidden
- `404`: Not Found
- `422`: Validation Error
- `429`: Rate Limited
- `500`: Internal Server Error

### Application Error Codes
- `CASE_NOT_FOUND`: Case does not exist
- `PERMISSION_DENIED`: Insufficient permissions
- `INVALID_CASE_NAME`: Case name format invalid
- `PROCESSING_FAILED`: Document processing error
- `VECTOR_STORE_ERROR`: Vector database error
- `AI_SERVICE_ERROR`: AI service unavailable
- `RATE_LIMIT_EXCEEDED`: Too many requests

## Rate Limiting

### Limits by Endpoint Category
- **Search**: 100 requests/minute
- **Document Processing**: 10 requests/minute
- **Motion Generation**: 5 requests/minute
- **General API**: 300 requests/minute

### Rate Limit Headers
```
X-RateLimit-Limit: 100
X-RateLimit-Remaining: 95
X-RateLimit-Reset: 1705756200
```

## Pagination

### Standard Parameters
- `limit`: Number of results (max: 100)
- `offset`: Starting position
- `sort`: Sort field
- `order`: Sort order (asc/desc)

### Response Format
```json
{
  "data": [...],
  "pagination": {
    "total": 250,
    "limit": 20,
    "offset": 40,
    "pages": 13,
    "current_page": 3
  }
}
```

## Webhooks (Future)

### Event Types
- `case.created`
- `document.processed`
- `discovery.completed`
- `deficiency.analyzed`
- `motion.generated`

### Webhook Payload
```json
{
  "event": "discovery.completed",
  "timestamp": "2024-01-20T10:30:00Z",
  "data": {
    "production_id": "cc0e8400-e29b-41d4-a716-446655440000",
    "case_id": "550e8400-e29b-41d4-a716-446655440000",
    "document_count": 150
  }
}
```

## API Versioning

### Version Strategy
- Versions in URL path: `/api/v1/`, `/api/v2/`
- Breaking changes require new version
- Deprecation notices 6 months in advance
- Sunset period of 12 months

### Version Headers
```
API-Version: 1.0
API-Deprecation-Date: 2025-01-01
API-Sunset-Date: 2025-07-01
```

## SDK Support

### Available SDKs
- Python: `pip install clerk-legal-sdk`
- JavaScript: `npm install @clerk-legal/sdk`
- Ruby: `gem install clerk-legal`

### SDK Example (Python)
```python
from clerk_legal import ClerkClient

client = ClerkClient(api_key="your_api_key")

# Search documents
results = client.search(
    case_id="550e8400-e29b-41d4-a716-446655440000",
    query="termination clause",
    limit=10
)

# Generate motion
outline = client.motions.generate_outline(
    case_id="550e8400-e29b-41d4-a716-446655440000",
    motion_type="summary_judgment"
)
```