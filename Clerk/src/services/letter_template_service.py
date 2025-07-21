"""
Letter Template Service for managing Good Faith letter templates.

Handles template CRUD operations, jurisdiction-based selection,
rendering with variable substitution, and caching.
"""

from datetime import datetime
from typing import Dict, List, Any

from src.ai_agents.bmad_framework.good_faith_letter_template_loader import (
    GoodFaithLetterTemplateLoader,
)
from src.ai_agents.bmad_framework.template_loader import (
    DocumentTemplate,
    TemplateSection,
)
from src.models.deficiency_models import DeficiencyReport, DeficiencyItem
from src.utils.logger import get_logger

logger = get_logger("clerk_api")


class LetterTemplateService:
    """
    Service for managing Good Faith letter templates.

    Provides template selection, rendering, and management operations
    with jurisdiction-specific support and DeficiencyReport integration.
    """

    def __init__(self):
        """Initialize LetterTemplateService with template loader."""
        self.template_loader = GoodFaithLetterTemplateLoader()
        self._template_cache: Dict[str, DocumentTemplate] = {}
        logger.info("Initialized LetterTemplateService")

    async def get_template_by_jurisdiction(
        self, jurisdiction: str, use_cache: bool = True
    ) -> DocumentTemplate:
        """
        Get template for specific jurisdiction.

        Args:
            jurisdiction: Jurisdiction name (federal, california, florida, texas).
            use_cache: Whether to use cached template if available.

        Returns:
            DocumentTemplate: Loaded template for jurisdiction.

        Raises:
            ValidationError: If jurisdiction not supported.
        """
        cache_key = f"jurisdiction_{jurisdiction.lower()}"

        if use_cache and cache_key in self._template_cache:
            logger.debug(f"Using cached template for jurisdiction: {jurisdiction}")
            return self._template_cache[cache_key]

        template = await self.template_loader.load_template_by_jurisdiction(
            jurisdiction
        )

        if use_cache:
            self._template_cache[cache_key] = template

        logger.info(f"Loaded template for jurisdiction: {jurisdiction}")
        return template

    async def render_letter_from_deficiency_report(
        self,
        deficiency_report: DeficiencyReport,
        deficiency_items: List[DeficiencyItem],
        jurisdiction: str,
        additional_variables: Dict[str, Any],
    ) -> str:
        """
        Render Good Faith letter using DeficiencyReport data.

        Args:
            deficiency_report: The deficiency analysis report.
            deficiency_items: List of deficiency items to include.
            jurisdiction: Jurisdiction for template selection.
            additional_variables: Additional template variables.

        Returns:
            Rendered letter content.
        """
        # Load template
        template = await self.get_template_by_jurisdiction(jurisdiction)

        # Build variable mapping from deficiency data
        variables = self._build_variables_from_deficiency_report(
            deficiency_report, deficiency_items, additional_variables
        )

        # Render template
        rendered_content = await self.render_template(template, variables)

        logger.info(
            f"Rendered Good Faith letter for case {deficiency_report.case_name} "
            f"with {len(deficiency_items)} deficiency items"
        )

        return rendered_content

    async def render_template(
        self, template: DocumentTemplate, variables: Dict[str, Any]
    ) -> str:
        """
        Render template with variable substitution.

        Args:
            template: Template to render.
            variables: Variable values for substitution.

        Returns:
            Rendered template content.

        Raises:
            ValueError: If required variables are missing.
        """
        # Validate required variables
        self._validate_required_variables(template, variables)

        # Render sections
        rendered_sections = []
        for section in sorted(template.sections, key=lambda s: s.order):
            # Check conditional sections
            if section.condition and not self._evaluate_condition(
                section.condition, variables
            ):
                continue

            # Handle repeatable sections
            if hasattr(section, "repeatable") and section.repeatable:
                rendered_section = self._render_repeatable_section(section, variables)
            else:
                rendered_section = self._render_section(section, variables)

            if rendered_section:
                rendered_sections.append(rendered_section)

        return "\n\n".join(rendered_sections)

    def _render_section(
        self, section: TemplateSection, variables: Dict[str, Any]
    ) -> str:
        """Render a single template section."""
        if not section.template:
            return ""

        content = section.template

        # Replace variables using {{VARIABLE}} syntax
        for var_name in section.variables:
            if var_name in variables:
                placeholder = f"{{{{{var_name}}}}}"
                value = str(variables[var_name])
                content = content.replace(placeholder, value)

        return content.strip()

    def _render_repeatable_section(
        self, section: TemplateSection, variables: Dict[str, Any]
    ) -> str:
        """Render a repeatable section (like detailed_deficiencies)."""
        # Look for deficiency items in variables
        deficiency_items = variables.get("DEFICIENCY_ITEMS", [])
        if not deficiency_items:
            return ""

        rendered_items = []
        for item in deficiency_items:
            item_content = section.template

            # Replace variables for this item
            for var_name in section.variables:
                placeholder = f"{{{{{var_name}}}}}"
                if var_name in item:
                    value = str(item[var_name])
                    item_content = item_content.replace(placeholder, value)

            rendered_items.append(item_content.strip())

        return "\n\n".join(rendered_items)

    def _build_variables_from_deficiency_report(
        self,
        report: DeficiencyReport,
        items: List[DeficiencyItem],
        additional: Dict[str, Any],
    ) -> Dict[str, Any]:
        """Build template variables from DeficiencyReport data."""
        # Start with additional variables
        variables = additional.copy()

        # Add report-level statistics
        stats = report.summary_statistics
        variables.update(
            {
                "DEFICIENCY_COUNT": stats.get("not_produced", 0)
                + stats.get("partially_produced", 0),
                "DOCUMENTS_MISSING": stats.get("not_produced", 0),
                "PRIVILEGE_ISSUES": 0,  # To be determined from items
                "PRODUCTION_DATE": report.created_at.strftime("%B %d, %Y"),
            }
        )

        # Build deficiency items for repeatable sections
        deficiency_items = []
        for item in items:
            if item.classification in [
                "not_produced",
                "partially_produced",
                "no_responsive_docs",
            ]:
                # Extract just the number from "RFP No. 12" format
                request_number = item.request_number.replace("RFP No. ", "").replace(
                    "Request No. ", ""
                )

                # Determine deficiency type based on classification
                if "objection" in item.oc_response_text.lower():
                    deficiency_type = "Non-privileged objections waived"
                else:
                    deficiency_type = "Incomplete response"

                deficiency_items.append(
                    {
                        "REQUEST_NUMBER": request_number,
                        "DEFICIENCY_TYPE": deficiency_type,
                        "DEFICIENCY_DESCRIPTION": self._get_deficiency_description(
                            item
                        ),
                    }
                )

        variables["DEFICIENCY_ITEMS"] = deficiency_items

        # Add today's date if not provided
        if "RECIPIENT_DATE" not in variables:
            variables["RECIPIENT_DATE"] = datetime.now().strftime("%B %d, %Y")

        return variables

    def _get_deficiency_description(self, item: DeficiencyItem) -> str:
        """Generate deficiency description based on classification."""
        # Map AI classifications to letter-style deficiency types
        if item.classification == "not_produced":
            if "objection" in item.oc_response_text.lower():
                return "Non-privileged objections waived. Please withdraw and provide a complete response"
            else:
                return "Incomplete response. Please provide complete response to this request"
        elif item.classification == "partially_produced":
            return (
                "Incomplete response. Please supplement with all responsive documents"
            )
        elif item.classification == "no_responsive_docs":
            return "Plaintiff disagrees with this response and would like to discuss further in an attempt to resolve without court intervention"
        return "Please provide a complete response"

    def _get_required_action(self, item: DeficiencyItem) -> str:
        """Generate required action based on classification - not used in new format."""
        # In the new format, the action is incorporated into the description
        return ""

    def _validate_required_variables(
        self, template: DocumentTemplate, variables: Dict[str, Any]
    ) -> None:
        """Validate all required variables are provided."""
        # Get required variables from validation rules
        required_vars = []
        if "required_variables" in template.validation_rules:
            required_vars = template.validation_rules["required_variables"]

        missing_vars = []
        for var in required_vars:
            if var not in variables:
                missing_vars.append(var)

        if missing_vars:
            raise ValueError(
                f"Missing required template variables: {', '.join(missing_vars)}"
            )

    def _evaluate_condition(self, condition: str, variables: Dict[str, Any]) -> bool:
        """Evaluate a template condition."""
        # Simple evaluation for conditions like "PRIVILEGE_ISSUES > 0"
        try:
            # Replace variable names with values
            eval_condition = condition
            for var_name, value in variables.items():
                if var_name in eval_condition:
                    eval_condition = eval_condition.replace(var_name, str(value))

            # Safe evaluation - only allow comparisons
            if any(op in eval_condition for op in [">", "<", ">=", "<=", "==", "!="]):
                return eval(eval_condition)

            return False
        except Exception as e:
            logger.warning(f"Failed to evaluate condition '{condition}': {e}")
            return False

    async def list_available_templates(self) -> List[Dict[str, Any]]:
        """
        List all available templates with metadata.

        Returns:
            List of template information dictionaries.
        """
        templates = []

        for jurisdiction in self.template_loader.list_jurisdictions():
            try:
                template = await self.get_template_by_jurisdiction(jurisdiction)
                templates.append(
                    {
                        "jurisdiction": jurisdiction,
                        "title": template.title,
                        "version": template.version,
                        "description": template.description,
                        "compliance_rules": template.raw_yaml.get("metadata", {}).get(
                            "compliance_rules", []
                        ),
                    }
                )
            except Exception as e:
                logger.error(f"Failed to load template for {jurisdiction}: {e}")

        return templates

    async def get_template_requirements(self, jurisdiction: str) -> Dict[str, Any]:
        """
        Get requirements and variables for a jurisdiction's template.

        Args:
            jurisdiction: Jurisdiction name.

        Returns:
            Dictionary with template requirements.
        """
        template = await self.get_template_by_jurisdiction(jurisdiction)

        # Collect all variables from all sections
        all_variables = set()
        for section in template.sections:
            all_variables.update(section.variables)

        # Get compliance requirements
        compliance_reqs = self.template_loader.get_jurisdiction_requirements(
            jurisdiction
        )

        return {
            "jurisdiction": jurisdiction,
            "template_version": template.version,
            "required_variables": template.validation_rules.get(
                "required_variables", []
            ),
            "all_variables": sorted(list(all_variables)),
            "sections": [
                {"name": s.name, "required": s.required} for s in template.sections
            ],
            "compliance_requirements": compliance_reqs,
        }

    def clear_cache(self) -> None:
        """Clear template cache."""
        self._template_cache.clear()
        logger.info("Cleared template cache")
