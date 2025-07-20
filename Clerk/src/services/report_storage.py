"""
Report storage service for database operations.

Handles CRUD operations for deficiency reports with versioning
and case isolation.
"""

import json
from datetime import datetime, timedelta
from typing import Dict, List, Optional
from uuid import UUID, uuid4

from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

from src.models.deficiency_models import (
    DeficiencyItem,
    DeficiencyReport,
    GeneratedReport,
    ReportVersion,
)
from src.utils.logger import get_logger

logger = get_logger("clerk_api")


class ReportStorage:
    """
    Service for managing report persistence in PostgreSQL.

    Handles storage, retrieval, versioning, and deletion of
    deficiency reports with case isolation.
    """

    def __init__(self, db_session: AsyncSession):
        """
        Initialize ReportStorage with database session.

        Args:
            db_session (AsyncSession): Database session for operations.
        """
        self.db = db_session
        logger.info("Initialized ReportStorage")

    async def save_report(
        self,
        report: DeficiencyReport,
        deficiency_items: List[DeficiencyItem],
        created_by: Optional[str] = None,
    ) -> DeficiencyReport:
        """
        Save or update a deficiency report with items.

        Args:
            report (DeficiencyReport): Report to save.
            deficiency_items (List[DeficiencyItem]): Report items.
            created_by (str): User creating/updating the report.

        Returns:
            DeficiencyReport: Saved report with updated metadata.

        Raises:
            Exception: If database operation fails.
        """
        try:
            # Check if report exists
            result = await self.db.execute(
                text("SELECT version FROM deficiency_reports WHERE id = :id"),
                {"id": str(report.id)},
            )
            existing_version = result.scalar()

            if existing_version is not None:
                # Update existing report
                report.version = existing_version + 1
                report.updated_at = datetime.utcnow()

                # Create version snapshot before update
                await self._create_version_snapshot(
                    report.id, existing_version, report, deficiency_items, created_by
                )

                # Update report
                await self.db.execute(
                    text("""
                        UPDATE deficiency_reports
                        SET case_name = :case_name,
                            production_id = :production_id,
                            rtp_document_id = :rtp_document_id,
                            oc_response_document_id = :oc_response_document_id,
                            analysis_status = :analysis_status,
                            total_requests = :total_requests,
                            summary_statistics = :summary_statistics,
                            completed_at = :completed_at,
                            analyzed_by = :analyzed_by,
                            updated_at = :updated_at,
                            version = :version
                        WHERE id = :id
                    """),
                    {
                        "id": str(report.id),
                        "case_name": report.case_name,
                        "production_id": str(report.production_id),
                        "rtp_document_id": str(report.rtp_document_id),
                        "oc_response_document_id": str(report.oc_response_document_id),
                        "analysis_status": report.analysis_status,
                        "total_requests": report.total_requests,
                        "summary_statistics": json.dumps(report.summary_statistics),
                        "completed_at": report.completed_at,
                        "analyzed_by": report.analyzed_by,
                        "updated_at": report.updated_at,
                        "version": report.version,
                    },
                )
                logger.info(f"Updating report {report.id} to version {report.version}")
            else:
                # Create new report
                await self.db.execute(
                    text("""
                        INSERT INTO deficiency_reports (
                            id, case_name, production_id, rtp_document_id,
                            oc_response_document_id, analysis_status,
                            total_requests, summary_statistics, created_at,
                            completed_at, analyzed_by, version
                        ) VALUES (
                            :id, :case_name, :production_id, :rtp_document_id,
                            :oc_response_document_id, :analysis_status,
                            :total_requests, :summary_statistics, :created_at,
                            :completed_at, :analyzed_by, :version
                        )
                    """),
                    {
                        "id": str(report.id),
                        "case_name": report.case_name,
                        "production_id": str(report.production_id),
                        "rtp_document_id": str(report.rtp_document_id),
                        "oc_response_document_id": str(report.oc_response_document_id),
                        "analysis_status": report.analysis_status,
                        "total_requests": report.total_requests,
                        "summary_statistics": json.dumps(report.summary_statistics),
                        "created_at": report.created_at,
                        "completed_at": report.completed_at,
                        "analyzed_by": report.analyzed_by,
                        "version": report.version,
                    },
                )
                logger.info(f"Creating new report {report.id}")

            # Save deficiency items
            await self._save_deficiency_items(report.id, deficiency_items)

            # Commit transaction
            await self.db.commit()

            return report

        except Exception as e:
            await self.db.rollback()
            logger.error(f"Failed to save report: {e}")
            raise

    async def _save_deficiency_items(
        self, report_id: UUID, items: List[DeficiencyItem]
    ) -> None:
        """Save or update deficiency items for a report."""
        # Delete existing items
        await self.db.execute(
            text("DELETE FROM deficiency_items WHERE report_id = :report_id"),
            {"report_id": str(report_id)},
        )

        # Add new items
        for item in items:
            item.report_id = report_id
            await self.db.execute(
                text("""
                    INSERT INTO deficiency_items (
                        id, report_id, request_number, request_text,
                        oc_response_text, classification, confidence_score,
                        evidence_chunks, reviewer_notes, modified_by,
                        modified_at, created_at
                    ) VALUES (
                        :id, :report_id, :request_number, :request_text,
                        :oc_response_text, :classification, :confidence_score,
                        :evidence_chunks, :reviewer_notes, :modified_by,
                        :modified_at, :created_at
                    )
                """),
                {
                    "id": str(item.id),
                    "report_id": str(report_id),
                    "request_number": item.request_number,
                    "request_text": item.request_text,
                    "oc_response_text": item.oc_response_text,
                    "classification": item.classification,
                    "confidence_score": item.confidence_score,
                    "evidence_chunks": json.dumps(item.evidence_chunks),
                    "reviewer_notes": item.reviewer_notes,
                    "modified_by": item.modified_by,
                    "modified_at": item.modified_at,
                    "created_at": datetime.utcnow(),
                },
            )

    async def _create_version_snapshot(
        self,
        report_id: UUID,
        version_number: int,
        report: DeficiencyReport,
        items: List[DeficiencyItem],
        created_by: Optional[str],
    ) -> None:
        """Create a version snapshot of the report."""
        await self.db.execute(
            text("""
                INSERT INTO report_versions (
                    id, report_id, version, content,
                    change_summary, created_by, created_at
                ) VALUES (
                    :id, :report_id, :version, :content,
                    :change_summary, :created_by, :created_at
                )
            """),
            {
                "id": str(uuid4()),
                "report_id": str(report_id),
                "version": version_number,
                "content": json.dumps(
                    {
                        "report": report.model_dump(mode="json"),
                        "items": [item.model_dump(mode="json") for item in items],
                    }
                ),
                "change_summary": f"Version {version_number} snapshot",
                "created_by": created_by,
                "created_at": datetime.utcnow(),
            },
        )

    async def get_report(
        self, report_id: UUID, case_name: str
    ) -> Optional[DeficiencyReport]:
        """
        Get a report by ID with case isolation.

        Args:
            report_id (UUID): Report identifier.
            case_name (str): Case name for isolation.

        Returns:
            DeficiencyReport: Report if found and accessible.
        """
        result = await self.db.execute(
            text("""
                SELECT id, case_name, production_id, rtp_document_id,
                       oc_response_document_id, analysis_status, created_at,
                       completed_at, total_requests, summary_statistics,
                       analyzed_by, updated_at, version
                FROM deficiency_reports
                WHERE id = :id AND case_name = :case_name
            """),
            {"id": str(report_id), "case_name": case_name},
        )
        row = result.first()
        if row:
            return DeficiencyReport(
                id=UUID(row.id),
                case_name=row.case_name,
                production_id=UUID(row.production_id),
                rtp_document_id=UUID(row.rtp_document_id),
                oc_response_document_id=UUID(row.oc_response_document_id),
                analysis_status=row.analysis_status,
                created_at=row.created_at,
                completed_at=row.completed_at,
                total_requests=row.total_requests,
                summary_statistics=json.loads(row.summary_statistics)
                if row.summary_statistics
                else {},
                analyzed_by=row.analyzed_by,
                updated_at=row.updated_at,
                version=row.version,
            )
        return None

    async def get_report_items(self, report_id: UUID) -> List[DeficiencyItem]:
        """
        Get all deficiency items for a report.

        Args:
            report_id (UUID): Report identifier.

        Returns:
            List[DeficiencyItem]: Report items.
        """
        result = await self.db.execute(
            text("""
                SELECT id, report_id, request_number, request_text,
                       oc_response_text, classification, confidence_score,
                       evidence_chunks, reviewer_notes, modified_by,
                       modified_at, created_at
                FROM deficiency_items
                WHERE report_id = :report_id
                ORDER BY request_number
            """),
            {"report_id": str(report_id)},
        )
        items = []
        for row in result:
            items.append(
                DeficiencyItem(
                    id=UUID(row.id),
                    report_id=UUID(row.report_id),
                    request_number=row.request_number,
                    request_text=row.request_text,
                    oc_response_text=row.oc_response_text,
                    classification=row.classification,
                    confidence_score=row.confidence_score,
                    evidence_chunks=json.loads(row.evidence_chunks)
                    if row.evidence_chunks
                    else [],
                    reviewer_notes=row.reviewer_notes,
                    modified_by=row.modified_by,
                    modified_at=row.modified_at,
                    created_at=row.created_at,
                )
            )
        return items

    async def list_reports(
        self,
        case_name: str,
        status: Optional[str] = None,
        limit: int = 50,
        offset: int = 0,
    ) -> List[DeficiencyReport]:
        """
        List reports for a case with optional filtering.

        Args:
            case_name (str): Case name for isolation.
            status (str): Optional status filter.
            limit (int): Maximum results to return.
            offset (int): Results offset for pagination.

        Returns:
            List[DeficiencyReport]: Filtered reports.
        """
        # Build query with optional status filter
        query_params = {"case_name": case_name, "limit": limit, "offset": offset}

        if status:
            query_sql = """
                SELECT id, case_name, production_id, rtp_document_id,
                       oc_response_document_id, analysis_status, created_at,
                       completed_at, total_requests, summary_statistics,
                       analyzed_by, updated_at, version
                FROM deficiency_reports
                WHERE case_name = :case_name AND analysis_status = :status
                ORDER BY created_at DESC
                LIMIT :limit OFFSET :offset
            """
            query_params["status"] = status
        else:
            query_sql = """
                SELECT id, case_name, production_id, rtp_document_id,
                       oc_response_document_id, analysis_status, created_at,
                       completed_at, total_requests, summary_statistics,
                       analyzed_by, updated_at, version
                FROM deficiency_reports
                WHERE case_name = :case_name
                ORDER BY created_at DESC
                LIMIT :limit OFFSET :offset
            """

        result = await self.db.execute(text(query_sql), query_params)

        reports = []
        for row in result:
            reports.append(
                DeficiencyReport(
                    id=UUID(row.id),
                    case_name=row.case_name,
                    production_id=UUID(row.production_id),
                    rtp_document_id=UUID(row.rtp_document_id),
                    oc_response_document_id=UUID(row.oc_response_document_id),
                    analysis_status=row.analysis_status,
                    created_at=row.created_at,
                    completed_at=row.completed_at,
                    total_requests=row.total_requests,
                    summary_statistics=json.loads(row.summary_statistics)
                    if row.summary_statistics
                    else {},
                    analyzed_by=row.analyzed_by,
                    updated_at=row.updated_at,
                    version=row.version,
                )
            )
        return reports

    async def save_generated_report(
        self,
        report_id: UUID,
        format: str,
        content: str,
        options: Optional[Dict] = None,
        expires_in_days: int = 30,
    ) -> GeneratedReport:
        """
        Save a generated report in specific format.

        Args:
            report_id (UUID): Parent report ID.
            format (str): Report format (json/html/markdown/pdf).
            content (str): Formatted report content.
            options (Dict): Generation options used.
            expires_in_days (int): Days until expiration.

        Returns:
            GeneratedReport: Saved generated report.
        """
        generated_id = uuid4()
        expires_at = datetime.utcnow() + timedelta(days=expires_in_days)

        await self.db.execute(
            text("""
                INSERT INTO generated_reports (
                    id, report_id, format, content,
                    generation_options, created_at, expires_at
                ) VALUES (
                    :id, :report_id, :format, :content,
                    :generation_options, :created_at, :expires_at
                )
            """),
            {
                "id": str(generated_id),
                "report_id": str(report_id),
                "format": format,
                "content": content,
                "generation_options": json.dumps(options) if options else None,
                "created_at": datetime.utcnow(),
                "expires_at": expires_at,
            },
        )

        await self.db.commit()

        logger.info(f"Saved {format} report for {report_id}, expires {expires_at}")

        return GeneratedReport(
            id=generated_id,
            report_id=report_id,
            format=format,
            content=content,
            generation_options=options,
            created_at=datetime.utcnow(),
            expires_at=expires_at,
        )

    async def get_generated_report(
        self, report_id: UUID, format: str
    ) -> Optional[GeneratedReport]:
        """
        Get a previously generated report.

        Args:
            report_id (UUID): Parent report ID.
            format (str): Desired format.

        Returns:
            GeneratedReport: Generated report if found and not expired.
        """
        result = await self.db.execute(
            text("""
                SELECT id, report_id, format, content, file_path,
                       generation_options, created_at, expires_at
                FROM generated_reports
                WHERE report_id = :report_id 
                  AND format = :format
                  AND expires_at > :now
                ORDER BY created_at DESC
                LIMIT 1
            """),
            {"report_id": str(report_id), "format": format, "now": datetime.utcnow()},
        )
        row = result.first()
        if row:
            return GeneratedReport(
                id=UUID(row.id),
                report_id=UUID(row.report_id),
                format=row.format,
                content=row.content,
                file_path=row.file_path,
                generation_options=json.loads(row.generation_options)
                if row.generation_options
                else None,
                created_at=row.created_at,
                expires_at=row.expires_at,
            )
        return None

    async def get_report_version(
        self, report_id: UUID, version: int
    ) -> Optional[ReportVersion]:
        """
        Get a specific version of a report.

        Args:
            report_id (UUID): Report identifier.
            version (int): Version number.

        Returns:
            ReportVersion: Report version if found.
        """
        result = await self.db.execute(
            text("""
                SELECT id, report_id, version, content,
                       change_summary, created_by, created_at
                FROM report_versions
                WHERE report_id = :report_id AND version = :version
            """),
            {"report_id": str(report_id), "version": version},
        )
        row = result.first()
        if row:
            return ReportVersion(
                id=UUID(row.id),
                report_id=UUID(row.report_id),
                version=row.version,
                content=json.loads(row.content) if row.content else {},
                change_summary=row.change_summary,
                created_by=row.created_by,
                created_at=row.created_at,
            )
        return None

    async def list_report_versions(self, report_id: UUID) -> List[ReportVersion]:
        """
        List all versions of a report.

        Args:
            report_id (UUID): Report identifier.

        Returns:
            List[ReportVersion]: All versions ordered by version number.
        """
        result = await self.db.execute(
            text("""
                SELECT id, report_id, version, content,
                       change_summary, created_by, created_at
                FROM report_versions
                WHERE report_id = :report_id
                ORDER BY version DESC
            """),
            {"report_id": str(report_id)},
        )

        versions = []
        for row in result:
            versions.append(
                ReportVersion(
                    id=UUID(row.id),
                    report_id=UUID(row.report_id),
                    version=row.version,
                    content=json.loads(row.content) if row.content else {},
                    change_summary=row.change_summary,
                    created_by=row.created_by,
                    created_at=row.created_at,
                )
            )
        return versions

    async def cleanup_expired_reports(self) -> int:
        """
        Delete expired generated reports.

        Returns:
            int: Number of reports deleted.
        """
        result = await self.db.execute(
            text("""
                DELETE FROM generated_reports
                WHERE expires_at <= :now
            """),
            {"now": datetime.utcnow()},
        )
        await self.db.commit()

        deleted_count = result.rowcount
        if deleted_count > 0:
            logger.info(f"Cleaned up {deleted_count} expired reports")

        return deleted_count
