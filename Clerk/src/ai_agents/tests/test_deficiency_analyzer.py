"""
Unit tests for DeficiencyAnalyzer.

Tests the discovery deficiency analysis functionality with focus on:
- Production-scoped filtering
- Accurate deficiency detection
- Case isolation
- Helper method functionality
"""

import pytest
from unittest.mock import Mock, patch, AsyncMock
from datetime import datetime
from typing import List

from ..deficiency_analyzer import DeficiencyAnalyzer, SearchStrategy
from ...models.deficiency_models import ProductionStatus, RequestAnalysis, EvidenceItem
from ...vector_storage.qdrant_store import SearchResult


@pytest.fixture
def analyzer():
    """Create a DeficiencyAnalyzer instance for testing."""
    return DeficiencyAnalyzer("test_case")


@pytest.fixture
def mock_documents():
    """Create mock documents for testing."""
    return [
        SearchResult(
            id="doc1",
            case_name="test_case",
            document_id="hash1",
            content="This manual covers safety training procedures...",
            score=0.95,
            metadata={
                "file_name": "training_manual.pdf",
                "title": "Safety Training Manual",
                "document_type": "manual",
                "production_batch": "PROD_001",
                "bates_range": "DEF00001-DEF00050"
            }
        ),
        SearchResult(
            id="doc2", 
            case_name="test_case",
            document_id="hash2",
            content="Our safety policy requires all employees...",
            score=0.92,
            metadata={
                "file_name": "policy.pdf",
                "title": "Company Safety Policy",
                "document_type": "policy",
                "production_batch": "PROD_001",
                "bates_range": "DEF00051-DEF00075"
            }
        )
    ]


@pytest.mark.asyncio
async def test_production_filtering(analyzer):
    """Ensure searches are filtered to production batch only."""
    with patch.object(analyzer.vector_store, 'search_documents') as mock_search:
        mock_search.return_value = []
        
        # Mock embedding generation
        with patch('src.ai_agents.deficiency_analyzer.EmbeddingGenerator') as mock_embedding:
            mock_generator = Mock()
            mock_generator.generate_embedding.return_value = ([0.1] * 1536, 10)
            mock_embedding.return_value = mock_generator
            
            await analyzer._search_production_documents(
                query="test query",
                production_batch="PROD_001"
            )
            
            # Verify filter was applied
            call_args = mock_search.call_args
            filters = call_args.kwargs['filters']
            
            # Check that production_batch filter is present
            assert filters is not None
            assert "metadata.production_batch" in filters
            assert filters["metadata.production_batch"] == "PROD_001"


@pytest.mark.asyncio
async def test_deficiency_detection_not_produced(analyzer):
    """Test accurate deficiency detection when documents not produced."""
    # Mock search to return no results
    with patch.object(analyzer, '_search_production_documents', return_value=[]):
        # Mock search strategy
        with patch.object(analyzer.search_agent, 'run') as mock_search_agent:
            mock_search_agent.return_value = AsyncMock(
                data=SearchStrategy(
                    queries=["safety training materials"],
                    search_approach="keyword",
                    reasoning="Searching for safety training documents"
                )
            )
            
            # Mock analysis agent
            with patch.object(analyzer.analysis_agent, 'run') as mock_analysis:
                mock_analysis.return_value = AsyncMock(
                    data=RequestAnalysis(
                        request_number=1,
                        request_text="All training materials related to safety",
                        response_text="Responsive documents produced",
                        status=ProductionStatus.NOT_PRODUCED,
                        confidence=95.0,
                        evidence=[],
                        deficiencies=["No safety training materials found in production"],
                        search_queries_used=[]
                    )
                )
                
                analysis = await analyzer._analyze_single_request(
                    request_number=1,
                    request_text="All training materials related to safety",
                    response_text="Responsive documents produced",
                    production_batch="PROD_001",
                    processing_id="test_123"
                )
                
                assert analysis.status == ProductionStatus.NOT_PRODUCED
                assert len(analysis.deficiencies) > 0
                assert analysis.confidence == 95.0


@pytest.mark.asyncio
async def test_deficiency_detection_fully_produced(analyzer, mock_documents):
    """Test detection when documents are fully produced."""
    # Mock search to return relevant documents
    with patch.object(analyzer, '_search_production_documents', return_value=mock_documents):
        # Mock search strategy
        with patch.object(analyzer.search_agent, 'run') as mock_search_agent:
            mock_search_agent.return_value = AsyncMock(
                data=SearchStrategy(
                    queries=["safety training", "safety manual"],
                    search_approach="keyword",
                    reasoning="Searching for safety-related documents"
                )
            )
            
            # Mock analysis agent
            with patch.object(analyzer.analysis_agent, 'run') as mock_analysis:
                mock_analysis.return_value = AsyncMock(
                    data=RequestAnalysis(
                        request_number=1,
                        request_text="All safety training materials",
                        response_text=None,
                        status=ProductionStatus.FULLY_PRODUCED,
                        confidence=90.0,
                        evidence=[
                            EvidenceItem(
                                document_id="doc1",
                                document_title="Safety Training Manual",
                                bates_range="DEF00001-DEF00050",
                                quoted_text="This manual covers safety training procedures",
                                confidence_score=95.0
                            )
                        ],
                        deficiencies=[],
                        search_queries_used=[]
                    )
                )
                
                analysis = await analyzer._analyze_single_request(
                    request_number=1,
                    request_text="All safety training materials",
                    response_text=None,
                    production_batch="PROD_001",
                    processing_id="test_123"
                )
                
                assert analysis.status == ProductionStatus.FULLY_PRODUCED
                assert len(analysis.evidence) > 0
                assert len(analysis.deficiencies) == 0


def test_case_name_validation():
    """Test case name validation."""
    # Valid case name
    analyzer = DeficiencyAnalyzer("valid_case")
    assert analyzer.case_name == "valid_case"
    
    # Invalid case names
    with pytest.raises(ValueError):
        DeficiencyAnalyzer("")
    
    with pytest.raises(ValueError):
        DeficiencyAnalyzer(None)


def test_deduplication(analyzer, mock_documents):
    """Test document deduplication."""
    # Create duplicate documents
    duplicated = mock_documents + [mock_documents[0]]  # Add duplicate of first doc
    
    unique = analyzer._deduplicate_results(duplicated)
    
    assert len(unique) == 2  # Should only have 2 unique documents
    assert all(doc.document_id in ["hash1", "hash2"] for doc in unique)


def test_completeness_calculation(analyzer):
    """Test overall completeness calculation."""
    # All fully produced
    analyses = [
        RequestAnalysis(
            request_number=i,
            request_text=f"Request {i}",
            status=ProductionStatus.FULLY_PRODUCED,
            confidence=90.0
        )
        for i in range(1, 4)
    ]
    
    completeness = analyzer._calculate_completeness(analyses)
    assert completeness == 100.0
    
    # Mixed production
    analyses[1].status = ProductionStatus.NOT_PRODUCED
    completeness = analyzer._calculate_completeness(analyses)
    assert completeness == pytest.approx(66.67, rel=0.1)
    
    # Empty analyses
    assert analyzer._calculate_completeness([]) == 0.0


def test_format_documents_for_analysis(analyzer, mock_documents):
    """Test document formatting for AI analysis."""
    formatted = analyzer._format_documents_for_analysis(mock_documents)
    
    # Check that both documents are included
    assert "Safety Training Manual" in formatted
    assert "Company Safety Policy" in formatted
    assert "DEF00001-DEF00050" in formatted
    assert "DEF00051-DEF00075" in formatted
    assert "Score: 0.950" in formatted  # Check score formatting
    assert "Score: 0.920" in formatted
    
    # Test with no documents
    formatted_empty = analyzer._format_documents_for_analysis([])
    assert formatted_empty == "No documents found"
    
    # Test with many documents (should limit to 10)
    many_docs = mock_documents * 10  # 20 documents
    formatted_many = analyzer._format_documents_for_analysis(many_docs)
    assert "... and 10 more documents" in formatted_many


@pytest.mark.asyncio
async def test_emit_progress(analyzer):
    """Test WebSocket progress emission."""
    with patch('src.ai_agents.deficiency_analyzer.sio.emit') as mock_emit:
        await analyzer._emit_progress("proc_123", 5, 10)
        
        mock_emit.assert_called_once()
        call_args = mock_emit.call_args
        
        assert call_args[0][0] == 'discovery:deficiency_analysis_progress'
        assert call_args[0][1]['processingId'] == "proc_123"
        assert call_args[0][1]['currentRequest'] == 5
        assert call_args[0][1]['totalRequests'] == 10
        assert call_args[0][1]['progressPercent'] == 50.0
        assert call_args[1]['room'] == 'case_test_case'


@pytest.mark.asyncio
async def test_full_analysis_flow(analyzer):
    """Test the complete analysis flow."""
    # Mock RFP extraction
    with patch.object(analyzer, '_extract_rfp_requests') as mock_rfp:
        mock_rfp.return_value = {
            1: "All safety training materials",
            2: "All incident reports from 2023"
        }
        
        # Mock defense response extraction
        with patch.object(analyzer, '_extract_defense_responses') as mock_defense:
            mock_defense.return_value = {
                1: "See responsive documents",
                2: "No responsive documents"
            }
            
            # Mock single request analysis
            with patch.object(analyzer, '_analyze_single_request') as mock_analyze:
                mock_analyze.side_effect = [
                    RequestAnalysis(
                        request_number=1,
                        request_text="All safety training materials",
                        response_text="See responsive documents",
                        status=ProductionStatus.FULLY_PRODUCED,
                        confidence=90.0
                    ),
                    RequestAnalysis(
                        request_number=2,
                        request_text="All incident reports from 2023",
                        response_text="No responsive documents",
                        status=ProductionStatus.NOT_PRODUCED,
                        confidence=95.0
                    )
                ]
                
                # Mock progress emission
                with patch.object(analyzer, '_emit_progress'):
                    report = await analyzer.analyze_discovery_deficiencies(
                        rfp_document_id="rfp_123",
                        defense_response_id="defense_456",
                        production_batch="PROD_001",
                        processing_id="proc_789"
                    )
                    
                    assert report.case_name == "test_case"
                    assert report.production_batch == "PROD_001"
                    assert len(report.analyses) == 2
                    assert report.overall_completeness == 50.0  # 1 of 2 produced