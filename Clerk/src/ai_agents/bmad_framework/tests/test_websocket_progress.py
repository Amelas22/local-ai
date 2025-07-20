"""
Unit tests for WebSocket progress tracking.
"""

import pytest
from unittest.mock import AsyncMock, patch
from datetime import datetime

from src.ai_agents.bmad_framework.websocket_progress import (
    ProgressTracker,
    ProgressUpdate,
    track_progress,
    BatchProgressTracker,
)


class TestProgressUpdate:
    """Test ProgressUpdate dataclass."""

    def test_progress_update_creation(self):
        """Test creating progress update."""
        update = ProgressUpdate(
            task_name="test_task",
            current_step=5,
            total_steps=10,
            percentage=50,
            status="processing",
            message="Processing data",
        )

        assert update.task_name == "test_task"
        assert update.current_step == 5
        assert update.total_steps == 10
        assert update.percentage == 50
        assert update.status == "processing"
        assert update.message == "Processing data"
        assert isinstance(update.timestamp, datetime)
        assert update.metadata == {}

    def test_progress_update_with_metadata(self):
        """Test progress update with metadata."""
        metadata = {"file": "test.pdf", "size": 1024}
        update = ProgressUpdate(
            task_name="test",
            current_step=1,
            total_steps=1,
            percentage=100,
            status="completed",
            message="Done",
            metadata=metadata,
        )

        assert update.metadata == metadata


class TestProgressTracker:
    """Test ProgressTracker functionality."""

    @pytest.fixture
    def tracker(self):
        """Create progress tracker instance."""
        return ProgressTracker(
            case_id="case-123",
            agent_id="test-agent",
            task_name="test_task",
            total_steps=10,
        )

    def test_initialization(self, tracker):
        """Test tracker initialization."""
        assert tracker.case_id == "case-123"
        assert tracker.agent_id == "test-agent"
        assert tracker.task_name == "test_task"
        assert tracker.total_steps == 10
        assert tracker.current_step == 0
        assert tracker.room == "case_case-123"
        assert tracker.percentage == 0

    def test_percentage_calculation(self, tracker):
        """Test percentage calculation."""
        tracker.current_step = 0
        assert tracker.percentage == 0

        tracker.current_step = 5
        assert tracker.percentage == 50

        tracker.current_step = 10
        assert tracker.percentage == 100

        # Test overflow protection
        tracker.current_step = 15
        assert tracker.percentage == 100

    def test_percentage_with_zero_steps(self):
        """Test percentage when total steps is zero."""
        tracker = ProgressTracker(
            case_id="case-123", agent_id="test-agent", task_name="test", total_steps=0
        )
        assert tracker.percentage == 0

    @pytest.mark.asyncio
    @patch("src.ai_agents.bmad_framework.websocket_progress.WEBSOCKET_AVAILABLE", True)
    @patch("src.ai_agents.bmad_framework.websocket_progress.sio")
    async def test_emit_start(self, mock_sio, tracker):
        """Test emitting start event."""
        mock_sio.emit = AsyncMock()

        await tracker.emit_start("Starting analysis")

        # Check emit was called
        mock_sio.emit.assert_called_once()
        call_args = mock_sio.emit.call_args

        assert call_args[0][0] == "agent:task_started"
        event_data = call_args[0][1]
        assert event_data["case_id"] == "case-123"
        assert event_data["agent_id"] == "test-agent"
        assert event_data["task_name"] == "test_task"
        assert event_data["status"] == "started"
        assert event_data["message"] == "Starting analysis"

        # Check update was stored
        assert len(tracker.updates) == 1
        assert tracker.updates[0].status == "started"

    @pytest.mark.asyncio
    @patch("src.ai_agents.bmad_framework.websocket_progress.WEBSOCKET_AVAILABLE", True)
    @patch("src.ai_agents.bmad_framework.websocket_progress.sio")
    async def test_emit_progress(self, mock_sio, tracker):
        """Test emitting progress updates."""
        mock_sio.emit = AsyncMock()

        # Auto-increment
        await tracker.emit_progress(message="Step 1")
        assert tracker.current_step == 1

        # Explicit step
        await tracker.emit_progress(step=5, message="Step 5")
        assert tracker.current_step == 5

        # Check emit calls
        assert mock_sio.emit.call_count == 2

        # Check last emit
        call_args = mock_sio.emit.call_args
        assert call_args[0][0] == "agent:task_progress"
        event_data = call_args[0][1]
        assert event_data["current_step"] == 5
        assert event_data["percentage"] == 50
        assert event_data["message"] == "Step 5"

    @pytest.mark.asyncio
    @patch("src.ai_agents.bmad_framework.websocket_progress.WEBSOCKET_AVAILABLE", True)
    @patch("src.ai_agents.bmad_framework.websocket_progress.sio")
    async def test_emit_completion(self, mock_sio, tracker):
        """Test emitting completion event."""
        mock_sio.emit = AsyncMock()

        result = {"documents": 42}
        await tracker.emit_completion("Analysis complete", result)

        # Check emit
        mock_sio.emit.assert_called_once()
        call_args = mock_sio.emit.call_args

        assert call_args[0][0] == "agent:task_completed"
        event_data = call_args[0][1]
        assert event_data["status"] == "completed"
        assert event_data["percentage"] == 100
        assert event_data["result"] == result
        assert "elapsed_time" in event_data

    @pytest.mark.asyncio
    @patch("src.ai_agents.bmad_framework.websocket_progress.WEBSOCKET_AVAILABLE", True)
    @patch("src.ai_agents.bmad_framework.websocket_progress.sio")
    async def test_emit_failure(self, mock_sio, tracker):
        """Test emitting failure event."""
        mock_sio.emit = AsyncMock()

        await tracker.emit_failure("Connection timeout", "TimeoutError")

        # Check emit
        mock_sio.emit.assert_called_once()
        call_args = mock_sio.emit.call_args

        assert call_args[0][0] == "agent:task_failed"
        event_data = call_args[0][1]
        assert event_data["status"] == "failed"
        assert event_data["error"] == "Connection timeout"
        assert event_data["error_type"] == "TimeoutError"

    @pytest.mark.asyncio
    @patch("src.ai_agents.bmad_framework.websocket_progress.WEBSOCKET_AVAILABLE", True)
    @patch("src.ai_agents.bmad_framework.websocket_progress.sio")
    async def test_custom_websocket_channel(self, mock_sio, tracker):
        """Test emitting to custom WebSocket channel."""
        mock_sio.emit = AsyncMock()

        tracker.websocket_channel = "custom-channel"
        await tracker.emit_start()

        # Should emit to both room and custom channel
        assert mock_sio.emit.call_count == 2

    @pytest.mark.asyncio
    @patch("src.ai_agents.bmad_framework.websocket_progress.WEBSOCKET_AVAILABLE", False)
    async def test_no_websocket_available(self, tracker):
        """Test behavior when WebSocket is not available."""
        # Should not raise error
        await tracker.emit_start("Starting")
        await tracker.emit_progress(message="Progress")
        await tracker.emit_completion("Done")

        # Updates should still be stored
        assert len(tracker.updates) == 3

    @pytest.mark.asyncio
    async def test_listener_notifications(self, tracker):
        """Test progress listener notifications."""
        events = []

        async def listener(event_type, update):
            events.append((event_type, update.status))

        tracker.add_listener(listener)

        await tracker.emit_start()
        await tracker.emit_progress()
        await tracker.emit_completion()

        assert len(events) == 3
        assert events[0] == ("agent:task_started", "started")
        assert events[1] == ("agent:task_progress", "processing")
        assert events[2] == ("agent:task_completed", "completed")

        # Test remove listener
        tracker.remove_listener(listener)
        await tracker.emit_progress()
        assert len(events) == 3  # No new event

    @pytest.mark.asyncio
    async def test_update_total_steps(self, tracker):
        """Test dynamically updating total steps."""
        assert tracker.total_steps == 10

        await tracker.update_total_steps(20)

        assert tracker.total_steps == 20
        assert len(tracker.updates) == 1
        assert "Updated total steps to 20" in tracker.updates[0].message


class TestTrackProgressContext:
    """Test track_progress context manager."""

    @pytest.mark.asyncio
    @patch("src.ai_agents.bmad_framework.websocket_progress.WEBSOCKET_AVAILABLE", True)
    @patch("src.ai_agents.bmad_framework.websocket_progress.sio")
    async def test_successful_tracking(self, mock_sio):
        """Test successful task tracking."""
        mock_sio.emit = AsyncMock()

        async with track_progress(
            case_id="case-123",
            agent_id="test-agent",
            task_name="test_task",
            total_steps=3,
        ) as tracker:
            await tracker.emit_progress(message="Step 1")
            await tracker.emit_progress(message="Step 2")
            await tracker.emit_progress(message="Step 3")

        # Should have start, 3 progress, and completion
        assert mock_sio.emit.call_count == 5

        # Check event types
        call_types = [call[0][0] for call in mock_sio.emit.call_args_list]
        assert call_types[0] == "agent:task_started"
        assert call_types[1:4] == ["agent:task_progress"] * 3
        assert call_types[4] == "agent:task_completed"

    @pytest.mark.asyncio
    @patch("src.ai_agents.bmad_framework.websocket_progress.WEBSOCKET_AVAILABLE", True)
    @patch("src.ai_agents.bmad_framework.websocket_progress.sio")
    async def test_tracking_with_exception(self, mock_sio):
        """Test tracking when exception occurs."""
        mock_sio.emit = AsyncMock()

        with pytest.raises(ValueError):
            async with track_progress(
                case_id="case-123", agent_id="test-agent", task_name="test_task"
            ) as tracker:
                await tracker.emit_progress(message="Working...")
                raise ValueError("Test error")

        # Should have start, progress, and failure
        assert mock_sio.emit.call_count == 3

        # Check last event is failure
        last_call = mock_sio.emit.call_args_list[-1]
        assert last_call[0][0] == "agent:task_failed"
        event_data = last_call[0][1]
        assert event_data["error"] == "Test error"
        assert event_data["error_type"] == "ValueError"


class TestBatchProgressTracker:
    """Test BatchProgressTracker functionality."""

    @pytest.fixture
    def batch_tracker(self):
        """Create batch progress tracker."""
        return BatchProgressTracker(
            case_id="case-123",
            agent_id="test-agent",
            workflow_name="analysis_workflow",
            tasks=["parse", "search", "categorize"],
        )

    def test_initialization(self, batch_tracker):
        """Test batch tracker initialization."""
        assert batch_tracker.case_id == "case-123"
        assert batch_tracker.agent_id == "test-agent"
        assert batch_tracker.workflow_name == "analysis_workflow"
        assert batch_tracker.tasks == ["parse", "search", "categorize"]
        assert batch_tracker.current_task_index == -1
        assert batch_tracker.trackers == {}

    @pytest.mark.asyncio
    async def test_start_task(self, batch_tracker):
        """Test starting a task."""
        tracker = await batch_tracker.start_task("parse", total_steps=5)

        assert tracker.task_name == "parse"
        assert tracker.total_steps == 5
        assert batch_tracker.current_task_index == 0
        assert "parse" in batch_tracker.trackers

    @pytest.mark.asyncio
    async def test_start_invalid_task(self, batch_tracker):
        """Test starting an invalid task."""
        with pytest.raises(ValueError) as exc_info:
            await batch_tracker.start_task("invalid_task")

        assert "not in workflow" in str(exc_info.value)

    @pytest.mark.asyncio
    @patch("src.ai_agents.bmad_framework.websocket_progress.WEBSOCKET_AVAILABLE", True)
    @patch("src.ai_agents.bmad_framework.websocket_progress.sio")
    async def test_workflow_progress(self, mock_sio, batch_tracker):
        """Test workflow progress emission."""
        mock_sio.emit = AsyncMock()

        # Start and complete tasks
        tracker1 = await batch_tracker.start_task("parse")
        await tracker1.emit_completion()

        tracker2 = await batch_tracker.start_task("search")

        # Find workflow progress emissions
        workflow_calls = [
            call
            for call in mock_sio.emit.call_args_list
            if call[0][0] == "agent:workflow_progress"
        ]

        assert len(workflow_calls) >= 2

        # Check last workflow progress
        last_workflow = workflow_calls[-1][0][1]
        assert last_workflow["workflow_name"] == "analysis_workflow"
        assert last_workflow["current_task"] == "search"
        assert last_workflow["completed_tasks"] == 1
        assert last_workflow["total_tasks"] == 3
        assert last_workflow["percentage"] == 33
