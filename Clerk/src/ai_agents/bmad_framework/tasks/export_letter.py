"""
Export letter task implementation.

Provides functionality to export Good Faith letters in various formats.
"""

from typing import Dict, Any, Optional
from uuid import UUID


def _get_content_type(format: str) -> str:
    """
    Get content type for export format.
    
    Args:
        format: Export format (pdf, docx, html)
        
    Returns:
        MIME content type
    """
    content_types = {
        "pdf": "application/pdf",
        "docx": "application/vnd.openxmlformats-officedocument.wordprocessingml.document",
        "html": "text/html",
    }
    return content_types.get(format, "application/octet-stream")