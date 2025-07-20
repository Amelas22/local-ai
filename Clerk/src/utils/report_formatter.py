"""
Report formatting utilities for multi-format output.

Provides JSON, Markdown, and HTML formatting capabilities
for deficiency reports.
"""

import json
from datetime import datetime
from typing import Any, Dict

from jinja2 import Template


class ReportFormatter:
    """
    Utility class for formatting reports in multiple formats.

    Handles conversion of report data to JSON, Markdown, and HTML.
    """

    @staticmethod
    def to_json(data: Dict[str, Any], pretty: bool = True) -> str:
        """
        Convert report data to JSON format.

        Args:
            data (Dict): Report data to format.
            pretty (bool): Use pretty printing with indentation.

        Returns:
            str: JSON formatted report.
        """
        if pretty:
            return json.dumps(
                data,
                indent=2,
                default=str,  # Handle datetime, UUID, etc.
                ensure_ascii=False,
            )
        return json.dumps(data, default=str, ensure_ascii=False)

    @staticmethod
    def to_markdown(report_data: Dict[str, Any], include_toc: bool = True) -> str:
        """
        Convert report data to Markdown format.

        Args:
            report_data (Dict): Report data with all sections.
            include_toc (bool): Include table of contents.

        Returns:
            str: Markdown formatted report.
        """
        md_lines = []

        # Header
        md_lines.append("# Deficiency Analysis Report")
        md_lines.append(f"\n**Case:** {report_data['report']['case_name']}")
        md_lines.append(
            f"**Generated:** {datetime.utcnow().strftime('%Y-%m-%d %H:%M UTC')}"
        )
        md_lines.append(
            f"**Total Requests Analyzed:** {report_data['report']['total_requests']}"
        )

        # Table of Contents
        if include_toc:
            md_lines.append("\n## Table of Contents")
            md_lines.append("1. [Executive Summary](#executive-summary)")
            md_lines.append("2. [Summary Statistics](#summary-statistics)")
            md_lines.append("3. [Detailed Findings](#detailed-findings)")
            md_lines.append("4. [Methodology](#methodology)")

        # Executive Summary with insights
        md_lines.append("\n## Executive Summary")
        if "insights" in report_data:
            for insight in report_data["insights"]:
                md_lines.append(f"- {insight}")

        # Summary Statistics
        md_lines.append("\n## Summary Statistics")
        stats = report_data.get("statistics", {})
        md_lines.append("\n| Classification | Count | Percentage |")
        md_lines.append("|----------------|-------|------------|")

        for classification in [
            "fully_produced",
            "partially_produced",
            "not_produced",
            "no_responsive_docs",
        ]:
            count = stats.get(classification, 0)
            percentage = stats.get(f"{classification}_percentage", 0)
            label = classification.replace("_", " ").title()
            md_lines.append(f"| {label} | {count} | {percentage}% |")

        # Detailed Findings
        md_lines.append("\n## Detailed Findings")

        for finding in report_data.get("findings", []):
            md_lines.append(f"\n### {finding['request_number']}")
            md_lines.append(f"\n**Request:** {finding['request_text']}")
            md_lines.append(f"\n**OC Response:** {finding['oc_response']}")
            md_lines.append(f"\n**Classification:** {finding['classification']}")

            if "confidence_level" in finding:
                md_lines.append(
                    f"**Confidence:** {finding['confidence_level']} "
                    f"({finding.get('confidence_score', 0):.2f})"
                )

            if finding.get("evidence"):
                md_lines.append("\n**Evidence:**")
                for idx, evidence in enumerate(finding["evidence"][:3]):
                    md_lines.append(f"\n{idx + 1}. {evidence['text'][:200]}...")
                    md_lines.append(f"   - *{evidence['citation']}*")
                    md_lines.append(
                        f"   - Relevance: {evidence['relevance_score']:.2f}"
                    )

        # Methodology
        md_lines.append("\n## Methodology")
        md_lines.append("\nThis report was generated using AI-powered analysis to:")
        md_lines.append("- Compare RTP requests against produced documents")
        md_lines.append("- Classify production completeness")
        md_lines.append("- Identify relevant evidence in the production set")

        return "\n".join(md_lines)

    @staticmethod
    def to_html(report_data: Dict[str, Any], template: Template = None) -> str:
        """
        Convert report data to HTML format.

        Args:
            report_data (Dict): Report data with all sections.
            template (Template): Optional Jinja2 template.

        Returns:
            str: HTML formatted report.
        """
        if template:
            return template.render(**report_data)

        # Default HTML template
        html_parts = [
            "<!DOCTYPE html>",
            "<html lang='en'>",
            "<head>",
            "<meta charset='UTF-8'>",
            "<meta name='viewport' content='width=device-width, initial-scale=1.0'>",
            "<title>Deficiency Analysis Report</title>",
            "<style>",
            "body { font-family: Arial, sans-serif; margin: 40px; }",
            "h1, h2, h3 { color: #333; }",
            "table { border-collapse: collapse; width: 100%; margin: 20px 0; }",
            "th, td { border: 1px solid #ddd; padding: 8px; text-align: left; }",
            "th { background-color: #f2f2f2; }",
            ".evidence { background-color: #f9f9f9; padding: 10px; margin: 10px 0; }",
            ".confidence-high { color: green; }",
            ".confidence-moderate { color: orange; }",
            ".confidence-low { color: red; }",
            "</style>",
            "</head>",
            "<body>",
        ]

        # Header
        html_parts.append("<h1>Deficiency Analysis Report</h1>")
        html_parts.append(
            f"<p><strong>Case:</strong> {report_data['report']['case_name']}</p>"
        )
        html_parts.append(
            f"<p><strong>Generated:</strong> {datetime.utcnow().strftime('%Y-%m-%d %H:%M UTC')}</p>"
        )

        # Summary Statistics Table
        html_parts.append("<h2>Summary Statistics</h2>")
        html_parts.append("<table>")
        html_parts.append(
            "<tr><th>Classification</th><th>Count</th><th>Percentage</th></tr>"
        )

        stats = report_data.get("statistics", {})
        for classification in [
            "fully_produced",
            "partially_produced",
            "not_produced",
            "no_responsive_docs",
        ]:
            count = stats.get(classification, 0)
            percentage = stats.get(f"{classification}_percentage", 0)
            label = classification.replace("_", " ").title()
            html_parts.append(
                f"<tr><td>{label}</td><td>{count}</td><td>{percentage}%</td></tr>"
            )

        html_parts.append("</table>")

        # Detailed Findings
        html_parts.append("<h2>Detailed Findings</h2>")

        for finding in report_data.get("findings", []):
            html_parts.append(f"<h3>{finding['request_number']}</h3>")
            html_parts.append(
                f"<p><strong>Request:</strong> {finding['request_text']}</p>"
            )
            html_parts.append(
                f"<p><strong>OC Response:</strong> {finding['oc_response']}</p>"
            )
            html_parts.append(
                f"<p><strong>Classification:</strong> {finding['classification']}</p>"
            )

            if "confidence_level" in finding:
                confidence_class = "confidence-high"
                if finding["confidence_score"] < 0.8:
                    confidence_class = "confidence-moderate"
                if finding["confidence_score"] < 0.7:
                    confidence_class = "confidence-low"

                html_parts.append(
                    f"<p class='{confidence_class}'><strong>Confidence:</strong> "
                    f"{finding['confidence_level']} ({finding.get('confidence_score', 0):.2f})</p>"
                )

        html_parts.extend(["</body>", "</html>"])

        return "\n".join(html_parts)
