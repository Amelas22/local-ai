# Good Faith Letter Template System Guide

## Table of Contents
1. [Overview](#overview)
2. [Architecture](#architecture)
3. [Template Authoring Guide](#template-authoring-guide)
4. [Usage Examples](#usage-examples)
5. [API Reference](#api-reference)
6. [Customization Guide](#customization-guide)
7. [Troubleshooting](#troubleshooting)

## Overview

The Good Faith Letter Template System is a comprehensive solution for generating discovery deficiency letters. It leverages the BMad Framework's template infrastructure to provide:

- **Jurisdiction templates** for Federal and State courts  
- **Simple letter format** matching standard attorney correspondence
- **Dynamic content generation** from DeficiencyReport data
- **Version control** for template tracking
- **RESTful API** for template management

## Architecture

### System Components

```
┌─────────────────────────────────────────────────────────────┐
│                    Client Application                        │
├─────────────────────────────────────────────────────────────┤
│                  API Layer (FastAPI)                         │
│  GET /api/templates/good-faith-letters                      │
│  GET /api/templates/good-faith-letters/{jurisdiction}       │
├─────────────────────────────────────────────────────────────┤
│              Letter Template Service                         │
│  - Template selection by jurisdiction                       │
│  - Variable mapping from DeficiencyReport                   │
│  - Template rendering with substitution                     │
├─────────────────────────────────────────────────────────────┤
│         Good Faith Letter Template Loader                    │
│  - Jurisdiction-specific loading                            │
│  - Compliance validation                                     │
│  - Template caching                                          │
├─────────────────────────────────────────────────────────────┤
│              BMad Template Infrastructure                    │
│  - YAML template parsing                                     │
│  - Variable validation                                       │
│  - Section management                                        │
└─────────────────────────────────────────────────────────────┘
```

### File Structure

```
Clerk/src/ai_agents/bmad_framework/
├── good_faith_letter_template_loader.py   # Specialized loader
├── templates/
│   └── good-faith-letters/
│       ├── good-faith-letter-federal.yaml
│       └── good-faith-letter-state.yaml
└── docs/
    ├── TEMPLATE_INTEGRATION_PATTERNS.md
    └── GOOD_FAITH_LETTER_TEMPLATE_GUIDE.md

Clerk/src/services/
└── letter_template_service.py             # Service layer

Clerk/src/api/
└── deficiency_endpoints.py                # API endpoints
```

## Template Authoring Guide

### Template Structure

Each Good Faith letter template follows this structure:

```yaml
metadata:
  type: legal_document
  subtype: good_faith_letter
  jurisdiction: [federal|state]
  version: "1.0"
  title: "Good Faith Letter - [Jurisdiction]"
  description: "Description of template purpose"
  author: "Clerk Legal AI System"

document_settings:
  font: Times New Roman
  font_size: 12
  margins: standard_legal
  line_spacing: double
  page_numbers: true

sections:
  - name: section_name
    required: true|false
    order: 1
    template: |
      Template content with {{VARIABLES}}
    variables:
      - VARIABLE_NAME_1
      - VARIABLE_NAME_2
    condition: "CONDITION_EXPRESSION"  # Optional

validation_rules:
  required_variables:
    - CRITICAL_VAR_1
    - CRITICAL_VAR_2
  conditional_sections:
    - name: section_name
      condition: "VARIABLE > 0"
  formatting:
    - variable_pattern: "^[A-Z][A-Z0-9_]*$"
    - template_syntax: "{{VARIABLE_NAME}}"
    - no_template_text_outside_sections: true

output_options:
  formats:
    - pdf:
        page_size: letter
        margins:
          top: 1.0
          bottom: 1.0
          left: 1.25
          right: 1.0
    - docx:
        template_style: legal_pleading
```

### Variable Naming Convention

Variables must follow these rules:
- **UPPERCASE_WITH_UNDERSCORES** format
- Start with a letter
- Only letters, numbers, and underscores allowed
- Descriptive names (e.g., `PLAINTIFF_NAME`, not `PN`)

### Conditional Sections

Sections can be conditionally included:

```yaml
- name: privilege_log_deficiencies
  required: false
  condition: "PRIVILEGE_ISSUES > 0"
  template: |
    The privilege log contains deficiencies...
```

### Repeatable Sections

For lists of items (like deficiencies):

```yaml
- name: detailed_deficiencies
  required: true
  repeatable: true
  template: |
    Request No. {{REQUEST_NUMBER}}: {{REQUEST_TEXT}}
    
    Deficiency: {{DEFICIENCY_DESCRIPTION}}
```

## Usage Examples

### Example 1: Basic Template Rendering

```python
from src.services.letter_template_service import LetterTemplateService
from src.models.deficiency_models import DeficiencyReport, DeficiencyItem

# Initialize service
service = LetterTemplateService()

# Load deficiency data
report = DeficiencyReport(
    case_name="Smith_v_Jones_2024",
    total_requests=25,
    summary_statistics={
        "not_produced": 8,
        "partially_produced": 5
    }
)

items = [
    DeficiencyItem(
        request_number="RFP No. 1",
        request_text="All contracts",
        oc_response_text="No responsive documents",
        classification="not_produced"
    )
]

# Additional variables
variables = {
    "SENDER_EMAIL": "team@lawfirm.com",
    "LETTER_DATE": "October 4, 2024",
    "OPPOSING_COUNSEL_NAME": "Jane Doe, Esq.",
    "OPPOSING_LAW_FIRM": "Doe & Associates",
    "ADDRESS_LINE1": "123 Main Street",
    "CITY": "Miami",
    "STATE": "FL",
    "ZIP": "33101",
    "CASE_NAME": "Smith v. ABC Corp",
    "SALUTATION": "Counselor",
    "REQUESTING_PARTY": "Plaintiff",
    "CLIENT_REFERENCE": "client's",
    "SPECIFIC_DISCOVERY_REFERENCES": "Mr. Smith's responses to Plaintiff's First Request for Production",
    "WAIVER_LANGUAGE": "Please note that all untimely non-privileged objections have been waived.",
    "PARTY_NAME": "ABC Corp",
    "RTP_SET": "1st Request for Production",
    "ATTORNEY_NAME": "Robert Johnson, Esq.",
    # ... other required variables
}

# Render letter
letter_content = await service.render_letter_from_deficiency_report(
    deficiency_report=report,
    deficiency_items=items,
    jurisdiction="federal",
    additional_variables=variables
)
```

### Example 2: API Usage

```python
import requests

# List available templates
response = requests.get(
    "https://api.clerk.legal/api/deficiency/templates/good-faith-letters",
    headers={"X-Case-ID": "case-123", "Authorization": "Bearer token"}
)
templates = response.json()

# Get template requirements
response = requests.get(
    "https://api.clerk.legal/api/deficiency/templates/good-faith-letters/california",
    headers={"X-Case-ID": "case-123", "Authorization": "Bearer token"}
)
requirements = response.json()
print(f"Required variables: {requirements['required_variables']}")
```

### Example 3: Custom Template Creation (Future)

```python
# Note: Custom template creation will be implemented in a future story
custom_template = """
metadata:
  type: legal_document
  subtype: good_faith_letter
  jurisdiction: custom_state
  version: "1.0"
  
sections:
  - name: custom_section
    template: |
      Custom content for {{STATE_NAME}}
    variables:
      - STATE_NAME
"""

# POST to create custom template (future implementation)
```

## API Reference

### List Templates
**GET** `/api/deficiency/templates/good-faith-letters`

Returns list of available templates with metadata.

**Response:**
```json
[
  {
    "jurisdiction": "federal",
    "title": "Good Faith Letter - Federal",
    "version": "1.0",
    "description": "Federal court good faith letter template",
    "compliance_rules": ["frcp_rule_37"]
  }
]
```

### Get Template Requirements
**GET** `/api/deficiency/templates/good-faith-letters/{jurisdiction}`

Returns requirements and variables for specific template.

**Response:**
```json
{
  "jurisdiction": "california",
  "template_version": "1.0",
  "required_variables": ["COURT_NAME", "CASE_NUMBER", ...],
  "all_variables": ["COURT_NAME", "CASE_NUMBER", "OPTIONAL_VAR", ...],
  "sections": [
    {"name": "caption", "required": true},
    {"name": "privilege_log_deficiencies", "required": false}
  ],
  "compliance_requirements": {
    "rule_id": "ccp_2031.310",
    "description": "California Code of Civil Procedure § 2031.310",
    "required_sections": ["caption", "deficiency_summary", ...],
    "required_phrases": ["45-day", "CCP 2031.310"],
    "deadline_days": 45
  }
}
```

## Customization Guide

### Adding a New Jurisdiction

1. Create template file: `good-faith-letter-[jurisdiction].yaml`
2. Add jurisdiction mapping in `GoodFaithLetterTemplateLoader`:
   ```python
   self.jurisdiction_map["new_state"] = "good-faith-letter-new_state.yaml"
   ```
3. Add compliance rules:
   ```python
   self.compliance_rules["new_state"] = ComplianceRule(
       rule_id="state_rule_123",
       description="State Rule Description",
       required_sections=[...],
       required_phrases=[...],
       deadline_days=30
   )
   ```

### Modifying Templates

1. Update the YAML file with changes
2. Increment the version number in metadata
3. Test compliance validation
4. Update any affected API documentation

### Extending Variable Processing

To add custom variable processing:

```python
class CustomLetterTemplateService(LetterTemplateService):
    def _build_variables_from_deficiency_report(self, report, items, additional):
        variables = super()._build_variables_from_deficiency_report(
            report, items, additional
        )
        
        # Add custom processing
        variables["CUSTOM_VAR"] = self._calculate_custom_value(report)
        
        return variables
```

## Troubleshooting

### Common Issues

1. **Missing Required Variables**
   - Error: "Missing required template variables: COURT_NAME, CASE_NUMBER"
   - Solution: Ensure all required variables are provided in the variables dictionary

2. **Invalid Jurisdiction**
   - Error: "No template found for jurisdiction: invalid"
   - Solution: Use one of: federal, state

3. **Compliance Validation Failure**
   - Error: "Missing required phrase: '45-day'"
   - Solution: Check template includes all jurisdiction-specific requirements

4. **Variable Format Error**
   - Error: "Invalid variable name 'court-name'"
   - Solution: Use UPPERCASE_WITH_UNDERSCORES format

### Debug Mode

Enable detailed logging:

```python
import logging
logging.getLogger("clerk_api").setLevel(logging.DEBUG)
```

### Performance Tips

1. **Enable Template Caching**: Templates are cached by default
2. **Batch Operations**: Process multiple letters in parallel
3. **Minimize Variables**: Only include necessary variables

## Best Practices

1. **Always validate templates** after modifications
2. **Test with real DeficiencyReport data** before production
3. **Keep templates versioned** for compliance tracking
4. **Document custom modifications** in template metadata
5. **Use meaningful variable names** for maintainability
6. **Follow jurisdiction-specific formatting** requirements

## Future Enhancements

- Custom template storage in database
- Template versioning with diff tracking
- Multi-language support
- Template inheritance for common sections
- AI-assisted template generation
- Automated compliance updates