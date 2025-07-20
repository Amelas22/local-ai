"""Add deficiency report storage tables

Revision ID: 004_add_deficiency_tables
Revises: 003_add_default_updated_at
Create Date: 2025-01-20

"""

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql
from sqlalchemy.sql import func


# revision identifiers, used by Alembic.
revision = "004_add_deficiency_tables"
down_revision = "003_add_default_updated_at"
branch_labels = None
depends_on = None


def upgrade():
    """Create tables for deficiency report storage with versioning."""

    # Create deficiency_reports table
    op.create_table(
        "deficiency_reports",
        sa.Column("id", sa.UUID(), primary_key=True),
        sa.Column("case_name", sa.String(255), nullable=False),
        sa.Column("production_id", sa.UUID(), nullable=False),
        sa.Column("rtp_document_id", sa.UUID(), nullable=False),
        sa.Column("oc_response_document_id", sa.UUID(), nullable=False),
        sa.Column("analysis_status", sa.String(50), nullable=False, default="pending"),
        sa.Column("total_requests", sa.Integer(), nullable=False, default=0),
        sa.Column("summary_statistics", postgresql.JSONB(), nullable=False),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=func.now(),
        ),
        sa.Column("completed_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("analyzed_by", sa.String(255), nullable=True),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            nullable=True,
            server_default=func.now(),
        ),
        sa.Column("version", sa.Integer(), nullable=False, default=1),
    )

    # Create index on case_name for case isolation queries
    op.create_index(
        "idx_deficiency_reports_case_name", "deficiency_reports", ["case_name"]
    )
    op.create_index(
        "idx_deficiency_reports_production_id", "deficiency_reports", ["production_id"]
    )
    op.create_index(
        "idx_deficiency_reports_status", "deficiency_reports", ["analysis_status"]
    )

    # Create deficiency_items table
    op.create_table(
        "deficiency_items",
        sa.Column("id", sa.UUID(), primary_key=True),
        sa.Column(
            "report_id",
            sa.UUID(),
            sa.ForeignKey("deficiency_reports.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column("request_number", sa.String(100), nullable=False),
        sa.Column("request_text", sa.Text(), nullable=False),
        sa.Column("oc_response_text", sa.Text(), nullable=False),
        sa.Column("classification", sa.String(50), nullable=False),
        sa.Column("confidence_score", sa.Float(), nullable=False),
        sa.Column("evidence_chunks", postgresql.JSONB(), nullable=False, default=[]),
        sa.Column("reviewer_notes", sa.Text(), nullable=True),
        sa.Column("modified_by", sa.String(255), nullable=True),
        sa.Column("modified_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=func.now(),
        ),
    )

    # Create indexes for deficiency_items
    op.create_index("idx_deficiency_items_report_id", "deficiency_items", ["report_id"])
    op.create_index(
        "idx_deficiency_items_classification", "deficiency_items", ["classification"]
    )

    # Create report_versions table for versioning
    op.create_table(
        "report_versions",
        sa.Column("id", sa.UUID(), primary_key=True),
        sa.Column(
            "report_id",
            sa.UUID(),
            sa.ForeignKey("deficiency_reports.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column("version", sa.Integer(), nullable=False),
        sa.Column("content", postgresql.JSONB(), nullable=False),
        sa.Column("change_summary", sa.Text(), nullable=True),
        sa.Column("created_by", sa.String(255), nullable=True),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=func.now(),
        ),
    )

    # Create unique constraint on report_id + version
    op.create_index(
        "idx_report_versions_report_version",
        "report_versions",
        ["report_id", "version"],
        unique=True,
    )

    # Create generated_reports table for storing formatted outputs
    op.create_table(
        "generated_reports",
        sa.Column("id", sa.UUID(), primary_key=True),
        sa.Column(
            "report_id",
            sa.UUID(),
            sa.ForeignKey("deficiency_reports.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column("format", sa.String(20), nullable=False),  # json, html, markdown, pdf
        sa.Column("content", sa.Text(), nullable=False),
        sa.Column("file_path", sa.String(500), nullable=True),  # For PDF storage
        sa.Column("generation_options", postgresql.JSONB(), nullable=True),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=func.now(),
        ),
        sa.Column(
            "expires_at", sa.DateTime(timezone=True), nullable=True
        ),  # For cleanup
    )

    # Create indexes for generated_reports
    op.create_index(
        "idx_generated_reports_report_id", "generated_reports", ["report_id"]
    )
    op.create_index("idx_generated_reports_format", "generated_reports", ["format"])
    op.create_index(
        "idx_generated_reports_expires", "generated_reports", ["expires_at"]
    )

    # Add check constraints
    op.create_check_constraint(
        "ck_deficiency_reports_status",
        "deficiency_reports",
        "analysis_status IN ('pending', 'processing', 'completed', 'failed')",
    )

    op.create_check_constraint(
        "ck_deficiency_items_classification",
        "deficiency_items",
        "classification IN ('fully_produced', 'partially_produced', 'not_produced', 'no_responsive_docs')",
    )

    op.create_check_constraint(
        "ck_deficiency_items_confidence",
        "deficiency_items",
        "confidence_score >= 0 AND confidence_score <= 1",
    )

    op.create_check_constraint(
        "ck_generated_reports_format",
        "generated_reports",
        "format IN ('json', 'html', 'markdown', 'pdf')",
    )


def downgrade():
    """Drop deficiency report storage tables."""
    op.drop_table("generated_reports")
    op.drop_table("report_versions")
    op.drop_table("deficiency_items")
    op.drop_table("deficiency_reports")
