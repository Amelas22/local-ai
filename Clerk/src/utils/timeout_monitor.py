"""
Timeout monitoring utilities for long-running processes
"""

import asyncio
import logging
from datetime import datetime, timedelta
from typing import Optional, Dict, Any, Callable
from functools import wraps

logger = logging.getLogger(__name__)

class TimeoutMonitor:
    """Monitor for tracking long-running operations and warning about potential timeouts"""
    
    def __init__(self, operation_name: str, warning_threshold: int = 15, critical_threshold: int = 20):
        """
        Initialize timeout monitor
        
        Args:
            operation_name: Name of the operation being monitored
            warning_threshold: Seconds after which to log warnings
            critical_threshold: Seconds after which to log critical warnings
        """
        self.operation_name = operation_name
        self.warning_threshold = warning_threshold
        self.critical_threshold = critical_threshold
        self.start_time = datetime.utcnow()
        self.last_progress_time = self.start_time
        self.progress_steps = []
        self.warnings_sent = set()
        
    def log_progress(self, step_name: str, details: Optional[Dict[str, Any]] = None):
        """Log progress for a step in the operation"""
        current_time = datetime.utcnow()
        elapsed = current_time - self.start_time
        step_elapsed = current_time - self.last_progress_time
        
        self.progress_steps.append({
            "step": step_name,
            "timestamp": current_time,
            "total_elapsed": elapsed,
            "step_elapsed": step_elapsed,
            "details": details or {}
        })
        
        logger.info(f"[TIMEOUT_MONITOR] {self.operation_name} - {step_name} "
                   f"(Total: {elapsed}, Step: {step_elapsed})")
        
        # Check for warnings
        self._check_timeout_warnings(elapsed)
        
        self.last_progress_time = current_time
        
    def _check_timeout_warnings(self, elapsed: timedelta):
        """Check if we should send timeout warnings"""
        elapsed_seconds = elapsed.total_seconds()
        
        # Warning threshold
        if (elapsed_seconds > self.warning_threshold and 
            "warning" not in self.warnings_sent):
            logger.warning(f"[TIMEOUT_MONITOR] {self.operation_name} has been running for "
                          f"{elapsed_seconds:.1f}s (warning threshold: {self.warning_threshold}s)")
            self.warnings_sent.add("warning")
        
        # Critical threshold  
        if (elapsed_seconds > self.critical_threshold and
            "critical" not in self.warnings_sent):
            logger.critical(f"[TIMEOUT_MONITOR] {self.operation_name} has been running for "
                           f"{elapsed_seconds:.1f}s (critical threshold: {self.critical_threshold}s)")
            logger.critical(f"[TIMEOUT_MONITOR] Progress so far: {[s['step'] for s in self.progress_steps]}")
            self.warnings_sent.add("critical")
    
    def get_summary(self) -> Dict[str, Any]:
        """Get summary of the operation timing"""
        current_time = datetime.utcnow()
        total_elapsed = current_time - self.start_time
        
        return {
            "operation_name": self.operation_name,
            "start_time": self.start_time,
            "total_elapsed": total_elapsed,
            "total_elapsed_seconds": total_elapsed.total_seconds(),
            "steps_completed": len(self.progress_steps),
            "current_step": self.progress_steps[-1]["step"] if self.progress_steps else "Not started",
            "warnings_sent": list(self.warnings_sent),
            "steps": self.progress_steps
        }
    
    def finish(self, success: bool = True):
        """Mark the operation as finished"""
        current_time = datetime.utcnow()
        total_elapsed = current_time - self.start_time
        
        status = "COMPLETED" if success else "FAILED"
        logger.info(f"[TIMEOUT_MONITOR] {self.operation_name} {status} in {total_elapsed}")
        logger.info(f"[TIMEOUT_MONITOR] Steps completed: {len(self.progress_steps)}")
        
        # Log detailed breakdown if it took a long time
        if total_elapsed.total_seconds() > self.warning_threshold:
            logger.info(f"[TIMEOUT_MONITOR] Detailed breakdown for {self.operation_name}:")
            for i, step in enumerate(self.progress_steps):
                logger.info(f"[TIMEOUT_MONITOR]   Step {i+1}: {step['step']} - {step['step_elapsed']}")


def timeout_monitored(operation_name: str, warning_threshold: int = 15, critical_threshold: int = 20):
    """
    Decorator to automatically monitor function execution time
    
    Args:
        operation_name: Name of the operation
        warning_threshold: Seconds after which to log warnings
        critical_threshold: Seconds after which to log critical warnings
    """
    def decorator(func: Callable):
        @wraps(func)
        async def async_wrapper(*args, **kwargs):
            monitor = TimeoutMonitor(operation_name, warning_threshold, critical_threshold)
            monitor.log_progress("Started")
            
            try:
                result = await func(*args, **kwargs)
                monitor.finish(success=True)
                return result
            except Exception as e:
                monitor.finish(success=False)
                logger.error(f"[TIMEOUT_MONITOR] {operation_name} failed: {str(e)}")
                raise
                
        @wraps(func)
        def sync_wrapper(*args, **kwargs):
            monitor = TimeoutMonitor(operation_name, warning_threshold, critical_threshold)
            monitor.log_progress("Started")
            
            try:
                result = func(*args, **kwargs)
                monitor.finish(success=True)
                return result
            except Exception as e:
                monitor.finish(success=False)
                logger.error(f"[TIMEOUT_MONITOR] {operation_name} failed: {str(e)}")
                raise
        
        return async_wrapper if asyncio.iscoroutinefunction(func) else sync_wrapper
    return decorator


class ProgressTracker:
    """Track progress through a multi-step process"""
    
    def __init__(self, total_steps: int, operation_name: str):
        self.total_steps = total_steps
        self.operation_name = operation_name
        self.current_step = 0
        self.start_time = datetime.utcnow()
        self.step_times = []
        
    def next_step(self, step_name: str, details: Optional[str] = None):
        """Move to the next step"""
        current_time = datetime.utcnow()
        self.current_step += 1
        
        if self.step_times:
            # Calculate time for previous step
            prev_step_time = current_time - self.step_times[-1]["start_time"]
            self.step_times[-1]["duration"] = prev_step_time
        
        self.step_times.append({
            "step_number": self.current_step,
            "step_name": step_name,
            "start_time": current_time,
            "details": details,
            "duration": None
        })
        
        # Calculate progress
        progress_pct = (self.current_step / self.total_steps) * 100
        elapsed = current_time - self.start_time
        
        # Estimate remaining time
        if self.current_step > 1:
            avg_step_time = elapsed / (self.current_step - 1)
            remaining_steps = self.total_steps - self.current_step
            estimated_remaining = avg_step_time * remaining_steps
        else:
            estimated_remaining = "unknown"
        
        logger.info(f"[PROGRESS] {self.operation_name} - Step {self.current_step}/{self.total_steps} "
                   f"({progress_pct:.1f}%): {step_name}")
        logger.info(f"[PROGRESS] Elapsed: {elapsed}, Estimated remaining: {estimated_remaining}")
        
        if details:
            logger.info(f"[PROGRESS] Details: {details}")
    
    def finish(self):
        """Mark the process as finished"""
        current_time = datetime.utcnow()
        total_time = current_time - self.start_time
        
        # Finish the last step
        if self.step_times and self.step_times[-1]["duration"] is None:
            self.step_times[-1]["duration"] = current_time - self.step_times[-1]["start_time"]
        
        logger.info(f"[PROGRESS] {self.operation_name} COMPLETED in {total_time}")
        logger.info(f"[PROGRESS] Total steps: {len(self.step_times)}")
        
        # Log step breakdown
        for step in self.step_times:
            duration = step["duration"] or timedelta(0)
            logger.info(f"[PROGRESS]   {step['step_name']}: {duration}")