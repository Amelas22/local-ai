import { store } from '@/store/store';
import { loginSuccess, logout as logoutAction } from '@/store/slices/authSlice';
import type { LoginCredentials, SignUpData } from './auth.service';

// Mock user for development
const MOCK_USER = {
  id: 'dev-user-123',
  email: 'dev@clerk.ai',
  name: 'Development User',
  role: 'admin',
};

const MOCK_TOKEN = 'dev-token-123456';

class DevAuthService {
  constructor() {
    // Automatically log in the dev user
    setTimeout(() => {
      store.dispatch(loginSuccess({
        user: MOCK_USER,
        token: MOCK_TOKEN,
      }));
    }, 100);
  }

  async login(credentials: LoginCredentials) {
    console.log('Dev mode: Mock login with', credentials);
    
    // Simulate API delay
    await new Promise(resolve => setTimeout(resolve, 500));
    
    // Always succeed in dev mode
    return {
      user: MOCK_USER,
      token: MOCK_TOKEN,
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
      access_token: MOCK_TOKEN,
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