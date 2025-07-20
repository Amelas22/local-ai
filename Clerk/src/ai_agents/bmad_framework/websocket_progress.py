"""
WebSocket progress tracking for BMad framework.

This module provides progress tracking and real-time updates for agent task execution.
"""

import logging
import time
from typing import Dict, List, Optional, Any, Callable
from dataclasses import dataclass, field
from datetime import datetime
from contextlib import asynccontextmanager

try:
    from src.websocket.socket_server import sio

    WEBSOCKET_AVAILABLE = True
except ImportError:
    WEBSOCKET_AVAILABLE = False
    sio = None

logger = logging.getLogger("clerk_api")


async def emit_progress_update(
    case_id: str,
    agent_id: str,
    task_name: str,
    message: str,
    percentage: int,
    status: str = "processing",
    metadata: Optional[Dict[str, Any]] = None,
) -> None:
    """
    Emit a progress update via WebSocket.

    Args:
        case_id: Case ID for routing.
        agent_id: Agent ID.
        task_name: Name of the task.
        message: Progress message.
        percentage: Progress percentage (0-100).
        status: Status (started|processing|completed|failed).
        metadata: Additional metadata.
    """
    if not WEBSOCKET_AVAILABLE or not sio:
        logger.debug(f"WebSocket not available, logging progress: {message}")
        return

    event_data = {
        "case_id": case_id,
        "agent_id": agent_id,
        "task_name": task_name,
        "message": message,
        "percentage": percentage,
        "status": status,
        "timestamp": datetime.utcnow().isoformat(),
        **(metadata or {}),
    }

    try:
        # Emit to case room
        await sio.emit("agent:task_progress", event_data, room=f"case_{case_id}")
    except Exception as e:
        logger.error(f"Failed to emit progress update: {str(e)}")


@dataclass
class ProgressUpdate:
    """Represents a progress update for a task."""

    task_name: str
    current_step: int
    total_steps: int
    percentage: int
    status: str  # started|processing|completed|failed
    message: str
    timestamp: datetime = field(default_factory=datetime.utcnow)
    metadata: Dict[str, Any] = field(default_factory=dict)


class ProgressTracker:
    """
    Tracks and emits progress updates for agent tasks.
    """

    def __init__(
        self,
        case_id: str,
        agent_id: str,
        task_name: str,
        total_steps: Optional[int] = None,
        websocket_channel: Optional[str] = None,
    ):
        """
        Initialize progress tracker.

        Args:
            case_id: Case ID for isolation.
            agent_id: Agent executing the task.
            task_name: Name of the task being executed.
            total_steps: Total number of steps (if known).
            websocket_channel: Optional custom WebSocket channel.
        """
        self.case_id = case_id
        self.agent_id = agent_id
        self.task_name = task_name
        self.total_steps = total_steps or 0
        self.current_step = 0
        self.websocket_channel = websocket_channel
        self.start_time = time.time()
        self.updates: List[ProgressUpdate] = []
        self._listeners: List[Callable] = []

    @property
    def room(self) -> str:
        """Get WebSocket room for case isolation."""
        return f"case_{self.case_id}"

    @property
    def percentage(self) -> int:
        """Calculate completion percentage."""
        if self.total_steps <= 0:
            return 0
        return min(100, int((self.current_step / self.total_steps) * 100))

    async def emit_start(
        self, message: str = "", metadata: Optional[Dict[str, Any]] = None
    ) -> None:
        """
        Emit task started event.

        Args:
            message: Optional start message.
            metadata: Additional metadata.
        """
        if not message:
            message = f"Starting {self.task_name}"

        update = ProgressUpdate(
            task_name=self.task_name,
            current_step=0,
            total_steps=self.total_steps,
            percentage=0,
            status="started",
            message=message,
            metadata=metadata or {},
        )

        await self._emit_update("agent:task_started", update)

    async def emit_progress(
        self,
        step: Optional[int] = None,
        message: str = "",
        metadata: Optional[Dict[str, Any]] = None,
    ) -> None:
        """
        Emit progress update.

        Args:
            step: Current step number (auto-increments if not provided).
            message: Progress message.
            metadata: Additional metadata.
        """
        if step is not None:
            self.current_step = step
        else:
            self.current_step += 1

        update = ProgressUpdate(
            task_name=self.task_name,
            current_step=self.current_step,
            total_steps=self.total_steps,
            percentage=self.percentage,
            status="processing",
            message=message,
            metadata=metadata or {},
        )

        await self._emit_update("agent:task_progress", update)

    async def emit_completion(
        self,
        message: str = "",
        result: Optional[Any] = None,
        metadata: Optional[Dict[str, Any]] = None,
    ) -> None:
        """
        Emit task completion event.

        Args:
            message: Completion message.
            result: Task result.
            metadata: Additional metadata.
        """
        if not message:
            message = f"Completed {self.task_name}"

        elapsed_time = time.time() - self.start_time

        final_metadata = {
            "elapsed_time": elapsed_time,
            "result": result,
            **(metadata or {}),
        }

        update = ProgressUpdate(
            task_name=self.task_name,
            current_step=self.total_steps,
            total_steps=self.total_steps,
            percentage=100,
            status="completed",
            message=message,
            metadata=final_metadata,
        )

        await self._emit_update("agent:task_completed", update)

    async def emit_failure(
        self,
        error: str,
        error_type: Optional[str] = None,
        metadata: Optional[Dict[str, Any]] = None,
    ) -> None:
        """
        Emit task failure event.

        Args:
            error: Error message.
            error_type: Type of error.
            metadata: Additional metadata.
        """
        elapsed_time = time.time() - self.start_time

        final_metadata = {
            "elapsed_time": elapsed_time,
            "error": error,
            "error_type": error_type or "unknown",
            **(metadata or {}),
        }

        update = ProgressUpdate(
            task_name=self.task_name,
            current_step=self.current_step,
            total_steps=self.total_steps,
            percentage=self.percentage,
            status="failed",
            message=f"Failed: {error}",
            metadata=final_metadata,
        )

        await self._emit_update("agent:task_failed", update)

    async def _emit_update(self, event_type: str, update: ProgressUpdate) -> None:
        """
        Emit WebSocket update.

        Args:
            event_type: Event type to emit.
            update: Progress update data.
        """
        # Store update
        self.updates.append(update)

        # Prepare event data
        event_data = {
            "case_id": self.case_id,
            "agent_id": self.agent_id,
            "task_name": update.task_name,
            "current_step": update.current_step,
            "total_steps": update.total_steps,
            "percentage": update.percentage,
            "status": update.status,
            "message": update.message,
            "timestamp": update.timestamp.isoformat(),
            **update.metadata,
        }

        # Emit via WebSocket if available
        if WEBSOCKET_AVAILABLE and sio:
            try:
                await sio.emit(event_type, event_data, room=self.room)

                # Also emit to custom channel if specified
                if self.websocket_channel:
                    await sio.emit(event_type, event_data, room=self.websocket_channel)

            except Exception as e:
                logger.error(f"Failed to emit WebSocket event: {str(e)}")
        else:
            # Log if WebSocket not available
            logger.info(
                f"WebSocket event (not emitted): {event_type}",
                extra={"event_data": event_data},
            )

        # Notify listeners
        for listener in self._listeners:
            try:
                await listener(event_type, update)
            except Exception as e:
                logger.error(f"Listener error: {str(e)}")

    def add_listener(self, listener: Callable) -> None:
        """
        Add a progress listener.

        Args:
            listener: Async function to call on updates.
        """
        self._listeners.append(listener)

    def remove_listener(self, listener: Callable) -> None:
        """Remove a progress listener."""
        if listener in self._listeners:
            self._listeners.remove(listener)

    async def update_total_steps(self, total_steps: int) -> None:
        """
        Update total steps dynamically.

        Useful when total steps are not known initially.
        """
        self.total_steps = total_steps
        # Emit progress update with new total
        await self.emit_progress(message=f"Updated total steps to {total_steps}")


@asynccontextmanager
async def track_progress(
    case_id: str,
    agent_id: str,
    task_name: str,
    total_steps: Optional[int] = None,
    websocket_channel: Optional[str] = None,
):
    """
    Context manager for progress tracking.

    Automatically emits start/completion/failure events.

    Usage:
        async with track_progress(case_id, agent_id, "analyze") as tracker:
            await tracker.emit_progress(message="Processing...")
            # Task work here
    """
    tracker = ProgressTracker(
        case_id=case_id,
        agent_id=agent_id,
        task_name=task_name,
        total_steps=total_steps,
        websocket_channel=websocket_channel,
    )

    try:
        # Emit start event
        await tracker.emit_start()

        # Yield tracker for use
        yield tracker

        # Emit completion if not already done
        if tracker.updates and tracker.updates[-1].status != "completed":
            await tracker.emit_completion()

    except Exception as e:
        # Emit failure on exception
        await tracker.emit_failure(error=str(e), error_type=type(e).__name__)
        raise


class BatchProgressTracker:
    """
    Tracks progress for multiple related tasks.

    Useful for workflows with multiple steps.
    """

    def __init__(
        self, case_id: str, agent_id: str, workflow_name: str, tasks: List[str]
    ):
        """
        Initialize batch tracker.

        Args:
            case_id: Case ID for isolation.
            agent_id: Agent executing the workflow.
            workflow_name: Name of the overall workflow.
            tasks: List of task names in order.
        """
        self.case_id = case_id
        self.agent_id = agent_id
        self.workflow_name = workflow_name
        self.tasks = tasks
        self.current_task_index = -1
        self.trackers: Dict[str, ProgressTracker] = {}

    async def start_task(
        self, task_name: str, total_steps: Optional[int] = None
    ) -> ProgressTracker:
        """
        Start tracking a new task.

        Args:
            task_name: Name of the task.
            total_steps: Total steps for this task.

        Returns:
            Progress tracker for the task.
        """
        if task_name not in self.tasks:
            raise ValueError(f"Task '{task_name}' not in workflow")

        self.current_task_index = self.tasks.index(task_name)

        # Create tracker
        tracker = ProgressTracker(
            case_id=self.case_id,
            agent_id=self.agent_id,
            task_name=task_name,
            total_steps=total_steps,
        )

        self.trackers[task_name] = tracker

        # Emit workflow progress
        await self._emit_workflow_progress()

        return tracker

    async def _emit_workflow_progress(self) -> None:
        """Emit overall workflow progress."""
        completed_tasks = len(
            [
                t
                for t in self.trackers.values()
                if t.updates and t.updates[-1].status == "completed"
            ]
        )

        percentage = int((completed_tasks / len(self.tasks)) * 100)

        event_data = {
            "case_id": self.case_id,
            "agent_id": self.agent_id,
            "workflow_name": self.workflow_name,
            "current_task": self.tasks[self.current_task_index]
            if self.current_task_index >= 0
            else None,
            "completed_tasks": completed_tasks,
            "total_tasks": len(self.tasks),
            "percentage": percentage,
            "task_list": self.tasks,
        }

        if WEBSOCKET_AVAILABLE and sio:
            try:
                await sio.emit(
                    "agent:workflow_progress", event_data, room=f"case_{self.case_id}"
                )
            except Exception as e:
                logger.error(f"Failed to emit workflow progress: {str(e)}")
