# Clerk Legal AI System - Claude Context

## Project Overview

**Clerk** is a comprehensive legal AI system designed to revolutionize motion drafting and document management for law firms. The system automates document processing, provides intelligent search capabilities, and generates legal motion drafts using AI.

### Core Capabilities
- **Document Processing**: Automatically ingests PDF documents from Box cloud storage
- **Hybrid Search**: Combines vector similarity with full-text search for precise legal research
- **Motion Drafting**: AI-powered generation of legal motion outlines and complete drafts
- **Case Isolation**: Strict data separation ensuring case information never crosses between matters
- **Cost Tracking**: Detailed API usage monitoring and reporting
- **Workflow Automation**: n8n integration for automated document processing pipelines

## Architecture

### Technology Stack
- **Backend**: FastAPI (Python 3.11+)
- **Vector Database**: Qdrant with hybrid search capabilities
- **Document Storage**: Box API integration
- **AI Models**: OpenAI GPT models for context generation and drafting
- **Workflow Engine**: n8n for automation
- **Chat Interface**: Open WebUI (planned)
- **Embedding Model**: OpenAI text-embedding-3-small

### Key Components

#### Document Processing Pipeline
1. **Box Traversal**: Recursively scans Box folders for PDF documents
2. **Unified Document Management**: Combined deduplication and discovery system
   - SHA-256 hash-based duplicate detection
   - AI-powered document classification (motions, depositions, medical records, etc.)
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
- `/search` - Hybrid search across case documents
- `/generate-motion-outline` - Create motion outlines from opposing counsel's filings
- `/generate-motion-draft` - Full motion drafting capabilities

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

## Troubleshooting

### Common Issues

#### Box API Authentication
```python
# Test Box connection
from src.document_processing.box_client import BoxClient
client = BoxClient()
client.test_connection()
```
**Solutions:**
- Verify JWT credentials in .env
- Check Box app configuration
- Ensure service account has folder access
- Validate private key format (proper line breaks)

#### Qdrant Connection Issues
```python
# Test Qdrant connection
from src.vector_storage.qdrant_store import QdrantVectorStore
store = QdrantVectorStore()
store.test_connection()
```
**Solutions:**
- Verify QDRANT_HOST and QDRANT_API_KEY
- Check if collections are created
- Ensure pgvector extension is enabled
- Test network connectivity to Qdrant instance

#### OpenAI Rate Limits
**Symptoms**: 429 errors, slow processing
**Solutions:**
- Reduce batch sizes in document processing
- Implement exponential backoff (already in code)
- Upgrade OpenAI tier if needed
- Monitor cost tracking for usage patterns

#### Memory Issues with Large PDFs
**Symptoms**: Out of memory errors, slow processing
**Solutions:**
- Process fewer documents concurrently
- Increase system memory allocation
- Enable document size limits
- Monitor chunk processing statistics

#### Case Isolation Violations
**Critical Issue**: Never acceptable
**Detection**: Check logs for cross-case data leakage
**Prevention**: Always use case_name in metadata filters
**Testing**: Run isolation verification tests regularly

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

### Performance Monitoring
- **Document Processing**: ~10-15 seconds per document
- **Vector Search**: <100ms typical response time
- **Initial Import**: 4-6 hours for 4,000-6,000 documents
- **Storage Requirements**: ~2GB for 240,000 vectors

## External Integrations

### Box API
- **Authentication**: JWT-based service account
- **Permissions**: Read access to matter folders
- **Rate Limits**: Respect Box API limits
- **Folder Structure**: Mirrors firm's case organization

### n8n Workflows
- **Motion Processing**: Automated outline and draft generation
- **Document Monitoring**: Watches for new uploads
- **Status Updates**: Updates Google Sheets with progress
- **Error Handling**: Retries and notifications

### External Research APIs
- **Perplexity**: Deep legal research
- **Jina**: Document search and analysis
- **Integration Pattern**: Async processing with rate limiting

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
- **Docker**: containerized deployment available
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
- **Evidence Documents**: Medical Record, Police Report, Expert Report, Photos, Videos
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
- `STATEMENT_OF_FACTS`: Factual narrative with evidence citations
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