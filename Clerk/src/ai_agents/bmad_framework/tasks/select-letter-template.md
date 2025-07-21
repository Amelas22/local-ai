# Select Letter Template Task

## Purpose
Select the appropriate Good Faith letter template based on jurisdiction and case requirements following BMad template patterns.

## Task Execution
1. Validate jurisdiction parameter (federal/state)
2. Load appropriate template from BMad templates directory
3. Extract template metadata including required variables
4. Validate template compliance with jurisdiction requirements
5. Return template definition with requirements

## Elicitation Required
elicit: false

## WebSocket Events
- agent:task_started - Template selection begun
- agent:task_progress - Loading template for jurisdiction
- agent:task_completed - Template selected successfully

## Implementation
```python
async def execute_select_letter_template(
    jurisdiction: str,
    state_code: Optional[str] = None,
    security_context: AgentSecurityContext = None
) -> Dict[str, Any]:
    """BMad task to select appropriate letter template."""
    from ai_agents.bmad_framework.template_loader import TemplateLoader
    from ai_agents.bmad_framework.websocket_progress import emit_task_event
    
    await emit_task_event(
        "task_started",
        agent_id="good-faith-letter",
        task_name="select-letter-template",
        case_id=security_context.case_id if security_context else None
    )
    
    try:
        # Validate jurisdiction
        if jurisdiction not in ["federal", "state"]:
            raise ValueError(f"Invalid jurisdiction: {jurisdiction}")
        
        # If state jurisdiction, require state code
        if jurisdiction == "state" and not state_code:
            raise ValueError("State code required for state jurisdiction")
        
        await emit_task_event(
            "task_progress",
            agent_id="good-faith-letter", 
            task_name="select-letter-template",
            message=f"Loading {jurisdiction} template"
        )
        
        # Load template
        loader = TemplateLoader()
        template_name = f"good-faith-letter-{jurisdiction}.yaml"
        template_path = f"good-faith-letters/{template_name}"
        
        template_def = await loader.load_template(template_path)
        
        # Extract requirements
        requirements = {
            "template_id": template_def.metadata.get("id", template_name),
            "jurisdiction": jurisdiction,
            "state_code": state_code,
            "required_variables": template_def.get_required_variables(),
            "optional_variables": template_def.get_optional_variables(),
            "sections": [s.name for s in template_def.sections],
            "compliance_rules": template_def.metadata.get("compliance_rules", [])
        }
        
        await emit_task_event(
            "task_completed",
            agent_id="good-faith-letter",
            task_name="select-letter-template",
            result=requirements
        )
        
        return requirements
        
    except Exception as e:
        await emit_task_event(
            "task_failed",
            agent_id="good-faith-letter",
            task_name="select-letter-template",
            error=str(e)
        )
        raise
```

## Input Parameters
- **jurisdiction** (str, required): Either "federal" or "state"
- **state_code** (str, optional): Required if jurisdiction is "state" (e.g., "FL", "TX")
- **security_context** (AgentSecurityContext, required): Security and case context

## Output Format
```json
{
    "template_id": "good-faith-letter-federal",
    "jurisdiction": "federal",
    "state_code": null,
    "required_variables": [
        "CASE_NAME",
        "CASE_NUMBER",
        "OPPOSING_COUNSEL_NAME",
        "DEFICIENCY_COUNT",
        "DEFICIENCY_ITEMS"
    ],
    "optional_variables": [
        "CC_RECIPIENTS",
        "EXHIBITS"
    ],
    "sections": [
        "header",
        "salutation",
        "introduction",
        "deficiency_summary",
        "deficiency_details",
        "meet_and_confer",
        "conclusion",
        "signature_block"
    ],
    "compliance_rules": [
        "FRCP Rule 37 requirements",
        "Meet and confer certification"
    ]
}
```