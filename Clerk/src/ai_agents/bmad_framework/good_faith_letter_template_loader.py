"""
Good Faith Letter Template Loader for BMad framework.

Specialized loader for Good Faith letter templates with jurisdiction support
and compliance validation.
"""

import logging
from pathlib import Path
from typing import Dict, List, Optional, Any
from dataclasses import dataclass

from .template_loader import TemplateLoader, DocumentTemplate, TemplateSection
from .exceptions import ValidationError

logger = logging.getLogger("clerk_api")


@dataclass
class ComplianceRule:
    """Represents a compliance rule for a jurisdiction."""

    rule_id: str
    description: str
    required_sections: List[str]
    required_phrases: List[str]
    deadline_days: Optional[int] = None


class GoodFaithLetterTemplateLoader(TemplateLoader):
    """Specialized loader for Good Faith letter templates with jurisdiction support."""

    def __init__(self):
        """Initialize with good-faith-letters subdirectory."""
        super().__init__(Path(__file__).parent / "templates" / "good-faith-letters")

        # Jurisdiction to template mapping
        self.jurisdiction_map = {
            "federal": "good-faith-letter-federal.yaml",
            "state": "good-faith-letter-state.yaml",
        }

        # Compliance rules by jurisdiction (simplified - no legal citations)
        self.compliance_rules = {
            "federal": ComplianceRule(
                rule_id="federal_discovery",
                description="Federal court discovery deficiency letter",
                required_sections=[
                    "header",
                    "opening_paragraph",
                    "rtp_deficiencies",
                    "closing_paragraph",
                    "signature_block",
                ],
                required_phrases=["meet and confer"],
                deadline_days=None,  # Varies by court
            ),
            "state": ComplianceRule(
                rule_id="state_discovery",
                description="State court discovery deficiency letter",
                required_sections=[
                    "header",
                    "opening_paragraph",
                    "rtp_deficiencies",
                    "closing_paragraph",
                    "signature_block",
                ],
                required_phrases=["meet and confer"],
                deadline_days=None,  # Varies by state
            ),
        }

    async def load_template_by_jurisdiction(
        self, jurisdiction: str
    ) -> DocumentTemplate:
        """
        Load template for specific jurisdiction.

        Args:
            jurisdiction: Jurisdiction name (federal, california, florida, texas).

        Returns:
            DocumentTemplate: Loaded and validated template.

        Raises:
            ValidationError: If jurisdiction not supported or template invalid.
        """
        jurisdiction_lower = jurisdiction.lower()
        template_file = self.jurisdiction_map.get(jurisdiction_lower)

        if not template_file:
            raise ValidationError(
                "Jurisdiction validation",
                f"No template found for jurisdiction: {jurisdiction}",
                {
                    "jurisdiction": jurisdiction,
                    "available": list(self.jurisdiction_map.keys()),
                },
            )

        # Load template
        template = self.load_template(template_file)

        # Validate compliance
        compliance_errors = self.validate_template_compliance(template)
        if compliance_errors:
            raise ValidationError(
                "Compliance validation",
                f"Template compliance errors: {'; '.join(compliance_errors)}",
                {"errors": compliance_errors, "jurisdiction": jurisdiction},
            )

        logger.info(f"Loaded compliant template for jurisdiction: {jurisdiction}")
        return template

    def validate_template_compliance(self, template: DocumentTemplate) -> List[str]:
        """
        Validate template meets legal requirements.

        Args:
            template: Template to validate.

        Returns:
            List of validation errors (empty if valid).
        """
        errors = []

        # Get jurisdiction from template
        jurisdiction = template.jurisdiction.lower()
        if jurisdiction not in self.compliance_rules:
            errors.append(f"Unknown jurisdiction: {jurisdiction}")
            return errors

        rule = self.compliance_rules[jurisdiction]

        # Check required sections
        template_sections = [s.name for s in template.sections]
        for req_section in rule.required_sections:
            if req_section not in template_sections:
                errors.append(f"Missing required section: {req_section}")

        # Check required phrases in template content
        template_content = self._get_template_content(template)
        for phrase in rule.required_phrases:
            if phrase.lower() not in template_content.lower():
                errors.append(f"Missing required phrase: '{phrase}'")

        # Validate variable naming convention
        for section in template.sections:
            for var in section.variables:
                if not self._is_valid_variable_name(var):
                    errors.append(
                        f"Invalid variable name '{var}' in section '{section.name}'. "
                        "Variables must be UPPERCASE_WITH_UNDERSCORES"
                    )

        # Check for template syntax in content
        if "{{" in template_content and "}}" in template_content:
            # Validate all {{VARIABLES}} use defined variables
            import re

            used_vars = re.findall(r"\{\{(\w+)\}\}", template_content)
            defined_vars = self._get_all_variables(template)

            for used_var in used_vars:
                if used_var not in defined_vars:
                    errors.append("Undefined variable used in template: {{var}}")

        # Check version exists
        if not template.version:
            errors.append("Template must include version for compliance tracking")

        # Validate metadata compliance rules section
        if "compliance_rules" not in template.raw_yaml.get("metadata", {}):
            errors.append("Template metadata must include compliance_rules section")

        return errors

    def _get_template_content(self, template: DocumentTemplate) -> str:
        """Extract all template content for validation."""
        content_parts = []
        for section in template.sections:
            if section.template:
                content_parts.append(section.template)
            # Recursively get subsection content
            content_parts.extend(self._get_subsection_content(section.subsections))
        return " ".join(content_parts)

    def _get_subsection_content(self, subsections: List[TemplateSection]) -> List[str]:
        """Recursively extract subsection content."""
        content_parts = []
        for subsection in subsections:
            if subsection.template:
                content_parts.append(subsection.template)
            content_parts.extend(self._get_subsection_content(subsection.subsections))
        return content_parts

    def _get_all_variables(self, template: DocumentTemplate) -> set:
        """Get all defined variables from template."""
        variables = set()
        for section in template.sections:
            variables.update(section.variables)
            variables.update(self._get_subsection_variables(section.subsections))
        return variables

    def _get_subsection_variables(self, subsections: List[TemplateSection]) -> set:
        """Recursively get subsection variables."""
        variables = set()
        for subsection in subsections:
            variables.update(subsection.variables)
            variables.update(self._get_subsection_variables(subsection.subsections))
        return variables

    def _is_valid_variable_name(self, var_name: str) -> bool:
        """Check if variable name follows UPPERCASE_UNDERSCORE pattern."""
        import re

        return bool(re.match(r"^[A-Z][A-Z0-9_]*$", var_name))

    def get_jurisdiction_requirements(self, jurisdiction: str) -> Dict[str, Any]:
        """
        Get compliance requirements for a jurisdiction.

        Args:
            jurisdiction: Jurisdiction name.

        Returns:
            Dictionary with compliance requirements.
        """
        jurisdiction_lower = jurisdiction.lower()
        if jurisdiction_lower not in self.compliance_rules:
            raise ValidationError(
                "Jurisdiction lookup",
                f"Unknown jurisdiction: {jurisdiction}",
                {
                    "jurisdiction": jurisdiction,
                    "available": list(self.compliance_rules.keys()),
                },
            )

        rule = self.compliance_rules[jurisdiction_lower]
        return {
            "jurisdiction": jurisdiction,
            "rule_id": rule.rule_id,
            "description": rule.description,
            "required_sections": rule.required_sections,
            "required_phrases": rule.required_phrases,
            "deadline_days": rule.deadline_days,
        }

    def list_jurisdictions(self) -> List[str]:
        """Get list of supported jurisdictions."""
        return sorted(list(self.jurisdiction_map.keys()))
