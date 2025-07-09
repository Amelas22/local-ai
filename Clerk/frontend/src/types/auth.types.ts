/**
 * Authentication type definitions for JWT-based authentication.
 */

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

export interface SignUpData extends LoginCredentials {
  name: string;
  law_firm_id: string;
}

export interface AuthState {
  isAuthenticated: boolean;
  user: User | null;
  token: string | null;
  refreshToken: string | null;
  isLoading: boolean;
  error: string | null;
  initialized: boolean;
  initializing: boolean;
}

export interface AuthError {
  status: number;
  message: string;
  detail?: string;
}