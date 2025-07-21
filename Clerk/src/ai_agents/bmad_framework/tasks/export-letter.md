# Export Good Faith Letter Task

## Purpose
Export finalized Good Faith letters to various formats (PDF, DOCX, HTML) using BMad document creation patterns.

## Task Execution
1. Validate letter is finalized and user has export permissions
2. Prepare letter content with proper formatting
3. Apply jurisdiction-specific formatting rules
4. Generate requested export format(s)
5. Return export data or file references

## Elicitation Required
elicit: false

## WebSocket Events
- agent:task_started - Export task begun
- agent:task_progress - Generating format
- agent:task_completed - Export completed

## Implementation
```python
async def execute_export_letter(
    letter_id: str,
    format: str,
    include_metadata: bool = True,
    security_context: AgentSecurityContext = None
) -> Dict[str, Any]:
    """BMad task to export Good Faith letter."""
    from src.services.good_faith_letter_agent_service import GoodFaithLetterAgentService
    from ai_agents.bmad_framework.websocket_progress import emit_task_event
    from src.utils.document_exporter import DocumentExporter
    import io
    
    await emit_task_event(
        "task_started",
        agent_id="good-faith-letter",
        task_name="export-letter",
        case_id=security_context.case_id if security_context else None
    )
    
    try:
        # Get letter
        service = GoodFaithLetterAgentService()
        letter = await service.get_letter(
            letter_id=UUID(letter_id),
            security_context=security_context
        )
        
        if not letter:
            raise ValueError(f"Letter {letter_id} not found")
        
        if letter.status != LetterStatus.FINALIZED:
            raise ValueError("Only finalized letters can be exported")
        
        await emit_task_event(
            "task_progress",
            agent_id="good-faith-letter",
            task_name="export-letter",
            message=f"Generating {format.upper()} export"
        )
        
        # Prepare content with metadata
        export_content = _prepare_export_content(letter, include_metadata)
        
        # Generate export based on format
        exporter = DocumentExporter()
        
        if format == "pdf":
            # Generate PDF with legal formatting
            pdf_options = {
                "page_size": "letter",
                "margins": {"top": 1.0, "bottom": 1.0, "left": 1.0, "right": 1.0},
                "font": "Times New Roman",
                "font_size": 12,
                "line_spacing": "single"
            }
            
            export_data = await exporter.to_pdf(
                content=export_content,
                options=pdf_options
            )
            
        elif format == "docx":
            # Generate DOCX with styles
            docx_options = {
                "template_style": "business_letter",
                "header_footer": True,
                "page_numbers": False
            }
            
            export_data = await exporter.to_docx(
                content=export_content,
                options=docx_options
            )
            
        elif format == "html":
            # Generate clean HTML
            html_options = {
                "include_css": True,
                "print_friendly": True
            }
            
            export_data = await exporter.to_html(
                content=export_content,
                options=html_options
            )
            
        else:
            raise ValueError(f"Unsupported format: {format}")
        
        # Create result
        result = {
            "format": format,
            "content": export_data,
            "filename": f"good-faith-letter-{letter.case_name}-{letter_id}.{format}",
            "content_type": _get_content_type(format),
            "size": len(export_data)
        }
        
        await emit_task_event(
            "task_completed",
            agent_id="good-faith-letter",
            task_name="export-letter",
            result={"format": format, "size": result["size"]}
        )
        
        return result
        
    except Exception as e:
        await emit_task_event(
            "task_failed",
            agent_id="good-faith-letter",
            task_name="export-letter",
            error=str(e)
        )
        raise


def _prepare_export_content(letter: GeneratedLetter, include_metadata: bool) -> str:
    """Prepare letter content for export."""
    content = letter.content
    
    if include_metadata:
        # Add metadata header
        metadata_header = f"""[METADATA]
Case: {letter.case_name}
Jurisdiction: {letter.jurisdiction.title()}
Generated: {letter.created_at.strftime("%B %d, %Y")}
Version: {letter.version}
Approved By: {letter.approved_by}

---

"""
        content = metadata_header + content
    
    return content


def _get_content_type(format: str) -> str:
    """Get MIME content type for format."""
    types = {
        "pdf": "application/pdf",
        "docx": "application/vnd.openxmlformats-officedocument.wordprocessingml.document",
        "html": "text/html"
    }
    return types.get(format, "application/octet-stream")
```

## Input Parameters
- **letter_id** (str, required): UUID of the letter to export
- **format** (str, required): Export format ("pdf", "docx", "html")
- **include_metadata** (bool, optional): Include letter metadata in export
- **security_context** (AgentSecurityContext, required): Security and case context

## Output Format
```json
{
    "format": "pdf",
    "content": "<binary data>",
    "filename": "good-faith-letter-Smith_v_Jones_2024-uuid.pdf",
    "content_type": "application/pdf",
    "size": 45678
}
```

## Integration with create-doc
This task extends the BMad create-doc pattern specifically for Good Faith letters:
- Uses same document export utilities
- Follows legal document formatting standards
- Maintains case isolation
- Supports standard export formats

## Error Handling
- Letter not found: Clear error message
- Letter not finalized: Prevent export of draft letters
- Format not supported: List supported formats
- Export failure: Log details and return error