"""
SQLAlchemy ORM models for Good Faith Letter persistence.

This module defines the database tables for storing generated letters
with full audit trail and case isolation.
"""

from sqlalchemy import (
    Column,
    String,
    DateTime,
    Text,
    Integer,
    ForeignKey,
    JSON,
    Index,
    CheckConstraint,
)
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func
import uuid
from src.database.connection import Base


class GeneratedLetterDB(Base):
    """
    Database model for generated Good Faith letters.

    Stores letter content and metadata with case isolation.
    """

    __tablename__ = "generated_letters"

    id = Column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    report_id = Column(String(36), nullable=False, index=True)
    case_name = Column(String(255), nullable=False, index=True)
    jurisdiction = Column(String(50), nullable=False)
    content = Column(Text, nullable=False)
    status = Column(String(20), nullable=False, default="draft", index=True)
    version = Column(Integer, nullable=False, default=1)
    agent_execution_id = Column(String(255))
    letter_metadata = Column("metadata", JSON, default=dict)

    # Timestamps
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())

    # Approval tracking
    approved_by = Column(String(255))
    approved_at = Column(DateTime(timezone=True))

    # Relationships
    edits = relationship(
        "LetterEditDB", back_populates="letter", cascade="all, delete-orphan"
    )

    # Indexes for performance
    __table_args__ = (
        Index("idx_letters_case_report", "case_name", "report_id"),
        Index("idx_letters_status_case", "status", "case_name"),
        CheckConstraint(
            "status IN ('draft', 'review', 'approved', 'finalized')",
            name="check_letter_status",
        ),
        CheckConstraint(
            "jurisdiction IN ('federal', 'state')", name="check_jurisdiction"
        ),
        CheckConstraint("version >= 1", name="check_version_positive"),
    )


class LetterEditDB(Base):
    """
    Database model for letter edit history.

    Tracks all changes made to letters for audit trail.
    """

    __tablename__ = "letter_edits"

    id = Column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    letter_id = Column(
        String(36), ForeignKey("generated_letters.id"), nullable=False, index=True
    )
    section_name = Column(String(100), nullable=False)
    original_content = Column(Text)
    new_content = Column(Text, nullable=False)
    editor_id = Column(String(255), nullable=False)
    editor_notes = Column(Text)
    edited_at = Column(DateTime(timezone=True), server_default=func.now())

    # Relationships
    letter = relationship("GeneratedLetterDB", back_populates="edits")

    # Index for audit queries
    __table_args__ = (Index("idx_edits_letter_timestamp", "letter_id", "edited_at"),)
