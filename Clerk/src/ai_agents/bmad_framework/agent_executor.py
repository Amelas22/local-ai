"""
Agent executor module for BMad framework.

This module executes agent commands with API integration and case isolation.
"""

import logging
from pathlib import Path
from typing import Dict, Optional, Any, Callable
from dataclasses import dataclass
import asyncio
from datetime import datetime

from .agent_loader import AgentLoader, AgentDefinition
from .security import AgentSecurityContext, validate_case_isolation
from .exceptions import TaskExecutionError, DependencyNotFoundError, ValidationError

logger = logging.getLogger("clerk_api")


@dataclass
class ExecutionContext:
    """
    Context for agent execution.

    Contains all necessary information for executing agent commands.
    """

    agent_def: AgentDefinition
    security_context: AgentSecurityContext
    case_name: str
    command: str
    parameters: Dict[str, Any]
    websocket_channel: Optional[str] = None
    elicitation_handler: Optional[Callable] = None


@dataclass
class ExecutionResult:
    """
    Result of agent command execution.
    """

    success: bool
    command: str
    result: Any
    error: Optional[str] = None
    metadata: Dict[str, Any] = None

    def __post_init__(self):
        if self.metadata is None:
            self.metadata = {}


class AgentExecutor:
    """
    Executes agent commands with full framework integration.
    """

    def __init__(
        self,
        agent_loader: Optional[AgentLoader] = None,
        base_path: Optional[Path] = None,
    ):
        """
        Initialize agent executor.

        Args:
            agent_loader: Agent loader instance. Creates new one if not provided.
            base_path: Base path for dependencies. Defaults to bmad-framework directory.
        """
        self.agent_loader = agent_loader or AgentLoader()

        if base_path is None:
            base_path = Path(__file__).parent
        self.base_path = Path(base_path)

        # Command handlers registry
        self._command_handlers: Dict[str, Callable] = {}

        # Task handlers registry
        self._task_handlers: Dict[str, Callable] = {}

        # Register built-in handlers
        self._register_builtin_handlers()

        # Register default task handlers
        self._register_default_task_handlers()

    def _register_builtin_handlers(self):
        """Register built-in command handlers."""
        self._command_handlers["help"] = self._handle_help_command
        self._command_handlers["exit"] = self._handle_exit_command

    def _register_default_task_handlers(self):
        """Register default task handlers for known agents."""
        try:
            # Import deficiency analyzer handlers
            from .task_handlers import (
                handle_analyze_rtp,
                handle_search_production,
                handle_categorize_compliance,
                handle_full_analysis,
            )

            # Register task handlers
            self._task_handlers["analyze-rtp"] = handle_analyze_rtp
            self._task_handlers["search-production"] = handle_search_production
            self._task_handlers["categorize-compliance"] = handle_categorize_compliance
            self._task_handlers["analyze"] = handle_full_analysis

        except ImportError:
            logger.debug("No default task handlers available")

    @validate_case_isolation
    async def execute_command(
        self,
        agent_def: AgentDefinition,
        command: str,
        case_name: str,
        security_context: AgentSecurityContext,
        parameters: Optional[Dict[str, Any]] = None,
        websocket_channel: Optional[str] = None,
        elicitation_handler: Optional[Callable] = None,
    ) -> ExecutionResult:
        """
        Execute an agent command.

        Args:
            agent_def: Agent definition.
            command: Command to execute (with or without * prefix).
            case_name: Case name for isolation.
            security_context: Security context with permissions.
            parameters: Command parameters.
            websocket_channel: WebSocket channel for progress updates.
            elicitation_handler: Handler for user interaction in tasks.

        Returns:
            Execution result.
        """
        # Clean command name
        command = command.lstrip("*")

        # Log command execution
        security_context.log_operation(
            "command_execution", {"command": command, "case": case_name}
        )

        # Create execution context
        context = ExecutionContext(
            agent_def=agent_def,
            security_context=security_context,
            case_name=case_name,
            command=command,
            parameters=parameters or {},
            websocket_channel=websocket_channel,
            elicitation_handler=elicitation_handler,
        )

        try:
            # Validate command exists
            if command not in agent_def.command_names:
                available = ", ".join(agent_def.command_names)
                raise ValidationError(
                    "Command",
                    f"Unknown command '{command}'",
                    {"available_commands": available},
                )

            # Check if built-in handler exists
            if command in self._command_handlers:
                result = await self._command_handlers[command](context)
                return ExecutionResult(
                    success=True,
                    command=command,
                    result=result,
                    metadata={"handler": "builtin"},
                )

            # Otherwise, execute as task
            result = await self._execute_task_command(context)
            return ExecutionResult(
                success=True,
                command=command,
                result=result,
                metadata={"handler": "task"},
            )

        except Exception as e:
            logger.error(
                f"Command execution failed: {str(e)}",
                extra={
                    "agent_id": agent_def.id,
                    "command": command,
                    "case_name": case_name,
                    "error_type": type(e).__name__,
                },
            )

            return ExecutionResult(
                success=False,
                command=command,
                result=None,
                error=str(e),
                metadata={"error_type": type(e).__name__},
            )

    async def _handle_help_command(self, context: ExecutionContext) -> str:
        """Handle the help command."""
        agent_def = context.agent_def

        help_text = f"Available commands for {agent_def.name}:\n\n"

        for i, cmd in enumerate(agent_def.commands, 1):
            if isinstance(cmd, dict):
                for name, desc in cmd.items():
                    help_text += f"{i}. *{name} - {desc}\n"
            elif isinstance(cmd, str) and ":" in cmd:
                name, desc = cmd.split(":", 1)
                help_text += f"{i}. *{name.strip()} - {desc.strip()}\n"

        return help_text

    async def _handle_exit_command(self, context: ExecutionContext) -> str:
        """Handle the exit command."""
        return f"Exiting {context.agent_def.name}. Thank you for using the {context.agent_def.title}!"

    @validate_case_isolation
    async def _execute_task_command(self, context: ExecutionContext) -> Any:
        """
        Execute a command as a task.

        Maps command to task file and executes it.
        """
        # Find matching task
        task_name = self._find_task_for_command(context)
        if not task_name:
            raise TaskExecutionError(
                context.command, "No task mapping found for command"
            )

        # Load task definition
        task_content = await self._load_task(task_name)

        # Parse task structure
        task_def = self._parse_task_content(task_content)

        # Execute task steps
        return await self._execute_task_steps(context, task_def)

    def _find_task_for_command(self, context: ExecutionContext) -> Optional[str]:
        """
        Find task file for a command.

        Uses REQUEST-RESOLUTION pattern from agent definition.
        """
        # Direct mapping first - check if any task starts with the command name
        for task in context.agent_def.tasks:
            task_base = Path(task).stem
            # Check exact match or if task starts with command name
            if task_base == context.command or task_base.startswith(
                f"{context.command}-"
            ):
                return task

        # Try common patterns
        patterns = [
            f"{context.command}.md",
            f"{context.command}-*.md",  # Wildcard pattern
            f"{context.command}-task.md",
            f"{context.command}-compliance.md",  # For categorize command
            f"create-{context.command}.md",
            f"execute-{context.command}.md",
            f"{context.command}-rtp.md",  # For analyze command
            f"{context.command}-production.md",  # For search command
        ]

        # Check each pattern
        for pattern in patterns:
            # Direct match
            if pattern in context.agent_def.tasks:
                return pattern

            # Wildcard matching for patterns with *
            if "*" in pattern:
                prefix = pattern.replace("*.md", "")
                for task in context.agent_def.tasks:
                    if task.startswith(prefix) and task.endswith(".md"):
                        return task

        # REQUEST-RESOLUTION fuzzy matching
        if context.agent_def.request_resolution:
            # Look for tasks that contain the command name
            command_lower = context.command.lower()
            for task in context.agent_def.tasks:
                task_lower = task.lower()
                if command_lower in task_lower:
                    return task

        return None

    async def _load_task(self, task_name: str) -> str:
        """
        Load task content from file.

        Args:
            task_name: Task filename.

        Returns:
            Task content.

        Raises:
            DependencyNotFoundError: If task file not found.
        """
        task_path = self.base_path / "tasks" / task_name

        if not task_path.exists():
            # Try .bmad-core path
            bmad_core_path = Path(".bmad-core") / "tasks" / task_name
            if bmad_core_path.exists():
                task_path = bmad_core_path
            else:
                raise DependencyNotFoundError(
                    "task",
                    task_name,
                    f"Task file not found in {self.base_path / 'tasks'}",
                )

        try:
            return task_path.read_text(encoding="utf-8")
        except Exception as e:
            raise TaskExecutionError(task_name, f"Failed to read task file: {str(e)}")

    def _parse_task_content(self, content: str) -> Dict[str, Any]:
        """
        Parse task content into structured format.

        Extracts purpose, execution steps, elicitation flag, etc.
        """
        lines = content.split("\n")
        task_def = {
            "purpose": "",
            "execution_steps": [],
            "elicit": False,
            "websocket_events": [],
            "current_section": None,
        }

        for line in lines:
            line = line.strip()

            # Section headers
            if line.startswith("## Purpose"):
                task_def["current_section"] = "purpose"
            elif line.startswith("## Task Execution"):
                task_def["current_section"] = "execution"
            elif line.startswith("## Elicitation Required"):
                task_def["current_section"] = "elicitation"
            elif line.startswith("## WebSocket Events"):
                task_def["current_section"] = "websocket"

            # Content parsing
            elif task_def["current_section"] == "purpose" and line:
                task_def["purpose"] += line + " "
            elif task_def["current_section"] == "execution" and line.startswith(
                ("1.", "2.", "3.", "-")
            ):
                task_def["execution_steps"].append(line)
            elif (
                task_def["current_section"] == "elicitation" and "true" in line.lower()
            ):
                task_def["elicit"] = True
            elif task_def["current_section"] == "websocket" and line.startswith("-"):
                task_def["websocket_events"].append(line[1:].strip())

        return task_def

    async def _execute_task_steps(
        self, context: ExecutionContext, task_def: Dict[str, Any]
    ) -> Any:
        """
        Execute task steps sequentially.

        Handles elicitation and WebSocket events.
        """
        # Check if we have a registered handler for this task
        task_name = self._find_task_for_command(context)
        if task_name:
            task_key = Path(task_name).stem

            # Check for registered handler
            if task_key in self._task_handlers:
                logger.debug(f"Using registered handler for task: {task_key}")
                return await self._task_handlers[task_key](context)

            # Also check if command itself has a handler
            if context.command in self._task_handlers:
                logger.debug(f"Using registered handler for command: {context.command}")
                return await self._task_handlers[context.command](context)

        # Default implementation - simulate task execution
        results = []

        # Emit task started event if WebSocket available
        if context.websocket_channel:
            await self._emit_websocket_event(
                context,
                "agent:task_started",
                {"task": context.command, "purpose": task_def["purpose"].strip()},
            )

        # Execute each step
        total_steps = len(task_def["execution_steps"])
        for i, step in enumerate(task_def["execution_steps"]):
            # Emit progress
            if context.websocket_channel:
                await self._emit_websocket_event(
                    context,
                    "agent:task_progress",
                    {
                        "current_step": i + 1,
                        "total_steps": total_steps,
                        "percentage": int((i + 1) / total_steps * 100),
                        "status": "processing",
                        "message": step,
                    },
                )

            # Handle elicitation if required
            if task_def["elicit"] and context.elicitation_handler:
                response = await context.elicitation_handler(step, i + 1)
                results.append(
                    {"step": i + 1, "description": step, "response": response}
                )
            else:
                # Simulate step execution
                results.append(
                    {"step": i + 1, "description": step, "status": "completed"}
                )

            # Small delay to simulate work
            await asyncio.sleep(0.1)

        # Emit completion
        if context.websocket_channel:
            await self._emit_websocket_event(
                context,
                "agent:task_completed",
                {"task": context.command, "steps_completed": total_steps},
            )

        return {
            "task": context.command,
            "purpose": task_def["purpose"].strip(),
            "steps_executed": results,
            "elicitation_used": task_def["elicit"],
        }

    async def _emit_websocket_event(
        self, context: ExecutionContext, event_type: str, data: Dict[str, Any]
    ) -> None:
        """
        Emit WebSocket event for real-time updates.

        Uses the websocket_progress module for actual emission.
        """
        from .websocket_progress import WEBSOCKET_AVAILABLE, sio

        event_data = {
            "case_id": context.security_context.case_id,
            "case_name": context.case_name,
            "agent_id": context.agent_def.id,
            "agent_name": context.agent_def.name,
            "task_name": context.command,
            "timestamp": datetime.utcnow().isoformat(),
            **data,
        }

        if WEBSOCKET_AVAILABLE and sio and context.websocket_channel:
            try:
                # Emit to case room for isolation
                await sio.emit(
                    event_type,
                    event_data,
                    room=f"case_{context.security_context.case_id}",
                )

                # Also emit to custom channel if specified
                if (
                    context.websocket_channel
                    != f"case_{context.security_context.case_id}"
                ):
                    await sio.emit(
                        event_type, event_data, room=context.websocket_channel
                    )

            except Exception as e:
                logger.error(
                    f"Failed to emit WebSocket event: {str(e)}",
                    extra={"event_type": event_type, "error": str(e)},
                )
        else:
            # Fallback to logging when WebSocket not available
            logger.info(
                f"WebSocket event (not emitted): {event_type}",
                extra={
                    "channel": context.websocket_channel,
                    "data": event_data,
                    "websocket_available": WEBSOCKET_AVAILABLE,
                },
            )

    def register_command_handler(
        self, command: str, handler: Callable[[ExecutionContext], Any]
    ) -> None:
        """
        Register a custom command handler.

        Args:
            command: Command name (without * prefix).
            handler: Async function to handle the command.
        """
        self._command_handlers[command] = handler
        logger.debug(f"Registered handler for command: {command}")

    async def load_dependencies(self, agent_def: AgentDefinition) -> Dict[str, Any]:
        """
        Load all dependencies for an agent.

        Args:
            agent_def: Agent definition with dependency lists.

        Returns:
            Dictionary of loaded dependencies by type.
        """
        dependencies = {"tasks": {}, "templates": {}, "checklists": {}, "data": {}}

        # Load tasks
        for task in agent_def.tasks:
            try:
                dependencies["tasks"][task] = await self._load_task(task)
            except Exception as e:
                logger.warning(f"Failed to load task {task}: {str(e)}")

        # Load templates (placeholder)
        for template in agent_def.templates:
            dependencies["templates"][template] = f"Template: {template}"

        # Load checklists (placeholder)
        for checklist in agent_def.checklists:
            dependencies["checklists"][checklist] = f"Checklist: {checklist}"

        # Load data files (placeholder)
        for data_file in agent_def.data:
            dependencies["data"][data_file] = f"Data: {data_file}"

        return dependencies
