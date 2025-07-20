# Agent Activation Patterns

This document covers the implementation of agent activation patterns in the BMad framework.

## Table of Contents

1. [Standard Activation Flow](#standard-activation-flow)
2. [Custom Activation Support](#custom-activation-support)
3. [Error Recovery](#error-recovery)
4. [Context Preservation](#context-preservation)
5. [Implementation Examples](#implementation-examples)

---

## Standard Activation Flow

### Core Activation Module

```python
# Clerk/src/ai_agents/bmad-framework/activation.py

from typing import Dict, Optional, Any
from dataclasses import dataclass
from enum import Enum
import logging

from .agent_loader import AgentDefinition
from .exceptions import ActivationError
from .security import AgentSecurityContext

logger = logging.getLogger("clerk_api.bmad_framework")


class ActivationState(Enum):
    """Agent activation states."""
    UNINITIALIZED = "uninitialized"
    LOADING = "loading"
    VALIDATING = "validating"
    ACTIVATING = "activating"
    READY = "ready"
    FAILED = "failed"
    DEGRADED = "degraded"


@dataclass
class ActivationContext:
    """Context for agent activation."""
    agent_def: AgentDefinition
    security_context: AgentSecurityContext
    case_name: str
    activation_config: Dict[str, Any]
    state: ActivationState = ActivationState.UNINITIALIZED
    errors: list = None
    warnings: list = None
    
    def __post_init__(self):
        if self.errors is None:
            self.errors = []
        if self.warnings is None:
            self.warnings = []


class AgentActivator:
    """Handles agent activation lifecycle."""
    
    def __init__(self):
        self.activation_hooks = {}
        self.state_transitions = {}
        
    async def activate(self, context: ActivationContext) -> ActivationContext:
        """
        Execute standard 5-step BMad activation sequence.
        
        Steps:
        1. Read configuration
        2. Adopt persona
        3. Initialize security
        4. Execute custom activation
        5. Finalize and greet
        """
        try:
            # Step 1: Read configuration
            context.state = ActivationState.LOADING
            await self._read_configuration(context)
            
            # Step 2: Validate
            context.state = ActivationState.VALIDATING
            await self._validate_activation(context)
            
            # Step 3: Execute activation instructions
            context.state = ActivationState.ACTIVATING
            await self._execute_activation_instructions(context)
            
            # Step 4: Apply security context
            await self._apply_security_context(context)
            
            # Step 5: Finalize
            context.state = ActivationState.READY
            await self._finalize_activation(context)
            
            logger.info(f"Agent {context.agent_def.id} activated successfully")
            return context
            
        except Exception as e:
            context.state = ActivationState.FAILED
            context.errors.append(str(e))
            logger.error(f"Activation failed for {context.agent_def.id}: {e}")
            raise ActivationError(f"Activation failed: {e}")
    
    async def _read_configuration(self, context: ActivationContext):
        """Read and process agent configuration."""
        # Validate agent definition
        if not context.agent_def:
            raise ActivationError("No agent definition provided")
        
        # Process activation config overrides
        if context.activation_config.get("skip_validation"):
            context.warnings.append("Validation skipped by config")
    
    async def _validate_activation(self, context: ActivationContext):
        """Validate activation requirements."""
        # Check required dependencies
        for dep_type, deps in context.agent_def.dependencies.items():
            for dep in deps:
                if not await self._check_dependency(dep_type, dep):
                    if context.activation_config.get("allow_missing_deps"):
                        context.warnings.append(f"Missing {dep_type}: {dep}")
                    else:
                        raise ActivationError(f"Missing required {dep_type}: {dep}")
    
    async def _execute_activation_instructions(self, context: ActivationContext):
        """Execute agent's activation instructions."""
        instructions = context.agent_def.activation_instructions
        
        for i, instruction in enumerate(instructions):
            # Parse instruction type
            if instruction.startswith("STEP"):
                await self._execute_step(instruction, context)
            elif instruction.startswith("CRITICAL"):
                await self._execute_critical(instruction, context)
            elif instruction.startswith("IF"):
                await self._execute_conditional(instruction, context)
    
    async def _apply_security_context(self, context: ActivationContext):
        """Apply security boundaries and permissions."""
        # Validate case access
        if not context.security_context.has_permission("read"):
            raise ActivationError("Insufficient permissions for activation")
        
        # Apply case isolation
        context.agent_def.runtime_context = {
            "case_name": context.case_name,
            "permissions": context.security_context.permissions,
            "user_id": context.security_context.user_id
        }
    
    async def _finalize_activation(self, context: ActivationContext):
        """Complete activation and prepare for use."""
        # Set ready state
        context.agent_def.is_active = True
        
        # Execute greeting if interactive
        if not context.activation_config.get("skip_greeting"):
            await self._greet_user(context)
    
    async def _check_dependency(self, dep_type: str, dep_name: str) -> bool:
        """Check if dependency exists."""
        # Implementation depends on dependency type
        # This is a placeholder
        return True
    
    async def _execute_step(self, instruction: str, context: ActivationContext):
        """Execute a STEP instruction."""
        logger.debug(f"Executing: {instruction}")
    
    async def _execute_critical(self, instruction: str, context: ActivationContext):
        """Execute a CRITICAL instruction."""
        logger.info(f"Critical instruction: {instruction}")
    
    async def _execute_conditional(self, instruction: str, context: ActivationContext):
        """Execute conditional instruction."""
        # Parse IF condition and execute accordingly
        pass
    
    async def _greet_user(self, context: ActivationContext):
        """Generate agent greeting."""
        agent = context.agent_def
        greeting = f"{agent.name} ready. {agent.persona.role}"
        if agent.icon:
            greeting = f"{agent.icon} {greeting}"
        
        # This would typically emit through appropriate channel
        logger.info(f"Greeting: {greeting}")
```

### Activation State Tracking

```python
class ActivationStateTracker:
    """Track and manage activation state transitions."""
    
    def __init__(self):
        self.state_history = []
        self.timestamps = {}
        self.metrics = {}
    
    def transition(self, 
                   context: ActivationContext, 
                   new_state: ActivationState,
                   metadata: Dict[str, Any] = None):
        """Record state transition."""
        old_state = context.state
        timestamp = datetime.now()
        
        # Record transition
        self.state_history.append({
            "from": old_state,
            "to": new_state,
            "timestamp": timestamp,
            "metadata": metadata or {}
        })
        
        # Update timestamps
        self.timestamps[new_state] = timestamp
        
        # Calculate metrics
        if old_state in self.timestamps:
            duration = (timestamp - self.timestamps[old_state]).total_seconds()
            self.metrics[f"{old_state}_duration"] = duration
        
        # Update context
        context.state = new_state
    
    def get_activation_report(self) -> Dict[str, Any]:
        """Generate activation performance report."""
        return {
            "total_duration": self._calculate_total_duration(),
            "state_durations": self.metrics,
            "transition_count": len(self.state_history),
            "final_state": self.state_history[-1]["to"] if self.state_history else None
        }
```

### Activation Context Manager

```python
from contextlib import asynccontextmanager

@asynccontextmanager
async def activation_context(agent_def: AgentDefinition,
                           case_name: str,
                           security_context: AgentSecurityContext,
                           **config):
    """Context manager for agent activation."""
    
    # Create activation context
    context = ActivationContext(
        agent_def=agent_def,
        security_context=security_context,
        case_name=case_name,
        activation_config=config
    )
    
    # Create activator
    activator = AgentActivator()
    tracker = ActivationStateTracker()
    
    try:
        # Track activation start
        tracker.transition(context, ActivationState.LOADING)
        
        # Activate agent
        yield await activator.activate(context)
        
    except Exception as e:
        # Track failure
        tracker.transition(context, ActivationState.FAILED, {"error": str(e)})
        raise
        
    finally:
        # Generate report
        report = tracker.get_activation_report()
        logger.info(f"Activation report: {report}")
```

---

## Custom Activation Support

### Plugin System for Activation Overrides

```python
from abc import ABC, abstractmethod
from typing import Protocol

class ActivationPlugin(Protocol):
    """Protocol for activation plugins."""
    
    @property
    def name(self) -> str:
        """Plugin name."""
        ...
    
    @property
    def priority(self) -> int:
        """Execution priority (lower = earlier)."""
        ...
    
    async def pre_activation(self, context: ActivationContext) -> None:
        """Called before standard activation."""
        ...
    
    async def post_activation(self, context: ActivationContext) -> None:
        """Called after standard activation."""
        ...
    
    async def override_step(self, step: str, context: ActivationContext) -> Optional[bool]:
        """Override specific activation step. Return True to skip default."""
        ...


class ActivationPluginRegistry:
    """Manage activation plugins."""
    
    def __init__(self):
        self.plugins: List[ActivationPlugin] = []
    
    def register(self, plugin: ActivationPlugin):
        """Register activation plugin."""
        self.plugins.append(plugin)
        self.plugins.sort(key=lambda p: p.priority)
    
    async def execute_pre_activation(self, context: ActivationContext):
        """Execute all pre-activation hooks."""
        for plugin in self.plugins:
            try:
                await plugin.pre_activation(context)
            except Exception as e:
                logger.error(f"Plugin {plugin.name} pre-activation failed: {e}")
                if not context.activation_config.get("ignore_plugin_errors"):
                    raise
    
    async def execute_post_activation(self, context: ActivationContext):
        """Execute all post-activation hooks."""
        for plugin in self.plugins:
            try:
                await plugin.post_activation(context)
            except Exception as e:
                logger.error(f"Plugin {plugin.name} post-activation failed: {e}")


# Example plugin implementation
class SecurityEnhancementPlugin:
    """Enhanced security checks during activation."""
    
    name = "security_enhancement"
    priority = 10
    
    async def pre_activation(self, context: ActivationContext):
        """Additional security validation."""
        # Check enhanced permissions
        if context.activation_config.get("security_level") == "enhanced":
            if not context.security_context.has_permission("admin"):
                raise ActivationError("Enhanced security requires admin permission")
    
    async def post_activation(self, context: ActivationContext):
        """Apply additional security constraints."""
        context.agent_def.runtime_context["security_enhanced"] = True
    
    async def override_step(self, step: str, context: ActivationContext) -> Optional[bool]:
        """No overrides."""
        return None
```

### Conditional Activation

```python
class ConditionalActivator:
    """Handle conditional activation based on context."""
    
    def __init__(self):
        self.conditions = {}
        self.register_default_conditions()
    
    def register_condition(self, name: str, evaluator: Callable):
        """Register condition evaluator."""
        self.conditions[name] = evaluator
    
    def register_default_conditions(self):
        """Register built-in conditions."""
        self.conditions["api_mode"] = lambda ctx: ctx.activation_config.get("api_mode", False)
        self.conditions["interactive_mode"] = lambda ctx: not ctx.activation_config.get("api_mode", False)
        self.conditions["debug_mode"] = lambda ctx: ctx.activation_config.get("debug", False)
        self.conditions["case_exists"] = lambda ctx: ctx.case_name is not None
    
    async def evaluate_instruction(self, instruction: str, context: ActivationContext) -> bool:
        """Evaluate conditional instruction."""
        # Parse IF condition
        if instruction.startswith("IF"):
            parts = instruction.split(":", 1)
            if len(parts) == 2:
                condition = parts[0].replace("IF", "").strip()
                
                # Evaluate condition
                if condition in self.conditions:
                    return self.conditions[condition](context)
                
                # Complex conditions
                return self._evaluate_complex_condition(condition, context)
        
        return True
    
    def _evaluate_complex_condition(self, condition: str, context: ActivationContext) -> bool:
        """Evaluate complex conditions with AND/OR."""
        # Simple implementation - can be enhanced
        if " AND " in condition:
            parts = condition.split(" AND ")
            return all(self.conditions.get(p.strip(), lambda x: False)(context) for p in parts)
        elif " OR " in condition:
            parts = condition.split(" OR ")
            return any(self.conditions.get(p.strip(), lambda x: False)(context) for p in parts)
        
        return False
```

### Multi-Agent Activation Sequences

```python
class MultiAgentActivator:
    """Handle activation of multiple agents in sequence or parallel."""
    
    def __init__(self):
        self.single_activator = AgentActivator()
    
    async def activate_sequence(self, 
                               agents: List[AgentDefinition],
                               case_name: str,
                               security_context: AgentSecurityContext,
                               **config) -> List[ActivationContext]:
        """Activate agents in sequence."""
        results = []
        shared_context = {}
        
        for agent in agents:
            # Create context with shared data
            context = ActivationContext(
                agent_def=agent,
                security_context=security_context,
                case_name=case_name,
                activation_config={**config, "shared_context": shared_context}
            )
            
            try:
                # Activate agent
                activated = await self.single_activator.activate(context)
                results.append(activated)
                
                # Share data between agents
                shared_context[agent.id] = {
                    "status": "active",
                    "capabilities": agent.commands
                }
                
            except Exception as e:
                logger.error(f"Failed to activate {agent.id}: {e}")
                if not config.get("continue_on_error"):
                    raise
                    
                results.append(context)
                shared_context[agent.id] = {"status": "failed", "error": str(e)}
        
        return results
    
    async def activate_parallel(self,
                               agents: List[AgentDefinition],
                               case_name: str,
                               security_context: AgentSecurityContext,
                               **config) -> List[ActivationContext]:
        """Activate agents in parallel."""
        tasks = []
        
        for agent in agents:
            context = ActivationContext(
                agent_def=agent,
                security_context=security_context,
                case_name=case_name,
                activation_config=config
            )
            
            tasks.append(self.single_activator.activate(context))
        
        # Execute in parallel
        results = await asyncio.gather(*tasks, return_exceptions=True)
        
        # Process results
        activated = []
        for i, result in enumerate(results):
            if isinstance(result, Exception):
                logger.error(f"Parallel activation failed for {agents[i].id}: {result}")
                if not config.get("continue_on_error"):
                    raise result
            else:
                activated.append(result)
        
        return activated
```

### Activation Rollback Mechanisms

```python
class ActivationRollback:
    """Handle activation rollback on failure."""
    
    def __init__(self):
        self.checkpoints = []
        self.rollback_handlers = {}
    
    def checkpoint(self, name: str, state: Dict[str, Any], rollback_fn: Callable):
        """Create activation checkpoint."""
        self.checkpoints.append({
            "name": name,
            "state": state.copy(),
            "timestamp": datetime.now()
        })
        self.rollback_handlers[name] = rollback_fn
    
    async def rollback_to(self, checkpoint_name: str):
        """Rollback to specific checkpoint."""
        # Find checkpoint
        checkpoint_idx = None
        for i, cp in enumerate(self.checkpoints):
            if cp["name"] == checkpoint_name:
                checkpoint_idx = i
                break
        
        if checkpoint_idx is None:
            raise ValueError(f"Checkpoint {checkpoint_name} not found")
        
        # Rollback in reverse order
        for i in range(len(self.checkpoints) - 1, checkpoint_idx, -1):
            cp = self.checkpoints[i]
            if cp["name"] in self.rollback_handlers:
                await self.rollback_handlers[cp["name"]](cp["state"])
        
        # Remove rolled back checkpoints
        self.checkpoints = self.checkpoints[:checkpoint_idx + 1]
    
    async def full_rollback(self):
        """Rollback all checkpoints."""
        for cp in reversed(self.checkpoints):
            if cp["name"] in self.rollback_handlers:
                await self.rollback_handlers[cp["name"]](cp["state"])
        
        self.checkpoints.clear()
```

---

## Error Recovery

### Graceful Degradation Strategies

```python
class DegradedModeHandler:
    """Handle degraded mode activation when full activation fails."""
    
    def __init__(self):
        self.degradation_levels = {
            "full": self._no_degradation,
            "limited_commands": self._limit_commands,
            "read_only": self._read_only_mode,
            "emergency": self._emergency_mode
        }
    
    async def apply_degradation(self, 
                               context: ActivationContext,
                               level: str = "limited_commands"):
        """Apply degradation strategy."""
        if level not in self.degradation_levels:
            level = "limited_commands"
        
        await self.degradation_levels[level](context)
        context.state = ActivationState.DEGRADED
        context.warnings.append(f"Running in degraded mode: {level}")
    
    async def _no_degradation(self, context: ActivationContext):
        """No degradation - full functionality."""
        pass
    
    async def _limit_commands(self, context: ActivationContext):
        """Limit available commands to essentials."""
        essential_commands = ["help", "exit", "status"]
        context.agent_def.commands = [
            cmd for cmd in context.agent_def.commands 
            if any(cmd.startswith(essential) for essential in essential_commands)
        ]
    
    async def _read_only_mode(self, context: ActivationContext):
        """Restrict to read-only operations."""
        # Remove all write operations
        read_only_commands = ["help", "search", "list", "view", "status", "exit"]
        context.agent_def.commands = [
            cmd for cmd in context.agent_def.commands
            if any(cmd.startswith(ro_cmd) for ro_cmd in read_only_commands)
        ]
        
        # Update security context
        context.security_context.permissions = ["read"]
    
    async def _emergency_mode(self, context: ActivationContext):
        """Emergency mode - minimal functionality."""
        context.agent_def.commands = ["help", "exit"]
        context.agent_def.capabilities = {"emergency_mode": True}
```

### Partial Activation Support

```python
class PartialActivator:
    """Support partial activation when some components fail."""
    
    def __init__(self):
        self.required_components = ["security", "commands"]
        self.optional_components = ["templates", "tasks", "checklists", "data"]
    
    async def activate_partial(self, context: ActivationContext) -> ActivationContext:
        """Attempt partial activation."""
        activation_report = {
            "succeeded": [],
            "failed": [],
            "skipped": []
        }
        
        # Try required components
        for component in self.required_components:
            try:
                await self._activate_component(component, context)
                activation_report["succeeded"].append(component)
            except Exception as e:
                activation_report["failed"].append((component, str(e)))
                # Cannot continue without required components
                raise ActivationError(f"Required component {component} failed: {e}")
        
        # Try optional components
        for component in self.optional_components:
            try:
                await self._activate_component(component, context)
                activation_report["succeeded"].append(component)
            except Exception as e:
                activation_report["failed"].append((component, str(e)))
                context.warnings.append(f"Optional component {component} failed: {e}")
        
        # Update context with report
        context.activation_report = activation_report
        
        # Determine final state
        if activation_report["failed"]:
            context.state = ActivationState.DEGRADED
        else:
            context.state = ActivationState.READY
        
        return context
    
    async def _activate_component(self, component: str, context: ActivationContext):
        """Activate specific component."""
        if component == "security":
            await self._activate_security(context)
        elif component == "commands":
            await self._activate_commands(context)
        elif component == "templates":
            await self._load_templates(context)
        elif component == "tasks":
            await self._load_tasks(context)
        # Add more components as needed
```

### Recovery Checkpoints

```python
class RecoveryCheckpointManager:
    """Manage recovery checkpoints during activation."""
    
    def __init__(self):
        self.checkpoints = {}
        self.recovery_strategies = {}
    
    def register_checkpoint(self, 
                           name: str,
                           save_fn: Callable,
                           restore_fn: Callable,
                           recovery_strategy: Optional[Callable] = None):
        """Register a recovery checkpoint."""
        self.checkpoints[name] = {
            "save": save_fn,
            "restore": restore_fn
        }
        if recovery_strategy:
            self.recovery_strategies[name] = recovery_strategy
    
    async def save_checkpoint(self, name: str, context: ActivationContext) -> Dict[str, Any]:
        """Save checkpoint state."""
        if name not in self.checkpoints:
            raise ValueError(f"Unknown checkpoint: {name}")
        
        state = await self.checkpoints[name]["save"](context)
        return {
            "checkpoint": name,
            "timestamp": datetime.now(),
            "state": state
        }
    
    async def restore_checkpoint(self, checkpoint_data: Dict[str, Any], context: ActivationContext):
        """Restore from checkpoint."""
        name = checkpoint_data["checkpoint"]
        if name not in self.checkpoints:
            raise ValueError(f"Unknown checkpoint: {name}")
        
        await self.checkpoints[name]["restore"](checkpoint_data["state"], context)
    
    async def attempt_recovery(self, 
                              checkpoint_name: str,
                              error: Exception,
                              context: ActivationContext) -> bool:
        """Attempt to recover from error at checkpoint."""
        if checkpoint_name in self.recovery_strategies:
            try:
                await self.recovery_strategies[checkpoint_name](error, context)
                return True
            except Exception as recovery_error:
                logger.error(f"Recovery failed: {recovery_error}")
                return False
        
        return False
```

### Error Reporting and Diagnostics

```python
@dataclass
class ActivationDiagnostics:
    """Detailed diagnostics for activation failures."""
    
    timestamp: datetime
    agent_id: str
    error_type: str
    error_message: str
    stack_trace: str
    context_snapshot: Dict[str, Any]
    system_info: Dict[str, Any]
    recovery_attempted: bool
    recovery_successful: bool
    
    def to_report(self) -> str:
        """Generate human-readable diagnostic report."""
        report = f"""
Activation Diagnostic Report
===========================
Timestamp: {self.timestamp}
Agent ID: {self.agent_id}
Error Type: {self.error_type}
Error Message: {self.error_message}

Context:
{json.dumps(self.context_snapshot, indent=2)}

System Info:
{json.dumps(self.system_info, indent=2)}

Recovery Attempted: {self.recovery_attempted}
Recovery Successful: {self.recovery_successful}

Stack Trace:
{self.stack_trace}
"""
        return report
    
    def to_json(self) -> Dict[str, Any]:
        """Export as JSON for logging."""
        return {
            "timestamp": self.timestamp.isoformat(),
            "agent_id": self.agent_id,
            "error": {
                "type": self.error_type,
                "message": self.error_message,
                "stack_trace": self.stack_trace
            },
            "context": self.context_snapshot,
            "system": self.system_info,
            "recovery": {
                "attempted": self.recovery_attempted,
                "successful": self.recovery_successful
            }
        }


class DiagnosticCollector:
    """Collect diagnostics during activation."""
    
    @staticmethod
    async def collect_diagnostics(error: Exception,
                                 context: ActivationContext) -> ActivationDiagnostics:
        """Collect comprehensive diagnostics."""
        import traceback
        import platform
        
        return ActivationDiagnostics(
            timestamp=datetime.now(),
            agent_id=context.agent_def.id,
            error_type=type(error).__name__,
            error_message=str(error),
            stack_trace=traceback.format_exc(),
            context_snapshot={
                "state": context.state.value,
                "case_name": context.case_name,
                "config": context.activation_config,
                "warnings": context.warnings,
                "errors": context.errors
            },
            system_info={
                "platform": platform.platform(),
                "python_version": platform.python_version(),
                "memory_usage": self._get_memory_usage(),
                "cpu_count": os.cpu_count()
            },
            recovery_attempted=False,
            recovery_successful=False
        )
    
    @staticmethod
    def _get_memory_usage() -> Dict[str, float]:
        """Get current memory usage."""
        import psutil
        process = psutil.Process()
        memory = process.memory_info()
        return {
            "rss_mb": memory.rss / 1024 / 1024,
            "vms_mb": memory.vms / 1024 / 1024
        }
```

---

## Context Preservation

### Session State Serialization

```python
import pickle
import json
from typing import Any, Dict

class SessionStateSerializer:
    """Serialize and deserialize session state."""
    
    def __init__(self):
        self.serializers = {
            "json": self._serialize_json,
            "pickle": self._serialize_pickle,
            "custom": self._serialize_custom
        }
        self.deserializers = {
            "json": self._deserialize_json,
            "pickle": self._deserialize_pickle,
            "custom": self._deserialize_custom
        }
    
    async def serialize(self, 
                       state: Dict[str, Any],
                       format: str = "json") -> bytes:
        """Serialize session state."""
        if format not in self.serializers:
            raise ValueError(f"Unknown format: {format}")
        
        return await self.serializers[format](state)
    
    async def deserialize(self,
                         data: bytes,
                         format: str = "json") -> Dict[str, Any]:
        """Deserialize session state."""
        if format not in self.deserializers:
            raise ValueError(f"Unknown format: {format}")
        
        return await self.deserializers[format](data)
    
    async def _serialize_json(self, state: Dict[str, Any]) -> bytes:
        """JSON serialization."""
        # Convert non-serializable objects
        clean_state = self._prepare_for_json(state)
        return json.dumps(clean_state).encode()
    
    async def _deserialize_json(self, data: bytes) -> Dict[str, Any]:
        """JSON deserialization."""
        state = json.loads(data.decode())
        return self._restore_from_json(state)
    
    async def _serialize_pickle(self, state: Dict[str, Any]) -> bytes:
        """Pickle serialization (includes more object types)."""
        return pickle.dumps(state)
    
    async def _deserialize_pickle(self, data: bytes) -> Dict[str, Any]:
        """Pickle deserialization."""
        return pickle.loads(data)
    
    async def _serialize_custom(self, state: Dict[str, Any]) -> bytes:
        """Custom serialization for complex objects."""
        # Implement custom logic for specific types
        pass
    
    def _prepare_for_json(self, obj: Any) -> Any:
        """Prepare object for JSON serialization."""
        if isinstance(obj, datetime):
            return obj.isoformat()
        elif isinstance(obj, set):
            return list(obj)
        elif isinstance(obj, dict):
            return {k: self._prepare_for_json(v) for k, v in obj.items()}
        elif isinstance(obj, list):
            return [self._prepare_for_json(item) for item in obj]
        elif hasattr(obj, "__dict__"):
            return self._prepare_for_json(obj.__dict__)
        else:
            return obj
    
    def _restore_from_json(self, obj: Any) -> Any:
        """Restore objects from JSON."""
        # Implement restoration logic
        return obj
```

### Cross-Session Continuity

```python
class SessionContinuityManager:
    """Manage continuity across agent sessions."""
    
    def __init__(self, storage_backend: Optional[StorageBackend] = None):
        self.storage = storage_backend or InMemoryStorage()
        self.serializer = SessionStateSerializer()
    
    async def save_session(self, 
                          agent_id: str,
                          case_name: str,
                          session_data: Dict[str, Any]) -> str:
        """Save session for later restoration."""
        session_id = self._generate_session_id(agent_id, case_name)
        
        # Prepare session data
        session = {
            "agent_id": agent_id,
            "case_name": case_name,
            "timestamp": datetime.now(),
            "data": session_data,
            "version": "1.0"
        }
        
        # Serialize and store
        serialized = await self.serializer.serialize(session)
        await self.storage.store(session_id, serialized)
        
        return session_id
    
    async def restore_session(self, session_id: str) -> Dict[str, Any]:
        """Restore previous session."""
        # Retrieve from storage
        serialized = await self.storage.retrieve(session_id)
        if not serialized:
            raise ValueError(f"Session {session_id} not found")
        
        # Deserialize
        session = await self.serializer.deserialize(serialized)
        
        # Check version compatibility
        if session.get("version") != "1.0":
            session = await self._migrate_session(session)
        
        return session
    
    async def list_sessions(self, 
                           agent_id: Optional[str] = None,
                           case_name: Optional[str] = None) -> List[Dict[str, Any]]:
        """List available sessions."""
        all_sessions = await self.storage.list_keys()
        
        sessions = []
        for session_id in all_sessions:
            try:
                session = await self.restore_session(session_id)
                
                # Apply filters
                if agent_id and session["agent_id"] != agent_id:
                    continue
                if case_name and session["case_name"] != case_name:
                    continue
                
                sessions.append({
                    "session_id": session_id,
                    "agent_id": session["agent_id"],
                    "case_name": session["case_name"],
                    "timestamp": session["timestamp"]
                })
                
            except Exception as e:
                logger.warning(f"Failed to load session {session_id}: {e}")
        
        return sessions
    
    def _generate_session_id(self, agent_id: str, case_name: str) -> str:
        """Generate unique session ID."""
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        return f"{agent_id}_{case_name}_{timestamp}"
    
    async def _migrate_session(self, session: Dict[str, Any]) -> Dict[str, Any]:
        """Migrate session data to current version."""
        # Implement migration logic
        return session
```

### Context Migration Between Agents

```python
class AgentContextMigrator:
    """Migrate context between different agents."""
    
    def __init__(self):
        self.migration_rules = {}
        self.transformation_functions = {}
    
    def register_migration_rule(self,
                               from_agent: str,
                               to_agent: str,
                               rule: Dict[str, Any]):
        """Register migration rule between agents."""
        key = f"{from_agent}->{to_agent}"
        self.migration_rules[key] = rule
    
    def register_transformation(self,
                               name: str,
                               transform_fn: Callable):
        """Register data transformation function."""
        self.transformation_functions[name] = transform_fn
    
    async def migrate_context(self,
                             from_context: ActivationContext,
                             to_agent: AgentDefinition) -> Dict[str, Any]:
        """Migrate context from one agent to another."""
        from_agent_id = from_context.agent_def.id
        to_agent_id = to_agent.id
        
        # Find migration rule
        rule_key = f"{from_agent_id}->{to_agent_id}"
        if rule_key not in self.migration_rules:
            # Try generic rules
            rule_key = f"*->{to_agent_id}"
            if rule_key not in self.migration_rules:
                rule_key = f"{from_agent_id}->*"
                if rule_key not in self.migration_rules:
                    # Default migration
                    return await self._default_migration(from_context)
        
        rule = self.migration_rules[rule_key]
        return await self._apply_migration_rule(from_context, rule)
    
    async def _apply_migration_rule(self,
                                   from_context: ActivationContext,
                                   rule: Dict[str, Any]) -> Dict[str, Any]:
        """Apply migration rule to context."""
        migrated = {}
        
        # Map fields according to rule
        for target_field, source_spec in rule.get("field_mapping", {}).items():
            if isinstance(source_spec, str):
                # Direct mapping
                value = self._get_nested_value(from_context, source_spec)
            else:
                # Complex mapping with transformation
                source_field = source_spec.get("source")
                transform = source_spec.get("transform")
                
                value = self._get_nested_value(from_context, source_field)
                
                if transform and transform in self.transformation_functions:
                    value = await self.transformation_functions[transform](value)
            
            self._set_nested_value(migrated, target_field, value)
        
        # Apply defaults
        for field, default_value in rule.get("defaults", {}).items():
            if not self._has_nested_value(migrated, field):
                self._set_nested_value(migrated, field, default_value)
        
        return migrated
    
    async def _default_migration(self, from_context: ActivationContext) -> Dict[str, Any]:
        """Default migration strategy."""
        return {
            "case_name": from_context.case_name,
            "previous_agent": from_context.agent_def.id,
            "shared_data": getattr(from_context, "shared_data", {}),
            "timestamp": datetime.now()
        }
    
    def _get_nested_value(self, obj: Any, path: str) -> Any:
        """Get nested value using dot notation."""
        parts = path.split(".")
        current = obj
        
        for part in parts:
            if hasattr(current, part):
                current = getattr(current, part)
            elif isinstance(current, dict) and part in current:
                current = current[part]
            else:
                return None
        
        return current
    
    def _set_nested_value(self, obj: Dict[str, Any], path: str, value: Any):
        """Set nested value using dot notation."""
        parts = path.split(".")
        current = obj
        
        for part in parts[:-1]:
            if part not in current:
                current[part] = {}
            current = current[part]
        
        current[parts[-1]] = value
    
    def _has_nested_value(self, obj: Dict[str, Any], path: str) -> bool:
        """Check if nested value exists."""
        return self._get_nested_value(obj, path) is not None
```

### State Versioning Support

```python
class StateVersionManager:
    """Manage state versioning for backward compatibility."""
    
    def __init__(self):
        self.version_schemas = {}
        self.migration_paths = {}
        self.current_version = "2.0.0"
    
    def register_version_schema(self, version: str, schema: Dict[str, Any]):
        """Register schema for specific version."""
        self.version_schemas[version] = schema
    
    def register_migration_path(self, 
                               from_version: str,
                               to_version: str,
                               migrator: Callable):
        """Register migration path between versions."""
        key = f"{from_version}->{to_version}"
        self.migration_paths[key] = migrator
    
    async def validate_state(self, state: Dict[str, Any]) -> bool:
        """Validate state against its version schema."""
        version = state.get("_version", "1.0.0")
        
        if version not in self.version_schemas:
            logger.warning(f"No schema for version {version}")
            return True
        
        schema = self.version_schemas[version]
        return self._validate_against_schema(state, schema)
    
    async def migrate_state(self, state: Dict[str, Any]) -> Dict[str, Any]:
        """Migrate state to current version."""
        from_version = state.get("_version", "1.0.0")
        
        if from_version == self.current_version:
            return state
        
        # Find migration path
        path = self._find_migration_path(from_version, self.current_version)
        if not path:
            raise ValueError(f"No migration path from {from_version} to {self.current_version}")
        
        # Apply migrations in sequence
        current_state = state.copy()
        for i in range(len(path) - 1):
            from_v = path[i]
            to_v = path[i + 1]
            
            migration_key = f"{from_v}->{to_v}"
            if migration_key in self.migration_paths:
                migrator = self.migration_paths[migration_key]
                current_state = await migrator(current_state)
                current_state["_version"] = to_v
        
        return current_state
    
    def _find_migration_path(self, from_version: str, to_version: str) -> List[str]:
        """Find migration path using BFS."""
        from collections import deque
        
        # Build graph
        graph = {}
        for key in self.migration_paths:
            from_v, to_v = key.split("->")
            if from_v not in graph:
                graph[from_v] = []
            graph[from_v].append(to_v)
        
        # BFS to find path
        queue = deque([(from_version, [from_version])])
        visited = {from_version}
        
        while queue:
            current, path = queue.popleft()
            
            if current == to_version:
                return path
            
            if current in graph:
                for next_version in graph[current]:
                    if next_version not in visited:
                        visited.add(next_version)
                        queue.append((next_version, path + [next_version]))
        
        return None
    
    def _validate_against_schema(self, state: Dict[str, Any], schema: Dict[str, Any]) -> bool:
        """Validate state against schema."""
        # Simple validation - can be enhanced with jsonschema
        required_fields = schema.get("required", [])
        
        for field in required_fields:
            if field not in state:
                return False
        
        return True
```

---

## Implementation Examples

### Complete Activation Example

```python
async def activate_legal_agent(agent_id: str, 
                              case_name: str,
                              user_id: str,
                              config: Dict[str, Any] = None) -> ActivationContext:
    """Complete example of activating a legal agent."""
    
    # 1. Load agent definition
    loader = AgentLoader()
    agent_def = await loader.load_agent(agent_id)
    
    # 2. Create security context
    from src.middleware.case_context import get_case_context
    case_context = await get_case_context(case_name, user_id)
    security_context = AgentSecurityContext(case_context, agent_id)
    
    # 3. Set up activation with all features
    activator = AgentActivator()
    
    # Register plugins
    plugin_registry = ActivationPluginRegistry()
    plugin_registry.register(SecurityEnhancementPlugin())
    
    # Set up recovery
    rollback = ActivationRollback()
    checkpoint_manager = RecoveryCheckpointManager()
    
    # Configure degradation
    degradation_handler = DegradedModeHandler()
    
    # 4. Create activation context
    context = ActivationContext(
        agent_def=agent_def,
        security_context=security_context,
        case_name=case_name,
        activation_config=config or {}
    )
    
    try:
        # Pre-activation plugins
        await plugin_registry.execute_pre_activation(context)
        
        # Checkpoint before activation
        await checkpoint_manager.save_checkpoint("pre_activation", context)
        
        # Activate with monitoring
        async with activation_context(
            agent_def=agent_def,
            case_name=case_name,
            security_context=security_context,
            **(config or {})
        ) as activated_context:
            
            # Post-activation plugins
            await plugin_registry.execute_post_activation(activated_context)
            
            # Save session for continuity
            continuity_manager = SessionContinuityManager()
            session_id = await continuity_manager.save_session(
                agent_id=agent_id,
                case_name=case_name,
                session_data={
                    "activation_time": datetime.now(),
                    "user_id": user_id,
                    "config": config
                }
            )
            
            logger.info(f"Agent {agent_id} activated successfully. Session: {session_id}")
            return activated_context
            
    except Exception as e:
        # Collect diagnostics
        diagnostics = await DiagnosticCollector.collect_diagnostics(e, context)
        logger.error(f"Activation failed: {diagnostics.to_report()}")
        
        # Attempt recovery
        if await checkpoint_manager.attempt_recovery("pre_activation", e, context):
            # Try degraded mode
            await degradation_handler.apply_degradation(context, "limited_commands")
            return context
        else:
            # Full rollback
            await rollback.full_rollback()
            raise


# Usage example
if __name__ == "__main__":
    import asyncio
    
    async def main():
        context = await activate_legal_agent(
            agent_id="discovery-analyzer",
            case_name="Smith_v_Jones_2024",
            user_id="user-123",
            config={
                "api_mode": False,
                "debug": True,
                "security_level": "enhanced"
            }
        )
        
        print(f"Agent state: {context.state}")
        print(f"Available commands: {context.agent_def.commands}")
    
    asyncio.run(main())
```

### Custom Activation for API Mode

```python
async def activate_api_agent(agent_id: str,
                            case_name: str,
                            api_key: str) -> ActivationContext:
    """Activate agent for API-only mode."""
    
    # Custom API configuration
    api_config = {
        "api_mode": True,
        "skip_greeting": True,
        "response_format": "json",
        "timeout": 300,
        "rate_limit": 100
    }
    
    # API-specific security
    security_context = await create_api_security_context(api_key)
    
    # Activate with API plugins
    context = await activate_legal_agent(
        agent_id=agent_id,
        case_name=case_name,
        user_id=security_context.user_id,
        config=api_config
    )
    
    # Set up API-specific handlers
    context.response_formatter = JSONResponseFormatter()
    context.error_handler = APIErrorHandler()
    
    return context
```

This completes the ACTIVATION_PATTERNS.md documentation. The file provides comprehensive coverage of agent activation patterns including standard flows, custom activation support, error recovery, and context preservation mechanisms.