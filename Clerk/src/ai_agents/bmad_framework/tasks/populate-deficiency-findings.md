# Populate Deficiency Findings Task

## Purpose
Map DeficiencyReport data to Good Faith letter template variables following BMad patterns.

## Task Execution
1. Load DeficiencyReport from provided report_id
2. Extract case information and metadata
3. Process deficiency items into template-ready format
4. Include evidence chunks with proper formatting
5. Return mapped variables for template rendering

## Elicitation Required
elicit: false

## WebSocket Events
- agent:task_started - Task execution begun
- agent:task_progress - Processing deficiency items
- agent:task_completed - Variables mapped successfully

## Implementation
```python
async def execute_populate_deficiency_findings(
    report_id: str,
    include_evidence: bool = True,
    evidence_format: str = "inline",
    max_evidence_per_item: int = 3,
    security_context: AgentSecurityContext = None
) -> Dict[str, Any]:
    """BMad task to populate template variables from deficiency report."""
    from src.services.deficiency_service import DeficiencyService
    from ai_agents.bmad_framework.websocket_progress import emit_task_event
    from datetime import datetime
    
    await emit_task_event(
        "task_started",
        agent_id="good-faith-letter",
        task_name="populate-deficiency-findings",
        case_id=security_context.case_id if security_context else None
    )
    
    try:
        # Validate inputs
        if not report_id:
            raise ValueError("report_id is required")
            
        if not security_context:
            raise ValueError("security_context is required for case isolation")
            
        # Load deficiency report
        service = DeficiencyService()
        report = await service.get_deficiency_report(report_id)
        items = await service.get_deficiency_items(report_id)
        
        if not report:
            await emit_task_event(
                "task_failed",
                agent_id="good-faith-letter", 
                task_name="populate-deficiency-findings",
                error=f"DeficiencyReport not found: {report_id}"
            )
            raise ValueError(f"DeficiencyReport not found: {report_id}")
        
        await emit_task_event(
            "task_progress",
            agent_id="good-faith-letter",
            task_name="populate-deficiency-findings",
            message=f"Processing {len(items)} deficiency items"
        )
        
        # Format deficiency items for template
        formatted_items = []
        for idx, item in enumerate(items):
            formatted_item = {
                "REQUEST_NUMBER": item.request_number,
                "REQUEST_TEXT": item.request_text,
                "OC_RESPONSE": item.oc_response_text,
                "CLASSIFICATION": item.classification.replace("_", " ").title(),
                "DEFICIENCY_TYPE": _get_deficiency_type(item.classification),
                "EVIDENCE": []
            }
            
            # Include evidence if requested
            if include_evidence and item.evidence_chunks:
                evidence_chunks = sorted(
                    item.evidence_chunks,
                    key=lambda x: x.get("relevance_score", 0),
                    reverse=True
                )[:max_evidence_per_item]
                
                for chunk in evidence_chunks:
                    formatted_evidence = _format_evidence_chunk(chunk, evidence_format)
                    formatted_item["EVIDENCE"].append(formatted_evidence)
            
            formatted_items.append(formatted_item)
            
            # Progress update every 10 items
            if (idx + 1) % 10 == 0:
                await emit_task_event(
                    "task_progress",
                    agent_id="good-faith-letter",
                    task_name="populate-deficiency-findings",
                    message=f"Processed {idx + 1}/{len(items)} items"
                )
        
        # Build template variables
        template_vars = {
            # Case information
            "CASE_NAME": report.case_name,
            "CASE_NUMBER": report.case_number if hasattr(report, 'case_number') else "TBD",
            
            # Report metadata
            "PRODUCTION_DATE": report.created_at.strftime("%B %d, %Y"),
            "ANALYSIS_DATE": datetime.utcnow().strftime("%B %d, %Y"),
            
            # Summary statistics
            "DEFICIENCY_COUNT": report.total_requests - report.summary_statistics.get("fully_produced", 0),
            "TOTAL_REQUESTS": report.total_requests,
            "FULLY_PRODUCED_COUNT": report.summary_statistics.get("fully_produced", 0),
            "PARTIALLY_PRODUCED_COUNT": report.summary_statistics.get("partially_produced", 0),
            "NOT_PRODUCED_COUNT": report.summary_statistics.get("not_produced", 0),
            "NO_RESPONSIVE_COUNT": report.summary_statistics.get("no_responsive_docs", 0),
            
            # Deficiency items
            "DEFICIENCY_ITEMS": formatted_items,
            
            # Evidence configuration
            "INCLUDE_EVIDENCE": include_evidence,
            "EVIDENCE_FORMAT": evidence_format
        }
        
        await emit_task_event(
            "task_completed",
            agent_id="good-faith-letter",
            task_name="populate-deficiency-findings",
            result={"variable_count": len(template_vars)}
        )
        
        return template_vars
        
    except Exception as e:
        await emit_task_event(
            "task_failed", 
            agent_id="good-faith-letter",
            task_name="populate-deficiency-findings",
            error=str(e)
        )
        raise


def _get_deficiency_type(classification: str) -> str:
    """Map classification to deficiency type description."""
    mapping = {
        "not_produced": "Failed to Produce",
        "partially_produced": "Incomplete Production",
        "no_responsive_docs": "Claimed No Responsive Documents",
        "fully_produced": "Fully Produced"
    }
    return mapping.get(classification, "Unknown")


def _format_evidence_chunk(chunk: Dict[str, Any], format_type: str) -> Dict[str, str]:
    """Format evidence chunk based on format type."""
    formatted = {
        "DOCUMENT_ID": chunk.get("document_id", ""),
        "TEXT": chunk.get("chunk_text", ""),
        "RELEVANCE_SCORE": f"{chunk.get('relevance_score', 0):.2f}",
        "PAGE_NUMBER": str(chunk.get("page_number", ""))
    }
    
    if format_type == "footnote":
        # Format for footnote reference
        formatted["REFERENCE_MARKER"] = f"[{chunk.get('document_id', '')[:8]}]"
    elif format_type == "appendix":
        # Format for appendix reference
        formatted["APPENDIX_REF"] = f"Appendix {chunk.get('document_id', '')[:4]}"
    
    return formatted
```

## Input Parameters
- **report_id** (str, required): UUID of the DeficiencyReport
- **include_evidence** (bool, optional): Whether to include evidence chunks (default: True)
- **evidence_format** (str, optional): Format for evidence ("inline", "footnote", "appendix")
- **max_evidence_per_item** (int, optional): Maximum evidence chunks per deficiency (default: 3)
- **security_context** (AgentSecurityContext, required): Security and case context

## Output Format
```json
{
    "CASE_NAME": "Smith v. Jones",
    "CASE_NUMBER": "2024-CV-12345",
    "PRODUCTION_DATE": "January 15, 2024",
    "ANALYSIS_DATE": "January 20, 2024",
    "DEFICIENCY_COUNT": 15,
    "TOTAL_REQUESTS": 25,
    "FULLY_PRODUCED_COUNT": 10,
    "PARTIALLY_PRODUCED_COUNT": 5,
    "NOT_PRODUCED_COUNT": 8,
    "NO_RESPONSIVE_COUNT": 2,
    "DEFICIENCY_ITEMS": [
        {
            "REQUEST_NUMBER": "RFP No. 12",
            "REQUEST_TEXT": "All emails regarding contract negotiations",
            "OC_RESPONSE": "No responsive documents",
            "CLASSIFICATION": "Not Produced",
            "DEFICIENCY_TYPE": "Failed to Produce",
            "EVIDENCE": [
                {
                    "DOCUMENT_ID": "doc123",
                    "TEXT": "Email from John Doe discussing contract terms...",
                    "RELEVANCE_SCORE": "0.92",
                    "PAGE_NUMBER": "15"
                }
            ]
        }
    ],
    "INCLUDE_EVIDENCE": true,
    "EVIDENCE_FORMAT": "inline"
}
```