# Agent Utilization Patterns

This document covers command execution, task chaining, workflow composition, and inter-agent communication patterns.

## Table of Contents

1. [Command Execution Engine](#command-execution-engine)
2. [Task Chaining System](#task-chaining-system)
3. [Workflow Composition](#workflow-composition)
4. [Inter-Agent Communication](#inter-agent-communication)
5. [Advanced Patterns](#advanced-patterns)

---

## Command Execution Engine

### Command Parser with Fuzzy Matching

```python
# Clerk/src/ai_agents/bmad-framework/command_engine.py

from typing import List, Dict, Any, Optional, Tuple
from dataclasses import dataclass
from difflib import get_close_matches
import shlex
import re

from .exceptions import CommandNotFoundError, InvalidCommandError


@dataclass
class ParsedCommand:
    """Parsed command structure."""
    command: str
    args: List[str]
    kwargs: Dict[str, Any]
    raw_input: str
    confidence: float = 1.0
    

class CommandParser:
    """Advanced command parser with fuzzy matching and parameter extraction."""
    
    def __init__(self, agent_def):
        self.agent_def = agent_def
        self.command_list = self._extract_command_names()
        self.command_patterns = self._build_command_patterns()
        
    def _extract_command_names(self) -> List[str]:
        """Extract command names from agent definition."""
        commands = []
        for cmd in self.agent_def.commands:
            if isinstance(cmd, str):
                # Simple format: "help: Show help"
                command_name = cmd.split(":")[0].strip()
                commands.append(command_name)
            elif isinstance(cmd, dict):
                # Complex format with parameters
                commands.extend(cmd.keys())
        return commands
    
    def _build_command_patterns(self) -> Dict[str, re.Pattern]:
        """Build regex patterns for complex commands."""
        patterns = {}
        
        # Common parameter patterns
        patterns["search"] = re.compile(r'search\s+(?P<query>.*)', re.IGNORECASE)
        patterns["analyze"] = re.compile(
            r'analyze\s+(?:--rtp-id=(?P<rtp_id>\S+))?\s*(?:--production-id=(?P<production_id>\S+))?',
            re.IGNORECASE
        )
        
        return patterns
    
    def parse(self, user_input: str) -> ParsedCommand:
        """Parse user input into command structure."""
        if not user_input:
            raise InvalidCommandError("Empty command")
        
        # Remove command prefix if present
        if user_input.startswith("*"):
            user_input = user_input[1:]
        else:
            raise InvalidCommandError("Commands must start with *")
        
        # Try exact match first
        parts = shlex.split(user_input)
        if not parts:
            raise InvalidCommandError("Invalid command format")
        
        command_name = parts[0].lower()
        
        # Check for exact match
        if command_name in self.command_list:
            return self._parse_arguments(command_name, parts[1:], user_input)
        
        # Try fuzzy matching
        matched_command = self._fuzzy_match(command_name)
        if matched_command:
            return self._parse_arguments(
                matched_command, 
                parts[1:], 
                user_input,
                confidence=self._calculate_confidence(command_name, matched_command)
            )
        
        # Try pattern matching
        for pattern_name, pattern in self.command_patterns.items():
            match = pattern.match(user_input)
            if match:
                return ParsedCommand(
                    command=pattern_name,
                    args=[],
                    kwargs=match.groupdict(),
                    raw_input=user_input
                )
        
        raise CommandNotFoundError(f"Unknown command: {command_name}")
    
    def _fuzzy_match(self, command: str) -> Optional[str]:
        """Find closest matching command."""
        matches = get_close_matches(command, self.command_list, n=1, cutoff=0.6)
        return matches[0] if matches else None
    
    def _calculate_confidence(self, input_cmd: str, matched_cmd: str) -> float:
        """Calculate confidence score for fuzzy match."""
        return len(set(input_cmd) & set(matched_cmd)) / len(set(input_cmd) | set(matched_cmd))
    
    def _parse_arguments(self, 
                        command: str, 
                        args: List[str], 
                        raw_input: str,
                        confidence: float = 1.0) -> ParsedCommand:
        """Parse command arguments and options."""
        parsed_args = []
        parsed_kwargs = {}
        
        i = 0
        while i < len(args):
            arg = args[i]
            
            # Named parameter
            if arg.startswith("--"):
                if "=" in arg:
                    key, value = arg[2:].split("=", 1)
                    parsed_kwargs[key] = value
                else:
                    # Boolean flag or next arg is value
                    key = arg[2:]
                    if i + 1 < len(args) and not args[i + 1].startswith("-"):
                        parsed_kwargs[key] = args[i + 1]
                        i += 1
                    else:
                        parsed_kwargs[key] = True
            
            # Short parameter
            elif arg.startswith("-") and len(arg) > 1:
                key = arg[1:]
                if i + 1 < len(args) and not args[i + 1].startswith("-"):
                    parsed_kwargs[key] = args[i + 1]
                    i += 1
                else:
                    parsed_kwargs[key] = True
            
            # Positional argument
            else:
                parsed_args.append(arg)
            
            i += 1
        
        return ParsedCommand(
            command=command,
            args=parsed_args,
            kwargs=parsed_kwargs,
            raw_input=raw_input,
            confidence=confidence
        )
```

### Parameter Validation Framework

```python
from typing import Type, Union, get_type_hints
from pydantic import BaseModel, ValidationError


class ParameterValidator:
    """Validate command parameters against schemas."""
    
    def __init__(self):
        self.schemas = {}
        self.type_converters = {
            int: self._convert_int,
            float: self._convert_float,
            bool: self._convert_bool,
            str: str,
            list: self._convert_list,
            dict: self._convert_dict
        }
    
    def register_schema(self, command: str, schema: Type[BaseModel]):
        """Register parameter schema for command."""
        self.schemas[command] = schema
    
    async def validate(self, 
                      command: str, 
                      args: List[str], 
                      kwargs: Dict[str, Any]) -> Dict[str, Any]:
        """Validate and convert parameters."""
        if command not in self.schemas:
            # No schema, pass through
            return {"args": args, **kwargs}
        
        schema = self.schemas[command]
        
        # Convert args to kwargs based on schema
        converted = await self._args_to_kwargs(schema, args, kwargs)
        
        # Validate with schema
        try:
            validated = schema(**converted)
            return validated.dict()
        except ValidationError as e:
            raise InvalidCommandError(f"Invalid parameters: {e}")
    
    async def _args_to_kwargs(self,
                             schema: Type[BaseModel],
                             args: List[str],
                             kwargs: Dict[str, Any]) -> Dict[str, Any]:
        """Convert positional args to kwargs based on schema."""
        hints = get_type_hints(schema)
        field_names = list(schema.__fields__.keys())
        
        result = kwargs.copy()
        
        # Map positional args to field names
        for i, arg in enumerate(args):
            if i < len(field_names):
                field_name = field_names[i]
                if field_name not in result:  # Don't override kwargs
                    field_type = hints.get(field_name, str)
                    result[field_name] = await self._convert_type(arg, field_type)
        
        return result
    
    async def _convert_type(self, value: str, target_type: Type) -> Any:
        """Convert string value to target type."""
        # Handle Optional types
        if hasattr(target_type, "__origin__") and target_type.__origin__ is Union:
            # Get the non-None type
            for arg in target_type.__args__:
                if arg is not type(None):
                    target_type = arg
                    break
        
        # Convert using registered converter
        converter = self.type_converters.get(target_type, str)
        return converter(value)
    
    def _convert_int(self, value: str) -> int:
        """Convert to integer."""
        try:
            return int(value)
        except ValueError:
            raise InvalidCommandError(f"Invalid integer: {value}")
    
    def _convert_float(self, value: str) -> float:
        """Convert to float."""
        try:
            return float(value)
        except ValueError:
            raise InvalidCommandError(f"Invalid float: {value}")
    
    def _convert_bool(self, value: str) -> bool:
        """Convert to boolean."""
        return value.lower() in ("true", "yes", "1", "on")
    
    def _convert_list(self, value: str) -> List[str]:
        """Convert comma-separated to list."""
        return [v.strip() for v in value.split(",")]
    
    def _convert_dict(self, value: str) -> Dict[str, Any]:
        """Convert JSON string to dict."""
        import json
        try:
            return json.loads(value)
        except json.JSONDecodeError:
            raise InvalidCommandError(f"Invalid JSON: {value}")
```

### Async Command Execution

```python
import asyncio
from typing import Callable, Awaitable
from concurrent.futures import ThreadPoolExecutor


class AsyncCommandExecutor:
    """Execute commands asynchronously with timeout and cancellation."""
    
    def __init__(self, max_workers: int = 5):
        self.executor = ThreadPoolExecutor(max_workers=max_workers)
        self.running_tasks = {}
        self.command_handlers = {}
    
    def register_handler(self, 
                        command: str, 
                        handler: Callable[..., Awaitable[Any]]):
        """Register async command handler."""
        self.command_handlers[command] = handler
    
    async def execute(self,
                     command: ParsedCommand,
                     context: Dict[str, Any],
                     timeout: Optional[float] = None) -> Any:
        """Execute command with optional timeout."""
        if command.command not in self.command_handlers:
            raise CommandNotFoundError(f"No handler for: {command.command}")
        
        handler = self.command_handlers[command.command]
        
        # Create task
        task_id = f"{command.command}_{id(command)}"
        task = asyncio.create_task(
            self._execute_with_context(handler, command, context)
        )
        self.running_tasks[task_id] = task
        
        try:
            # Execute with timeout
            result = await asyncio.wait_for(task, timeout=timeout)
            return result
            
        except asyncio.TimeoutError:
            # Cancel task
            task.cancel()
            raise CommandTimeoutError(f"Command {command.command} timed out")
            
        finally:
            # Clean up
            self.running_tasks.pop(task_id, None)
    
    async def _execute_with_context(self,
                                   handler: Callable,
                                   command: ParsedCommand,
                                   context: Dict[str, Any]) -> Any:
        """Execute handler with context injection."""
        # Inject context
        handler_context = {
            "command": command,
            "case_name": context.get("case_name"),
            "security_context": context.get("security_context"),
            "agent_def": context.get("agent_def")
        }
        
        # Execute handler
        return await handler(**handler_context, **command.kwargs)
    
    async def cancel_command(self, task_id: str) -> bool:
        """Cancel running command."""
        if task_id in self.running_tasks:
            task = self.running_tasks[task_id]
            task.cancel()
            return True
        return False
    
    def get_running_commands(self) -> List[str]:
        """Get list of running command IDs."""
        return list(self.running_tasks.keys())
```

### Result Formatting Pipeline

```python
from abc import ABC, abstractmethod
from typing import Any


class ResultFormatter(ABC):
    """Base class for result formatters."""
    
    @abstractmethod
    async def format(self, result: Any, context: Dict[str, Any]) -> Any:
        """Format command result."""
        pass


class TextResultFormatter(ResultFormatter):
    """Format results as human-readable text."""
    
    async def format(self, result: Any, context: Dict[str, Any]) -> str:
        """Format result as text."""
        if isinstance(result, dict):
            return self._format_dict(result)
        elif isinstance(result, list):
            return self._format_list(result)
        elif isinstance(result, BaseModel):
            return self._format_model(result)
        else:
            return str(result)
    
    def _format_dict(self, data: Dict[str, Any], indent: int = 0) -> str:
        """Format dictionary as indented text."""
        lines = []
        for key, value in data.items():
            prefix = "  " * indent
            if isinstance(value, (dict, list)):
                lines.append(f"{prefix}{key}:")
                if isinstance(value, dict):
                    lines.append(self._format_dict(value, indent + 1))
                else:
                    lines.append(self._format_list(value, indent + 1))
            else:
                lines.append(f"{prefix}{key}: {value}")
        
        return "\n".join(lines)
    
    def _format_list(self, data: List[Any], indent: int = 0) -> str:
        """Format list as numbered items."""
        lines = []
        prefix = "  " * indent
        
        for i, item in enumerate(data, 1):
            if isinstance(item, dict):
                lines.append(f"{prefix}{i}.")
                lines.append(self._format_dict(item, indent + 1))
            else:
                lines.append(f"{prefix}{i}. {item}")
        
        return "\n".join(lines)
    
    def _format_model(self, model: BaseModel) -> str:
        """Format Pydantic model."""
        return self._format_dict(model.dict())


class JSONResultFormatter(ResultFormatter):
    """Format results as JSON."""
    
    async def format(self, result: Any, context: Dict[str, Any]) -> str:
        """Format result as JSON."""
        import json
        
        if isinstance(result, BaseModel):
            data = result.dict()
        elif hasattr(result, "__dict__"):
            data = result.__dict__
        else:
            data = result
        
        return json.dumps(data, indent=2, default=str)


class TableResultFormatter(ResultFormatter):
    """Format results as ASCII table."""
    
    async def format(self, result: Any, context: Dict[str, Any]) -> str:
        """Format result as table."""
        if isinstance(result, list) and all(isinstance(item, dict) for item in result):
            return self._format_table(result)
        elif isinstance(result, dict):
            return self._format_dict_table(result)
        else:
            # Fallback to text
            formatter = TextResultFormatter()
            return await formatter.format(result, context)
    
    def _format_table(self, data: List[Dict[str, Any]]) -> str:
        """Format list of dicts as table."""
        if not data:
            return "No data"
        
        # Get column names
        columns = list(data[0].keys())
        
        # Calculate column widths
        widths = {}
        for col in columns:
            widths[col] = max(
                len(str(col)),
                max(len(str(row.get(col, ""))) for row in data)
            )
        
        # Build table
        lines = []
        
        # Header
        header = " | ".join(col.ljust(widths[col]) for col in columns)
        lines.append(header)
        lines.append("-" * len(header))
        
        # Rows
        for row in data:
            row_str = " | ".join(
                str(row.get(col, "")).ljust(widths[col]) for col in columns
            )
            lines.append(row_str)
        
        return "\n".join(lines)
    
    def _format_dict_table(self, data: Dict[str, Any]) -> str:
        """Format dict as two-column table."""
        lines = []
        
        # Calculate widths
        key_width = max(len(str(k)) for k in data.keys())
        value_width = max(len(str(v)) for v in data.values())
        
        # Header
        header = f"{'Key'.ljust(key_width)} | {'Value'.ljust(value_width)}"
        lines.append(header)
        lines.append("-" * len(header))
        
        # Rows
        for key, value in data.items():
            lines.append(f"{str(key).ljust(key_width)} | {str(value).ljust(value_width)}")
        
        return "\n".join(lines)


class FormatterPipeline:
    """Pipeline for result formatting."""
    
    def __init__(self):
        self.formatters = {
            "text": TextResultFormatter(),
            "json": JSONResultFormatter(),
            "table": TableResultFormatter()
        }
        self.default_format = "text"
    
    async def format(self,
                    result: Any,
                    format_type: Optional[str] = None,
                    context: Dict[str, Any] = None) -> Any:
        """Format result using specified formatter."""
        format_type = format_type or self.default_format
        
        if format_type not in self.formatters:
            format_type = self.default_format
        
        formatter = self.formatters[format_type]
        return await formatter.format(result, context or {})
```

---

## Task Chaining System

### Task Dependency Resolver

```python
from typing import Set, List, Dict, Any
from collections import defaultdict
import networkx as nx


@dataclass 
class Task:
    """Task definition."""
    name: str
    dependencies: List[str]
    handler: Callable
    params: Dict[str, Any]
    parallel_safe: bool = True
    

class TaskDependencyResolver:
    """Resolve task dependencies and execution order."""
    
    def __init__(self):
        self.tasks = {}
        self.dependency_graph = nx.DiGraph()
    
    def register_task(self, task: Task):
        """Register task with dependencies."""
        self.tasks[task.name] = task
        self.dependency_graph.add_node(task.name)
        
        # Add dependency edges
        for dep in task.dependencies:
            self.dependency_graph.add_edge(dep, task.name)
    
    def resolve_execution_order(self, target_tasks: List[str]) -> List[List[str]]:
        """
        Resolve execution order for target tasks.
        Returns list of task groups that can run in parallel.
        """
        # Get all required tasks
        required_tasks = set()
        for task in target_tasks:
            required_tasks.update(nx.ancestors(self.dependency_graph, task))
            required_tasks.add(task)
        
        # Create subgraph of required tasks
        subgraph = self.dependency_graph.subgraph(required_tasks)
        
        # Check for cycles
        if not nx.is_directed_acyclic_graph(subgraph):
            cycles = list(nx.simple_cycles(subgraph))
            raise ValueError(f"Circular dependencies detected: {cycles}")
        
        # Get execution levels
        levels = self._get_execution_levels(subgraph)
        
        return levels
    
    def _get_execution_levels(self, graph: nx.DiGraph) -> List[List[str]]:
        """Get tasks grouped by execution level."""
        levels = []
        remaining = set(graph.nodes())
        
        while remaining:
            # Find tasks with no dependencies in remaining set
            level = []
            for task in remaining:
                predecessors = set(graph.predecessors(task))
                if not predecessors.intersection(remaining):
                    level.append(task)
            
            if not level:
                # Should not happen if graph is DAG
                raise ValueError("Failed to resolve execution order")
            
            levels.append(level)
            remaining -= set(level)
        
        return levels
    
    def validate_dependencies(self) -> List[str]:
        """Validate all dependencies exist."""
        errors = []
        
        for task_name, task in self.tasks.items():
            for dep in task.dependencies:
                if dep not in self.tasks:
                    errors.append(f"Task {task_name} depends on unknown task {dep}")
        
        return errors
```

### Sequential Task Execution

```python
class SequentialTaskExecutor:
    """Execute tasks in sequential order."""
    
    def __init__(self, resolver: TaskDependencyResolver):
        self.resolver = resolver
        self.execution_history = []
        self.results = {}
    
    async def execute(self,
                     target_tasks: List[str],
                     context: Dict[str, Any],
                     progress_callback: Optional[Callable] = None) -> Dict[str, Any]:
        """Execute tasks sequentially."""
        # Resolve execution order
        execution_levels = self.resolver.resolve_execution_order(target_tasks)
        
        total_tasks = sum(len(level) for level in execution_levels)
        completed_tasks = 0
        
        # Execute each level
        for level_idx, level_tasks in enumerate(execution_levels):
            for task_name in level_tasks:
                # Get task
                task = self.resolver.tasks[task_name]
                
                # Prepare context with previous results
                task_context = {
                    **context,
                    "previous_results": self.results.copy(),
                    "task_name": task_name
                }
                
                # Report progress
                if progress_callback:
                    await progress_callback({
                        "task": task_name,
                        "completed": completed_tasks,
                        "total": total_tasks,
                        "percentage": (completed_tasks / total_tasks) * 100
                    })
                
                # Execute task
                try:
                    result = await task.handler(**task_context, **task.params)
                    self.results[task_name] = result
                    self.execution_history.append({
                        "task": task_name,
                        "status": "success",
                        "result": result,
                        "timestamp": datetime.now()
                    })
                    
                except Exception as e:
                    self.execution_history.append({
                        "task": task_name,
                        "status": "failed",
                        "error": str(e),
                        "timestamp": datetime.now()
                    })
                    raise TaskExecutionError(f"Task {task_name} failed: {e}")
                
                completed_tasks += 1
        
        # Final progress
        if progress_callback:
            await progress_callback({
                "completed": total_tasks,
                "total": total_tasks,
                "percentage": 100,
                "status": "completed"
            })
        
        return self.results
```

### Parallel Task Support

```python
class ParallelTaskExecutor:
    """Execute independent tasks in parallel."""
    
    def __init__(self, 
                 resolver: TaskDependencyResolver,
                 max_concurrent: int = 5):
        self.resolver = resolver
        self.max_concurrent = max_concurrent
        self.semaphore = asyncio.Semaphore(max_concurrent)
    
    async def execute(self,
                     target_tasks: List[str],
                     context: Dict[str, Any],
                     progress_callback: Optional[Callable] = None) -> Dict[str, Any]:
        """Execute tasks with parallelism where possible."""
        # Resolve execution order
        execution_levels = self.resolver.resolve_execution_order(target_tasks)
        
        results = {}
        total_tasks = sum(len(level) for level in execution_levels)
        completed_tasks = 0
        
        # Execute each level
        for level_idx, level_tasks in enumerate(execution_levels):
            # Filter parallel-safe tasks
            parallel_tasks = []
            sequential_tasks = []
            
            for task_name in level_tasks:
                task = self.resolver.tasks[task_name]
                if task.parallel_safe:
                    parallel_tasks.append(task_name)
                else:
                    sequential_tasks.append(task_name)
            
            # Execute parallel tasks
            if parallel_tasks:
                level_results = await self._execute_parallel(
                    parallel_tasks, 
                    context, 
                    results,
                    progress_callback,
                    completed_tasks,
                    total_tasks
                )
                results.update(level_results)
                completed_tasks += len(parallel_tasks)
            
            # Execute sequential tasks
            for task_name in sequential_tasks:
                task_result = await self._execute_single(
                    task_name,
                    context,
                    results
                )
                results[task_name] = task_result
                completed_tasks += 1
                
                if progress_callback:
                    await progress_callback({
                        "task": task_name,
                        "completed": completed_tasks,
                        "total": total_tasks,
                        "percentage": (completed_tasks / total_tasks) * 100
                    })
        
        return results
    
    async def _execute_parallel(self,
                               task_names: List[str],
                               context: Dict[str, Any],
                               previous_results: Dict[str, Any],
                               progress_callback: Optional[Callable],
                               completed_count: int,
                               total_count: int) -> Dict[str, Any]:
        """Execute tasks in parallel."""
        tasks = []
        
        for task_name in task_names:
            task = self._create_task_coroutine(
                task_name,
                context,
                previous_results,
                progress_callback,
                completed_count,
                total_count
            )
            tasks.append(task)
        
        # Execute all tasks
        results = await asyncio.gather(*tasks, return_exceptions=True)
        
        # Process results
        task_results = {}
        for task_name, result in zip(task_names, results):
            if isinstance(result, Exception):
                raise TaskExecutionError(f"Task {task_name} failed: {result}")
            task_results[task_name] = result
        
        return task_results
    
    async def _create_task_coroutine(self,
                                    task_name: str,
                                    context: Dict[str, Any],
                                    previous_results: Dict[str, Any],
                                    progress_callback: Optional[Callable],
                                    completed_count: int,
                                    total_count: int):
        """Create task coroutine with semaphore."""
        async with self.semaphore:
            return await self._execute_single(task_name, context, previous_results)
    
    async def _execute_single(self,
                             task_name: str,
                             context: Dict[str, Any],
                             previous_results: Dict[str, Any]) -> Any:
        """Execute single task."""
        task = self.resolver.tasks[task_name]
        
        task_context = {
            **context,
            "previous_results": previous_results.copy(),
            "task_name": task_name
        }
        
        return await task.handler(**task_context, **task.params)
```

### Conditional Task Branching

```python
from typing import Callable, Any


class ConditionalTaskExecutor:
    """Execute tasks with conditional branching."""
    
    def __init__(self, resolver: TaskDependencyResolver):
        self.resolver = resolver
        self.conditions = {}
        self.branch_history = []
    
    def register_condition(self,
                          name: str,
                          evaluator: Callable[[Dict[str, Any]], bool]):
        """Register branching condition."""
        self.conditions[name] = evaluator
    
    async def execute_conditional(self,
                                 workflow: Dict[str, Any],
                                 context: Dict[str, Any]) -> Dict[str, Any]:
        """Execute workflow with conditional branches."""
        results = {}
        current_node = workflow.get("start", "main")
        
        while current_node:
            node_def = workflow["nodes"][current_node]
            
            # Execute node based on type
            if node_def["type"] == "task":
                # Execute task
                task_name = node_def["task"]
                result = await self._execute_task(task_name, context, results)
                results[task_name] = result
                
                # Next node
                current_node = node_def.get("next")
                
            elif node_def["type"] == "condition":
                # Evaluate condition
                condition_name = node_def["condition"]
                condition_context = {
                    **context,
                    "results": results
                }
                
                if self.conditions[condition_name](condition_context):
                    current_node = node_def.get("true_branch")
                    self.branch_history.append({
                        "condition": condition_name,
                        "result": True,
                        "branch": current_node
                    })
                else:
                    current_node = node_def.get("false_branch")
                    self.branch_history.append({
                        "condition": condition_name,
                        "result": False,
                        "branch": current_node
                    })
                    
            elif node_def["type"] == "parallel":
                # Execute parallel branches
                branches = node_def["branches"]
                branch_results = await self._execute_parallel_branches(
                    branches, 
                    context, 
                    results
                )
                results.update(branch_results)
                
                # Next node
                current_node = node_def.get("next")
                
            elif node_def["type"] == "end":
                # Workflow complete
                current_node = None
            
            else:
                raise ValueError(f"Unknown node type: {node_def['type']}")
        
        return results
    
    async def _execute_task(self,
                           task_name: str,
                           context: Dict[str, Any],
                           previous_results: Dict[str, Any]) -> Any:
        """Execute single task."""
        if task_name not in self.resolver.tasks:
            raise TaskNotFoundError(f"Task not found: {task_name}")
        
        task = self.resolver.tasks[task_name]
        task_context = {
            **context,
            "previous_results": previous_results
        }
        
        return await task.handler(**task_context, **task.params)
    
    async def _execute_parallel_branches(self,
                                       branches: List[str],
                                       context: Dict[str, Any],
                                       previous_results: Dict[str, Any]) -> Dict[str, Any]:
        """Execute multiple branches in parallel."""
        tasks = []
        
        for branch in branches:
            branch_workflow = {
                "start": branch,
                "nodes": context["workflow"]["nodes"]
            }
            task = self.execute_conditional(branch_workflow, context)
            tasks.append(task)
        
        branch_results = await asyncio.gather(*tasks)
        
        # Merge results
        merged_results = {}
        for result in branch_results:
            merged_results.update(result)
        
        return merged_results
```

---

## Workflow Composition

### Workflow Definition Language

```python
from typing import List, Dict, Any, Optional
from enum import Enum
import yaml


class NodeType(Enum):
    """Workflow node types."""
    TASK = "task"
    CONDITION = "condition"
    PARALLEL = "parallel"
    LOOP = "loop"
    SUBWORKFLOW = "subworkflow"
    END = "end"


@dataclass
class WorkflowNode:
    """Workflow node definition."""
    id: str
    type: NodeType
    config: Dict[str, Any]
    next: Optional[str] = None
    

@dataclass
class WorkflowDefinition:
    """Complete workflow definition."""
    name: str
    version: str
    description: str
    start_node: str
    nodes: Dict[str, WorkflowNode]
    variables: Dict[str, Any]
    error_handlers: Dict[str, str]


class WorkflowParser:
    """Parse workflow definitions from YAML."""
    
    def parse(self, yaml_content: str) -> WorkflowDefinition:
        """Parse YAML workflow definition."""
        data = yaml.safe_load(yaml_content)
        
        # Parse nodes
        nodes = {}
        for node_id, node_data in data.get("nodes", {}).items():
            node = WorkflowNode(
                id=node_id,
                type=NodeType(node_data["type"]),
                config=node_data.get("config", {}),
                next=node_data.get("next")
            )
            nodes[node_id] = node
        
        # Create workflow definition
        return WorkflowDefinition(
            name=data["name"],
            version=data.get("version", "1.0"),
            description=data.get("description", ""),
            start_node=data.get("start", "main"),
            nodes=nodes,
            variables=data.get("variables", {}),
            error_handlers=data.get("error_handlers", {})
        )


# Example workflow YAML
EXAMPLE_WORKFLOW = """
name: discovery_analysis_workflow
version: "1.0"
description: Complete discovery deficiency analysis workflow

start: validate_inputs

variables:
  max_retries: 3
  confidence_threshold: 0.8

nodes:
  validate_inputs:
    type: task
    config:
      task: validate_analysis_inputs
      timeout: 30
    next: load_documents
    
  load_documents:
    type: parallel
    config:
      branches:
        - load_rtp
        - load_production
        - load_oc_response
    next: check_load_status
    
  load_rtp:
    type: task
    config:
      task: load_rtp_document
      
  load_production:
    type: task
    config:
      task: load_production_documents
      
  load_oc_response:
    type: task
    config:
      task: load_oc_response_document
      
  check_load_status:
    type: condition
    config:
      condition: all_documents_loaded
      true_branch: parse_rtp
      false_branch: handle_missing_docs
      
  parse_rtp:
    type: task
    config:
      task: parse_rtp_requests
    next: analyze_loop
    
  analyze_loop:
    type: loop
    config:
      items: "${results.rtp_requests}"
      item_var: request
      body: analyze_single_request
    next: generate_report
    
  analyze_single_request:
    type: subworkflow
    config:
      workflow: single_request_analysis
      inputs:
        request: "${request}"
        
  generate_report:
    type: task
    config:
      task: generate_deficiency_report
    next: end
    
  handle_missing_docs:
    type: task
    config:
      task: report_missing_documents
    next: end
    
  end:
    type: end

error_handlers:
  parse_error: handle_parse_error
  analysis_error: retry_with_backoff
"""
```

### Visual Workflow Designer Specs

```python
@dataclass
class VisualNode:
    """Visual representation of workflow node."""
    id: str
    type: NodeType
    position: Tuple[float, float]
    size: Tuple[float, float]
    label: str
    color: str
    inputs: List[str]
    outputs: List[str]
    

@dataclass
class VisualEdge:
    """Visual representation of workflow edge."""
    id: str
    source: str
    target: str
    label: Optional[str] = None
    style: str = "solid"
    

class WorkflowVisualizer:
    """Generate visual representation of workflows."""
    
    def __init__(self):
        self.node_colors = {
            NodeType.TASK: "#4CAF50",
            NodeType.CONDITION: "#FF9800",
            NodeType.PARALLEL: "#2196F3",
            NodeType.LOOP: "#9C27B0",
            NodeType.SUBWORKFLOW: "#00BCD4",
            NodeType.END: "#F44336"
        }
    
    def visualize(self, workflow: WorkflowDefinition) -> Dict[str, Any]:
        """Generate visual representation."""
        nodes = []
        edges = []
        
        # Layout nodes
        positions = self._calculate_layout(workflow)
        
        # Create visual nodes
        for node_id, node in workflow.nodes.items():
            visual_node = VisualNode(
                id=node_id,
                type=node.type,
                position=positions[node_id],
                size=(120, 60),
                label=self._get_node_label(node),
                color=self.node_colors[node.type],
                inputs=self._get_node_inputs(node),
                outputs=self._get_node_outputs(node)
            )
            nodes.append(visual_node)
        
        # Create edges
        for node_id, node in workflow.nodes.items():
            if node.next:
                edge = VisualEdge(
                    id=f"{node_id}->{node.next}",
                    source=node_id,
                    target=node.next
                )
                edges.append(edge)
            
            # Conditional branches
            if node.type == NodeType.CONDITION:
                if "true_branch" in node.config:
                    edge = VisualEdge(
                        id=f"{node_id}->{node.config['true_branch']}",
                        source=node_id,
                        target=node.config["true_branch"],
                        label="True",
                        style="dashed"
                    )
                    edges.append(edge)
                
                if "false_branch" in node.config:
                    edge = VisualEdge(
                        id=f"{node_id}->{node.config['false_branch']}",
                        source=node_id,
                        target=node.config["false_branch"],
                        label="False",
                        style="dotted"
                    )
                    edges.append(edge)
        
        return {
            "nodes": [n.__dict__ for n in nodes],
            "edges": [e.__dict__ for e in edges],
            "layout": "hierarchical"
        }
    
    def _calculate_layout(self, workflow: WorkflowDefinition) -> Dict[str, Tuple[float, float]]:
        """Calculate node positions using hierarchical layout."""
        import networkx as nx
        
        # Build graph
        G = nx.DiGraph()
        for node_id, node in workflow.nodes.items():
            G.add_node(node_id)
            if node.next:
                G.add_edge(node_id, node.next)
        
        # Calculate positions
        pos = nx.spring_layout(G, k=2, iterations=50)
        
        # Scale to canvas size
        canvas_width = 800
        canvas_height = 600
        
        positions = {}
        for node_id, (x, y) in pos.items():
            positions[node_id] = (
                (x + 1) * canvas_width / 2,
                (y + 1) * canvas_height / 2
            )
        
        return positions
    
    def _get_node_label(self, node: WorkflowNode) -> str:
        """Get display label for node."""
        if node.type == NodeType.TASK:
            return node.config.get("task", node.id)
        elif node.type == NodeType.CONDITION:
            return node.config.get("condition", node.id)
        else:
            return node.id
    
    def _get_node_inputs(self, node: WorkflowNode) -> List[str]:
        """Get node input parameters."""
        return node.config.get("inputs", [])
    
    def _get_node_outputs(self, node: WorkflowNode) -> List[str]:
        """Get node output parameters."""
        return node.config.get("outputs", [])
```

### Workflow Validation

```python
class WorkflowValidator:
    """Validate workflow definitions."""
    
    def __init__(self, task_registry: Optional[Dict[str, Task]] = None):
        self.task_registry = task_registry or {}
        self.validators = {
            NodeType.TASK: self._validate_task_node,
            NodeType.CONDITION: self._validate_condition_node,
            NodeType.PARALLEL: self._validate_parallel_node,
            NodeType.LOOP: self._validate_loop_node,
            NodeType.SUBWORKFLOW: self._validate_subworkflow_node,
            NodeType.END: self._validate_end_node
        }
    
    def validate(self, workflow: WorkflowDefinition) -> List[str]:
        """Validate complete workflow."""
        errors = []
        
        # Check start node exists
        if workflow.start_node not in workflow.nodes:
            errors.append(f"Start node '{workflow.start_node}' not found")
        
        # Validate each node
        for node_id, node in workflow.nodes.items():
            node_errors = self._validate_node(node)
            errors.extend(node_errors)
        
        # Check for unreachable nodes
        unreachable = self._find_unreachable_nodes(workflow)
        if unreachable:
            errors.append(f"Unreachable nodes: {unreachable}")
        
        # Check for cycles
        if self._has_cycles(workflow):
            errors.append("Workflow contains cycles")
        
        # Validate variables
        var_errors = self._validate_variables(workflow)
        errors.extend(var_errors)
        
        return errors
    
    def _validate_node(self, node: WorkflowNode) -> List[str]:
        """Validate individual node."""
        if node.type not in self.validators:
            return [f"Unknown node type: {node.type}"]
        
        return self.validators[node.type](node)
    
    def _validate_task_node(self, node: WorkflowNode) -> List[str]:
        """Validate task node."""
        errors = []
        
        task_name = node.config.get("task")
        if not task_name:
            errors.append(f"Task node {node.id} missing 'task' config")
        elif self.task_registry and task_name not in self.task_registry:
            errors.append(f"Unknown task: {task_name}")
        
        return errors
    
    def _validate_condition_node(self, node: WorkflowNode) -> List[str]:
        """Validate condition node."""
        errors = []
        
        if "condition" not in node.config:
            errors.append(f"Condition node {node.id} missing 'condition' config")
        
        if "true_branch" not in node.config:
            errors.append(f"Condition node {node.id} missing 'true_branch'")
        
        if "false_branch" not in node.config:
            errors.append(f"Condition node {node.id} missing 'false_branch'")
        
        return errors
    
    def _validate_parallel_node(self, node: WorkflowNode) -> List[str]:
        """Validate parallel node."""
        errors = []
        
        branches = node.config.get("branches", [])
        if not branches:
            errors.append(f"Parallel node {node.id} has no branches")
        
        return errors
    
    def _validate_loop_node(self, node: WorkflowNode) -> List[str]:
        """Validate loop node."""
        errors = []
        
        if "items" not in node.config:
            errors.append(f"Loop node {node.id} missing 'items' config")
        
        if "body" not in node.config:
            errors.append(f"Loop node {node.id} missing 'body' config")
        
        return errors
    
    def _validate_subworkflow_node(self, node: WorkflowNode) -> List[str]:
        """Validate subworkflow node."""
        errors = []
        
        if "workflow" not in node.config:
            errors.append(f"Subworkflow node {node.id} missing 'workflow' config")
        
        return errors
    
    def _validate_end_node(self, node: WorkflowNode) -> List[str]:
        """Validate end node."""
        # End nodes are always valid
        return []
    
    def _find_unreachable_nodes(self, workflow: WorkflowDefinition) -> Set[str]:
        """Find nodes not reachable from start."""
        import networkx as nx
        
        # Build graph
        G = nx.DiGraph()
        for node_id in workflow.nodes:
            G.add_node(node_id)
        
        for node_id, node in workflow.nodes.items():
            # Add regular edges
            if node.next:
                G.add_edge(node_id, node.next)
            
            # Add conditional edges
            if node.type == NodeType.CONDITION:
                if "true_branch" in node.config:
                    G.add_edge(node_id, node.config["true_branch"])
                if "false_branch" in node.config:
                    G.add_edge(node_id, node.config["false_branch"])
            
            # Add parallel edges
            elif node.type == NodeType.PARALLEL:
                for branch in node.config.get("branches", []):
                    if branch in workflow.nodes:
                        G.add_edge(node_id, branch)
        
        # Find reachable nodes
        reachable = nx.descendants(G, workflow.start_node)
        reachable.add(workflow.start_node)
        
        # Find unreachable
        all_nodes = set(workflow.nodes.keys())
        unreachable = all_nodes - reachable
        
        return unreachable
    
    def _has_cycles(self, workflow: WorkflowDefinition) -> bool:
        """Check if workflow has cycles."""
        import networkx as nx
        
        # Build graph (similar to above)
        G = nx.DiGraph()
        # ... (graph building code)
        
        return not nx.is_directed_acyclic_graph(G)
    
    def _validate_variables(self, workflow: WorkflowDefinition) -> List[str]:
        """Validate workflow variables."""
        errors = []
        
        # Check variable references in nodes
        for node_id, node in workflow.nodes.items():
            for key, value in node.config.items():
                if isinstance(value, str) and value.startswith("${"):
                    var_name = value[2:-1].split(".")[0]
                    if var_name not in workflow.variables:
                        errors.append(
                            f"Node {node_id} references undefined variable: {var_name}"
                        )
        
        return errors
```

### Runtime Workflow Modification

```python
class DynamicWorkflowModifier:
    """Modify workflows at runtime."""
    
    def __init__(self, workflow: WorkflowDefinition):
        self.workflow = workflow
        self.modifications = []
    
    def add_node(self, 
                 node: WorkflowNode,
                 after: Optional[str] = None,
                 before: Optional[str] = None) -> None:
        """Add node to workflow."""
        # Add to nodes
        self.workflow.nodes[node.id] = node
        
        # Update connections
        if after and after in self.workflow.nodes:
            # Insert after specified node
            after_node = self.workflow.nodes[after]
            old_next = after_node.next
            after_node.next = node.id
            node.next = old_next
            
        elif before and before in self.workflow.nodes:
            # Insert before specified node
            # Find nodes pointing to 'before'
            for n_id, n in self.workflow.nodes.items():
                if n.next == before:
                    n.next = node.id
            node.next = before
        
        self.modifications.append({
            "action": "add_node",
            "node": node.id,
            "timestamp": datetime.now()
        })
    
    def remove_node(self, node_id: str) -> None:
        """Remove node from workflow."""
        if node_id not in self.workflow.nodes:
            raise ValueError(f"Node {node_id} not found")
        
        node = self.workflow.nodes[node_id]
        
        # Update connections to bypass removed node
        for n_id, n in self.workflow.nodes.items():
            if n.next == node_id:
                n.next = node.next
            
            # Update conditional branches
            if n.type == NodeType.CONDITION:
                if n.config.get("true_branch") == node_id:
                    n.config["true_branch"] = node.next
                if n.config.get("false_branch") == node_id:
                    n.config["false_branch"] = node.next
        
        # Remove node
        del self.workflow.nodes[node_id]
        
        self.modifications.append({
            "action": "remove_node",
            "node": node_id,
            "timestamp": datetime.now()
        })
    
    def modify_node_config(self, 
                          node_id: str,
                          config_updates: Dict[str, Any]) -> None:
        """Modify node configuration."""
        if node_id not in self.workflow.nodes:
            raise ValueError(f"Node {node_id} not found")
        
        node = self.workflow.nodes[node_id]
        old_config = node.config.copy()
        
        # Update config
        node.config.update(config_updates)
        
        self.modifications.append({
            "action": "modify_config",
            "node": node_id,
            "old_config": old_config,
            "new_config": node.config,
            "timestamp": datetime.now()
        })
    
    def add_branch(self,
                   condition_node_id: str,
                   branch_type: str,
                   target_node_id: str) -> None:
        """Add branch to condition node."""
        if condition_node_id not in self.workflow.nodes:
            raise ValueError(f"Node {condition_node_id} not found")
        
        node = self.workflow.nodes[condition_node_id]
        if node.type != NodeType.CONDITION:
            raise ValueError(f"Node {condition_node_id} is not a condition node")
        
        if branch_type == "true":
            node.config["true_branch"] = target_node_id
        elif branch_type == "false":
            node.config["false_branch"] = target_node_id
        else:
            raise ValueError(f"Invalid branch type: {branch_type}")
        
        self.modifications.append({
            "action": "add_branch",
            "node": condition_node_id,
            "branch_type": branch_type,
            "target": target_node_id,
            "timestamp": datetime.now()
        })
    
    def get_modification_history(self) -> List[Dict[str, Any]]:
        """Get history of modifications."""
        return self.modifications.copy()
    
    def validate_modifications(self) -> List[str]:
        """Validate workflow after modifications."""
        validator = WorkflowValidator()
        return validator.validate(self.workflow)
```

---

## Inter-Agent Communication

### Agent Discovery Protocol

```python
@dataclass
class AgentInfo:
    """Agent information for discovery."""
    id: str
    name: str
    version: str
    capabilities: List[str]
    status: str
    endpoint: str
    last_seen: datetime


class AgentRegistry:
    """Central registry for agent discovery."""
    
    def __init__(self):
        self.agents: Dict[str, AgentInfo] = {}
        self.capabilities_index: Dict[str, Set[str]] = defaultdict(set)
        self.heartbeat_interval = 30  # seconds
    
    async def register(self, agent_info: AgentInfo) -> None:
        """Register agent in registry."""
        self.agents[agent_info.id] = agent_info
        
        # Index by capabilities
        for capability in agent_info.capabilities:
            self.capabilities_index[capability].add(agent_info.id)
        
        # Log registration
        logger.info(f"Agent {agent_info.id} registered with capabilities: {agent_info.capabilities}")
    
    async def unregister(self, agent_id: str) -> None:
        """Remove agent from registry."""
        if agent_id in self.agents:
            agent_info = self.agents[agent_id]
            
            # Remove from capabilities index
            for capability in agent_info.capabilities:
                self.capabilities_index[capability].discard(agent_id)
            
            # Remove agent
            del self.agents[agent_id]
            
            logger.info(f"Agent {agent_id} unregistered")
    
    async def discover(self, 
                      capability: Optional[str] = None,
                      status: Optional[str] = None) -> List[AgentInfo]:
        """Discover agents by capability or status."""
        agents = []
        
        if capability:
            # Find by capability
            agent_ids = self.capabilities_index.get(capability, set())
            agents = [self.agents[aid] for aid in agent_ids if aid in self.agents]
        else:
            # All agents
            agents = list(self.agents.values())
        
        # Filter by status
        if status:
            agents = [a for a in agents if a.status == status]
        
        # Filter out stale agents
        now = datetime.now()
        active_agents = []
        for agent in agents:
            if (now - agent.last_seen).seconds < self.heartbeat_interval * 2:
                active_agents.append(agent)
        
        return active_agents
    
    async def update_heartbeat(self, agent_id: str) -> None:
        """Update agent heartbeat timestamp."""
        if agent_id in self.agents:
            self.agents[agent_id].last_seen = datetime.now()
    
    async def get_agent(self, agent_id: str) -> Optional[AgentInfo]:
        """Get specific agent info."""
        return self.agents.get(agent_id)
    
    async def find_best_agent(self, 
                             capability: str,
                             criteria: Optional[Dict[str, Any]] = None) -> Optional[AgentInfo]:
        """Find best agent for capability based on criteria."""
        candidates = await self.discover(capability=capability, status="active")
        
        if not candidates:
            return None
        
        if not criteria:
            # Return first available
            return candidates[0]
        
        # Score candidates
        scored = []
        for agent in candidates:
            score = self._score_agent(agent, criteria)
            scored.append((score, agent))
        
        # Return highest scoring
        scored.sort(reverse=True, key=lambda x: x[0])
        return scored[0][1] if scored else None
    
    def _score_agent(self, agent: AgentInfo, criteria: Dict[str, Any]) -> float:
        """Score agent based on criteria."""
        score = 0.0
        
        # Version preference
        if "min_version" in criteria:
            if self._compare_versions(agent.version, criteria["min_version"]) >= 0:
                score += 1.0
        
        # Load balancing (could check agent load if available)
        # For now, prefer agents with more recent heartbeat
        recency = (datetime.now() - agent.last_seen).seconds
        score += max(0, 1.0 - (recency / self.heartbeat_interval))
        
        return score
    
    def _compare_versions(self, v1: str, v2: str) -> int:
        """Compare semantic versions."""
        from packaging import version
        return -1 if version.parse(v1) < version.parse(v2) else (
            1 if version.parse(v1) > version.parse(v2) else 0
        )
```

### Message Passing System

```python
from abc import ABC, abstractmethod
from typing import Any, Optional
import uuid


@dataclass
class AgentMessage:
    """Message between agents."""
    id: str
    from_agent: str
    to_agent: str
    message_type: str
    payload: Dict[str, Any]
    timestamp: datetime
    correlation_id: Optional[str] = None
    reply_to: Optional[str] = None
    

class MessageTransport(ABC):
    """Abstract message transport."""
    
    @abstractmethod
    async def send(self, message: AgentMessage) -> None:
        """Send message to agent."""
        pass
    
    @abstractmethod
    async def receive(self, agent_id: str, timeout: Optional[float] = None) -> Optional[AgentMessage]:
        """Receive message for agent."""
        pass


class InMemoryMessageTransport(MessageTransport):
    """In-memory message transport for testing."""
    
    def __init__(self):
        self.queues: Dict[str, asyncio.Queue] = defaultdict(asyncio.Queue)
    
    async def send(self, message: AgentMessage) -> None:
        """Send message to agent's queue."""
        await self.queues[message.to_agent].put(message)
    
    async def receive(self, agent_id: str, timeout: Optional[float] = None) -> Optional[AgentMessage]:
        """Receive message from queue."""
        try:
            if timeout:
                return await asyncio.wait_for(
                    self.queues[agent_id].get(),
                    timeout=timeout
                )
            else:
                return await self.queues[agent_id].get()
        except asyncio.TimeoutError:
            return None


class AgentMessenger:
    """High-level messaging interface for agents."""
    
    def __init__(self, 
                 agent_id: str,
                 transport: MessageTransport,
                 registry: AgentRegistry):
        self.agent_id = agent_id
        self.transport = transport
        self.registry = registry
        self.handlers = {}
        self.correlation_callbacks = {}
    
    def handle(self, message_type: str):
        """Decorator to register message handler."""
        def decorator(func):
            self.handlers[message_type] = func
            return func
        return decorator
    
    async def send(self,
                  to_agent: str,
                  message_type: str,
                  payload: Dict[str, Any],
                  correlation_id: Optional[str] = None) -> str:
        """Send message to another agent."""
        message = AgentMessage(
            id=str(uuid.uuid4()),
            from_agent=self.agent_id,
            to_agent=to_agent,
            message_type=message_type,
            payload=payload,
            timestamp=datetime.now(),
            correlation_id=correlation_id
        )
        
        await self.transport.send(message)
        return message.id
    
    async def request(self,
                     to_agent: str,
                     message_type: str,
                     payload: Dict[str, Any],
                     timeout: float = 30.0) -> Optional[AgentMessage]:
        """Send request and wait for response."""
        correlation_id = str(uuid.uuid4())
        
        # Set up response handler
        response_future = asyncio.Future()
        self.correlation_callbacks[correlation_id] = response_future
        
        # Send request
        await self.send(to_agent, message_type, payload, correlation_id)
        
        try:
            # Wait for response
            response = await asyncio.wait_for(response_future, timeout=timeout)
            return response
        except asyncio.TimeoutError:
            return None
        finally:
            # Clean up
            self.correlation_callbacks.pop(correlation_id, None)
    
    async def reply(self,
                   original_message: AgentMessage,
                   payload: Dict[str, Any]) -> str:
        """Reply to a message."""
        reply = AgentMessage(
            id=str(uuid.uuid4()),
            from_agent=self.agent_id,
            to_agent=original_message.from_agent,
            message_type=f"{original_message.message_type}_response",
            payload=payload,
            timestamp=datetime.now(),
            correlation_id=original_message.correlation_id,
            reply_to=original_message.id
        )
        
        await self.transport.send(reply)
        return reply.id
    
    async def broadcast(self,
                       capability: str,
                       message_type: str,
                       payload: Dict[str, Any]) -> List[str]:
        """Broadcast message to all agents with capability."""
        agents = await self.registry.discover(capability=capability)
        
        message_ids = []
        for agent in agents:
            if agent.id != self.agent_id:  # Don't send to self
                msg_id = await self.send(agent.id, message_type, payload)
                message_ids.append(msg_id)
        
        return message_ids
    
    async def start_receiving(self) -> None:
        """Start receiving messages."""
        while True:
            try:
                message = await self.transport.receive(self.agent_id, timeout=1.0)
                
                if message:
                    # Check for correlation callback
                    if message.correlation_id in self.correlation_callbacks:
                        future = self.correlation_callbacks[message.correlation_id]
                        if not future.done():
                            future.set_result(message)
                    
                    # Handle by type
                    elif message.message_type in self.handlers:
                        handler = self.handlers[message.message_type]
                        asyncio.create_task(self._handle_message(handler, message))
                    
                    else:
                        logger.warning(f"No handler for message type: {message.message_type}")
                
            except Exception as e:
                logger.error(f"Error receiving message: {e}")
    
    async def _handle_message(self, handler: Callable, message: AgentMessage) -> None:
        """Handle message with error handling."""
        try:
            await handler(message)
        except Exception as e:
            logger.error(f"Error handling message {message.id}: {e}")
```

### Shared Context Management

```python
class SharedContextManager:
    """Manage shared context between agents."""
    
    def __init__(self):
        self.contexts: Dict[str, Dict[str, Any]] = {}
        self.context_locks: Dict[str, asyncio.Lock] = defaultdict(asyncio.Lock)
        self.subscribers: Dict[str, Set[str]] = defaultdict(set)
        self.version_counters: Dict[str, int] = defaultdict(int)
    
    async def create_context(self, 
                           context_id: str,
                           initial_data: Dict[str, Any] = None) -> None:
        """Create new shared context."""
        async with self.context_locks[context_id]:
            self.contexts[context_id] = initial_data or {}
            self.version_counters[context_id] = 1
            
            logger.info(f"Created shared context: {context_id}")
    
    async def get_context(self, context_id: str) -> Optional[Dict[str, Any]]:
        """Get shared context data."""
        return self.contexts.get(context_id)
    
    async def update_context(self,
                           context_id: str,
                           updates: Dict[str, Any],
                           agent_id: str) -> int:
        """Update shared context."""
        async with self.context_locks[context_id]:
            if context_id not in self.contexts:
                raise ValueError(f"Context {context_id} not found")
            
            # Apply updates
            self.contexts[context_id].update(updates)
            
            # Increment version
            self.version_counters[context_id] += 1
            version = self.version_counters[context_id]
            
            # Notify subscribers
            await self._notify_subscribers(context_id, updates, agent_id)
            
            return version
    
    async def subscribe(self, context_id: str, agent_id: str) -> None:
        """Subscribe to context updates."""
        self.subscribers[context_id].add(agent_id)
        logger.info(f"Agent {agent_id} subscribed to context {context_id}")
    
    async def unsubscribe(self, context_id: str, agent_id: str) -> None:
        """Unsubscribe from context updates."""
        self.subscribers[context_id].discard(agent_id)
    
    async def _notify_subscribers(self,
                                context_id: str,
                                updates: Dict[str, Any],
                                updater_agent_id: str) -> None:
        """Notify subscribers of context update."""
        for subscriber_id in self.subscribers[context_id]:
            if subscriber_id != updater_agent_id:
                # Send notification (implementation depends on messaging system)
                logger.debug(f"Notifying {subscriber_id} of context update")
    
    async def acquire_lock(self, context_id: str, agent_id: str, timeout: float = 5.0) -> bool:
        """Acquire exclusive lock on context."""
        try:
            await asyncio.wait_for(
                self.context_locks[context_id].acquire(),
                timeout=timeout
            )
            return True
        except asyncio.TimeoutError:
            return False
    
    async def release_lock(self, context_id: str, agent_id: str) -> None:
        """Release context lock."""
        self.context_locks[context_id].release()
    
    async def get_version(self, context_id: str) -> int:
        """Get current context version."""
        return self.version_counters.get(context_id, 0)
```

### Agent Coordination Patterns

```python
class AgentCoordinator:
    """Coordinate multi-agent workflows."""
    
    def __init__(self, 
                 registry: AgentRegistry,
                 messenger: AgentMessenger,
                 context_manager: SharedContextManager):
        self.registry = registry
        self.messenger = messenger
        self.context_manager = context_manager
        self.coordination_strategies = {
            "leader_follower": self._coordinate_leader_follower,
            "peer_to_peer": self._coordinate_peer_to_peer,
            "hierarchical": self._coordinate_hierarchical,
            "consensus": self._coordinate_consensus
        }
    
    async def coordinate_task(self,
                            task_definition: Dict[str, Any],
                            strategy: str = "leader_follower") -> Dict[str, Any]:
        """Coordinate task execution across agents."""
        if strategy not in self.coordination_strategies:
            raise ValueError(f"Unknown coordination strategy: {strategy}")
        
        coordinator_fn = self.coordination_strategies[strategy]
        return await coordinator_fn(task_definition)
    
    async def _coordinate_leader_follower(self, 
                                        task_definition: Dict[str, Any]) -> Dict[str, Any]:
        """Leader-follower coordination pattern."""
        # Select leader based on capability
        leader_capability = task_definition["leader_capability"]
        leader = await self.registry.find_best_agent(leader_capability)
        
        if not leader:
            raise ValueError(f"No agent found with capability: {leader_capability}")
        
        # Create shared context
        context_id = f"task_{uuid.uuid4()}"
        await self.context_manager.create_context(context_id, {
            "task": task_definition,
            "leader": leader.id,
            "status": "initiated"
        })
        
        # Send task to leader
        response = await self.messenger.request(
            to_agent=leader.id,
            message_type="execute_as_leader",
            payload={
                "task": task_definition,
                "context_id": context_id
            }
        )
        
        if not response:
            raise TaskExecutionError("Leader failed to respond")
        
        # Get final context
        final_context = await self.context_manager.get_context(context_id)
        
        return {
            "leader": leader.id,
            "result": response.payload,
            "context": final_context
        }
    
    async def _coordinate_peer_to_peer(self,
                                     task_definition: Dict[str, Any]) -> Dict[str, Any]:
        """Peer-to-peer coordination pattern."""
        # Find all capable agents
        capability = task_definition["required_capability"]
        agents = await self.registry.discover(capability=capability)
        
        if not agents:
            raise ValueError(f"No agents found with capability: {capability}")
        
        # Partition work
        work_items = task_definition["work_items"]
        partitions = self._partition_work(work_items, len(agents))
        
        # Create shared context
        context_id = f"p2p_task_{uuid.uuid4()}"
        await self.context_manager.create_context(context_id, {
            "task": task_definition,
            "agents": [a.id for a in agents],
            "partitions": partitions,
            "results": {}
        })
        
        # Send work to each agent
        tasks = []
        for agent, partition in zip(agents, partitions):
            task = self.messenger.request(
                to_agent=agent.id,
                message_type="execute_partition",
                payload={
                    "partition": partition,
                    "context_id": context_id
                }
            )
            tasks.append(task)
        
        # Wait for all responses
        responses = await asyncio.gather(*tasks, return_exceptions=True)
        
        # Aggregate results
        results = {}
        for i, response in enumerate(responses):
            if isinstance(response, Exception):
                results[agents[i].id] = {"status": "failed", "error": str(response)}
            else:
                results[agents[i].id] = response.payload
        
        return {
            "strategy": "peer_to_peer",
            "agents": [a.id for a in agents],
            "results": results
        }
    
    async def _coordinate_hierarchical(self,
                                     task_definition: Dict[str, Any]) -> Dict[str, Any]:
        """Hierarchical coordination pattern."""
        # Build agent hierarchy
        hierarchy = task_definition["hierarchy"]
        
        # Start from root
        root_agent_id = hierarchy["root"]
        root_agent = await self.registry.get_agent(root_agent_id)
        
        if not root_agent:
            raise ValueError(f"Root agent {root_agent_id} not found")
        
        # Execute hierarchically
        result = await self._execute_hierarchical_node(
            node_id=root_agent_id,
            hierarchy=hierarchy,
            task_definition=task_definition
        )
        
        return {
            "strategy": "hierarchical",
            "hierarchy": hierarchy,
            "result": result
        }
    
    async def _coordinate_consensus(self,
                                  task_definition: Dict[str, Any]) -> Dict[str, Any]:
        """Consensus-based coordination pattern."""
        # Find participating agents
        capability = task_definition["required_capability"]
        agents = await self.registry.discover(capability=capability)
        
        min_agents = task_definition.get("min_agents", 3)
        if len(agents) < min_agents:
            raise ValueError(f"Need at least {min_agents} agents, found {len(agents)}")
        
        # Phase 1: Proposal
        proposal = task_definition["proposal"]
        votes = {}
        
        # Send proposal to all agents
        vote_tasks = []
        for agent in agents:
            task = self.messenger.request(
                to_agent=agent.id,
                message_type="vote_on_proposal",
                payload={"proposal": proposal}
            )
            vote_tasks.append((agent.id, task))
        
        # Collect votes
        for agent_id, task in vote_tasks:
            try:
                response = await task
                votes[agent_id] = response.payload.get("vote", "abstain")
            except Exception as e:
                votes[agent_id] = "error"
        
        # Phase 2: Consensus decision
        yes_votes = sum(1 for v in votes.values() if v == "yes")
        no_votes = sum(1 for v in votes.values() if v == "no")
        
        consensus_threshold = task_definition.get("consensus_threshold", 0.66)
        consensus_reached = yes_votes / len(agents) >= consensus_threshold
        
        # Phase 3: Execute if consensus
        if consensus_reached:
            # Select executor
            executor = await self._select_executor(agents, task_definition)
            
            result = await self.messenger.request(
                to_agent=executor.id,
                message_type="execute_consensus_task",
                payload={"task": task_definition}
            )
            
            return {
                "strategy": "consensus",
                "votes": votes,
                "consensus": True,
                "executor": executor.id,
                "result": result.payload if result else None
            }
        else:
            return {
                "strategy": "consensus",
                "votes": votes,
                "consensus": False,
                "reason": "Insufficient votes"
            }
    
    def _partition_work(self, items: List[Any], num_partitions: int) -> List[List[Any]]:
        """Partition work items evenly."""
        partitions = [[] for _ in range(num_partitions)]
        
        for i, item in enumerate(items):
            partitions[i % num_partitions].append(item)
        
        return partitions
    
    async def _execute_hierarchical_node(self,
                                       node_id: str,
                                       hierarchy: Dict[str, Any],
                                       task_definition: Dict[str, Any]) -> Any:
        """Execute hierarchical node and its children."""
        # Execute current node
        response = await self.messenger.request(
            to_agent=node_id,
            message_type="execute_hierarchical",
            payload={"task": task_definition}
        )
        
        if not response:
            raise TaskExecutionError(f"Agent {node_id} failed to respond")
        
        # Execute children if any
        children = hierarchy.get(node_id, [])
        if children:
            child_results = []
            for child_id in children:
                child_result = await self._execute_hierarchical_node(
                    child_id,
                    hierarchy,
                    task_definition
                )
                child_results.append(child_result)
            
            # Aggregate with parent result
            return {
                "node": response.payload,
                "children": child_results
            }
        else:
            return response.payload
    
    async def _select_executor(self, 
                             agents: List[AgentInfo],
                             task_definition: Dict[str, Any]) -> AgentInfo:
        """Select best agent to execute task."""
        # Simple selection - can be enhanced with load balancing, etc.
        return agents[0]
```

---

## Advanced Patterns

### Dynamic Command Generation

```python
class DynamicCommandGenerator:
    """Generate commands at runtime based on context."""
    
    def __init__(self):
        self.command_templates = {}
        self.command_builders = {}
    
    def register_template(self, name: str, template: Dict[str, Any]):
        """Register command template."""
        self.command_templates[name] = template
    
    def register_builder(self, name: str, builder: Callable):
        """Register command builder function."""
        self.command_builders[name] = builder
    
    async def generate_commands(self,
                              context: Dict[str, Any],
                              agent_def: AgentDefinition) -> List[Dict[str, Any]]:
        """Generate dynamic commands based on context."""
        generated_commands = []
        
        # Check context-based rules
        if "case_type" in context:
            case_type = context["case_type"]
            
            # Generate case-specific commands
            if case_type == "discovery":
                generated_commands.extend(self._generate_discovery_commands(context))
            elif case_type == "motion":
                generated_commands.extend(self._generate_motion_commands(context))
        
        # Check agent capabilities
        for capability in agent_def.capabilities:
            if capability in self.command_builders:
                builder = self.command_builders[capability]
                commands = await builder(context, agent_def)
                generated_commands.extend(commands)
        
        return generated_commands
    
    def _generate_discovery_commands(self, context: Dict[str, Any]) -> List[Dict[str, Any]]:
        """Generate discovery-specific commands."""
        commands = []
        
        # Basic discovery commands
        commands.append({
            "name": "analyze-production",
            "description": "Analyze production completeness",
            "handler": "discovery_analysis_handler"
        })
        
        # Add jurisdiction-specific commands
        if context.get("jurisdiction") == "federal":
            commands.append({
                "name": "check-frcp-compliance",
                "description": "Check FRCP compliance",
                "handler": "frcp_compliance_handler"
            })
        
        return commands
    
    def _generate_motion_commands(self, context: Dict[str, Any]) -> List[Dict[str, Any]]:
        """Generate motion-specific commands."""
        commands = []
        
        motion_types = context.get("available_motions", [])
        
        for motion_type in motion_types:
            commands.append({
                "name": f"draft-{motion_type}",
                "description": f"Draft {motion_type} motion",
                "handler": "motion_drafter_handler",
                "params": {"motion_type": motion_type}
            })
        
        return commands
```

### Command Composition

```python
class CommandComposer:
    """Compose complex commands from simple ones."""
    
    def __init__(self, executor: AsyncCommandExecutor):
        self.executor = executor
        self.compositions = {}
    
    def compose(self, name: str, steps: List[Dict[str, Any]]):
        """Define command composition."""
        self.compositions[name] = steps
    
    async def execute_composition(self,
                                 composition_name: str,
                                 initial_context: Dict[str, Any]) -> Dict[str, Any]:
        """Execute composed command."""
        if composition_name not in self.compositions:
            raise ValueError(f"Unknown composition: {composition_name}")
        
        steps = self.compositions[composition_name]
        context = initial_context.copy()
        results = {}
        
        for i, step in enumerate(steps):
            step_name = step.get("name", f"step_{i}")
            
            # Resolve command
            command = await self._resolve_command(step, context, results)
            
            # Execute
            try:
                result = await self.executor.execute(command, context)
                results[step_name] = result
                
                # Update context with result
                if step.get("update_context"):
                    context.update(result)
                
            except Exception as e:
                # Handle error based on step config
                if step.get("required", True):
                    raise
                else:
                    results[step_name] = {"error": str(e)}
        
        return results
    
    async def _resolve_command(self,
                             step: Dict[str, Any],
                             context: Dict[str, Any],
                             previous_results: Dict[str, Any]) -> ParsedCommand:
        """Resolve command with parameter interpolation."""
        command_name = step["command"]
        
        # Resolve parameters
        params = {}
        for key, value in step.get("params", {}).items():
            if isinstance(value, str) and value.startswith("${"):
                # Interpolate from context or results
                params[key] = self._interpolate_value(value, context, previous_results)
            else:
                params[key] = value
        
        return ParsedCommand(
            command=command_name,
            args=[],
            kwargs=params,
            raw_input=f"*{command_name}"
        )
    
    def _interpolate_value(self,
                          template: str,
                          context: Dict[str, Any],
                          results: Dict[str, Any]) -> Any:
        """Interpolate template values."""
        # Remove ${ and }
        path = template[2:-1]
        
        # Check if it's a result reference
        if path.startswith("results."):
            path = path[8:]  # Remove "results."
            return self._get_nested_value(results, path)
        else:
            return self._get_nested_value(context, path)
    
    def _get_nested_value(self, data: Dict[str, Any], path: str) -> Any:
        """Get value from nested dict using dot notation."""
        parts = path.split(".")
        current = data
        
        for part in parts:
            if isinstance(current, dict) and part in current:
                current = current[part]
            else:
                return None
        
        return current
```

### Parameter Inference

```python
class ParameterInferenceEngine:
    """Infer command parameters from context."""
    
    def __init__(self):
        self.inference_rules = []
        self.type_inferencers = {}
    
    def add_rule(self, rule: Dict[str, Any]):
        """Add inference rule."""
        self.inference_rules.append(rule)
    
    def register_type_inferencer(self, param_type: str, inferencer: Callable):
        """Register type-specific inferencer."""
        self.type_inferencers[param_type] = inferencer
    
    async def infer_parameters(self,
                             command: str,
                             context: Dict[str, Any],
                             partial_params: Dict[str, Any] = None) -> Dict[str, Any]:
        """Infer missing parameters."""
        inferred = partial_params.copy() if partial_params else {}
        
        # Apply inference rules
        for rule in self.inference_rules:
            if self._rule_applies(rule, command, context):
                param_name = rule["parameter"]
                if param_name not in inferred:
                    value = await self._apply_rule(rule, context)
                    if value is not None:
                        inferred[param_name] = value
        
        # Apply type-based inference
        # This would need command parameter schema
        
        return inferred
    
    def _rule_applies(self, rule: Dict[str, Any], command: str, context: Dict[str, Any]) -> bool:
        """Check if rule applies to current situation."""
        # Check command match
        if "command" in rule:
            if isinstance(rule["command"], list):
                if command not in rule["command"]:
                    return False
            elif command != rule["command"]:
                return False
        
        # Check context conditions
        if "conditions" in rule:
            for condition in rule["conditions"]:
                if not self._evaluate_condition(condition, context):
                    return False
        
        return True
    
    async def _apply_rule(self, rule: Dict[str, Any], context: Dict[str, Any]) -> Any:
        """Apply inference rule to get parameter value."""
        inference_type = rule["inference_type"]
        
        if inference_type == "context_value":
            # Get value from context
            return self._get_context_value(context, rule["source_path"])
            
        elif inference_type == "computed":
            # Compute value
            computer = rule["computer"]
            return await computer(context)
            
        elif inference_type == "default":
            # Use default value
            return rule["default_value"]
            
        elif inference_type == "type_based":
            # Use type inferencer
            param_type = rule["parameter_type"]
            if param_type in self.type_inferencers:
                inferencer = self.type_inferencers[param_type]
                return await inferencer(context)
        
        return None
    
    def _evaluate_condition(self, condition: Dict[str, Any], context: Dict[str, Any]) -> bool:
        """Evaluate condition against context."""
        field = condition["field"]
        operator = condition["operator"]
        value = condition["value"]
        
        context_value = self._get_context_value(context, field)
        
        if operator == "equals":
            return context_value == value
        elif operator == "contains":
            return value in context_value
        elif operator == "exists":
            return context_value is not None
        # Add more operators as needed
        
        return False
    
    def _get_context_value(self, context: Dict[str, Any], path: str) -> Any:
        """Get value from context using path."""
        parts = path.split(".")
        current = context
        
        for part in parts:
            if isinstance(current, dict) and part in current:
                current = current[part]
            else:
                return None
        
        return current
```

### Adaptive Interfaces

```python
class AdaptiveCommandInterface:
    """Adapt command interface based on user behavior and context."""
    
    def __init__(self):
        self.usage_history = []
        self.user_preferences = {}
        self.command_shortcuts = {}
        self.learning_enabled = True
    
    async def adapt_interface(self,
                            user_id: str,
                            context: Dict[str, Any]) -> Dict[str, Any]:
        """Generate adapted interface for user."""
        # Get user history
        user_history = self._get_user_history(user_id)
        
        # Analyze patterns
        patterns = self._analyze_usage_patterns(user_history)
        
        # Generate adaptations
        adaptations = {
            "suggested_commands": self._suggest_commands(patterns, context),
            "shortcuts": self._generate_shortcuts(patterns),
            "ui_modifications": self._adapt_ui(patterns),
            "help_focus": self._personalize_help(patterns)
        }
        
        return adaptations
    
    def _get_user_history(self, user_id: str) -> List[Dict[str, Any]]:
        """Get user's command history."""
        return [
            entry for entry in self.usage_history 
            if entry.get("user_id") == user_id
        ]
    
    def _analyze_usage_patterns(self, history: List[Dict[str, Any]]) -> Dict[str, Any]:
        """Analyze user's usage patterns."""
        patterns = {
            "frequent_commands": self._get_frequent_commands(history),
            "command_sequences": self._find_command_sequences(history),
            "time_patterns": self._analyze_time_patterns(history),
            "error_patterns": self._analyze_errors(history)
        }
        
        return patterns
    
    def _suggest_commands(self, 
                         patterns: Dict[str, Any],
                         context: Dict[str, Any]) -> List[str]:
        """Suggest commands based on patterns and context."""
        suggestions = []
        
        # Add frequently used commands
        frequent = patterns["frequent_commands"][:5]
        suggestions.extend(frequent)
        
        # Add context-relevant commands
        if "case_type" in context:
            if context["case_type"] == "discovery":
                suggestions.extend(["analyze", "search-production"])
        
        # Add next command in common sequences
        sequences = patterns["command_sequences"]
        last_command = context.get("last_command")
        if last_command:
            for seq in sequences:
                if seq[0] == last_command and len(seq) > 1:
                    suggestions.append(seq[1])
        
        # Remove duplicates and limit
        seen = set()
        unique_suggestions = []
        for cmd in suggestions:
            if cmd not in seen:
                seen.add(cmd)
                unique_suggestions.append(cmd)
        
        return unique_suggestions[:8]
    
    def _generate_shortcuts(self, patterns: Dict[str, Any]) -> Dict[str, str]:
        """Generate command shortcuts."""
        shortcuts = {}
        
        # Create shortcuts for frequent commands
        for i, cmd in enumerate(patterns["frequent_commands"][:9]):
            shortcuts[str(i + 1)] = cmd
        
        # Create abbreviated shortcuts
        for cmd in patterns["frequent_commands"][:5]:
            abbrev = self._create_abbreviation(cmd)
            if abbrev and abbrev not in shortcuts:
                shortcuts[abbrev] = cmd
        
        return shortcuts
    
    def _adapt_ui(self, patterns: Dict[str, Any]) -> Dict[str, Any]:
        """Generate UI adaptations."""
        return {
            "command_order": patterns["frequent_commands"],
            "hide_unused": True,
            "quick_access": patterns["frequent_commands"][:3],
            "theme": "efficient" if len(patterns["frequent_commands"]) > 10 else "guided"
        }
    
    def _personalize_help(self, patterns: Dict[str, Any]) -> Dict[str, Any]:
        """Personalize help content."""
        return {
            "focus_commands": patterns["frequent_commands"][:5],
            "troubleshoot": patterns["error_patterns"],
            "tips": self._generate_tips(patterns)
        }
    
    def _get_frequent_commands(self, history: List[Dict[str, Any]]) -> List[str]:
        """Get most frequently used commands."""
        from collections import Counter
        
        commands = [entry["command"] for entry in history if "command" in entry]
        command_counts = Counter(commands)
        
        return [cmd for cmd, count in command_counts.most_common()]
    
    def _find_command_sequences(self, history: List[Dict[str, Any]]) -> List[List[str]]:
        """Find common command sequences."""
        sequences = []
        
        # Simple bigram analysis
        for i in range(len(history) - 1):
            if "command" in history[i] and "command" in history[i + 1]:
                seq = [history[i]["command"], history[i + 1]["command"]]
                sequences.append(seq)
        
        # Count and return most common
        from collections import Counter
        seq_tuples = [tuple(seq) for seq in sequences]
        seq_counts = Counter(seq_tuples)
        
        return [list(seq) for seq, count in seq_counts.most_common(5)]
    
    def _analyze_time_patterns(self, history: List[Dict[str, Any]]) -> Dict[str, Any]:
        """Analyze time-based usage patterns."""
        # Placeholder - would analyze when commands are used
        return {}
    
    def _analyze_errors(self, history: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """Analyze common errors."""
        errors = [
            entry for entry in history 
            if entry.get("status") == "error"
        ]
        
        # Group by error type
        error_patterns = {}
        for error in errors:
            error_type = error.get("error_type", "unknown")
            if error_type not in error_patterns:
                error_patterns[error_type] = []
            error_patterns[error_type].append(error)
        
        return error_patterns
    
    def _create_abbreviation(self, command: str) -> str:
        """Create command abbreviation."""
        parts = command.split("-")
        if len(parts) > 1:
            return "".join(p[0] for p in parts)
        elif len(command) > 3:
            return command[:3]
        return None
    
    def _generate_tips(self, patterns: Dict[str, Any]) -> List[str]:
        """Generate personalized tips."""
        tips = []
        
        # Tips based on usage
        if len(patterns["frequent_commands"]) < 3:
            tips.append("Try exploring more commands with *help")
        
        # Tips based on errors
        if patterns.get("error_patterns"):
            tips.append("Use *help <command> for detailed command usage")
        
        return tips
    
    async def record_usage(self,
                          user_id: str,
                          command: str,
                          context: Dict[str, Any],
                          result: Dict[str, Any]) -> None:
        """Record command usage for learning."""
        if self.learning_enabled:
            self.usage_history.append({
                "user_id": user_id,
                "command": command,
                "context": context.copy(),
                "status": result.get("status", "success"),
                "error_type": result.get("error_type"),
                "timestamp": datetime.now()
            })
            
            # Limit history size
            if len(self.usage_history) > 10000:
                self.usage_history = self.usage_history[-5000:]
```

This completes the comprehensive UTILIZATION_PATTERNS.md documentation covering command execution engines, task chaining, workflow composition, and inter-agent communication patterns.