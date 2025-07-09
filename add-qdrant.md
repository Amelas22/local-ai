## FEATURE:

**Automatic Qdrant Collection Creation on Case Creation**

When someone clicks create case on the clerk frontend, the case is added to the SQL database but the vector storage collections are not created. This feature will automatically create the case-specific Qdrant collections immediately after a new case is created in the database.

### Current State:
- Case creation generates a `collection_name` using MD5 hash of `law_firm_id + case_name`
- The `collection_name` is stored in the database but no Qdrant collections are created
- Collections are only created when documents are first uploaded to a case

### Desired State:
- Upon successful case creation, automatically create all required Qdrant collections
- Emit WebSocket events to notify frontend of collection creation progress
- Ensure collections are ready for immediate document upload

### Qdrant Collections Structure:
```
Qdrant Collections:
├── Shared Resources (Available to all cases)
│   ├── florida_statutes          # Florida state laws
│   ├── fmcsr_regulations        # Federal Motor Carrier Safety Regulations  
│   ├── federal_rules            # Federal rules and procedures
│   └── case_law_precedents      # Legal precedents database
│
└── Case-Specific (Isolated per matter)
    ├── {collection_name}               # Main case database for RAG search
    ├── {collection_name}_facts         # Extracted facts with embeddings
    ├── {collection_name}_timeline      # Chronological events
    └── {collection_name}_depositions   # Deposition citations
```

Note: `{collection_name}` is the sanitized, hashed collection name (e.g., "firm123_smith_v_jones_2024_a1b2c3")

### Implementation Approach:

1. **Modify `create_case` endpoint** in `/Clerk/src/api/case_endpoints.py`:
   - After successful case creation in database
   - Initialize QdrantVectorStore instance
   - Create collections asynchronously
   - Emit WebSocket progress events

2. **Add new method** to `/Clerk/src/vector_storage/qdrant_store.py`:
   ```python
   async def create_case_collections(self, collection_name: str) -> Dict[str, bool]:
       """Create all collections for a new case"""
       collections = {
           collection_name: "Main case documents",
           f"{collection_name}_facts": "Extracted facts",
           f"{collection_name}_timeline": "Chronological events",
           f"{collection_name}_depositions": "Deposition citations"
       }
       # Create each collection and track success
   ```

3. **WebSocket Integration**:
   - Emit events as each collection is created
   - Send completion event when all collections are ready
   - Handle errors gracefully with error events

4. **Testing**:
   - Unit tests with mocked Qdrant client
   - Integration tests with real Qdrant instance
   - Test rollback on failure scenarios

## EXAMPLES:

### Key Files and Code Examples:

#### 1. **Collection Name Generation** (`/Clerk/src/services/case_service.py`):
```python
@staticmethod
def generate_collection_name(case_name: str, law_firm_id: str) -> str:
    """Convert case name to a valid Qdrant collection name."""
    # Sanitize case name - remove special characters, convert to lowercase
    sanitized = ''.join(c if c.isalnum() or c in '_- ' else '_' for c in case_name.lower())
    sanitized = sanitized.replace(' ', '_').replace('-', '_')
    
    # Create hash for uniqueness
    hash_input = f"{law_firm_id}_{sanitized}"
    hash_suffix = hashlib.md5(hash_input.encode()).hexdigest()[:8]
    
    # Combine parts with length limit (Qdrant max is 63 chars)
    collection_name = f"{sanitized[:40]}_{hash_suffix}"
    return collection_name
```

#### 2. **Current Case Creation Flow** (`/Clerk/src/api/case_endpoints.py`):
```python
@router.post("", response_model=Case)
async def create_case(request: CaseCreateRequest, ...):
    # Creates case in database
    case = await CaseService.create_case(...)
    # TODO: Add Qdrant collection creation here
    return case
```

#### 3. **Qdrant Collection Creation** (`/Clerk/src/vector_storage/qdrant_store.py`):
```python
def ensure_collection_exists(self, folder_name: str, use_case_manager: bool = True):
    """Ensure collection exists for a specific folder/case"""
    collection_name = self.get_collection_name(folder_name)
    
    if not self.client.collection_exists(collection_name):
        self.create_collection(collection_name)
        
def _create_hybrid_collection(self, collection_name: str):
    """Create hybrid collection with multiple vector types"""
    self.client.create_collection(
        collection_name=collection_name,
        vectors_config={
            "dense": VectorParams(
                size=settings.vector.embedding_dimensions,
                distance=Distance.COSINE
            ),
            "sparse": SparseVectorParams(
                index=SparseIndexParams(on_disk=False)
            )
        },
        # ... additional config
    )
```

#### 4. **WebSocket Events** (`/Clerk/src/websocket/socket_server.py`):
```python
async def emit_case_event(event_type: str, case_id: str, data: dict):
    """Emit case-related events"""
    await sio.emit(f'case:{event_type}', {
        'case_id': case_id,
        'data': data
    })
```

#### 5. **Case Context Tracking** (`/Clerk/src/middleware/case_context.py`):
```python
@dataclass
class CaseContext:
    """Context for case-specific operations"""
    case_id: str
    case_name: str
    collection_name: str
    law_firm_id: str
    permissions: List[str]
```

### Integration Points:

1. **After Case Creation in `case_endpoints.py`**:
   - Initialize QdrantVectorStore
   - Create main collection and specialized collections
   - Emit WebSocket events for progress

2. **Collection Naming Convention**:
   - Main: `{collection_name}`
   - Facts: `{collection_name}_facts`
   - Timeline: `{collection_name}_timeline`
   - Depositions: `{collection_name}_depositions`

3. **Error Handling**:
   - Rollback case creation if Qdrant fails
   - Log collection creation failures
   - Notify frontend of any errors

## DOCUMENTATION:

### Qdrant Documentation:
- **url**: https://qdrant.tech/documentation/concepts/collections/
- **why**: Understanding collection creation, configuration, and management

- **url**: https://qdrant.tech/documentation/concepts/indexing/
- **why**: Hybrid search configuration with dense and sparse vectors

- **url**: https://qdrant.tech/documentation/concepts/payload/
- **why**: Payload indexing for case metadata and filtering

### Python Libraries:
- **url**: https://python-socketio.readthedocs.io/en/stable/server.html#emitting-events
- **why**: WebSocket event emission for real-time updates during collection creation

- **url**: https://docs.sqlalchemy.org/en/20/orm/session_transaction.html
- **why**: Transaction handling for atomic case + collection creation

### Project Files:
- **file**: `/Clerk/src/vector_storage/qdrant_store.py`
- **why**: Core Qdrant integration - collection creation methods

- **file**: `/Clerk/src/api/case_endpoints.py`
- **why**: Case creation endpoint that needs modification

- **file**: `/Clerk/src/services/case_service.py`
- **why**: Case service logic and collection name generation

- **file**: `/Clerk/src/config/settings.py`
- **why**: Qdrant configuration settings (embedding dimensions, hybrid search flags)

- **file**: `/Clerk/src/websocket/socket_server.py`
- **why**: WebSocket server for emitting progress events

- **file**: `CLAUDE.md`
- **why**: Project structure, testing requirements, and coding standards

- **file**: `docker-compose.yml` and `docker-compose.override.yml`
- **why**: Qdrant service configuration and connection details

### MCP Servers:
- **mcp**: Context7 MCP Server
- **why**: Look up Qdrant Python client documentation and best practices

- **mcp**: Brave-search MCP Server
- **why**: Search for Qdrant collection creation patterns and error handling

### Testing & Development:
- **file**: `start_services_with_postgres.py`
- **why**: Launch full tech stack with `--profile cpu` for testing

- **file**: `/Clerk/src/api/tests/test_case_endpoints.py`
- **why**: Existing case endpoint tests that need updating

## OTHER CONSIDERATIONS:

### Important Implementation Details:

1. **Collection Name Constraints**:
   - Qdrant collection names must be 1-63 characters
   - Only alphanumeric, underscore, and hyphen allowed
   - The `generate_collection_name` already handles this, but specialized collections need the same treatment

2. **Async/Await Consistency**:
   - Case creation endpoint is async
   - QdrantVectorStore has both sync and async clients
   - Use async client for better performance in async endpoints

3. **Transaction Management**:
   - Case creation should be atomic with collection creation
   - If Qdrant fails, rollback the database transaction
   - Consider using SQLAlchemy's `async with` context manager

4. **Environment-Specific Settings**:
   - Check `settings.legal.enable_hybrid_search` to determine collection type
   - Use `settings.vector.embedding_dimensions` for vector size (1536 for OpenAI)
   - Respect `settings.qdrant` configuration for connection details

5. **Case Isolation**:
   - Each case must have completely isolated collections
   - Never mix data between cases (legal requirement)
   - The collection name includes law_firm_id hash for additional isolation

6. **WebSocket Events**:
   - Frontend expects specific event format: `case:collection_created`
   - Include progress updates for each collection type
   - Send final `case:ready` event when all collections are created

7. **Error Scenarios**:
   - Qdrant service might be down
   - Collection might already exist (handle gracefully)
   - Network timeouts during collection creation
   - Insufficient Qdrant resources/quota

8. **Testing Requirements**:
   - Always create tests in the same directory as the code (`tests/` subdirectory)
   - Test both success and failure scenarios
   - Mock Qdrant client for unit tests
   - Integration tests should use real Qdrant instance

9. **Startup Script Compatibility**:
   - Ensure changes work with: `python start_services_with_postgres.py --profile cpu`
   - Qdrant service must be running before Clerk starts
   - Check docker-compose dependencies

10. **Specialized Collections**:
    - `_facts`, `_timeline`, `_depositions` are suffixes, not prefixes
    - Each specialized collection needs appropriate vector configuration
    - Consider different embedding models for different collection types

11. **Performance Considerations**:
    - Collection creation is relatively slow (~100-500ms per collection)
    - Consider background task for collection creation
    - Don't block the API response waiting for all collections

12. **Future Extensibility**:
    - Design for easy addition of new collection types
    - Consider configuration-driven collection definitions
    - Allow for different vector dimensions per collection type


