"""
Audit logging utility for legal compliance.

Provides structured logging for all letter operations to maintain
audit trail for legal requirements.
"""

import json
from datetime import datetime
from typing import Dict, Any, Optional, List
from uuid import UUID

from src.utils.logger import get_logger


class AuditLogger:
    """
    Handles audit logging for legal compliance.

    Logs all operations on letters including generation, edits,
    approvals, and exports with full user attribution.
    """

    def __init__(self, component: str):
        """
        Initialize audit logger for a component.

        Args:
            component: Component name for log context
        """
        self.component = component
        self.logger = get_logger(f"audit.{component}")

    def log_letter_generation(
        self,
        letter_id: str,
        case_name: str,
        user_id: str,
        report_id: str,
        jurisdiction: str,
        metadata: Optional[Dict[str, Any]] = None,
    ):
        """
        Log letter generation event.

        Args:
            letter_id: Generated letter ID
            case_name: Case identifier
            user_id: User who initiated generation
            report_id: Source deficiency report ID
            jurisdiction: Letter jurisdiction
            metadata: Additional metadata
        """
        self._log_event(
            event_type="LETTER_GENERATED",
            letter_id=letter_id,
            case_name=case_name,
            user_id=user_id,
            details={
                "report_id": report_id,
                "jurisdiction": jurisdiction,
                "metadata": metadata or {},
            },
        )

    def log_letter_edit(
        self,
        letter_id: str,
        case_name: str,
        editor_id: str,
        version_before: int,
        version_after: int,
        sections_modified: List[str],
        edit_notes: Optional[str] = None,
    ):
        """
        Log letter edit event.

        Args:
            letter_id: Letter being edited
            case_name: Case identifier
            editor_id: User making edits
            version_before: Version before edit
            version_after: Version after edit
            sections_modified: List of sections that were modified
            edit_notes: Optional editor notes
        """
        self._log_event(
            event_type="LETTER_EDITED",
            letter_id=letter_id,
            case_name=case_name,
            user_id=editor_id,
            details={
                "version_before": version_before,
                "version_after": version_after,
                "sections_modified": sections_modified,
                "edit_notes": edit_notes,
            },
        )

    def log_letter_approval(
        self,
        letter_id: str,
        case_name: str,
        approver_id: str,
        approval_notes: Optional[str] = None,
    ):
        """
        Log letter approval event.

        Args:
            letter_id: Letter being approved
            case_name: Case identifier
            approver_id: User approving the letter
            approval_notes: Optional approval notes
        """
        self._log_event(
            event_type="LETTER_APPROVED",
            letter_id=letter_id,
            case_name=case_name,
            user_id=approver_id,
            details={
                "approval_notes": approval_notes,
                "approval_timestamp": datetime.utcnow().isoformat(),
            },
        )

    def log_letter_finalization(
        self,
        letter_id: str,
        case_name: str,
        finalizer_id: str,
        export_formats: Optional[List[str]] = None,
    ):
        """
        Log letter finalization event.

        Args:
            letter_id: Letter being finalized
            case_name: Case identifier
            finalizer_id: User finalizing the letter
            export_formats: Requested export formats
        """
        self._log_event(
            event_type="LETTER_FINALIZED",
            letter_id=letter_id,
            case_name=case_name,
            user_id=finalizer_id,
            details={
                "export_formats": export_formats or [],
                "finalization_timestamp": datetime.utcnow().isoformat(),
            },
        )

    def log_letter_export(
        self,
        letter_id: str,
        case_name: str,
        user_id: str,
        export_format: str,
        file_size: Optional[int] = None,
    ):
        """
        Log letter export event.

        Args:
            letter_id: Letter being exported
            case_name: Case identifier
            user_id: User exporting the letter
            export_format: Format of export (pdf, docx, html)
            file_size: Size of exported file in bytes
        """
        self._log_event(
            event_type="LETTER_EXPORTED",
            letter_id=letter_id,
            case_name=case_name,
            user_id=user_id,
            details={
                "format": export_format,
                "file_size": file_size,
                "export_timestamp": datetime.utcnow().isoformat(),
            },
        )

    def log_security_event(
        self,
        event_type: str,
        user_id: str,
        details: Dict[str, Any],
        severity: str = "INFO",
    ):
        """
        Log security-related events.

        Args:
            event_type: Type of security event
            user_id: User involved in event
            details: Event details
            severity: Event severity (INFO, WARNING, ERROR, CRITICAL)
        """
        self._log_event(
            event_type=f"SECURITY_{event_type}",
            user_id=user_id,
            severity=severity,
            details=details,
        )

    def log_access_denied(
        self,
        user_id: str,
        resource_type: str,
        resource_id: str,
        case_name: Optional[str] = None,
        reason: str = "Insufficient permissions",
    ):
        """
        Log access denied events.

        Args:
            user_id: User who was denied access
            resource_type: Type of resource (letter, report, etc.)
            resource_id: ID of resource
            case_name: Case name if applicable
            reason: Reason for denial
        """
        self._log_event(
            event_type="ACCESS_DENIED",
            user_id=user_id,
            severity="WARNING",
            resource_type=resource_type,
            resource_id=resource_id,
            case_name=case_name,
            details={"reason": reason, "timestamp": datetime.utcnow().isoformat()},
        )

    def log_rate_limit_exceeded(self, user_id: str, endpoint: str, ip_address: str):
        """
        Log rate limit exceeded events.

        Args:
            user_id: User who exceeded rate limit
            endpoint: API endpoint accessed
            ip_address: IP address of request
        """
        self._log_event(
            event_type="RATE_LIMIT_EXCEEDED",
            user_id=user_id,
            severity="WARNING",
            details={
                "endpoint": endpoint,
                "ip_address": ip_address,
                "timestamp": datetime.utcnow().isoformat(),
            },
        )

    def log_error(
        self,
        operation: str,
        error_message: str,
        user_id: Optional[str] = None,
        letter_id: Optional[str] = None,
        stack_trace: Optional[str] = None,
    ):
        """
        Log error events.

        Args:
            operation: Operation that failed
            error_message: Error message
            user_id: User if applicable
            letter_id: Letter ID if applicable
            stack_trace: Stack trace for debugging
        """
        self._log_event(
            event_type="ERROR",
            severity="ERROR",
            operation=operation,
            user_id=user_id,
            letter_id=letter_id,
            details={
                "error_message": error_message,
                "stack_trace": stack_trace,
                "timestamp": datetime.utcnow().isoformat(),
            },
        )

    def _log_event(self, event_type: str, severity: str = "INFO", **kwargs):
        """
        Internal method to log events.

        Args:
            event_type: Type of event
            severity: Log severity
            **kwargs: Event data
        """
        log_entry = {
            "timestamp": datetime.utcnow().isoformat(),
            "component": self.component,
            "event_type": event_type,
            "severity": severity,
            **kwargs,
        }

        # Convert UUIDs to strings for JSON serialization
        for key, value in log_entry.items():
            if isinstance(value, UUID):
                log_entry[key] = str(value)
            elif isinstance(value, dict):
                for k, v in value.items():
                    if isinstance(v, UUID):
                        value[k] = str(v)

        # Log as JSON for easy parsing
        log_message = json.dumps(log_entry)

        # Use appropriate log level
        if severity == "ERROR":
            self.logger.error(log_message)
        elif severity == "WARNING":
            self.logger.warning(log_message)
        elif severity == "CRITICAL":
            self.logger.critical(log_message)
        else:
            self.logger.info(log_message)


# Global audit logger instances
letter_audit_logger = AuditLogger("good_faith_letter")
api_audit_logger = AuditLogger("api")
security_audit_logger = AuditLogger("security")
