"""
Tests for GoodFaithLetterTemplateLoader.

Tests template loading, validation, and compliance checking for
Good Faith letter templates.
"""

import pytest
from unittest.mock import patch

from ..good_faith_letter_template_loader import (
    GoodFaithLetterTemplateLoader,
    ComplianceRule,
)
from ..template_loader import DocumentTemplate, TemplateSection
from ..exceptions import ValidationError


class TestGoodFaithLetterTemplateLoader:
    """Test suite for GoodFaithLetterTemplateLoader."""

    @pytest.fixture
    def loader(self):
        """Create loader instance for testing."""
        return GoodFaithLetterTemplateLoader()

    @pytest.fixture
    def mock_template(self):
        """Create mock template for testing."""
        template = DocumentTemplate(
            type="legal_document",
            subtype="good_faith_letter",
            version="1.0",
            title="Good Faith Letter - Federal",
            description="Federal good faith letter template",
            jurisdiction="federal",
            raw_yaml={"metadata": {"compliance_rules": ["frcp_rule_37"]}},
        )

        # Add required sections
        template.sections = [
            TemplateSection(
                name="header",
                template="Reply to: {{SENDER_EMAIL}}",
                variables=["SENDER_EMAIL"],
            ),
            TemplateSection(
                name="opening_paragraph",
                template="I am writing to follow up on your client's deficiencies. We must meet and confer.",
                variables=["CLIENT_REFERENCE", "REQUESTING_PARTY"],
            ),
            TemplateSection(
                name="rtp_deficiencies",
                template="{{PARTY_NAME}}'s Response to {{REQUESTING_PARTY}}'s {{RTP_SET}}",
                variables=["PARTY_NAME", "REQUESTING_PARTY", "RTP_SET"],
            ),
            TemplateSection(
                name="closing_paragraph",
                template="Please review all of the above at your earliest convenience.",
                variables=[],
            ),
            TemplateSection(
                name="signature_block",
                template="Sincerely, {{ATTORNEY_NAME}}",
                variables=["ATTORNEY_NAME"],
            ),
        ]

        return template

    def test_init(self, loader):
        """Test loader initialization."""
        assert loader.jurisdiction_map["federal"] == "good-faith-letter-federal.yaml"
        assert loader.jurisdiction_map["state"] == "good-faith-letter-state.yaml"
        assert len(loader.compliance_rules) == 2

    def test_list_jurisdictions(self, loader):
        """Test listing supported jurisdictions."""
        jurisdictions = loader.list_jurisdictions()
        assert jurisdictions == ["federal", "state"]

    @pytest.mark.asyncio
    async def test_load_template_by_jurisdiction_invalid(self, loader):
        """Test loading template with invalid jurisdiction."""
        with pytest.raises(ValidationError) as excinfo:
            await loader.load_template_by_jurisdiction("invalid")

        assert "No template found for jurisdiction" in str(excinfo.value)
        assert excinfo.value.details["jurisdiction"] == "invalid"

    @pytest.mark.asyncio
    @patch.object(GoodFaithLetterTemplateLoader, "load_template")
    async def test_load_template_by_jurisdiction_success(
        self, mock_load, loader, mock_template
    ):
        """Test successful template loading by jurisdiction."""
        mock_load.return_value = mock_template

        template = await loader.load_template_by_jurisdiction("federal")

        assert template.jurisdiction == "federal"
        mock_load.assert_called_once_with("good-faith-letter-federal.yaml")

    def test_validate_template_compliance_success(self, loader, mock_template):
        """Test successful compliance validation."""
        errors = loader.validate_template_compliance(mock_template)
        assert errors == []

    def test_validate_template_compliance_missing_section(self, loader, mock_template):
        """Test compliance validation with missing section."""
        # Remove a required section
        mock_template.sections = mock_template.sections[:-1]  # Remove signature_block

        errors = loader.validate_template_compliance(mock_template)
        assert "Missing required section: signature_block" in errors

    def test_validate_template_compliance_missing_phrase(self, loader, mock_template):
        """Test compliance validation with missing required phrase."""
        # Modify template to remove required phrase
        mock_template.sections[1].template = "This letter addresses deficiencies."

        errors = loader.validate_template_compliance(mock_template)
        assert any("meet and confer" in error for error in errors)

    def test_validate_template_compliance_invalid_variable_name(
        self, loader, mock_template
    ):
        """Test compliance validation with invalid variable names."""
        # Add invalid variable name
        mock_template.sections[0].variables.append("invalid-var")

        errors = loader.validate_template_compliance(mock_template)
        assert any("Invalid variable name" in error for error in errors)

    def test_validate_template_compliance_state(self, loader):
        """Test state template compliance validation."""
        template = DocumentTemplate(
            type="legal_document",
            subtype="good_faith_letter",
            version="1.0",
            title="Good Faith Letter - State",
            description="State good faith letter template",
            jurisdiction="state",
            raw_yaml={"metadata": {"compliance_rules": ["state_discovery"]}},
        )

        # Add sections without required meet and confer phrase
        template.sections = [
            TemplateSection(name="header", template="Reply to: email"),
            TemplateSection(
                name="opening_paragraph", template="Following up on deficiencies"
            ),
            TemplateSection(name="rtp_deficiencies", template="Deficiencies noted"),
            TemplateSection(name="closing_paragraph", template="Please respond"),
            TemplateSection(name="signature_block", template="Signed"),
        ]

        errors = loader.validate_template_compliance(template)
        # Should have error for missing "meet and confer" phrase
        assert any("meet and confer" in error for error in errors)

    def test_get_jurisdiction_requirements(self, loader):
        """Test getting jurisdiction requirements."""
        reqs = loader.get_jurisdiction_requirements("federal")

        assert reqs["jurisdiction"] == "federal"
        assert reqs["rule_id"] == "federal_discovery"
        assert reqs["deadline_days"] is None  # Varies by court
        assert "header" in reqs["required_sections"]
        assert "meet and confer" in reqs["required_phrases"]

    def test_get_jurisdiction_requirements_invalid(self, loader):
        """Test getting requirements for invalid jurisdiction."""
        with pytest.raises(ValidationError) as excinfo:
            loader.get_jurisdiction_requirements("invalid")

        assert "Unknown jurisdiction" in str(excinfo.value)

    def test_get_template_content(self, loader, mock_template):
        """Test extracting template content."""
        content = loader._get_template_content(mock_template)

        assert "Reply to:" in content
        assert "deficiencies" in content
        assert "Sincerely" in content

    def test_get_all_variables(self, loader, mock_template):
        """Test getting all defined variables."""
        variables = loader._get_all_variables(mock_template)

        expected = {
            "SENDER_EMAIL",
            "CLIENT_REFERENCE",
            "REQUESTING_PARTY",
            "PARTY_NAME",
            "RTP_SET",
            "ATTORNEY_NAME",
        }
        assert variables == expected

    def test_is_valid_variable_name(self, loader):
        """Test variable name validation."""
        assert loader._is_valid_variable_name("COURT_NAME")
        assert loader._is_valid_variable_name("CASE_NUMBER_123")
        assert loader._is_valid_variable_name("A")

        assert not loader._is_valid_variable_name("court_name")
        assert not loader._is_valid_variable_name("Court_Name")
        assert not loader._is_valid_variable_name("COURT-NAME")
        assert not loader._is_valid_variable_name("123_COURT")
        assert not loader._is_valid_variable_name("")

    def test_compliance_rules_structure(self, loader):
        """Test compliance rules have correct structure."""
        for jurisdiction, rule in loader.compliance_rules.items():
            assert isinstance(rule, ComplianceRule)
            assert rule.rule_id
            assert rule.description
            assert isinstance(rule.required_sections, list)
            assert isinstance(rule.required_phrases, list)
            assert len(rule.required_sections) == 5  # All need 5 core sections

    def test_template_with_subsections(self, loader):
        """Test validation with nested subsections."""
        template = DocumentTemplate(
            type="legal_document",
            subtype="good_faith_letter",
            version="1.0",
            title="Test Template",
            description="Test",
            jurisdiction="federal",
            raw_yaml={"metadata": {"compliance_rules": ["test"]}},
        )

        # Add section with subsections
        main_section = TemplateSection(
            name="main", template="Main content", variables=["MAIN_VAR"]
        )
        main_section.subsections = [
            TemplateSection(
                name="sub1", template="Sub content {{SUB_VAR}}", variables=["SUB_VAR"]
            )
        ]
        template.sections = [main_section]

        # Test variable extraction includes subsection variables
        variables = loader._get_all_variables(template)
        assert "MAIN_VAR" in variables
        assert "SUB_VAR" in variables
