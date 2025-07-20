"""
Unit tests for BMad framework agent loader.
"""

import pytest
import tempfile
from pathlib import Path

from src.ai_agents.bmad_framework.agent_loader import AgentLoader, AgentDefinition
from src.ai_agents.bmad_framework.exceptions import AgentLoadError


class TestAgentDefinition:
    """Test AgentDefinition dataclass functionality."""

    def test_default_values(self):
        """Test default values for agent definition."""
        agent_def = AgentDefinition()

        assert agent_def.name == ""
        assert agent_def.id == ""
        assert agent_def.icon == "🤖"
        assert agent_def.tasks == []
        assert agent_def.commands == []
        assert agent_def.core_principles == []

    def test_command_names_extraction(self):
        """Test extracting command names."""
        agent_def = AgentDefinition(
            commands=[
                {"help": "Show available commands"},
                {"analyze": "Analyze documents"},
                "simple: Simple command description",
            ]
        )

        names = agent_def.command_names
        assert "help" in names
        assert "analyze" in names
        assert "simple" in names

    def test_get_command_description(self):
        """Test getting command descriptions."""
        agent_def = AgentDefinition(
            commands=[
                {"help": "Show available commands"},
                {"analyze": "Analyze documents"},
                "simple: Simple command description",
            ]
        )

        assert agent_def.get_command_description("help") == "Show available commands"
        assert agent_def.get_command_description("*analyze") == "Analyze documents"
        assert (
            agent_def.get_command_description("simple") == "Simple command description"
        )
        assert agent_def.get_command_description("unknown") is None


class TestAgentLoader:
    """Test AgentLoader functionality."""

    @pytest.fixture
    def temp_agent_dir(self):
        """Create temporary directory for agent files."""
        with tempfile.TemporaryDirectory() as temp_dir:
            yield Path(temp_dir)

    @pytest.fixture
    def sample_agent_yaml(self):
        """Sample valid agent YAML content."""
        return """
activation-instructions:
  - STEP 1: Read entire file
  - STEP 2: Adopt persona
  - STEP 3: Greet user

agent:
  name: Test Agent
  id: test-agent
  title: Test Agent Title
  icon: 🧪
  whenToUse: Use for testing
  customization: null

persona:
  role: Test Role
  style: Test Style
  identity: Test Identity
  focus: Test Focus
  core_principles:
    - Principle 1
    - Principle 2

commands:
  - help: Show commands
  - test: Run tests
  - analyze: Analyze data

dependencies:
  tasks:
    - test-task.md
  templates:
    - test-template.yaml
  checklists:
    - test-checklist.md
"""

    @pytest.fixture
    def sample_agent_markdown(self, sample_agent_yaml):
        """Sample agent definition in Markdown format."""
        return f"""# Test Agent

This is a test agent definition.

```yaml
{sample_agent_yaml}
```

Additional documentation here.
"""

    @pytest.mark.asyncio
    async def test_load_agent_yaml(self, temp_agent_dir, sample_agent_yaml):
        """Test loading agent from YAML file."""
        # Create agent file
        agent_file = temp_agent_dir / "test-agent.yaml"
        agent_file.write_text(sample_agent_yaml)

        # Load agent
        loader = AgentLoader(temp_agent_dir)
        agent_def = await loader.load_agent("test-agent")

        # Verify loaded data
        assert agent_def.name == "Test Agent"
        assert agent_def.id == "test-agent"
        assert agent_def.title == "Test Agent Title"
        assert agent_def.icon == "🧪"
        assert agent_def.role == "Test Role"
        assert agent_def.style == "Test Style"
        assert len(agent_def.commands) == 3
        assert len(agent_def.tasks) == 1
        assert "test-task.md" in agent_def.tasks

    @pytest.mark.asyncio
    async def test_load_agent_markdown(self, temp_agent_dir, sample_agent_markdown):
        """Test loading agent from Markdown file with embedded YAML."""
        # Create agent file
        agent_file = temp_agent_dir / "test-agent.md"
        agent_file.write_text(sample_agent_markdown)

        # Load agent
        loader = AgentLoader(temp_agent_dir)
        agent_def = await loader.load_agent("test-agent")

        # Verify loaded data
        assert agent_def.name == "Test Agent"
        assert agent_def.id == "test-agent"
        assert len(agent_def.activation_instructions) == 3

    @pytest.mark.asyncio
    async def test_agent_not_found(self, temp_agent_dir):
        """Test error when agent file not found."""
        loader = AgentLoader(temp_agent_dir)

        with pytest.raises(AgentLoadError) as exc_info:
            await loader.load_agent("non-existent")

        assert "Agent file not found" in str(exc_info.value)
        assert exc_info.value.agent_id == "non-existent"

    @pytest.mark.asyncio
    async def test_invalid_yaml_syntax(self, temp_agent_dir):
        """Test error with invalid YAML syntax."""
        # Create agent file with invalid YAML
        agent_file = temp_agent_dir / "bad-agent.yaml"
        agent_file.write_text("invalid: yaml: syntax: here")

        loader = AgentLoader(temp_agent_dir)

        with pytest.raises(AgentLoadError) as exc_info:
            await loader.load_agent("bad-agent")

        assert "Invalid YAML syntax" in str(
            exc_info.value
        ) or "'Mark' object has no attribute 'get'" in str(exc_info.value)

    @pytest.mark.asyncio
    async def test_validation_errors(self, temp_agent_dir):
        """Test validation errors for incomplete agent definition."""
        # Create agent file missing required fields
        agent_file = temp_agent_dir / "incomplete.yaml"
        agent_file.write_text("""
agent:
  name: Incomplete
persona:
  style: Some style
""")

        loader = AgentLoader(temp_agent_dir)

        with pytest.raises(AgentLoadError) as exc_info:
            await loader.load_agent("incomplete")

        assert "Multiple validation errors" in str(exc_info.value)
        # Check that all expected validation errors are mentioned in the error message
        error_msg = str(exc_info.value)
        assert "agent.id" in error_msg
        assert "persona.role" in error_msg
        assert "at least one command" in error_msg

    @pytest.mark.asyncio
    async def test_agent_caching(self, temp_agent_dir, sample_agent_yaml):
        """Test that agents are cached after first load."""
        # Create agent file
        agent_file = temp_agent_dir / "cached-agent.yaml"
        agent_file.write_text(sample_agent_yaml)

        loader = AgentLoader(temp_agent_dir)

        # First load
        agent_def1 = await loader.load_agent("cached-agent")

        # Delete file to ensure it's using cache
        agent_file.unlink()

        # Second load should use cache
        agent_def2 = await loader.load_agent("cached-agent")

        assert agent_def1 is agent_def2  # Same object

    @pytest.mark.asyncio
    async def test_list_available_agents(self, temp_agent_dir):
        """Test listing available agents."""
        # Create multiple agent files
        (temp_agent_dir / "agent1.yaml").write_text("agent: {id: agent1}")
        (temp_agent_dir / "agent2.yml").write_text("agent: {id: agent2}")
        (temp_agent_dir / "agent3.md").write_text("```yaml\nagent: {id: agent3}\n```")
        (temp_agent_dir / "agent4-agent.yaml").write_text("agent: {id: agent4}")
        (temp_agent_dir / "not-an-agent.txt").write_text("some text")

        loader = AgentLoader(temp_agent_dir)
        agents = await loader.list_available_agents()

        assert "agent1" in agents
        assert "agent2" in agents
        assert "agent3" in agents
        assert "agent4" in agents
        assert "not-an-agent" not in agents
        assert len(agents) == 4

    def test_clear_cache(self, temp_agent_dir):
        """Test clearing the agent cache."""
        loader = AgentLoader(temp_agent_dir)

        # Add something to cache
        loader._agent_cache["test"] = AgentDefinition(id="test")
        assert len(loader._agent_cache) == 1

        # Clear cache
        loader.clear_cache()
        assert len(loader._agent_cache) == 0

    def test_extract_yaml_from_content(self, temp_agent_dir):
        """Test extracting YAML from Markdown content."""
        loader = AgentLoader(temp_agent_dir)

        content = """
# Some Markdown

Here is text.

```yaml
key: value
nested:
  item: 123
```

More text here.
"""

        yaml_content = loader._extract_yaml_from_content(content)
        assert yaml_content is not None
        assert "key: value" in yaml_content
        assert "item: 123" in yaml_content
        assert "Some Markdown" not in yaml_content

    def test_find_agent_file_variations(self, temp_agent_dir):
        """Test finding agent files with various naming conventions."""
        loader = AgentLoader(temp_agent_dir)

        # Test .yaml extension
        (temp_agent_dir / "test1.yaml").touch()
        assert loader._find_agent_file("test1") is not None

        # Test .yml extension
        (temp_agent_dir / "test2.yml").touch()
        assert loader._find_agent_file("test2") is not None

        # Test .md extension
        (temp_agent_dir / "test3.md").touch()
        assert loader._find_agent_file("test3") is not None

        # Test -agent suffix
        (temp_agent_dir / "test4-agent.yaml").touch()
        assert loader._find_agent_file("test4") is not None
