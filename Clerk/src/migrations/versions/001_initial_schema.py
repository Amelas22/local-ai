"""
Initial migration - Create authentication and case management schema.

Revision ID: 001_initial_schema
Revises:
Create Date: 2024-01-01 00:00:00.000000

"""

from typing import Sequence, Union
from alembic import op
import sqlalchemy as sa

# revision identifiers
revision: str = "001_initial_schema"
down_revision: Union[str, None] = None
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Create initial database schema."""

    # Create law_firms table
    op.create_table(
        "law_firms",
        sa.Column("id", sa.String(length=36), nullable=False),
        sa.Column("name", sa.String(length=255), nullable=False),
        sa.Column("domain", sa.String(length=255), nullable=True),
        sa.Column("is_active", sa.Boolean(), nullable=True, server_default="true"),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=True,
        ),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=True),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("name"),
    )
    op.create_index("idx_law_firms_domain", "law_firms", ["domain"], unique=False)
    op.create_index("idx_law_firms_name", "law_firms", ["name"], unique=False)

    # Create users table
    op.create_table(
        "users",
        sa.Column("id", sa.String(length=36), nullable=False),
        sa.Column("email", sa.String(length=255), nullable=False),
        sa.Column("password_hash", sa.String(length=255), nullable=False),
        sa.Column("name", sa.String(length=255), nullable=False),
        sa.Column("law_firm_id", sa.String(length=36), nullable=False),
        sa.Column("is_active", sa.Boolean(), nullable=True, server_default="true"),
        sa.Column("is_admin", sa.Boolean(), nullable=True, server_default="false"),
        sa.Column("last_login", sa.DateTime(timezone=True), nullable=True),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=True,
        ),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=True),
        sa.ForeignKeyConstraint(["law_firm_id"], ["law_firms.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("email"),
    )
    op.create_index("idx_users_email", "users", ["email"], unique=False)
    op.create_index("idx_users_law_firm_id", "users", ["law_firm_id"], unique=False)

    # Create cases table
    op.create_table(
        "cases",
        sa.Column("id", sa.String(length=36), nullable=False),
        sa.Column("name", sa.String(length=100), nullable=False),
        sa.Column("collection_name", sa.String(length=100), nullable=False),
        sa.Column("description", sa.Text(), nullable=True),
        sa.Column("law_firm_id", sa.String(length=36), nullable=False),
        sa.Column(
            "status",
            sa.Enum("active", "archived", "closed", "deleted", name="casestatus"),
            nullable=False,
            server_default="active",
        ),
        sa.Column("created_by", sa.String(length=36), nullable=False),
        sa.Column("case_metadata", sa.Text(), nullable=True),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=True,
        ),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=True),
        sa.ForeignKeyConstraint(
            ["created_by"],
            ["users.id"],
        ),
        sa.ForeignKeyConstraint(["law_firm_id"], ["law_firms.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("collection_name"),
    )
    op.create_index(
        "idx_cases_collection_name", "cases", ["collection_name"], unique=False
    )
    op.create_index("idx_cases_created_by", "cases", ["created_by"], unique=False)
    op.create_index("idx_cases_law_firm_id", "cases", ["law_firm_id"], unique=False)
    op.create_index("idx_cases_name", "cases", ["name"], unique=False)
    op.create_index("idx_cases_status", "cases", ["status"], unique=False)

    # Create user_case_permissions table
    op.create_table(
        "user_case_permissions",
        sa.Column("id", sa.String(length=36), nullable=False),
        sa.Column("user_id", sa.String(length=36), nullable=False),
        sa.Column("case_id", sa.String(length=36), nullable=False),
        sa.Column(
            "permission_level",
            sa.Enum("read", "write", "admin", name="permissionlevel"),
            nullable=False,
        ),
        sa.Column(
            "granted_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=True,
        ),
        sa.Column("granted_by", sa.String(length=36), nullable=True),
        sa.Column("expires_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=True,
        ),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=True),
        sa.ForeignKeyConstraint(["case_id"], ["cases.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(
            ["granted_by"],
            ["users.id"],
        ),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(
        "idx_user_case_permissions_case_id",
        "user_case_permissions",
        ["case_id"],
        unique=False,
    )
    op.create_index(
        "idx_user_case_permissions_user_case",
        "user_case_permissions",
        ["user_id", "case_id"],
        unique=True,
    )
    op.create_index(
        "idx_user_case_permissions_user_id",
        "user_case_permissions",
        ["user_id"],
        unique=False,
    )

    # Create user_case_permissions_orm table (duplicate for ORM compatibility)
    op.create_table(
        "user_case_permissions_orm",
        sa.Column("id", sa.String(length=36), nullable=False),
        sa.Column("user_id", sa.String(length=36), nullable=False),
        sa.Column("case_id", sa.String(length=36), nullable=False),
        sa.Column(
            "permission_level",
            sa.Enum("read", "write", "admin", name="permissionlevel"),
            nullable=False,
        ),
        sa.Column(
            "granted_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=True,
        ),
        sa.Column("granted_by", sa.String(length=36), nullable=True),
        sa.Column("expires_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=True,
        ),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=True),
        sa.ForeignKeyConstraint(["case_id"], ["cases.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(
            ["granted_by"],
            ["users.id"],
        ),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(
        "idx_user_case_perm_case_id",
        "user_case_permissions_orm",
        ["case_id"],
        unique=False,
    )
    op.create_index(
        "idx_user_case_perm_user_case",
        "user_case_permissions_orm",
        ["user_id", "case_id"],
        unique=True,
    )
    op.create_index(
        "idx_user_case_perm_user_id",
        "user_case_permissions_orm",
        ["user_id"],
        unique=False,
    )

    # Create refresh_tokens table
    op.create_table(
        "refresh_tokens",
        sa.Column("id", sa.String(length=36), nullable=False),
        sa.Column("user_id", sa.String(length=36), nullable=False),
        sa.Column("token", sa.String(length=500), nullable=False),
        sa.Column("expires_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=True,
        ),
        sa.Column("revoked_at", sa.DateTime(timezone=True), nullable=True),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("token"),
    )
    op.create_index(
        "idx_refresh_tokens_expires_at", "refresh_tokens", ["expires_at"], unique=False
    )
    op.create_index(
        "idx_refresh_tokens_token", "refresh_tokens", ["token"], unique=False
    )
    op.create_index(
        "idx_refresh_tokens_user_id", "refresh_tokens", ["user_id"], unique=False
    )

    # Create a view for user active cases (similar to Supabase RLS)
    op.execute("""
        CREATE OR REPLACE VIEW user_active_cases AS
        SELECT c.*
        FROM cases c
        INNER JOIN user_case_permissions ucp ON c.id = ucp.case_id
        WHERE c.status != 'deleted'
        AND (ucp.expires_at IS NULL OR ucp.expires_at > NOW());
    """)


def downgrade() -> None:
    """Drop all tables and enums."""

    # Drop view
    op.execute("DROP VIEW IF EXISTS user_active_cases")

    # Drop tables
    op.drop_table("refresh_tokens")
    op.drop_table("user_case_permissions_orm")
    op.drop_table("user_case_permissions")
    op.drop_table("cases")
    op.drop_table("users")
    op.drop_table("law_firms")

    # Drop enums
    op.execute("DROP TYPE IF EXISTS casestatus")
    op.execute("DROP TYPE IF EXISTS permissionlevel")
