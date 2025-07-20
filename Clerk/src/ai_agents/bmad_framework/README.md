# BMad Framework for Legal AI Agents

This framework adapts the BMad creator tools patterns for legal AI agents in the Clerk system.

## Directory Structure

```
bmad-framework/
├── __init__.py          # Module exports
├── agents/              # Agent YAML definitions
├── tasks/               # Task definitions (.md files)
├── templates/           # Document templates (.yaml files)
├── checklists/          # Validation checklists (.md files)
├── data/                # Reference data (.json files)
├── tests/               # Unit tests for framework components
├── agent_loader.py      # YAML parser for agent definitions
├── agent_executor.py    # Executes agents with API integration
├── api_mapper.py        # Maps BMad commands to FastAPI endpoints
├── exceptions.py        # Framework-specific exceptions
└── README.md            # This file
```

## Agent Structure

Agents are defined using YAML files with the following structure:

```yaml
activation-instructions:
  - Step-by-step activation process
  
agent:
  name: Agent Name
  id: unique-agent-id
  title: Professional Title
  icon: 🎯
  whenToUse: When to use this agent
  customization: Additional customization
  
persona:
  role: Role description
  style: Communication style
  identity: Agent identity
  focus: Primary focus areas
  core_principles:
    - Principle 1
    - Principle 2
    
commands:
  - help: Show available commands
  - command_name: Command description
  
dependencies:
  tasks:
    - task-file.md
  templates:
    - template-file.yaml
  checklists:
    - checklist-file.md
  data:
    - data-file.json
```

## Usage

1. Create an agent definition YAML file in the `agents/` directory
2. Create supporting tasks, templates, and checklists in their respective directories
3. Load and execute the agent using the framework:

```python
from ai_agents.bmad_framework import AgentLoader, AgentExecutor

# Load agent definition
loader = AgentLoader()
agent_def = await loader.load_agent("discovery-analyzer")

# Execute agent
executor = AgentExecutor()
result = await executor.execute_command(
    agent_def=agent_def,
    command="analyze",
    case_name="Smith_v_Jones_2024",
    params={"rtp_id": "123", "production_id": "456"}
)
```

## Case Isolation

All operations MUST include case_name parameter to ensure proper data isolation between legal cases.

## WebSocket Integration

Long-running tasks emit progress events following the pattern:
- `agent:task_progress` - Progress updates
- `agent:task_started` - Task initiation
- `agent:task_completed` - Successful completion
- `agent:task_failed` - Error notification

## Testing

All framework components have comprehensive unit tests in the `tests/` directory following pytest conventions.