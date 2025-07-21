"""
Tests for Good Faith Letter data files.
"""
import pytest
import json
from pathlib import Path


class TestJurisdictionRequirements:
    """Test suite for jurisdiction requirements data."""
    
    def test_jurisdiction_file_exists_and_valid(self):
        """Test jurisdiction requirements file exists and is valid JSON."""
        data_path = Path(__file__).parent.parent / "jurisdiction-requirements.json"
        assert data_path.exists()
        
        with open(data_path, 'r') as f:
            data = json.load(f)
        
        # Check required top-level keys
        assert 'federal' in data
        assert 'states' in data
        assert 'general_requirements' in data
    
    def test_federal_requirements_complete(self):
        """Test federal jurisdiction has all required fields."""
        data_path = Path(__file__).parent.parent / "jurisdiction-requirements.json"
        
        with open(data_path, 'r') as f:
            data = json.load(f)
        
        federal = data['federal']
        
        # Check required fields
        assert 'discovery_rules' in federal
        assert 'response_deadlines' in federal
        assert 'required_elements' in federal
        assert 'citation_format' in federal
        
        # Check Rule 37 details
        rule_37 = federal['discovery_rules']['rule_37']
        assert rule_37['meet_and_confer_required'] is True
        assert 'certification_language' in rule_37
        assert len(rule_37['motion_requirements']) > 0
    
    def test_state_requirements_complete(self):
        """Test each state has required fields."""
        data_path = Path(__file__).parent.parent / "jurisdiction-requirements.json"
        
        with open(data_path, 'r') as f:
            data = json.load(f)
        
        required_states = ['FL', 'TX', 'CA', 'NY']
        
        for state_code in required_states:
            assert state_code in data['states']
            
            state = data['states'][state_code]
            assert 'name' in state
            assert 'discovery_rules' in state
            assert 'response_deadlines' in state
            assert 'required_elements' in state
            assert 'citation_format' in state
    
    def test_response_deadlines_format(self):
        """Test response deadline data structure."""
        data_path = Path(__file__).parent.parent / "jurisdiction-requirements.json"
        
        with open(data_path, 'r') as f:
            data = json.load(f)
        
        # Check federal
        federal_deadlines = data['federal']['response_deadlines']
        assert 'standard_days' in federal_deadlines
        assert isinstance(federal_deadlines['standard_days'], int)
        
        # Check states
        for state_code, state_data in data['states'].items():
            deadlines = state_data['response_deadlines']
            assert 'standard_days' in deadlines
            assert isinstance(deadlines['standard_days'], int)
            assert deadlines['standard_days'] > 0


class TestStandardLegalPhrases:
    """Test suite for standard legal phrases data."""
    
    def test_phrases_file_exists_and_valid(self):
        """Test standard phrases file exists and is valid JSON."""
        data_path = Path(__file__).parent.parent / "standard-legal-phrases.json"
        assert data_path.exists()
        
        with open(data_path, 'r') as f:
            data = json.load(f)
        
        # Check major categories exist
        expected_categories = [
            'salutations',
            'opening_phrases',
            'deficiency_introductions',
            'meet_and_confer',
            'deadline_language',
            'closing_phrases'
        ]
        
        for category in expected_categories:
            assert category in data
    
    def test_salutations_structure(self):
        """Test salutations have proper structure."""
        data_path = Path(__file__).parent.parent / "standard-legal-phrases.json"
        
        with open(data_path, 'r') as f:
            data = json.load(f)
        
        salutations = data['salutations']
        assert 'formal' in salutations
        assert isinstance(salutations['formal'], list)
        assert len(salutations['formal']) > 0
        assert 'avoid' in salutations
    
    def test_meet_and_confer_language(self):
        """Test meet and confer sections."""
        data_path = Path(__file__).parent.parent / "standard-legal-phrases.json"
        
        with open(data_path, 'r') as f:
            data = json.load(f)
        
        meet_confer = data['meet_and_confer']
        assert 'certification' in meet_confer
        assert 'federal' in meet_confer['certification']
        assert 'proposals' in meet_confer
        assert isinstance(meet_confer['proposals'], list)
    
    def test_professional_tone_guidance(self):
        """Test professional tone section exists."""
        data_path = Path(__file__).parent.parent / "standard-legal-phrases.json"
        
        with open(data_path, 'r') as f:
            data = json.load(f)
        
        tone = data['professional_tone']
        assert 'avoid_phrases' in tone
        assert 'preferred_alternatives' in tone
        
        # Check alternatives exist for avoided phrases
        for phrase in ['you_failed', 'bad_faith']:
            assert phrase in tone['preferred_alternatives']
    
    def test_motion_warnings_available(self):
        """Test motion to compel warning language."""
        data_path = Path(__file__).parent.parent / "standard-legal-phrases.json"
        
        with open(data_path, 'r') as f:
            data = json.load(f)
        
        warnings = data['motion_warnings']
        assert 'standard' in warnings
        assert 'diplomatic' in warnings
        assert 'Motion to Compel' in warnings['standard']
    
    def test_no_placeholder_values(self):
        """Test that placeholder values are properly formatted."""
        data_path = Path(__file__).parent.parent / "standard-legal-phrases.json"
        
        with open(data_path, 'r') as f:
            content = f.read()
        
        # Check for common placeholder patterns
        assert '[DATE]' in content  # Placeholders should exist
        assert '[NUMBER]' in content
        assert '{{' not in content  # But not template syntax in data
    
    def test_all_phrase_lists_non_empty(self):
        """Test all phrase lists contain at least one item."""
        data_path = Path(__file__).parent.parent / "standard-legal-phrases.json"
        
        with open(data_path, 'r') as f:
            data = json.load(f)
        
        def check_non_empty(obj, path=""):
            if isinstance(obj, list):
                assert len(obj) > 0, f"Empty list at {path}"
            elif isinstance(obj, dict):
                for key, value in obj.items():
                    check_non_empty(value, f"{path}.{key}")
        
        check_non_empty(data)