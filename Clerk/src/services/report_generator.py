"""
Report generation service for deficiency analysis results.

This service formats DeficiencyReport data into various output formats
including JSON, HTML, and preparation for PDF generation.
"""

from datetime import datetime
from typing import Any, Dict, List, Optional, Union
from uuid import UUID

from jinja2 import Environment, FileSystemLoader, select_autoescape
from pydantic import BaseModel

from src.models.deficiency_models import DeficiencyItem, DeficiencyReport
from src.services.deficiency_service import DeficiencyService
from src.services.report_storage import ReportStorage
from src.utils.logger import get_logger
from src.utils.report_formatter import ReportFormatter

logger = get_logger("clerk_api")


class ReportVersion(BaseModel):
    """Model for tracking report versions."""

    version: int
    created_at: datetime
    created_by: Optional[str] = None
    change_summary: Optional[str] = None


class ReportGenerator:
    """
    Service for generating deficiency reports in multiple formats.

    Handles formatting of DeficiencyReport data structures into
    JSON, HTML, and other formats with case isolation.
    """

    def __init__(self, db_session=None):
        """
        Initialize ReportGenerator with required dependencies.

        Sets up Jinja2 template environment and deficiency service.

        Args:
            db_session: Optional database session for storage operations.
        """
        self.deficiency_service = DeficiencyService()
        self.storage = ReportStorage(db_session) if db_session else None
        self._setup_template_environment()
        logger.info("Initialized ReportGenerator")

    def _setup_template_environment(self) -> None:
        """Configure Jinja2 template environment for HTML rendering."""
        # Templates will be in Clerk/templates/deficiency_reports/
        self.jinja_env = Environment(
            loader=FileSystemLoader("templates/deficiency_reports"),
            autoescape=select_autoescape(["html", "xml"]),
        )

    async def format_deficiency_report(
        self,
        report: DeficiencyReport,
        deficiency_items: List[DeficiencyItem],
        include_evidence: bool = True,
        max_evidence_per_item: int = 5,
    ) -> Dict[str, Union[DeficiencyReport, List[DeficiencyItem]]]:
        """
        Format DeficiencyReport data structure for various outputs.

        Args:
            report (DeficiencyReport): The deficiency report to format.
            deficiency_items (List[DeficiencyItem]): Associated deficiency items.
            include_evidence (bool): Whether to include evidence chunks.
            max_evidence_per_item (int): Maximum evidence chunks per item.

        Returns:
            Dict: Formatted report data with report and items.

        Raises:
            ValueError: If report or items are invalid.
        """
        if not report:
            raise ValueError("Report cannot be None")

        logger.info(
            f"Formatting deficiency report {report.id} for case {report.case_name}"
        )

        # Filter evidence if requested
        if not include_evidence:
            for item in deficiency_items:
                item.evidence_chunks = []
        elif max_evidence_per_item > 0:
            for item in deficiency_items:
                # Limit evidence chunks to top N by relevance score
                sorted_chunks = sorted(
                    item.evidence_chunks,
                    key=lambda x: x.get("relevance_score", 0),
                    reverse=True,
                )
                item.evidence_chunks = sorted_chunks[:max_evidence_per_item]

        return {
            "report": report,
            "deficiency_items": deficiency_items,
            "metadata": {
                "generated_at": datetime.utcnow(),
                "total_items": len(deficiency_items),
                "evidence_included": include_evidence,
            },
        }

    def get_report_version_info(
        self, report_id: UUID, version: int = 1
    ) -> ReportVersion:
        """
        Get version information for a report.

        Args:
            report_id (UUID): Report identifier.
            version (int): Version number to retrieve.

        Returns:
            ReportVersion: Version information for the report.
        """
        # This will be implemented with database integration
        return ReportVersion(
            version=version,
            created_at=datetime.utcnow(),
            change_summary="Initial report generation",
        )

    def calculate_summary_statistics(
        self, deficiency_items: List[DeficiencyItem]
    ) -> Dict[str, Union[int, float, str]]:
        """
        Calculate aggregate statistics for deficiency items.

        Args:
            deficiency_items (List[DeficiencyItem]): Items to analyze.

        Returns:
            Dict: Statistics including counts and percentages.
        """
        if not deficiency_items:
            return self._get_empty_statistics()

        # Count items by classification
        classification_counts = {
            "fully_produced": 0,
            "partially_produced": 0,
            "not_produced": 0,
            "no_responsive_docs": 0,
        }

        for item in deficiency_items:
            if item.classification in classification_counts:
                classification_counts[item.classification] += 1

        total_items = len(deficiency_items)

        # Calculate percentages
        percentages = {
            f"{key}_percentage": round((count / total_items) * 100, 2)
            for key, count in classification_counts.items()
        }

        # Determine most common deficiency type
        most_common = (
            max(classification_counts.items(), key=lambda x: x[1])[0]
            if classification_counts
            else None
        )

        return {
            **classification_counts,
            **percentages,
            "total_analyzed": total_items,
            "most_common_deficiency": most_common,
            "compliance_rate": round(
                (classification_counts["fully_produced"] / total_items) * 100, 2
            )
            if total_items > 0
            else 0.0,
        }

    def _get_empty_statistics(self) -> Dict[str, Union[int, float, None]]:
        """Return empty statistics structure."""
        return {
            "fully_produced": 0,
            "partially_produced": 0,
            "not_produced": 0,
            "no_responsive_docs": 0,
            "fully_produced_percentage": 0.0,
            "partially_produced_percentage": 0.0,
            "not_produced_percentage": 0.0,
            "no_responsive_docs_percentage": 0.0,
            "total_analyzed": 0,
            "most_common_deficiency": None,
            "compliance_rate": 0.0,
        }

    def generate_summary_insights(
        self, statistics: Dict[str, Union[int, float, str]]
    ) -> List[str]:
        """
        Generate human-readable insights from statistics.

        Args:
            statistics (Dict): Calculated summary statistics.

        Returns:
            List[str]: List of insight statements.
        """
        insights = []

        # Compliance insight
        compliance_rate = statistics.get("compliance_rate", 0)
        if compliance_rate >= 80:
            insights.append(
                f"High compliance rate ({compliance_rate}%) indicates "
                "thorough production effort."
            )
        elif compliance_rate >= 50:
            insights.append(
                f"Moderate compliance rate ({compliance_rate}%) suggests "
                "room for improvement in production completeness."
            )
        else:
            insights.append(
                f"Low compliance rate ({compliance_rate}%) indicates "
                "significant deficiencies in production."
            )

        # Most common deficiency insight
        most_common = statistics.get("most_common_deficiency")
        if most_common and most_common != "fully_produced":
            insights.append(
                f"Most common issue: {most_common.replace('_', ' ').title()}"
            )

        # Specific deficiency insights
        not_produced = statistics.get("not_produced", 0)
        if not_produced > 0:
            insights.append(
                f"{not_produced} requests have no production despite "
                "potential responsive documents."
            )

        return insights

    def format_detailed_findings(
        self,
        deficiency_items: List[DeficiencyItem],
        include_confidence: bool = True,
        collapsible_evidence: bool = True,
    ) -> List[Dict]:
        """
        Format deficiency items for detailed review.

        Args:
            deficiency_items (List[DeficiencyItem]): Items to format.
            include_confidence (bool): Include confidence scores.
            collapsible_evidence (bool): Format for collapsible sections.

        Returns:
            List[Dict]: Formatted findings for each RTP request.
        """
        formatted_findings = []

        for item in deficiency_items:
            finding = {
                "request_number": item.request_number,
                "request_text": item.request_text,
                "oc_response": item.oc_response_text,
                "classification": self._format_classification(item.classification),
                "classification_raw": item.classification,
            }

            if include_confidence:
                finding["confidence_score"] = item.confidence_score
                finding["confidence_level"] = self._get_confidence_level(
                    item.confidence_score
                )

            # Format evidence with citations
            if item.evidence_chunks:
                finding["evidence"] = self._format_evidence_chunks(
                    item.evidence_chunks, collapsible_evidence
                )
                finding["evidence_count"] = len(item.evidence_chunks)
            else:
                finding["evidence"] = []
                finding["evidence_count"] = 0

            # Include reviewer notes if present
            if item.reviewer_notes:
                finding["reviewer_notes"] = item.reviewer_notes

            if item.modified_by:
                finding["last_modified"] = {
                    "by": item.modified_by,
                    "at": item.modified_at.isoformat() if item.modified_at else None,
                }

            formatted_findings.append(finding)

        return formatted_findings

    def _format_classification(self, classification: str) -> str:
        """Convert classification to human-readable format."""
        formatting_map = {
            "fully_produced": "Fully Produced",
            "partially_produced": "Partially Produced",
            "not_produced": "Not Produced",
            "no_responsive_docs": "No Responsive Documents",
        }
        return formatting_map.get(classification, classification)

    def _get_confidence_level(self, score: float) -> str:
        """Categorize confidence score into levels."""
        if score >= 0.9:
            return "Very High"
        elif score >= 0.8:
            return "High"
        elif score >= 0.7:
            return "Moderate"
        elif score >= 0.6:
            return "Low"
        else:
            return "Very Low"

    def _format_evidence_chunks(
        self, chunks: List[Dict], collapsible: bool = True
    ) -> List[Dict]:
        """
        Format evidence chunks with citations.

        Args:
            chunks (List[Dict]): Evidence chunks to format.
            collapsible (bool): Add metadata for UI collapsing.

        Returns:
            List[Dict]: Formatted evidence with citations.
        """
        formatted_chunks = []

        for idx, chunk in enumerate(chunks):
            formatted = {
                "index": idx + 1,
                "text": chunk.get("chunk_text", ""),
                "relevance_score": chunk.get("relevance_score", 0),
                "source_document_id": chunk.get("document_id", ""),
                "citation": self._build_citation(chunk),
            }

            if collapsible:
                formatted["collapsed"] = idx >= 3  # Show first 3 by default

            formatted_chunks.append(formatted)

        # Sort by relevance score descending
        formatted_chunks.sort(key=lambda x: x["relevance_score"], reverse=True)

        return formatted_chunks

    def _build_citation(self, chunk: Dict) -> str:
        """
        Build citation string from chunk metadata.

        Args:
            chunk (Dict): Evidence chunk with metadata.

        Returns:
            str: Formatted citation.
        """
        parts = []

        if chunk.get("bates_range"):
            parts.append(f"Bates: {chunk['bates_range']}")

        if chunk.get("page_number"):
            parts.append(f"Page {chunk['page_number']}")

        if chunk.get("document_name"):
            parts.append(f"Doc: {chunk['document_name']}")

        return (
            " | ".join(parts)
            if parts
            else f"Doc ID: {chunk.get('document_id', 'Unknown')}"
        )

    async def generate_report(
        self,
        report: DeficiencyReport,
        deficiency_items: List[DeficiencyItem],
        format: str = "json",
        options: Dict[str, Any] = None,
    ) -> str:
        """
        Generate report in specified format.

        Args:
            report (DeficiencyReport): The deficiency report.
            deficiency_items (List[DeficiencyItem]): Associated items.
            format (str): Output format (json|markdown|html).
            options (Dict): Format-specific options.

        Returns:
            str: Formatted report content.

        Raises:
            ValueError: If format is not supported.
        """
        options = options or {}

        # Validate format
        supported_formats = ["json", "markdown", "html"]
        if format not in supported_formats:
            raise ValueError(f"Format must be one of: {supported_formats}")

        logger.info(f"Generating {format} report for case {report.case_name}")

        # Prepare common report data
        report_data = await self._prepare_report_data(report, deficiency_items, options)

        # Generate based on format
        formatter = ReportFormatter()

        if format == "json":
            return formatter.to_json(report_data, pretty=options.get("pretty", True))

        elif format == "markdown":
            return formatter.to_markdown(
                report_data, include_toc=options.get("include_toc", True)
            )

        elif format == "html":
            template = None
            if options.get("template_name"):
                template = self.jinja_env.get_template(options["template_name"])
            return formatter.to_html(report_data, template)

    async def _prepare_report_data(
        self,
        report: DeficiencyReport,
        deficiency_items: List[DeficiencyItem],
        options: Dict[str, Any],
    ) -> Dict[str, Any]:
        """
        Prepare comprehensive report data structure.

        Args:
            report (DeficiencyReport): Report metadata.
            deficiency_items (List[DeficiencyItem]): Report items.
            options (Dict): Processing options.

        Returns:
            Dict: Complete report data for formatting.
        """
        # Format basic report data
        formatted_data = await self.format_deficiency_report(
            report,
            deficiency_items,
            include_evidence=options.get("include_evidence", True),
            max_evidence_per_item=options.get("max_evidence_per_item", 5),
        )

        # Calculate statistics
        statistics = self.calculate_summary_statistics(deficiency_items)

        # Generate insights
        insights = self.generate_summary_insights(statistics)

        # Format detailed findings
        findings = self.format_detailed_findings(
            deficiency_items,
            include_confidence=options.get("include_confidence", True),
            collapsible_evidence=options.get("collapsible_evidence", True),
        )

        return {
            "report": report.model_dump(),
            "statistics": statistics,
            "insights": insights,
            "findings": findings,
            "metadata": formatted_data["metadata"],
            "generation_options": options,
        }

    async def generate_and_store_report(
        self,
        report: DeficiencyReport,
        deficiency_items: List[DeficiencyItem],
        format: str = "json",
        options: Dict[str, Any] = None,
        created_by: Optional[str] = None,
    ) -> Dict[str, Any]:
        """
        Generate report and store in database.

        Args:
            report (DeficiencyReport): The deficiency report.
            deficiency_items (List[DeficiencyItem]): Associated items.
            format (str): Output format.
            options (Dict): Format-specific options.
            created_by (str): User generating the report.

        Returns:
            Dict: Contains report_id, format, and storage status.

        Raises:
            RuntimeError: If storage is not configured.
        """
        if not self.storage:
            raise RuntimeError(
                "Storage not configured. Initialize with database session."
            )

        # Generate report content
        content = await self.generate_report(report, deficiency_items, format, options)

        # Store report data
        saved_report = await self.storage.save_report(
            report, deficiency_items, created_by
        )

        # Store generated format
        generated = await self.storage.save_generated_report(
            report_id=saved_report.id, format=format, content=content, options=options
        )

        return {
            "report_id": str(saved_report.id),
            "version": saved_report.version,
            "format": format,
            "generated_id": str(generated.id),
            "expires_at": generated.expires_at.isoformat(),
        }
