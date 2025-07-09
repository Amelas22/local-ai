"""add password_hash column

Revision ID: 002_add_password_hash
Revises: 001_initial_schema
Create Date: 2025-01-04 20:03:00

"""
from alembic import op
import sqlalchemy as sa

# revision identifiers, used by Alembic.
revision = '002_add_password_hash'
down_revision = '001_initial_schema'
branch_labels = None
depends_on = None


def upgrade() -> None:
    """Add password_hash column to users table."""
    op.add_column('users', sa.Column('password_hash', sa.String(255), nullable=True))
    
    # Set a default password hash for existing users
    # This is a hash of "changeme123" - users should change this on first login
    default_hash = "$2b$12$4fPqXzXfSzXfZ6yxuKjHgOp5xBKXKqDif3U7Jcvq6N3sXXt3NQFHS"
    op.execute(f"UPDATE users SET password_hash = '{default_hash}' WHERE password_hash IS NULL")
    
    # Make the column non-nullable after setting defaults
    op.alter_column('users', 'password_hash', nullable=False)


def downgrade() -> None:
    """Remove password_hash column from users table."""
    op.drop_column('users', 'password_hash')