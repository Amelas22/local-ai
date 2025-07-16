"""
Timeout monitoring and progress tracking utilities
Helps track long-running operations and identify bottlenecks
"""

import asyncio
import time
import logging
from typing import Dict, Any, Optional, List, Callable
from datetime import datetime
from dataclasses import dataclass, field
from functools import wraps

logger = logging.getLogger(__name__)


@dataclass
class ProgressStep:
    """Single progress step in an operation"""

    step_name: str
    description: str
    start_time: float
    end_time: Optional[float] = None
    duration: Optional[float] = None
    metadata: Dict[str, Any] = field(default_factory=dict)

    def complete(self):
        """Mark step as complete"""
        self.end_time = time.time()
        self.duration = self.end_time - self.start_time


class TimeoutMonitor:
    """Monitor for tracking operation timeouts and progress"""

    def __init__(
        self,
        operation_name: str,
        warning_threshold: float = 60.0,  # seconds
        critical_threshold: float = 120.0,  # seconds
        check_interval: float = 5.0,
    ):  # seconds
        """
        Initialize timeout monitor

        Args:
            operation_name: Name of the operation being monitored
            warning_threshold: Time after which to issue warnings
            critical_threshold: Time after which operation is considered critical
            check_interval: How often to check progress
        """
        self.operation_name = operation_name
        self.warning_threshold = warning_threshold
        self.critical_threshold = critical_threshold
        self.check_interval = check_interval

        self.start_time = time.time()
        self.end_time = None
        self.progress_log: List[Dict[str, Any]] = []
        self.is_running = True
        self.monitor_task = None

        # Start monitoring
        self._start_monitoring()

    def _start_monitoring(self):
        """Start the background monitoring task"""
        self.monitor_task = asyncio.create_task(self._monitor_loop())

    async def _monitor_loop(self):
        """Background loop that checks timeouts"""
        while self.is_running:
            try:
                elapsed = time.time() - self.start_time

                if elapsed > self.critical_threshold:
                    logger.warning(
                        f"[TIMEOUT_MONITOR] {self.operation_name} has been running for "
                        f"{elapsed:.1f}s (critical threshold: {self.critical_threshold}s)"
                    )
                    # Log progress so far
                    progress_summary = [p["message"] for p in self.progress_log[-5:]]
                    if progress_summary:
                        logger.warning(
                            f"[TIMEOUT_MONITOR] Progress so far: {progress_summary}"
                        )

                elif elapsed > self.warning_threshold:
                    logger.info(
                        f"[TIMEOUT_MONITOR] {self.operation_name} has been running for "
                        f"{elapsed:.1f}s (warning threshold: {self.warning_threshold}s)"
                    )

                await asyncio.sleep(self.check_interval)

            except Exception as e:
                logger.error(f"[TIMEOUT_MONITOR] Error in monitor loop: {str(e)}")
                break

    def log_progress(self, message: str, metadata: Optional[Dict[str, Any]] = None):
        """Log progress update"""
        self.progress_log.append(
            {
                "timestamp": time.time(),
                "elapsed": time.time() - self.start_time,
                "message": message,
                "metadata": metadata or {},
            }
        )

        # Also log to standard logger
        elapsed = time.time() - self.start_time
        logger.info(f"[PROGRESS] {self.operation_name} [{elapsed:.1f}s]: {message}")

    def finish(self, success: bool = True):
        """Mark operation as finished"""
        self.is_running = False
        self.end_time = time.time()

        if self.monitor_task:
            self.monitor_task.cancel()

        total_time = self.end_time - self.start_time
        status = "completed successfully" if success else "failed"

        logger.info(
            f"[TIMEOUT_MONITOR] {self.operation_name} {status} after {total_time:.1f}s"
        )

    def get_summary(self) -> Dict[str, Any]:
        """Get summary of operation timing"""
        current_time = self.end_time or time.time()
        total_elapsed = current_time - self.start_time

        return {
            "operation": self.operation_name,
            "start_time": datetime.fromtimestamp(self.start_time).isoformat(),
            "end_time": datetime.fromtimestamp(self.end_time).isoformat()
            if self.end_time
            else None,
            "total_elapsed_seconds": total_elapsed,
            "is_running": self.is_running,
            "exceeded_warning": total_elapsed > self.warning_threshold,
            "exceeded_critical": total_elapsed > self.critical_threshold,
            "progress_steps": len(self.progress_log),
            "last_progress": self.progress_log[-1] if self.progress_log else None,
        }


class ProgressTracker:
    """Track detailed progress through multi-step operations"""

    def __init__(self, total_steps: int, operation_name: str):
        """
        Initialize progress tracker

        Args:
            total_steps: Total number of steps in operation
            operation_name: Name of the operation
        """
        self.total_steps = total_steps
        self.operation_name = operation_name
        self.current_step = 0
        self.steps: List[ProgressStep] = []
        self.start_time = time.time()

    def next_step(
        self,
        step_name: str,
        description: str = "",
        metadata: Optional[Dict[str, Any]] = None,
    ):
        """Move to next step"""
        # Complete previous step if exists
        if self.steps and self.steps[-1].end_time is None:
            self.steps[-1].complete()

        # Start new step
        self.current_step += 1
        step = ProgressStep(
            step_name=step_name,
            description=description,
            start_time=time.time(),
            metadata=metadata or {},
        )
        self.steps.append(step)

        # Log progress
        percent_complete = (self.current_step / self.total_steps) * 100
        logger.info(
            f"[PROGRESS] {self.operation_name} - Step {self.current_step}/{self.total_steps} "
            f"({percent_complete:.0f}%): {step_name}"
        )

        if description:
            logger.info(f"[PROGRESS] {description}")

    def update_current_step(self, metadata: Dict[str, Any]):
        """Update metadata for current step"""
        if self.steps:
            self.steps[-1].metadata.update(metadata)

    def finish(self):
        """Mark tracking as complete"""
        if self.steps and self.steps[-1].end_time is None:
            self.steps[-1].complete()

        total_time = time.time() - self.start_time
        logger.info(
            f"[PROGRESS] {self.operation_name} completed all {self.total_steps} steps "
            f"in {total_time:.1f}s"
        )

        # Log slowest steps
        sorted_steps = sorted(
            [s for s in self.steps if s.duration is not None],
            key=lambda s: s.duration,
            reverse=True,
        )

        if sorted_steps:
            logger.info("[PROGRESS] Slowest steps:")
            for step in sorted_steps[:3]:
                logger.info(f"  - {step.step_name}: {step.duration:.1f}s")

    def get_summary(self) -> Dict[str, Any]:
        """Get summary of progress"""
        current_time = time.time()
        elapsed = current_time - self.start_time

        step_summaries = []
        for step in self.steps:
            step_summaries.append(
                {
                    "name": step.step_name,
                    "description": step.description,
                    "duration": step.duration,
                    "metadata": step.metadata,
                }
            )

        return {
            "operation": self.operation_name,
            "total_steps": self.total_steps,
            "completed_steps": self.current_step,
            "percent_complete": (self.current_step / self.total_steps) * 100,
            "elapsed_seconds": elapsed,
            "steps": step_summaries,
            "average_step_duration": elapsed / max(self.current_step, 1),
        }


def timeout_monitored(
    warning_threshold: float = 60.0, critical_threshold: float = 120.0
):
    """
    Decorator to monitor function execution time

    Args:
        warning_threshold: Seconds before warning
        critical_threshold: Seconds before critical warning
    """

    def decorator(func: Callable):
        @wraps(func)
        async def async_wrapper(*args, **kwargs):
            operation_name = f"{func.__module__}.{func.__name__}"
            monitor = TimeoutMonitor(
                operation_name=operation_name,
                warning_threshold=warning_threshold,
                critical_threshold=critical_threshold,
            )

            try:
                result = await func(*args, **kwargs)
                monitor.finish(success=True)
                return result
            except Exception:
                monitor.finish(success=False)
                raise

        @wraps(func)
        def sync_wrapper(*args, **kwargs):
            operation_name = f"{func.__module__}.{func.__name__}"
            start_time = time.time()

            try:
                result = func(*args, **kwargs)
                elapsed = time.time() - start_time

                if elapsed > critical_threshold:
                    logger.warning(
                        f"[TIMEOUT] {operation_name} took {elapsed:.1f}s "
                        f"(exceeded critical threshold of {critical_threshold}s)"
                    )
                elif elapsed > warning_threshold:
                    logger.info(
                        f"[TIMEOUT] {operation_name} took {elapsed:.1f}s "
                        f"(exceeded warning threshold of {warning_threshold}s)"
                    )

                return result

            except Exception as e:
                elapsed = time.time() - start_time
                logger.error(
                    f"[TIMEOUT] {operation_name} failed after {elapsed:.1f}s: {str(e)}"
                )
                raise

        if asyncio.iscoroutinefunction(func):
            return async_wrapper
        else:
            return sync_wrapper

    return decorator


class OperationTimer:
    """Context manager for timing operations"""

    def __init__(self, operation_name: str, log_level: str = "INFO"):
        self.operation_name = operation_name
        self.log_level = log_level
        self.start_time = None
        self.end_time = None

    def __enter__(self):
        self.start_time = time.time()
        logger.log(
            getattr(logging, self.log_level), f"[TIMER] Starting {self.operation_name}"
        )
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        self.end_time = time.time()
        elapsed = self.end_time - self.start_time

        if exc_type is None:
            logger.log(
                getattr(logging, self.log_level),
                f"[TIMER] {self.operation_name} completed in {elapsed:.2f}s",
            )
        else:
            logger.error(
                f"[TIMER] {self.operation_name} failed after {elapsed:.2f}s: {exc_val}"
            )

    @property
    def elapsed(self) -> float:
        """Get elapsed time"""
        if self.start_time is None:
            return 0.0

        end = self.end_time or time.time()
        return end - self.start_time
