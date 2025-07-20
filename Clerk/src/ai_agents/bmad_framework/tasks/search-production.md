# Search Production Documents

## Purpose
Search through produced documents using RAG (Retrieval Augmented Generation) with Qdrant vector store to find documents responsive to specific RTP requests.

## Task Execution

### 1. Validate Search Parameters
- Ensure case_name is provided
- Verify search query or RTP request text
- Check user has read permission
- Validate vector store connectivity

### 2. Prepare Search Query
- Clean and optimize query text
- Extract key terms and concepts
- Identify date ranges if present
- Expand acronyms and legal terms
- Create both keyword and semantic queries

### 3. Initialize Vector Store Connection
- Connect to QdrantVectorStore
- Select case-specific collection
- Verify collection exists and has documents
- Check embedding model availability

### 4. Execute Hybrid Search
- Perform vector similarity search
- Execute keyword/BM25 search in parallel
- Combine results with configurable weights:
  - Vector weight: 0.7 (semantic)
  - Text weight: 0.3 (keyword)
- Apply case isolation filter
- Limit results based on parameters

### 5. Process Search Results
For each result:
- Extract document metadata
- Calculate relevance score
- Identify matching sections/chunks
- Highlight relevant passages
- Track document type and date
- Note bates numbers if available

### 6. Rank and Filter Results
- Re-rank by relevance to RTP request
- Apply date range filters if specified
- Filter by document type if requested
- Remove duplicate or near-duplicate results
- Apply confidence threshold

### 7. Analyze Result Coverage
- Determine if results fully address request
- Identify gaps in production
- Note partially responsive documents
- Flag potentially privileged content
- Calculate overall responsiveness score

### 8. Generate Search Report
- List of responsive documents
- Relevance scores and rankings
- Matching text excerpts
- Coverage analysis
- Recommendations for further search

## Elicitation Required
elicit: false

## WebSocket Events
- agent:task_started - Search initiated
- agent:task_progress - Search progress update
- agent:results_found - Batch of results ready
- agent:ranking_complete - Results ranked
- agent:task_completed - Search finished

## Search Parameters
```yaml
required:
  - case_name: string
  - query: string  # RTP request text or search terms

optional:
  - limit: integer (default: 50)
  - date_range:
      start: date
      end: date
  - document_types: array of strings
  - vector_weight: float (0.0-1.0, default: 0.7)
  - text_weight: float (0.0-1.0, default: 0.3)
  - confidence_threshold: float (default: 0.5)
```

## Integration Points
- QdrantVectorStore for vector search
- OpenAI embeddings for query vectorization
- Case management for access control
- Document metadata store
- WebSocket for real-time updates

## Output Format
```json
{
  "search_id": "search-456",
  "case_name": "Smith_v_Jones_2024",
  "query": "All emails regarding contract negotiations",
  "total_results": 42,
  "results": [
    {
      "document_id": "doc-789",
      "document_name": "Email_Smith_to_Jones_2022-03-15.pdf",
      "relevance_score": 0.92,
      "vector_score": 0.95,
      "text_score": 0.85,
      "matching_chunks": [
        {
          "text": "...contract negotiations are proceeding...",
          "page": 1,
          "highlight_positions": [[10, 32]]
        }
      ],
      "metadata": {
        "date": "2022-03-15",
        "document_type": "email",
        "bates_number": "SMITH_001234"
      }
    }
  ],
  "coverage_analysis": {
    "fully_responsive": 15,
    "partially_responsive": 20,
    "potentially_responsive": 7,
    "responsiveness_score": 0.75
  }
}
```

## Error Handling
- Vector store connection failures
- Embedding model errors
- Invalid search queries
- No results found
- Case access violations

## Advanced Features
- Query expansion with synonyms
- Legal citation recognition
- Date parsing and normalization
- Privilege detection warnings
- Duplicate detection