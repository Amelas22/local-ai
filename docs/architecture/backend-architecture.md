# Backend Architecture

## Overview

The Clerk Legal AI System backend is built with FastAPI following a layered architecture pattern with clear separation of concerns. The system emphasizes modularity, testability, and scalability while maintaining strict case isolation for security.

## Architecture Principles

### Core Design Principles
- **Vertical Slice Architecture**: Features organized by domain
- **Dependency Inversion**: High-level modules independent of low-level details
- **Single Responsibility**: Each module has one reason to change
- **Case Isolation**: Every operation scoped to a specific case
- **Async-First**: Leverage Python's async/await for I/O operations

### Technical Principles
- **KISS**: Keep implementations simple and straightforward
- **YAGNI**: Build only what's needed now
- **DRY**: Avoid duplication through proper abstraction
- **Type Safety**: Full type hints and Pydantic validation

## System Architecture Layers

```
┌─────────────────────────────────────────┐
│          API Layer (FastAPI)            │
├─────────────────────────────────────────┤
│      Middleware (Auth, Context)         │
├─────────────────────────────────────────┤
│    Service Layer (Business Logic)       │
├─────────────────────────────────────────┤
│       Domain Models (Pydantic)          │
├─────────────────────────────────────────┤
│  Infrastructure (DB, APIs, Storage)     │
└─────────────────────────────────────────┘
```

## Component Architecture

### API Layer
The API layer handles HTTP requests and responses using FastAPI:

```python
# main.py structure
app = FastAPI(
    title="Clerk Legal AI System",
    version="1.0.0",
    docs_url="/api/docs"
)

# Middleware registration
app.add_middleware(CaseContextMiddleware)
app.add_middleware(CORSMiddleware, ...)

# Router registration
app.include_router(cases_router, prefix="/api/cases")
app.include_router(discovery_router, prefix="/api/discovery")
app.include_router(motions_router, prefix="/api/motions")
```

### Middleware Layer
Custom middleware for cross-cutting concerns:

#### Case Context Middleware
```python
class CaseContextMiddleware:
    """Extracts and validates case context from requests"""
    async def __call__(self, request: Request, call_next):
        case_id = request.headers.get("X-Case-ID")
        if case_id:
            # Validate case access
            case_context = await validate_case_access(case_id, user_id)
            request.state.case_context = case_context
        return await call_next(request)
```

#### Authentication Middleware
- JWT token validation
- User context injection
- Permission verification

### Service Layer
Business logic implementation with clear interfaces:

```python
class CaseManager:
    """Manages case lifecycle and permissions"""
    
    async def create_case(
        self,
        name: str,
        law_firm_id: UUID,
        created_by: UUID
    ) -> Case:
        # Validate case name uniqueness
        # Create case record
        # Initialize vector collection
        # Grant creator permissions
        
class DeficiencyService:
    """Handles deficiency analysis workflow"""
    
    async def analyze_production(
        self,
        production_id: UUID,
        case_name: str
    ) -> DeficiencyReport:
        # Load RTP and OC response
        # Perform AI analysis
        # Generate report
        # Store results
```

### Domain Models
Pydantic models for data validation and serialization:

```python
class Case(BaseModel):
    id: UUID
    name: str = Field(..., max_length=50)
    law_firm_id: UUID
    status: CaseStatus
    created_at: datetime
    metadata: Dict[str, Any] = {}
    
    class Config:
        orm_mode = True
```

### Infrastructure Layer
External system integrations:

#### Database Access
```python
class DatabaseSession:
    """Manages PostgreSQL connections"""
    
    @asynccontextmanager
    async def get_session(self):
        async with self.async_session() as session:
            yield session
```

#### Vector Storage
```python
class QdrantVectorStore:
    """Manages vector database operations"""
    
    async def store_embeddings(
        self,
        case_name: str,
        documents: List[Document]
    ) -> None:
        # Generate embeddings
        # Store in case collection
        # Update indexes
```

## Async Architecture

### Async Patterns
```python
# Concurrent operations
async def process_discovery_batch(
    documents: List[Document],
    case_name: str
) -> ProcessingResult:
    # Process documents concurrently
    tasks = [
        process_document(doc, case_name)
        for doc in documents
    ]
    results = await asyncio.gather(*tasks)
    return ProcessingResult(results=results)
```

### Background Tasks
```python
# FastAPI background tasks
@app.post("/api/discovery/process")
async def process_discovery(
    request: ProcessingRequest,
    background_tasks: BackgroundTasks
):
    # Queue for background processing
    background_tasks.add_task(
        process_discovery_production,
        request.production_id,
        request.case_name
    )
    return {"status": "processing"}
```

## WebSocket Architecture

### Real-time Updates
```python
# Socket.io integration
sio = socketio.AsyncServer(
    async_mode='asgi',
    cors_allowed_origins="*"
)

@sio.event
async def connect(sid, environ):
    # Validate connection
    # Subscribe to case events
    
@sio.event
async def discovery_progress(sid, data):
    # Emit progress to subscribers
    await sio.emit(
        'discovery:progress',
        data,
        room=f"case:{data['case_id']}"
    )
```

### Event Types
- `discovery:started` - Processing begins
- `discovery:progress` - Status updates
- `discovery:completed` - Processing done
- `deficiency:analysis_progress` - Analysis updates
- `motion:draft_progress` - Motion generation

## AI Agent Architecture

### Agent Design Pattern
```python
class BaseAgent(ABC):
    """Base class for all AI agents"""
    
    @abstractmethod
    async def process(
        self,
        input_data: Any,
        case_context: CaseContext
    ) -> Any:
        pass
        
class DeficiencyAnalyzer(BaseAgent):
    """Analyzes discovery deficiencies"""
    
    async def process(
        self,
        rtp_items: List[RTPItem],
        case_context: CaseContext
    ) -> DeficiencyReport:
        # Implement analysis logic
```

### Agent Capabilities
- **Motion Drafter**: Generates legal motions
- **Fact Extractor**: Extracts facts from documents
- **Deficiency Analyzer**: Compares RTP with productions
- **Letter Generator**: Creates Good Faith letters

## Error Handling

### Exception Hierarchy
```python
class ClerkException(Exception):
    """Base exception for all Clerk errors"""
    
class CaseNotFoundException(ClerkException):
    """Case does not exist"""
    
class PermissionDeniedException(ClerkException):
    """User lacks required permissions"""
    
class ProcessingException(ClerkException):
    """Document processing failed"""
```

### Error Response Format
```python
class ErrorResponse(BaseModel):
    error: str
    message: str
    details: Optional[Dict[str, Any]]
    timestamp: datetime
    request_id: str
```

## Security Architecture

### Authentication Flow
1. User provides JWT token
2. Middleware validates token
3. User context extracted
4. Permissions checked per endpoint

### Case Isolation
```python
def enforce_case_isolation(case_name: str):
    """Decorator to ensure case isolation"""
    def decorator(func):
        @wraps(func)
        async def wrapper(*args, **kwargs):
            # Verify case_name in kwargs
            # Check user has case access
            return await func(*args, **kwargs)
        return wrapper
    return decorator
```

### API Security
- Rate limiting per user/endpoint
- Input validation via Pydantic
- SQL injection prevention
- XSS protection in responses

## Performance Optimization

### Caching Strategy
```python
class MotionCache:
    """Caches generated motion content"""
    
    async def get_or_generate(
        self,
        cache_key: str,
        generator_func: Callable
    ) -> str:
        # Check cache first
        # Generate if miss
        # Store in cache
```

### Database Optimization
- Connection pooling
- Prepared statements
- Batch operations
- Proper indexing

### Vector Search Optimization
- Hybrid search (semantic + keyword)
- Reranking with Cohere
- Chunking strategies
- Metadata filtering

## Testing Architecture

### Test Categories
```python
# Unit tests
async def test_case_creation():
    """Test case creation logic"""
    
# Integration tests  
async def test_discovery_pipeline():
    """Test full discovery workflow"""
    
# E2E tests
async def test_motion_generation_flow():
    """Test complete motion generation"""
```

### Test Fixtures
```python
@pytest.fixture
async def test_case():
    """Provides test case context"""
    
@pytest.fixture
async def mock_openai():
    """Mocks OpenAI API calls"""
```

## Monitoring and Observability

### Logging Strategy
```python
import logging

logger = logging.getLogger("clerk_api")

# Structured logging
logger.info(
    "Discovery processing started",
    extra={
        "case_id": case_id,
        "document_count": len(documents),
        "user_id": user_id
    }
)
```

### Metrics Collection
- Request latency
- AI token usage
- Error rates
- WebSocket connections
- Database query times

### Cost Tracking
```python
class CostTracker:
    """Tracks AI and API usage costs"""
    
    async def track_openai_usage(
        self,
        tokens: int,
        model: str,
        operation: str
    ):
        # Calculate cost
        # Store in database
        # Update dashboards
```

## Deployment Architecture

### Container Structure
```dockerfile
FROM python:3.11-slim

# Install dependencies
COPY requirements.txt .
RUN pip install -r requirements.txt

# Copy application
COPY . /app
WORKDIR /app

# Run with uvicorn
CMD ["uvicorn", "main:app", "--host", "0.0.0.0", "--port", "8000"]
```

### Environment Configuration
```python
class Settings(BaseSettings):
    # Database
    postgres_url: str
    
    # Vector DB
    qdrant_host: str
    qdrant_port: int
    
    # APIs
    openai_api_key: SecretStr
    box_client_id: str
    
    # Features
    enable_deficiency_analysis: bool = False
    
    class Config:
        env_file = ".env"
```

## Scalability Considerations

### Horizontal Scaling
- Stateless API design
- Session affinity for WebSockets
- Distributed task queue ready
- Database connection pooling

### Vertical Scaling
- Async I/O for concurrency
- Efficient memory usage
- Streaming for large files
- Lazy loading of data

## Future Architecture Considerations

### Potential Enhancements
- GraphQL API layer
- Event sourcing for audit
- CQRS for read/write split
- Microservices extraction
- Kubernetes deployment

### Technology Upgrades
- Python 3.12 features
- FastAPI 1.0 migration
- Pydantic v3 when stable
- Alternative vector DBs
- Multi-region deployment