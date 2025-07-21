# Generate Signature Block Task

## Purpose
Create appropriate signature format for Good Faith letters including attorney information and professional formatting.

## Task Execution
1. Accept attorney and firm information
2. Format professional signature block
3. Include appropriate contact information
4. Add any required certifications
5. Return formatted signature block

## Elicitation Required
elicit: false

## WebSocket Events
- agent:task_started - Signature generation begun
- agent:task_progress - Formatting signature elements
- agent:task_completed - Signature block created

## Implementation
```python
async def execute_generate_signature_block(
    attorney_name: str,
    attorney_title: str,
    firm_name: str,
    bar_number: str,
    address_lines: List[str],
    phone: str,
    email: str,
    additional_signatories: Optional[List[Dict[str, str]]] = None,
    include_certification: bool = True,
    jurisdiction: str = "federal",
    security_context: AgentSecurityContext = None
) -> Dict[str, Any]:
    """BMad task to generate professional signature block."""
    from ai_agents.bmad_framework.websocket_progress import emit_task_event
    
    await emit_task_event(
        "task_started",
        agent_id="good-faith-letter",
        task_name="generate-signature-block",
        case_id=security_context.case_id if security_context else None
    )
    
    try:
        await emit_task_event(
            "task_progress",
            agent_id="good-faith-letter",
            task_name="generate-signature-block",
            message="Formatting attorney information"
        )
        
        # Format primary signature
        primary_signature = {
            "ATTORNEY_NAME": attorney_name,
            "ATTORNEY_TITLE": attorney_title,
            "BAR_NUMBER": bar_number,
            "FIRM_NAME": firm_name,
            "ADDRESS": "\n".join(address_lines),
            "PHONE": phone,
            "EMAIL": email,
            "SIGNATURE_LINE": "_" * 40,
            "DATE_LINE": "Date: _________________"
        }
        
        # Format additional signatories if provided
        formatted_additional = []
        if additional_signatories:
            for signatory in additional_signatories:
                formatted_additional.append({
                    "ATTORNEY_NAME": signatory.get("name", ""),
                    "ATTORNEY_TITLE": signatory.get("title", "Attorney"),
                    "BAR_NUMBER": signatory.get("bar_number", ""),
                    "SIGNATURE_LINE": "_" * 40
                })
        
        # Add certification language if required
        certification_text = ""
        if include_certification:
            if jurisdiction == "federal":
                certification_text = (
                    "I hereby certify that I have conferred or attempted to confer "
                    "with opposing counsel in a good faith effort to resolve the issues "
                    "raised in this letter without court action."
                )
            else:
                certification_text = (
                    "I hereby certify that I have made a good faith attempt to resolve "
                    "the discovery issues identified in this letter."
                )
        
        await emit_task_event(
            "task_progress",
            agent_id="good-faith-letter",
            task_name="generate-signature-block",
            message="Applying jurisdiction-specific formatting"
        )
        
        # Build complete signature block
        signature_block = {
            "PRIMARY_SIGNATURE": primary_signature,
            "ADDITIONAL_SIGNATURES": formatted_additional,
            "CERTIFICATION_TEXT": certification_text,
            "CLOSING": "Respectfully submitted,",
            "FORMATTED_BLOCK": _format_complete_block(
                primary_signature,
                formatted_additional,
                certification_text
            )
        }
        
        await emit_task_event(
            "task_completed",
            agent_id="good-faith-letter",
            task_name="generate-signature-block",
            result={"signature_count": 1 + len(formatted_additional)}
        )
        
        return signature_block
        
    except Exception as e:
        await emit_task_event(
            "task_failed",
            agent_id="good-faith-letter",
            task_name="generate-signature-block",
            error=str(e)
        )
        raise


def _format_complete_block(
    primary: Dict[str, str],
    additional: List[Dict[str, str]],
    certification: str
) -> str:
    """Format complete signature block as string."""
    lines = []
    
    # Add closing
    lines.append("Respectfully submitted,")
    lines.append("")
    
    # Add certification if present
    if certification:
        lines.append(certification)
        lines.append("")
    
    # Add primary signature
    lines.append(primary["SIGNATURE_LINE"])
    lines.append(primary["ATTORNEY_NAME"])
    lines.append(primary["ATTORNEY_TITLE"])
    lines.append(f"Bar No. {primary['BAR_NUMBER']}")
    lines.append(primary["FIRM_NAME"])
    lines.append(primary["ADDRESS"])
    lines.append(f"Phone: {primary['PHONE']}")
    lines.append(f"Email: {primary['EMAIL']}")
    
    # Add additional signatures
    for sig in additional:
        lines.append("")
        lines.append(sig["SIGNATURE_LINE"])
        lines.append(sig["ATTORNEY_NAME"])
        lines.append(sig["ATTORNEY_TITLE"])
        lines.append(f"Bar No. {sig['BAR_NUMBER']}")
    
    return "\n".join(lines)
```

## Input Parameters
- **attorney_name** (str, required): Primary attorney's name
- **attorney_title** (str, required): Attorney's professional title
- **firm_name** (str, required): Law firm name
- **bar_number** (str, required): Bar admission number
- **address_lines** (List[str], required): Firm address lines
- **phone** (str, required): Contact phone number
- **email** (str, required): Contact email address
- **additional_signatories** (List[Dict], optional): Additional attorneys to include
- **include_certification** (bool, optional): Include good faith certification (default: True)
- **jurisdiction** (str, optional): Jurisdiction for certification language (default: "federal")
- **security_context** (AgentSecurityContext, required): Security and case context

## Output Format
```json
{
    "PRIMARY_SIGNATURE": {
        "ATTORNEY_NAME": "Jane Smith, Esq.",
        "ATTORNEY_TITLE": "Partner",
        "BAR_NUMBER": "12345",
        "FIRM_NAME": "Smith & Associates, P.A.",
        "ADDRESS": "123 Main Street\nSuite 400\nMiami, FL 33131",
        "PHONE": "(305) 555-1234",
        "EMAIL": "jsmith@smithlaw.com",
        "SIGNATURE_LINE": "________________________________________",
        "DATE_LINE": "Date: _________________"
    },
    "ADDITIONAL_SIGNATURES": [
        {
            "ATTORNEY_NAME": "John Doe, Esq.",
            "ATTORNEY_TITLE": "Associate",
            "BAR_NUMBER": "67890",
            "SIGNATURE_LINE": "________________________________________"
        }
    ],
    "CERTIFICATION_TEXT": "I hereby certify that I have conferred...",
    "CLOSING": "Respectfully submitted,",
    "FORMATTED_BLOCK": "Respectfully submitted,\n\nI hereby certify..."
}
```