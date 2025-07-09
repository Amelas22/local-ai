# Discovery Document Processing with Real-time Review Interface - PRP

name: "Discovery Processing Feature v1.0"
description: |

## Purpose
Implement a comprehensive discovery document processing system that automatically splits concatenated discovery response PDFs, extracts case facts using AI, and provides a real-time paralegal review interface with inline editing capabilities.

## Core Principles
1. **Context is King**: All backend services and patterns are documented
2. **Validation Loops**: Executable tests for each component
3. **Information Dense**: References to existing codebase patterns
4. **Progressive Success**: Start with upload, then processing, then UI
5. **Global rules**: Follow all rules in CLAUDE.md

---

## Goal
Build a feature that transforms the manual discovery review process into an AI-assisted workflow where:
- Paralegals work within their selected case context (case databases already created via "Create Case" feature)
- They can upload concatenated discovery PDFs (or select from Box) for the current case
- The system automatically splits documents and extracts case facts to the case-specific database
- Users review facts in real-time with source highlighting
- All facts are immediately stored in the case's Qdrant collections with full edit/delete capabilities

## Why
- **Business value**: Reduces discovery review time from days to hours
- **User impact**: Paralegals can focus on fact verification rather than extraction
- **Integration**: Leverages existing document processing and fact extraction systems
- **Problems solved**: Manual fact extraction is error-prone and time-consuming

## What
A two-panel interface where users upload discovery documents and RFP files, then review extracted facts in real-time with PDF highlighting and inline editing.

### Case Context Architecture
**CRITICAL**: The system relies on the user having already selected a case in the frontend:
1. Cases are created via the frontend's "Create Case" feature, which initializes Qdrant collections
2. Users must select a case before accessing discovery processing
3. The frontend maintains the selected case in application state/context
4. All API calls include case context via headers (X-Case-ID)
5. Backend middleware extracts and validates case context from requests
6. WebSocket sessions maintain case subscription for real-time updates

### Success Criteria
- [ ] System correctly identifies user's selected case from frontend context
- [ ] Multi-source upload (files, folders, Box integration) functional
- [ ] Documents split accurately at boundaries (>90% accuracy)
- [ ] Facts extracted and stored in correct case-specific Qdrant collections
- [ ] Real-time WebSocket updates during processing include case context
- [ ] PDF viewer highlights fact sources accurately
- [ ] Edit/delete operations persist immediately to correct case collections
- [ ] No duplicate facts stored (deduplication working within case)
- [ ] Processing handles 500+ page PDFs without crashes

## All Needed Context

### Documentation & References

```yaml
# MUST READ - Include these in your context window

# Frontend Libraries
- url: https://react.dev/reference/react
  why: Core React hooks and component patterns
  
- url: https://react-pdf-viewer.dev/
  why: PDF viewer implementation with highlight plugin
  
- url: https://react-pdf-viewer.dev/plugins/highlight/
  why: Text selection and highlighting for fact sources
  
- url: https://react-dropzone.js.org/
  why: Drag-and-drop file upload with validation

- url: https://socket.io/docs/v4/client-api/
  why: WebSocket client for real-time updates

# Backend Documentation  
- url: https://python-socketio.readthedocs.io/en/stable/api.html
  why: Python SocketIO server patterns and events
  
- url: https://developer.box.com/reference/
  why: Box API for folder selection and file access
  
- url: https://spacy.io/api/doc
  why: NLP entity extraction used in fact_extractor.py

# Internal Documentation
- file: CLAUDE.md
  why: Project structure, testing requirements, coding standards
  
- file: Clerk/src/ai_agents/fact_extractor.py
  why: Existing fact extraction patterns and deduplication
  
- file: Clerk/src/document_processing/discovery_splitter_normalized.py
  why: Document boundary detection implementation
  
- file: Clerk/src/websocket/socket_server.py
  why: WebSocket event patterns already implemented
  
- file: Clerk/src/middleware/case_context.py
  why: Case isolation middleware patterns
  
- file: Clerk/main.py
  why: Existing discovery endpoint at line 712
```

### Current Codebase Structure
```bash
Clerk/
├── main.py                          # FastAPI app with /discovery/process endpoint
├── src/
│   ├── ai_agents/
│   │   ├── fact_extractor.py        # Fact extraction with deduplication
│   │   └── tests/
│   ├── document_processing/
│   │   ├── discovery_splitter.py    # Document boundary detection
│   │   ├── discovery_splitter_normalized.py
│   │   └── tests/
│   ├── websocket/
│   │   ├── socket_server.py         # WebSocket events
│   │   └── tests/
│   ├── models/
│   │   ├── unified_document_models.py
│   │   └── case_models.py
│   ├── middleware/
│   │   └── case_context.py          # Case validation
│   └── api/
│       └── discovery_normalized_endpoints.py
└── frontend/
    ├── src/
    │   ├── components/
    │   └── pages/
    └── package.json
```

### Desired Codebase Structure with New Files
```bash
Clerk/
├── frontend/
│   ├── src/
│   │   ├── components/
│   │   │   ├── discovery/
│   │   │   │   ├── DiscoveryUpload.tsx      # Dual upload zones
│   │   │   │   ├── FactCard.tsx             # Individual fact display
│   │   │   │   ├── FactReviewPanel.tsx      # Main review interface
│   │   │   │   ├── DocumentTabs.tsx         # Tab management
│   │   │   │   └── PDFViewer.tsx            # PDF with highlighting
│   │   │   └── shared/
│   │   │       └── BoxFolderPicker.tsx      # Box integration
│   │   ├── pages/
│   │   │   └── DiscoveryProcessing.tsx      # Main page component
│   │   ├── hooks/
│   │   │   └── useDiscoverySocket.ts        # WebSocket management
│   │   └── services/
│   │       └── discoveryService.ts          # API calls
├── src/
│   ├── api/
│   │   └── discovery_endpoints.py           # Enhanced endpoints
│   └── services/
│       └── fact_manager.py                  # Fact CRUD operations
```

### Known Gotchas & Library Quirks
```python
# CRITICAL: react-pdf-viewer requires worker setup
# Example: Must configure PDF.js worker in public folder

# CRITICAL: Qdrant stores facts in case-specific collections
# Pattern: f"{case_name}_facts" - NEVER query without case_name. case_name is available from postgres database based on selected case.

# CRITICAL: Box API rate limits: 4 req/sec per user
# Solution: Implement request queuing in frontend

# CRITICAL: WebSocket events must include case_id for security
# Pattern: socket.emit('discovery:started', {'case_id': case_id})

# GOTCHA: react-dropzone folder upload only works in Chrome/Edge
# Fallback: Always provide Box folder option

# GOTCHA: Large PDFs (>100MB) can crash browser
# Solution: Stream processing with progress events
```

## Implementation Blueprint

### Data Models and Structure

```python
# Extend existing models in src/models/unified_document_models.py

from pydantic import BaseModel, Field
from typing import List, Optional, Dict
from datetime import datetime

class FactSource(BaseModel):
    """Source location for an extracted fact"""
    doc_id: str
    doc_title: str
    page: int
    bbox: List[float]  # [x1, y1, x2, y2] coordinates
    text_snippet: str  # Surrounding context

class ExtractedFactWithSource(ExtractedFact):
    """Enhanced fact model with source tracking"""
    source: FactSource
    is_edited: bool = False
    edit_history: List[Dict] = Field(default_factory=list)
    
class DiscoveryProcessingRequest(BaseModel):
    """Request model for discovery processing"""
    case_id: str
    case_name: str
    discovery_files: List[str] = Field(default_factory=list)
    box_folder_id: Optional[str] = None
    rfp_file: Optional[str] = None
    
class DiscoveryProcessingStatus(BaseModel):
    """Real-time status updates"""
    processing_id: str
    case_id: str
    total_documents: int
    processed_documents: int
    total_facts: int
    current_document: Optional[str] = None
    status: str  # "processing", "completed", "error"
```

### List of Tasks to Complete (In Order)

```yaml
Task 1: Create Frontend Upload Component
MODIFY frontend/src/pages/DiscoveryProcessing.tsx:
  - CREATE new page component
  - IMPORT react-dropzone for file handling
  - IMPLEMENT dual upload zones (discovery docs + RFP)
  - ADD Box folder selection button
  
CREATE frontend/src/components/discovery/DiscoveryUpload.tsx:
  - MIRROR pattern from: existing upload components
  - IMPLEMENT file validation (PDF only)
  - HANDLE multiple file selection
  - INTEGRATE Box picker SDK

Task 2: Implement WebSocket Connection Management
CREATE frontend/src/hooks/useDiscoverySocket.ts:
  - PATTERN: Follow existing WebSocket patterns
  - IMPLEMENT auto-reconnection with backoff
  - HANDLE all discovery:* events
  - MAINTAIN connection state

Task 3: Build Fact Review Interface
CREATE frontend/src/components/discovery/FactReviewPanel.tsx:
  - IMPLEMENT tab-based document navigation
  - CREATE fact card grid layout
  - HANDLE real-time fact additions
  - TRACK review completion state

CREATE frontend/src/components/discovery/FactCard.tsx:
  - DISPLAY fact content with metadata
  - IMPLEMENT inline edit mode
  - ADD delete confirmation
  - SHOW confidence scores

Task 4: Integrate PDF Viewer with Highlighting
CREATE frontend/src/components/discovery/PDFViewer.tsx:
  - SETUP @react-pdf-viewer with worker
  - IMPLEMENT highlight plugin
  - ADD navigation to specific page/bbox
  - HANDLE large PDF optimization

Task 5: Enhance Backend Processing Endpoints
MODIFY src/api/discovery_endpoints.py:
  - ENHANCE /discovery/process endpoint
  - ADD fact update/delete endpoints
  - IMPLEMENT progress tracking
  - ENSURE case isolation

CREATE src/services/fact_manager.py:
  - IMPLEMENT fact CRUD operations
  - ADD deduplication checks
  - HANDLE edit history
  - INTEGRATE with Qdrant

Task 6: Add Real-time Processing Events
MODIFY src/websocket/socket_server.py:
  - ADD discovery:fact_extracted event
  - IMPLEMENT fact:update handler
  - ADD fact:delete handler
  - ENSURE case-based filtering

Task 7: Implement Box Integration
MODIFY frontend/src/services/discoveryService.ts:
  - ADD Box folder listing endpoint
  - IMPLEMENT file streaming from Box
  - HANDLE authentication flow
  - ADD progress tracking

Task 8: Create Comprehensive Tests
CREATE frontend/src/components/discovery/__tests__/:
  - TEST file upload validation
  - TEST WebSocket reconnection
  - TEST fact editing flow
  - TEST PDF highlighting

CREATE src/services/tests/test_fact_manager.py:
  - TEST CRUD operations
  - TEST deduplication logic
  - TEST case isolation
  - TEST concurrent updates
```

### Case Context Flow Example

```javascript
// EXAMPLE: Complete flow showing case context handling

// 1. User selects a case in the frontend
const CaseSelector = () => {
    const { setCurrentCase } = useCaseContext();
    
    const handleCaseSelect = async (caseId) => {
        // Fetch case details
        const caseData = await api.getCase(caseId);
        
        // Set in context (persisted across app)
        setCurrentCase({
            id: caseData.id,
            name: caseData.name,
            lawFirm: caseData.law_firm_id
        });
        
        // Navigate to discovery processing
        navigate('/discovery');
    };
};

// 2. Discovery page requires case context
const DiscoveryProcessing = () => {
    const { currentCase } = useCaseContext();
    
    // CRITICAL: Redirect if no case selected
    if (!currentCase) {
        return <Navigate to="/cases" />;
    }
    
    // All API calls automatically include case context
    const apiClient = useApiClient(); // Includes X-Case-ID header
};

// 3. Backend middleware extracts case context
// src/middleware/case_context.py
@app.middleware("http")
async def case_context_middleware(request: Request, call_next):
    case_id = request.headers.get("X-Case-ID")
    if case_id and request.url.path.startswith("/api/"):
        # Validate case access
        case = await case_manager.get_case(case_id)
        request.state.case_context = CaseContext(
            case_id=case.id,
            case_name=case.name,
            user_id=request.state.user_id
        )
    return await call_next(request)

// 4. WebSocket maintains case subscription
socket.on('connect', () => {
    // Subscribe to case-specific room
    socket.emit('subscribe_case', { case_id: currentCase.id });
});
```

### Per Task Pseudocode

```python
# Task 1: Upload Component
# DiscoveryUpload.tsx pseudocode
const DiscoveryUpload = () => {
    const {getRootProps, getInputProps} = useDropzone({
        accept: {'application/pdf': ['.pdf']},
        multiple: true,
        onDrop: async (files) => {
            // PATTERN: Show immediate feedback
            setUploading(true);
            
            // CRITICAL: Validate file sizes
            const validFiles = files.filter(f => f.size < 100_000_000);
            
            // PATTERN: Use FormData for multipart upload
            const formData = new FormData();
            validFiles.forEach(f => formData.append('files', f));
            
            await discoveryService.uploadFiles(formData);
        }
    });
    
    // GOTCHA: Box picker requires initialization
    const handleBoxSelect = () => {
        if (!window.Box) {
            loadBoxSDK().then(() => showBoxPicker());
        }
    };
};

# Task 5: Backend Processing Enhancement
# src/services/fact_manager.py
class FactManager:
    def __init__(self):
        self.vector_store = QdrantVectorStore()
        
    async def update_fact(
        self, 
        case_name: str, 
        fact_id: str, 
        new_content: str,
        user_id: str
    ) -> ExtractedFactWithSource:
        # PATTERN: Always validate case access first
        if not await self.validate_case_access(case_name, user_id):
            raise PermissionError("No access to case")
            
        # CRITICAL: Get existing fact for history
        existing = await self.vector_store.get_by_id(
            collection_name=f"{case_name}_facts",
            point_id=fact_id
        )
        
        # PATTERN: Maintain edit history
        edit_entry = {
            "timestamp": datetime.utcnow().isoformat(),
            "user_id": user_id,
            "old_content": existing.payload["content"],
            "new_content": new_content
        }
        
        # GOTCHA: Re-embed with new content
        new_embedding = await self.generate_embedding(new_content)
        
        # CRITICAL: Update atomically
        await self.vector_store.update_point(
            collection_name=f"{case_name}_facts",
            point_id=fact_id,
            payload={
                **existing.payload,
                "content": new_content,
                "is_edited": True,
                "edit_history": existing.payload.get("edit_history", []) + [edit_entry]
            },
            vector=new_embedding
        )

# Task 6: WebSocket Event Handlers
# Enhance src/websocket/socket_server.py
@sio.on('fact:update')
async def handle_fact_update(sid, data):
    # PATTERN: Extract case context from session
    case_id = await get_session_case(sid)
    if not case_id or case_id != data.get('case_id'):
        return {'error': 'Invalid case context'}
    
    # CRITICAL: Validate before processing
    try:
        fact_manager = FactManager()
        updated_fact = await fact_manager.update_fact(
            case_name=data['case_name'],
            fact_id=data['fact_id'],
            new_content=data['content'],
            user_id=get_user_id(sid)
        )
        
        # PATTERN: Broadcast to case subscribers
        await sio.emit(
            'fact:updated',
            {
                'fact_id': data['fact_id'],
                'content': data['content'],
                'updated_by': get_user_id(sid)
            },
            room=f"case_{case_id}"
        )
    except Exception as e:
        logger.error(f"Fact update failed: {e}")
        return {'error': str(e)}
```

### Integration Points
```yaml
DATABASE:
  - No SQL changes needed (using Qdrant for facts)
  - Ensure case_facts collection exists per case -- this is built via the "Create Case" feature in the clerk app.
  
CONFIG:
  - add to: .env
    BOX_APP_CLIENT_ID=your_client_id
    PDF_WORKER_URL=/pdf.worker.min.js
    MAX_UPLOAD_SIZE=104857600  # 100MB
  
ROUTES:
  - modify: src/api/discovery_endpoints.py
  - add: PUT /api/facts/{fact_id}
  - add: DELETE /api/facts/{fact_id}
  
FRONTEND_ROUTES:
  - add to: frontend/src/App.tsx
  - pattern: <Route path="/discovery" element={<DiscoveryProcessing />} />
```

## Validation Loop

### Level 1: Syntax & Style
```bash
# Backend Python
cd Clerk
ruff check src/ --fix
ruff format src/
mypy src/services/fact_manager.py

# Frontend TypeScript  
cd frontend
npm run lint:fix
npm run type-check

# Expected: No errors. Fix any issues before proceeding.
```

### Level 2: Unit Tests
```python
# CREATE src/services/tests/test_fact_manager.py
import pytest
from src.services.fact_manager import FactManager

@pytest.mark.asyncio
async def test_update_fact_success():
    """Test successful fact update with history"""
    manager = FactManager()
    result = await manager.update_fact(
        case_name="test_case",
        fact_id="fact_123", 
        new_content="Updated fact content",
        user_id="user_456"
    )
    assert result.is_edited is True
    assert len(result.edit_history) > 0

@pytest.mark.asyncio
async def test_update_fact_permission_denied():
    """Test fact update without case access"""
    manager = FactManager()
    with pytest.raises(PermissionError):
        await manager.update_fact(
            case_name="unauthorized_case",
            fact_id="fact_123",
            new_content="Should fail",
            user_id="bad_user"
        )

@pytest.mark.asyncio  
async def test_deduplication_prevents_duplicate():
    """Test that similar facts are not duplicated"""
    manager = FactManager()
    fact1 = await manager.create_fact(
        case_name="test_case",
        content="The accident occurred on January 15, 2024"
    )
    
    # Attempt to create nearly identical fact
    fact2 = await manager.create_fact(
        case_name="test_case", 
        content="The accident occurred on January 15, 2024."
    )
    
    assert fact2 is None  # Should be rejected as duplicate
```

```bash
# Run backend tests
cd Clerk
python -m pytest src/services/tests/test_fact_manager.py -v

# Run frontend tests
cd frontend
npm test -- --coverage
```

### Level 3: Integration Test
```bash
# Start services
cd Clerk
python start_services_with_postgres.py --profile cpu

# Test discovery processing endpoint
curl -X POST http://localhost:8000/discovery/process \
  -H "Content-Type: application/json" \
  -H "X-Case-ID: test-case-123" \
  -d '{
    "case_id": "test-case-123",
    "case_name": "Test_v_Case_2024",
    "discovery_files": ["test.pdf"]
  }'

# Expected: {"processing_id": "...", "status": "started"}

# Test fact update via WebSocket
npm install -g wscat
wscat -c ws://localhost:8000/ws/socket.io/
> {"event": "fact:update", "data": {"case_id": "test-case-123", "fact_id": "fact_1", "content": "Updated"}}

# Expected: Acknowledgment and broadcast to subscribers
```

## Final Validation Checklist
- [ ] All tests pass: `python -m pytest && npm test`
- [ ] No linting errors: `ruff check && npm run lint`
- [ ] No type errors: `mypy src/ && npm run type-check`
- [ ] File upload works with drag-and-drop
- [ ] Box folder selection opens picker
- [ ] Facts appear in real-time during processing
- [ ] PDF viewer highlights fact sources correctly
- [ ] Edit/delete operations persist immediately
- [ ] No duplicate facts created
- [ ] WebSocket reconnects after disconnection
- [ ] Large PDFs (100+ pages) process without crashing
- [ ] Case isolation verified (no cross-case data leaks)

---

## Anti-Patterns to Avoid
- ❌ Don't query Qdrant without case_name filter
- ❌ Don't load entire PDFs into memory at once
- ❌ Don't emit WebSocket events without case context
- ❌ Don't skip deduplication checks
- ❌ Don't allow synchronous operations in async handlers
- ❌ Don't hardcode Box credentials
- ❌ Don't ignore WebSocket connection failures

## Confidence Score: 8/10

### Reasoning:
- **Strengths**: 
  - Comprehensive context with all needed documentation
  - Clear implementation path following existing patterns
  - Detailed validation gates at each level
  - Addresses all major technical challenges
  
- **Potential Challenges**:
  - PDF highlighting accuracy depends on bbox coordinates
  - Box API integration may require additional auth setup
  - Real-time performance with many concurrent users
  
- **Mitigation**: 
  - Start with basic features and iterate
  - Test with real discovery documents early
  - Monitor WebSocket performance under load