# Pre-Analysis Validation Checklist

## Purpose
Validate all prerequisites before starting deficiency analysis to ensure accurate results

## Validation Steps

### 1. Case Context Validation
- [ ] Case name is provided and valid
- [ ] User has read permission for the case
- [ ] Case exists in database
- [ ] Case status is active (not archived)

### 2. RTP Document Validation
- [ ] RTP document has been successfully parsed
- [ ] At least one RTP request was extracted
- [ ] Request numbers are properly formatted
- [ ] Request text is complete and readable
- [ ] Page references are accurate

### 3. Production Document Validation
- [ ] Production documents are indexed in Qdrant
- [ ] Vector embeddings are generated
- [ ] Document metadata is complete
- [ ] Bates numbers are properly formatted
- [ ] Case isolation is confirmed

### 4. OC Response Validation (if provided)
- [ ] OC response document is accessible
- [ ] Response format is parseable
- [ ] Response correlates to RTP requests
- [ ] Objections and claims are identified

### 5. System Resources Check
- [ ] Qdrant vector store is accessible
- [ ] OpenAI API is responsive
- [ ] Sufficient API quota available
- [ ] Database connections are stable
- [ ] WebSocket server is running

### 6. Analysis Parameters
- [ ] Confidence threshold is set (default: 0.7)
- [ ] Search weights are configured
- [ ] Result limits are appropriate
- [ ] Date ranges are valid
- [ ] Document type filters are set

### 7. Output Configuration
- [ ] Report format is specified
- [ ] Output destination is writable
- [ ] Template files are accessible
- [ ] Citation format is selected

## Validation Errors

### Critical Errors (Stop Analysis)
- Missing case name or invalid case
- No RTP requests found
- Vector store unavailable
- No production documents indexed

### Warning Conditions (Continue with Caution)
- Low number of production documents
- Missing OC response document
- Partial metadata on documents
- API quota running low

### Information Messages
- Using default confidence threshold
- Standard citation format selected
- Analysis limited to specific date range

## Pre-Flight Commands
```python
# Check case access
valid = await case_manager.validate_case_access(
    case_id=case_id,
    user_id=user_id,
    required_permission="read"
)

# Verify RTP parsing
rtp_data = await get_parsed_rtp(case_name, rtp_document_id)
assert len(rtp_data.requests) > 0

# Test vector store
test_results = await vector_store.health_check()
assert test_results.status == "healthy"

# Check production documents
doc_count = await vector_store.count_documents(case_name)
assert doc_count > 0
```

## Checklist Completion
- All critical items must pass
- Document any warnings in analysis log
- Proceed only when validation succeeds
- Report validation status via WebSocket