"""
Tests for LetterTemplateService.

Tests template management, rendering, and DeficiencyReport integration.
"""

import pytest
from unittest.mock import Mock, patch
from uuid import uuid4

from ..letter_template_service import LetterTemplateService
from ...ai_agents.bmad_framework.template_loader import (
    DocumentTemplate,
    TemplateSection,
)
from ...models.deficiency_models import DeficiencyReport, DeficiencyItem


class TestLetterTemplateService:
    """Test suite for LetterTemplateService."""

    @pytest.fixture
    def service(self):
        """Create service instance for testing."""
        return LetterTemplateService()

    @pytest.fixture
    def mock_template(self):
        """Create mock template for testing."""
        template = DocumentTemplate(
            type="legal_document",
            subtype="good_faith_letter",
            version="1.0",
            title="Test Template",
            description="Test template",
            jurisdiction="federal",
            raw_yaml={"metadata": {"compliance_rules": ["test_rule"]}},
        )

        template.sections = [
            TemplateSection(
                name="salutation",
                order=1,
                template="Dear {{SALUTATION}}:",
                variables=["SALUTATION"],
            ),
            TemplateSection(
                name="opening_paragraph",
                order=2,
                template="I am writing regarding {{DEFICIENCY_COUNT}} deficiencies we must meet and confer about.",
                variables=["DEFICIENCY_COUNT"],
            ),
            TemplateSection(
                name="conditional_section",
                order=3,
                template="Privilege issues: {{PRIVILEGE_ISSUES}}",
                variables=["PRIVILEGE_ISSUES"],
                condition="PRIVILEGE_ISSUES > 0",
            ),
        ]

        template.validation_rules = {
            "required_variables": ["SALUTATION", "DEFICIENCY_COUNT"]
        }

        return template

    @pytest.fixture
    def mock_deficiency_report(self):
        """Create mock deficiency report."""
        return DeficiencyReport(
            id=uuid4(),
            case_name="Test_Case_2024",
            production_id=uuid4(),
            rtp_document_id=uuid4(),
            oc_response_document_id=uuid4(),
            analysis_status="completed",
            total_requests=10,
            summary_statistics={
                "fully_produced": 3,
                "partially_produced": 2,
                "not_produced": 4,
                "no_responsive_docs": 1,
                "total_analyzed": 10,
            },
        )

    @pytest.fixture
    def mock_deficiency_items(self):
        """Create mock deficiency items."""
        return [
            DeficiencyItem(
                id=uuid4(),
                report_id=uuid4(),
                request_number="RFP No. 1",
                request_text="All contracts",
                oc_response_text="No responsive documents",
                classification="not_produced",
                confidence_score=0.9,
                evidence_chunks=[],
            ),
            DeficiencyItem(
                id=uuid4(),
                report_id=uuid4(),
                request_number="RFP No. 2",
                request_text="All emails",
                oc_response_text="See production",
                classification="partially_produced",
                confidence_score=0.8,
                evidence_chunks=[],
            ),
        ]

    @pytest.mark.asyncio
    async def test_get_template_by_jurisdiction_cached(self, service):
        """Test getting template with caching."""
        mock_template = Mock(spec=DocumentTemplate)

        with patch.object(
            service.template_loader,
            "load_template_by_jurisdiction",
            return_value=mock_template,
        ) as mock_load:
            # First call loads template
            template1 = await service.get_template_by_jurisdiction("federal")
            assert template1 == mock_template
            assert mock_load.call_count == 1

            # Second call uses cache
            template2 = await service.get_template_by_jurisdiction("federal")
            assert template2 == mock_template
            assert mock_load.call_count == 1  # Not called again

    @pytest.mark.asyncio
    async def test_get_template_by_jurisdiction_no_cache(self, service):
        """Test getting template without caching."""
        mock_template = Mock(spec=DocumentTemplate)

        with patch.object(
            service.template_loader,
            "load_template_by_jurisdiction",
            return_value=mock_template,
        ) as mock_load:
            # Call with use_cache=False
            await service.get_template_by_jurisdiction("federal", use_cache=False)
            await service.get_template_by_jurisdiction("federal", use_cache=False)

            assert mock_load.call_count == 2  # Called twice

    @pytest.mark.asyncio
    async def test_render_template_simple(self, service, mock_template):
        """Test basic template rendering."""
        variables = {
            "SALUTATION": "Counselor",
            "DEFICIENCY_COUNT": 5,
            "PRIVILEGE_ISSUES": 0,
        }

        rendered = await service.render_template(mock_template, variables)

        assert "Dear Counselor:" in rendered
        assert "5 deficiencies we must meet and confer about" in rendered
        assert "Privilege issues:" not in rendered  # Conditional section excluded

    @pytest.mark.asyncio
    async def test_render_template_with_conditional(self, service, mock_template):
        """Test template rendering with conditional section."""
        variables = {
            "SALUTATION": "Counselor",
            "DEFICIENCY_COUNT": 5,
            "PRIVILEGE_ISSUES": 3,
        }

        rendered = await service.render_template(mock_template, variables)

        assert "Dear Counselor:" in rendered
        assert "5 deficiencies we must meet and confer about" in rendered
        assert "Privilege issues: 3" in rendered  # Conditional section included

    @pytest.mark.asyncio
    async def test_render_template_missing_required(self, service, mock_template):
        """Test rendering with missing required variables."""
        variables = {
            "SALUTATION": "Counselor"
            # Missing DEFICIENCY_COUNT
        }

        with pytest.raises(ValueError) as excinfo:
            await service.render_template(mock_template, variables)

        assert "Missing required template variables" in str(excinfo.value)
        assert "DEFICIENCY_COUNT" in str(excinfo.value)

    @pytest.mark.asyncio
    async def test_render_letter_from_deficiency_report(
        self, service, mock_deficiency_report, mock_deficiency_items
    ):
        """Test rendering letter from DeficiencyReport."""
        mock_template = Mock(spec=DocumentTemplate)
        mock_template.sections = []
        mock_template.validation_rules = {"required_variables": []}

        with patch.object(
            service, "get_template_by_jurisdiction", return_value=mock_template
        ):
            with patch.object(
                service, "render_template", return_value="Rendered letter content"
            ) as mock_render:
                additional_vars = {
                    "RECIPIENT_NAME": "Opposing Counsel",
                    "ATTORNEY_NAME": "Test Attorney",
                }

                result = await service.render_letter_from_deficiency_report(
                    mock_deficiency_report,
                    mock_deficiency_items,
                    "federal",
                    additional_vars,
                )

                assert result == "Rendered letter content"

                # Check variables passed to render_template
                call_args = mock_render.call_args[0][1]
                assert (
                    call_args["DEFICIENCY_COUNT"] == 6
                )  # not_produced + partially_produced
                assert call_args["DOCUMENTS_MISSING"] == 4
                assert len(call_args["DEFICIENCY_ITEMS"]) == 2

    def test_build_variables_from_deficiency_report(
        self, service, mock_deficiency_report, mock_deficiency_items
    ):
        """Test building variables from deficiency data."""
        additional = {"ATTORNEY_NAME": "Test Attorney"}

        variables = service._build_variables_from_deficiency_report(
            mock_deficiency_report, mock_deficiency_items, additional
        )

        assert variables["ATTORNEY_NAME"] == "Test Attorney"
        assert variables["DEFICIENCY_COUNT"] == 6
        assert variables["DOCUMENTS_MISSING"] == 4
        assert "RECIPIENT_DATE" in variables
        assert len(variables["DEFICIENCY_ITEMS"]) == 2

        # Check deficiency item structure
        item = variables["DEFICIENCY_ITEMS"][0]
        assert item["REQUEST_NUMBER"] == "1"  # Should strip "RFP No. " prefix
        assert "DEFICIENCY_TYPE" in item
        assert "DEFICIENCY_DESCRIPTION" in item

    def test_get_deficiency_description(self, service):
        """Test deficiency description generation."""
        item_not_produced = Mock(
            classification="not_produced", oc_response_text="No documents"
        )
        desc = service._get_deficiency_description(item_not_produced)
        assert "Incomplete response" in desc

        item_with_objection = Mock(
            classification="not_produced",
            oc_response_text="Objection based on privilege",
        )
        desc = service._get_deficiency_description(item_with_objection)
        assert "Non-privileged objections waived" in desc

        item_partial = Mock(
            classification="partially_produced", oc_response_text="See production"
        )
        desc = service._get_deficiency_description(item_partial)
        assert "supplement with all responsive documents" in desc

    def test_get_required_action(self, service):
        """Test required action generation - not used in new format."""
        item_not_produced = Mock(classification="not_produced")
        action = service._get_required_action(item_not_produced)
        assert action == ""  # Should return empty string in new format

        item_partial = Mock(classification="partially_produced")
        action = service._get_required_action(item_partial)
        assert action == ""  # Should return empty string in new format

    def test_evaluate_condition(self, service):
        """Test condition evaluation."""
        variables = {"PRIVILEGE_ISSUES": 5, "COUNT": 10}

        assert service._evaluate_condition("PRIVILEGE_ISSUES > 0", variables) is True
        assert service._evaluate_condition("PRIVILEGE_ISSUES > 10", variables) is False
        assert service._evaluate_condition("COUNT >= 10", variables) is True
        assert service._evaluate_condition("invalid condition", variables) is False

    @pytest.mark.asyncio
    async def test_list_available_templates(self, service):
        """Test listing available templates."""
        mock_template = Mock(
            title="Test Template",
            version="1.0",
            description="Test",
            raw_yaml={"metadata": {"compliance_rules": ["rule1"]}},
        )

        with patch.object(
            service.template_loader,
            "list_jurisdictions",
            return_value=["federal", "state"],
        ):
            with patch.object(
                service, "get_template_by_jurisdiction", return_value=mock_template
            ):
                templates = await service.list_available_templates()

                assert len(templates) == 2
                assert templates[0]["jurisdiction"] == "federal"
                assert templates[0]["title"] == "Test Template"
                assert templates[0]["compliance_rules"] == ["rule1"]

    @pytest.mark.asyncio
    async def test_get_template_requirements(self, service, mock_template):
        """Test getting template requirements."""
        with patch.object(
            service, "get_template_by_jurisdiction", return_value=mock_template
        ):
            with patch.object(
                service.template_loader,
                "get_jurisdiction_requirements",
                return_value={"rule_id": "test_rule"},
            ):
                reqs = await service.get_template_requirements("federal")

                assert reqs["jurisdiction"] == "federal"
                assert reqs["template_version"] == "1.0"
                assert "SALUTATION" in reqs["required_variables"]
                assert set(reqs["all_variables"]) == {
                    "SALUTATION",
                    "DEFICIENCY_COUNT",
                    "PRIVILEGE_ISSUES",
                }
                assert len(reqs["sections"]) == 3
                assert reqs["compliance_requirements"]["rule_id"] == "test_rule"

    def test_render_repeatable_section(self, service):
        """Test rendering repeatable sections."""
        section = TemplateSection(
            name="deficiencies",
            template="Request {{REQUEST_NUMBER}}: {{REQUEST_TEXT}}",
            variables=["REQUEST_NUMBER", "REQUEST_TEXT"],
        )
        # Add repeatable attribute dynamically as the template loader does
        section.repeatable = True

        variables = {
            "DEFICIENCY_ITEMS": [
                {"REQUEST_NUMBER": "1", "REQUEST_TEXT": "Documents"},
                {"REQUEST_NUMBER": "2", "REQUEST_TEXT": "Emails"},
            ]
        }

        rendered = service._render_repeatable_section(section, variables)

        assert "Request 1: Documents" in rendered
        assert "Request 2: Emails" in rendered
        assert rendered.count("Request") == 2

    def test_clear_cache(self, service):
        """Test cache clearing."""
        service._template_cache = {"test": "value"}
        service.clear_cache()
        assert len(service._template_cache) == 0
