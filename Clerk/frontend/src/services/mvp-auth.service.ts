/**
 * MVP Auth Service Stub
 * 
 * WARNING: This auth service is for MVP development only and MUST NOT be used in production.
 * It bypasses all authentication and returns a consistent mock user.
 * 
 * To re-enable authentication:
 * 1. Remove this file
 * 2. Update auth.service.ts to remove MVP mode check
 * 3. Remove VITE_MVP_MODE environment variable
 */

import type { AuthService, AuthTokens, LoginCredentials } from './auth.service';
import type { TokenResponse } from '@/types/auth.types';
import { tokenService } from './token.service';
import { store } from '@/store/store';
import { loginSuccess, setLoading, setInitialized } from '@/store/slices/authSlice';

// Mock user matching backend MockUserMiddleware
export const mockUser = {
  id: '123e4567-e89b-12d3-a456-426614174001',
  email: 'dev@clerk.ai',
  name: 'Development User',
  law_firm_id: '123e4567-e89b-12d3-a456-426614174000',
  law_firm_name: 'Development Law Firm',
  is_active: true,
  is_admin: true,
  permissions: ['read', 'write', 'delete'],
  metadata: {
    mvp_mode: true,
    warning: 'This is a mock user for MVP development only'
  }
};

// Mock tokens for MVP mode
const mockTokens: AuthTokens = {
  access_token: 'mvp-mock-access-token',
  refresh_token: 'mvp-mock-refresh-token',
  token_type: 'bearer'
};

export class MvpAuthService implements AuthService {
  constructor() {
    console.warn('🚨 MVP Auth Service Active - NO AUTHENTICATION 🚨');
    console.warn('All users will be logged in as:', mockUser.email);
    console.warn('DO NOT USE IN PRODUCTION!');
  }

  async login(credentials: LoginCredentials): Promise<AuthTokens> {
    console.log('[MVP Auth] Mock login called with:', credentials.email);
    
    // Simulate async behavior
    await new Promise(resolve => setTimeout(resolve, 500));
    
    // Save mock tokens with exact token_type
    const tokens: TokenResponse = {
      access_token: mockTokens.access_token,
      refresh_token: mockTokens.refresh_token,
      token_type: 'bearer' as const
    };
    tokenService.setTokens(tokens);
    
    // Update Redux store
    store.dispatch(loginSuccess({
      user: mockUser,
      token: mockTokens.access_token,
      refreshToken: mockTokens.refresh_token
    }));
    
    console.log('[MVP Auth] Mock login successful');
    return mockTokens;
  }

  async logout(): Promise<void> {
    console.log('[MVP Auth] Mock logout called');
    
    // Clear tokens (even though they're mock)
    tokenService.clearTokens();
    
    // In MVP mode, we don't actually log out
    console.log('[MVP Auth] Logout simulated but user remains logged in');
  }

  async getCurrentUser(): Promise<any> {
    console.log('[MVP Auth] Returning mock user');
    return mockUser;
  }

  async refreshAccessToken(): Promise<AuthTokens> {
    console.log('[MVP Auth] Mock token refresh called');
    
    // Always return valid mock tokens
    return mockTokens;
  }

  async initialize(): Promise<void> {
    console.log('[MVP Auth] Initializing MVP auth service');
    
    // Always auto-login with mock user
    store.dispatch(setLoading(true));
    
    try {
      // Set mock tokens with exact token_type
      const tokens: TokenResponse = {
        access_token: mockTokens.access_token,
        refresh_token: mockTokens.refresh_token,
        token_type: 'bearer' as const
      };
      tokenService.setTokens(tokens);
      
      // Update Redux store with mock user
      store.dispatch(loginSuccess({
        user: mockUser,
        token: mockTokens.access_token,
        refreshToken: mockTokens.refresh_token
      }));
      
      console.log('[MVP Auth] Auto-logged in with mock user');
    } catch (error) {
      console.error('[MVP Auth] Failed to initialize:', error);
    } finally {
      store.dispatch(setLoading(false));
      store.dispatch(setInitialized());
    }
  }

  async checkAuthStatus(): Promise<boolean> {
    // Always authenticated in MVP mode
    return true;
  }

  isAuthenticated(): boolean {
    // Always authenticated in MVP mode
    return true;
  }

  getUser(): any {
    return mockUser;
  }
}

// Export singleton instance
export const mvpAuthService = new MvpAuthService();