# Discovery Processing Feature - Product Requirements and Planning (PRP)

## FEATURE: Discovery Document Processing with Real-time Review Interface

### Overview
This feature implements a comprehensive discovery document processing system that automatically splits concatenated discovery response PDFs, extracts case facts, and provides a real-time review interface for paralegals to verify and edit extracted information. The system integrates with Box cloud storage and provides real-time updates via WebSocket during processing.

### Key Capabilities
1. **Multi-source Document Upload**: Support for individual files, multiple files, folders, and Box cloud integration
2. **Automatic Document Splitting**: AI-powered detection of document boundaries in concatenated PDFs
3. **Intelligent Fact Extraction**: NLP-based extraction of case facts with categorization and confidence scoring
4. **Real-time Processing Updates**: WebSocket-based live updates as documents are processed
5. **Interactive Review Interface**: PDF viewer with highlighting and inline fact editing capabilities
6. **Automatic Deduplication**: Prevents duplicate facts from being stored in the database

### Technical Architecture

#### Frontend Components
- **Upload Interface**: Dual upload zones for discovery documents and RFP documents
- **Processing Dashboard**: Tab-based interface showing document processing progress
- **Fact Review Cards**: Interactive cards displaying extracted facts with source links
- **PDF Viewer**: Embedded viewer with text highlighting and navigation capabilities
- **Progress Tracking**: Real-time status updates and completion tracking

#### Backend Processing Pipeline
1. **Document Reception**: Handle uploads from multiple sources (direct upload, Box integration)
2. **Boundary Detection**: Use LLM to identify document boundaries in concatenated PDFs
3. **Document Classification**: Classify each split document by type
4. **Fact Extraction**: Extract facts using NLP with entity recognition and categorization
5. **Vector Embedding**: Generate embeddings for semantic search capabilities
6. **Storage**: Store facts in Qdrant with case isolation and deduplication
7. **Real-time Updates**: Emit WebSocket events at each processing stage

### User Interface Design

#### Upload Section (Left Panel)
```
┌─────────────────────────────────┐
│ Discovery Document Processing    │
├─────────────────────────────────┤
│ Discovery Response Documents     │
│ ┌─────────────────────────────┐ │
│ │  Drop files/folders here    │ │
│ │  or click to browse         │ │
│ │  ─────────────────          │ │
│ │  [Browse Box Folder]        │ │
│ └─────────────────────────────┘ │
│                                 │
│ Request for Production (RFP)    │
│ ┌─────────────────────────────┐ │
│ │  Drop RFP document here     │ │
│ │  or click to browse         │ │
│ └─────────────────────────────┘ │
│                                 │
│ [Start Processing]              │
└─────────────────────────────────┘
```

#### Main Processing Area
```
┌────────────────────────────────────────────────────┐
│ Doc 1 ✓ │ Doc 2 │ Doc 3 │ Doc 4 │ Processing...   │
├────────────────────────────────────────────────────┤
│                                                    │
│  ┌──────────────────────────────────────────┐    │
│  │ Fact #1                                   │    │
│  │ The accident occurred on January 15, 2024 │    │
│  │ Category: Substantive                     │    │
│  │ Confidence: 0.95                          │    │
│  │ [View Source] [Edit] [Delete]            │    │
│  └──────────────────────────────────────────┘    │
│                                                    │
│  ┌──────────────────────────────────────────┐    │
│  │ Fact #2                                   │    │
│  │ Dr. Smith diagnosed a herniated disc      │    │
│  │ Category: Medical                         │    │
│  │ Confidence: 0.88                          │    │
│  │ [View Source] [Edit] [Delete]            │    │
│  └──────────────────────────────────────────┘    │
│                                                    │
│  [Complete Review]                                 │
└────────────────────────────────────────────────────┘
```

## EXAMPLES:

### Example 1: Processing Flow with WebSocket Events
```python
# Frontend initiates processing
POST /discovery/process
{
    "case_id": "case-123",
    "case_name": "Smith_v_Jones_2024",
    "discovery_files": ["file1.pdf", "file2.pdf"],
    "rfp_file": "rfp_document.pdf",
    "box_folder_id": "123456789"  # Optional
}

# WebSocket events emitted during processing
→ discovery:started {"case_id": "case-123", "total_files": 2}
→ discovery:document_found {"doc_id": "doc-1", "title": "Medical Records", "pages": 45}
→ discovery:fact_extracted {
    "fact_id": "fact-001",
    "content": "Patient treated for back pain on 1/15/2024",
    "category": "medical",
    "source": {"doc_id": "doc-1", "page": 12, "bbox": [100, 200, 400, 250]},
    "confidence": 0.92
}
→ discovery:document_completed {"doc_id": "doc-1", "facts_extracted": 15}
→ discovery:completed {"case_id": "case-123", "total_facts": 47}
```

### Example 2: Fact Review and Edit Flow
```javascript
// User clicks "View Source" on a fact card
handleViewSource(fact) {
    openPDFViewer({
        documentId: fact.source.doc_id,
        page: fact.source.page,
        highlight: fact.source.bbox,
        scrollTo: true
    });
}

// User edits a fact
handleEditFact(factId, newContent) {
    // Update fact in UI immediately
    updateFactCard(factId, newContent);
    
    // Send update to backend
    socket.emit('fact:update', {
        case_id: currentCaseId,
        fact_id: factId,
        content: newContent
    });
}

// User deletes a fact
handleDeleteFact(factId) {
    if (confirm('Delete this fact?')) {
        removeFact(factId);
        socket.emit('fact:delete', {
            case_id: currentCaseId,
            fact_id: factId
        });
    }
}
```

### Example 3: Document Tab Management
```javascript
// As documents are discovered, create tabs
socket.on('discovery:document_found', (data) => {
    addDocumentTab({
        id: data.doc_id,
        title: data.title || `Document ${tabCount + 1}`,
        pageCount: data.pages,
        status: 'processing'
    });
});

// Update tab status when document completes
socket.on('discovery:document_completed', (data) => {
    updateTabStatus(data.doc_id, 'ready');
    updateFactCount(data.doc_id, data.facts_extracted);
});

// Mark tab as reviewed
handleCompleteReview(docId) {
    updateTabStatus(docId, 'completed');
    // Show green checkmark on tab
}
```

### Example 4: Box Integration Flow
```javascript
// User selects Box folder option
async function handleBoxFolderSelect() {
    const boxPicker = new Box.ContentPicker();
    boxPicker.addListener('choose', async (items) => {
        const folderId = items[0].id;
        setBoxFolderId(folderId);
        
        // Fetch folder contents preview
        const response = await fetch(`/api/box/folder/${folderId}/preview`);
        const files = await response.json();
        displayFilePreview(files);
    });
    boxPicker.show();
}
```

### Example 5: Fact Deduplication Logic
```python
async def check_duplicate_fact(case_name: str, new_fact: ExtractedFact) -> bool:
    """Check if similar fact already exists in the case database."""
    
    # Search for similar facts using vector similarity
    similar_facts = await vector_store.search(
        collection_name=f"{case_name}_facts",
        query_vector=new_fact.embedding,
        limit=5,
        score_threshold=0.85  # High similarity threshold
    )
    
    # Additional text similarity check
    for existing_fact in similar_facts:
        similarity = calculate_text_similarity(
            new_fact.content, 
            existing_fact.payload.content
        )
        if similarity > 0.9:  # 90% text similarity
            return True  # Duplicate found
    
    return False  # No duplicate
```

## DOCUMENTATION:

### Core React Libraries
- **url**: https://react.dev/reference/react
- **why**: Core React documentation for component development

- **url**: https://react.dev/learn/synchronizing-with-effects
- **why**: Understanding React effects for real-time updates

### PDF Viewer Libraries
- **url**: https://react-pdf-viewer.dev/
- **why**: Main documentation for @react-pdf-viewer library

- **url**: https://react-pdf-viewer.dev/plugins/highlight/
- **why**: Highlight plugin for text selection and annotation

- **url**: https://github.com/agentcooper/react-pdf-highlighter
- **why**: Alternative PDF highlighter specifically for annotations

### File Upload Libraries
- **url**: https://react-dropzone.js.org/
- **why**: react-dropzone documentation for drag-and-drop uploads

- **url**: https://github.com/react-dropzone/react-dropzone
- **why**: GitHub repo with examples and advanced usage

### WebSocket Documentation
- **url**: https://python-socketio.readthedocs.io/en/stable/api.html
- **why**: Python SocketIO server documentation

- **url**: https://socket.io/docs/v4/client-api/
- **why**: SocketIO client documentation for React integration

### AI and NLP Libraries
- **url**: https://ai.pydantic.dev/llms.txt
- **why**: Pydantic AI documentation for structured outputs

- **url**: https://spacy.io/api/doc
- **why**: spaCy documentation for NLP entity extraction

### Box API Documentation
- **url**: https://developer.box.com/reference/
- **why**: Box API reference for folder operations

- **url**: https://github.com/box/box-python-sdk
- **why**: Box Python SDK for backend integration

### Vector Database
- **mcp**: Context7 MCP Server - search for "qdrant"
- **why**: Qdrant vector database documentation for fact storage

### Testing Frameworks
- **url**: https://docs.pytest.org/en/stable/
- **why**: pytest documentation for backend testing

- **url**: https://testing-library.com/docs/react-testing-library/intro/
- **why**: React Testing Library for frontend component tests

### Project Files
- **file**: CLAUDE.md
- **why**: Project structure, testing requirements, and coding standards

- **file**: Clerk/src/ai_agents/fact_extractor.py
- **why**: Existing fact extraction implementation

- **file**: Clerk/src/document_processing/discovery_splitter_normalized.py
- **why**: Document splitting logic with normalized schema

- **file**: Clerk/src/websocket/socket_server.py
- **why**: WebSocket event implementation

- **file**: Clerk/src/models/unified_document_models.py
- **why**: Document data models and schemas

- **file**: start_services_with_postgres.py
- **why**: Service startup configuration with CPU profile

## OTHER CONSIDERATIONS:

### Implementation Priorities (MVP Focus)
1. **Core Functionality First**: Focus on basic upload, processing, and display before advanced features
2. **Iterative Enhancement**: Start with simple fact cards, add editing capabilities in phase 2
3. **Performance Optimization**: Handle large PDFs (500+ pages) gracefully with streaming
4. **Error Recovery**: Implement robust error handling for partial processing failures

### Technical Gotchas and Solutions

#### 1. Large PDF Handling
- **Issue**: Browser memory limits when loading large PDFs
- **Solution**: Implement PDF.js with virtual scrolling and lazy page loading
- **Code Example**:
```javascript
const pdfViewer = new PDFViewer({
    container: viewerContainer,
    enableWebGL: true,
    renderInteractiveForms: false,
    maxCanvasPixels: 16777216  // Limit canvas size
});
```

#### 2. WebSocket Connection Management
- **Issue**: Connection drops during long processing sessions
- **Solution**: Implement automatic reconnection with exponential backoff
- **Code Example**:
```javascript
const socket = io({
    reconnection: true,
    reconnectionDelay: 1000,
    reconnectionDelayMax: 5000,
    reconnectionAttempts: 10
});
```

#### 3. Fact Deduplication Edge Cases
- **Issue**: Similar facts with minor variations not caught by vector similarity
- **Solution**: Implement multi-level deduplication (vector + fuzzy text matching)
- **Threshold Tuning**: Start with 0.85 vector similarity, adjust based on testing

#### 4. Box API Rate Limits
- **Issue**: Box API has rate limits for file operations
- **Solution**: Implement request queuing and batch operations
- **Rate Limits**: 4 requests per second per user, 2000 requests per minute

#### 5. Case Isolation Security
- **Issue**: Ensuring complete data isolation between cases
- **Solution**: Always include case_name/case_id in all queries and validations
- **Validation Pattern**:
```python
@require_case_context("read")
async def get_facts(case_context: CaseContext):
    # case_context automatically validated by middleware
    facts = await vector_store.search(
        collection_name=f"{case_context.case_name}_facts"
    )
```

#### 6. Browser Compatibility
- **PDF Features**: Test text selection/highlighting across Chrome, Firefox, Safari, Edge
- **File Upload**: Folder upload via webkitdirectory only works in Chrome/Edge
- **Fallback**: Provide Box folder selection as alternative to local folder upload

#### 7. State Management During Processing
- **Issue**: Managing UI state across multiple concurrent document processes
- **Solution**: Use Redux or Zustand for centralized state management
- **Structure**:
```javascript
const discoveryState = {
    processingId: 'proc-123',
    documents: {
        'doc-1': { status: 'completed', facts: 15 },
        'doc-2': { status: 'processing', facts: 3 },
        'doc-3': { status: 'pending', facts: 0 }
    },
    activeFacts: { /* fact data */ },
    websocketStatus: 'connected'
}
```

### Performance Considerations
1. **Chunked Processing**: Process documents in parallel but limit to 3-5 concurrent
2. **Fact Batching**: Send fact updates in batches of 10-20 to reduce WebSocket traffic
3. **Virtual Scrolling**: For fact cards when dealing with 100+ facts per document
4. **Caching**: Cache PDF pages client-side after first load

### Accessibility Requirements
1. **Keyboard Navigation**: Tab through fact cards, Enter to edit, Space to view source
2. **Screen Reader Support**: ARIA labels for all interactive elements
3. **High Contrast Mode**: Ensure fact cards and highlights visible in high contrast
4. **Focus Management**: Return focus to fact card after PDF viewer closes

### Development and Testing Checklist
- [ ] Set up react-dropzone with file validation
- [ ] Implement PDF viewer with highlight support
- [ ] Create WebSocket connection manager with reconnection
- [ ] Build fact card components with edit/delete functionality
- [ ] Implement document tab management system
- [ ] Add Box folder picker integration
- [ ] Create comprehensive error boundaries
- [ ] Write unit tests for fact deduplication logic
- [ ] Test with large PDFs (500+ pages)
- [ ] Verify case isolation in all API calls
- [ ] Load test WebSocket with 50+ concurrent users
- [ ] Cross-browser testing for PDF features
- [ ] Accessibility audit with screen reader

### Future Enhancements (Post-MVP)
1. **Batch Operations**: Select multiple facts for bulk actions
2. **Fact Relationships**: Link related facts across documents
3. **RFP Matching**: Automatically match facts to RFP requirements
4. **Export Options**: Export reviewed facts to various formats
5. **Collaboration**: Multiple users reviewing same discovery set
6. **Version History**: Track changes to facts over time
7. **Smart Suggestions**: AI-powered fact categorization improvements
8. **Advanced Search**: Search within discovered facts with filters