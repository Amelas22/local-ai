"""
Tests for Good Faith Letter compliance checklists.
"""
import pytest
from pathlib import Path
import re


class TestLetterRequirementsChecklists:
    """Test suite for letter requirements checklists."""
    
    def test_federal_checklist_exists(self):
        """Test federal requirements checklist exists and is valid."""
        checklist_path = Path(__file__).parent.parent / "letter-requirements-federal.md"
        assert checklist_path.exists()
        
        content = checklist_path.read_text()
        
        # Check required sections
        assert "## Federal Court Requirements" in content
        assert "### FRCP Rule 37 Requirements" in content
        assert "### Case Caption Requirements" in content
        assert "### Professional Tone Requirements" in content
        
        # Check for specific Rule 37 requirements
        assert "Meet and Confer Certification" in content
        assert "Specific Deficiencies" in content
        assert "Motion to Compel" in content
    
    def test_state_checklist_exists(self):
        """Test state requirements checklist exists and is valid."""
        checklist_path = Path(__file__).parent.parent / "letter-requirements-state.md"
        assert checklist_path.exists()
        
        content = checklist_path.read_text()
        
        # Check state-specific sections
        assert "## State-Specific Requirements by Jurisdiction" in content
        assert "### Response Deadline Variations" in content
        
        # Check specific states covered
        states = ["Florida", "Texas", "California", "New York"]
        for state in states:
            assert state in content
        
        # Check deadline information
        assert "10-day response period" in content  # Florida
        assert "30-day response period" in content  # Texas
    
    def test_professional_tone_checklist_exists(self):
        """Test professional tone review checklist exists."""
        checklist_path = Path(__file__).parent.parent / "professional-tone-review.md"
        assert checklist_path.exists()
        
        content = checklist_path.read_text()
        
        # Check required sections
        assert "## Professional Language Standards" in content
        assert "## Language to Avoid" in content
        assert "## Preferred Professional Alternatives" in content
        assert "## Best Practices for Professional Tone" in content
    
    def test_checklists_have_checkboxes(self):
        """Test all checklists use proper checkbox format."""
        checklist_files = [
            "letter-requirements-federal.md",
            "letter-requirements-state.md",
            "professional-tone-review.md"
        ]
        
        for filename in checklist_files:
            checklist_path = Path(__file__).parent.parent / filename
            content = checklist_path.read_text()
            
            # Check for checkbox format
            checkboxes = re.findall(r'- \[ \]', content)
            assert len(checkboxes) > 0, f"No checkboxes found in {filename}"
    
    def test_federal_checklist_completeness(self):
        """Test federal checklist covers all required elements."""
        checklist_path = Path(__file__).parent.parent / "letter-requirements-federal.md"
        content = checklist_path.read_text()
        
        required_elements = [
            "Case Caption Requirements",
            "Letter Format Requirements",
            "FRCP Rule 37 Requirements",
            "Content Requirements",
            "Professional Tone Requirements",
            "Closing Requirements",
            "Validation Steps",
            "Common Pitfalls to Avoid",
            "Best Practices"
        ]
        
        for element in required_elements:
            assert element in content, f"Missing required element: {element}"
    
    def test_state_checklist_jurisdictions(self):
        """Test state checklist includes major jurisdictions."""
        checklist_path = Path(__file__).parent.parent / "letter-requirements-state.md"
        content = checklist_path.read_text()
        
        # Major jurisdictions that should be covered
        jurisdictions = {
            "Florida": ["Fla. R. Civ. P. 1.380", "10-day"],
            "Texas": ["Tex. R. Civ. P. 215", "30-day"],
            "California": ["CCP § 2031.310", "meet and confer"],
            "New York": ["CPLR", "22 NYCRR 202.7"]
        }
        
        for state, requirements in jurisdictions.items():
            assert state in content
            for req in requirements:
                assert req in content, f"Missing {req} for {state}"
    
    def test_professional_tone_examples(self):
        """Test professional tone checklist includes examples."""
        checklist_path = Path(__file__).parent.parent / "professional-tone-review.md"
        content = checklist_path.read_text()
        
        # Should have both negative and positive examples
        assert "## Language to Avoid" in content
        assert "## Preferred Professional Alternatives" in content
        
        # Check for specific examples
        assert "❌" in content  # Negative examples marker
        assert "✅" in content  # Positive examples marker
        
        # Should have sample phrases
        assert "## Sample Professional Phrases" in content
    
    def test_checklists_actionable(self):
        """Test checklists provide actionable items."""
        checklist_files = [
            "letter-requirements-federal.md",
            "letter-requirements-state.md",
            "professional-tone-review.md"
        ]
        
        for filename in checklist_files:
            checklist_path = Path(__file__).parent.parent / filename
            content = checklist_path.read_text()
            
            # Each checklist should have validation steps
            assert "Validation" in content or "Review" in content
            
            # Should have clear action items (checkboxes)
            assert "- [ ]" in content
    
    def test_checklists_cross_reference(self):
        """Test checklists reference relevant rules and authorities."""
        # Federal checklist should reference FRCP
        federal_path = Path(__file__).parent.parent / "letter-requirements-federal.md"
        federal_content = federal_path.read_text()
        assert "FRCP Rule 37" in federal_content
        
        # State checklist should reference state rules
        state_path = Path(__file__).parent.parent / "letter-requirements-state.md"
        state_content = state_path.read_text()
        assert "Rules of Civil Procedure" in state_content