# PRP: Fix JWT Authentication in Development Mode for Clerk Frontend

## Goal/Why/What

**Goal**: Fix JWT authentication failures (401 Unauthorized errors) in development mode that prevent the Clerk frontend from accessing API endpoints.

**Why**: The development auth service is not properly integrated with the API client interceptor, causing missing Authorization headers and preventing developers from testing the application locally.

**What**: Implement a robust authentication flow in development mode that:
- Ensures proper token injection in API requests
- Resolves race conditions during initialization
- Maintains consistency with production auth patterns
- Allows seamless local development without authentication friction

## Context

### Documentation Links
- **Axios Interceptors**: https://axios-http.com/docs/interceptors - Official docs for request/response interceptors
- **JWT with Axios Best Practices**: https://mihai-andrei.com/blog/jwt-authentication-using-axios-interceptors/ - Comprehensive JWT implementation guide
- **Handling Token Refresh**: https://www.cashfree.com/blog/axios-interceptors-jwt-refresh-react-native/ - Queue pattern for concurrent requests
- **FastAPI JWT Auth**: https://testdriven.io/blog/fastapi-jwt-auth/ - Backend JWT implementation patterns
- **Race Condition Prevention**: https://brainsandbeards.com/blog/2024-token-renewal-mutex/ - Token renewal patterns

### Key Files to Read and Understand
```bash
# Frontend - Authentication Services
Clerk/frontend/src/services/utils/apiClient.ts          # API client with interceptors
Clerk/frontend/src/services/auth.service.dev.ts         # Development auth service
Clerk/frontend/src/services/token.service.ts            # Token management service
Clerk/frontend/src/services/auth.service.ts             # Main auth service
Clerk/frontend/src/stores/authSlice.ts                  # Redux auth state

# Backend - Authentication Middleware
Clerk/src/middleware/auth_middleware.py                  # JWT validation middleware
Clerk/.env                                              # Environment configuration

# Configuration Files
Clerk/frontend/.env                                      # Frontend env vars (VITE_AUTH_ENABLED)
```

### Current Codebase Tree (Authentication-Related)
```
Clerk/
  frontend/
    src/
      services/
        utils/
          apiClient.ts              # Has interceptor but misses dev tokens
        auth.service.ts             # Main auth with async initialization issue
        auth.service.dev.ts         # Dev auth with setTimeout race condition
        token.service.ts            # Token storage/retrieval service
      stores/
        authSlice.ts                # Redux auth state management
      hooks/
        useAuth.ts                  # Auth hook for components
  src/
    middleware/
      auth_middleware.py            # Backend JWT validation
```

## Implementation Blueprint

### Data Models/Types
```typescript
// Token initialization state
interface AuthInitState {
  initialized: boolean;
  initializing: boolean;
  error: string | null;
}

// Dev auth configuration
interface DevAuthConfig {
  mockToken: string;
  mockUser: User;
  autoLoginDelay: number;
}
```

### Task List (In Order)
1. **Fix Auth Service Initialization Race Condition**
   - Convert auth service initialization to Promise-based pattern
   - Ensure apiClient waits for auth service before making requests

2. **Update API Client Interceptor**
   - Add fallback to Redux state for dev tokens
   - Ensure proper token format in Authorization header
   - Add logging for debugging in dev mode

3. **Synchronize Token Storage**
   - Ensure dev auth service uses tokenService for consistency
   - Update all token reads to use single source of truth

4. **Update Backend Middleware**
   - Add development mode token acceptance
   - Validate dev-token-123456 in development environment

5. **Add Initialization Guards**
   - Prevent API calls before auth initialization
   - Add auth ready state to Redux

6. **Create Comprehensive Tests**
   - Unit tests for auth services
   - Integration tests for API interceptors
   - End-to-end tests for auth flow

### Pseudocode Approach

```typescript
// 1. Promise-based auth initialization
class AuthServiceManager {
  private authServicePromise: Promise<AuthService>;
  
  async initialize(): Promise<AuthService> {
    if (isDevelopment) {
      const devAuth = await initializeDevAuth();
      await devAuth.waitForReady();
      return devAuth;
    }
    return new ProductionAuthService();
  }
}

// 2. Updated API interceptor
apiClient.interceptors.request.use(async (config) => {
  // Wait for auth service if not ready
  await authServiceManager.waitForReady();
  
  // Get token from single source
  const token = tokenService.getAccessToken();
  if (token) {
    config.headers.Authorization = `Bearer ${token}`;
  }
  
  return config;
});

// 3. Dev auth with immediate token setting
class DevAuthService {
  constructor() {
    // Set tokens immediately, not in setTimeout
    this.initializeDevAuth();
  }
  
  private initializeDevAuth() {
    tokenService.setTokens({
      access_token: MOCK_TOKEN,
      refresh_token: MOCK_TOKEN
    });
    store.dispatch(authReady());
  }
}
```

## Integration Points

### Configuration Changes
```env
# Frontend .env
VITE_AUTH_ENABLED=false
VITE_DEV_MOCK_TOKEN=dev-token-123456
VITE_API_BASE_URL=http://localhost:8000

# Backend .env
AUTH_ENABLED=false
DEV_MOCK_TOKEN=dev-token-123456
```

### API Route Changes
- No route changes required
- All existing routes will work with proper auth headers

### Database Schema Changes
- None required

## Validation Loop

### Level 1: Syntax and Style (must pass 100%)
```bash
# Frontend
cd Clerk/frontend
npm run lint
npm run type-check

# Backend
cd Clerk
ruff check src/middleware/auth_middleware.py
mypy src/middleware/auth_middleware.py
```

### Level 2: Unit Tests (must pass 100%)
```bash
# Frontend auth service tests
cd Clerk/frontend
npm test src/services/tests/auth.service.test.ts
npm test src/services/tests/auth.service.dev.test.ts
npm test src/services/tests/apiClient.test.ts

# Backend middleware tests
cd Clerk
pytest src/middleware/tests/test_auth_middleware.py -v
```

### Level 3: Integration Tests
```bash
# Test auth flow end-to-end
cd Clerk/frontend
npm run test:e2e -- --spec=auth-flow.spec.ts

# Test API requests with auth
cd Clerk
pytest tests/integration/test_auth_integration.py -v
```

## Typical User Workflow After Implementation

1. Developer starts frontend with `npm run dev`
2. Dev auth service automatically logs in with mock credentials
3. All API requests include proper Authorization headers
4. Backend accepts dev token in development mode
5. Developer can test all authenticated features locally

## Final Checklist

- [ ] **Files exist**: All listed files are present in the codebase
- [ ] **Environment variables**: Both frontend and backend .env files configured
- [ ] **No hardcoded values**: All tokens/secrets from environment
- [ ] **Tests pass**: All unit and integration tests green
- [ ] **Lint passes**: No linting errors in changed files
- [ ] **Type safety**: TypeScript compilation successful
- [ ] **Race conditions**: Auth initialization completes before API calls
- [ ] **Token consistency**: Single source of truth for token storage
- [ ] **Dev experience**: No manual auth steps required in dev mode
- [ ] **Error handling**: Graceful fallbacks for auth failures
- [ ] **Logging**: Appropriate debug logs for troubleshooting
- [ ] **Documentation**: README updated with dev auth setup

## Anti-Patterns to Avoid

1. **Don't use setTimeout for critical initialization** - Use Promises/async-await
2. **Don't store tokens in multiple places** - Use single source of truth
3. **Don't make API calls before auth ready** - Wait for initialization
4. **Don't hardcode tokens** - Use environment variables
5. **Don't skip error handling** - Handle all auth failure scenarios
6. **Don't mix auth patterns** - Keep dev/prod auth consistent
7. **Don't forget cleanup** - Clear tokens on logout
8. **Don't expose sensitive info in logs** - Sanitize debug output

## Implementation Notes

### Critical Implementation Details

1. **Token Format Consistency**: Ensure mock token follows JWT structure:
   ```typescript
   const MOCK_TOKEN = "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJzdWIiOiJkZXYtdXNlci0xMjMiLCJsYXdfZmlybV9pZCI6ImRldi1maXJtLTEyMyIsImlhdCI6MTUxNjIzOTAyMn0.SflKxwRJSMeKKF2QT4fwpMeJf36POk6yJV_adQssw5c";
   ```

2. **Redux State Updates**: Ensure auth state updates trigger re-renders:
   ```typescript
   // Use Redux Toolkit's createSlice for immutable updates
   authSlice.reducers.setAuthReady: (state) => {
     state.initialized = true;
     state.initializing = false;
   }
   ```

3. **Axios Request Queue**: Implement proper queue for concurrent requests during token refresh:
   ```typescript
   let failedQueue: any[] = [];
   const processQueue = (error: any, token: string | null = null) => {
     failedQueue.forEach((prom) => {
       if (error) {
         prom.reject(error);
       } else {
         prom.resolve(token);
       }
     });
     failedQueue = [];
   };
   ```

4. **Backend Environment Check**: Use proper environment detection:
   ```python
   def is_development_mode() -> bool:
       return os.getenv("AUTH_ENABLED", "true").lower() == "false"
   ```

### Testing Considerations

1. **Mock Timer Control**: Use Jest timer mocks for testing setTimeout/Promise timing
2. **Network Mocking**: Mock axios for predictable test behavior
3. **State Testing**: Test Redux state changes during auth flow
4. **Error Scenarios**: Test 401, 403, network errors
5. **Concurrency**: Test multiple simultaneous API calls

## Success Metrics

- Zero 401 errors in development mode after implementation
- API requests include Authorization header 100% of the time
- No race condition errors in console
- Auth initialization completes in < 100ms
- All existing tests continue to pass
- New auth tests provide > 90% coverage

## Confidence Score: 9/10

This PRP provides comprehensive context for fixing the JWT authentication issues in development mode. The implementation path is clear, with specific code examples and patterns from the existing codebase. The validation gates are executable and will ensure the solution works correctly. The only reason it's not 10/10 is that some edge cases might emerge during implementation that require minor adjustments to the approach.