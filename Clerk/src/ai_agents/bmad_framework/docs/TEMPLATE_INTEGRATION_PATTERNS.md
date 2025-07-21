# Template Integration Patterns

## Overview

This document describes the template integration patterns between the existing motion drafting system and the new BMad Framework template system, with Good Faith Letters as the first production implementation.

## Current State: Motion Drafter

The motion drafter (`motion_drafter.py`) currently uses inline template generation:

### Motion Drafter Characteristics
- **Inline Templates**: Templates are hardcoded in the Python code
- **Dynamic Generation**: Content is generated through AI prompts with specific formatting instructions
- **Section-Based Structure**: Documents are built section by section (caption, introduction, arguments, conclusion, etc.)
- **Format Instructions**: Formatting rules are embedded in prompt strings

### Example from Motion Drafter
```python
def _create_introduction_prompt(self, outline_section, essential_content, cumulative_context):
    return f"""Draft the INTRODUCTION section...
    
    Example format:
    "Plaintiff, [NAME], as Personal Representative of the Estate of [NAME], 
    by and through undersigned counsel, files this [Motion Type]..."
    """
```

## New Pattern: BMad Template System

The Good Faith Letter implementation demonstrates the BMad Framework template pattern:

### BMad Template Characteristics
- **YAML-Based Templates**: Templates are external YAML files
- **Variable Substitution**: Uses {{VARIABLE_NAME}} syntax for dynamic content
- **Compliance-Driven**: Templates include compliance rules and validation
- **Jurisdiction-Specific**: Different templates for different jurisdictions
- **Version Control**: Templates are versioned for compliance tracking

### Example from Good Faith Letter Template
```yaml
sections:
  - name: caption
    required: true
    template: |
      {{COURT_NAME}}
      {{JURISDICTION}}
      
      {{PLAINTIFF_NAME}},
                        Plaintiff,
      v.                            Case No. {{CASE_NUMBER}}
      {{DEFENDANT_NAME}},
                        Defendant.
    variables:
      - COURT_NAME
      - JURISDICTION
      - PLAINTIFF_NAME
      - DEFENDANT_NAME
      - CASE_NUMBER
```

## Integration Patterns

### 1. Template Loading Pattern

**Motion Drafter (Current)**:
```python
# Templates are hardcoded in methods
caption_content = legal_formatter.format_case_caption(
    case_name=self.document_context.get("case_name"),
    case_number="2024-XXXXX-CA-01",
    plaintiff_name="Plaintiff Name",
    defendant_names=["Defendant Name"]
)
```

**BMad Framework (New)**:
```python
# Templates are loaded from files
template_loader = GoodFaithLetterTemplateLoader()
template = await template_loader.load_template_by_jurisdiction("federal")
```

### 2. Variable Management Pattern

**Motion Drafter (Current)**:
- Variables are passed as function arguments
- No centralized variable definition
- No validation of required variables

**BMad Framework (New)**:
- Variables are defined in template YAML
- Centralized variable management
- Automatic validation of required variables
- Type safety through variable definitions

### 3. Content Generation Pattern

**Motion Drafter (Current)**:
```python
# AI generates content based on prompts
result = await self.section_writer.run(drafting_prompt)
```

**BMad Framework (New)**:
```python
# Template rendering with variable substitution
rendered_content = await service.render_template(template, variables)
```

### 4. Section Management Pattern

**Motion Drafter (Current)**:
- Sections defined as Python enums
- Section order hardcoded in restructuring logic
- Dynamic section generation based on AI

**BMad Framework (New)**:
- Sections defined in YAML with order field
- Conditional sections based on template rules
- Repeatable sections for lists (e.g., deficiency items)

## Migration Path for Motion Templates

To migrate motion templates to the BMad system:

### Phase 1: Template Extraction
1. Extract hardcoded templates from motion_drafter.py
2. Convert to YAML format
3. Identify common variables across motion types

### Phase 2: Create Motion Template Structure
```yaml
metadata:
  type: legal_document
  subtype: motion
  motion_type: summary_judgment  # or dismissal, etc.
  jurisdiction: federal
  
sections:
  - name: caption
    # Similar structure to Good Faith letters
  - name: introduction
    template: |
      {{PLAINTIFF_NAME}}, as Personal Representative of the Estate of 
      {{DECEDENT_NAME}}, by and through undersigned counsel, files this 
      {{MOTION_TYPE}} and respectfully shows...
```

### Phase 3: Integration Points
1. Create `MotionTemplateLoader` extending `TemplateLoader`
2. Add motion-specific validation rules
3. Integrate with existing motion outline system

### Phase 4: Hybrid Approach
- Keep AI-driven content generation for arguments
- Use templates for standard sections (caption, introduction, prayer)
- Combine template structure with dynamic content

## Shared Utilities

Both systems can share common utilities:

### 1. Citation Formatting
```python
from src.ai_agents.citation_formatter import citation_formatter
# Used by both motion drafter and template renderer
```

### 2. Legal Formatting
```python
from src.ai_agents.legal_formatter import legal_formatter
# Common formatting rules
```

### 3. Variable Processing
```python
# New shared utility for variable extraction and validation
class TemplateVariableProcessor:
    def extract_variables_from_context(self, context: Dict) -> Dict[str, Any]
    def validate_variables(self, template: DocumentTemplate, variables: Dict)
```

## Benefits of BMad Template System

1. **Compliance**: Built-in compliance validation
2. **Consistency**: Standardized document structure
3. **Maintainability**: Templates can be updated without code changes
4. **Testability**: Templates can be tested independently
5. **Flexibility**: Easy to add new jurisdictions or document types

## Recommendations

1. **Gradual Migration**: Start with simple motions (e.g., routine motions)
2. **Hybrid Approach**: Keep AI generation for complex arguments
3. **Template Library**: Build a library of tested, compliant templates
4. **Version Management**: Track template changes for compliance
5. **Validation Framework**: Extend validation for motion-specific rules

## Future Enhancements

1. **Template Inheritance**: Base templates with jurisdiction overrides
2. **Dynamic Sections**: AI-selected sections based on motion type
3. **Template Marketplace**: Share templates across firms
4. **Compliance Updates**: Automatic updates when rules change
5. **Multi-Language Support**: Templates in different languages

## Conclusion

The Good Faith Letter implementation demonstrates a robust template system that can be extended to other document types. The BMad Framework provides structure and compliance validation while maintaining flexibility for dynamic content generation. Future motion template implementation should follow these patterns while preserving the AI-driven capabilities that make complex argument generation possible.