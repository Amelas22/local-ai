# PRP: Automatic Qdrant Collection Creation on Case Creation

## Overview
This PRP details the implementation of automatic Qdrant collection creation when a new case is created in the Clerk legal AI system. Currently, cases are created in PostgreSQL but vector storage collections are only created when documents are first uploaded. This feature will create all required collections immediately after case creation.

## Context and Background

### Current State
- Case creation generates a `collection_name` using MD5 hash of `law_firm_id + case_name`
- Collection name is stored in the database but no Qdrant collections are created
- Collections are lazily created when documents are first uploaded

### Desired State
- Upon successful case creation, automatically create 4 Qdrant collections
- Emit WebSocket events to notify frontend of progress
- Ensure collections are ready for immediate document upload
- Handle errors gracefully without blocking case creation

### Collection Structure
```
{collection_name}               # Main case database for RAG search
{collection_name}_facts         # Extracted facts with embeddings
{collection_name}_timeline      # Chronological events
{collection_name}_depositions   # Deposition citations
```

## Implementation Blueprint

### Pseudocode Overview
```python
# In case_endpoints.py create_case()
async def create_case():
    # 1. Create case in database (existing)
    case = await CaseService.create_case(...)
    
    # 2. Create Qdrant collections (new)
    try:
        vector_store = QdrantVectorStore()
        await create_case_collections_with_events(
            vector_store, 
            case.collection_name,
            case.id
        )
    except Exception as e:
        # Log error but don't fail case creation
        logger.error(f"Failed to create Qdrant collections: {e}")
        await emit_case_event("collection_error", case.id, {"error": str(e)})
    
    # 3. Return case (existing)
    return case
```

### Detailed Implementation Steps

#### 1. Add Async Collection Creation Method to QdrantVectorStore
**File**: `/Clerk/src/vector_storage/qdrant_store.py`

```python
async def create_case_collections(self, collection_name: str) -> Dict[str, bool]:
    """
    Create all collections for a new case.
    
    Args:
        collection_name: Base collection name for the case
        
    Returns:
        Dict mapping collection name to creation success status
    """
    collections = [
        (collection_name, "Main case documents"),
        (f"{collection_name}_facts", "Extracted facts"),
        (f"{collection_name}_timeline", "Chronological events"),
        (f"{collection_name}_depositions", "Deposition citations")
    ]
    
    results = {}
    
    for coll_name, description in collections:
        try:
            # Check length constraint (max 63 chars)
            if len(coll_name) > 63:
                # Truncate intelligently
                suffix_len = len(coll_name.split('_')[-1])
                base_max_len = 62 - suffix_len - 1
                base = coll_name[:base_max_len]
                suffix = coll_name.split('_')[-1]
                coll_name = f"{base}_{suffix}"
            
            # Check if exists
            exists = await self.async_client.collection_exists(coll_name)
            if not exists:
                # Create based on settings
                if settings.legal.enable_hybrid_search:
                    await self._create_hybrid_collection_async(coll_name)
                else:
                    await self._create_standard_collection_async(coll_name)
                
                # Verify creation
                exists = await self.async_client.collection_exists(coll_name)
                results[coll_name] = exists
            else:
                results[coll_name] = True  # Already exists
                
        except Exception as e:
            logger.error(f"Failed to create collection {coll_name}: {e}")
            results[coll_name] = False
    
    return results
```

#### 2. Add Async Collection Creation Methods
**File**: `/Clerk/src/vector_storage/qdrant_store.py`

```python
async def _create_standard_collection_async(self, collection_name: str):
    """Async version of standard collection creation"""
    quantization_config = None
    if hasattr(settings.vector, 'quantization') and settings.vector.quantization:
        quantization_config = ScalarQuantization(
            scalar=ScalarQuantizationConfig(
                type=ScalarType.INT8,
                quantile=0.99,
                always_ram=True
            )
        )
    
    await self.async_client.create_collection(
        collection_name=collection_name,
        vectors_config=VectorParams(
            size=settings.vector.embedding_dimensions,
            distance=Distance.COSINE
        ),
        hnsw_config=HnswConfigDiff(
            m=settings.vector.hnsw_m,
            ef_construct=settings.vector.hnsw_ef_construct,
            on_disk=False,
            max_indexing_threads=8
        ),
        quantization_config=quantization_config,
        on_disk_payload=False
    )
    await self._create_payload_indexes_async(collection_name)

async def _create_hybrid_collection_async(self, collection_name: str):
    """Async version of hybrid collection creation"""
    # Similar to sync version but using async_client
    await self.async_client.create_collection(
        collection_name=collection_name,
        vectors_config={
            "semantic": VectorParams(
                size=settings.vector.embedding_dimensions,
                distance=Distance.COSINE,
                hnsw_config=HnswConfigDiff(
                    m=settings.vector.hnsw_m,
                    ef_construct=settings.vector.hnsw_ef_construct
                ),
                quantization_config=ScalarQuantization(
                    scalar=ScalarQuantizationConfig(
                        type=ScalarType.INT8,
                        quantile=0.99,
                        always_ram=True
                    )
                ) if settings.vector.quantization else None
            ),
            "legal_concepts": VectorParams(
                size=settings.vector.legal_embedding_dimensions,
                distance=Distance.COSINE
            )
        },
        sparse_vectors_config={
            "keywords": SparseVectorParams(
                index=SparseIndexParams(
                    on_disk=False
                )
            ),
            "citations": SparseVectorParams(
                index=SparseIndexParams(
                    on_disk=False
                )
            )
        },
        on_disk_payload=False
    )
    await self._create_payload_indexes_async(collection_name)

async def _create_payload_indexes_async(self, collection_name: str):
    """Async version of payload index creation"""
    indexes = [
        ("case_name", "keyword"),
        ("document_id", "keyword"),
        ("document_type", "keyword"),
        ("chunk_index", "integer"),
        ("page_number", "integer"),
        ("sentence_count", "integer"),
        ("has_citations", "bool"),
        ("citation_density", "float"),
        ("created_at", "datetime")
    ]
    
    for field_name, field_type in indexes:
        try:
            await self.async_client.create_payload_index(
                collection_name=collection_name,
                field_name=field_name,
                field_type=field_type
            )
        except Exception as e:
            logger.warning(f"Failed to create index {field_name}: {e}")
```

#### 3. Add WebSocket Event Emission Helper
**File**: `/Clerk/src/websocket/socket_server.py`

```python
async def emit_case_event(event_type: str, case_id: str, data: dict):
    """
    Emit case-related events.
    
    Args:
        event_type: Type of event (e.g., 'collection_created', 'collection_error')
        case_id: ID of the case
        data: Event data payload
    """
    event_data = {
        'caseId': case_id,
        'eventType': event_type,
        'timestamp': datetime.utcnow().isoformat(),
        **data
    }
    
    await sio.emit(f'case:{event_type}', event_data)
    logger.info(f"Emitted case event: case:{event_type} for case {case_id}")
```

#### 4. Create Helper Function for Collection Creation with Events
**File**: `/Clerk/src/api/case_endpoints.py`

```python
async def create_case_collections_with_events(
    vector_store: QdrantVectorStore,
    collection_name: str,
    case_id: str
) -> bool:
    """
    Create Qdrant collections for a case with WebSocket progress events.
    
    Args:
        vector_store: QdrantVectorStore instance
        collection_name: Base collection name
        case_id: Case ID for event emission
        
    Returns:
        True if all collections created successfully
    """
    from src.websocket.socket_server import emit_case_event
    
    # Emit start event
    await emit_case_event("collections_started", case_id, {
        "totalCollections": 4,
        "message": "Creating vector storage collections"
    })
    
    # Create collections
    results = await vector_store.create_case_collections(collection_name)
    
    # Emit progress for each collection
    success_count = 0
    for idx, (coll_name, success) in enumerate(results.items()):
        collection_type = "main"
        if "_facts" in coll_name:
            collection_type = "facts"
        elif "_timeline" in coll_name:
            collection_type = "timeline"
        elif "_depositions" in coll_name:
            collection_type = "depositions"
            
        if success:
            success_count += 1
            await emit_case_event("collection_created", case_id, {
                "collectionName": coll_name,
                "collectionType": collection_type,
                "progress": (idx + 1) / 4
            })
        else:
            await emit_case_event("collection_failed", case_id, {
                "collectionName": coll_name,
                "collectionType": collection_type,
                "error": "Failed to create collection"
            })
    
    # Emit completion event
    if success_count == 4:
        await emit_case_event("collections_ready", case_id, {
            "message": "All collections created successfully",
            "collectionsCreated": success_count
        })
        return True
    else:
        await emit_case_event("collections_partial", case_id, {
            "message": f"Created {success_count} of 4 collections",
            "collectionsCreated": success_count,
            "collectionsFailed": 4 - success_count
        })
        return False
```

#### 5. Modify Case Creation Endpoint
**File**: `/Clerk/src/api/case_endpoints.py`

```python
# Add import at top
from src.vector_storage.qdrant_store import QdrantVectorStore

# Modify create_case endpoint
@router.post("", response_model=Case)
async def create_case(
    request: CaseCreateRequest,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
) -> Case:
    """
    Create a new case with automatic Qdrant collection creation.
    """
    try:
        # Create case in database (existing code)
        law_firm_id = current_user.law_firm_id
        
        case = await CaseService.create_case(
            db=db,
            name=request.name,
            law_firm_id=law_firm_id,
            created_by=current_user.id,
            description=None,
            metadata=request.metadata
        )
        
        # Create Qdrant collections asynchronously (new code)
        try:
            vector_store = QdrantVectorStore()
            collections_created = await create_case_collections_with_events(
                vector_store,
                case.collection_name,
                case.id
            )
            
            if not collections_created:
                logger.warning(
                    f"Some collections failed to create for case {case.id}"
                )
                
        except Exception as e:
            # Log error but don't fail case creation
            logger.error(
                f"Failed to create Qdrant collections for case {case.id}: {e}"
            )
            # Emit error event
            try:
                from src.websocket.socket_server import emit_case_event
                await emit_case_event("collection_error", case.id, {
                    "error": str(e),
                    "message": "Collections will be created when first document is uploaded"
                })
            except:
                pass  # Don't fail on WebSocket error
        
        # Parse metadata and return (existing code)
        metadata = {}
        if case.case_metadata:
            try:
                import json
                metadata = json.loads(case.case_metadata)
            except:
                pass
        
        return Case(
            id=case.id,
            name=case.name,
            collection_name=case.collection_name,
            description=case.description,
            law_firm_id=case.law_firm_id,
            status=case.status,
            created_by=case.created_by,
            metadata=metadata,
            created_at=case.created_at,
            updated_at=case.updated_at
        )
        
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e)
        )
    except Exception as e:
        logger.error(f"Error creating case: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to create case"
        )
```

#### 6. Add Tests for QdrantVectorStore
**File**: `/Clerk/src/vector_storage/tests/test_qdrant_store.py`

```python
import pytest
from unittest.mock import Mock, AsyncMock, patch
from src.vector_storage.qdrant_store import QdrantVectorStore
from src.config.settings import settings

class TestQdrantVectorStore:
    """Test QdrantVectorStore collection creation functionality"""
    
    @pytest.fixture
    def mock_qdrant_async_client(self):
        """Mock async Qdrant client"""
        client = AsyncMock()
        client.collection_exists = AsyncMock()
        client.create_collection = AsyncMock()
        client.create_payload_index = AsyncMock()
        return client
    
    @pytest.fixture
    def vector_store(self, mock_qdrant_async_client):
        """Create QdrantVectorStore with mocked client"""
        store = QdrantVectorStore()
        store.async_client = mock_qdrant_async_client
        return store
    
    @pytest.mark.asyncio
    async def test_create_case_collections_success(self, vector_store):
        """Test successful creation of all case collections"""
        # Setup
        collection_name = "test_case_12345678"
        vector_store.async_client.collection_exists.return_value = False
        
        # Execute
        results = await vector_store.create_case_collections(collection_name)
        
        # Verify
        assert len(results) == 4
        assert all(results.values())
        assert collection_name in results
        assert f"{collection_name}_facts" in results
        assert f"{collection_name}_timeline" in results
        assert f"{collection_name}_depositions" in results
        
        # Verify create_collection was called 4 times
        assert vector_store.async_client.create_collection.call_count == 4
    
    @pytest.mark.asyncio
    async def test_create_case_collections_already_exist(self, vector_store):
        """Test when collections already exist"""
        # Setup
        collection_name = "existing_case_12345678"
        vector_store.async_client.collection_exists.return_value = True
        
        # Execute
        results = await vector_store.create_case_collections(collection_name)
        
        # Verify
        assert all(results.values())
        # Should not create collections that already exist
        vector_store.async_client.create_collection.assert_not_called()
    
    @pytest.mark.asyncio
    async def test_create_case_collections_partial_failure(self, vector_store):
        """Test partial failure during collection creation"""
        # Setup
        collection_name = "partial_fail_12345678"
        vector_store.async_client.collection_exists.return_value = False
        
        # Make third collection creation fail
        vector_store.async_client.create_collection.side_effect = [
            None,  # Success
            None,  # Success
            Exception("Qdrant error"),  # Failure
            None   # Success
        ]
        
        # Execute
        results = await vector_store.create_case_collections(collection_name)
        
        # Verify
        assert results[collection_name] == True
        assert results[f"{collection_name}_facts"] == True
        assert results[f"{collection_name}_timeline"] == False
        assert results[f"{collection_name}_depositions"] == True
    
    @pytest.mark.asyncio
    async def test_create_case_collections_long_name(self, vector_store):
        """Test collection name truncation for long names"""
        # Setup - name that would exceed 63 chars with suffixes
        collection_name = "very_long_case_name_that_exceeds_limit_when_suffixes_added_12345678"
        vector_store.async_client.collection_exists.return_value = False
        
        # Execute
        results = await vector_store.create_case_collections(collection_name)
        
        # Verify all collection names are within limit
        for coll_name in results.keys():
            assert len(coll_name) <= 63
```

#### 7. Add Tests for Case Endpoint
**File**: `/Clerk/src/api/tests/test_case_endpoints.py`

```python
import pytest
from unittest.mock import Mock, AsyncMock, patch
from fastapi.testclient import TestClient
from src.api.case_endpoints import router

class TestCaseEndpoints:
    """Test case creation with Qdrant collection creation"""
    
    @pytest.mark.asyncio
    @patch('src.api.case_endpoints.CaseService.create_case')
    @patch('src.api.case_endpoints.QdrantVectorStore')
    @patch('src.api.case_endpoints.create_case_collections_with_events')
    async def test_create_case_with_collections_success(
        self,
        mock_create_collections,
        mock_vector_store_class,
        mock_create_case
    ):
        """Test successful case creation with Qdrant collections"""
        # Setup
        mock_case = Mock(
            id="case-123",
            name="Test Case",
            collection_name="test_case_12345678",
            case_metadata=None
        )
        mock_create_case.return_value = mock_case
        mock_create_collections.return_value = True
        
        # Execute (would need proper FastAPI test client setup)
        # This is a simplified example
        
        # Verify
        mock_create_collections.assert_called_once()
        mock_vector_store_class.assert_called_once()
    
    @pytest.mark.asyncio
    @patch('src.api.case_endpoints.CaseService.create_case')
    @patch('src.api.case_endpoints.QdrantVectorStore')
    @patch('src.api.case_endpoints.create_case_collections_with_events')
    async def test_create_case_collections_failure_non_blocking(
        self,
        mock_create_collections,
        mock_vector_store_class,
        mock_create_case
    ):
        """Test that Qdrant failure doesn't block case creation"""
        # Setup
        mock_case = Mock(
            id="case-456",
            name="Test Case 2",
            collection_name="test_case_2_12345678"
        )
        mock_create_case.return_value = mock_case
        mock_create_collections.side_effect = Exception("Qdrant unavailable")
        
        # Execute - should not raise exception
        # Case should still be created successfully
        
        # Verify case was created despite Qdrant error
        mock_create_case.assert_called_once()
```

#### 8. Integration Test
**File**: `/Clerk/src/api/tests/test_case_integration.py`

```python
import pytest
from unittest.mock import patch, AsyncMock

@pytest.mark.integration
class TestCaseCreationIntegration:
    """Integration tests for case creation with Qdrant"""
    
    @pytest.mark.asyncio
    async def test_full_case_creation_flow(self, test_client, test_db):
        """Test complete case creation flow including Qdrant collections"""
        # This would require a test Qdrant instance or extensive mocking
        # Example structure:
        
        with patch('src.vector_storage.qdrant_store.QdrantVectorStore') as mock_store:
            mock_store.return_value.create_case_collections = AsyncMock(
                return_value={
                    "test_case_123": True,
                    "test_case_123_facts": True,
                    "test_case_123_timeline": True,
                    "test_case_123_depositions": True
                }
            )
            
            response = test_client.post(
                "/api/cases",
                json={"name": "Test Case", "metadata": {}}
            )
            
            assert response.status_code == 200
            assert mock_store.return_value.create_case_collections.called
```

## Implementation Tasks

### Task List (in order)
1. **Add WebSocket event emitter** (`emit_case_event`) to `socket_server.py`
2. **Implement async collection creation methods** in `QdrantVectorStore`:
   - `create_case_collections`
   - `_create_standard_collection_async`
   - `_create_hybrid_collection_async`
   - `_create_payload_indexes_async`
3. **Create helper function** `create_case_collections_with_events` in `case_endpoints.py`
4. **Modify `create_case` endpoint** to call collection creation after case is saved
5. **Create test file** `/Clerk/src/vector_storage/tests/test_qdrant_store.py` with unit tests
6. **Add integration tests** to test the full flow
7. **Test with running system** using `python start_services_with_postgres.py --profile cpu`
8. **Update frontend** to handle new WebSocket events (if needed)

## Error Handling Strategy

1. **Qdrant Service Down**: Log error, emit WebSocket event, but allow case creation
2. **Collection Already Exists**: Treat as success, continue with other collections
3. **Timeout**: Use Qdrant client timeout settings, fail gracefully
4. **Partial Failure**: Create what we can, report which collections failed
5. **WebSocket Errors**: Never let WebSocket failures affect case creation

## Configuration

### Environment Variables
```bash
# Existing variables used
QDRANT_HOST=localhost
QDRANT_PORT=6333
QDRANT_API_KEY=your_key
QDRANT_HTTPS=false

# Settings referenced
ENABLE_HYBRID_SEARCH=true
VECTOR_EMBEDDING_DIMENSIONS=1536
VECTOR_LEGAL_EMBEDDING_DIMENSIONS=768
```

### Collection Types
- **Main Collection**: Hybrid search with semantic and legal concept vectors
- **Facts Collection**: Standard collection for fact embeddings
- **Timeline Collection**: Standard collection with temporal metadata
- **Depositions Collection**: Hybrid collection optimized for citation search

## Validation Gates

```bash
# 1. Lint and format check
cd /Clerk
ruff check --fix src/
ruff format src/

# 2. Type checking (if mypy is configured)
mypy src/api/case_endpoints.py src/vector_storage/qdrant_store.py

# 3. Run unit tests
python -m pytest src/vector_storage/tests/test_qdrant_store.py -v
python -m pytest src/api/tests/test_case_endpoints.py -v

# 4. Run integration test (requires services running)
python start_services_with_postgres.py --profile cpu
python -m pytest src/api/tests/test_case_integration.py -v -m integration

# 5. Manual validation
# - Create a new case via frontend
# - Check Docker logs for Qdrant container to see collections created
# - Verify WebSocket events in browser console
# - Check that all 4 collections exist in Qdrant UI (http://localhost:6333/dashboard)
```

## Success Criteria

1. **Functional Requirements**:
   - ✅ All 4 collections created automatically on case creation
   - ✅ WebSocket events emitted for progress tracking
   - ✅ Case creation succeeds even if Qdrant fails
   - ✅ Collections ready for immediate document upload

2. **Non-Functional Requirements**:
   - ✅ Collection creation completes within 2 seconds
   - ✅ No blocking of API response
   - ✅ Comprehensive error logging
   - ✅ All tests pass

3. **Code Quality**:
   - ✅ Follows existing patterns
   - ✅ Comprehensive test coverage
   - ✅ Clear error messages
   - ✅ Type hints on all functions

## References

### Documentation URLs
- **Qdrant Collections**: https://qdrant.tech/documentation/concepts/collections/
- **Qdrant Async Client**: https://github.com/qdrant/qdrant-client/blob/master/qdrant_client/async_qdrant_client.py
- **FastAPI Background Tasks**: https://fastapi.tiangolo.com/tutorial/background-tasks/
- **Python SocketIO Server**: https://python-socketio.readthedocs.io/en/stable/server.html#emitting-events
- **SQLAlchemy Async Sessions**: https://docs.sqlalchemy.org/en/20/orm/extensions/asyncio.html

### Existing Patterns to Follow
- WebSocket events: See `emit_discovery_started()` in `socket_server.py`
- Async operations: See `hybrid_search()` in `qdrant_store.py`
- Error handling: See `ensure_collection_exists()` in `qdrant_store.py`
- Test structure: See `test_case_manager.py` for test patterns
