#!/usr/bin/env python3
"""
Fix DocumentBoundary creation to include all required parameters
"""

# The fix for DocumentBoundary creation - add title and bates_range as Optional parameters

document_boundary_fix = """
# In discovery_splitter.py, when creating DocumentBoundary objects:

DocumentBoundary(
    start_page=prev_start,
    end_page=boundary_start - 1,
    confidence=boundary_info.get("confidence", 0.8),
    document_type_hint=self._map_document_type(
        boundary_info.get("document_type_hint", "OTHER")
    ),
    indicators=boundary_info.get("indicators", []),
    title=boundary_info.get("title", None),  # Add this
    bates_range=boundary_info.get("bates_range", None)  # Add this
)
"""

# Apply the fix to all DocumentBoundary creations
fixes = [
    # Fix 1: Line ~213
    {
        "old": """DocumentBoundary(
                            start_page=prev_start,
                            end_page=boundary_start - 1,
                            confidence=boundary_info.get("confidence", 0.8),
                            document_type_hint=self._map_document_type(
                                boundary_info.get("document_type_hint", "OTHER")
                            ),
                            indicators=boundary_info.get("indicators", []),
                        )""",
        "new": """DocumentBoundary(
                            start_page=prev_start,
                            end_page=boundary_start - 1,
                            confidence=boundary_info.get("confidence", 0.8),
                            document_type_hint=self._map_document_type(
                                boundary_info.get("document_type_hint", "OTHER")
                            ),
                            indicators=boundary_info.get("indicators", []),
                            title=boundary_info.get("title", None),
                            bates_range=boundary_info.get("bates_range", None)
                        )"""
    },
    # Fix 2: Line ~229
    {
        "old": """DocumentBoundary(
                        start_page=prev_start,
                        end_page=total_pages - 1,
                        confidence=0.8,
                        document_type_hint=self._map_document_type("OTHER"),
                        indicators=["End of window"],
                    )""",
        "new": """DocumentBoundary(
                        start_page=prev_start,
                        end_page=total_pages - 1,
                        confidence=0.8,
                        document_type_hint=self._map_document_type("OTHER"),
                        indicators=["End of window"],
                        title=None,
                        bates_range=None
                    )"""
    },
    # Fix 3: Line ~555
    {
        "old": """section_boundary = DocumentBoundary(
                start_page=section_start,
                end_page=section_end,
                confidence=boundary.confidence,
                document_type_hint=boundary.document_type_hint,
                indicators=getattr(boundary, "indicators", getattr(boundary, "boundary_indicators", [])),
            )""",
        "new": """section_boundary = DocumentBoundary(
                start_page=section_start,
                end_page=section_end,
                confidence=boundary.confidence,
                document_type_hint=boundary.document_type_hint,
                indicators=getattr(boundary, "indicators", getattr(boundary, "boundary_indicators", [])),
                title=getattr(boundary, "title", None),
                bates_range=getattr(boundary, "bates_range", None)
            )"""
    }
]

print("DocumentBoundary fixes to apply:")
for i, fix in enumerate(fixes, 1):
    print(f"\nFix {i}:")
    print("Replace:")
    print(fix["old"])
    print("\nWith:")
    print(fix["new"])