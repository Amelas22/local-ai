# Discovery Processing End-to-End Test

This directory contains comprehensive end-to-end tests for the discovery processing workflow in Clerk.

## Test Overview

The `test_discovery_processing_e2e.py` file tests the complete discovery processing flow including:

1. **Document Upload**: Accepts PDF files via JSON with base64 encoding or multipart/form-data
2. **Document Splitting**: Uses AI to identify document boundaries within large PDFs
3. **Chunk Storage**: Stores document chunks in the main case collection
4. **Fact Extraction**: Extracts legal facts and stores them in the `{case_name}_facts` collection
5. **Document Metadata**: Stores document metadata in the `{case_name}_documents` collection
6. **WebSocket Events**: Emits real-time progress updates throughout the process

## Test Cases

### 1. Complete Discovery Processing Flow
- Tests the full workflow from PDF upload to fact storage
- Verifies all WebSocket events are emitted correctly
- Ensures documents are split and stored in appropriate collections
- Validates fact extraction and storage

### 2. Error Handling
- Tests graceful handling of corrupted PDFs
- Verifies error events are emitted via WebSocket
- Ensures partial failures don't crash the system

### 3. Fact Search
- Tests searching for facts after processing
- Verifies case isolation works correctly
- Validates search filtering by confidence, category, etc.

### 4. Document Deduplication
- Tests that duplicate documents are not processed twice
- Verifies hash-based deduplication works correctly

### 5. Multipart Form Upload
- Tests alternative upload method using multipart/form-data
- Ensures compatibility with different client implementations

## Running the Tests

### Prerequisites
- Python 3.11+
- All dependencies from requirements.txt installed
- Test PDF file at: `/mnt/d/jrl/GitHub Repos/local-ai/tesdoc_Redacted_ocr.pdf`

### Run All E2E Tests
```bash
# From the Clerk directory
python run_discovery_e2e_test.py
```

### Run Specific Test
```bash
# Run just the complete flow test
python run_discovery_e2e_test.py test_complete_discovery_processing_flow

# Or use pytest directly
pytest src/api/tests/test_discovery_processing_e2e.py::TestDiscoveryProcessingE2E::test_complete_discovery_processing_flow -v -s
```

### Run with Docker
```bash
# From the local-ai-package directory
docker-compose -p localai -f docker-compose.yml -f docker-compose.clerk.yml exec clerk python run_discovery_e2e_test.py
```

## Test Configuration

The tests use mocked dependencies by default:
- **Supabase**: Mocked for case/fact storage
- **Qdrant**: Mocked for vector storage
- **OpenAI**: Mocked for embeddings and AI processing
- **WebSocket**: Events are captured for verification

To run against real services, modify the fixture implementations to use actual clients.

## Test Data

The test uses a real PDF file located at:
```
/mnt/d/jrl/GitHub Repos/local-ai/tesdoc_Redacted_ocr.pdf
```

This PDF should contain multiple documents to test the splitting functionality.

## Expected Results

When running the complete flow test, you should see:
1. WebSocket events for: started, document_found, chunking, embedding, fact_extracted, completed
2. At least 2 documents discovered (from splitting)
3. At least 2 facts extracted
4. All data stored in appropriate collections

## Debugging

To debug failing tests:
1. Check the console output for WebSocket events
2. Verify mock configurations match actual API expectations
3. Ensure the test PDF exists and is readable
4. Check environment variables are set correctly

## Integration with Frontend

The test mimics the exact flow used by the frontend:
1. Frontend uploads PDF with metadata
2. Backend returns processing_id
3. Frontend subscribes to WebSocket events
4. Backend emits progress updates
5. Frontend displays results in real-time

This ensures the test accurately represents production usage.