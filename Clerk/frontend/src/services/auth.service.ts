import axios from 'axios';
import { store } from '../store/store';
import { loginStart, loginSuccess, loginFailure, logout as logoutAction } from '../store/slices/authSlice';
import { tokenService } from './token.service';
import type { TokenResponse, User, LoginCredentials, SignUpData } from '@/types/auth.types';
export type { LoginCredentials, SignUpData } from '@/types/auth.types';

class AuthService {
  private baseURL: string;

  constructor() {
    this.baseURL = import.meta.env.VITE_API_URL || '';
    // Check for existing tokens on initialization
    this.initializeAuth();
  }

  private async initializeAuth() {
    const accessToken = tokenService.getAccessToken();
    const refreshToken = tokenService.getRefreshToken();
    
    if (accessToken && refreshToken) {
      // Verify token is still valid
      if (!tokenService.isAccessTokenExpired()) {
        try {
          const user = await this.getCurrentUser();
          if (user) {
            store.dispatch(loginSuccess({
              user,
              token: accessToken,
              refreshToken
            }));
          }
        } catch (error) {
          // Token invalid, clear it
          tokenService.clearTokens();
        }
      }
    }
  }

  async login(credentials: LoginCredentials) {
    try {
      store.dispatch(loginStart());
      
      // Create FormData for OAuth2 compliance
      const formData = new URLSearchParams();
      formData.append('username', credentials.email); // OAuth2 uses 'username' field
      formData.append('password', credentials.password);

      // Make login request
      const response = await axios.post<TokenResponse>(
        `${this.baseURL}/api/auth/login`,
        formData,
        {
          headers: {
            'Content-Type': 'application/x-www-form-urlencoded',
          },
        }
      );

      const tokens = response.data;
      
      // Store tokens
      tokenService.setTokens(tokens);
      
      // Get user info
      const user = await this.getCurrentUser();
      
      // Update Redux state
      store.dispatch(loginSuccess({
        user,
        token: tokens.access_token,
        refreshToken: tokens.refresh_token
      }));

      return {
        user,
        token: tokens.access_token,
      };
    } catch (error: any) {
      const message = error.response?.data?.detail || error.message || 'Login failed';
      store.dispatch(loginFailure(message));
      throw new Error(message);
    }
  }

  async signUp(data: SignUpData) {
    try {
      // Make registration request
      const response = await axios.post(
        `${this.baseURL}/api/auth/register`,
        {
          email: data.email,
          password: data.password,
          name: data.name,
          law_firm_id: data.law_firm_id || 'default', // TODO: Get from context or form
        },
        {
          headers: {
            'Content-Type': 'application/json',
          },
        }
      );

      return {
        user: response.data,
        message: 'Account created successfully. Please log in.',
      };
    } catch (error: any) {
      const message = error.response?.data?.detail || error.message || 'Sign up failed';
      throw new Error(message);
    }
  }

  async logout() {
    try {
      const token = tokenService.getAccessToken();
      
      if (token) {
        // Call logout endpoint to revoke refresh tokens
        await axios.post(
          `${this.baseURL}/api/auth/logout`,
          {},
          {
            headers: {
              Authorization: `Bearer ${token}`,
            },
          }
        );
      }
    } catch (error) {
      // Log error but continue with local logout
      console.error('Logout error:', error);
    } finally {
      // Always clear local tokens and state
      tokenService.clearTokens();
      store.dispatch(logoutAction());
    }
  }

  async resetPassword(_email: string) {
    // TODO: Implement password reset when backend endpoint is available
    throw new Error('Password reset not yet implemented');
  }

  async updatePassword(currentPassword: string, newPassword: string) {
    try {
      const token = tokenService.getAccessToken();
      
      const response = await axios.post(
        `${this.baseURL}/api/auth/change-password`,
        {
          current_password: currentPassword,
          new_password: newPassword,
        },
        {
          headers: {
            Authorization: `Bearer ${token}`,
            'Content-Type': 'application/json',
          },
        }
      );

      return response.data;
    } catch (error: any) {
      const message = error.response?.data?.detail || error.message || 'Password update failed';
      throw new Error(message);
    }
  }

  async getCurrentUser(): Promise<User> {
    const token = tokenService.getAccessToken();
    
    if (!token) {
      throw new Error('No authentication token');
    }

    const response = await axios.get<User>(
      `${this.baseURL}/api/auth/me`,
      {
        headers: {
          Authorization: `Bearer ${token}`,
        },
      }
    );

    return response.data;
  }

  async refreshAccessToken(): Promise<TokenResponse> {
    const refreshToken = tokenService.getRefreshToken();
    
    if (!refreshToken) {
      throw new Error('No refresh token available');
    }

    const response = await axios.post<TokenResponse>(
      `${this.baseURL}/api/auth/refresh`,
      {
        refresh_token: refreshToken,
      },
      {
        headers: {
          'Content-Type': 'application/json',
        },
      }
    );

    const tokens = response.data;
    tokenService.setTokens(tokens);
    
    return tokens;
  }

  isAuthenticated(): boolean {
    return tokenService.hasTokens() && !tokenService.isAccessTokenExpired();
  }
}

// Create a promise-based auth service manager
class AuthServiceManager {
  private authServicePromise: Promise<AuthService>;
  private authServiceInstance: AuthService | null = null;

  constructor() {
    this.authServicePromise = this.initializeAuthService();
  }

  private async initializeAuthService(): Promise<AuthService> {
    if (import.meta.env.VITE_AUTH_ENABLED === 'true') {
      this.authServiceInstance = new AuthService();
    } else {
      // In development, use mock auth service
      console.log('Auth disabled - using development auth service');
      const module = await import('./auth.service.dev');
      this.authServiceInstance = module.authService as any;
      // Wait for dev auth to be ready
      await (this.authServiceInstance as any).waitForReady();
    }
    return this.authServiceInstance!;
  }

  async getAuthService(): Promise<AuthService> {
    if (this.authServiceInstance) {
      return this.authServiceInstance;
    }
    return this.authServicePromise;
  }

  // Convenience method to check if auth is ready
  isReady(): boolean {
    return this.authServiceInstance !== null;
  }
}

// Export a singleton instance
const authServiceManager = new AuthServiceManager();

// Export both the manager and a proxy that will wait for initialization
export { authServiceManager };

// Export a proxy that maintains backward compatibility but logs warnings
export const authService = new Proxy({} as AuthService, {
  get(_target, prop) {
    if (!authServiceManager.isReady()) {
      console.warn(`Auth service accessed before initialization. Property: ${String(prop)}`);
    }
    const service = (authServiceManager as any).authServiceInstance;
    if (service) {
      return service[prop];
    }
    throw new Error('Auth service not initialized. Use authServiceManager.getAuthService() for async initialization.');
  }
});