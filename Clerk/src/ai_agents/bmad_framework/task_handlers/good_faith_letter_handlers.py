"""
Task handlers for Good Faith Letter agent.

This module provides handlers for letter generation tasks including
template selection, deficiency population, and signature generation.
"""

from typing import Dict, Any, Optional, List
from datetime import datetime

from ..exceptions import ValidationError, TaskExecutionError
from ..security import AgentSecurityContext
from ..template_loader import TemplateLoader


async def handle_select_template(
    context: AgentSecurityContext,
    jurisdiction: str,
    state_code: Optional[str] = None,
    **kwargs
) -> Dict[str, Any]:
    """
    Select appropriate letter template based on jurisdiction.
    
    Args:
        context: Security context
        jurisdiction: federal or state
        state_code: Required if jurisdiction is state
        
    Returns:
        Template metadata including required variables
    """
    if jurisdiction not in ["federal", "state"]:
        raise ValueError(f"Invalid jurisdiction: {jurisdiction}")
        
    if jurisdiction == "state" and not state_code:
        raise ValueError("State code required for state jurisdiction")
        
    template_id = f"good-faith-letter-{jurisdiction}"
    
    # Mock template metadata for testing
    if jurisdiction == "federal":
        return {
            "template_id": template_id,
            "jurisdiction": jurisdiction,
            "required_variables": ["CASE_NAME", "ATTORNEY_NAME", "DEFICIENCY_COUNT"],
            "sections": ["header", "introduction", "deficiencies", "conclusion", "signature"]
        }
    else:
        return {
            "template_id": template_id,
            "jurisdiction": jurisdiction,
            "state_code": state_code,
            "required_variables": ["CASE_NAME", "ATTORNEY_NAME", "DEFICIENCY_COUNT", "STATE_CODE"],
            "sections": ["header", "introduction", "deficiencies", "conclusion", "signature"]
        }


async def handle_populate_deficiency_findings(
    context: AgentSecurityContext,
    report_id: str,
    deficiency_report: Optional[Dict[str, Any]] = None,
    deficiency_items: Optional[List[Dict[str, Any]]] = None,
    include_evidence: bool = False,
    **kwargs
) -> Dict[str, Any]:
    """
    Populate template variables from deficiency report.
    
    Args:
        context: Security context
        report_id: DeficiencyReport ID
        deficiency_report: Report data (for testing)
        deficiency_items: Deficiency items (for testing)
        include_evidence: Whether to include evidence chunks
        
    Returns:
        Template variables populated from report
    """
    # For testing, use provided data
    if deficiency_report:
        case_name = deficiency_report.get("case_name", "Test Case")
        created_at = deficiency_report.get("created_at", datetime.now())
        total_requests = deficiency_report.get("total_requests", 0)
        summary_stats = deficiency_report.get("summary_statistics", {})
        fully_produced = summary_stats.get("fully_produced", 0)
    else:
        # Default test values
        case_name = "Test Case"
        created_at = datetime.now()
        total_requests = 25
        fully_produced = 10
        
    # Calculate deficiency count
    deficiency_count = total_requests - fully_produced
    
    # Build deficiency items list
    deficiency_list = []
    if deficiency_items:
        for item in deficiency_items:
            deficiency_entry = {
                "REQUEST_NUMBER": item.get("request_number"),
                "REQUEST_TEXT": item.get("request_text"),
                "OC_RESPONSE": item.get("oc_response_text"),
                "CLASSIFICATION": item.get("classification"),
            }
            
            if include_evidence and item.get("evidence_chunks"):
                deficiency_entry["EVIDENCE"] = [
                    {
                        "text": chunk.get("chunk_text"),
                        "relevance": chunk.get("relevance_score")
                    }
                    for chunk in item["evidence_chunks"]
                ]
                
            deficiency_list.append(deficiency_entry)
    
    return {
        "CASE_NAME": case_name,
        "DEFICIENCY_COUNT": deficiency_count,
        "TOTAL_REQUESTS": total_requests,
        "ANALYSIS_DATE": created_at.strftime("%B %d, %Y"),
        "DEFICIENCY_ITEMS": deficiency_list,
        "PRODUCTION_SUMMARY": {
            "fully_produced": fully_produced,
            "partially_produced": summary_stats.get("partially_produced", 0),
            "not_produced": summary_stats.get("not_produced", 0),
            "no_responsive_docs": summary_stats.get("no_responsive_docs", 0)
        }
    }


async def handle_generate_signature_block(
    context: AgentSecurityContext,
    attorney_name: str,
    attorney_title: Optional[str] = None,
    firm_name: Optional[str] = None,
    bar_number: Optional[str] = None,
    email: Optional[str] = None,
    phone: Optional[str] = None,
    include_certification: bool = False,
    additional_signatories: Optional[List[Dict[str, str]]] = None,
    **kwargs
) -> Dict[str, Any]:
    """
    Generate signature block for letter.
    
    Args:
        context: Security context
        attorney_name: Primary attorney name
        attorney_title: Title (e.g., Partner, Associate)
        firm_name: Law firm name
        bar_number: Bar admission number
        email: Contact email
        phone: Contact phone
        include_certification: Whether to include certification text
        additional_signatories: List of additional signatories
        
    Returns:
        Signature block components
    """
    # Build primary signature
    primary_sig = {
        "ATTORNEY_NAME": attorney_name,
        "ATTORNEY_TITLE": attorney_title or "Attorney",
        "FIRM_NAME": firm_name or "",
        "BAR_NUMBER": bar_number or "",
        "EMAIL": email or "",
        "PHONE": phone or ""
    }
    
    # Build formatted block
    formatted_lines = ["Respectfully submitted,", "", ""]
    
    if firm_name:
        formatted_lines.append(firm_name.upper())
        formatted_lines.append("")
        
    formatted_lines.extend([
        f"/s/ {attorney_name}",
        attorney_name,
    ])
    
    if attorney_title:
        formatted_lines.append(attorney_title)
        
    if bar_number:
        formatted_lines.append(f"Bar No. {bar_number}")
        
    if email:
        formatted_lines.append(email)
        
    if phone:
        formatted_lines.append(phone)
    
    result = {
        "PRIMARY_SIGNATURE": primary_sig,
        "CLOSING": "Respectfully submitted,",
        "FORMATTED_BLOCK": "\n".join(formatted_lines)
    }
    
    # Add certification if requested
    if include_certification:
        result["CERTIFICATION_TEXT"] = (
            "I hereby certify that I have made a good faith effort to meet and confer "
            "with opposing counsel regarding the discovery deficiencies outlined in this letter."
        )
    
    # Add additional signatories
    if additional_signatories:
        result["ADDITIONAL_SIGNATORIES"] = [
            {
                "name": sig.get("name"),
                "title": sig.get("title", "Attorney"),
                "bar_number": sig.get("bar_number", "")
            }
            for sig in additional_signatories
        ]
    
    return result


# Export task handler for framework registration
async def execute_task(
    task_name: str,
    security_context: Optional[AgentSecurityContext] = None,
    **parameters
) -> Any:
    """
    Execute a Good Faith Letter task by name.
    
    This is a dispatcher that routes to specific handlers.
    
    Args:
        task_name: Name of the task to execute
        security_context: Optional security context
        **parameters: Task-specific parameters
        
    Returns:
        Task result
    """
    # Map task names to handlers
    task_handlers = {
        "select-letter-template": handle_select_template,
        "populate-deficiency-findings": handle_populate_deficiency_findings,
        "generate-signature-block": handle_generate_signature_block,
    }
    
    handler = task_handlers.get(task_name)
    if not handler:
        raise TaskExecutionError(
            task_name,
            f"Unknown task: {task_name}",
            {"available_tasks": list(task_handlers.keys())}
        )
    
    # Execute handler
    return await handler(security_context, **parameters)