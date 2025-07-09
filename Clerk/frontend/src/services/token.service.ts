/**
 * Token management service for JWT authentication.
 * Handles secure storage and retrieval of access and refresh tokens.
 */

import { store } from '@/store/store';
import { updateTokens, logout } from '@/store/slices/authSlice';
import type { TokenResponse } from '@/types/auth.types';

class TokenService {
  private readonly ACCESS_TOKEN_KEY = 'clerk_access_token';
  private readonly REFRESH_TOKEN_KEY = 'clerk_refresh_token';

  /**
   * Store tokens in localStorage and update Redux state.
   */
  setTokens(tokens: TokenResponse): void {
    console.log('[TokenService] Setting tokens');
    localStorage.setItem(this.ACCESS_TOKEN_KEY, tokens.access_token);
    localStorage.setItem(this.REFRESH_TOKEN_KEY, tokens.refresh_token);
    
    // Update Redux store
    store.dispatch(updateTokens({
      accessToken: tokens.access_token,
      refreshToken: tokens.refresh_token
    }));
  }

  /**
   * Get the access token from localStorage.
   * In development mode without auth, returns the mock token.
   */
  getAccessToken(): string | null {
    const token = localStorage.getItem(this.ACCESS_TOKEN_KEY);
    
    // In dev mode without auth, use mock token
    if (import.meta.env.DEV && !import.meta.env.VITE_AUTH_ENABLED) {
      console.log('[TokenService] Dev mode - returning mock token');
      return 'dev-token-123456';
    }
    
    return token;
  }

  /**
   * Get the refresh token from localStorage.
   */
  getRefreshToken(): string | null {
    return localStorage.getItem(this.REFRESH_TOKEN_KEY);
  }

  /**
   * Clear all tokens from localStorage and Redux state.
   */
  clearTokens(): void {
    console.log('[TokenService] Clearing tokens');
    localStorage.removeItem(this.ACCESS_TOKEN_KEY);
    localStorage.removeItem(this.REFRESH_TOKEN_KEY);
    
    // Clear from Redux
    store.dispatch(logout());
  }

  /**
   * Check if we have valid tokens stored.
   */
  hasTokens(): boolean {
    return !!(this.getAccessToken() && this.getRefreshToken());
  }

  /**
   * Decode JWT token to get payload.
   * Note: This does not verify the token signature.
   */
  decodeToken(token: string): any {
    try {
      const base64Url = token.split('.')[1];
      const base64 = base64Url.replace(/-/g, '+').replace(/_/g, '/');
      const jsonPayload = decodeURIComponent(
        atob(base64)
          .split('')
          .map((c) => '%' + ('00' + c.charCodeAt(0).toString(16)).slice(-2))
          .join('')
      );
      return JSON.parse(jsonPayload);
    } catch (error) {
      console.error('Error decoding token:', error);
      return null;
    }
  }

  /**
   * Check if a token is expired.
   */
  isTokenExpired(token: string): boolean {
    const decoded = this.decodeToken(token);
    if (!decoded || !decoded.exp) {
      return true;
    }

    // Check if token is expired (with 30 second buffer)
    const now = Date.now() / 1000;
    return decoded.exp < now + 30;
  }

  /**
   * Check if the current access token is expired.
   */
  isAccessTokenExpired(): boolean {
    const token = this.getAccessToken();
    if (!token) {
      return true;
    }
    return this.isTokenExpired(token);
  }
}

// Export singleton instance
export const tokenService = new TokenService();