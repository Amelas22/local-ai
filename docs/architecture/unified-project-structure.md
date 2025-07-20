# Unified Project Structure

## Overview

The Clerk Legal AI System follows a vertical slice architecture with clear separation of concerns and co-located tests. This document outlines the complete project structure and organizational principles.

## Project Root Structure

```
local-ai-package/
├── Clerk/                          # Main application directory
│   ├── main.py                     # FastAPI application entry point
│   ├── requirements.txt            # Python dependencies
│   ├── Dockerfile                  # Container configuration
│   ├── .env.example               # Environment variable template
│   ├── CLAUDE.md                  # AI assistant guidelines
│   ├── README.md                  # Project documentation
│   └── src/                       # Source code directory
├── docker-compose.yml             # Main infrastructure compose
├── docker-compose.clerk.yml       # Clerk service compose overlay
├── docs/                          # Project documentation
│   ├── prd.md                     # Product Requirements Document
│   ├── architecture/              # Architecture documentation
│   └── stories/                   # User stories and epics
└── tests/                         # Integration test suites

```

## Source Code Organization

### Core Modules

```
src/
├── __init__.py
├── config/                        # Configuration and shared resources
│   ├── __init__.py
│   ├── shared_resources.py        # Shared collection management
│   └── tests/
│       └── test_shared_resources.py
│
├── models/                        # Data models and schemas
│   ├── __init__.py
│   ├── unified_document_models.py # Document processing models
│   ├── motion_models.py           # Motion drafting models
│   ├── case_models.py             # Case management models
│   ├── deficiency_models.py       # Deficiency analysis models
│   └── tests/
│       └── test_models.py
│
├── services/                      # Business logic layer
│   ├── __init__.py
│   ├── case_manager.py            # Case CRUD operations
│   ├── deficiency_service.py      # Deficiency analysis service
│   └── tests/
│       ├── test_case_manager.py
│       └── test_deficiency_service.py
│
├── middleware/                    # FastAPI middleware
│   ├── __init__.py
│   ├── case_context.py            # Case validation middleware
│   └── tests/
│       └── test_case_context.py
│
├── utils/                         # Shared utilities
│   ├── __init__.py
│   ├── legal_formatter.py         # Legal document formatting
│   ├── motion_cache_manager.py    # Motion caching utilities
│   └── tests/
│       └── test_utils.py
```

### Feature Modules

```
src/
├── ai_agents/                     # AI-powered agents
│   ├── __init__.py
│   ├── motion_drafter.py          # Motion generation
│   ├── case_researcher.py         # Case law research
│   ├── legal_document_agent.py    # Document analysis
│   ├── fact_extractor.py          # Fact extraction
│   ├── evidence_discovery_agent.py # Discovery analysis
│   ├── deficiency_analyzer.py     # Deficiency detection
│   ├── good_faith_letter_agent.py # Letter generation
│   └── tests/
│       ├── test_motion_drafter.py
│       ├── test_fact_extractor.py
│       ├── test_deficiency_analyzer.py
│       └── test_good_faith_letter_agent.py
│
├── document_processing/           # PDF and document handling
│   ├── __init__.py
│   ├── box_client.py              # Box API integration
│   ├── chunker.py                 # Document chunking
│   ├── pdf_extractor.py           # PDF text extraction
│   ├── unified_document_manager.py # Document lifecycle
│   ├── discovery_splitter.py      # Discovery boundary detection
│   └── tests/
│       ├── test_pdf_extractor.py
│       ├── test_chunker.py
│       └── test_discovery_splitter.py
│
├── vector_storage/                # Vector database operations
│   ├── __init__.py
│   ├── qdrant_store.py            # Qdrant integration
│   ├── embeddings.py              # Embedding generation
│   └── tests/
│       └── test_qdrant_store.py
│
├── websocket/                     # Real-time communications
│   ├── __init__.py
│   ├── socket_server.py           # Socket.io server
│   └── tests/
│       └── test_socket_server.py
```

### BMad Framework Integration

```
src/ai_agents/bmad-framework/      # BMad AI agent framework
├── __init__.py
├── agent_loader.py                # Agent definition loader
├── agent_executor.py              # Command execution engine
├── integration.py                 # Clerk system integration
├── security.py                    # Security and permissions
├── websocket_progress.py          # Progress tracking
├── exceptions.py                  # Framework exceptions
├── agents/                        # Agent definitions
│   ├── discovery-analyzer.yaml
│   └── bmad-master.yaml
├── tasks/                         # Task workflows
│   ├── analyze-rtp.md
│   └── create-next-story.md
├── templates/                     # Document templates
│   ├── motion-tmpl.yaml
│   └── deficiency-report-tmpl.yaml
└── checklists/                    # Validation checklists
    └── story-dod-checklist.md
```

### Legacy and Migration

```
src/
├── document_injector.py           # Legacy document processor
└── document_injector_unified.py   # Unified document processor
```

## Testing Structure

### Test Organization Principles

1. **Co-location**: Tests live next to the code they test in `tests/` subdirectories
2. **Naming**: Test files follow `test_*.py` pattern
3. **Structure**: Tests mirror the module structure they're testing
4. **Coverage**: Each module should have corresponding test coverage

### Test Categories

- **Unit Tests**: Test individual functions and classes in isolation
- **Integration Tests**: Test interactions between modules
- **E2E Tests**: Test complete user workflows
- **Performance Tests**: Test system performance under load

## Configuration Files

### Environment Configuration

```
.env.example                       # Template for environment variables
settings.py                        # Application settings management
```

### Docker Configuration

```
Dockerfile                         # Clerk service container
docker-compose.yml                 # Infrastructure services
docker-compose.clerk.yml          # Clerk service overlay
```

## Documentation Structure

```
docs/
├── prd.md                        # Product Requirements Document
├── architecture/                 # Architecture documentation
│   ├── tech-stack.md            # Technology stack
│   ├── unified-project-structure.md
│   ├── coding-standards.md      # Coding conventions
│   ├── testing-strategy.md      # Testing approach
│   ├── data-models.md           # Data model documentation
│   ├── database-schema.md       # Database structure
│   ├── backend-architecture.md  # Backend design
│   ├── rest-api-spec.md        # API specifications
│   ├── external-apis.md        # External integrations
│   ├── frontend-architecture.md # Frontend design
│   ├── components.md           # UI component library
│   └── core-workflows.md       # Business workflows
└── stories/                     # User stories
    ├── 1.1.story.md
    ├── 1.2.story.md
    └── ...
```

## Module Dependencies

### Dependency Flow

```
Frontend (React)
    ↓
API Layer (FastAPI)
    ↓
Middleware (Auth, Case Context)
    ↓
Services (Business Logic)
    ↓
Models (Data Structures)
    ↓
Infrastructure (Vector DB, PostgreSQL, External APIs)
```

### Import Conventions

1. **Absolute imports** from `src/` root
2. **No circular dependencies** between modules
3. **Clear dependency hierarchy** (high-level → low-level)
4. **Explicit exports** in `__init__.py` files

## File Naming Conventions

### Python Files
- **Modules**: `snake_case.py`
- **Classes**: `PascalCase` within files
- **Tests**: `test_*.py`
- **Constants**: `UPPER_SNAKE_CASE`

### Documentation Files
- **Markdown**: `kebab-case.md`
- **YAML**: `kebab-case.yaml` or `kebab-case.yml`

## Best Practices

### Module Size Limits
- **Files**: Maximum 500 lines
- **Functions**: Maximum 50 lines
- **Classes**: Single responsibility principle

### Code Organization
- **Vertical slices**: Feature-based organization
- **Co-located tests**: Tests next to implementation
- **Clear boundaries**: Well-defined module interfaces
- **Dependency injection**: For testability

### Documentation Requirements
- **Docstrings**: Google style for all public functions
- **Type hints**: Required for all function signatures
- **Comments**: Explain "why", not "what"
- **README**: Keep updated with changes

## Security Considerations

### Case Isolation
- All operations must include `case_name` parameter
- No cross-case data access
- Proper permission validation

### Sensitive Data
- Never log API keys or secrets
- Use environment variables for configuration
- Implement proper access controls

## Deployment Structure

### Container Organization
- Clerk runs as part of the localai stack
- Shares network with qdrant and postgres
- Uses docker-compose overlays for configuration

### Service Dependencies
- PostgreSQL for case management
- Qdrant for vector storage
- OpenAI API for embeddings and LLM
- Box API for document storage