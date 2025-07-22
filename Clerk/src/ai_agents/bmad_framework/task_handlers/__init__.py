"""
Task handlers module for BMad framework.

This module contains handler implementations for various agent tasks.
"""

from .deficiency_analyzer_handlers import (
    handle_analyze_rtp,
    handle_search_production,
    handle_categorize_compliance,
    handle_full_analysis,
)

from .good_faith_letter_handlers import (
    execute_task,
    handle_select_template,
    handle_populate_deficiency_findings,
    handle_generate_signature_block,
)

__all__ = [
    "handle_analyze_rtp",
    "handle_search_production",
    "handle_categorize_compliance",
    "handle_full_analysis",
    "execute_task",
    "handle_select_template",
    "handle_populate_deficiency_findings",
    "handle_generate_signature_block",
]
