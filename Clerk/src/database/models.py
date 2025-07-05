"""
SQLAlchemy ORM models for the Clerk Legal AI System.

These models replicate the existing Supabase schema while adding
JWT authentication support.
"""
from sqlalchemy import Column, String, DateTime, Boolean, ForeignKey, Table, Text, Enum as SQLEnum, Index
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func
from datetime import datetime
import uuid
import enum
from src.database.connection import Base


class PermissionLevel(str, enum.Enum):
    """Permission levels for case access."""
    READ = "read"
    WRITE = "write"
    ADMIN = "admin"


class CaseStatus(str, enum.Enum):
    """Status of a legal case."""
    ACTIVE = "active"
    ARCHIVED = "archived"
    CLOSED = "closed"
    DELETED = "deleted"


# Association table for user-case permissions
user_case_permissions = Table(
    'user_case_permissions',
    Base.metadata,
    Column('id', String(36), primary_key=True, default=lambda: str(uuid.uuid4())),
    Column('user_id', String(36), ForeignKey('users.id', ondelete='CASCADE'), nullable=False),
    Column('case_id', String(36), ForeignKey('cases.id', ondelete='CASCADE'), nullable=False),
    Column('permission_level', SQLEnum(PermissionLevel), nullable=False),
    Column('granted_at', DateTime(timezone=True), server_default=func.now()),
    Column('granted_by', String(36), ForeignKey('users.id'), nullable=True),
    Column('expires_at', DateTime(timezone=True), nullable=True),
    Column('created_at', DateTime(timezone=True), server_default=func.now()),
    Column('updated_at', DateTime(timezone=True), onupdate=func.now()),
    Index('idx_user_case_permissions_user_id', 'user_id'),
    Index('idx_user_case_permissions_case_id', 'case_id'),
    Index('idx_user_case_permissions_user_case', 'user_id', 'case_id', unique=True),
)


class LawFirm(Base):
    """Law firm organization model."""
    __tablename__ = 'law_firms'
    
    id = Column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    name = Column(String(255), nullable=False, unique=True)
    domain = Column(String(255), nullable=True)
    is_active = Column(Boolean, default=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())
    
    # Relationships
    users = relationship("User", back_populates="law_firm", cascade="all, delete-orphan")
    cases = relationship("Case", back_populates="law_firm", cascade="all, delete-orphan")
    
    __table_args__ = (
        Index('idx_law_firms_name', 'name'),
        Index('idx_law_firms_domain', 'domain'),
    )


class User(Base):
    """User account model with JWT authentication support."""
    __tablename__ = 'users'
    
    id = Column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    email = Column(String(255), nullable=False, unique=True)
    password_hash = Column(String(255), nullable=False)  # New for JWT auth
    name = Column(String(255), nullable=False)
    law_firm_id = Column(String(36), ForeignKey('law_firms.id', ondelete='CASCADE'), nullable=False)
    is_active = Column(Boolean, default=True)
    is_admin = Column(Boolean, default=False)
    last_login = Column(DateTime(timezone=True), nullable=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())
    
    # Relationships
    law_firm = relationship("LawFirm", back_populates="users")
    created_cases = relationship("Case", foreign_keys="Case.created_by", back_populates="creator")
    case_permissions = relationship(
        "Case",
        secondary=user_case_permissions,
        back_populates="permitted_users",
        overlaps="permissions",
        primaryjoin="User.id==user_case_permissions.c.user_id",
        secondaryjoin="Case.id==user_case_permissions.c.case_id"
    )
    permissions = relationship(
        "UserCasePermission", 
        foreign_keys="UserCasePermission.user_id",
        back_populates="user", 
        cascade="all, delete-orphan"
    )
    granted_permissions = relationship(
        "UserCasePermission",
        foreign_keys="UserCasePermission.granted_by",
        back_populates="granter"
    )
    
    __table_args__ = (
        Index('idx_users_email', 'email'),
        Index('idx_users_law_firm_id', 'law_firm_id'),
    )


class Case(Base):
    """Legal case model."""
    __tablename__ = 'cases'
    
    id = Column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    name = Column(String(100), nullable=False)
    collection_name = Column(String(100), nullable=False, unique=True)
    description = Column(Text, nullable=True)
    law_firm_id = Column(String(36), ForeignKey('law_firms.id', ondelete='CASCADE'), nullable=False)
    status = Column(SQLEnum(CaseStatus), default=CaseStatus.ACTIVE, nullable=False)
    created_by = Column(String(36), ForeignKey('users.id'), nullable=False)
    case_metadata = Column(Text, nullable=True)  # JSON stored as text
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())
    
    # Relationships
    law_firm = relationship("LawFirm", back_populates="cases")
    creator = relationship("User", foreign_keys=[created_by], back_populates="created_cases")
    permitted_users = relationship(
        "User",
        secondary=user_case_permissions,
        back_populates="case_permissions",
        overlaps="permissions",
        primaryjoin="Case.id==user_case_permissions.c.case_id",
        secondaryjoin="User.id==user_case_permissions.c.user_id"
    )
    permissions = relationship("UserCasePermission", back_populates="case", cascade="all, delete-orphan")
    
    __table_args__ = (
        Index('idx_cases_name', 'name'),
        Index('idx_cases_collection_name', 'collection_name'),
        Index('idx_cases_law_firm_id', 'law_firm_id'),
        Index('idx_cases_status', 'status'),
        Index('idx_cases_created_by', 'created_by'),
    )


class UserCasePermission(Base):
    """User permissions for cases (direct ORM model for association table)."""
    __tablename__ = 'user_case_permissions_orm'
    
    id = Column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    user_id = Column(String(36), ForeignKey('users.id', ondelete='CASCADE'), nullable=False)
    case_id = Column(String(36), ForeignKey('cases.id', ondelete='CASCADE'), nullable=False)
    permission_level = Column(SQLEnum(PermissionLevel), nullable=False)
    granted_at = Column(DateTime(timezone=True), server_default=func.now())
    granted_by = Column(String(36), ForeignKey('users.id'), nullable=True)
    expires_at = Column(DateTime(timezone=True), nullable=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())
    
    # Relationships
    user = relationship("User", foreign_keys=[user_id], back_populates="permissions")
    case = relationship("Case", back_populates="permissions")
    granter = relationship("User", foreign_keys=[granted_by], back_populates="granted_permissions")
    
    __table_args__ = (
        Index('idx_user_case_perm_user_id', 'user_id'),
        Index('idx_user_case_perm_case_id', 'case_id'),
        Index('idx_user_case_perm_user_case', 'user_id', 'case_id', unique=True),
    )


class RefreshToken(Base):
    """JWT refresh tokens for session management."""
    __tablename__ = 'refresh_tokens'
    
    id = Column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    user_id = Column(String(36), ForeignKey('users.id', ondelete='CASCADE'), nullable=False)
    token = Column(String(500), nullable=False, unique=True)
    expires_at = Column(DateTime(timezone=True), nullable=False)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    revoked_at = Column(DateTime(timezone=True), nullable=True)
    
    # Relationships
    user = relationship("User")
    
    __table_args__ = (
        Index('idx_refresh_tokens_token', 'token'),
        Index('idx_refresh_tokens_user_id', 'user_id'),
        Index('idx_refresh_tokens_expires_at', 'expires_at'),
    )