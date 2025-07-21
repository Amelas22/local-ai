"""
Tests for Good Faith Letter BMad templates.
"""
import pytest
from pathlib import Path
import yaml

from ai_agents.bmad_framework.template_loader import TemplateLoader


class TestGoodFaithLetterTemplates:
    """Test suite for Good Faith Letter templates."""
    
    def test_federal_template_structure(self):
        """Test federal template has required BMad structure."""
        template_path = Path(__file__).parent.parent / "good-faith-letters" / "good-faith-letter-federal.yaml"
        
        with open(template_path, 'r') as f:
            template_data = yaml.safe_load(f)
        
        # Check metadata
        assert template_data['metadata']['type'] == 'legal_document'
        assert template_data['metadata']['subtype'] == 'good_faith_letter'
        assert template_data['metadata']['jurisdiction'] == 'federal'
        
        # Check sections exist
        assert 'sections' in template_data
        section_names = [s['name'] for s in template_data['sections']]
        
        # Required sections for Good Faith letters
        required_sections = [
            'header', 'date_line', 'recipient_info', 
            're_line', 'salutation', 'opening_paragraph',
            'closing_paragraph', 'signature_block'
        ]
        
        for section in required_sections:
            assert section in section_names
    
    def test_state_template_structure(self):
        """Test state template has required BMad structure."""
        template_path = Path(__file__).parent.parent / "good-faith-letters" / "good-faith-letter-state.yaml"
        
        with open(template_path, 'r') as f:
            template_data = yaml.safe_load(f)
        
        # Check metadata
        assert template_data['metadata']['type'] == 'legal_document'
        assert template_data['metadata']['subtype'] == 'good_faith_letter' 
        assert template_data['metadata']['jurisdiction'] == 'state'
        
        # Check state-specific configurations
        assert 'validation_rules' in template_data
        assert 'required_variables' in template_data['validation_rules']
    
    def test_template_variables_format(self):
        """Test template variables follow BMad naming convention."""
        for template_name in ['good-faith-letter-federal.yaml', 'good-faith-letter-state.yaml']:
            template_path = Path(__file__).parent.parent / "good-faith-letters" / template_name
            
            with open(template_path, 'r') as f:
                template_data = yaml.safe_load(f)
            
            # Check all variables follow UPPERCASE_UNDERSCORE pattern
            for section in template_data['sections']:
                if 'variables' in section:
                    for var in section['variables']:
                        assert var.isupper()
                        assert all(c.isalnum() or c == '_' for c in var)
    
    @pytest.mark.asyncio
    async def test_template_loader_can_load(self):
        """Test TemplateLoader can load Good Faith templates."""
        loader = TemplateLoader()
        
        # Load federal template
        federal_template = await loader.load_template("good-faith-letters/good-faith-letter-federal.yaml")
        assert federal_template is not None
        assert federal_template.metadata['jurisdiction'] == 'federal'
        
        # Load state template
        state_template = await loader.load_template("good-faith-letters/good-faith-letter-state.yaml")
        assert state_template is not None
        assert state_template.metadata['jurisdiction'] == 'state'
    
    def test_frcp_rule_37_requirements(self):
        """Test federal template includes FRCP Rule 37 requirements."""
        template_path = Path(__file__).parent.parent / "good-faith-letters" / "good-faith-letter-federal.yaml"
        
        with open(template_path, 'r') as f:
            template_data = yaml.safe_load(f)
        
        # Check for meet and confer language in closing
        closing_section = next(
            s for s in template_data['sections'] 
            if s['name'] == 'closing_paragraph'
        )
        
        assert 'Meet and Confer' in closing_section['template']
        assert 'Motion to Compel' in closing_section['template']
    
    def test_template_output_formats(self):
        """Test templates support required output formats."""
        for template_name in ['good-faith-letter-federal.yaml', 'good-faith-letter-state.yaml']:
            template_path = Path(__file__).parent.parent / "good-faith-letters" / template_name
            
            with open(template_path, 'r') as f:
                template_data = yaml.safe_load(f)
            
            # Check output options
            assert 'output_options' in template_data
            assert 'formats' in template_data['output_options']
            
            formats = template_data['output_options']['formats']
            format_types = [list(f.keys())[0] for f in formats]
            
            # Should support at least PDF and DOCX
            assert 'pdf' in format_types
            assert 'docx' in format_types
    
    def test_repeatable_sections(self):
        """Test templates have repeatable sections for deficiency items."""
        template_path = Path(__file__).parent.parent / "good-faith-letters" / "good-faith-letter-federal.yaml"
        
        with open(template_path, 'r') as f:
            template_data = yaml.safe_load(f)
        
        # Find repeatable sections
        repeatable_sections = [
            s for s in template_data['sections']
            if s.get('repeatable', False)
        ]
        
        assert len(repeatable_sections) > 0
        
        # Check RTP items section is repeatable
        rtp_items = next(
            s for s in repeatable_sections
            if 'rtp_items' in s['name']
        )
        assert rtp_items is not None
    
    def test_conditional_sections(self):
        """Test templates support conditional sections."""
        template_path = Path(__file__).parent.parent / "good-faith-letters" / "good-faith-letter-federal.yaml"
        
        with open(template_path, 'r') as f:
            template_data = yaml.safe_load(f)
        
        # Find conditional sections
        conditional_sections = [
            s for s in template_data['sections']
            if 'condition' in s
        ]
        
        assert len(conditional_sections) > 0
        
        # Check interrogatory sections are conditional
        interrogatory_section = next(
            s for s in conditional_sections
            if 'interrogatory' in s['name']
        )
        assert interrogatory_section['condition'] == "HAS_INTERROGATORY_DEFICIENCIES == true"