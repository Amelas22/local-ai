# Clerk Legal AI System - Claude Context

## 🚨 IMPORTANT: Documentation Update Rule

**ALWAYS update the following files when making changes to the codebase:**
1. **CLAUDE.md** - Update architecture, components, or configuration sections when:
   - Adding new features or modules
   - Changing API endpoints or services
   - Modifying the technology stack
   - Updating environment variables or configuration
   - Changing deployment procedures

2. **tasks.md** - Update task status when:
   - Completing any task (mark as ✅)
   - Starting work on a task (mark as 🚧)
   - Identifying new tasks to add
   - Updating the "Last Updated" date
   - Adding to "Recent Accomplishments" section

3. **planning.md** - Update when:
   - Architectural decisions are made
   - Development priorities change
   - New phases or milestones are defined
   - Technical debt is identified or resolved

**This ensures the documentation remains the single source of truth for the project.**

---

## Project Overview

**Clerk** is a comprehensive legal AI system designed to revolutionize motion drafting and document management for law firms. The system automates document processing, provides intelligent search capabilities, and generates legal motion drafts using AI.

### Core Capabilities
- **Document Processing**: Automatically ingests PDF documents from Box cloud storage
- **Hybrid Search**: Combines vector similarity with full-text search for precise legal research
- **Motion Drafting**: AI-powered generation of legal motion outlines and complete drafts
- **Case Isolation**: Strict data separation ensuring case information never crosses between matters
- **Discovery Processing**: AI-powered document classification and processing

## Architecture

### Technology Stack
- **Backend**: FastAPI (Python 3.11+)
- **Vector Database**: Qdrant with hybrid search capabilities
- **Document Storage**: Box API integration
- **AI Models**: OpenAI GPT models for context generation and drafting
- **Embedding Model**: OpenAI text-embedding-3-small
- **Real-time Updates**: Socket.io for WebSocket communication
- **Frontend**: React 18 + TypeScript + Material-UI + Redux Toolkit

### Key Components

#### Document Processing Pipeline
1. **Box Traversal**: Recursively scans Box folders for PDF documents
2. **Unified Document Management**: Combined deduplication and discovery system
   - SHA-256 hash-based duplicate detection
   - AI-powered document classification (motions, depositions, etc.)
   - Metadata extraction (parties, dates, key facts)
   - Case-specific document registries
3. **Text Extraction**: Multi-library PDF processing (pdfplumber, PyPDF2, pdfminer)
4. **Chunking**: ~1400 character chunks with 200 character overlap
   - Each chunk linked to source document via `document_id`
5. **Context Generation**: LLM-powered contextual summaries for each chunk
6. **Vector Storage**: Embeddings stored in Qdrant with case metadata
7. **Fact Extraction**: Extracts case-specific facts with proper entity recognition

#### API Endpoints
- `/health` - System health checks
- `/process-folder` - Process Box folder for documents
- `/discovery/process` - Process discovery with WebSocket updates
- `/search` - Hybrid search across case documents
- `/generate-motion-outline` - Create motion outlines from opposing counsel's filings
- `/generate-motion-draft` - Full motion drafting capabilities
- `/websocket/status` - WebSocket connection status
- `/ws/socket.io` - WebSocket endpoint for real-time updates

### Directory Structure
```
/Clerk/
├── main.py                 # FastAPI application entry point
├── src/
│   ├── document_injector.py      # Legacy document processing
│   ├── document_injector_unified.py # Unified document processing
│   ├── ai_agents/                # Legal AI agents
│   │   ├── motion_drafter.py     # Motion drafting logic
│   │   ├── case_researcher.py    # Case research agent
│   │   ├── legal_document_agent.py
│   │   ├── fact_extractor.py     # Legal fact extraction
│   │   └── evidence_discovery_agent.py # Evidence search for motions
│   ├── document_processing/      # PDF processing utilities
│   │   ├── box_client.py         # Box API integration
│   │   ├── chunker.py            # Document chunking
│   │   ├── pdf_extractor.py      # PDF text extraction
│   │   ├── source_document_indexer.py # Legacy source document classification
│   │   ├── qdrant_deduplicator.py    # Legacy deduplication
│   │   └── unified_document_manager.py # Unified document management
│   ├── models/                   # Data models
│   │   ├── source_document_models.py  # Legacy source document models
│   │   └── unified_document_models.py # Unified document models
│   ├── vector_storage/           # Vector database operations
│   │   ├── qdrant_store.py       # Qdrant integration
│   │   └── embeddings.py         # Embedding generation
│   ├── integrations/             # External API integrations
│   │   ├── perplexity.py         # Legal research API
│   │   └── docx_generator.py     # Document generation
│   ├── websocket/                # WebSocket real-time updates
│   │   ├── __init__.py
│   │   └── socket_server.py      # Socket.io server implementation
│   └── utils/                    # Shared utilities
├── config/                       # Configuration management
├── migrations/                   # Database migrations
└── tests/                       # Test suites
```

## Environment Setup

### Required Environment Variables
```bash
# Box API Configuration
BOX_CLIENT_ID=your_box_client_id
BOX_CLIENT_SECRET=your_box_client_secret
BOX_ENTERPRISE_ID=your_enterprise_id
BOX_JWT_KEY_ID=your_jwt_key_id
BOX_PRIVATE_KEY="-----BEGIN ENCRYPTED PRIVATE KEY-----..."
BOX_PASSPHRASE=your_private_key_passphrase

# Qdrant Configuration
QDRANT_HOST=your_qdrant_host
QDRANT_PORT=6333
QDRANT_API_KEY=your_qdrant_api_key
QDRANT_HTTPS=true

# OpenAI Configuration
OPENAI_API_KEY=your_openai_api_key
CONTEXT_LLM_MODEL=gpt-3.5-turbo

# Optional Overrides
CHUNK_SIZE=1400
CHUNK_OVERLAP=200
```

### Development Commands

#### Installation
```bash
cd /mnt/c/Webapps/local-ai/Clerk
pip install -r requirements.txt
```

#### Running the Application
```bash
# Start FastAPI server
python main.py

# Or with uvicorn directly
uvicorn main:app --host 0.0.0.0 --port 8000 --reload
```

#### Testing
```bash
# Run all tests
python -m pytest tests/

# Test specific component
python -m pytest tests/test_document_processing/

# Test Box connection
python test_box_connection.py

# Test legacy document injection
python -m src.document_injector --folder-id 123456789

# Test unified document injection
python cli_injector_unified.py --folder-id 123456789 --max-documents 5

# Test unified system with search
python cli_injector_unified.py --folder-id 123456789 --search "motion to dismiss"

# Test unified connections
python cli_injector_unified.py --test-connection
```

#### Database Operations
```bash
# Run migrations
psql -d your_qdrant_db -f migrations/001_hybrid_search_setup.sql

# Check document statistics
python -c "from src.document_injector import DocumentInjector; injector = DocumentInjector(); print(injector.deduplicator.get_statistics())"
```

## Common Development Patterns

### Document Processing
```python
from src.document_injector import DocumentInjector

# Initialize with cost tracking
injector = DocumentInjector(enable_cost_tracking=True)

# Process single case folder
results = injector.process_case_folder("123456789")

# Get cost report
cost_report = injector.get_cost_report()
```

### Hybrid Search
```python
from src.vector_storage import FullTextSearchManager, EmbeddingGenerator

search_manager = FullTextSearchManager()
embedding_gen = EmbeddingGenerator()

query = "patient diagnosis on January 15, 2023"
query_embedding = embedding_gen.generate_embedding(query)

results = search_manager.hybrid_search(
    case_name="Smith v. Jones",
    query_text=query,
    query_embedding=query_embedding,
    vector_weight=0.7,
    text_weight=0.3
)
```

### Motion Generation
```python
from src.ai_agents.motion_drafter import MotionDrafter

drafter = MotionDrafter()
outline = drafter.generate_outline(
    case_name="Smith v. Jones",
    opposing_motion_text="...",
    motion_type="summary_judgment"
)
```

## Critical Security Requirements

### Case Isolation
- **Case-Specific Collections**: Each case has its own document registry and collections
- **Unified Document Management**: Case-specific `{case_name}_documents` collection
- **Metadata Filtering**: Every query MUST include case_name filter
- **Duplicate Handling**: Same document can exist in multiple cases without conflicts
- **Chunk Linking**: All chunks linked to source documents via `document_id`
- **Verification**: Post-storage checks ensure documents are isolated
- **Logging**: Any cross-case data leakage is logged as critical error
- **Testing**: Regular isolation verification in test suites

### API Security
- Never log API keys or sensitive data
- Rotate keys regularly
- Use service accounts with minimal permissions
- Monitor for unusual API usage patterns


### Debug Commands
```bash
# Enable debug logging
export LOG_LEVEL=DEBUG
python main.py

# Check document processing stats
python -c "
from src.document_injector import DocumentInjector
injector = DocumentInjector()
print('Statistics:', injector.deduplicator.get_statistics())
"

# Verify case isolation
python -c "
from src.vector_storage.qdrant_store import QdrantVectorStore
store = QdrantVectorStore()
store.verify_case_isolation('Case Name')
"
```

## External Integrations

### Box API
- **Authentication**: JWT-based service account
- **Permissions**: Read access to matter folders
- **Rate Limits**: Respect Box API limits
- **Folder Structure**: Mirrors firm's case organization

## Development Guidelines

### Code Style
- Follow existing patterns in the codebase
- Use type hints consistently
- Implement proper error handling with retries
- Log important operations for debugging
- Never commit API keys or secrets

### Testing Strategy
- Unit tests for core functions
- Integration tests for API endpoints
- End-to-end tests for document processing pipeline
- Case isolation verification tests
- Performance tests for large document sets

### Deployment
- **Current**: Hostinger VPS deployment
- **Docker**: containerized deployment
- **Monitoring**: Implement logging and health checks
- **Caching**: Redis for frequently accessed data
- **Scaling**: Horizontal scaling for document processing

## Unified Document Management System

### Overview
The unified document management system combines document deduplication and source document discovery into a single, streamlined system. This replaces the previous separate systems for tracking duplicates and indexing documents for evidence discovery.

### Key Features
1. **Combined Registry and Discovery**: Single collection per case (`{case_name}_documents`)
2. **Intelligent Deduplication**: SHA-256 hash-based with duplicate location tracking
3. **AI-Powered Classification**: Automatically identifies document types (motions, depositions, etc.)
4. **Chunk-Document Linking**: Every chunk has `document_id` linking to its source document
5. **Case Isolation**: Each case has its own document collection, allowing same documents in multiple cases

### Document Classification
Documents are automatically classified into comprehensive types:
- **Legal Filings**: Motion, Complaint, Answer, Memorandum, Brief, Order
- **Discovery Documents**: Deposition, Interrogatory, Request for Admission/Production
- **Evidence Documents**: Police Report, Expert Report, Photos, Videos
- **Business/Financial**: Invoice, Contract, Financial Records, Employment Records, Insurance
- **Other Evidence**: Correspondence, Incident Reports, Witness Statements, Affidavits

### Document Processing Flow
1. **Hash Calculation**: Generate SHA-256 hash for deduplication
2. **Duplicate Check**: Verify if document already exists in case
3. **AI Classification**: Determine document type and extract metadata
4. **Entity Extraction**: Identify parties, dates, key facts
5. **Embedding Generation**: Create vector for semantic search
6. **Unified Storage**: Store all metadata in single collection
7. **Chunk Creation**: Generate chunks with `document_id` reference

### Evidence Discovery Features
1. **Semantic Search**: Find documents by legal argument or topic
2. **Document Type Filtering**: Search specific types of evidence
3. **Relevance Tagging**: Filter by liability, damages, causation, etc.
4. **Party and Date Extraction**: Find documents by involved parties or dates
5. **Key Page Identification**: Highlights most relevant pages within documents
6. **Duplicate Tracking**: See all locations where a document appears

### Key Components
- **UnifiedDocument Model**: Combines deduplication and discovery metadata
- **UnifiedDocumentManager**: Single manager for all document operations
- **Case-Specific Collections**: Each case has isolated document storage
- **Chunk Linking**: Direct connection between chunks and source documents

### Key Files
- `src/models/unified_document_models.py`: Unified document data models
- `src/document_processing/unified_document_manager.py`: Combined deduplication and indexing
- `src/document_injector_unified.py`: Updated document processing pipeline
- `cli_injector_unified.py`: Command-line interface for unified system

### Migration from Legacy System
- Legacy files remain for backward compatibility:
  - `src/document_processing/source_document_indexer.py` (legacy)
  - `src/document_processing/qdrant_deduplicator.py` (legacy)
  - `src/models/source_document_models.py` (legacy)
- New documents use unified system automatically
- Existing collections remain intact

## Discovery Production Processing

### Overview
Discovery productions often come as massive consolidated PDFs (200+ pages) containing multiple documents concatenated together. The discovery processing system automatically segments these productions into individual documents for proper processing and fact extraction.

### Key Features
1. **Automatic Multi-Document Detection**: Identifies large productions by file size and naming patterns
2. **Intelligent Boundary Detection**: Uses 25-page sliding windows with 5-page overlap to find document boundaries
3. **Document-Specific Context**: Generates context for each segmented document, not the entire production
4. **Fact Extraction Override**: Forces fact extraction for all discovery materials regardless of type
5. **Bates Number Preservation**: Maintains Bates numbering throughout processing
6. **Production Metadata Tracking**: Tracks production batch, date, producing party, and RFP responses

### Discovery Processing Endpoint
**POST `/process/discovery`**
```json
{
  "folder_id": "123456789",
  "case_name": "Smith_v_Jones_2024",
  "production_batch": "Defendant's First Production",
  "producing_party": "ABC Transport Corp",
  "production_date": "2024-06-30T12:00:00",
  "responsive_to_requests": ["RFP 1-25", "RFA 1-15"],
  "confidentiality_designation": "Confidential"
}
```

### Document Segmentation Process
1. **Boundary Detection Phase**:
   - Process PDF in 25-page windows
   - Identify document start/end markers
   - Build complete document map before processing
   
2. **Document Classification**:
   - Classify each segment into appropriate document type
   - Support for 70+ discovery document types
   - Confidence scoring for each classification

3. **Context-Aware Chunking**:
   - Generate context specific to each document
   - Maintain standard 1200/200 character chunking
   - Prepend document context to each chunk

### Large Document Handling
- **Single-Pass Processing**: Documents up to 50 pages
- **Chunked Processing**: Documents over 50 pages processed in sections
- **Section Context**: Each section gets its own context summary

### Discovery-Specific Document Types
- Driver/Employee Documentation (DQF, employment apps, drug tests)
- Vehicle/Equipment Records (maintenance, inspection, ECM data)
- Hours of Service (logs, trip reports, bills of lading)
- Communication Records (emails, satellite messages, texts)
- Safety/Compliance (violations, citations, accident reports)
- Company Documentation (policies, handbooks, training materials)

### Configuration Settings
```python
# Discovery processing settings
DISCOVERY_WINDOW_SIZE = 25  # Pages per analysis window
DISCOVERY_WINDOW_OVERLAP = 5  # Overlap between windows
DISCOVERY_BOUNDARY_CONFIDENCE_THRESHOLD = 0.7
DISCOVERY_BOUNDARY_DETECTION_MODEL = "gpt-4.1-mini-2025-04-14"
DISCOVERY_MULTI_DOC_SIZE_THRESHOLD_MB = 10  # Trigger multi-doc processing
```

### Key Files
- `src/document_processing/discovery_splitter.py`: Core segmentation and boundary detection
- `src/models/unified_document_models.py`: Discovery-specific models and document types
- `test_discovery_processing.py`: Test suite for discovery processing
- `examples/discovery_processing_example.py`: Usage examples

## Motion Drafting System

### Current Implementation
The motion drafting system is built around the `/draft-motion-cached` endpoint and uses a sophisticated multi-stage approach:

1. **Outline Processing**: Receives structured outlines from doc-converter with sections, arguments, and authorities
2. **Caching Layer**: Uses `OutlineCacheManager` to store large outlines for efficient reprocessing
3. **Section-by-Section Generation**: Each section type (Introduction, Facts, Legal Standard, Arguments, etc.) is generated individually
4. **Quality Control**: Implements confidence scoring, coherence checking, and citation verification
5. **Export Options**: DOCX generation with professional formatting and Box cloud storage integration

### Motion Section Types
- `PREINTRODUCTION`: Case caption and header information
- `INTRODUCTION`: Opening statement and motion purpose
- `PROCEDURAL_BACKGROUND`: Case history and procedural posture
- `MEMORANDUM_OF_LAW`: Legal framework introduction
- `LEGAL_STANDARD`: Applicable legal tests and standards
- `ARGUMENT`/`SUB_ARGUMENT`: Main legal arguments with authorities
- `CONCLUSION`: Summary of requested relief
- `PRAYER_FOR_RELIEF`: Specific relief requested from court

### Key Motion Drafting Files
- `src/ai_agents/motion_drafter.py`: Core drafting engine with AI agents
- `src/ai_agents/rag_research_agent.py`: Research integration for evidence and citations
- `src/utils/legal_formatter.py`: Professional legal document formatting
- `src/utils/motion_cache_manager.py`: Performance optimization through caching
- `src/models/motion_models.py`: Data structures for motions and outlines

### Motion Quality Standards
To meet firm standards, the system must produce motions with:
- **Fact-Specific Arguments**: Deep integration of case facts throughout
- **Dense Citations**: Pinpoint citations with explanatory parentheticals
- **Evidence Integration**: Specific deposition page/line citations
- **Natural Flow**: Progressive argument building with smooth transitions
- **Procedural Sophistication**: Nuanced understanding of legal contexts
- **Professional Advocacy Voice**: Assertive, professional tone
- **Anticipatory Arguments**: Preemptive counter-argument responses

## Priority Improvements for Motion Drafting

### Phase 1: Fact and Evidence Integration (Immediate Priority)
1. **Enhanced Fact Extraction System**
   - Build comprehensive fact database from case documents
   - Create fact-to-argument mapping system
   - Implement timeline generation for chronological clarity

2. **Evidence Citation Enhancement**
   - Parse depositions for page/line citations
   - Extract and index exhibit references
   - Create evidence-to-argument linkage system

3. **Research Integration Improvements**
   - Enhance RAG agent to retrieve specific evidence
   - Implement multi-database querying (case + firm knowledge)
   - Add citation verification against source documents

### Phase 2: Citation and Authority Enhancement
1. **Advanced Citation Processing**
   - Implement Bluebook-compliant formatting
   - Add pinpoint page citations from case law
   - Generate explanatory parentheticals
   - Implement proper signal usage

2. **Case Law Analysis Depth**
   - Multi-layer case analysis system
   - Doctrinal development tracking
   - Circuit split identification
   - Distinguishing opposing authorities

### Phase 3: Document Flow and Coherence
1. **Advanced Document Planning**
   - Thematic connection mapping
   - Progressive argument building logic
   - Natural transition generation
   - Cross-reference tracking

2. **Adaptive Length Management**
   - Dynamic word count targets
   - Content density optimization
   - Section balancing algorithms

### Phase 4: Professional Enhancement
1. **Tone and Voice Refinement**
   - Fine-tune on firm's successful motions
   - Implement advocacy voice patterns
   - Remove academic/mechanical language

2. **Procedural Sophistication**
   - Specialized modules for different motion types
   - Burden-shifting framework implementation
   - Multi-factor test application

## Technical Implementation Details

### API Endpoints for Motion Drafting
- `POST /draft-motion-cached`: Main endpoint for full motion generation
- `POST /draft-motion-from-cache`: Generate from previously cached outline
- `POST /cache-outline`: Store large outlines for reuse
- `POST /draft-motion`: Direct motion generation without caching
- `GET /motion-export/{motion_id}`: Export completed motions

### Development Commands for Motion Testing
```bash
# Test motion generation with sample outline
curl -X POST "http://localhost:8000/draft-motion-cached" \
  -H "Content-Type: application/json" \
  -d @sample_outline.json

# Check motion cache status
python -c "from src.utils.motion_cache_manager import MotionCacheManager; cache = MotionCacheManager(); print(cache.get_cache_stats())"

# Test citation extraction
python -c "from src.ai_agents.citation_processor import CitationProcessor; processor = CitationProcessor(); processor.test_extraction('sample_deposition.txt')"
```

### Performance Optimization
- **Parallel Section Generation**: Process independent sections concurrently
- **Smart Caching**: Cache frequently used legal authorities and boilerplate
- **Context Window Management**: Optimize token usage for long documents
- **Batch Processing**: Group similar operations for efficiency

## Next Steps for Development

1. **Immediate (Week 1-2)**:
   - Implement enhanced fact extraction system
   - Build evidence citation parser
   - Create fact-to-argument mapping

2. **Short-term (Week 3-4)**:
   - Enhance citation formatting system
   - Implement case law depth analysis
   - Improve RAG research integration

3. **Medium-term (Month 2)**:
   - Develop document flow optimization
   - Implement adaptive length management
   - Create procedural sophistication modules

4. **Long-term (Month 3+)**:
   - Fine-tune advocacy voice
   - Build template learning system
   - Implement comprehensive quality metrics

## Frontend Architecture

### Overview
The Clerk frontend provides a modern, responsive web interface for legal teams to interact with the document processing system. Built with React and TypeScript, it emphasizes real-time feedback, professional design, and intuitive workflows specifically tailored for legal professionals.

### Technology Stack
- **Framework**: React 18+ with TypeScript for type safety
- **UI Library**: Material-UI (MUI) for professional, consistent design
- **State Management**: Redux Toolkit with RTK Query for API integration
- **Real-time Communication**: WebSockets via Socket.io for live updates
- **Visualization**: D3.js for custom visualizations, Recharts for charts
- **Build Tool**: Vite for fast development and optimized production builds
- **Styling**: Tailwind CSS with custom legal-themed design system
- **Testing**: Jest + React Testing Library for unit/integration tests
- **E2E Testing**: Playwright for end-to-end testing

### Frontend Directory Structure
```
Clerk/
├── frontend/
│   ├── src/
│   │   ├── components/
│   │   │   ├── discovery/          # Discovery processing components
│   │   │   │   ├── DiscoveryForm.tsx
│   │   │   │   ├── ProcessingVisualization.tsx
│   │   │   │   ├── DocumentStream.tsx
│   │   │   │   ├── ChunkingAnimation.tsx
│   │   │   │   ├── BatesNumberDisplay.tsx
│   │   │   │   └── ProductionMetadata.tsx
│   │   │   ├── motion/             # Motion drafting components
│   │   │   │   ├── MotionOutlineForm.tsx
│   │   │   │   ├── DraftingProgress.tsx
│   │   │   │   └── MotionPreview.tsx
│   │   │   ├── search/             # Search interface components
│   │   │   │   ├── SearchBar.tsx
│   │   │   │   ├── SearchResults.tsx
│   │   │   │   └── FilterPanel.tsx
│   │   │   ├── common/             # Shared components
│   │   │   │   ├── Layout.tsx
│   │   │   │   ├── Header.tsx
│   │   │   │   ├── Sidebar.tsx
│   │   │   │   ├── LoadingStates.tsx
│   │   │   │   └── ErrorBoundary.tsx
│   │   │   └── dashboard/          # Dashboard components
│   │   │       ├── CaseDashboard.tsx
│   │   │       ├── ProcessingStats.tsx
│   │   │       └── RecentActivity.tsx
│   │   ├── services/               # API and service layers
│   │   │   ├── api/
│   │   │   │   ├── discoveryApi.ts
│   │   │   │   ├── motionApi.ts
│   │   │   │   └── searchApi.ts
│   │   │   ├── websocket/
│   │   │   │   ├── socketClient.ts
│   │   │   │   └── eventHandlers.ts
│   │   │   └── utils/
│   │   │       ├── apiClient.ts
│   │   │       └── errorHandler.ts
│   │   ├── store/                  # Redux store configuration
│   │   │   ├── store.ts
│   │   │   ├── slices/
│   │   │   │   ├── discoverySlice.ts
│   │   │   │   ├── motionSlice.ts
│   │   │   │   └── uiSlice.ts
│   │   │   └── api/
│   │   │       └── baseApi.ts
│   │   ├── hooks/                  # Custom React hooks
│   │   │   ├── useWebSocket.ts
│   │   │   ├── useDiscoveryProcess.ts
│   │   │   └── useAuth.ts
│   │   ├── types/                  # TypeScript type definitions
│   │   │   ├── discovery.types.ts
│   │   │   ├── motion.types.ts
│   │   │   ├── api.types.ts
│   │   │   └── websocket.types.ts
│   │   ├── utils/                  # Utility functions
│   │   │   ├── validators.ts
│   │   │   ├── formatters.ts
│   │   │   └── constants.ts
│   │   ├── styles/                 # Global styles and themes
│   │   │   ├── theme.ts
│   │   │   ├── globals.css
│   │   │   └── tailwind.css
│   │   ├── App.tsx
│   │   └── main.tsx
│   ├── public/                     # Static assets
│   ├── tests/                      # Test files
│   ├── package.json
│   ├── tsconfig.json
│   ├── vite.config.ts
│   ├── tailwind.config.js
│   └── .env.example
```

### Key Frontend Components

#### Discovery Processing UI
1. **DiscoveryForm Component**
   - Form validation with react-hook-form
   - Auto-complete for case names
   - Date picker for production dates
   - Multi-select for responsive requests
   - Real-time validation feedback

2. **ProcessingVisualization Component**
   - Real-time document discovery feed
   - Animated chunking visualization
   - Vector embedding progress
   - Storage confirmation animations
   - Error state handling

3. **DocumentStream Component**
   - Live updates as documents are found
   - Bates number highlighting
   - Document type badges
   - Confidence score indicators
   - Click-to-expand details

#### WebSocket Integration
```typescript
// Event types for discovery processing
interface DiscoveryEvents {
  'discovery:started': { caseId: string; totalFiles: number };
  'discovery:document_found': { 
    documentId: string;
    title: string;
    type: DocumentType;
    batesRange?: { start: string; end: string };
  };
  'discovery:chunking': {
    documentId: string;
    progress: number;
    chunksCreated: number;
  };
  'discovery:embedding': {
    chunkId: string;
    progress: number;
  };
  'discovery:stored': {
    documentId: string;
    vectorsStored: number;
  };
  'discovery:completed': {
    summary: ProcessingSummary;
  };
  'discovery:error': {
    error: string;
    documentId?: string;
  };
}
```

### Frontend Development Patterns

#### API Integration Pattern
```typescript
// Using RTK Query for API calls
export const discoveryApi = createApi({
  reducerPath: 'discoveryApi',
  baseQuery: fetchBaseQuery({
    baseUrl: '/api/discovery',
    prepareHeaders: (headers) => {
      const token = selectAuthToken(store.getState());
      if (token) headers.set('authorization', `Bearer ${token}`);
      return headers;
    },
  }),
  endpoints: (builder) => ({
    processDiscovery: builder.mutation<ProcessingResult, DiscoveryRequest>({
      query: (request) => ({
        url: '/process/normalized',
        method: 'POST',
        body: request,
      }),
    }),
  }),
});
```

#### Component Structure Pattern
```typescript
// Consistent component structure
interface ComponentProps {
  className?: string;
  onComplete?: (result: any) => void;
  initialData?: Partial<FormData>;
}

export const DiscoveryForm: React.FC<ComponentProps> = ({
  className,
  onComplete,
  initialData,
}) => {
  // Hook usage at the top
  const dispatch = useAppDispatch();
  const { processDiscovery, isLoading } = useDiscoveryProcess();
  
  // Local state
  const [formData, setFormData] = useState(initialData || {});
  
  // Event handlers
  const handleSubmit = async (data: FormData) => {
    const result = await processDiscovery(data);
    onComplete?.(result);
  };
  
  // Render
  return (
    <form onSubmit={handleSubmit} className={className}>
      {/* Form content */}
    </form>
  );
};
```

### Frontend Commands

#### Development
```bash
cd frontend
npm install                 # Install dependencies
npm run dev                # Start development server
npm run build             # Build for production
npm run preview           # Preview production build
npm run test              # Run tests
npm run test:e2e          # Run E2E tests
npm run lint              # Run ESLint
npm run type-check        # Run TypeScript compiler
```

#### Testing
```bash
# Unit tests
npm run test:unit         # Run unit tests
npm run test:watch        # Run tests in watch mode
npm run test:coverage     # Generate coverage report

# E2E tests
npm run test:e2e          # Run Playwright tests
npm run test:e2e:ui       # Open Playwright UI
```

### Environment Configuration
```env
# Frontend environment variables
VITE_API_URL=http://localhost:8000
VITE_WS_URL=ws://localhost:8000
VITE_AUTH_ENABLED=false
VITE_MOCK_API=false
VITE_LOG_LEVEL=info
```

### Security Considerations
1. **Input Validation**: All user inputs validated client-side and server-side
2. **XSS Prevention**: React's built-in XSS protection + Content Security Policy
3. **CORS Configuration**: Strict origin validation for API requests
4. **WebSocket Security**: Token-based authentication for real-time connections
5. **Sensitive Data**: No storage of sensitive data in localStorage
6. **HTTPS Only**: Enforce HTTPS in production environments

### Performance Optimization
1. **Code Splitting**: Route-based code splitting with React.lazy
2. **Bundle Optimization**: Tree shaking and minification via Vite
3. **Image Optimization**: Lazy loading and responsive images
4. **Memoization**: React.memo for expensive components
5. **Virtual Scrolling**: For large document lists
6. **Debouncing**: Search and form inputs debounced
7. **WebSocket Throttling**: Rate limiting for real-time updates

### Accessibility Standards
1. **WCAG 2.1 AA Compliance**: Full keyboard navigation support
2. **Screen Reader Support**: Proper ARIA labels and landmarks
3. **High Contrast Mode**: Alternative color schemes
4. **Focus Management**: Clear focus indicators
5. **Error Announcements**: Screen reader friendly error messages

### Integration with Backend

#### API Endpoints Used
- `POST /api/discovery/process/normalized` - Main discovery processing
- `GET /api/discovery/productions/{case_id}` - List productions
- `GET /api/discovery/search/bates/{case_id}/{bates_number}` - Bates search
- `GET /api/discovery/stats/{case_id}` - Processing statistics
- `WS /ws/discovery` - WebSocket connection for real-time updates

#### Authentication Flow
1. Initial authentication via `/api/auth/login`
2. JWT token stored in memory (not localStorage)
3. Token included in all API requests
4. WebSocket authentication via query parameter
5. Automatic token refresh before expiration

## WebSocket Real-time Architecture

### Overview
The Clerk system implements WebSocket communication using Socket.io for real-time updates during document processing. This eliminates the need for polling and provides instant feedback to users as their documents are processed.

### WebSocket Components

#### Frontend WebSocket Implementation
```typescript
// socketClient.ts - Singleton WebSocket client
import { io, Socket } from 'socket.io-client';

class SocketClient {
  private socket: Socket | null = null;
  
  connect(url?: string): void {
    this.socket = io(url || import.meta.env.VITE_WS_URL, {
      path: '/ws/socket.io/',
      transports: ['websocket'],
      reconnection: false, // Manual reconnection for better control
      auth: { token: store.getState().auth.token }
    });
  }
}

// Usage in components with custom hook
const { connected, emit, on } = useWebSocket();

// Subscribe to events
useEffect(() => {
  const unsubscribe = on('discovery:document_found', (data) => {
    console.log('New document:', data);
  });
  
  return unsubscribe; // Cleanup
}, []);
```

#### Backend WebSocket Server
```python
# socket_server.py - Socket.io server with FastAPI
import socketio

sio = socketio.AsyncServer(
    async_mode='asgi',
    cors_allowed_origins='*'
)

# Mount on FastAPI
app.mount("/ws", socketio.ASGIApp(sio, socketio_path='/socket.io'))

# Emit events during processing
async def emit_document_found(processing_id, document_id, title, doc_type):
    await sio.emit('discovery:document_found', {
        'processingId': processing_id,
        'documentId': document_id,
        'title': title,
        'type': doc_type
    })
```

### WebSocket Event Flow

#### Discovery Processing Events
1. **discovery:started**
   ```json
   {
     "processingId": "uuid",
     "caseId": "Smith_v_Jones_2024",
     "totalFiles": 150
   }
   ```

2. **discovery:document_found**
   ```json
   {
     "documentId": "doc_123",
     "title": "Deposition of John Smith",
     "type": "deposition",
     "pageCount": 45,
     "batesRange": {"start": "DEF000001", "end": "DEF000045"},
     "confidence": 0.95
   }
   ```

3. **discovery:chunking**
   ```json
   {
     "documentId": "doc_123",
     "progress": 75.5,
     "chunksCreated": 30
   }
   ```

4. **discovery:embedding**
   ```json
   {
     "documentId": "doc_123",
     "chunkId": "chunk_456",
     "progress": 80.0
   }
   ```

5. **discovery:stored**
   ```json
   {
     "documentId": "doc_123",
     "vectorsStored": 30
   }
   ```

6. **discovery:completed**
   ```json
   {
     "processingId": "uuid",
     "summary": {
       "totalDocuments": 150,
       "processedDocuments": 148,
       "totalChunks": 4500,
       "totalVectors": 4500,
       "totalErrors": 2,
       "processingTime": 1845.5,
       "averageConfidence": 0.92
     }
   }
   ```

### WebSocket Redux Integration
```typescript
// WebSocket events update Redux state automatically
const discoverySlice = createSlice({
  name: 'discovery',
  reducers: {
    documentFound: (state, action) => {
      state.documents.push(action.payload);
      state.stats.documentsFound += 1;
    },
    documentChunking: (state, action) => {
      const doc = state.documents.find(d => d.id === action.payload.documentId);
      if (doc) {
        doc.chunks = action.payload.chunksCreated;
        doc.progress = action.payload.progress;
      }
    }
  }
});
```

### Connection Management
- **Automatic Reconnection**: Exponential backoff strategy (1s, 2s, 4s, 8s, 16s)
- **Connection States**: Tracked in Redux (disconnected, connecting, connected, error)
- **Event Buffering**: Events queued during disconnection (planned feature)
- **Health Monitoring**: Regular ping/pong for connection health

### Testing WebSocket Connections
```bash
# Check WebSocket status
curl http://localhost:8000/websocket/status

# Response
{
  "status": "active",
  "connections": {
    "total": 3,
    "connections": [
      {
        "sid": "abc123",
        "connected_at": "2025-01-02T10:30:00Z",
        "case_id": "Smith_v_Jones_2024"
      }
    ]
  }
}
```

### Security Considerations
1. **Authentication**: JWT token passed in connection handshake
2. **Case Isolation**: Events filtered by case_id subscription
3. **Rate Limiting**: Prevent event flooding (planned)
4. **SSL/TLS**: WebSocket upgraded from HTTPS in production

### Performance Benefits
- **Instant Updates**: No polling delay, updates arrive immediately
- **Reduced Bandwidth**: Only sends data when changes occur
- **Server Efficiency**: One persistent connection vs many HTTP requests
- **Scalability**: Can handle thousands of concurrent connections

### WebSocket Troubleshooting

#### Common Issues and Solutions

1. **Socket.io Version Mismatch**
   - **Issue**: Frontend uses Socket.io v4 client, backend uses python-socketio v5
   - **Solution**: Ensure compatibility by:
     - Adding `async_handlers=True` to AsyncServer configuration
     - Allow both websocket and polling transports
     - Use compatible versions (socket.io-client 4.7.x with python-socketio 5.x)

2. **Connection Through Reverse Proxy**
   - **Issue**: WebSocket fails when connecting through Caddy/Nginx
   - **Solution**: 
     - Use relative URLs in frontend (let proxy handle routing)
     - Ensure proxy forwards WebSocket upgrade headers
     - Configure CORS properly on backend

3. **Path Configuration**
   - **Issue**: Socket.io path mismatch between client and server
   - **Client Path**: `/ws/socket.io/`
   - **Server Mount**: `/ws` (Socket.io adds `/socket.io/` automatically)
   - **Solution**: Ensure paths align: client uses `/ws/socket.io/`, server mounts at `/ws`

4. **Authentication Issues**
   - **Issue**: WebSocket connection rejected due to auth
   - **Solution**: Pass auth token in connection options:
     ```javascript
     io(url, { auth: { token: 'your-token' } })
     ```

5. **CORS Problems**
   - **Issue**: Cross-origin requests blocked
   - **Solution**: Configure Socket.io server with:
     ```python
     sio = socketio.AsyncServer(cors_allowed_origins='*')
     ```

#### Debug Commands
```bash
# Test WebSocket connection
curl http://localhost:8000/websocket/status

# Test WebSocket events
curl -X GET http://localhost:8000/websocket/test

# Check Socket.io endpoint
curl http://localhost:8000/ws/socket.io/

# Python test script
python test_websocket_connection.py

# HTML test page
open test_websocket_frontend.html
```

#### Configuration Checklist
- [ ] Frontend uses compatible Socket.io client version
- [ ] Backend python-socketio configured for v4 compatibility
- [ ] Reverse proxy forwards WebSocket headers
- [ ] CORS allows frontend origin
- [ ] Socket.io paths match between client/server
- [ ] Authentication configured (if required)
- [ ] Both websocket and polling transports enabled

### Frontend Deployment with Caddy
```caddy
# Caddyfile configuration for Clerk frontend
{$CLERK_HOSTNAME} {
    # Serve static files from the frontend build
    root * /srv/clerk-frontend
    
    # Enable gzip compression
    encode gzip
    
    # API proxy - forward API calls to backend
    handle /api/* {
        reverse_proxy clerk:8000
    }
    
    # WebSocket proxy
    handle /ws/* {
        reverse_proxy clerk:8000
    }
    
    # SPA support - serve index.html for all routes
    try_files {path} /index.html
    file_server
}

# Clerk Backend API (if needed separately)
{$CLERK_API_HOSTNAME} {
    reverse_proxy clerk:8000
}
```

The system uses Caddy as a reverse proxy instead of Nginx, providing:
- Automatic HTTPS with Let's Encrypt
- Simpler configuration syntax
- Built-in WebSocket support
- Automatic certificate renewal
- Zero-downtime reloads

Environment variables in `.env`:
```bash
CLERK_HOSTNAME=:8010        # For local development
CLERK_API_HOSTNAME=:8011    # Backend API direct access
```

---

## 📝 Documentation Maintenance Guidelines

### When to Update Documentation

**Every code change should trigger a documentation review:**

1. **Feature Addition** → Update:
   - CLAUDE.md: Add to architecture/components sections
   - tasks.md: Mark related tasks as completed
   - planning.md: Update if it affects roadmap

2. **Bug Fix** → Update:
   - tasks.md: Note in recent accomplishments
   - CLAUDE.md: Update troubleshooting if relevant

3. **Configuration Change** → Update:
   - CLAUDE.md: Environment variables, deployment sections
   - tasks.md: Note the change

4. **API Changes** → Update:
   - CLAUDE.md: API endpoints section
   - tasks.md: Mark API tasks as completed

5. **Dependency Updates** → Update:
   - CLAUDE.md: Technology stack section
   - requirements.txt or package.json as needed

### Documentation Update Checklist

Before committing any code changes, ask yourself:
- [ ] Does this change affect the architecture? → Update CLAUDE.md
- [ ] Does this complete or progress a task? → Update tasks.md
- [ ] Does this change our technical approach? → Update planning.md
- [ ] Would a new developer need to know about this? → Update CLAUDE.md
- [ ] Does this add technical debt? → Update planning.md

### Quick Reference

```bash
# Always update documentation in the same commit as code changes
git add CLAUDE.md tasks.md planning.md
git commit -m "feat: add WebSocket support + update docs"
```

Remember: **Outdated documentation is worse than no documentation!**
