name: "Case Context Management with Multi-Tenant Data Isolation"
description: |

## Purpose
Implement a centralized case selection system that enforces strict data isolation boundaries and manages database scope across the entire Clerk interface, preparing the architecture for multi-law firm deployment.

## Core Principles
1. **Case Isolation**: Every operation must be isolated by case to prevent data leakage
2. **Global Context**: Case selection propagates throughout the entire interface
3. **Multi-Tenant Ready**: Architecture supports law firm boundaries
4. **Performance**: Optimize for case-specific queries
5. **Security**: Enforce isolation at database and application layers

---

## Goal
Transform Clerk from automatic case name generation via Box folders to a comprehensive case management system with:
- User-controlled case creation
- Strict data isolation per case
- Global case context throughout the interface
- Multi-tenant architecture foundation
- Shared resource management

## Why
- **Data Security**: Prevent cross-case data contamination
- **User Control**: Allow direct case creation without Box dependency
- **Scalability**: Enable multi-law firm SaaS deployment
- **Performance**: Reduce query scope to relevant databases only
- **Compliance**: Create audit trail for all case data access

## What
### User-Visible Behavior
1. Add Case button in sidebar to create new cases
2. Case dropdown shows only user's authorized cases
3. Selected case context visible across all screens
4. Case-specific data automatically scoped
5. Shared legal resources always available

### Technical Requirements
- 50-character case name limit
- Case ID hashing for collection names
- Database-level isolation per case
- Middleware case validation
- Audit logging for access
- WebSocket case filtering

### Success Criteria
- [ ] Users can create cases without Box folders
- [ ] Case A data never appears in Case B
- [ ] All components inherit global case context
- [ ] Shared resources remain globally accessible
- [ ] Multi-tenant boundaries enforced
- [ ] Performance improved through scoped queries

## All Needed Context

### Documentation & References
```yaml
# MUST READ - Include these in your context window
- url: https://qdrant.tech/documentation/guides/multiple-partitions/
  why: Qdrant multitenancy best practices (payload-based partitioning)
  
- url: https://qdrant.tech/articles/multitenancy/
  why: How to implement multitenancy in Qdrant
  
- url: https://fastapi.tiangolo.com/tutorial/middleware/
  why: FastAPI middleware for case context validation
  
- url: https://mikehuls.com/adding-context-to-each-fastapi-request-using-request-state/
  why: Adding context to FastAPI requests via request.state
  
- url: https://supabase.com/docs/guides/database/tables
  why: Creating Supabase tables for case management
  
- file: /mnt/c/Users/jlemr/Test2/local-ai-package/Clerk/src/vector_storage/qdrant_store.py
  why: Current vector storage implementation with collection-based isolation
  
- file: /mnt/c/Users/jlemr/Test2/local-ai-package/Clerk/frontend/src/context/CaseContext.tsx
  why: Existing frontend case state management
  
- file: /mnt/c/Users/jlemr/Test2/local-ai-package/Clerk/src/utils/logger.py
  why: Existing audit logging patterns (log_case_access function)
  
- file: /mnt/c/Users/jlemr/Test2/local-ai-package/Clerk/src/websocket/socket_server.py
  why: WebSocket case subscription pattern

- file: CLAUDE.md
  why: Project structure and testing requirements

```

### Current Codebase Structure
```bash
Clerk/
    main.py                             # FastAPI app - needs middleware
    src/
        vector_storage/
            qdrant_store.py             # Collection-based isolation
        document_processing/
            box_client.py               # Auto case name generation
        ai_agents/
            fact_extractor.py           # Case-specific collections
        websocket/
            socket_server.py            # Case subscriptions
        models/
            unified_document_models.py  # Has case_name field
        utils/
            logger.py                   # Audit logging functions
    frontend/
        src/
            context/
                CaseContext.tsx         # Global case state
            components/
                common/
                    Sidebar.tsx         # Case dropdown UI
            lib/
                supabase.ts            # Supabase client
```

### Desired Codebase Structure
```bash
Clerk/
    main.py                             # + Case context middleware
    src/
        middleware/
            case_context.py             # NEW: Case validation middleware
        models/
            case_models.py              # NEW: Case data models
        config/
            shared_resources.py         # NEW: Shared resource config
        services/
            case_manager.py             # NEW: Case CRUD operations
        vector_storage/
            qdrant_store.py             # MODIFY: Add database isolation
    frontend/
        src/
            components/
                cases/
                    AddCaseModal.tsx    # NEW: Case creation UI
                    CaseSelector.tsx    # NEW: Enhanced dropdown
            hooks/
                useCaseManagement.ts    # NEW: Case CRUD hooks
    supabase/
        migrations/
            001_case_management.sql     # NEW: Case tables
```

### Known Gotchas & Library Quirks
```python

# GOTCHA: Qdrant collection names limited to 63 chars
# Solution: Hash long case names, store mapping in Supabase

# CRITICAL: FastAPI middleware runs on EVERY request
# Must be performant - cache case validations

# GOTCHA: React 19 + SocketIO requires specific configuration
# Current implementation in socket_server.py works - don't change core setup

# CRITICAL: Supabase RLS (Row Level Security) needed for multi-tenant
# Enable RLS on all case-related tables

# CRITICAL: No current supabase tables for case management
# Create new tables for case management
```

## Implementation Blueprint

### Data Models and Structure

```python
# src/models/case_models.py
from pydantic import BaseModel, Field, validator
from datetime import datetime
from typing import Optional, Dict, Any
from enum import Enum

class CaseStatus(str, Enum):
    ACTIVE = "active"
    ARCHIVED = "archived"
    CLOSED = "closed"

class Case(BaseModel):
    """Core case model for Supabase storage"""
    id: str = Field(..., description="UUID")
    name: str = Field(..., max_length=50, description="User-friendly case name")
    law_firm_id: str = Field(..., description="Law firm UUID")
    collection_name: str = Field(..., description="Hashed name for Qdrant")
    status: CaseStatus = Field(default=CaseStatus.ACTIVE)
    created_by: str = Field(..., description="User UUID")
    created_at: datetime
    updated_at: datetime
    metadata: Dict[str, Any] = Field(default_factory=dict)
    
    @validator('name')
    def validate_case_name(cls, v):
        """Ensure case name is Qdrant-compatible"""
        if not v or len(v.strip()) == 0:
            raise ValueError("Case name cannot be empty")
        # Additional validation logic
        return v.strip()

class CaseContext(BaseModel):
    """Request-scoped case context"""
    case_id: str
    case_name: str
    law_firm_id: str
    user_id: str
    permissions: list[str] = Field(default_factory=list)

# Supabase table schema
"""
CREATE TABLE cases (
    id UUID DEFAULT gen_random_uuid() PRIMARY KEY,
    name VARCHAR(50) NOT NULL,
    law_firm_id UUID NOT NULL REFERENCES law_firms(id),
    collection_name VARCHAR(63) NOT NULL UNIQUE,
    status VARCHAR(20) DEFAULT 'active',
    created_by UUID NOT NULL REFERENCES users(id),
    created_at TIMESTAMPTZ DEFAULT NOW(),
    updated_at TIMESTAMPTZ DEFAULT NOW(),
    metadata JSONB DEFAULT '{}',
    UNIQUE(law_firm_id, name)
);

CREATE INDEX idx_cases_law_firm ON cases(law_firm_id);
CREATE INDEX idx_cases_status ON cases(status);
"""
```

### List of Tasks

```yaml
Task 1: Create Supabase Case Management Infrastructure
CREATE supabase/migrations/001_case_management.sql:
  - Define cases table with constraints
  - Define user_case_permissions table
  - Define case_audit_log table
  - Enable RLS policies for law firm isolation
  - Create indexes for performance

Task 2: Build Case Management Service
CREATE src/services/case_manager.py:
  - PATTERN from: src/document_processing/box_client.py (for Supabase client usage)
  - Implement create_case() with name validation
  - Implement get_user_cases() with law firm filtering
  - Implement case_name_to_collection() hashing
  - Add case access validation methods

Task 3: Implement Case Context Middleware
CREATE src/middleware/case_context.py:
  - PATTERN from: main.py CORS middleware setup
  - Extract case_id from request headers
  - Validate user has access to case
  - Set request.state.case_context
  - Log access via log_case_access()

MODIFY main.py:
  - Import and add CaseContextMiddleware
  - Add after CORS middleware
  - Ensure WebSocket compatibility

Task 4: Create Frontend Case Management Components
CREATE frontend/src/components/cases/AddCaseModal.tsx:
  - PATTERN from: frontend/src/components/common/Modal.tsx
  - Form with 50-char case name input
  - Validation before submission
  - Call POST /api/cases endpoint
  - Update case list on success

CREATE frontend/src/hooks/useCaseManagement.ts:
  - PATTERN from: frontend/src/hooks/useAuth.ts
  - Implement createCase mutation
  - Implement getCases query with caching
  - Handle optimistic updates

Task 5: Update Case Selection UI
MODIFY frontend/src/components/common/Sidebar.tsx:
  - Add "Add Case" button above dropdown
  - Show AddCaseModal on click
  - Display law firm name in header
  - Make dropdown read-only in other views

MODIFY frontend/src/context/CaseContext.tsx:
  - Add createCase method
  - Add law firm context
  - Propagate case_id in all API calls via headers

Task 6: Implement Shared Resource Configuration
CREATE src/config/shared_resources.py:
  - Define SHARED_COLLECTIONS list
  - Add is_shared_resource() function
  - Configure exclusion from case dropdowns

Task 7: Convert to Database-Level Isolation
MODIFY src/vector_storage/qdrant_store.py:
  - Update __init__ to accept database_name
  - Modify all methods to use database context
  - Ensure backward compatibility
  - Add migration logic for existing collections

Task 8: Update AI Agents for New Pattern
MODIFY src/ai_agents/fact_extractor.py:
  - Use database_name instead of collection prefix
  - Update collection naming pattern
  - Ensure case validation via middleware

Task 9: Add Case Management API Endpoints
MODIFY main.py:
  - POST /api/cases - Create new case
  - GET /api/cases - List user's cases (filtered)
  - PUT /api/cases/{id} - Update case status
  - Add proper error handling

Task 10: Implement Audit Logging
MODIFY src/utils/logger.py:
  - Enhance log_case_access with more details
  - Add case_created, case_archived events
  - Ensure all case operations are logged

Task 11: Update WebSocket for Case Filtering
MODIFY src/websocket/socket_server.py:
  - Filter events by case_id subscription
  - Add case context to all emitted events
  - Validate case access on subscription

Task 12: Create Comprehensive Tests
CREATE src/services/tests/test_case_manager.py:
  - Test case creation with validation
  - Test law firm isolation
  - Test collection name hashing

CREATE src/middleware/tests/test_case_context.py:
  - Test middleware validation
  - Test unauthorized access blocking
  - Test performance with caching
```

### Integration Points
```yaml
DATABASE:
  - migration: "Run 001_case_management.sql via Supabase CLI"
  - RLS: "Enable row-level security on cases table"
  
CONFIG:
  - add to: .env
  - values: |
      SHARED_COLLECTIONS=florida_statutes,fmcsr_regulations
      ENABLE_CASE_ISOLATION=true
      MAX_CASE_NAME_LENGTH=50
  
ROUTES:
  - add to: main.py
  - pattern: |
      from src.routers import case_router
      app.include_router(case_router, prefix="/api/cases", tags=["cases"])

FRONTEND:
  - update: All API calls to include X-Case-ID header
  - pattern: |
      headers: {
        'X-Case-ID': caseContext.activeCaseId,
        ...existingHeaders
      }
```

## Validation Loop

### Level 1: Syntax & Style
```bash
# Backend
cd Clerk
ruff check src/ --fix
mypy src/

# Frontend
cd frontend
npm run lint
npm run type-check

# Expected: No errors
```

### Level 2: Unit Tests
```python
# Test case creation with validation
def test_create_case_valid():
    case = create_case("Smith v Jones 2024", law_firm_id="123")
    assert case.collection_name != case.name  # Should be hashed
    assert len(case.name) <= 50

def test_create_case_too_long():
    with pytest.raises(ValidationError):
        create_case("A" * 51, law_firm_id="123")

# Test middleware isolation
async def test_middleware_blocks_unauthorized():
    request = MockRequest(headers={"X-Case-ID": "unauthorized-case"})
    with pytest.raises(HTTPException) as exc:
        await case_middleware(request, None)
    assert exc.value.status_code == 403

# Test law firm isolation
def test_get_cases_filtered_by_firm():
    cases = get_user_cases(user_id="user1", law_firm_id="firm1")
    assert all(c.law_firm_id == "firm1" for c in cases)
```

```bash
cd Clerk
python -m pytest src/ -v
```

### Level 3: Integration Test
```bash
# Start services
cd Clerk
python main.py

# Test case creation
curl -X POST http://localhost:8000/api/cases \
  -H "Content-Type: application/json" \
  -H "Authorization: Bearer $TOKEN" \
  -d '{"name": "Test Case 2024"}'

# Test case listing
curl http://localhost:8000/api/cases \
  -H "Authorization: Bearer $TOKEN"

# Test with case context
curl http://localhost:8000/api/search \
  -H "X-Case-ID: $CASE_ID" \
  -H "Authorization: Bearer $TOKEN" \
  -d '{"query": "test search"}'

# Expected: Results only from specified case
```

### Level 4: End-to-End Test
```bash
# Frontend test
cd frontend
npm run dev

# 1. Click "Add Case" button
# 2. Enter case name "E2E Test Case"
# 3. Submit and verify case appears in dropdown
# 4. Select case and verify context propagation
# 5. Navigate to different views - case should remain selected
# 6. Attempt to query - should only see case-specific data
```

## Final Validation Checklist
- [ ] All tests pass: `python -m pytest src/ -v`
- [ ] No linting errors: `ruff check src/`
- [ ] No type errors: `mypy src/`
- [ ] Case creation works via UI
- [ ] Case isolation verified (no cross-case data)
- [ ] Shared resources remain accessible
- [ ] Audit logs capture all access
- [ ] WebSocket events filtered by case
- [ ] Performance acceptable (<100ms middleware overhead)

---

## Anti-Patterns to Avoid
- ❌ Don't create cases without proper validation
- ❌ Don't allow cross-case queries at vector store level
- ❌ Don't skip audit logging for performance
- ❌ Don't hardcode shared resource names
- ❌ Don't trust client-provided case IDs without validation
- ❌ Don't create separate Qdrant instances per case (use databases)

## Critical Implementation Notes

### Qdrant Isolation Strategy
1. Use database parameter for logical separation
2. Add case_id to all payloads as backup
3. Always filter by both database AND payload

### Performance Considerations
1. Cache case permissions in Redis
2. Use connection pooling for Qdrant databases
3. Implement collection archiving for closed cases
4. Index Supabase queries properly

### Security Checklist
1. Enable Supabase RLS on all case-related tables
2. Validate case access in middleware AND queries
3. Log all case access attempts
4. Implement rate limiting per case
5. Regular audit log reviews