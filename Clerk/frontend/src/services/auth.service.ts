import { supabase } from './supabase';
import { store } from '../store/store';
import { loginSuccess, loginFailure, logout as logoutAction } from '../store/slices/authSlice';

export interface LoginCredentials {
  email: string;
  password: string;
}

export interface SignUpData extends LoginCredentials {
  name: string;
}

class AuthService {
  constructor() {
    // Set up auth state listener
    supabase.auth.onAuthStateChange(async (event, session) => {
      if (event === 'SIGNED_IN' && session) {
        // Fetch user profile from database
        const { data: userData } = await supabase
          .from('users')
          .select('*')
          .eq('id', session.user.id)
          .single();

        if (userData) {
          store.dispatch(loginSuccess({
            user: {
              id: userData.id,
              email: userData.email,
              name: userData.name,
              role: userData.role,
            },
            token: session.access_token,
          }));
        }
      } else if (event === 'SIGNED_OUT') {
        store.dispatch(logoutAction());
      }
    });
  }

  async login(credentials: LoginCredentials) {
    try {
      const { data, error } = await supabase.auth.signInWithPassword({
        email: credentials.email,
        password: credentials.password,
      });

      if (error) throw error;

      if (data.user && data.session) {
        // Fetch user profile
        const { data: userData, error: profileError } = await supabase
          .from('users')
          .select('*')
          .eq('id', data.user.id)
          .single();

        if (profileError) throw profileError;

        // Track session start
        await supabase.from('user_sessions').insert({
          user_id: data.user.id,
          started_at: new Date().toISOString(),
        });

        return {
          user: {
            id: userData.id,
            email: userData.email,
            name: userData.name,
            role: userData.role,
          },
          token: data.session.access_token,
        };
      }

      throw new Error('Login failed');
    } catch (error) {
      store.dispatch(loginFailure(error instanceof Error ? error.message : 'Login failed'));
      throw error;
    }
  }

  async signUp(data: SignUpData) {
    try {
      // Sign up with Supabase Auth
      const { data: authData, error: authError } = await supabase.auth.signUp({
        email: data.email,
        password: data.password,
      });

      if (authError) throw authError;

      if (authData.user) {
        // Create user profile in database
        const { error: profileError } = await supabase.from('users').insert({
          id: authData.user.id,
          email: data.email,
          name: data.name,
          role: 'user', // Default role
        });

        if (profileError) throw profileError;

        return {
          user: authData.user,
          message: 'Please check your email to confirm your account.',
        };
      }

      throw new Error('Sign up failed');
    } catch (error) {
      throw error;
    }
  }

  async logout() {
    try {
      const session = await this.getSession();
      if (session?.user) {
        // Update session end time
        await supabase
          .from('user_sessions')
          .update({ ended_at: new Date().toISOString() })
          .eq('user_id', session.user.id)
          .is('ended_at', null);
      }

      const { error } = await supabase.auth.signOut();
      if (error) throw error;
    } catch (error) {
      console.error('Logout error:', error);
      throw error;
    }
  }

  async resetPassword(email: string) {
    try {
      const { error } = await supabase.auth.resetPasswordForEmail(email, {
        redirectTo: `${window.location.origin}/reset-password`,
      });

      if (error) throw error;

      return { message: 'Password reset email sent. Please check your inbox.' };
    } catch (error) {
      throw error;
    }
  }

  async updatePassword(newPassword: string) {
    try {
      const { error } = await supabase.auth.updateUser({
        password: newPassword,
      });

      if (error) throw error;

      return { message: 'Password updated successfully.' };
    } catch (error) {
      throw error;
    }
  }

  async getSession() {
    const { data: { session } } = await supabase.auth.getSession();
    return session;
  }

  async refreshSession() {
    const { data: { session }, error } = await supabase.auth.refreshSession();
    if (error) throw error;
    return session;
  }

  async isAuthenticated(): Promise<boolean> {
    const session = await this.getSession();
    return !!session;
  }
}

// Export the auth service based on environment
export let authService: AuthService;

// Initialize auth service based on environment
if (import.meta.env.VITE_AUTH_ENABLED === 'true') {
  authService = new AuthService();
} else {
  // In development, use mock auth service
  console.log('Auth disabled - using development auth service');
  import('./auth.service.dev').then(module => {
    authService = module.authService as any;
  });
}