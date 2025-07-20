"""
Agent loader module for BMad framework.

This module handles loading and parsing of BMad agent YAML definitions.
"""

import yaml
import logging
from pathlib import Path
from typing import Dict, List, Optional, Any
from dataclasses import dataclass, field

from .exceptions import AgentLoadError, ValidationError

logger = logging.getLogger("clerk_api")


@dataclass
class AgentDefinition:
    """
    Parsed agent definition from YAML.

    Contains all metadata and configuration for a BMad agent.
    """

    # IDE file resolution
    ide_file_resolution: Optional[List[str]] = field(default_factory=list)
    request_resolution: Optional[str] = None

    # Activation instructions
    activation_instructions: List[str] = field(default_factory=list)

    # Agent metadata
    name: str = ""
    id: str = ""
    title: str = ""
    icon: str = "🤖"
    when_to_use: str = ""
    customization: Optional[str] = None

    # Persona
    role: str = ""
    style: str = ""
    identity: str = ""
    focus: str = ""
    core_principles: List[str] = field(default_factory=list)

    # Commands
    commands: List[Dict[str, str]] = field(default_factory=list)

    # Dependencies
    tasks: List[str] = field(default_factory=list)
    templates: List[str] = field(default_factory=list)
    checklists: List[str] = field(default_factory=list)
    data: List[str] = field(default_factory=list)
    utils: List[str] = field(default_factory=list)

    # Raw YAML content
    raw_yaml: Dict[str, Any] = field(default_factory=dict)

    @property
    def command_names(self) -> List[str]:
        """Get list of command names (without * prefix)."""
        names = []
        for cmd in self.commands:
            if isinstance(cmd, dict):
                names.extend(cmd.keys())
            elif isinstance(cmd, str):
                # Handle simple string commands
                names.append(cmd.split(":")[0].strip())
        return names

    def get_command_description(self, command: str) -> Optional[str]:
        """Get description for a specific command."""
        command = command.lstrip("*")
        for cmd in self.commands:
            if isinstance(cmd, dict) and command in cmd:
                return cmd[command]
            elif isinstance(cmd, str) and cmd.startswith(command):
                # Handle "command: description" format
                parts = cmd.split(":", 1)
                if len(parts) > 1:
                    return parts[1].strip()
        return None


class AgentLoader:
    """
    Loads and parses BMad agent definitions from YAML files.
    """

    def __init__(self, base_path: Optional[Path] = None):
        """
        Initialize agent loader.

        Args:
            base_path: Base path for agent definitions.
                      Defaults to bmad-framework/agents directory.
        """
        if base_path is None:
            base_path = Path(__file__).parent / "agents"
        self.base_path = Path(base_path)
        self._agent_cache: Dict[str, AgentDefinition] = {}

    async def load_agent(
        self, agent_id: str, force_reload: bool = False
    ) -> AgentDefinition:
        """
        Load an agent definition by ID.

        Args:
            agent_id: The agent ID to load.
            force_reload: Force reload from disk, bypassing cache.

        Returns:
            Parsed agent definition.

        Raises:
            AgentLoadError: If agent cannot be loaded.
        """
        # Validate agent_id
        if not agent_id or not isinstance(agent_id, str):
            raise AgentLoadError(
                agent_id or "empty",
                "Invalid agent ID provided",
                {"agent_id": agent_id, "type": type(agent_id).__name__},
            )

        # Check cache first unless force reload
        if not force_reload and agent_id in self._agent_cache:
            logger.debug(f"Returning cached agent: {agent_id}")
            return self._agent_cache[agent_id]

        # Find agent file
        agent_path = self._find_agent_file(agent_id)
        if not agent_path:
            available_agents = await self.list_available_agents()
            raise AgentLoadError(
                agent_id,
                f"Agent file not found in {self.base_path}",
                {
                    "searched_extensions": [".yaml", ".yml", ".md"],
                    "available_agents": available_agents,
                    "base_path": str(self.base_path),
                },
            )

        try:
            # Load and parse YAML
            agent_def = await self._parse_agent_file(agent_path)

            # Ensure agent ID matches filename
            if agent_def.id and agent_def.id != agent_id:
                logger.warning(
                    f"Agent ID mismatch: file={agent_id}, definition={agent_def.id}. "
                    f"Using definition ID."
                )

            # Validate definition
            self._validate_agent_definition(agent_def)

            # Cache the result
            self._agent_cache[agent_id] = agent_def

            logger.info(f"Successfully loaded agent: {agent_id} from {agent_path}")
            return agent_def

        except Exception as e:
            # Clear from cache on error
            self._agent_cache.pop(agent_id, None)

            if isinstance(e, (AgentLoadError, ValidationError)):
                raise

            raise AgentLoadError(
                agent_id,
                f"Failed to parse agent file: {str(e)}",
                {
                    "file_path": str(agent_path),
                    "error_type": type(e).__name__,
                    "error_details": str(e),
                },
            )

    def _find_agent_file(self, agent_id: str) -> Optional[Path]:
        """
        Find agent file by ID.

        Searches for files with various extensions.
        """
        # Try different file extensions
        for ext in [".yaml", ".yml", ".md"]:
            agent_path = self.base_path / f"{agent_id}{ext}"
            if agent_path.exists():
                return agent_path

        # Try with different naming conventions
        for ext in [".yaml", ".yml", ".md"]:
            agent_path = self.base_path / f"{agent_id}-agent{ext}"
            if agent_path.exists():
                return agent_path

        return None

    async def _parse_agent_file(self, file_path: Path) -> AgentDefinition:
        """
        Parse agent definition from file.

        Handles both pure YAML and Markdown with embedded YAML.
        """
        content = file_path.read_text(encoding="utf-8")

        # Extract YAML from Markdown if needed
        yaml_content = self._extract_yaml_from_content(content)
        if not yaml_content:
            yaml_content = content

        # Parse YAML
        try:
            data = yaml.safe_load(yaml_content)
        except yaml.YAMLError as e:
            raise AgentLoadError(
                file_path.stem,
                f"Invalid YAML syntax: {str(e)}",
                {"line": getattr(e, "problem_mark", {}).get("line", "unknown")},
            )

        if not isinstance(data, dict):
            raise AgentLoadError(
                file_path.stem,
                "YAML must be a dictionary/object",
                {"actual_type": type(data).__name__},
            )

        # Create agent definition
        agent_def = AgentDefinition(raw_yaml=data)

        # Parse IDE file resolution
        if "IDE-FILE-RESOLUTION" in data:
            agent_def.ide_file_resolution = data["IDE-FILE-RESOLUTION"]

        # Parse request resolution
        if "REQUEST-RESOLUTION" in data:
            agent_def.request_resolution = data["REQUEST-RESOLUTION"]

        # Parse activation instructions
        if "activation-instructions" in data:
            agent_def.activation_instructions = data["activation-instructions"]

        # Parse agent metadata
        if "agent" in data:
            agent_data = data["agent"]
            agent_def.name = agent_data.get("name", "")
            agent_def.id = agent_data.get("id", "")
            agent_def.title = agent_data.get("title", "")
            agent_def.icon = agent_data.get("icon", "🤖")
            agent_def.when_to_use = agent_data.get("whenToUse", "")
            agent_def.customization = agent_data.get("customization")

        # Parse persona
        if "persona" in data:
            persona_data = data["persona"]
            agent_def.role = persona_data.get("role", "")
            agent_def.style = persona_data.get("style", "")
            agent_def.identity = persona_data.get("identity", "")
            agent_def.focus = persona_data.get("focus", "")
            agent_def.core_principles = persona_data.get("core_principles", [])

        # Parse commands
        if "commands" in data:
            agent_def.commands = data["commands"]

        # Parse dependencies
        if "dependencies" in data:
            deps = data["dependencies"]
            agent_def.tasks = deps.get("tasks", [])
            agent_def.templates = deps.get("templates", [])
            agent_def.checklists = deps.get("checklists", [])
            agent_def.data = deps.get("data", [])
            agent_def.utils = deps.get("utils", [])

        return agent_def

    def _extract_yaml_from_content(self, content: str) -> Optional[str]:
        """
        Extract YAML block from Markdown content.

        Looks for ```yaml blocks in the content.
        """
        lines = content.split("\n")
        in_yaml = False
        yaml_lines = []

        for line in lines:
            if line.strip() == "```yaml":
                in_yaml = True
                continue
            elif line.strip() == "```" and in_yaml:
                # Found end of YAML block
                break
            elif in_yaml:
                yaml_lines.append(line)

        if yaml_lines:
            return "\n".join(yaml_lines)
        return None

    def _validate_agent_definition(self, agent_def: AgentDefinition) -> None:
        """
        Validate agent definition has required fields.

        Raises:
            ValidationError: If validation fails.
        """
        errors = []

        # Required agent metadata
        if not agent_def.id:
            errors.append("Missing required field: agent.id")
        if not agent_def.name:
            errors.append("Missing required field: agent.name")
        if not agent_def.title:
            errors.append("Missing required field: agent.title")

        # Required persona fields
        if not agent_def.role:
            errors.append("Missing required field: persona.role")
        if not agent_def.style:
            errors.append("Missing required field: persona.style")

        # Must have at least one command
        if not agent_def.commands:
            errors.append("Agent must define at least one command")

        # Activation instructions recommended
        if not agent_def.activation_instructions:
            logger.warning(f"Agent {agent_def.id} has no activation instructions")

        if errors:
            raise ValidationError(
                "Agent definition",
                f"Multiple validation errors: {'; '.join(errors)}",
                {"errors": errors, "agent_id": agent_def.id},
            )

    async def list_available_agents(self) -> List[str]:
        """
        List all available agent IDs.

        Returns:
            List of agent IDs found in the base path.
        """
        if not self.base_path.exists():
            return []

        agent_ids = set()

        # Search for agent files
        for ext in [".yaml", ".yml", ".md"]:
            for file_path in self.base_path.glob(f"*{ext}"):
                # Extract agent ID from filename
                agent_id = file_path.stem
                if agent_id.endswith("-agent"):
                    agent_id = agent_id[:-6]  # Remove "-agent" suffix
                agent_ids.add(agent_id)

        return sorted(list(agent_ids))

    def clear_cache(self) -> None:
        """Clear the agent definition cache."""
        self._agent_cache.clear()
        logger.debug("Cleared agent loader cache")
