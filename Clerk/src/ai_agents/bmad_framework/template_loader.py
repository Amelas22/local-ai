"""
Template loader utility for BMad framework.

Handles loading and parsing of YAML templates for document generation.
"""

import yaml
import logging
from pathlib import Path
from typing import Dict, List, Optional, Any
from dataclasses import dataclass, field

from .exceptions import DependencyNotFoundError, ValidationError

logger = logging.getLogger("clerk_api")


@dataclass
class TemplateSection:
    """Represents a section in a document template."""

    name: str
    required: bool = True
    order: int = 0
    instruction: str = ""
    template: str = ""
    elicit: bool = False
    variables: List[str] = field(default_factory=list)
    subsections: List["TemplateSection"] = field(default_factory=list)
    formatting: Dict[str, Any] = field(default_factory=dict)
    condition: Optional[str] = None


@dataclass
class DocumentTemplate:
    """Parsed document template."""

    # Metadata
    type: str
    subtype: str
    version: str
    title: str
    description: str
    jurisdiction: str = "general"
    author: str = ""

    # Document settings
    settings: Dict[str, Any] = field(default_factory=dict)

    # Sections
    sections: List[TemplateSection] = field(default_factory=list)

    # Validation rules
    validation_rules: List[Dict[str, str]] = field(default_factory=list)

    # Conditional sections
    conditional_sections: List[Dict[str, Any]] = field(default_factory=list)

    # Output options
    output_options: Dict[str, Any] = field(default_factory=dict)

    # Raw YAML
    raw_yaml: Dict[str, Any] = field(default_factory=dict)


class TemplateLoader:
    """Loads and parses document templates."""

    def __init__(self, base_path: Optional[Path] = None):
        """
        Initialize template loader.

        Args:
            base_path: Base path for templates. Defaults to bmad-framework/templates.
        """
        if base_path is None:
            base_path = Path(__file__).parent / "templates"
        self.base_path = Path(base_path)
        self._template_cache: Dict[str, DocumentTemplate] = {}

    def load_template(self, template_name: str) -> DocumentTemplate:
        """
        Load a template by name.

        Args:
            template_name: Template filename (with or without .yaml extension).

        Returns:
            Parsed document template.

        Raises:
            DependencyNotFoundError: If template not found.
            ValidationError: If template is invalid.
        """
        # Check cache
        if template_name in self._template_cache:
            return self._template_cache[template_name]

        # Find template file
        template_path = self._find_template_file(template_name)
        if not template_path:
            raise DependencyNotFoundError(
                "template", template_name, f"Template not found in {self.base_path}"
            )

        try:
            # Load YAML
            with open(template_path, "r", encoding="utf-8") as f:
                data = yaml.safe_load(f)

            # Parse template
            template = self._parse_template(data)

            # Validate
            self._validate_template(template)

            # Cache
            self._template_cache[template_name] = template

            logger.info(f"Loaded template: {template_name}")
            return template

        except Exception as e:
            if isinstance(e, (DependencyNotFoundError, ValidationError)):
                raise
            raise ValidationError(
                "Template parsing",
                f"Failed to parse template: {str(e)}",
                {"template": template_name, "error": str(e)},
            )

    def _find_template_file(self, template_name: str) -> Optional[Path]:
        """Find template file."""
        # Remove extension if provided
        if template_name.endswith(".yaml") or template_name.endswith(".yml"):
            base_name = template_name.rsplit(".", 1)[0]
        else:
            base_name = template_name

        # Try different extensions
        for ext in [".yaml", ".yml"]:
            path = self.base_path / f"{base_name}{ext}"
            if path.exists():
                return path

        # Try .bmad-core templates
        bmad_core_path = Path(".bmad-core/templates")
        if bmad_core_path.exists():
            for ext in [".yaml", ".yml"]:
                path = bmad_core_path / f"{base_name}{ext}"
                if path.exists():
                    return path

        return None

    def _parse_template(self, data: Dict[str, Any]) -> DocumentTemplate:
        """Parse template from YAML data."""
        # Extract metadata first
        meta = data.get("metadata", {})
        
        # Create template with required fields
        template = DocumentTemplate(
            type=meta.get("type", "document"),
            subtype=meta.get("subtype", "general"),
            version=meta.get("version", "1.0"),
            title=meta.get("title", "Untitled"),
            description=meta.get("description", ""),
            jurisdiction=meta.get("jurisdiction", "general"),
            author=meta.get("author", ""),
            raw_yaml=data
        )

        # Parse document settings
        if "document_settings" in data:
            template.settings = data["document_settings"]

        # Parse sections
        if "sections" in data:
            template.sections = self._parse_sections(data["sections"])

        # Parse validation rules
        if "validation_rules" in data:
            template.validation_rules = data["validation_rules"]

        # Parse conditional sections
        if "conditional_sections" in data:
            template.conditional_sections = data["conditional_sections"]

        # Parse output options
        if "output_options" in data:
            template.output_options = data["output_options"]

        return template

    def _parse_sections(
        self, sections_data: List[Dict[str, Any]]
    ) -> List[TemplateSection]:
        """Parse template sections."""
        sections = []

        for idx, section_data in enumerate(sections_data):
            section = TemplateSection(
                name=section_data.get("name", f"section_{idx}"),
                required=section_data.get("required", True),
                order=section_data.get("order", idx),
                instruction=section_data.get("instruction", ""),
                template=section_data.get("template", ""),
                elicit=section_data.get("elicit", False),
                variables=section_data.get("variables", []),
                formatting=section_data.get("formatting", {}),
                condition=section_data.get("condition"),
            )

            # Parse subsections
            if "subsections" in section_data:
                section.subsections = self._parse_sections(section_data["subsections"])

            sections.append(section)

        return sections

    def _validate_template(self, template: DocumentTemplate) -> None:
        """Validate template structure."""
        errors = []

        # Required metadata
        if not template.type:
            errors.append("Missing required metadata: type")
        if not template.title:
            errors.append("Missing required metadata: title")

        # At least one section required
        if not template.sections:
            errors.append("Template must have at least one section")

        # Check for duplicate section names
        section_names = [s.name for s in template.sections]
        if len(section_names) != len(set(section_names)):
            errors.append("Duplicate section names found")

        # Validate conditional sections
        for cond_section in template.conditional_sections:
            if "condition" not in cond_section:
                errors.append("Conditional section missing 'condition' field")

        if errors:
            raise ValidationError(
                "Template validation",
                f"Template validation failed: {'; '.join(errors)}",
                {"errors": errors, "template": template.title},
            )

    def list_templates(self) -> List[str]:
        """List available templates."""
        templates = []

        # Check base path
        if self.base_path.exists():
            for ext in [".yaml", ".yml"]:
                templates.extend([f.stem for f in self.base_path.glob(f"*{ext}")])

        # Check .bmad-core
        bmad_core_path = Path(".bmad-core/templates")
        if bmad_core_path.exists():
            for ext in [".yaml", ".yml"]:
                templates.extend([f.stem for f in bmad_core_path.glob(f"*{ext}")])

        return sorted(list(set(templates)))

    def get_template_info(self, template_name: str) -> Dict[str, Any]:
        """Get basic info about a template without full parsing."""
        template = self.load_template(template_name)

        return {
            "name": template_name,
            "type": template.type,
            "subtype": template.subtype,
            "title": template.title,
            "description": template.description,
            "jurisdiction": template.jurisdiction,
            "sections": [s.name for s in template.sections],
            "required_sections": [s.name for s in template.sections if s.required],
            "elicit_sections": [s.name for s in template.sections if s.elicit],
        }
