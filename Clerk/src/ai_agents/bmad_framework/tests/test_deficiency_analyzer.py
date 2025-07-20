"""
Tests for deficiency analyzer agent.
"""

import pytest
from unittest.mock import Mock, AsyncMock, patch
from pathlib import Path

from src.ai_agents.bmad_framework import AgentLoader, AgentExecutor
from src.ai_agents.bmad_framework.exceptions import AgentLoadError, TaskExecutionError
from src.ai_agents.bmad_framework.security import AgentSecurityContext


class TestDeficiencyAnalyzerAgent:
    """Test suite for deficiency analyzer agent."""

    @pytest.fixture
    def mock_case_context(self):
        """Create mock case context."""
        context = Mock()
        context.case_id = "case-123"
        context.case_name = "Smith_v_Jones_2024"
        context.user_id = "user-456"
        context.permissions = ["read", "write"]
        return context

    @pytest.fixture
    def mock_security_context(self, mock_case_context):
        """Create mock security context."""
        return AgentSecurityContext(
            case_context=mock_case_context, agent_id="deficiency-analyzer"
        )

    @pytest.fixture
    async def agent_loader(self):
        """Create agent loader instance."""
        return AgentLoader()

    @pytest.fixture
    async def agent_executor(self):
        """Create agent executor instance."""
        return AgentExecutor()

    async def test_agent_loading_success(self, agent_loader):
        """Test successful agent loading."""
        # Load deficiency analyzer agent
        agent_def = await agent_loader.load_agent("deficiency-analyzer")

        # Verify agent structure
        assert agent_def["agent"]["id"] == "deficiency-analyzer"
        assert agent_def["agent"]["name"] == "Discovery Analyzer"
        assert agent_def["agent"]["title"] == "Legal Discovery Analysis Specialist"
        assert agent_def["agent"]["icon"] == "⚖️"

        # Verify commands
        commands = [cmd.split(":")[0] for cmd in agent_def["commands"]]
        assert "help" in commands
        assert "analyze" in commands
        assert "search" in commands
        assert "categorize" in commands
        assert "report" in commands
        assert "evidence" in commands
        assert "exit" in commands

        # Verify dependencies
        assert "analyze-rtp.md" in agent_def["dependencies"]["tasks"]
        assert "search-production.md" in agent_def["dependencies"]["tasks"]
        assert "categorize-compliance.md" in agent_def["dependencies"]["tasks"]
        assert "generate-evidence-chunks.md" in agent_def["dependencies"]["tasks"]

        assert "deficiency-report-tmpl.yaml" in agent_def["dependencies"]["templates"]
        assert "evidence-citation-tmpl.yaml" in agent_def["dependencies"]["templates"]

    async def test_agent_loading_not_found(self, agent_loader):
        """Test agent loading with non-existent agent."""
        with pytest.raises(AgentLoadError) as exc_info:
            await agent_loader.load_agent("non-existent-agent")

        assert "not found" in str(exc_info.value).lower()

    async def test_analyze_command_execution(
        self, agent_executor, agent_loader, mock_security_context
    ):
        """Test analyze command execution."""
        # Load agent
        agent_def = await agent_loader.load_agent("deficiency-analyzer")

        # Mock integration points
        with patch(
            "src.ai_agents.bmad_framework.integration.ClerkIntegration"
        ) as mock_integration:
            mock_clerk = AsyncMock()
            mock_integration.return_value = mock_clerk

            # Mock RTP parser
            mock_clerk.get_rtp_parser.return_value.parse_rtp_document = AsyncMock(
                return_value=[
                    {"request_number": "1", "request_text": "All contracts"},
                    {"request_number": "2", "request_text": "All emails"},
                ]
            )

            # Mock vector store search
            mock_clerk.search_vector_store = AsyncMock(
                return_value=[
                    {"document_id": "doc-1", "relevance_score": 0.85},
                    {"document_id": "doc-2", "relevance_score": 0.72},
                ]
            )

            # Execute analyze command
            result = await agent_executor.execute_command(
                agent_def=agent_def,
                command="analyze",
                case_name="Smith_v_Jones_2024",
                security_context=mock_security_context,
                parameters={
                    "production_id": "prod-123",
                    "rtp_document_id": "rtp-456",
                    "oc_response_id": None,
                    "options": {"confidence_threshold": 0.7},
                },
            )

            # Verify result
            assert result["success"] is True
            assert "processing_id" in result
            assert result["total_requests"] == 2

    async def test_search_command_execution(
        self, agent_executor, agent_loader, mock_security_context
    ):
        """Test search command execution."""
        # Load agent
        agent_def = await agent_loader.load_agent("deficiency-analyzer")

        # Mock search functionality
        with patch("src.vector_storage.qdrant_store.QdrantVectorStore") as mock_store:
            mock_instance = AsyncMock()
            mock_store.return_value = mock_instance

            mock_instance.hybrid_search = AsyncMock(
                return_value=[
                    {
                        "document_id": "doc-1",
                        "chunk_text": "Contract negotiations...",
                        "relevance_score": 0.92,
                        "metadata": {"page_number": 5},
                    }
                ]
            )

            # Execute search command
            result = await agent_executor.execute_command(
                agent_def=agent_def,
                command="search",
                case_name="Smith_v_Jones_2024",
                security_context=mock_security_context,
                parameters={
                    "query": "contract negotiations",
                    "filters": {},
                    "limit": 50,
                    "offset": 0,
                },
            )

            # Verify result
            assert result["success"] is True
            assert len(result["results"]) == 1
            assert result["results"][0]["relevance_score"] == 0.92

    async def test_categorize_command_execution(
        self, agent_executor, agent_loader, mock_security_context
    ):
        """Test categorize command execution."""
        # Load agent
        agent_def = await agent_loader.load_agent("deficiency-analyzer")

        # Execute categorize command
        with patch(
            "src.ai_agents.bmad_framework.agent_executor.TaskExecutor"
        ) as mock_task:
            mock_task_instance = AsyncMock()
            mock_task.return_value = mock_task_instance

            mock_task_instance.execute = AsyncMock(
                return_value={
                    "classification": "partially_produced",
                    "confidence_score": 0.75,
                    "evidence_summary": "Found 3 relevant documents",
                    "recommendation": "Request clarification on date range",
                }
            )

            result = await agent_executor.execute_command(
                agent_def=agent_def,
                command="categorize",
                case_name="Smith_v_Jones_2024",
                security_context=mock_security_context,
                parameters={
                    "request_number": "RFP No. 1",
                    "request_text": "All contracts...",
                    "search_results": ["result-1", "result-2"],
                    "oc_response_text": "Documents produced",
                },
            )

            # Verify result
            assert result["classification"] == "partially_produced"
            assert result["confidence_score"] == 0.75

    async def test_command_routing(
        self, agent_executor, agent_loader, mock_security_context
    ):
        """Test command routing to appropriate handlers."""
        # Load agent
        agent_def = await agent_loader.load_agent("deficiency-analyzer")

        # Test invalid command
        with pytest.raises(TaskExecutionError) as exc_info:
            await agent_executor.execute_command(
                agent_def=agent_def,
                command="invalid_command",
                case_name="Smith_v_Jones_2024",
                security_context=mock_security_context,
                parameters={},
            )

        assert "not found" in str(exc_info.value).lower()

    async def test_security_context_enforcement(self, agent_executor, agent_loader):
        """Test security context is enforced."""
        # Load agent
        agent_def = await agent_loader.load_agent("deficiency-analyzer")

        # Create context without write permission
        mock_context = Mock()
        mock_context.case_id = "case-123"
        mock_context.case_name = "Smith_v_Jones_2024"
        mock_context.permissions = ["read"]  # No write permission

        security_context = AgentSecurityContext(
            case_context=mock_context, agent_id="deficiency-analyzer"
        )

        # Try to execute analyze (requires write)
        with pytest.raises(PermissionError) as exc_info:
            await agent_executor.execute_command(
                agent_def=agent_def,
                command="analyze",  # Requires write permission
                case_name="Smith_v_Jones_2024",
                security_context=security_context,
                parameters={},
            )

        assert "permission" in str(exc_info.value).lower()

    async def test_agent_dependencies_loading(self, agent_loader):
        """Test agent dependencies are properly loaded."""
        # Load agent
        agent_def = await agent_loader.load_agent("deficiency-analyzer")

        # Check task dependencies exist
        tasks_dir = Path("Clerk/src/ai_agents/bmad_framework/tasks")
        for task in agent_def["dependencies"]["tasks"]:
            task_path = tasks_dir / task
            assert task_path.exists(), f"Task {task} not found"

        # Check template dependencies exist
        templates_dir = Path("Clerk/src/ai_agents/bmad_framework/templates")
        for template in agent_def["dependencies"]["templates"]:
            template_path = templates_dir / template
            assert template_path.exists(), f"Template {template} not found"

        # Check data dependencies exist
        data_dir = Path("Clerk/src/ai_agents/bmad_framework/data")
        for data_file in agent_def["dependencies"]["data"]:
            data_path = data_dir / data_file
            assert data_path.exists(), f"Data file {data_file} not found"

    async def test_agent_customization_field(self, agent_loader):
        """Test agent customization field is properly parsed."""
        # Load agent
        agent_def = await agent_loader.load_agent("deficiency-analyzer")

        # Check customization field
        customization = agent_def["agent"].get("customization", "")
        assert "API-first execution mode" in customization
        assert "case_name required" in customization
        assert "WebSocket progress tracking" in customization
        assert "confidence scoring" in customization

    async def test_concurrent_command_execution(
        self, agent_executor, agent_loader, mock_security_context
    ):
        """Test concurrent command execution."""
        import asyncio

        # Load agent
        agent_def = await agent_loader.load_agent("deficiency-analyzer")

        # Mock task execution
        with patch(
            "src.ai_agents.bmad_framework.agent_executor.TaskExecutor"
        ) as mock_task:
            mock_task_instance = AsyncMock()
            mock_task.return_value = mock_task_instance

            mock_task_instance.execute = AsyncMock(
                side_effect=[
                    {"success": True, "result": "search_1"},
                    {"success": True, "result": "search_2"},
                    {"success": True, "result": "search_3"},
                ]
            )

            # Execute multiple searches concurrently
            tasks = [
                agent_executor.execute_command(
                    agent_def=agent_def,
                    command="search",
                    case_name="Smith_v_Jones_2024",
                    security_context=mock_security_context,
                    parameters={"query": f"query_{i}"},
                )
                for i in range(3)
            ]

            results = await asyncio.gather(*tasks)

            # Verify all completed
            assert len(results) == 3
            assert all(r["success"] for r in results)
