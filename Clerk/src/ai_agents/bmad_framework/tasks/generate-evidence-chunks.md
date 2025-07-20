# Generate Evidence Chunks

## Purpose
Extract evidence with citations and page numbers from document search results to support deficiency findings

## Task Execution

### 1. Validate Input
- Ensure document chunks from search results are provided
- Verify case_name for isolation
- Check citation format requirements
- Validate user permissions

### 2. Process Search Result Chunks
For each document chunk:
- Extract document metadata (ID, name, date)
- Identify page numbers or bates ranges
- Preserve original text formatting
- Calculate chunk relevance scores

### 3. Extract Relevant Passages
- Identify key sentences supporting deficiency
- Maintain surrounding context (2-3 sentences)
- Highlight specific terms matching RTP request
- Preserve legal citations within text

### 4. Format Citations
Apply evidence citation template:
- Document name and identifier
- Bates number range (if available)
- Page numbers in original document
- Date of document
- Document type classification

### 5. Calculate Relevance Scores
For each evidence chunk:
- Semantic similarity to RTP request
- Keyword match density
- Contextual importance
- Date relevance
- Aggregate confidence score

### 6. Organize Evidence by Request
- Group evidence chunks by RTP request
- Sort by relevance score descending
- Remove duplicate or overlapping chunks
- Maintain top N most relevant per request

### 7. Generate Evidence Summary
- Total evidence chunks found
- Distribution across requests
- Average confidence scores
- Document type breakdown
- Date range coverage

### 8. Create Citation Report
Format output with:
- Structured evidence array
- Full citation details
- Highlighted relevant text
- Cross-references to documents
- Evidence strength indicators

## Elicitation Required
elicit: false

## WebSocket Events
- agent:task_started - Evidence extraction started
- agent:task_progress - Processing chunk batch
- agent:evidence_found - Relevant evidence identified
- agent:citation_formatted - Citation created
- agent:task_completed - All evidence processed

## Evidence Chunk Structure
```yaml
evidence_chunk:
  document_id: string
  document_name: string
  chunk_text: string
  page_numbers: array of integers
  bates_range: 
    start: string
    end: string
  relevance_score: float (0.0-1.0)
  highlights: array of text ranges
  document_date: date
  document_type: string
```

## Integration Points
- Search results from search-production task
- Evidence citation template
- Document metadata store
- Bates number registry
- RTP request analyzer

## Output Format
```json
{
  "evidence_id": "evid-123",
  "case_name": "Smith_v_Jones_2024",
  "total_chunks": 145,
  "evidence_by_request": {
    "1": [
      {
        "document_id": "doc-789",
        "document_name": "Contract_Amendment_2022.pdf",
        "bates_range": {
          "start": "SMITH_001234",
          "end": "SMITH_001236"
        },
        "page_numbers": [12, 13],
        "chunk_text": "The parties agreed to modify the contract terms as follows: payment shall be made within 30 days of invoice...",
        "relevance_score": 0.92,
        "highlights": [
          {"start": 23, "end": 40, "text": "modify the contract"}
        ],
        "document_date": "2022-06-15",
        "document_type": "contract",
        "citation": "Contract Amendment dated June 15, 2022 (SMITH_001234-36) at pages 12-13"
      }
    ]
  },
  "summary": {
    "high_relevance_chunks": 45,
    "medium_relevance_chunks": 70,
    "low_relevance_chunks": 30,
    "document_types": {
      "contracts": 25,
      "emails": 80,
      "memos": 20,
      "letters": 20
    }
  }
}
```

## Citation Formatting Rules
- Always include document identifier
- Use bates numbers when available
- Fallback to page numbers if no bates
- Include document date in citation
- Maintain consistent format throughout

## Quality Controls
- Minimum relevance threshold: 0.5
- Maximum chunk length: 500 words
- Required metadata fields validation
- Duplicate detection across chunks
- Citation format verification

## Error Handling
- Missing document metadata
- Invalid bates numbers
- Chunk extraction failures
- Template formatting errors
- Relevance calculation errors