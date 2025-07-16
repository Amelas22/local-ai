# PRP: Remove Auth Middleware for MVP Development

## Goal
Temporarily remove authentication middleware from the Clerk system to accelerate MVP development by eliminating auth-related debugging friction while maintaining case isolation and preparing for easy re-enablement.

## Why
- Auth middleware causes repeated development friction with every new feature
- Investors care about core legal AI features, not authentication
- MVP demos will run on controlled Docker Desktop environment
- Auth can be re-enabled later with minimal effort
- Current AUTH_ENABLED=false still requires mock tokens and causes issues

## What
### User-Visible Behavior
- All API endpoints accessible without authentication tokens
- Frontend works without login screens or auth redirects
- Case isolation still functions using mock user context
- Clear "MVP Mode - No Authentication" warning banner
- All core features (discovery processing, motion drafting, search) work seamlessly

### Technical Requirements
1. Replace AuthMiddleware with MockUserMiddleware
2. Update all auth-dependent endpoints to use mock context
3. Remove auth from frontend API client
4. Bypass WebSocket authentication
5. Maintain case isolation with consistent mock user
6. Keep auth code commented for easy re-enablement

### Success Criteria
- [ ] No auth tokens required for any API endpoint
- [ ] Frontend operates without auth service
- [ ] All tests pass with mock user context
- [ ] Case isolation still prevents data leakage
- [ ] Auth can be re-enabled by uncommenting code
- [ ] Clear documentation of changes made

## All Needed Context

### Documentation URLs
- FastAPI Middleware Best Practices: https://fastapi.tiangolo.com/tutorial/middleware/
- Environment-based Auth Toggle: https://stackoverflow.com/questions/76159708/how-to-disable-authentication-in-fastapi-based-on-environment
- FastAPI Dependencies: https://fastapi.tiangolo.com/tutorial/dependencies/

### Files to Study
1. `/Clerk/main.py:141-145` - Auth middleware configuration
2. `/Clerk/src/middleware/auth_middleware.py` - Current auth implementation
3. `/Clerk/src/middleware/case_context.py` - Case context dependency on auth
4. `/Clerk/src/api/case_endpoints.py` - Auth dependencies in endpoints
5. `/Clerk/src/utils/auth.py` - Auth helper functions
6. `/Clerk/frontend/src/services/api.client.ts` - Frontend API client
7. `/Clerk/src/websocket/socket_server.py` - WebSocket auth validation

### Critical Information
- Mock user details already defined in auth_middleware.py:
  - ID: `123e4567-e89b-12d3-a456-426614174001`
  - Email: `dev@clerk.ai`
  - Law Firm ID: `123e4567-e89b-12d3-a456-426614174000`
- Case isolation MUST be maintained even without auth
- WebSocket connections check for auth tokens in connect handler
- Many endpoints use `Depends(get_current_user)` or `Depends(require_case_context)`
- Frontend Redux store expects user state

### Existing Patterns
- Auth middleware already has dev mode with AUTH_ENABLED flag
- Tests use DEV_MOCK_TOKEN pattern
- Mock user fallback exists in auth_middleware.py
- Middleware ordering: CORS → Auth → CaseContext

## Implementation Blueprint

### Data Models and Structures

```python
# src/middleware/mock_user_middleware.py
from types import SimpleNamespace
from fastapi import Request
from starlette.middleware.base import BaseHTTPMiddleware

class MockUserMiddleware(BaseHTTPMiddleware):
    """Inject mock user for MVP development - REMOVE IN PRODUCTION"""
    
    MOCK_USER = SimpleNamespace(
        id='123e4567-e89b-12d3-a456-426614174001',
        email='dev@clerk.ai',
        name='Development User',
        law_firm_id='123e4567-e89b-12d3-a456-426614174000',
        is_active=True,
        is_admin=True,
        permissions={'read': True, 'write': True, 'delete': True}
    )
```

### Task List (In Order)

#### 1. Create Mock User Middleware
**File**: `src/middleware/mock_user_middleware.py`
```python
# Pseudocode
class MockUserMiddleware:
    def dispatch(request, call_next):
        # Set all user attributes on request.state
        request.state.user_id = MOCK_USER.id
        request.state.user_email = MOCK_USER.email
        request.state.user_name = MOCK_USER.name
        request.state.law_firm_id = MOCK_USER.law_firm_id
        request.state.is_admin = MOCK_USER.is_admin
        request.state.user = MOCK_USER
        
        # Call next middleware
        response = call_next(request)
        return response
```

#### 2. Update Main Application
**File**: `main.py`
```python
# Pseudocode
# Line 141: Comment out AuthMiddleware
# from src.middleware.auth_middleware import AuthMiddleware
# app.add_middleware(AuthMiddleware)

# Add MockUserMiddleware instead
from src.middleware.mock_user_middleware import MockUserMiddleware
app.add_middleware(MockUserMiddleware)

# Add MVP mode indicator
@app.on_event("startup")
def startup_event():
    logger.warning("🚨 MVP MODE ACTIVE - NO AUTHENTICATION 🚨")
```

#### 3. Create Mock Auth Dependencies
**File**: `src/utils/mock_auth.py`
```python
# Pseudocode
def get_mock_user():
    return MockUserMiddleware.MOCK_USER

def get_mock_user_id():
    return MockUserMiddleware.MOCK_USER.id

def mock_require_admin():
    return MockUserMiddleware.MOCK_USER

# Wrapper for case context
def get_mock_case_context(case_id: str = Header(None)):
    return SimpleNamespace(
        case_id=case_id,
        case_name=case_id,
        user_id=MockUserMiddleware.MOCK_USER.id,
        permissions={'read': True, 'write': True}
    )
```

#### 4. Update API Endpoints
**Pattern**: Replace auth dependencies with mock versions
```python
# Before:
# user: User = Depends(get_current_user)
# After:
from src.utils.mock_auth import get_mock_user
user = Depends(get_mock_user)

# Before:
# case_context = Depends(require_case_context("write"))
# After:
from src.utils.mock_auth import get_mock_case_context
case_context = Depends(get_mock_case_context)
```

#### 5. Update Frontend API Client
**File**: `frontend/src/services/api.client.ts`
```typescript
// Pseudocode
const MVP_MODE = process.env.REACT_APP_MVP_MODE === 'true';

const apiClient = axios.create({
    baseURL: API_BASE_URL,
    headers: {
        'Content-Type': 'application/json',
        // MVP: No auth needed
        ...(MVP_MODE ? {} : {'Authorization': `Bearer ${getToken()}`})
    }
});

// Remove auth interceptors in MVP mode
if (!MVP_MODE) {
    // Add interceptors
}
```

#### 6. Create MVP Auth Service Stub
**File**: `frontend/src/services/mvp-auth.service.ts`
```typescript
// Pseudocode
export const mockUser = {
    id: '123e4567-e89b-12d3-a456-426614174001',
    email: 'dev@clerk.ai',
    name: 'Development User',
    isAuthenticated: true
};

export const authService = {
    login: async () => mockUser,
    logout: async () => {},
    getUser: () => mockUser,
    isAuthenticated: () => true
};
```

#### 7. Update WebSocket Server
**File**: `src/websocket/socket_server.py`
```python
# Pseudocode
@sio.event
async def connect(sid, environ, auth):
    if os.getenv('MVP_MODE') == 'true':
        # Skip auth validation
        await sio.save_session(sid, {
            'user_id': MockUserMiddleware.MOCK_USER.id,
            'authenticated': True
        })
        return True
    # Original auth logic...
```

#### 8. Update Docker Configuration
**File**: `docker-compose.yml`
```yaml
# Add MVP_MODE environment variable
environment:
  - MVP_MODE=true
  # Remove AUTH_ENABLED and DEV_MOCK_TOKEN
```

#### 9. Add MVP Warning Banner
**File**: `frontend/src/components/common/Layout.tsx`
```tsx
// Pseudocode
{process.env.REACT_APP_MVP_MODE === 'true' && (
    <Alert severity="warning" style={{position: 'fixed', top: 0}}>
        🚨 MVP Mode - No Authentication Active 🚨
    </Alert>
)}
```

#### 10. Update Tests
**Pattern**: Add MVP mode checks to auth-dependent tests
```python
# Pseudocode
@pytest.fixture
def mock_auth(monkeypatch):
    monkeypatch.setenv("MVP_MODE", "true")
    
def test_endpoint_with_auth(mock_auth):
    # Test should pass without auth in MVP mode
```

### Integration Points
1. **Middleware Stack**: MockUserMiddleware → CaseContextMiddleware
2. **API Endpoints**: All use mock auth dependencies
3. **Frontend**: Uses MVP auth service stub
4. **WebSocket**: Bypasses auth in MVP mode
5. **Tests**: Run with MVP_MODE=true

## Validation Loop

### Level 1: Syntax and Style
```bash
# Backend
cd Clerk
ruff check --fix .
ruff format .
python -m py_compile main.py src/**/*.py

# Frontend
cd frontend
npm run lint
npm run format
```

### Level 2: Unit Tests
```bash
# Backend tests with MVP mode
cd Clerk
MVP_MODE=true python -m pytest src/tests/ -v

# Frontend tests
cd frontend
REACT_APP_MVP_MODE=true npm test
```

### Level 3: Integration Tests
```bash
# Start services in MVP mode
docker-compose up -d

# Test API endpoints without auth
curl http://localhost:8000/api/cases
curl http://localhost:8000/health

# Test WebSocket connection
wscat -c ws://localhost:8000/ws/socket.io/
```

### Level 4: Feature Tests
```bash
# Test discovery processing
curl -X POST http://localhost:8000/discovery/process \
  -H "X-Case-ID: test-case" \
  -F "discovery_files=@test.pdf"

# Test motion drafting
curl -X POST http://localhost:8000/generate-motion-outline \
  -H "Content-Type: application/json" \
  -d '{"case_name": "test-case", "motion_type": "summary_judgment"}'

# Test search
curl -X POST http://localhost:8000/search \
  -H "X-Case-ID: test-case" \
  -H "Content-Type: application/json" \
  -d '{"query": "test query"}'
```

## Final Validation Checklist
- [ ] MockUserMiddleware injects consistent user context
- [ ] All API endpoints accessible without tokens
- [ ] Frontend operates without auth service
- [ ] Case isolation still functions
- [ ] WebSocket connections work without auth
- [ ] MVP warning banner displays
- [ ] All tests pass with MVP_MODE=true
- [ ] Original auth code remains but commented
- [ ] Re-enablement process documented

## Anti-Patterns to Avoid
1. **Don't delete auth code** - Comment it out for easy re-enablement
2. **Don't hardcode user IDs in endpoints** - Use mock middleware
3. **Don't skip case isolation** - Security boundary still needed
4. **Don't modify database schema** - Keep auth tables intact
5. **Don't create auth bypasses in production code** - Use MVP_MODE flag

## Re-Enablement Plan
1. Remove MockUserMiddleware from main.py
2. Uncomment AuthMiddleware import and registration
3. Remove mock_auth.py and mvp-auth.service.ts
4. Update docker-compose.yml to remove MVP_MODE
5. Restore original auth dependencies in endpoints
6. Remove MVP warning banner
7. Re-enable frontend auth service
8. Update tests to require auth

## Error Handling Strategy
- API errors return 200 instead of 401/403 in MVP mode
- Frontend skips auth redirects when MVP_MODE=true
- WebSocket fallback to mock user on any auth error
- Clear logging when operating in MVP mode

## Gotchas and Edge Cases
1. **Direct auth imports**: Search for `from src.utils.auth import` and update
2. **Admin panel routes**: May have hardcoded permission checks
3. **Database seed data**: Ensure dev user and law firm exist
4. **Redux initial state**: Must have mock user for state management
5. **Test fixtures**: Some may expect specific auth behavior
6. **File upload endpoints**: May validate user permissions inline

## Confidence Score: 9/10

High confidence due to:
- Clear separation of auth in middleware
- Existing dev mode patterns to follow
- Comprehensive context and examples
- Reversible changes
- Well-defined validation steps

Minor uncertainty around:
- Potential hidden auth dependencies in frontend components
- WebSocket auth bypass completeness