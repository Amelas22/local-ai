"""Add default value to updated_at columns

Revision ID: 003_add_default_updated_at
Revises: 002_add_password_hash
Create Date: 2025-01-06

"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.sql import func


# revision identifiers, used by Alembic.
revision = '003_add_default_updated_at'
down_revision = '002_add_password_hash'
branch_labels = None
depends_on = None


def upgrade():
    """Add server_default=func.now() to all updated_at columns."""
    # Update law_firms table
    op.alter_column('law_firms', 'updated_at',
                    existing_type=sa.DateTime(timezone=True),
                    server_default=func.now(),
                    existing_nullable=True)
    
    # Update users table
    op.alter_column('users', 'updated_at',
                    existing_type=sa.DateTime(timezone=True),
                    server_default=func.now(),
                    existing_nullable=True)
    
    # Update cases table
    op.alter_column('cases', 'updated_at',
                    existing_type=sa.DateTime(timezone=True),
                    server_default=func.now(),
                    existing_nullable=True)
    
    # Update user_case_permissions table
    op.alter_column('user_case_permissions', 'updated_at',
                    existing_type=sa.DateTime(timezone=True),
                    server_default=func.now(),
                    existing_nullable=True)
    
    # Update user_case_permissions_orm table
    op.alter_column('user_case_permissions_orm', 'updated_at',
                    existing_type=sa.DateTime(timezone=True),
                    server_default=func.now(),
                    existing_nullable=True)
    
    # Update refresh_tokens table doesn't have updated_at, so we skip it
    
    # Set updated_at to created_at for existing rows where updated_at is NULL
    op.execute("""
        UPDATE law_firms SET updated_at = created_at WHERE updated_at IS NULL;
        UPDATE users SET updated_at = created_at WHERE updated_at IS NULL;
        UPDATE cases SET updated_at = created_at WHERE updated_at IS NULL;
        UPDATE user_case_permissions SET updated_at = created_at WHERE updated_at IS NULL;
        UPDATE user_case_permissions_orm SET updated_at = created_at WHERE updated_at IS NULL;
    """)


def downgrade():
    """Remove server_default from updated_at columns."""
    # Remove server_default from all tables
    op.alter_column('law_firms', 'updated_at',
                    existing_type=sa.DateTime(timezone=True),
                    server_default=None,
                    existing_nullable=True)
    
    op.alter_column('users', 'updated_at',
                    existing_type=sa.DateTime(timezone=True),
                    server_default=None,
                    existing_nullable=True)
    
    op.alter_column('cases', 'updated_at',
                    existing_type=sa.DateTime(timezone=True),
                    server_default=None,
                    existing_nullable=True)
    
    op.alter_column('user_case_permissions', 'updated_at',
                    existing_type=sa.DateTime(timezone=True),
                    server_default=None,
                    existing_nullable=True)
    
    op.alter_column('user_case_permissions_orm', 'updated_at',
                    existing_type=sa.DateTime(timezone=True),
                    server_default=None,
                    existing_nullable=True)