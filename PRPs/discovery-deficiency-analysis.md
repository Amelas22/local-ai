# Discovery Deficiency Analysis Implementation PRP

## Overview
This PRP guides the implementation of an automated discovery deficiency analysis system that identifies gaps between what was requested in discovery and what was actually produced. The system runs automatically after discovery processing completes and generates a comprehensive report showing deficiencies.

**CRITICAL REQUIREMENT**: The system MUST search ONLY within documents from the current discovery production session using production_batch metadata filtering.

## Research Phase Findings

### 1. **Existing Patterns to Follow**

#### AI Agent Pattern (from `src/ai_agents/fact_extractor.py`)
```python
# Standard AI agent structure
class FactExtractor:
    def __init__(self, case_name: str):
        self._validate_case_name(case_name)
        self.case_name = case_name
        self.vector_store = QdrantVectorStore()
        self.agent = Agent(
            model_name,
            result_type=ExtractedFactsBatch,
            system_prompt=FACT_EXTRACTION_PROMPT
        )
```

#### Background Task Pattern (from `src/api/discovery_endpoints.py`)
```python
# Immediate response with background processing
background_tasks.add_task(
    _process_discovery_async,
    processing_id,
    case_context.case_name,
    discovery_request,
    file_contents
)
return DiscoveryProcessingResponse(
    processing_id=processing_id,
    status="processing",
    message="Discovery processing started"
)
```

#### Vector Search with Production Filtering
```python
# From research: production_batch is the key field for filtering
from qdrant_client import models

production_filter = models.Filter(
    must=[
        models.FieldCondition(
            key="case_name",
            match=models.MatchValue(value=case_name)
        ),
        models.FieldCondition(
            key="metadata.production_batch",  # Nested field access
            match=models.MatchValue(value=production_batch)
        )
    ]
)
```

### 2. **Document Structure Insights**

Discovery documents store rich metadata:
- `production_batch`: Primary identifier for grouping documents from same production
- `responsive_to_requests`: List of RFP items the document responds to
- `producing_party`: Who produced the document
- `bates_range`: Document identification numbers
- `confidentiality_designation`: Access level

### 3. **WebSocket Event Pattern**
```python
# Standard event emission pattern
await sio.emit(
    'discovery:deficiency_analysis_progress',
    {
        'processingId': processing_id,
        'currentRequest': current_request,
        'totalRequests': total_requests,
        'progressPercent': progress
    },
    room=f'case_{case_name}'
)
```

## Implementation Blueprint

### Phase 1: Core Models and Infrastructure

#### Task 1.1: Create Deficiency Models
Create `src/models/deficiency_models.py`:
```python
from pydantic import BaseModel, Field
from typing import List, Optional, Dict
from datetime import datetime
from enum import Enum

class ProductionStatus(str, Enum):
    FULLY_PRODUCED = "fully_produced"
    PARTIALLY_PRODUCED = "partially_produced"
    NOT_PRODUCED = "not_produced"

class EvidenceItem(BaseModel):
    document_id: str
    document_title: str
    bates_range: Optional[str]
    quoted_text: str
    confidence_score: float
    page_numbers: Optional[List[int]]

class RequestAnalysis(BaseModel):
    request_number: int
    request_text: str
    response_text: Optional[str]
    status: ProductionStatus
    confidence: float = Field(ge=0, le=100)
    evidence: List[EvidenceItem] = []
    deficiencies: List[str] = []
    search_queries_used: List[str] = []
    
class DeficiencyReport(BaseModel):
    id: str
    case_name: str
    processing_id: str
    production_batch: str
    rfp_document_id: str
    defense_response_id: Optional[str]
    analyses: List[RequestAnalysis]
    overall_completeness: float
    generated_at: datetime
    generated_by: str = "deficiency_analyzer"
    report_version: int = 1
```

#### Task 1.2: Create Deficiency Analyzer Agent
Create `src/ai_agents/deficiency_analyzer.py`:
```python
import asyncio
from typing import List, Dict, Any, Optional
from pydantic_ai import Agent
from pydantic import BaseModel

from ..models.deficiency_models import *
from ..vector_storage.qdrant_store import QdrantVectorStore
from ..document_processing.pdf_extractor import PDFExtractor
from ..utils.logger import setup_logger
from ..websocket.socket_server import sio

logger = setup_logger(__name__)

class SearchStrategy(BaseModel):
    """AI-generated search strategy for finding responsive documents"""
    queries: List[str]
    search_approach: str  # e.g., "keyword", "semantic", "date_range"
    reasoning: str

class DeficiencyAnalyzer:
    """Analyzes discovery productions for deficiencies against RFP requests"""
    
    def __init__(self, case_name: str):
        self._validate_case_name(case_name)
        self.case_name = case_name
        self.vector_store = QdrantVectorStore()
        
        # Agent for generating search strategies
        self.search_agent = Agent(
            'gpt-4o-mini',
            result_type=SearchStrategy,
            system_prompt="""You are a legal discovery expert. Given a Request for Production (RFP), 
            generate effective search queries to find responsive documents. Consider:
            - Key terms and concepts
            - Document types mentioned
            - Date ranges
            - Parties involved
            - Legal terminology variations
            
            DO NOT make assumptions. Only search for what is explicitly requested."""
        )
        
        # Agent for analyzing completeness
        self.analysis_agent = Agent(
            'gpt-4.1-mini',
            result_type=RequestAnalysis,
            system_prompt="""You are a discovery deficiency analyst. Analyze whether documents 
            produced satisfy the request. Be precise and evidence-based:
            
            1. FULLY PRODUCED: Clear evidence all requested items were provided
            2. PARTIALLY PRODUCED: Some but not all items found
            3. NOT PRODUCED: No responsive documents found
            
            Always cite specific evidence with quotes and bates numbers.
            Never assume documents exist without finding them."""
        )
    
    def _validate_case_name(self, case_name: str):
        if not case_name or not isinstance(case_name, str):
            raise ValueError("Case name must be a non-empty string")
    
    async def analyze_discovery_deficiencies(
        self,
        rfp_document_id: str,
        defense_response_id: Optional[str],
        production_batch: str,
        processing_id: str
    ) -> DeficiencyReport:
        """Main entry point for deficiency analysis"""
        logger.info(f"Starting deficiency analysis for case {self.case_name}, batch {production_batch}")
        
        # Extract RFP requests
        rfp_requests = await self._extract_rfp_requests(rfp_document_id)
        
        # Extract defense responses if provided
        defense_responses = {}
        if defense_response_id:
            defense_responses = await self._extract_defense_responses(defense_response_id)
        
        # Analyze each request
        analyses = []
        total_requests = len(rfp_requests)
        
        for idx, (request_num, request_text) in enumerate(rfp_requests.items()):
            # Emit progress
            await self._emit_progress(processing_id, idx + 1, total_requests)
            
            # Analyze single request
            analysis = await self._analyze_single_request(
                request_number=request_num,
                request_text=request_text,
                response_text=defense_responses.get(request_num),
                production_batch=production_batch,
                processing_id=processing_id
            )
            analyses.append(analysis)
        
        # Generate report
        report = DeficiencyReport(
            id=f"deficiency_{processing_id}",
            case_name=self.case_name,
            processing_id=processing_id,
            production_batch=production_batch,
            rfp_document_id=rfp_document_id,
            defense_response_id=defense_response_id,
            analyses=analyses,
            overall_completeness=self._calculate_completeness(analyses),
            generated_at=datetime.utcnow()
        )
        
        return report
```

### Phase 2: Search and Analysis Implementation

#### Task 2.1: Implement Production-Scoped Search
Add to `deficiency_analyzer.py`:
```python
async def _search_production_documents(
    self,
    query: str,
    production_batch: str,
    limit: int = 20
) -> List[UnifiedDocument]:
    """Search ONLY within current production batch"""
    from qdrant_client import models
    
    # CRITICAL: Filter to current production only
    production_filter = models.Filter(
        must=[
            models.FieldCondition(
                key="case_name",
                match=models.MatchValue(value=self.case_name)
            ),
            models.FieldCondition(
                key="metadata.production_batch",
                match=models.MatchValue(value=production_batch)
            )
        ]
    )
    
    # Perform hybrid search
    results = await self.vector_store.hybrid_search(
        collection_name=self.case_name,
        query_text=query,
        query_filter=production_filter,
        limit=limit,
        vector_weight=0.7,
        text_weight=0.3
    )
    
    return results

async def _analyze_single_request(
    self,
    request_number: int,
    request_text: str,
    response_text: Optional[str],
    production_batch: str,
    processing_id: str
) -> RequestAnalysis:
    """Analyze if a single request was satisfied"""
    
    # Generate search strategy
    search_strategy = await self.search_agent.run(
        f"Generate search queries for this RFP request: {request_text}"
    )
    
    # Execute searches
    all_results = []
    for query in search_strategy.data.queries:
        results = await self._search_production_documents(
            query=query,
            production_batch=production_batch
        )
        all_results.extend(results)
    
    # Deduplicate results
    unique_results = self._deduplicate_results(all_results)
    
    # Analyze completeness
    analysis_prompt = f"""
    Request: {request_text}
    Defense Response: {response_text or 'No response provided'}
    
    Found Documents ({len(unique_results)}):
    {self._format_documents_for_analysis(unique_results)}
    
    Analyze if the request was satisfied by these documents.
    """
    
    analysis = await self.analysis_agent.run(analysis_prompt)
    
    # Add search queries used
    analysis.data.search_queries_used = search_strategy.data.queries
    
    return analysis.data
```

#### Task 2.2: Implement RFP/Response Parsing
```python
async def _extract_rfp_requests(self, document_id: str) -> Dict[int, str]:
    """Extract individual requests from RFP document"""
    # Get document from vector store
    document = await self.vector_store.get_document(
        collection_name=self.case_name,
        document_id=document_id
    )
    
    # Use AI to parse requests
    parser_agent = Agent(
        'gpt-4o-mini',
        result_type=Dict[int, str],
        system_prompt="""Extract numbered requests from this Request for Production document.
        Return a dictionary mapping request numbers to request text.
        Example: {1: "All documents relating to...", 2: "All communications between..."}"""
    )
    
    requests = await parser_agent.run(document.content)
    return requests.data
```

### Phase 3: API Integration

#### Task 3.1: Add Deficiency Analysis Endpoint
Add to `src/api/discovery_endpoints.py`:
```python
@router.post("/analyze-deficiencies", response_model=DeficiencyReportResponse)
async def analyze_discovery_deficiencies(
    request: DeficiencyAnalysisRequest,
    background_tasks: BackgroundTasks,
    case_context: CaseContext = Depends(require_case_context("read"))
) -> DeficiencyReportResponse:
    """Analyze discovery production for deficiencies"""
    
    analysis_id = str(uuid.uuid4())
    
    # Start background analysis
    background_tasks.add_task(
        _analyze_deficiencies_async,
        analysis_id=analysis_id,
        case_name=case_context.case_name,
        rfp_document_id=request.rfp_document_id,
        defense_response_id=request.defense_response_id,
        production_batch=request.production_batch,
        processing_id=request.processing_id
    )
    
    return DeficiencyReportResponse(
        analysis_id=analysis_id,
        status="analyzing",
        message="Deficiency analysis started"
    )

async def _analyze_deficiencies_async(
    analysis_id: str,
    case_name: str,
    rfp_document_id: str,
    defense_response_id: Optional[str],
    production_batch: str,
    processing_id: str
):
    """Background task for deficiency analysis"""
    try:
        # Emit started event
        await sio.emit(
            'discovery:deficiency_analysis_started',
            {
                'analysisId': analysis_id,
                'caseId': case_name,
                'processingId': processing_id
            },
            room=f'case_{case_name}'
        )
        
        # Run analysis
        analyzer = DeficiencyAnalyzer(case_name)
        report = await analyzer.analyze_discovery_deficiencies(
            rfp_document_id=rfp_document_id,
            defense_response_id=defense_response_id,
            production_batch=production_batch,
            processing_id=processing_id
        )
        
        # Store report
        await store_deficiency_report(report)
        
        # Emit completed event
        await sio.emit(
            'discovery:deficiency_analysis_completed',
            {
                'analysisId': analysis_id,
                'reportId': report.id,
                'overallCompleteness': report.overall_completeness
            },
            room=f'case_{case_name}'
        )
        
    except Exception as e:
        logger.error(f"Deficiency analysis failed: {e}")
        await sio.emit(
            'discovery:deficiency_analysis_error',
            {
                'analysisId': analysis_id,
                'error': str(e)
            },
            room=f'case_{case_name}'
        )
```

### Phase 4: Frontend Implementation

#### Task 4.1: Create Report Viewer Component
Create `frontend/src/components/discovery/DeficiencyReportViewer.tsx`:
```typescript
import React, { useState, useEffect } from 'react';
import {
  Box,
  Paper,
  Typography,
  LinearProgress,
  Button,
  Accordion,
  AccordionSummary,
  AccordionDetails,
  Chip,
  IconButton,
  TextField,
} from '@mui/material';
import {
  ExpandMore as ExpandMoreIcon,
  Download as DownloadIcon,
  Edit as EditIcon,
  Save as SaveIcon,
} from '@mui/icons-material';
import { DeficiencyReport, RequestAnalysis } from '../../types/discovery.types';
import { useAppDispatch } from '../../hooks/redux';

interface DeficiencyReportViewerProps {
  report: DeficiencyReport;
  onUpdate?: (updatedReport: DeficiencyReport) => void;
}

export const DeficiencyReportViewer: React.FC<DeficiencyReportViewerProps> = ({
  report,
  onUpdate,
}) => {
  const [editMode, setEditMode] = useState(false);
  const [editedReport, setEditedReport] = useState(report);
  const dispatch = useAppDispatch();

  const getStatusColor = (status: string) => {
    switch (status) {
      case 'fully_produced':
        return 'success';
      case 'partially_produced':
        return 'warning';
      case 'not_produced':
        return 'error';
      default:
        return 'default';
    }
  };

  const handleDownload = async () => {
    // Implementation for downloading report
    try {
      const response = await fetch(`/api/discovery/reports/${report.id}/download`);
      const blob = await response.blob();
      const url = window.URL.createObjectURL(blob);
      const a = document.createElement('a');
      a.href = url;
      a.download = `deficiency_report_${report.production_batch}.pdf`;
      a.click();
    } catch (error) {
      console.error('Failed to download report:', error);
    }
  };

  const renderEvidence = (evidence: EvidenceItem[]) => {
    return evidence.map((item, idx) => (
      <Box key={idx} sx={{ mt: 1, p: 1, bgcolor: 'grey.100', borderRadius: 1 }}>
        <Typography variant="body2" fontWeight="bold">
          {item.document_title} ({item.bates_range})
        </Typography>
        <Typography
          variant="body2"
          sx={{ mt: 0.5, p: 1, bgcolor: '#90EE90', borderRadius: 1 }}
        >
          "{item.quoted_text}"
        </Typography>
        <Typography variant="caption" color="text.secondary">
          Confidence: {item.confidence_score}%
        </Typography>
      </Box>
    ));
  };

  return (
    <Box>
      <Paper sx={{ p: 3, mb: 3 }}>
        <Box display="flex" justifyContent="space-between" alignItems="center">
          <Box>
            <Typography variant="h5">Discovery Deficiency Analysis</Typography>
            <Typography variant="subtitle1" color="text.secondary">
              Production Batch: {report.production_batch}
            </Typography>
            <Typography variant="caption" color="text.secondary">
              Generated: {new Date(report.generated_at).toLocaleString()}
            </Typography>
          </Box>
          <Box>
            <IconButton onClick={() => setEditMode(!editMode)}>
              <EditIcon />
            </IconButton>
            <Button
              variant="contained"
              startIcon={<DownloadIcon />}
              onClick={handleDownload}
              sx={{ ml: 1 }}
            >
              Download Report
            </Button>
          </Box>
        </Box>
        
        <Box sx={{ mt: 3 }}>
          <Typography variant="body2" gutterBottom>
            Overall Completeness
          </Typography>
          <LinearProgress
            variant="determinate"
            value={report.overall_completeness}
            sx={{ height: 10, borderRadius: 5 }}
          />
          <Typography variant="body2" sx={{ mt: 1 }}>
            {report.overall_completeness.toFixed(1)}% Complete
          </Typography>
        </Box>
      </Paper>

      {report.analyses.map((analysis) => (
        <Accordion key={analysis.request_number} defaultExpanded>
          <AccordionSummary expandIcon={<ExpandMoreIcon />}>
            <Box display="flex" alignItems="center" width="100%">
              <Typography variant="h6" sx={{ flexGrow: 1 }}>
                Request {analysis.request_number}
              </Typography>
              <Chip
                label={analysis.status.replace('_', ' ').toUpperCase()}
                color={getStatusColor(analysis.status)}
                size="small"
                sx={{ mr: 2 }}
              />
              <Typography variant="caption" color="text.secondary">
                Confidence: {analysis.confidence}%
              </Typography>
            </Box>
          </AccordionSummary>
          <AccordionDetails>
            <RequestAnalysisView
              analysis={analysis}
              editable={editMode}
              onUpdate={(updated) => {
                // Handle update
              }}
            />
          </AccordionDetails>
        </Accordion>
      ))}
    </Box>
  );
};
```

#### Task 4.2: Integrate with Discovery Processing
Update `DiscoveryProcessing.tsx` to trigger deficiency analysis:
```typescript
// Add to existing discovery processing completion handler
useEffect(() => {
  if (processingComplete && rfpFile && defenseResponseFile) {
    // Automatically trigger deficiency analysis
    dispatch(startDeficiencyAnalysis({
      rfp_document_id: rfpFile.id,
      defense_response_id: defenseResponseFile.id,
      production_batch: currentProductionBatch,
      processing_id: processingId
    }));
  }
}, [processingComplete, rfpFile, defenseResponseFile]);
```

### Phase 5: Testing and Validation

#### Task 5.1: Create Unit Tests
Create `src/ai_agents/tests/test_deficiency_analyzer.py`:
```python
import pytest
from unittest.mock import Mock, patch
from ..deficiency_analyzer import DeficiencyAnalyzer
from ...models.deficiency_models import ProductionStatus

@pytest.mark.asyncio
async def test_production_filtering():
    """Ensure searches are filtered to production batch only"""
    analyzer = DeficiencyAnalyzer("test_case")
    
    with patch.object(analyzer.vector_store, 'hybrid_search') as mock_search:
        await analyzer._search_production_documents(
            query="test query",
            production_batch="PROD_001"
        )
        
        # Verify filter was applied
        call_args = mock_search.call_args
        filter_arg = call_args.kwargs['query_filter']
        
        # Check that production_batch filter is present
        assert any(
            cond.key == "metadata.production_batch" and 
            cond.match.value == "PROD_001"
            for cond in filter_arg.must
        )

@pytest.mark.asyncio
async def test_deficiency_detection():
    """Test accurate deficiency detection"""
    analyzer = DeficiencyAnalyzer("test_case")
    
    # Mock search results
    mock_results = []  # No documents found
    
    with patch.object(analyzer, '_search_production_documents', return_value=mock_results):
        analysis = await analyzer._analyze_single_request(
            request_number=1,
            request_text="All training materials related to safety",
            response_text="Responsive documents produced",
            production_batch="PROD_001",
            processing_id="test_123"
        )
        
        assert analysis.status == ProductionStatus.NOT_PRODUCED
        assert len(analysis.deficiencies) > 0
```

## Validation Gates

### Backend Validation
```bash
# 1. Syntax and style check
cd /mnt/d/jrl/GitHub\ Repos/local-ai/Clerk
python3 -m ruff check --fix src/

# 2. Type checking
python3 -m mypy src/ai_agents/deficiency_analyzer.py

# 3. Run unit tests
python3 -m pytest src/ai_agents/tests/test_deficiency_analyzer.py -v

# 4. Integration test
python3 test_deficiency_analysis.py
```

### Frontend Validation
```bash
# 1. TypeScript compilation
cd frontend
npm run type-check

# 2. Linting
npm run lint

# 3. Component tests
npm test DeficiencyReportViewer

# 4. Build check
npm run build
```

### End-to-End Validation
```python
# Create test_deficiency_analysis.py
import asyncio
from src.ai_agents.deficiency_analyzer import DeficiencyAnalyzer

async def test_full_flow():
    """Test complete deficiency analysis flow"""
    analyzer = DeficiencyAnalyzer("test_case")
    
    # Test with sample data
    report = await analyzer.analyze_discovery_deficiencies(
        rfp_document_id="rfp_123",
        defense_response_id="response_456",
        production_batch="PROD_001",
        processing_id="proc_789"
    )
    
    assert report.case_name == "test_case"
    assert len(report.analyses) > 0
    print(f"✓ Generated report with {len(report.analyses)} analyses")
    print(f"✓ Overall completeness: {report.overall_completeness}%")

if __name__ == "__main__":
    asyncio.run(test_full_flow())
```

## Critical Context and Patterns

### 1. **Production Filtering Implementation**
The MOST CRITICAL aspect is filtering searches to current production only:
```python
# ALWAYS use this pattern for searches
filter = models.Filter(
    must=[
        models.FieldCondition(
            key="case_name",
            match=models.MatchValue(value=case_name)
        ),
        models.FieldCondition(
            key="metadata.production_batch",  # Nested field
            match=models.MatchValue(value=production_batch)
        )
    ]
)
```

### 2. **WebSocket Events**
Follow the established pattern for real-time updates:
- Event names: `discovery:deficiency_*`
- Always include `processingId` and `caseId`
- Emit to case-specific rooms: `f'case_{case_name}'`

### 3. **Error Handling**
- Never let exceptions bubble up to users
- Always emit error events on failure
- Log detailed errors for debugging
- Provide user-friendly error messages

### 4. **Case Isolation**
- Every database query must include case_name filter
- Use CaseContext from middleware for validation
- Never allow cross-case data access

### 5. **AI Agent Guidelines**
```python
# Always include in system prompts
"DO NOT make assumptions. Only report what you find with evidence."
"Provide specific quotes and document references."
"Use confidence scores to indicate certainty."
```

## External Documentation References

1. **Qdrant Filtering**: https://qdrant.tech/documentation/concepts/filtering/
2. **Pydantic AI Agents**: https://ai.pydantic.dev/agents/
3. **FastAPI Background Tasks**: https://fastapi.tiangolo.com/tutorial/background-tasks/
4. **Socket.IO Python**: https://python-socketio.readthedocs.io/en/latest/server.html
5. **Material-UI Components**: https://mui.com/material-ui/react-accordion/

## Implementation Order

1. Core Infrastructure
   - [ ] Create deficiency models
   - [ ] Implement DeficiencyAnalyzer class
   - [ ] Add production-scoped search methods
   - [ ] Create unit tests

2. API Integration
   - [ ] Add analysis endpoint
   - [ ] Implement background processing
   - [ ] Add WebSocket events
   - [ ] Create integration tests

3. Frontend Development
   - [ ] Create DeficiencyReportViewer component
   - [ ] Add Redux actions/reducers
   - [ ] Integrate with discovery flow
   - [ ] Implement download functionality

4. Testing and Polish
   - [ ] End-to-end testing
   - [ ] Performance optimization
   - [ ] Error handling improvements
   - [ ] Documentation

## Common Pitfalls to Avoid

1. **Forgetting Production Filter**: Always filter by production_batch
2. **Case Mixing**: Never allow data from different cases to mix
3. **Blocking UI**: Use background tasks for long operations
4. **Over-promising**: AI should only report what it finds
5. **Missing WebSocket Events**: Users need real-time feedback

## Success Metrics

- [ ] Searches return only current production documents
- [ ] Reports accurately identify deficiencies
- [ ] Processing completes within 2 minutes for typical productions
- [ ] UI updates in real-time during analysis
- [ ] Reports are downloadable and editable

## Confidence Score: 8.5/10

High confidence due to:
- Clear existing patterns to follow
- Comprehensive research on document structure
- Detailed implementation blueprint
- Strong validation gates

Minor uncertainty on:
- Exact RFP parsing complexity
- Performance with very large productions

This PRP provides a complete roadmap for implementing the discovery deficiency analysis feature with all necessary context for successful one-pass implementation.