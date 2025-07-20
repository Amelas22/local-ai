"""
Tests for deficiency analysis tasks.
"""

import pytest
from unittest.mock import Mock, AsyncMock, patch, MagicMock
from datetime import datetime
from uuid import uuid4

from src.ai_agents.bmad_framework.agent_executor import TaskExecutor
from src.ai_agents.bmad_framework.exceptions import TaskExecutionError
from src.models.deficiency_models import DeficiencyItem


class TestAnalysisTasks:
    """Test suite for analysis task execution."""
    
    @pytest.fixture
    def task_executor(self):
        """Create task executor instance."""
        return TaskExecutor()
    
    @pytest.fixture
    def mock_case_context(self):
        """Create mock case context."""
        context = Mock()
        context.case_name = "Test_Case_2024"
        context.case_id = "case-123"
        return context
    
    @pytest.fixture
    def mock_rtp_parser(self):
        """Create mock RTP parser."""
        with patch('src.document_processing.rtp_parser.RTPParser') as mock:
            parser = Mock()
            parser.parse_rtp_document = AsyncMock()
            mock.return_value = parser
            yield parser
    
    @pytest.fixture
    def mock_qdrant_store(self):
        """Create mock Qdrant store."""
        with patch('src.vector_storage.qdrant_store.QdrantVectorStore') as mock:
            store = AsyncMock()
            mock.return_value = store
            yield store
    
    async def test_analyze_rtp_task_success(self, task_executor, mock_case_context, mock_rtp_parser):
        """Test successful RTP analysis task execution."""
        # Mock RTP parsing results
        mock_rtp_parser.parse_rtp_document.return_value = [
            {
                "request_number": "1",
                "request_text": "All documents relating to the contract",
                "category": "documents",
                "page_range": [2, 3]
            },
            {
                "request_number": "2",
                "request_text": "All emails between parties",
                "category": "communications",
                "page_range": [3, 4]
            }
        ]
        
        # Execute task
        result = await task_executor.execute_task(
            task_name="analyze-rtp",
            context={
                "case_name": mock_case_context.case_name,
                "rtp_document_path": "/path/to/rtp.pdf"
            }
        )
        
        # Verify results
        assert result["success"] is True
        assert result["total_requests"] == 2
        assert len(result["requests"]) == 2
        assert result["requests"][0]["request_number"] == "1"
        
        # Verify parser was called correctly
        mock_rtp_parser.parse_rtp_document.assert_called_once_with("/path/to/rtp.pdf")
    
    async def test_analyze_rtp_task_no_requests(self, task_executor, mock_case_context, mock_rtp_parser):
        """Test RTP analysis with no requests found."""
        # Mock empty parsing results
        mock_rtp_parser.parse_rtp_document.return_value = []
        
        # Execute task - should fail
        with pytest.raises(TaskExecutionError) as exc_info:
            await task_executor.execute_task(
                task_name="analyze-rtp",
                context={
                    "case_name": mock_case_context.case_name,
                    "rtp_document_path": "/path/to/rtp.pdf"
                }
            )
        
        assert "no requests found" in str(exc_info.value).lower()
    
    async def test_search_production_task_success(self, task_executor, mock_case_context, mock_qdrant_store):
        """Test successful production search task."""
        # Mock search results
        mock_qdrant_store.hybrid_search.return_value = [
            {
                "document_id": "doc-1",
                "chunk_text": "This contract specifies...",
                "relevance_score": 0.92,
                "metadata": {
                    "page_number": 5,
                    "document_name": "Contract_2022.pdf"
                }
            },
            {
                "document_id": "doc-2",
                "chunk_text": "The agreement states...",
                "relevance_score": 0.85,
                "metadata": {
                    "page_number": 12,
                    "document_name": "Agreement_2022.pdf"
                }
            }
        ]
        
        # Execute task
        result = await task_executor.execute_task(
            task_name="search-production",
            context={
                "case_name": mock_case_context.case_name,
                "query": "contract agreement terms",
                "limit": 50
            }
        )
        
        # Verify results
        assert result["success"] is True
        assert result["total_results"] == 2
        assert len(result["results"]) == 2
        assert result["results"][0]["relevance_score"] == 0.92
        
        # Verify search was called
        mock_qdrant_store.hybrid_search.assert_called_once()
        call_args = mock_qdrant_store.hybrid_search.call_args
        assert call_args[1]["case_name"] == mock_case_context.case_name
        assert call_args[1]["query_text"] == "contract agreement terms"
    
    async def test_search_production_with_filters(self, task_executor, mock_case_context, mock_qdrant_store):
        """Test production search with date and type filters."""
        # Mock filtered results
        mock_qdrant_store.hybrid_search.return_value = [
            {
                "document_id": "doc-3",
                "chunk_text": "Email regarding contract",
                "relevance_score": 0.88,
                "metadata": {
                    "document_type": "email",
                    "date": "2022-03-15"
                }
            }
        ]
        
        # Execute task with filters
        result = await task_executor.execute_task(
            task_name="search-production",
            context={
                "case_name": mock_case_context.case_name,
                "query": "contract negotiations",
                "filters": {
                    "document_types": ["email", "letter"],
                    "date_range": {
                        "start": "2022-01-01",
                        "end": "2022-12-31"
                    }
                },
                "limit": 20
            }
        )
        
        # Verify filtered results
        assert result["success"] is True
        assert len(result["results"]) == 1
        assert result["results"][0]["metadata"]["document_type"] == "email"
    
    async def test_categorize_compliance_task_fully_produced(self, task_executor, mock_case_context):
        """Test categorization for fully produced request."""
        # Execute task with high relevance results
        result = await task_executor.execute_task(
            task_name="categorize-compliance",
            context={
                "case_name": mock_case_context.case_name,
                "request_number": "1",
                "request_text": "All contracts related to Project X",
                "search_results": [
                    {"relevance_score": 0.95, "document_type": "contract"},
                    {"relevance_score": 0.92, "document_type": "contract"},
                    {"relevance_score": 0.88, "document_type": "contract"}
                ],
                "oc_response_text": "All responsive documents have been produced"
            }
        )
        
        # Verify categorization
        assert result["classification"] == "fully_produced"
        assert result["confidence_score"] >= 0.8
        assert "fully satisfy request" in result["evidence_summary"]
    
    async def test_categorize_compliance_task_partially_produced(self, task_executor, mock_case_context):
        """Test categorization for partially produced request."""
        # Execute task with mixed results
        result = await task_executor.execute_task(
            task_name="categorize-compliance",
            context={
                "case_name": mock_case_context.case_name,
                "request_number": "2",
                "request_text": "All emails and contracts for 2022",
                "search_results": [
                    {"relevance_score": 0.85, "document_type": "contract"},
                    {"relevance_score": 0.72, "document_type": "contract"}
                    # Note: No emails found
                ],
                "oc_response_text": "Responsive documents produced"
            }
        )
        
        # Verify categorization
        assert result["classification"] == "partially_produced"
        assert 0.5 <= result["confidence_score"] < 0.8
        assert "missing" in result["evidence_summary"].lower()
    
    async def test_categorize_compliance_task_not_produced(self, task_executor, mock_case_context):
        """Test categorization for not produced request."""
        # Execute task with no results
        result = await task_executor.execute_task(
            task_name="categorize-compliance",
            context={
                "case_name": mock_case_context.case_name,
                "request_number": "3",
                "request_text": "All board meeting minutes",
                "search_results": [],  # No documents found
                "oc_response_text": "No production"
            }
        )
        
        # Verify categorization
        assert result["classification"] == "not_produced"
        assert result["confidence_score"] >= 0.7
        assert "no responsive documents found" in result["evidence_summary"].lower()
    
    async def test_categorize_compliance_task_no_responsive_docs(self, task_executor, mock_case_context):
        """Test categorization for legitimate no responsive documents."""
        # Execute task
        result = await task_executor.execute_task(
            task_name="categorize-compliance",
            context={
                "case_name": mock_case_context.case_name,
                "request_number": "4",
                "request_text": "All documents from 2025",  # Future date
                "search_results": [],
                "oc_response_text": "After diligent search, no responsive documents exist for the requested timeframe"
            }
        )
        
        # Verify categorization
        assert result["classification"] == "no_responsive_docs"
        assert result["confidence_score"] >= 0.6
        assert "legitimate absence" in result["evidence_summary"].lower()
    
    async def test_generate_evidence_chunks_task(self, task_executor, mock_case_context):
        """Test evidence chunk generation task."""
        # Mock search results with chunks
        search_results = [
            {
                "document_id": "doc-1",
                "document_name": "Contract_2022.pdf",
                "chunk_text": "The parties agree to the following terms...",
                "metadata": {
                    "page_number": 5,
                    "bates_start": "SMITH_001234",
                    "bates_end": "SMITH_001235",
                    "date": "2022-06-15",
                    "document_type": "contract"
                },
                "relevance_score": 0.92
            },
            {
                "document_id": "doc-2",
                "document_name": "Email_Chain.pdf",
                "chunk_text": "Please review the attached contract...",
                "metadata": {
                    "page_number": 1,
                    "bates_start": "SMITH_002345",
                    "date": "2022-06-10",
                    "document_type": "email"
                },
                "relevance_score": 0.85
            }
        ]
        
        # Execute task
        result = await task_executor.execute_task(
            task_name="generate-evidence-chunks",
            context={
                "case_name": mock_case_context.case_name,
                "search_results": search_results,
                "request_text": "All contracts and related communications"
            }
        )
        
        # Verify evidence chunks
        assert result["success"] is True
        assert result["total_chunks"] == 2
        assert len(result["evidence_chunks"]) == 2
        
        # Check first chunk
        chunk1 = result["evidence_chunks"][0]
        assert chunk1["document_id"] == "doc-1"
        assert chunk1["relevance_score"] == 0.92
        assert "SMITH_001234-001235" in chunk1["citation"]
        assert "page 5" in chunk1["citation"].lower()
        
        # Check second chunk
        chunk2 = result["evidence_chunks"][1]
        assert chunk2["document_id"] == "doc-2"
        assert chunk2["document_type"] == "email"
    
    async def test_task_execution_with_websocket_progress(self, task_executor, mock_case_context):
        """Test task execution emits WebSocket progress events."""
        # Mock WebSocket
        with patch('src.ai_agents.bmad_framework.websocket_progress.sio') as mock_sio:
            mock_sio.emit = AsyncMock()
            
            # Execute a task
            await task_executor.execute_task(
                task_name="analyze-rtp",
                context={
                    "case_name": mock_case_context.case_name,
                    "rtp_document_path": "/path/to/rtp.pdf"
                },
                progress_tracker={
                    "case_id": mock_case_context.case_id,
                    "agent_id": "deficiency-analyzer"
                }
            )
            
            # Verify WebSocket events were emitted
            assert mock_sio.emit.called
            
            # Check for task started event
            start_calls = [
                call for call in mock_sio.emit.call_args_list
                if call[0][0] == "agent:task_started"
            ]
            assert len(start_calls) > 0
    
    async def test_task_error_handling(self, task_executor, mock_case_context):
        """Test proper error handling in tasks."""
        # Test with missing required parameter
        with pytest.raises(TaskExecutionError) as exc_info:
            await task_executor.execute_task(
                task_name="analyze-rtp",
                context={
                    "case_name": mock_case_context.case_name
                    # Missing rtp_document_path
                }
            )
        
        assert "required parameter" in str(exc_info.value).lower()
        
        # Test with invalid task name
        with pytest.raises(TaskExecutionError) as exc_info:
            await task_executor.execute_task(
                task_name="invalid-task",
                context={"case_name": mock_case_context.case_name}
            )
        
        assert "task not found" in str(exc_info.value).lower()
    
    async def test_task_case_isolation(self, task_executor):
        """Test tasks enforce case isolation."""
        # Test without case_name
        with pytest.raises(TaskExecutionError) as exc_info:
            await task_executor.execute_task(
                task_name="search-production",
                context={
                    "query": "test query"
                    # Missing case_name
                }
            )
        
        assert "case_name required" in str(exc_info.value).lower()