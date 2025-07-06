name: "Frontend Authentication Migration from Supabase to PostgreSQL JWT"
description: |

## Purpose
Migrate the Clerk frontend application from Supabase authentication to JWT-based authentication using the existing PostgreSQL backend, ensuring seamless user experience and maintaining development mode functionality.

## Core Principles
1. **Context is King**: Include ALL necessary documentation, examples, and caveats
2. **Validation Loops**: Provide executable tests/lints the AI can run and fix
3. **Information Dense**: Use keywords and patterns from the codebase
4. **Progressive Success**: Start simple, validate, then enhance
5. **Global rules**: Be sure to follow all rules in CLAUDE.md

---

## Goal
Completely remove Supabase dependency from the Clerk frontend application and replace it with JWT-based authentication that communicates with the existing PostgreSQL backend at /api/auth/* endpoints. The migration must maintain identical user experience, support automatic token refresh, and preserve development mode functionality. Additionally, ensure the "Add Case" functionality works properly by fixing any remaining Supabase dependencies in the backend case management system.

## Why
- **Reduce Dependencies**: Eliminate external Supabase dependency for better control
- **Unified Auth System**: Single authentication system across frontend and backend
- **Cost Optimization**: Remove Supabase subscription costs
- **Enhanced Security**: Direct control over authentication flow and token management
- **Backend Already Ready**: JWT authentication endpoints are fully implemented

## What
Replace all Supabase authentication calls with REST API calls to the backend JWT endpoints while maintaining the same user experience and development workflow.

### Success Criteria
- [ ] All Supabase dependencies removed from package.json
- [ ] Login/logout flows work with JWT tokens
- [ ] Automatic token refresh on 401 responses
- [ ] Protected routes enforce authentication
- [ ] Development mode with mock auth continues to work
- [ ] WebSocket authentication uses JWT tokens
- [ ] All auth-related tests pass
- [ ] No regression in user experience

## All Needed Context

### Documentation & References (list all context needed to implement the feature)
```yaml
# MUST READ - Include these in your context window
- url: https://axios-http.com/docs/interceptors
  why: Token refresh interceptor pattern, request/response handling
  
- url: https://www.cashfree.com/blog/axios-interceptors-jwt-refresh-react-native/
  why: Modern JWT refresh implementation with queue for multiple failed requests
  
- file: /mnt/c/Users/jlemr/Test2/local-ai-package/Clerk/src/api/auth_endpoints.py
  why: Exact API contract, request/response formats, OAuth2 form data requirement
  
- file: /mnt/c/Users/jlemr/Test2/local-ai-package/Clerk/frontend/src/services/auth.service.ts
  why: Current Supabase implementation to replace, interface to maintain
  
- file: /mnt/c/Users/jlemr/Test2/local-ai-package/Clerk/frontend/src/utils/apiClient.ts
  why: Existing interceptor pattern, token injection logic

- file: /mnt/c/Users/jlemr/Test2/local-ai-package/Clerk/frontend/src/services/auth.service.dev.ts
  why: Development auth service pattern to preserve

- doc: https://blog.stackademic.com/refresh-access-token-with-axios-interceptors-in-react-js-with-typescript-bd7a2d035562
  section: TypeScript implementation with proper typing
  critical: Queue management for simultaneous failed requests

- file: /mnt/c/Users/jlemr/Test2/local-ai-package/Clerk/src/services/case_manager.py
  why: PostgreSQL case manager adapter - correct implementation to use

- file: /mnt/c/Users/jlemr/Test2/local-ai-package/Clerk/src/api/case_endpoints.py
  why: Case API endpoints that frontend calls
```

### Current Codebase tree (run `tree` in the root of the project) to get an overview of the codebase
```bash
Clerk/frontend/
├── src/
│   ├── services/
│   │   ├── auth.service.ts         # Supabase auth implementation
│   │   ├── auth.service.dev.ts     # Development mock auth
│   │   └── supabase.ts            # Supabase client config
│   ├── store/
│   │   └── slices/
│   │       └── authSlice.ts       # Redux auth state
│   ├── utils/
│   │   ├── apiClient.ts           # Axios instance with interceptors
│   │   └── errorHandler.ts        # API error handling
│   ├── components/
│   │   └── ProtectedRoute.tsx     # Route guard component
│   └── hooks/
│       └── useAuth.ts             # Auth hook (if exists)
└── .env                           # Environment variables
```

### Desired Codebase tree with files to be added and responsibility of file
```bash
Clerk/frontend/
├── src/
│   ├── services/
│   │   ├── auth.service.ts         # JWT auth implementation (MODIFIED)
│   │   ├── auth.service.dev.ts     # Development mock auth (UNCHANGED)
│   │   ├── token.service.ts        # NEW: Token storage and management
│   │   └── supabase.ts            # REMOVED
│   ├── store/
│   │   └── slices/
│   │       └── authSlice.ts       # Redux auth state with refresh token (MODIFIED)
│   ├── utils/
│   │   ├── apiClient.ts           # Enhanced with token refresh logic (MODIFIED)
│   │   └── errorHandler.ts        # API error handling (UNCHANGED)
│   ├── types/
│   │   └── auth.types.ts          # NEW: TypeScript interfaces for auth
│   └── tests/
│       └── auth.service.test.ts   # NEW: Auth service tests
└── .env                           # Remove VITE_SUPABASE_* vars (MODIFIED)
```

### Known Gotchas of our codebase & Library Quirks
```python
# CRITICAL: Login endpoint expects OAuth2 form data, NOT JSON
# Example: Content-Type: application/x-www-form-urlencoded
# Fields: username (email) and password

# CRITICAL: Token expiration times
# Access token: 30 minutes (ACCESS_TOKEN_EXPIRE_MINUTES)
# Refresh token: 7 days (REFRESH_TOKEN_EXPIRE_DAYS)

# CRITICAL: Backend auth endpoints
# POST /api/auth/login - OAuth2 form data (username, password)
# POST /api/auth/refresh - JSON body with refresh_token
# GET /api/auth/me - Requires Bearer token header
# POST /api/auth/logout - Revokes all refresh tokens

# CRITICAL: Development mode
# When VITE_AUTH_ENABLED=false, use mock auth service
# Must maintain auto-login behavior for development

# CRITICAL: WebSocket authentication
# Socket.io auth object expects token in auth.token field

# CRITICAL: Case context
# X-Case-ID header must still be sent with all requests

# CRITICAL: Backend case management issue
# Error "Supabase client not initialized" suggests wrong import
# Must use: from src.services.case_manager import case_manager
# NOT: from src.services.case_manager_supabase_backup
# The case_manager.py is the PostgreSQL adapter that should be used
```

## Implementation Blueprint

### Data models and structure

Create TypeScript interfaces for type safety:
```typescript
// src/types/auth.types.ts
export interface TokenResponse {
  access_token: string;
  refresh_token: string;
  token_type: 'bearer';
}

export interface User {
  id: string;
  email: string;
  name: string;
  law_firm_id: string;
  is_admin: boolean;
  is_active: boolean;
}

export interface LoginCredentials {
  email: string;
  password: string;
}

export interface AuthState {
  isAuthenticated: boolean;
  user: User | null;
  token: string | null;
  refreshToken: string | null;  // NEW
  isLoading: boolean;
  error: string | null;
}
```

### list of tasks to be completed to fullfill the PRP in the order they should be completed

```yaml
Task 1:
CREATE src/types/auth.types.ts:
  - Define all TypeScript interfaces for auth
  - Export types for use across the application
  - Include JWT token response types

Task 2:
CREATE src/services/token.service.ts:
  - Implement secure token storage (localStorage for now)
  - Add methods: setTokens, getAccessToken, getRefreshToken, clearTokens
  - Consider expiration checking logic

Task 3:
MODIFY src/store/slices/authSlice.ts:
  - Add refreshToken to state interface
  - Update loginSuccess to store refresh token
  - Update logout to clear refresh token
  - Add updateTokens action for refresh

Task 4:
MODIFY src/services/auth.service.ts:
  - Replace Supabase calls with API calls
  - Implement login with OAuth2 form data
  - Implement logout with token revocation
  - Add getCurrentUser method
  - Handle token storage via tokenService

Task 5:
MODIFY src/utils/apiClient.ts:
  - Implement refresh token interceptor
  - Add request queue for multiple failed requests
  - Handle 401 responses with automatic retry
  - Update token in Redux after refresh

Task 6:
MODIFY src/components/ProtectedRoute.tsx:
  - Update authentication check logic
  - Remove Supabase session refresh
  - Check token validity from tokenService

Task 7:
UPDATE WebSocket authentication:
  - Find socket initialization code
  - Update to use JWT token instead of Supabase token
  - Ensure reconnection uses fresh token

Task 8:
REMOVE Supabase dependencies:
  - Delete src/services/supabase.ts
  - Remove from package.json
  - Update any remaining imports

Task 9:
UPDATE environment configuration:
  - Remove VITE_SUPABASE_URL and VITE_SUPABASE_ANON_KEY
  - Ensure VITE_API_URL is properly configured
  - Update .env.example

Task 10:
CREATE src/tests/auth.service.test.ts:
  - Test login flow with form data
  - Test token refresh logic
  - Test logout and token cleanup
  - Test error handling

Task 11:
FIX Backend Case Management - ENSURE "Add Case" functionality works:
  - Check all imports in backend are using correct case_manager
  - Search for any references to case_manager_supabase_backup.py
  - Verify /api/cases endpoint imports from src.services.case_manager
  - The error "Supabase client not initialized" indicates wrong import
  - Test case creation works with new PostgreSQL implementation
  - Frontend already has correct API calls, just needs backend fix
```

### Per task pseudocode as needed added to each task
```python

# Task 2 - Token Service
class TokenService:
    # PATTERN: Centralized token management
    setTokens(tokens: TokenResponse):
        localStorage.setItem('access_token', tokens.access_token)
        localStorage.setItem('refresh_token', tokens.refresh_token)
        # GOTCHA: Also update Redux store
        store.dispatch(updateTokens(tokens))
    
    getAccessToken():
        return localStorage.getItem('access_token')
    
    clearTokens():
        localStorage.removeItem('access_token')
        localStorage.removeItem('refresh_token')
        # Clear from Redux too

# Task 4 - Auth Service
async login(credentials: LoginCredentials):
    # CRITICAL: Use FormData for OAuth2 compliance
    const formData = new FormData()
    formData.append('username', credentials.email)  # Note: username field
    formData.append('password', credentials.password)
    
    # PATTERN: Use existing apiClient without auth header
    const response = await axios.post('/api/auth/login', formData, {
        headers: { 'Content-Type': 'application/x-www-form-urlencoded' }
    })
    
    # Store tokens and get user info
    tokenService.setTokens(response.data)
    const user = await this.getCurrentUser()
    
    # Update Redux state
    dispatch(loginSuccess({ user, token: response.data.access_token }))

# Task 5 - API Client Interceptors
# PATTERN: Token refresh with request queue
let isRefreshing = false
let failedQueue = []

apiClient.interceptors.response.use(
    response => response,
    async error => {
        const originalRequest = error.config
        
        if (error.response?.status === 401 && !originalRequest._retry) {
            if (isRefreshing) {
                # Queue the request
                return new Promise((resolve, reject) => {
                    failedQueue.push({ resolve, reject })
                }).then(token => {
                    originalRequest.headers.Authorization = `Bearer ${token}`
                    return apiClient(originalRequest)
                })
            }
            
            originalRequest._retry = true
            isRefreshing = true
            
            try {
                const refreshToken = tokenService.getRefreshToken()
                const response = await axios.post('/api/auth/refresh', {
                    refresh_token: refreshToken
                })
                
                tokenService.setTokens(response.data)
                processQueue(null, response.data.access_token)
                
                originalRequest.headers.Authorization = `Bearer ${response.data.access_token}`
                return apiClient(originalRequest)
                
            } catch (refreshError) {
                processQueue(refreshError, null)
                authService.logout()
                window.location.href = '/login'
                return Promise.reject(refreshError)
            } finally {
                isRefreshing = false
            }
        }
        
        return Promise.reject(error)
    }
)

# Task 11 - Fix Backend Case Management
# CRITICAL: Find and fix wrong imports
# Search for imports:
grep -r "case_manager_supabase_backup" Clerk/src/
# Should return NO results

# Verify correct import in case_endpoints.py:
# Should be: from src.services.case_manager import case_manager
# NOT: from src.services.case_manager_supabase_backup import case_manager

# Test case creation:
curl -X POST http://localhost:8010/api/cases \
  -H "Authorization: Bearer ${TOKEN}" \
  -H "Content-Type: application/json" \
  -d '{"name": "Test Case v. Demo"}'

# Expected: 201 Created with case details
# If error about Supabase, check imports again
```

### Integration Points
```yaml
REDUX:
  - modify: src/store/slices/authSlice.ts
  - add: refreshToken field to state
  - add: updateTokens action
  
API_CLIENT:
  - modify: src/utils/apiClient.ts
  - pattern: "Implement response interceptor for 401 handling"
  - add: Request queue for concurrent failed requests
  
WEBSOCKET:
  - find: Socket initialization (likely in App.tsx or a context)
  - update: "auth: { token: tokenService.getAccessToken() }"
  
ROUTES:
  - update: ProtectedRoute component
  - remove: Supabase session checks
  - add: Token validity checks
```

## Validation Loop

### Level 1: Syntax & Style
```bash
# Run these FIRST - fix any errors before proceeding
npm run lint                         # ESLint checking
npm run type-check                   # TypeScript checking

# Expected: No errors. If errors, READ the error and fix.
```

### Level 2: Unit Tests each new feature/file/function use existing test patterns
```typescript
// CREATE src/tests/auth.service.test.ts with these test cases:
describe('AuthService', () => {
  it('should login with email and password', async () => {
    const credentials = { email: 'test@example.com', password: 'password123' };
    const result = await authService.login(credentials);
    expect(result).toHaveProperty('user');
    expect(tokenService.getAccessToken()).toBeTruthy();
  });

  it('should handle login failure', async () => {
    const credentials = { email: 'invalid@example.com', password: 'wrong' };
    await expect(authService.login(credentials)).rejects.toThrow();
  });

  it('should refresh token on 401', async () => {
    // Mock 401 response
    // Verify refresh endpoint called
    // Verify original request retried
  });

  it('should logout and clear tokens', async () => {
    await authService.logout();
    expect(tokenService.getAccessToken()).toBeNull();
  });
});
```

```bash
# Run and iterate until passing:
npm test src/tests/auth.service.test.ts
# If failing: Read error, understand root cause, fix code, re-run (never mock to pass)
```

### Level 3: Integration Test
```bash
# Start the backend
cd /mnt/c/Users/jlemr/Test2/local-ai-package/Clerk
python main.py

# Start the frontend
cd /mnt/c/Users/jlemr/Test2/local-ai-package/Clerk/frontend
npm run dev

# Test the login flow
curl -X POST http://localhost:8010/api/auth/login \
  -H "Content-Type: application/x-www-form-urlencoded" \
  -d "username=admin@example.com&password=admin123456"

# Expected: {"access_token": "...", "refresh_token": "...", "token_type": "bearer"}

# Test protected endpoint
curl -X GET http://localhost:8010/api/auth/me \
  -H "Authorization: Bearer {access_token}"

# Expected: User object with id, email, name, etc.

# Test case creation (Task 11)
curl -X POST http://localhost:8010/api/cases \
  -H "Authorization: Bearer {access_token}" \
  -H "Content-Type: application/json" \
  -d '{"name": "Test Case v. Demo"}'

# Expected: 201 Created with case object
# If error mentions Supabase, backend has wrong imports
```

## Final validation Checklist
- [ ] All tests pass: `npm test`
- [ ] No linting errors: `npm run lint`
- [ ] No type errors: `npm run type-check`
- [ ] Manual login/logout flow works
- [ ] Token refresh works (wait 30+ minutes or modify token)
- [ ] Protected routes redirect when not authenticated
- [ ] Development mode still works with VITE_AUTH_ENABLED=false
- [ ] WebSocket connects with JWT token
- [ ] No Supabase imports remain in codebase
- [ ] Environment variables updated

---

## Anti-Patterns to Avoid
- ❌ Don't store tokens in Redux only (need persistence)
- ❌ Don't forget OAuth2 form data format for login
- ❌ Don't skip the request queue for token refresh
- ❌ Don't remove development auth service
- ❌ Don't break existing API interceptor patterns
- ❌ Don't forget to handle WebSocket authentication

## Confidence Score: 8/10

The implementation path is clear with comprehensive context. The main complexity lies in the token refresh interceptor with request queuing, but the provided examples and patterns should enable successful one-pass implementation. The backend auth is already fully functional, which reduces risk. The case management fix (Task 11) is straightforward - just need to ensure correct imports are used throughout the backend.