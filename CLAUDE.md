# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with the Clerk Legal AI System repository.

## Core Principles

**KISS (Keep It Simple, Stupid)**: Simplicity should be a key goal in design. Choose straightforward solutions over complex ones whenever possible. Simple solutions are easier to understand, maintain, and debug.

**YAGNI (You Aren't Gonna Need It)**: Avoid building functionality on speculation. Implement features only when they are needed, not when you anticipate they might be useful in the future.

**Dependency Inversion**: High-level modules should not depend on low-level modules. Both should depend on abstractions. This principle enables flexibility and testability.

**Open/Closed Principle**: Software entities should be open for extension but closed for modification. Design your systems so that new functionality can be added with minimal changes to existing code.

## 🧱 Code Structure & Modularity
- **Never create a file longer than 500 lines of code.** If a file approaches this limit, refactor by splitting it into modules or helper files.
- **Functions should be short and focused sub 50 lines of code** and have a single responsibility.
- **Classes should be short and focused sub 50 lines of code** and have a single responsibility.
- **Organize code into clearly separated modules**, grouped by feature or responsibility.

## Architecture

**Clerk** is a legal AI system for motion drafting and document management. It processes PDF documents, provides hybrid search capabilities, and generates legal motion drafts using AI.

Strict vertical slice architecture with tests that live next to the code they test:

```
Clerk/
    main.py                     # FastAPI application entry point
    src/
        document_injector.py            # Legacy document processing
        document_injector_unified.py    # Unified document processing
        
        ai_agents/                      # Legal AI agents module
            __init__.py
            motion_drafter.py
            case_researcher.py
            legal_document_agent.py
            fact_extractor.py
            evidence_discovery_agent.py
            tests/
                test_motion_drafter.py
                test_fact_extractor.py
                
        document_processing/            # PDF processing module
            __init__.py
            box_client.py
            chunker.py
            pdf_extractor.py
            unified_document_manager.py
            discovery_splitter.py
            tests/
                test_pdf_extractor.py
                test_chunker.py
                
        vector_storage/                 # Vector database module
            __init__.py
            qdrant_store.py
            embeddings.py
            tests/
                test_qdrant_store.py
                
        websocket/                      # Real-time updates module
            __init__.py
            socket_server.py
            tests/
                test_socket_server.py
                
        models/                         # Data models
            __init__.py
            unified_document_models.py
            motion_models.py
            case_models.py              # Case management models
            tests/
                test_models.py
                
        services/                       # Business logic services
            __init__.py
            case_manager.py             # Case CRUD operations
            tests/
                test_case_manager.py
                
        middleware/                     # FastAPI middleware
            __init__.py
            case_context.py             # Case validation middleware
            tests/
                test_case_context.py
                
        config/                         # Configuration modules
            __init__.py
            shared_resources.py         # Shared resource configuration
            tests/
                test_shared_resources.py
                
        utils/                          # Shared utilities
            __init__.py
            legal_formatter.py
            motion_cache_manager.py
            tests/
                test_utils.py
```

## Testing

**Always create Pytest unit tests for new features** (functions, classes, routes, etc)
Tests are always created in the same directory as the code they test in a tests/ directory. Create the tests directory if it doesn't exist.

**After updating any logic**, check whether existing unit tests need to be updated. If so, do it following the implementation.

Always test individual functions and classes.

## Style & Conventions

### 📎 Style & Conventions
- **Use Python** as the primary language (Python 3.11+).
- **Follow PEP8**, always use type hints, and format with `ruff`.
- **Use `pydanticv2` for data validation**.
- **ALWAYS use classes, data types, data models, for typesafety and verifiability**
- **ALWAYS use docstrings for every function** using the Google style:
  ```python
  def process_document(file_path: str, case_name: str) -> ProcessingResult:
      """
      Process a legal document for vector storage.

      Args:
          file_path (str): Path to the PDF document.
          case_name (str): Name of the legal case.

      Returns:
          ProcessingResult: Result of document processing.
          
      Raises:
          DocumentProcessingError: If document cannot be processed.
      """
  ```

## 🛠️ Environment Setup

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

# Supabase Configuration (for case management)
SUPABASE_URL=your_supabase_url
SUPABASE_ANON_KEY=your_supabase_anon_key
SUPABASE_SERVICE_ROLE_KEY=your_service_role_key  # Optional, for server-side operations

# Shared Resources Configuration
SHARED_COLLECTIONS=florida_statutes,fmcsr_regulations,federal_rules,case_law_precedents
ENABLE_CASE_ISOLATION=true
MAX_CASE_NAME_LENGTH=50

# Discovery Processing Configuration (NEW)
DISCOVERY_BOUNDARY_MODEL=gpt-4.1-mini       # AI model for document boundary detection
DISCOVERY_WINDOW_SIZE=5                     # Pages per analysis window
DISCOVERY_WINDOW_OVERLAP=1                  # Page overlap between windows
DISCOVERY_CONFIDENCE_THRESHOLD=0.7          # Minimum confidence for boundaries
DISCOVERY_CLASSIFICATION_MODEL=gpt-4.1-mini # Model for document classification
```

### Installation
```bash
cd /mnt/c/Webapps/local-ai/Clerk
pip install -r requirements.txt
```

## 🛠️ Development Commands

```bash
# Run all tests
python -m pytest

# Run specific tests
python -m pytest src/ai_agents/tests/test_motion_drafter.py -v

# Format code
ruff format .

# Run linter
ruff check .

# Start FastAPI server
python main.py

# Test document processing
python cli_injector_unified.py --folder-id 123456789 --max-documents 5

# Check WebSocket status
curl http://localhost:8000/websocket/status
```

## 🛠️ BRANCHING STRATEGY

This repository follows a develop → main branching strategy, where:

- `main` is the production branch containing stable releases
- `develop` is the integration branch where features are merged
- Feature branches are created from `develop` for work in progress

When creating branches, follow these naming conventions:

- Feature branches: `feature/descriptive-name`
- Bug fix branches: `fix/issue-description`
- Documentation branches: `docs/what-is-changing`
- Refactoring branches: `refactor/what-is-changing`

## Behavioural Guidelines

- Always use standard `pip` for package management.
- Always use `ruff` for linting and formatting.

- *** NEVER ASSUME OR GUESS ***
- When in doubt, ask for clarification or ask for help. You can do websearch to find relevant examples.

- *** CRITICAL: DOCKER CONTAINER MANAGEMENT ***
  - NEVER run Clerk containers with `docker run` directly
  - ALWAYS use docker-compose from the parent directory: `cd /mnt/c/Users/jlemr/Test2/local-ai-package`
  - ALWAYS use the correct docker-compose files: `docker-compose -p localai -f docker-compose.yml -f docker-compose.clerk.yml`
  - The Clerk service MUST run in the same network as qdrant and postgres (localai tech stack)
  - Database connection: `postgresql://postgres:${POSTGRES_PASSWORD}@postgres:5432/postgres` (NOT supabase-db!)
  - To restart Clerk: `docker-compose -p localai -f docker-compose.yml -f docker-compose.clerk.yml restart clerk`
  - To rebuild Clerk: `docker-compose -p localai -f docker-compose.yml -f docker-compose.clerk.yml build clerk`

- **Always confirm file paths & module names** exist before using them.

- **Comment non-obvious code** and ensure everything is understandable to a mid-level developer.
- When writing complex logic, **add an inline `# Reason:` comment** explaining the why, not just the what.

- **KEEP README.md UPDATED**
- Whenever you make changes to the codebase, update the README.md file to reflect the changes. Especially if you add configuration changes or new features.

- **ALWAYS keep CLAUDE.md UPDATED**
- Add new dependencies to CLAUDE.md
- Add important types and patterns to CLAUDE.md

## IMPORTANT TYPES & PATTERNS

### Case Management Pattern
Create and manage cases with proper validation and isolation:
```python
from src.services.case_manager import case_manager
from src.models.case_models import Case, CaseStatus

# Create a new case
case = await case_manager.create_case(
    name="Smith v Jones 2024",
    law_firm_id="firm-123",
    created_by="user-123"
)

# Validate case access
has_access = await case_manager.validate_case_access(
    case_id="case-123",
    user_id="user-123",
    required_permission="write"
)
```

### Case Context Middleware Pattern
All API requests automatically include case context:
```python
from src.middleware.case_context import get_case_context, require_case_context

@app.post("/api/search")
async def search(
    request: SearchRequest,
    case_context = Depends(get_case_context)  # Optional context
):
    # case_context contains case_id, case_name, permissions
    pass

@app.post("/api/documents")
async def create_document(
    request: DocumentRequest,
    case_context = Depends(require_case_context("write"))  # Required with permission
):
    # Automatically validates write permission
    pass
```

### Case Isolation Pattern
Every operation MUST be isolated by case to prevent data leakage:
```python
from src.models.unified_document_models import UnifiedDocument
from src.vector_storage.qdrant_store import QdrantVectorStore

# Always filter by case_name
async def search_case_documents(case_name: str, query: str) -> List[UnifiedDocument]:
    """Search documents within a specific case only."""
    store = QdrantVectorStore()
    return await store.hybrid_search(
        case_name=case_name,  # REQUIRED: Case isolation
        query_text=query,
        vector_weight=0.7,
        text_weight=0.3
    )
```

### Document Processing Pattern
Use the unified document management system:
```python
from src.document_injector_unified import UnifiedDocumentInjector
from src.models.unified_document_models import ProcessingResult

injector = UnifiedDocumentInjector(enable_cost_tracking=True)
result: ProcessingResult = await injector.process_case_folder(
    folder_id="123456789",
    case_name="Smith_v_Jones_2024"
)
```

### Discovery Processing Pattern (NEW)
Process multi-document discovery PDFs with AI-powered boundary detection:
```python
from src.document_processing.discovery_splitter import DiscoveryProductionProcessor

# Initialize with case name
processor = DiscoveryProductionProcessor(case_name="Smith_v_Jones_2024")

# Process discovery production
result = processor.process_discovery_production(
    pdf_path="/path/to/discovery.pdf",
    production_metadata={
        "production_batch": "PROD_001",
        "producing_party": "Opposing Counsel",
        "production_date": "2024-01-15",
        "responsive_to_requests": ["RFP_001", "RFP_005"],
        "confidentiality_designation": "Confidential"
    }
)

# Result contains:
# - segments_found: List of document segments with boundaries
# - average_confidence: Overall confidence in boundary detection
# - processing_windows: Number of AI analysis windows used
```

### WebSocket Event Pattern
Emit real-time updates during processing:
```python
from src.websocket.socket_server import sio

async def emit_processing_update(event_type: str, data: dict):
    """Emit WebSocket event for real-time updates."""
    await sio.emit(f'discovery:{event_type}', data)
```

### Shared Resources Pattern
Manage shared resources across all cases:
```python
from src.config.shared_resources import is_shared_resource, shared_resources

# Check if a collection is shared
if is_shared_resource("florida_statutes"):
    # This is a shared resource, available to all cases
    pass

# Filter out shared resources from case list
cases = vector_store.list_cases(include_shared=False)

# Add a new shared resource at runtime
shared_resources.add_shared_collection("new_shared_resource")
```

### Motion Drafting Pattern
Generate legal motions with structured outlines:
```python
from src.ai_agents.motion_drafter import MotionDrafter
from src.models.motion_models import MotionOutline, DraftedMotion

drafter = MotionDrafter()
motion: DraftedMotion = await drafter.draft_motion_from_outline(
    outline=outline,
    case_name="Smith_v_Jones_2024",
    motion_type="summary_judgment"
)
```

### API Endpoint Pattern
All endpoints must include proper error handling and validation:
```python
from fastapi import APIRouter, HTTPException
from pydantic import BaseModel

router = APIRouter()

class ProcessingRequest(BaseModel):
    folder_id: str
    case_name: str
    
@router.post("/process-folder")
async def process_folder(request: ProcessingRequest):
    """Process documents from Box folder."""
    try:
        # Implementation
        pass
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
```

### Critical Security Requirements
- **Case Isolation**: Every query MUST include case_name filter
- **API Security**: Never log API keys or sensitive data
- **Document Security**: Same document can exist in multiple cases without conflicts
- **WebSocket Security**: Events filtered by case_id subscription

### Key Dependencies
- FastAPI (backend framework)
- Qdrant (vector database)
- OpenAI (embeddings and LLM)
- Box SDK (document storage)
- Socket.io (real-time updates)
- pdfplumber/PyPDF2 (PDF processing)
- pytest (testing)
- ruff (linting)
- Supabase (case management and authentication)
- pydantic v2 (data validation)

### API Endpoints
- `/health` - System health checks
- `/api/cases` - GET: List user cases, POST: Create new case
- `/api/cases/{id}` - PUT: Update case status
- `/api/cases/{id}/permissions` - POST: Grant case permissions
- `/process-folder` - Process Box folder for documents
- `/discovery/process` - Process discovery with WebSocket updates
- `/search` - Hybrid search across case documents (requires X-Case-ID header)
- `/generate-motion-outline` - Create motion outlines
- `/generate-motion-draft` - Full motion drafting
- `/websocket/status` - WebSocket connection status
- `/ws/socket.io` - WebSocket endpoint for real-time updates