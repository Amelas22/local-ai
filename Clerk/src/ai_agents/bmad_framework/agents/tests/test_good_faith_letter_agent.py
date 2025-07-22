"""
Tests for Good Faith Letter agent YAML definition loading.
"""
import pytest
from pathlib import Path
import yaml

from src.ai_agents.bmad_framework.agent_loader import AgentLoader
from src.ai_agents.bmad_framework.exceptions import AgentLoadError


class TestGoodFaithLetterAgent:
    """Test suite for Good Faith Letter agent."""
    
    def test_agent_yaml_structure(self):
        """Test agent YAML file has required structure."""
        agent_path = Path(__file__).parent.parent / "good-faith-letter.yaml"
        
        with open(agent_path, 'r') as f:
            agent_data = yaml.safe_load(f)
        
        # Check required top-level keys
        assert 'activation-instructions' in agent_data
        assert 'agent' in agent_data
        assert 'persona' in agent_data
        assert 'commands' in agent_data
        assert 'dependencies' in agent_data
        
        # Check agent metadata
        agent_meta = agent_data['agent']
        assert agent_meta['id'] == 'good-faith-letter'
        assert agent_meta['name'] == 'Good Faith Letter Generator'
        assert agent_meta['customization'] == 'API-only execution, no interactive mode'
        
        # Check commands
        commands = agent_data['commands']
        expected_commands = [
            'generate-letter',
            'select-template',
            'preview-letter',
            'customize-letter',
            'finalize-letter'
        ]
        
        for cmd in expected_commands:
            assert any(cmd in str(c) for c in commands)
    
    @pytest.mark.asyncio
    async def test_agent_loader_can_load(self):
        """Test AgentLoader can load the agent definition."""
        loader = AgentLoader()
        
        # Load agent
        agent_def = await loader.load_agent("good-faith-letter")
        
        # Verify loaded correctly - AgentDefinition stores attributes directly
        assert agent_def is not None
        assert agent_def.id == "good-faith-letter"
        assert agent_def.name == "Good Faith Letter Generator"
        assert len(agent_def.commands) == 5
        
    @pytest.mark.asyncio
    async def test_agent_dependencies_valid(self):
        """Test agent dependencies are properly defined."""
        loader = AgentLoader()
        agent_def = await loader.load_agent("good-faith-letter")
        
        # Check dependencies - stored directly as attributes
        assert agent_def.tasks is not None
        assert agent_def.templates is not None
        assert agent_def.checklists is not None
        assert agent_def.data is not None
        
        # Verify task dependencies
        expected_tasks = [
            'select-letter-template.md',
            'populate-deficiency-findings.md',
            'generate-signature-block.md'
        ]
        for task in expected_tasks:
            assert task in agent_def.tasks
            
        # Verify template dependencies
        expected_templates = [
            'good-faith-letter-federal.yaml',
            'good-faith-letter-state.yaml'
        ]
        for template in expected_templates:
            assert template in agent_def.templates
    
    def test_agent_persona_configuration(self):
        """Test agent persona is properly configured."""
        agent_path = Path(__file__).parent.parent / "good-faith-letter.yaml"
        
        with open(agent_path, 'r') as f:
            agent_data = yaml.safe_load(f)
        
        persona = agent_data['persona']
        assert persona['role'] == 'Legal correspondence specialist'
        assert 'Professional' in persona['style']
        assert 'jurisdiction-aware' in persona['style']
        assert len(persona['core_principles']) == 4
        
    def test_agent_api_only_mode(self):
        """Test agent is configured for API-only execution."""
        agent_path = Path(__file__).parent.parent / "good-faith-letter.yaml"
        
        with open(agent_path, 'r') as f:
            agent_data = yaml.safe_load(f)
        
        # Check customization field indicates API-only
        customization = agent_data['agent']['customization']
        assert 'API-only execution' in customization
        assert 'no interactive mode' in customization