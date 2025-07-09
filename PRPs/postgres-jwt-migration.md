name: "PostgreSQL + JWT Migration for Clerk Legal AI"
description: |

## Purpose
Migrate Clerk Legal AI System from Supabase to direct PostgreSQL + JWT authentication, replacing all Supabase dependencies with a custom authentication and case management solution while maintaining existing patterns and functionality.

## Core Principles
1. **Context is King**: Include ALL necessary documentation, examples, and caveats
2. **Validation Loops**: Provide executable tests/lints the AI can run and fix
3. **Information Dense**: Use keywords and patterns from the codebase
4. **Progressive Success**: Start simple, validate, then enhance
5. **Global rules**: Be sure to follow all rules in CLAUDE.md

---

## Goal
Replace Supabase authentication and case management with a direct PostgreSQL + JWT solution for the Clerk Legal AI System, maintaining all existing functionality while gaining complete control over the authentication system and reducing external dependencies.

## Why
- **External Dependencies Issues**: Current Supabase integration is causing problems with case management
- **Complete Control**: Need full ownership of authentication and user management
- **Cost Optimization**: Eliminate Supabase subscription costs while utilizing existing PostgreSQL infrastructure
- **Custom Requirements**: Ability to implement specific legal industry authentication requirements
- **Case Isolation**: Better control over case-level security and data isolation

## What
Build a complete authentication and case management system that:
- Replaces Supabase Auth with JWT-based authentication
- Implements user, law firm, and case management in PostgreSQL
- Maintains existing API compatibility for minimal frontend changes
- Preserves case isolation and permission system
- Integrates with existing middleware patterns

### Success Criteria
- [ ] All Supabase dependencies removed from Clerk backend
- [ ] JWT authentication working with secure token management
- [ ] Case management fully functional with PostgreSQL
- [ ] All existing API endpoints maintain compatibility
- [ ] Tests passing with new implementation
- [ ] Frontend authentication updated to use new system

## All Needed Context

### Documentation & References
```yaml
- url: https://fastapi.tiangolo.com/tutorial/security/oauth2-jwt/
  why: FastAPI JWT implementation patterns for OAuth2 flow

- url: https://docs.sqlalchemy.org/en/14/orm/extensions/asyncio.html
  why: AsyncIO patterns for PostgreSQL connections in FastAPI

- url: https://python-jose.readthedocs.io/en/latest/
  why: JWT token encoding/decoding implementation

- url: https://passlib.readthedocs.io/en/stable/
  why: Secure password hashing with bcrypt

- url: https://alembic.sqlalchemy.org/en/latest/tutorial.html
  why: Database migration patterns for SQLAlchemy

- file: src/services/case_manager.py
  why: Current case management patterns to maintain compatibility

- file: src/middleware/case_context.py
  why: Middleware patterns for case validation

- file: src/models/case_models.py
  why: Existing data models to replicate in SQLAlchemy

- file: main.py
  why: API endpoint patterns and middleware integration

- file: docker-compose.yml
  why: PostgreSQL configuration already available

- docfile: SUPABASE_ALTERNATIVES_REPORT.md
  why: Complete migration examples and patterns
```

### Current Codebase tree
```bash
Clerk/
    main.py                             # FastAPI entry point
    src/
        services/
            case_manager.py             # Supabase-based case management
        middleware/
            case_context.py             # Case validation middleware
        models/
            case_models.py              # Pydantic models for cases
        vector_storage/
            qdrant_store.py             # Vector storage with case isolation
        config/
            shared_resources.py         # Shared resource management
        utils/
            logger.py                   # Logging utilities
    frontend/
        src/
            services/
                auth.service.ts         # Supabase auth client
                auth.service.dev.ts     # Dev auth service
            features/
                auth/
                    authSlice.ts        # Redux auth state
    supabase/
        migrations/
            001_case_management.sql     # Current DB schema
```

### Desired Codebase tree with files to be added
```bash
Clerk/
    main.py                             # FastAPI entry point (modified)
    src/
        database/
            connection.py               # NEW: PostgreSQL connection management
            models.py                   # NEW: SQLAlchemy ORM models
        services/
            auth_service.py             # NEW: JWT authentication service
            case_service.py             # NEW: PostgreSQL case management
            user_service.py             # NEW: User management service
            case_manager.py             # MODIFIED: Adapter for compatibility
        middleware/
            auth_middleware.py          # NEW: JWT validation middleware
            case_context.py             # MODIFIED: Work with new auth
        api/
            auth_endpoints.py           # NEW: Authentication endpoints
            case_endpoints.py           # NEW: Case management endpoints
            user_endpoints.py           # NEW: User management endpoints
        models/
            auth_models.py              # NEW: SQLAlchemy models
            case_models.py              # MODIFIED: Add SQLAlchemy support
        schemas/
            auth_schemas.py             # NEW: Pydantic schemas for auth
            case_schemas.py             # NEW: Pydantic schemas for cases
            user_schemas.py             # NEW: Pydantic schemas for users
        migrations/
            alembic.ini                 # NEW: Alembic configuration
            env.py                      # NEW: Alembic environment
            versions/
                001_initial_schema.py   # NEW: Initial migration
        tests/
            test_auth_service.py        # NEW: Auth service tests
            test_case_service.py        # NEW: Case service tests
            test_auth_endpoints.py      # NEW: Auth endpoint tests
    init_db.py                          # NEW: Database initialization script
    requirements.txt                    # MODIFIED: Add new dependencies
```

### Known Gotchas & Library Quirks
```python
# CRITICAL: SQLAlchemy async requires special session handling
# Always use async with statement for sessions
async with AsyncSessionLocal() as session:
    # operations here
    
# CRITICAL: FastAPI OAuth2PasswordBearer expects specific token format
# Must return {"access_token": token, "token_type": "bearer"}

# CRITICAL: python-jose requires cryptography backend
# Install with: python-jose[cryptography]

# CRITICAL: Case name to collection name conversion must match existing logic
# See generate_collection_name in case_manager.py

# CRITICAL: Maintain existing permission levels: read, write, admin
# Don't change permission names or frontend breaks

# CRITICAL: X-Case-ID header must continue to work
# Frontend expects this header for case context

# CRITICAL: PostgreSQL already running in docker-compose as supabase-db
# Connection string: postgresql://postgres:password@localhost:5432/postgres
```

## Implementation Blueprint

### Data models and structure

```python
# SQLAlchemy models matching existing Supabase schema
from sqlalchemy import Column, String, DateTime, Boolean, ForeignKey, Table, Text, Enum
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import relationship
from datetime import datetime
import uuid
import enum

Base = declarative_base()

class PermissionLevel(str, enum.Enum):
    READ = "read"
    WRITE = "write"
    ADMIN = "admin"

class CaseStatus(str, enum.Enum):
    ACTIVE = "active"
    ARCHIVED = "archived"
    DELETED = "deleted"

# Association table matching Supabase schema
user_case_permissions = Table('user_case_permissions', Base.metadata,
    Column('id', String, primary_key=True, default=lambda: str(uuid.uuid4())),
    Column('user_id', String, ForeignKey('users.id')),
    Column('case_id', String, ForeignKey('cases.id')),
    Column('permission_level', Enum(PermissionLevel)),
    Column('granted_at', DateTime, default=datetime.utcnow),
    Column('granted_by', String, ForeignKey('users.id')),
    Column('expires_at', DateTime, nullable=True)
)

# Pydantic schemas for API compatibility
from pydantic import BaseModel, Field, validator
from typing import Optional, List
from datetime import datetime

class CaseCreate(BaseModel):
    """Matches existing API schema"""
    name: str = Field(..., min_length=1, max_length=50)
    description: Optional[str] = None
    
class UserLogin(BaseModel):
    """OAuth2 compatible login schema"""
    username: str  # Email in OAuth2PasswordRequestForm
    password: str
    
class Token(BaseModel):
    """JWT token response"""
    access_token: str
    refresh_token: str
    token_type: str = "bearer"
```

### List of tasks to be completed in order

```yaml
Task 1: Set up database connection and models
CREATE src/database/connection.py:
  - PATTERN from: config/settings.py for environment variables
  - USE: asyncpg connection string from docker-compose PostgreSQL
  - IMPLEMENT: AsyncSession factory with proper cleanup

CREATE src/database/models.py:
  - COPY schema from: supabase/migrations/001_case_management.sql
  - CONVERT to SQLAlchemy ORM models
  - PRESERVE all column names and relationships

Task 2: Implement authentication service
CREATE src/services/auth_service.py:
  - PATTERN from: Example in SUPABASE_ALTERNATIVES_REPORT.md
  - USE: passlib for password hashing
  - USE: python-jose for JWT tokens
  - IMPLEMENT: Token creation and validation methods

Task 3: Create authentication endpoints
CREATE src/api/auth_endpoints.py:
  - PATTERN from: main.py router patterns
  - IMPLEMENT: /api/auth/register endpoint
  - IMPLEMENT: /api/auth/login endpoint
  - IMPLEMENT: /api/auth/refresh endpoint
  - USE: OAuth2PasswordRequestForm for login

Task 4: Implement authentication middleware
CREATE src/middleware/auth_middleware.py:
  - PATTERN from: src/middleware/case_context.py
  - VALIDATE: JWT tokens from Authorization header
  - INJECT: user info into request.state
  - HANDLE: Token expiration gracefully

Task 5: Implement case service
CREATE src/services/case_service.py:
  - PATTERN from: src/services/case_manager.py methods
  - PRESERVE: generate_collection_name logic exactly
  - IMPLEMENT: All CRUD operations with PostgreSQL
  - MAINTAIN: Permission validation logic

Task 6: Create case endpoints
CREATE src/api/case_endpoints.py:
  - MOVE endpoints from: main.py
  - PRESERVE: Exact API signatures
  - USE: New case service instead of case_manager
  - MAINTAIN: X-Case-ID header support

Task 7: Update case context middleware
MODIFY src/middleware/case_context.py:
  - FIND: Supabase client usage
  - REPLACE with: PostgreSQL case service calls
  - PRESERVE: get_case_context and require_case_context signatures
  - MAINTAIN: Permission checking logic

Task 8: Create database migrations
CREATE src/migrations/alembic.ini:
  - PATTERN from: Standard Alembic configuration
  - SET: Database URL from environment

CREATE src/migrations/env.py:
  - IMPORT: All models from src/database/models.py
  - CONFIGURE: Async migrations support

CREATE src/migrations/versions/001_initial_schema.py:
  - CONVERT: supabase/migrations/001_case_management.sql
  - PRESERVE: All indexes and constraints
  - ADD: JWT-specific tables if needed

Task 9: Update main.py
MODIFY main.py:
  - ADD: Authentication middleware to app
  - INCLUDE: New auth and case routers
  - PRESERVE: All other endpoints and middleware
  - MAINTAIN: Startup/shutdown events

Task 10: Create compatibility adapter
MODIFY src/services/case_manager.py:
  - CONVERT to: Adapter pattern calling new services
  - PRESERVE: All public method signatures
  - MAINTAIN: Backward compatibility for existing code

Task 11: Add comprehensive tests
CREATE src/tests/test_auth_service.py:
  - PATTERN from: src/services/tests/test_case_manager.py
  - TEST: Token creation and validation
  - TEST: Password hashing and verification
  - USE: pytest fixtures for test data

CREATE src/tests/test_case_service.py:
  - MIRROR: All tests from test_case_manager.py
  - ADAPT for: PostgreSQL instead of Supabase
  - MAINTAIN: Same test coverage

Task 12: Update frontend authentication
MODIFY frontend/src/services/auth.service.ts:
  - REPLACE: Supabase client with axios
  - IMPLEMENT: JWT token storage and refresh
  - MAINTAIN: Same public API for components

Task 13: Initialize database
CREATE init_db.py:
  - CREATE all tables using SQLAlchemy
  - SEED: Initial admin user
  - SEED: Shared resources configuration
  - RUN: Alembic migrations

Task 14: Update requirements and environment
MODIFY requirements.txt:
  - ADD: sqlalchemy[asyncio]>=2.0.0
  - ADD: asyncpg>=0.29.0
  - ADD: python-jose[cryptography]>=3.3.0
  - ADD: passlib[bcrypt]>=1.7.4
  - ADD: python-multipart>=0.0.6
  - ADD: alembic>=1.13.0
  - REMOVE: supabase>=2.0.0

MODIFY .env.example:
  - ADD: JWT_SECRET_KEY
  - ADD: JWT_ALGORITHM=HS256
  - ADD: ACCESS_TOKEN_EXPIRE_MINUTES=30
  - UPDATE: DATABASE_URL for PostgreSQL
```

### Integration Points
```yaml
DATABASE:
  - migration: "Convert Supabase schema to PostgreSQL/SQLAlchemy"
  - connection: "Use existing PostgreSQL from docker-compose"
  - pooling: "AsyncSession with connection pooling"
  
CONFIG:
  - add to: config/settings.py
  - pattern: "JWT_SECRET_KEY = os.getenv('JWT_SECRET_KEY', 'dev-secret-key')"
  - pattern: "DATABASE_URL = os.getenv('DATABASE_URL', 'postgresql+asyncpg://...')"
  
MIDDLEWARE:
  - add to: main.py
  - pattern: "app.add_middleware(AuthMiddleware)"
  - before: "app.add_middleware(CaseContextMiddleware)"
  
ROUTES:
  - add to: main.py  
  - pattern: "app.include_router(auth_router, prefix='/api/auth')"
  - pattern: "app.include_router(case_router, prefix='/api/cases')"
```

## Validation Loop

### Level 1: Syntax & Style
```bash
# Run these FIRST - fix any errors before proceeding
cd /mnt/c/Users/jlemr/Test2/local-ai-package/Clerk
ruff check src/ --fix        # Auto-fix style issues
ruff format src/             # Format code
mypy src/ --ignore-missing-imports  # Type checking

# Expected: No errors. If errors, READ and fix them.
```

### Level 2: Database Tests
```bash
# Test database connection and models
python -m pytest src/tests/test_database_connection.py -v
python -m pytest src/tests/test_models.py -v

# Test migrations
alembic upgrade head         # Apply migrations
alembic downgrade -1         # Test rollback
alembic upgrade head         # Re-apply

# Expected: All migrations apply cleanly
```

### Level 3: Unit Tests
```python
# Test authentication service
async def test_password_hashing():
    """Password hashing works correctly"""
    password = "test_password_123"
    hashed = AuthService.hash_password(password)
    assert AuthService.verify_password(password, hashed)
    assert not AuthService.verify_password("wrong_password", hashed)

async def test_jwt_token_creation():
    """JWT tokens are created with correct claims"""
    user_data = {"sub": "user-123", "law_firm_id": "firm-123"}
    token = AuthService.create_access_token(user_data)
    decoded = AuthService.decode_token(token)
    assert decoded["sub"] == "user-123"
    assert decoded["law_firm_id"] == "firm-123"

async def test_case_isolation():
    """Cases are properly isolated by law firm"""
    # Create cases for different law firms
    case1 = await case_service.create_case(db, CaseCreate(name="Case 1"), user_firm1)
    case2 = await case_service.create_case(db, CaseCreate(name="Case 2"), user_firm2)
    
    # Verify isolation
    firm1_cases = await case_service.get_user_cases(db, user_firm1.id)
    assert len(firm1_cases) == 1
    assert firm1_cases[0].id == case1.id
```

```bash
# Run unit tests
python -m pytest src/tests/ -v --asyncio-mode=auto

# Expected: All tests pass
```

### Level 4: Integration Tests
```bash
# Start the service
python main.py

# Test authentication flow
curl -X POST http://localhost:8000/api/auth/register \
  -H "Content-Type: application/json" \
  -d '{"email": "test@example.com", "password": "secure_password", "name": "Test User", "law_firm_id": "firm-123"}'

# Expected: {"id": "...", "email": "test@example.com", ...}

# Test login
curl -X POST http://localhost:8000/api/auth/login \
  -H "Content-Type: application/x-www-form-urlencoded" \
  -d "username=test@example.com&password=secure_password"

# Expected: {"access_token": "...", "refresh_token": "...", "token_type": "bearer"}

# Test case creation with token
TOKEN="<access_token_from_login>"
curl -X POST http://localhost:8000/api/cases \
  -H "Authorization: Bearer $TOKEN" \
  -H "Content-Type: application/json" \
  -d '{"name": "Test Case 2024"}'

# Expected: {"id": "...", "name": "Test Case 2024", ...}
```

### Level 5: Compatibility Tests
```bash
# Test that existing code still works
python -m pytest tests/test_case_isolation.py -v
python -m pytest tests/test_api_integration.py -v

# Test vector storage with new case management
python test_discovery_processing.py

# Expected: All existing tests pass without modification
```

## Final Validation Checklist
- [ ] All tests pass: `python -m pytest tests/ -v`
- [ ] No linting errors: `ruff check src/`
- [ ] No type errors: `mypy src/`
- [ ] Authentication endpoints working
- [ ] Case management maintains isolation
- [ ] Frontend can login and access cases
- [ ] X-Case-ID header still works
- [ ] Existing API endpoints unchanged
- [ ] Performance comparable to Supabase
- [ ] No Supabase imports remain in Clerk code

---

## Anti-Patterns to Avoid
- ❌ Don't change existing API contracts - maintain compatibility
- ❌ Don't skip permission checks - security is critical
- ❌ Don't use synchronous database calls in async context
- ❌ Don't store passwords in plain text - always hash
- ❌ Don't expose internal IDs - use UUIDs
- ❌ Don't break case isolation - every query needs case_name filter
- ❌ Don't hardcode secrets - use environment variables
- ❌ Don't ignore failing tests - fix them properly

## Migration Rollback Plan
If issues arise during migration:
1. Keep Supabase credentials in separate env file
2. Maintain adapter pattern in case_manager.py
3. Use feature flags to switch between implementations
4. Test thoroughly in staging before production

## Security Considerations
- JWT secret must be strong (32+ characters) and unique per environment
- Enable HTTPS-only cookies in production
- Implement token refresh before expiration
- Add rate limiting to auth endpoints
- Log all authentication attempts
- Implement account lockout after failed attempts
- Use secure password requirements

## Performance Optimization
- Connection pooling with AsyncSession
- Prepared statements for common queries
- Index on email, case_id, and user_id columns
- Cache user permissions in Redis if needed
- Batch operations where possible

## Confidence Score: 9/10
High confidence due to:
- Clear examples in SUPABASE_ALTERNATIVES_REPORT.md
- Existing patterns in codebase to follow
- Standard libraries with good documentation
- PostgreSQL already configured in docker-compose
- Comprehensive test coverage planned

Minor uncertainty on:
- Exact frontend changes needed (-1 point)