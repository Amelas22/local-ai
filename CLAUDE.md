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
2. **Duplicate Detection**: SHA-256 hash-based deduplication
3. **Text Extraction**: Multi-library PDF processing (pdfplumber, PyPDF2, pdfminer)
4. **Chunking**: ~1400 character chunks with 200 character overlap
5. **Context Generation**: LLM-powered contextual summaries for each chunk
6. **Vector Storage**: Embeddings stored in Qdrant with case metadata

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
│   ├── document_injector.py      # Core document processing
│   ├── ai_agents/                # Legal AI agents
│   │   ├── motion_drafter.py     # Motion drafting logic
│   │   ├── case_researcher.py    # Case research agent
│   │   └── legal_document_agent.py
│   ├── document_processing/      # PDF processing utilities
│   │   ├── box_client.py         # Box API integration
│   │   ├── chunker.py            # Document chunking
│   │   └── pdf_extractor.py      # PDF text extraction
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

# Test document injection
python -m src.document_injector --folder-id 123456789
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
- **Metadata Filtering**: Every query MUST include case_name filter
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

## Next Steps for Development

1. **Complete n8n Integration**: Finish workflow automation
2. **Implement Open WebUI**: Replace Google Sheets interface
3. **Add Deadline Tracking**: Calendar integration and notifications
4. **Enhance Motion Drafting**: Improve AI agents and templates
5. **Optimize Performance**: Caching and query optimization
6. **Implement Monitoring**: Comprehensive system monitoring