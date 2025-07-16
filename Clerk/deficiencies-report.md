# Discovery Deficiency Analysis Feature

## FEATURE:

Implement an automated discovery deficiency analysis system that processes Request for Production (RFP) documents and Defense Response documents against the stored discovery materials in the vector database. The system should automatically generate a comprehensive deficiency report after discovery processing completes, identifying what was produced, not produced, or partially produced for each request.

**CRITICAL REQUIREMENT**: The system MUST search ONLY within documents that were processed during the current discovery production session. It should NOT search the entire case database or include documents from other productions. This is achieved by filtering all vector searches using the processing_id and production_batch metadata from the current discovery processing session.

### Key Components:
1. **Automatic Trigger**: Runs in background after discovery processing while users review extracted facts
2. **AI-Powered Analysis**: Uses intelligent reasoning to search the vector database for responsive documents
3. **Scoped Search**: Searches ONLY within documents from the current discovery processing session
4. **Comprehensive Report**: Generates structured analysis with confidence scores and source citations
5. **UI Integration**: Displays editable report in UI with download capability

## EXAMPLES:

### 1. Request Parsing and Analysis
```python
async def analyze_discovery_deficiencies(
    case_name: str,
    rfp_document: Dict[str, Any],
    defense_response: Dict[str, Any],
    processing_id: str,
    production_metadata: Dict[str, Any]
) -> DeficiencyReport:
    """
    Analyze discovery production against requests.
    
    Example request handling:
    Request: "All training materials, policies, and procedures related to 
             speed management and safe driving practices from 2020-2024"
    
    AI Agent should:
    1. Extract key concepts: ["training materials", "policies", "procedures", 
                             "speed management", "safe driving", "2020-2024"]
    2. Generate search queries: 
       - "speed management training"
       - "safe driving policy"
       - "driving procedures"
    3. Search with date filters where applicable
    """
    
    # Parse RFP into individual requests
    requests = await parse_rfp_document(rfp_document)
    
    # Parse defense responses
    responses = await parse_defense_responses(defense_response)
    
    # Analyze each request - FILTER TO CURRENT PRODUCTION ONLY
    analyses = []
    for idx, request in enumerate(requests):
        analysis = await analyze_single_request(
            request=request,
            response=responses.get(idx),
            case_name=case_name,
            vector_store=vector_store,
            processing_id=processing_id,
            production_metadata=production_metadata
        )
        analyses.append(analysis)
    
    return DeficiencyReport(analyses=analyses)
```

### 2. Individual Request Analysis
```python
async def analyze_single_request(
    request: RequestItem,
    response: Optional[ResponseItem],
    case_name: str,
    vector_store: QdrantVectorStore,
    processing_id: str,
    production_metadata: Dict[str, Any]
) -> RequestAnalysis:
    """
    Example analysis for a single request.
    IMPORTANT: Only searches within documents from the current discovery production.
    """
    # Use AI to determine search strategy
    search_strategy = await llm.generate_search_strategy(
        request_text=request.text,
        context="discovery deficiency analysis"
    )
    
    # Execute searches based on strategy - FILTERED TO CURRENT PRODUCTION
    search_results = []
    for query in search_strategy.queries:
        # Build filter to only search documents from this production
        production_filter = models.Filter(
            must=[
                models.FieldCondition(
                    key="case_name",
                    match=models.MatchValue(value=case_name)
                ),
                models.FieldCondition(
                    key="processing_id",
                    match=models.MatchValue(value=processing_id)
                ),
                models.FieldCondition(
                    key="production_batch",
                    match=models.MatchValue(value=production_metadata.get("production_batch"))
                )
            ]
        )
        
        results = await vector_store.hybrid_search(
            case_name=case_name,
            query_text=query,
            limit=20,
            score_threshold=0.7,
            filter=production_filter  # This ensures we only search current production
        )
        search_results.extend(results)
    
    # Analyze results against request
    analysis = await llm.analyze_production_completeness(
        request=request.text,
        response=response.text if response else "No response provided",
        found_documents=search_results,
        instructions="""
        Determine if the request was:
        1. Fully Produced - All requested materials found
        2. Partially Produced - Some but not all materials found
        3. Not Produced - No responsive materials found
        
        Provide specific evidence with bates numbers and quotes.
        Include confidence score (0-100).
        """
    )
    
    return RequestAnalysis(
        request_number=request.number,
        request_text=request.text,
        response_text=response.text if response else None,
        status=analysis.status,
        confidence=analysis.confidence,
        evidence=analysis.evidence,
        deficiencies=analysis.deficiencies
    )
```

### 3. Report Generation with Formatting
```python
class DeficiencyReportGenerator:
    """
    Generate formatted deficiency reports with source citations.
    """
    
    def format_analysis(self, analysis: RequestAnalysis) -> str:
        """
        Format a single request analysis with color coding.
        """
        report = f"""
### Request {analysis.request_number}
**Request Text:** {analysis.request_text}

**Defense Response:** {analysis.response_text or "No response provided"}

**Analysis:** (Confidence: {analysis.confidence}%)
Status: **{self._format_status(analysis.status)}**

{analysis.analysis_text}

**Evidence Found:**
"""
        # Add evidence with highlighted quotes
        for evidence in analysis.evidence:
            report += f"""
- Document: {evidence.document_title} (Bates: {evidence.bates_range})
  <span style="background-color: #90EE90">{evidence.quoted_text}</span>
  
"""
        
        if analysis.deficiencies:
            report += "\n**Deficiencies Identified:**\n"
            for deficiency in analysis.deficiencies:
                report += f"- {deficiency}\n"
        
        return report
    
    def _format_status(self, status: str) -> str:
        """Color code status."""
        colors = {
            "Fully Produced": "🟢",
            "Partially Produced": "🟡", 
            "Not Produced": "🔴"
        }
        return f"{colors.get(status, '')} {status}"
```

### 4. WebSocket Updates During Analysis
```python
async def emit_deficiency_analysis_progress(
    processing_id: str,
    case_name: str,
    current_request: int,
    total_requests: int,
    current_status: str
):
    """
    Emit real-time progress updates during deficiency analysis.
    """
    await sio.emit(
        'discovery:deficiency_analysis_progress',
        {
            'processingId': processing_id,
            'currentRequest': current_request,
            'totalRequests': total_requests,
            'status': current_status,
            'progressPercent': (current_request / total_requests) * 100
        },
        room=f'case_{case_name}'
    )
```

### 5. UI Component for Report Display
```typescript
interface DeficiencyReport {
  requestAnalyses: RequestAnalysis[];
  generatedAt: string;
  overallCompleteness: number;
}

const DeficiencyReportViewer: React.FC<{report: DeficiencyReport}> = ({ report }) => {
  const [editedReport, setEditedReport] = useState(report);
  
  return (
    <Box>
      <Paper sx={{ p: 3, mb: 2 }}>
        <Typography variant="h5">Discovery Deficiency Analysis</Typography>
        <Typography variant="subtitle1">
          Generated: {new Date(report.generatedAt).toLocaleString()}
        </Typography>
        <LinearProgress 
          variant="determinate" 
          value={report.overallCompleteness} 
          sx={{ mt: 2 }}
        />
        <Typography variant="body2">
          Overall Completeness: {report.overallCompleteness}%
        </Typography>
      </Paper>
      
      {report.requestAnalyses.map((analysis) => (
        <RequestAnalysisCard 
          key={analysis.requestNumber}
          analysis={analysis}
          onEdit={(updated) => handleAnalysisEdit(analysis.requestNumber, updated)}
          editable={true}
        />
      ))}
      
      <Button 
        variant="contained" 
        onClick={handleDownloadReport}
        startIcon={<DownloadIcon />}
      >
        Download Report
      </Button>
    </Box>
  );
};
```

## DOCUMENTATION:

### Source Files to Reference:
1. **src/ai_agents/fact_extractor.py** - Reference for AI agent pattern and LLM usage
2. **src/vector_storage/qdrant_store.py** - Vector database search methods
3. **src/api/discovery_endpoints.py** - Discovery processing endpoint structure
4. **src/models/discovery_models.py** - Existing discovery data models
5. **src/services/fact_manager.py** - Pattern for managing analysis results
6. **src/document_processing/discovery_splitter.py** - Understanding document structure
7. **frontend/src/components/discovery/FactReviewPanel.tsx** - UI pattern for report display
8. **frontend/src/hooks/useDiscoverySocket.ts** - WebSocket integration pattern

### New Files to Create:
1. **src/ai_agents/deficiency_analyzer.py** - Main analysis agent
2. **src/models/deficiency_models.py** - Data models for analysis
3. **src/services/deficiency_report_service.py** - Report generation service
4. **frontend/src/components/discovery/DeficiencyReportViewer.tsx** - UI component
5. **frontend/src/components/discovery/RequestAnalysisCard.tsx** - Individual request display

### External Documentation:
- OpenAI Function Calling documentation for structured analysis
- Qdrant hybrid search documentation for optimal retrieval
- Material-UI documentation for report UI components

## OTHER CONSIDERATIONS:

### 1. **Production-Specific Filtering (CRITICAL)**
- **MUST filter all vector searches to ONLY documents from the current discovery production**
- Use processing_id and production_batch metadata to ensure search scope
- This prevents analysis from including documents from other productions or general case documents
- Example filter structure:
```python
# Every search MUST include these filters
production_filter = {
    "case_name": case_name,
    "processing_id": current_processing_id,
    "production_batch": current_production_batch
}
```

### 2. **Case Isolation**
- In addition to production filtering, ensure all vector searches are filtered by case_name
- Use the same case isolation patterns as in existing code
- Double-layer security: case isolation + production isolation

### 3. **Performance Optimization**
- Process requests in parallel where possible using asyncio.gather()
- Cache search results to avoid duplicate queries
- Implement pagination for large reports

### 4. **Error Handling**
- Handle cases where RFP or Defense Response parsing fails
- Gracefully handle when no documents are found
- Provide clear error messages in the UI

### 5. **AI Reasoning Guidelines**
```python
# The AI should NOT make assumptions
ANALYSIS_INSTRUCTIONS = """
When analyzing if documents were produced:
1. Only mark as "Fully Produced" if you find clear, specific evidence
2. If context is ambiguous or only partially relevant, mark as "Partially Produced"
3. If no relevant documents found, mark as "Not Produced"
4. Always provide specific quotes and bates numbers, when able, as evidence
5. Never assume documents exist without finding them
6. Consider date ranges, document types, and specific parties mentioned
"""
```

### 6. **Report Persistence**
- Save generated reports to the database for future reference
- Allow users to regenerate reports if new documents are added
- Track report versions and edits

### 7. **Bates Number Handling**
- Extract bates numbers from UnifiedDocument metadata
- Display bates ranges for multi-page documents
- Ensure bates numbers are searchable in the report

### 8. **Concurrent Processing**
- Run deficiency analysis as a background task while users review facts
- Don't block the UI during analysis
- Provide real-time progress updates via WebSocket

### 9. **Template Flexibility**
- Design the system to support custom analysis templates in the future
- Make the report format configurable
- Support export to multiple formats (PDF, DOCX, etc.)

### 10. **Search Strategy Examples**
The AI agent should intelligently determine search strategies based on request types:
- **Document requests**: Search by document type + keywords
- **Communication requests**: Search by parties involved + date ranges
- **Policy requests**: Search by document title patterns + keywords
- **Training materials**: Search by specific terms + document characteristics

### 11. **Testing Considerations**
- Create test cases with known deficiencies
- Validate confidence scores against manual review
- Test with various RFP formats and structures
- Ensure proper handling of edge cases (empty responses, malformed requests)