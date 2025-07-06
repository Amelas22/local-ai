import { store } from '@/store/store';
import { loginSuccess, logout as logoutAction, authInitStart, authInitComplete } from '@/store/slices/authSlice';
import type { LoginCredentials, SignUpData, User, TokenResponse } from '@/types/auth.types';
import { tokenService } from './token.service';

// Mock user for development
const MOCK_USER: User = {
  id: 'dev-user-123',
  email: 'dev@clerk.ai',
  name: 'Development User',
  law_firm_id: 'dev-firm-123',
  is_admin: true,
  is_active: true,
};

// Use simple mock tokens that match backend DEV_MOCK_TOKEN configuration
const MOCK_ACCESS_TOKEN = 'dev-token-123456';
const MOCK_REFRESH_TOKEN = 'dev-refresh-token-123456';

const MOCK_TOKENS: TokenResponse = {
  access_token: MOCK_ACCESS_TOKEN,
  refresh_token: MOCK_REFRESH_TOKEN,
  token_type: 'bearer'
};

class DevAuthService {
  private initPromise: Promise<void>;
  private initialized = false;

  constructor() {
    // Initialize immediately and store the promise for components to await
    this.initPromise = this.initializeDevAuth();
  }

  /**
   * Initialize development authentication immediately
   */
  private async initializeDevAuth(): Promise<void> {
    // Dispatch init start
    store.dispatch(authInitStart());
    
    // Store tokens in tokenService for consistency with apiClient
    tokenService.setTokens(MOCK_TOKENS);
    
    // Update Redux state
    store.dispatch(loginSuccess({
      user: MOCK_USER,
      token: MOCK_TOKENS.access_token,
      refreshToken: MOCK_TOKENS.refresh_token,
    }));

    // Mark auth as initialized
    store.dispatch(authInitComplete());
    
    this.initialized = true;
    console.log('Dev auth initialized with mock tokens');
  }

  /**
   * Wait for dev auth to be ready - components can await this
   */
  async waitForReady(): Promise<void> {
    return this.initPromise;
  }

  /**
   * Check if auth is initialized
   */
  isInitialized(): boolean {
    return this.initialized;
  }

  async login(credentials: LoginCredentials) {
    console.log('Dev mode: Mock login with', credentials);
    
    // Simulate API delay
    await new Promise(resolve => setTimeout(resolve, 500));
    
    // Store tokens properly
    tokenService.setTokens(MOCK_TOKENS);
    
    // Always succeed in dev mode
    return {
      user: MOCK_USER,
      token: MOCK_TOKENS.access_token,
    };
  }

  async signUp(data: SignUpData) {
    console.log('Dev mode: Mock signup with', data);
    
    // Simulate API delay
    await new Promise(resolve => setTimeout(resolve, 500));
    
    return {
      user: MOCK_USER,
      message: 'Dev mode: Account created successfully',
    };
  }

  async logout() {
    console.log('Dev mode: Mock logout');
    store.dispatch(logoutAction());
  }

  async resetPassword(email: string) {
    console.log('Dev mode: Mock password reset for', email);
    return { message: 'Dev mode: Password reset email sent' };
  }

  async updatePassword(_newPassword: string) {
    console.log('Dev mode: Mock password update');
    return { message: 'Dev mode: Password updated' };
  }

  async getSession() {
    return {
      user: MOCK_USER,
      access_token: MOCK_TOKENS.access_token,
      expires_at: Date.now() + 3600000, // 1 hour from now
    };
  }

  async refreshSession() {
    return this.getSession();
  }

  async isAuthenticated(): Promise<boolean> {
    return true; // Always authenticated in dev mode
  }
}

export const authService = new DevAuthService();