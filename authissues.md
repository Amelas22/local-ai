## FEATURE:

Fix JWT Authentication in Development Mode for Clerk Frontend

The Clerk frontend is experiencing 401 Unauthorized errors when attempting to access API endpoints (GET /api/cases and POST
/api/cases) in development mode. The console logs show "Auth disabled - using development auth service" but the API requests are not       
including the required Authorization header with the JWT token, causing the backend to reject the requests.

The issue occurs because:
1. In development mode, the frontend uses a mock auth service that generates a mock token
2. The apiClient interceptor is not properly injecting the authentication token from the development auth service
3. The request interceptor may be trying to read the token before the development auth service has initialized and set the token in Redux state

## EXAMPLES:

Current Issue - Missing Authorization Header

// Request being sent without Authorization header:
POST /api/cases HTTP/1.1
  Accept: application/json, text/plain, */*
  Content-Type: application/json
  // Missing: Authorization: Bearer <token>

## Fix 1: Update apiClient.ts Request Interceptor

// src/services/utils/apiClient.ts
this.client.interceptors.request.use(
    (config) => {
      // Add auth token from tokenService (which handles both prod and dev tokens)
      const token = tokenService.getAccessToken();

      // In development mode, fall back to Redux state if tokenService is empty
      if (!token && import.meta.env.VITE_AUTH_ENABLED === 'false') {
        const state = store.getState();
        const devToken = state.auth.token;
        if (devToken) {
          config.headers['Authorization'] = `Bearer ${devToken}`;
        }
      } else if (token) {
        config.headers['Authorization'] = `Bearer ${token}`;
      }

      // Add case ID from localStorage
      const activeCase = localStorage.getItem('activeCase');
      if (activeCase) {
        config.headers['X-Case-ID'] = activeCase;
      }

      return config;
    },
    (error) => {
      return Promise.reject(error);
    }
  );

## Fix 2: Update Development Auth Service to Use Token Service

// src/services/auth.service.dev.ts
import { tokenService } from '@/services/token.service';

class DevAuthService {
    constructor() {
      // Automatically log in the dev user
      setTimeout(() => {
        const tokens = {
          access_token: MOCK_TOKEN,
          refresh_token: MOCK_TOKEN,
          token_type: 'bearer' as const
        };

        // Store in tokenService for consistency
        tokenService.setTokens(tokens);

        store.dispatch(loginSuccess({
          user: MOCK_USER,
          token: MOCK_TOKEN,
          refreshToken: MOCK_TOKEN,
        }));
      }, 100);
    }

    isAuthenticated(): boolean {
      // Check both tokenService and Redux state
      return tokenService.hasTokens() || store.getState().auth.isAuthenticated;
    }
  }

## Fix 3: Handle Auth Initialization Race Condition

// src/services/auth.service.ts
// In the main auth service initialization
export let authService: AuthService;

  // Initialize auth service based on environment
  if (import.meta.env.VITE_AUTH_ENABLED === 'true') {
    authService = new AuthService();
  } else {
    // Use dynamic import with proper type casting
    const devAuthModule = await import('./auth.service.dev');
    authService = devAuthModule.authService;
  }

## Fix 4: Backend Middleware to Accept Dev Token

# src/middleware/auth_middleware.py
  class AuthMiddleware(BaseHTTPMiddleware):
      async def dispatch(self, request: Request, call_next):
          # In development mode, accept the dev token
          if os.getenv("AUTH_ENABLED", "true").lower() == "false":
              # Accept the dev-token-123456 for development
              auth_header = request.headers.get("Authorization")
              if auth_header == "Bearer dev-token-123456":
                  # Set mock user context
                  request.state.user_id = "dev-user-123"
                  request.state.law_firm_id = "dev-firm-123"
                  return await call_next(request)

## DOCUMENTATION:

1. Axios Interceptors Documentation
    - https://axios-http.com/docs/interceptors
    - Explains request/response interceptor patterns for token injection
2. JWT Authentication in FastAPI
    - https://fastapi.tiangolo.com/tutorial/security/first-steps/
    - https://testdriven.io/blog/fastapi-jwt-auth/
    - Backend JWT implementation patterns
3. Source Files to Reference
    - /mnt/c/Users/jlemr/Test2/local-ai-package/Clerk/frontend/src/services/utils/apiClient.ts - API client with interceptors
    - /mnt/c/Users/jlemr/Test2/local-ai-package/Clerk/frontend/src/services/auth.service.dev.ts - Development auth service
    - /mnt/c/Users/jlemr/Test2/local-ai-package/Clerk/frontend/src/services/token.service.ts - Token management service
    - /mnt/c/Users/jlemr/Test2/local-ai-package/Clerk/frontend/src/services/auth.service.ts - Main auth service
    - /mnt/c/Users/jlemr/Test2/local-ai-package/Clerk/src/middleware/auth_middleware.py - Backend auth middleware
4. Axios Request Queue Pattern
    - https://www.cashfree.com/blog/axios-interceptors-jwt-refresh-react-native/
    - Pattern for handling multiple failed requests during token refresh
5. Context7 MCP Server: Use to pull documentation that is needed
6. Brave-search MCP server: Use to research outside sources as needed

## OTHER CONSIDERATIONS:

1. Race Condition: The development auth service uses setTimeout(() => {...}, 100) to automatically log in the user. This creates a race condition where API requests might be made before the token is set. Consider using a Promise-based initialization pattern.
2. Token Storage Consistency: Currently, the development mode stores tokens in Redux but the production mode uses localStorage via
  tokenService. This inconsistency causes the apiClient interceptor to miss the dev token.
3. Backend Development Mode: The backend needs to be configured to accept the development token ("dev-token-123456") when running in       
  development mode. Check if AUTH_ENABLED environment variable is properly set and handled.
4. Environment Variable: Ensure VITE_AUTH_ENABLED=false is set in the frontend .env file for development mode.
5. Case Context: Even in development mode, the X-Case-ID header may be required for case-specific endpoints. Ensure a default case
  exists or the header is properly set.
6. Synchronous vs Asynchronous: The auth service initialization uses dynamic imports which are asynchronous, but the export expects a      
  synchronous value. This may cause the authService to be undefined when first accessed.
7. Token Format: Ensure the mock token follows the same JWT structure as production tokens if the backend validates token format even      
  in development mode.