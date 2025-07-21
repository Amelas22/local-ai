"""Add Good Faith Letter generation tables

Revision ID: 005_add_letter_tables
Revises: 004_add_deficiency_tables
Create Date: 2025-01-21

"""

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql
from sqlalchemy.sql import func


# revision identifiers, used by Alembic.
revision = "005_add_letter_tables"
down_revision = "004_add_deficiency_tables"
branch_labels = None
depends_on = None


def upgrade():
    """Create tables for Good Faith Letter storage."""

    # Create generated_letters table
    op.create_table(
        "generated_letters",
        sa.Column("id", sa.String(36), primary_key=True),
        sa.Column("report_id", sa.String(36), nullable=False),
        sa.Column("case_name", sa.String(255), nullable=False),
        sa.Column("jurisdiction", sa.String(50), nullable=False),
        sa.Column("content", sa.Text(), nullable=False),
        sa.Column(
            "status",
            sa.String(20),
            nullable=False,
            default="draft"
        ),
        sa.Column("version", sa.Integer(), nullable=False, default=1),
        sa.Column("agent_execution_id", sa.String(255), nullable=True),
        sa.Column("metadata", postgresql.JSONB(), nullable=False, default={}),
        # Timestamps
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=func.now(),
        ),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            nullable=True,
            onupdate=func.now()
        ),
        # Approval tracking
        sa.Column("approved_by", sa.String(255), nullable=True),
        sa.Column("approved_at", sa.DateTime(timezone=True), nullable=True),
    )

    # Create indexes for generated_letters
    op.create_index(
        "idx_letters_case_name", 
        "generated_letters", 
        ["case_name"]
    )
    op.create_index(
        "idx_letters_report_id", 
        "generated_letters", 
        ["report_id"]
    )
    op.create_index(
        "idx_letters_status", 
        "generated_letters", 
        ["status"]
    )
    op.create_index(
        "idx_letters_case_report",
        "generated_letters",
        ["case_name", "report_id"]
    )
    op.create_index(
        "idx_letters_status_case",
        "generated_letters",
        ["status", "case_name"]
    )

    # Create letter_edits table for audit trail
    op.create_table(
        "letter_edits",
        sa.Column("id", sa.String(36), primary_key=True),
        sa.Column(
            "letter_id",
            sa.String(36),
            sa.ForeignKey("generated_letters.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column("section_name", sa.String(100), nullable=False),
        sa.Column("original_content", sa.Text(), nullable=True),
        sa.Column("new_content", sa.Text(), nullable=False),
        sa.Column("editor_id", sa.String(255), nullable=False),
        sa.Column("editor_notes", sa.Text(), nullable=True),
        sa.Column(
            "edited_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=func.now(),
        ),
    )

    # Create index for letter_edits
    op.create_index(
        "idx_edits_letter_id", 
        "letter_edits", 
        ["letter_id"]
    )
    op.create_index(
        "idx_edits_letter_timestamp",
        "letter_edits",
        ["letter_id", "edited_at"]
    )

    # Add check constraints
    op.create_check_constraint(
        "check_letter_status",
        "generated_letters",
        "status IN ('draft', 'review', 'approved', 'finalized')",
    )

    op.create_check_constraint(
        "check_jurisdiction",
        "generated_letters",
        "jurisdiction IN ('federal', 'state')",
    )

    op.create_check_constraint(
        "check_version_positive",
        "generated_letters",
        "version >= 1",
    )


def downgrade():
    """Drop Good Faith Letter storage tables."""
    op.drop_table("letter_edits")
    op.drop_table("generated_letters")