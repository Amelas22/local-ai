"""
Unit tests for BMad framework agent executor.
"""

import pytest
from unittest.mock import Mock, AsyncMock, patch, MagicMock
from pathlib import Path
import tempfile

from src.ai_agents.bmad_framework.agent_executor import (
    AgentExecutor,
    ExecutionContext,
    ExecutionResult
)
from src.ai_agents.bmad_framework.agent_loader import AgentDefinition
from src.ai_agents.bmad_framework.security import AgentSecurityContext
from src.ai_agents.bmad_framework.exceptions import (
    TaskExecutionError,
    DependencyNotFoundError,
    ValidationError
)


class TestExecutionResult:
    """Test ExecutionResult dataclass."""
    
    def test_successful_result(self):
        """Test creating successful execution result."""
        result = ExecutionResult(
            success=True,
            command="test",
            result={"data": "value"}
        )
        
        assert result.success is True
        assert result.command == "test"
        assert result.result == {"data": "value"}
        assert result.error is None
        assert result.metadata == {}
    
    def test_failed_result(self):
        """Test creating failed execution result."""
        result = ExecutionResult(
            success=False,
            command="test",
            result=None,
            error="Test error",
            metadata={"error_type": "TestError"}
        )
        
        assert result.success is False
        assert result.error == "Test error"
        assert result.metadata["error_type"] == "TestError"


class TestAgentExecutor:
    """Test AgentExecutor functionality."""
    
    @pytest.fixture
    def mock_agent_def(self):
        """Create mock agent definition."""
        return AgentDefinition(
            id="test-agent",
            name="Test Agent",
            title="Test Agent Title",
            commands=[
                {"help": "Show help"},
                {"analyze": "Analyze data"},
                {"exit": "Exit agent"}
            ],
            tasks=["analyze-task.md"]
        )
    
    @pytest.fixture
    def mock_security_context(self):
        """Create mock security context."""
        case_context = Mock()
        case_context.case_id = "case-123"
        case_context.case_name = "Test_Case"
        case_context.user_id = "user-456"
        
        security_context = AgentSecurityContext(case_context, "test-agent")
        security_context.log_operation = Mock()
        
        return security_context
    
    @pytest.fixture
    def executor(self):
        """Create agent executor instance."""
        with tempfile.TemporaryDirectory() as temp_dir:
            executor = AgentExecutor(base_path=Path(temp_dir))
            yield executor
    
    @pytest.mark.asyncio
    async def test_execute_help_command(self, executor, mock_agent_def, mock_security_context):
        """Test executing built-in help command."""
        result = await executor.execute_command(
            agent_def=mock_agent_def,
            command="help",
            case_name="Test_Case",
            security_context=mock_security_context
        )
        
        assert result.success is True
        assert result.command == "help"
        assert "Available commands" in result.result
        assert "*help" in result.result
        assert "*analyze" in result.result
        assert result.metadata["handler"] == "builtin"
    
    @pytest.mark.asyncio
    async def test_execute_exit_command(self, executor, mock_agent_def, mock_security_context):
        """Test executing built-in exit command."""
        result = await executor.execute_command(
            agent_def=mock_agent_def,
            command="*exit",  # Test with * prefix
            case_name="Test_Case",
            security_context=mock_security_context
        )
        
        assert result.success is True
        assert result.command == "exit"
        assert "Exiting Test Agent" in result.result
        assert result.metadata["handler"] == "builtin"
    
    @pytest.mark.asyncio
    async def test_unknown_command(self, executor, mock_agent_def, mock_security_context):
        """Test executing unknown command."""
        result = await executor.execute_command(
            agent_def=mock_agent_def,
            command="unknown",
            case_name="Test_Case",
            security_context=mock_security_context
        )
        
        assert result.success is False
        assert result.command == "unknown"
        assert "Unknown command" in result.error
        assert result.metadata["error_type"] == "ValidationError"
    
    @pytest.mark.asyncio
    async def test_execute_task_command(self, executor, mock_agent_def, mock_security_context):
        """Test executing command as task."""
        # Create mock task file
        tasks_dir = Path(executor.base_path) / "tasks"
        tasks_dir.mkdir(exist_ok=True)
        
        task_content = """## Purpose
Analyze data for insights

## Task Execution
1. Load data
2. Process data
3. Generate report

## Elicitation Required
elicit: false

## WebSocket Events
- task_started
- task_progress
- task_completed
"""
        
        task_file = tasks_dir / "analyze-task.md"
        task_file.write_text(task_content)
        
        result = await executor.execute_command(
            agent_def=mock_agent_def,
            command="analyze",
            case_name="Test_Case",
            security_context=mock_security_context
        )
        
        assert result.success is True
        assert result.command == "analyze"
        assert result.metadata["handler"] == "task"
        assert result.result["task"] == "analyze"
        assert "Analyze data for insights" in result.result["purpose"]
        assert len(result.result["steps_executed"]) == 3
    
    @pytest.mark.asyncio
    async def test_case_isolation_mismatch(self, executor, mock_agent_def, mock_security_context):
        """Test case isolation validation."""
        # Mock task loading
        executor._find_task_for_command = Mock(return_value="test-task.md")
        executor._load_task = AsyncMock(return_value="task content")
        executor._parse_task_content = Mock(return_value={"execution_steps": []})
        
        # Expect ValidationError to be raised
        from src.ai_agents.bmad_framework.exceptions import ValidationError
        with pytest.raises(ValidationError) as exc_info:
            await executor.execute_command(
                agent_def=mock_agent_def,
                command="analyze",
                case_name="Different_Case",  # Mismatch with security context
                security_context=mock_security_context
            )
        
        assert "Case isolation validation failed: Case name mismatch" in str(exc_info.value)
    
    @pytest.mark.asyncio
    async def test_websocket_events(self, executor, mock_agent_def, mock_security_context):
        """Test WebSocket event emission during task execution."""
        # Create task with WebSocket events
        tasks_dir = Path(executor.base_path) / "tasks"
        tasks_dir.mkdir(exist_ok=True)
        
        task_content = """## Task Execution
1. Step one
2. Step two

## WebSocket Events
- agent:task_started
- agent:task_progress
"""
        
        task_file = tasks_dir / "analyze-task.md"
        task_file.write_text(task_content)
        
        # Mock WebSocket emission
        with patch.object(executor, '_emit_websocket_event', new_callable=AsyncMock) as mock_emit:
            result = await executor.execute_command(
                agent_def=mock_agent_def,
                command="analyze",
                case_name="Test_Case",
                security_context=mock_security_context,
                websocket_channel="test-channel"
            )
            
            assert result.success is True
            
            # Verify events were emitted
            assert mock_emit.call_count >= 3  # start, progress, complete
            
            # Check event types
            call_args = [call[0][1] for call in mock_emit.call_args_list]
            assert "agent:task_started" in call_args
            assert "agent:task_progress" in call_args
            assert "agent:task_completed" in call_args
    
    @pytest.mark.asyncio
    async def test_elicitation_handler(self, executor, mock_agent_def, mock_security_context):
        """Test task execution with elicitation."""
        # Create task requiring elicitation
        tasks_dir = Path(executor.base_path) / "tasks"
        tasks_dir.mkdir(exist_ok=True)
        
        task_content = """## Task Execution
1. First step
2. Second step

## Elicitation Required
elicit: true
"""
        
        task_file = tasks_dir / "analyze-task.md"
        task_file.write_text(task_content)
        
        # Mock elicitation handler
        elicitation_handler = AsyncMock(return_value="user response")
        
        result = await executor.execute_command(
            agent_def=mock_agent_def,
            command="analyze",
            case_name="Test_Case",
            security_context=mock_security_context,
            elicitation_handler=elicitation_handler
        )
        
        assert result.success is True
        assert result.result["elicitation_used"] is True
        
        # Verify elicitation was called
        assert elicitation_handler.call_count == 2
        
        # Check responses were recorded
        steps = result.result["steps_executed"]
        assert steps[0]["response"] == "user response"
        assert steps[1]["response"] == "user response"
    
    def test_find_task_for_command(self, executor):
        """Test finding task file for command."""
        agent_def = AgentDefinition(
            tasks=[
                "analyze.md",
                "create-report.md",
                "search-task.md"
            ]
        )
        
        context = Mock()
        context.agent_def = agent_def
        
        # Direct match
        context.command = "analyze"
        assert executor._find_task_for_command(context) == "analyze.md"
        
        # Pattern match
        context.command = "report"
        assert executor._find_task_for_command(context) == "create-report.md"
        
        # Task suffix match
        context.command = "search"
        assert executor._find_task_for_command(context) == "search-task.md"
        
        # No match
        context.command = "unknown"
        assert executor._find_task_for_command(context) is None
    
    def test_parse_task_content(self, executor):
        """Test parsing task content."""
        content = """## Purpose
Test task purpose

## Task Execution
1. First step
2. Second step
- Third step

## Elicitation Required
elicit: true

## WebSocket Events
- event1
- event2
"""
        
        task_def = executor._parse_task_content(content)
        
        assert "Test task purpose" in task_def["purpose"]
        assert len(task_def["execution_steps"]) == 3
        assert task_def["elicit"] is True
        assert len(task_def["websocket_events"]) == 2
        assert "event1" in task_def["websocket_events"]
    
    def test_register_custom_handler(self, executor):
        """Test registering custom command handler."""
        async def custom_handler(context):
            return f"Custom handler for {context.command}"
        
        executor.register_command_handler("custom", custom_handler)
        
        assert "custom" in executor._command_handlers
        assert executor._command_handlers["custom"] == custom_handler
    
    @pytest.mark.asyncio
    async def test_load_dependencies(self, executor):
        """Test loading agent dependencies."""
        # Create mock files
        tasks_dir = Path(executor.base_path) / "tasks"
        tasks_dir.mkdir(exist_ok=True)
        (tasks_dir / "task1.md").write_text("Task 1 content")
        (tasks_dir / "task2.md").write_text("Task 2 content")
        
        agent_def = AgentDefinition(
            tasks=["task1.md", "task2.md", "missing.md"],
            templates=["template1.yaml"],
            checklists=["checklist1.md"],
            data=["data1.json"]
        )
        
        deps = await executor.load_dependencies(agent_def)
        
        assert "task1.md" in deps["tasks"]
        assert deps["tasks"]["task1.md"] == "Task 1 content"
        assert "task2.md" in deps["tasks"]
        assert "missing.md" not in deps["tasks"]  # Failed to load
        
        assert "template1.yaml" in deps["templates"]
        assert "checklist1.md" in deps["checklists"]
        assert "data1.json" in deps["data"]
    
    @pytest.mark.asyncio
    async def test_task_not_found_error(self, executor, mock_agent_def, mock_security_context):
        """Test error when task file not found."""
        # No task file exists
        result = await executor.execute_command(
            agent_def=mock_agent_def,
            command="analyze",
            case_name="Test_Case",
            security_context=mock_security_context
        )
        
        assert result.success is False
        assert "Task file not found" in result.error or "No task mapping found" in result.error