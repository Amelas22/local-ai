# Security Integration

## Existing Security Measures
- **Authentication:** JWT-based authentication with PostgreSQL user management
- **Authorization:** Case-based access control via case context middleware
- **Data Protection:** Case isolation at database level
- **Security Tools:** Environment variable management, no secrets in code

## Enhancement Security Requirements
- **New Security Measures:** 
  - RTP/OC response documents not stored in vector DB (prevents exposure)
  - Deficiency reports inherit case access controls
  - Letter templates sanitized to prevent injection
- **Integration Points:**
  - All deficiency endpoints require authenticated user
  - Case context middleware validates access to reports
  - Audit logging for all modifications
- **Compliance Requirements:**
  - Attorney-client privilege maintained
  - Discovery document confidentiality preserved
  - Audit trail for compliance reporting

## Security Testing
- **Existing Security Tests:** JWT validation, case isolation tests
- **New Security Test Requirements:**
  - Cross-case access attempts must fail
  - Unauthenticated access blocked
  - SQL injection prevention in report queries
- **Penetration Testing:** Include deficiency endpoints in security audit

## Security Implementation Patterns

**Access Control Example:**
```python
from src.middleware.case_context import require_case_context

@router.get("/api/deficiency/report/{report_id}")
async def get_deficiency_report(
    report_id: str,
    case_context = Depends(require_case_context("read"))
):
    """Get deficiency report with case access validation."""
    # case_context ensures user has access to this case
    report = await deficiency_service.get_report(
        report_id=report_id,
        case_name=case_context.case_name  # Enforces isolation
    )
    if not report:
        raise HTTPException(status_code=404)
    return report
```

**Audit Logging Pattern:**
```python
async def update_deficiency_item(
    item_id: str,
    updates: DeficiencyItemUpdate,
    current_user: User = Depends(get_current_user)
):
    """Update deficiency item with audit trail."""
    # Log modification attempt
    logger.info(
        "Deficiency item update attempt",
        extra={
            "user_id": current_user.id,
            "item_id": item_id,
            "action": "update_deficiency_item"
        }
    )
    
    # Perform update with user tracking
    updates.modified_by = current_user.email
    updates.modified_at = datetime.utcnow()
    
    result = await deficiency_service.update_item(item_id, updates)
    
    # Log successful modification
    logger.info(
        "Deficiency item updated successfully",
        extra={
            "user_id": current_user.id,
            "item_id": item_id,
            "changes": updates.dict(exclude_unset=True)
        }
    )
    return result
```
