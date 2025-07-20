# Categorize Compliance Status

## Purpose
Analyze search results against RTP requests to categorize compliance status and identify deficiencies in document production.

## Task Execution

### 1. Load Analysis Context
- Retrieve parsed RTP requests from previous analysis
- Load search results for each request
- Verify case_name matches throughout
- Check user has write permission for categorization

### 2. Initialize Compliance Categories
Set up standard compliance categories:
- **Fully Produced**: All requested documents provided
- **Partially Produced**: Some but not all documents provided
- **Not Produced**: No responsive documents provided
- **No Responsive Documents**: Legitimate absence of documents
- **Privileged**: Documents withheld on privilege grounds
- **Objected**: Production refused with stated objections

### 3. Analyze Each RTP Request
For each request:
- Retrieve associated search results
- Review opposing counsel's response text
- Compare produced documents against request
- Evaluate completeness of production

### 4. Apply Categorization Logic
Determine category based on:
- **Fully Produced**: 
  - High relevance scores (>0.8)
  - Date ranges fully covered
  - All document types addressed
  - No gaps identified
  
- **Partially Produced**:
  - Some responsive documents found
  - Gaps in date ranges
  - Missing document types
  - Relevance scores 0.5-0.8
  
- **Not Produced**:
  - No documents found in search
  - OC response indicates non-production
  - No privilege claims
  
- **No Responsive Documents**:
  - OC states no documents exist
  - Search confirms absence
  - Reasonable explanation provided

### 5. Calculate Confidence Scores
For each categorization:
- Base score on search result quality
- Adjust for OC response clarity
- Factor in document metadata
- Consider date range coverage
- Account for privilege logs

### 6. Identify Evidence Gaps
- Document types mentioned but not produced
- Date ranges with missing documents
- Communications referenced but not provided
- Metadata inconsistencies
- Chain of custody issues

### 7. Generate Deficiency Details
For deficient categories:
- Specific documents likely missing
- Time periods not covered
- Types of documents expected
- Evidence from produced documents
- Inconsistencies in responses

### 8. Create Compliance Report
- Summary statistics by category
- Detailed findings per request
- Evidence supporting categorization
- Recommendations for follow-up
- Priority rankings for deficiencies

## Elicitation Required
elicit: true (for ambiguous categorizations)

## WebSocket Events
- agent:task_started - Categorization started
- agent:task_progress - Request being analyzed
- agent:category_assigned - Request categorized
- agent:deficiency_found - Deficiency identified
- agent:task_completed - Report generated

## Categorization Rules
```yaml
fully_produced:
  - relevance_threshold: 0.8
  - date_coverage: 100%
  - document_types: all_present
  
partially_produced:
  - relevance_threshold: 0.5
  - date_coverage: >50%
  - document_types: some_missing
  
not_produced:
  - relevance_threshold: <0.3
  - oc_response: indicates_non_production
  - privilege_claimed: false
  
no_responsive_documents:
  - oc_response: states_none_exist
  - search_confirms: true
  - explanation: reasonable
```

## Integration Points
- Search results from search-production task
- RTP requests from analyze-rtp task
- OC response parser
- Deficiency report generator
- Case management system

## Output Format
```json
{
  "categorization_id": "cat-789",
  "case_name": "Smith_v_Jones_2024",
  "total_requests": 25,
  "categorization_summary": {
    "fully_produced": 8,
    "partially_produced": 10,
    "not_produced": 5,
    "no_responsive_documents": 2
  },
  "detailed_categorization": [
    {
      "request_number": "1",
      "category": "partially_produced",
      "confidence_score": 0.75,
      "evidence": {
        "documents_found": 15,
        "date_coverage": "60%",
        "missing_types": ["emails", "memos"],
        "gaps": ["2021-Q3", "2022-Q1"]
      },
      "deficiency_details": {
        "severity": "high",
        "specific_gaps": "Missing internal emails discussing contract",
        "evidence_chunks": [
          {
            "document_id": "doc-123",
            "text": "As discussed in our emails last quarter...",
            "indicates_missing": "emails from Q3 2021"
          }
        ]
      }
    }
  ],
  "recommendations": {
    "high_priority": ["1", "5", "12"],
    "follow_up_needed": ["3", "7", "15"],
    "likely_privileged": ["18", "22"]
  }
}
```

## Elicitation Options
When categorization is ambiguous:
1. Proceed with current categorization
2. Review additional search results
3. Examine OC response in detail
4. Check for privilege log entries
5. Search for related documents
6. Consider date range expansion
7. Review similar requests
8. Flag for manual review
9. Request senior attorney input

## Error Handling
- Missing search results
- Corrupted RTP data
- Invalid OC responses
- Database write failures
- Confidence below threshold