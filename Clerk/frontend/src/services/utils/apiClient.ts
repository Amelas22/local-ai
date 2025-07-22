import axios from 'axios';
import type { AxiosInstance, AxiosRequestConfig, AxiosError, AxiosResponse } from 'axios';
import { store } from '@/store/store';
import { addToast } from '@/store/slices/uiSlice';
import { tokenService } from '@/services/token.service';
import { authServiceManager } from '@/services/auth.service';
import { logout } from '@/store/slices/authSlice';

interface RetryConfig {
  retries?: number;
  retryDelay?: number;
  retryCondition?: (error: AxiosError) => boolean;
}

class ApiClient {
  private client: AxiosInstance;
  private isRefreshing = false;
  private failedQueue: Array<{
    resolve: (token: string) => void;
    reject: (error: any) => void;
  }> = [];
  private readonly defaultRetryConfig: RetryConfig = {
    retries: 3,
    retryDelay: 1000,
    retryCondition: (error) => {
      // Retry on network errors or 5xx errors
      return !error.response || (error.response.status >= 500 && error.response.status < 600);
    },
  };

  constructor() {
    // Get base URL from import.meta.environment
    const baseURL = import.meta.env.VITE_API_URL || '';
    
    this.client = axios.create({
      baseURL,
      timeout: 30000, // 30 seconds
      headers: {
        'Content-Type': 'application/json',
      },
    });

    // Request interceptor to add auth token and case ID
    this.client.interceptors.request.use(
      async (config) => {
        // MVP Mode: Skip auth header entirely
        const isMvpMode = import.meta.env.VITE_MVP_MODE === 'true';
        
        if (isMvpMode) {
          // In MVP mode, no auth needed
          console.log('[API Client] MVP Mode active - skipping auth header');
        } else {
          // Normal auth flow
          // Ensure auth service is initialized before making requests
          if (!authServiceManager.isReady()) {
            console.log('Waiting for auth service initialization...');
            await authServiceManager.getAuthService();
          }

          // Add auth token from tokenService
          const token = tokenService.getAccessToken();
          if (token) {
            config.headers['Authorization'] = `Bearer ${token}`;
            // Log token injection in development
            if (import.meta.env.DEV) {
              console.log(`[API Client] Added auth token to ${config.url}`);
            }
          } else if (import.meta.env.DEV) {
            console.warn(`[API Client] No auth token available for ${config.url}`);
          }
        }
        
        // Add case ID from localStorage (works in both MVP and normal mode)
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

    // Response interceptor for error handling and token refresh
    this.client.interceptors.response.use(
      (response) => response,
      async (error) => {
        const originalRequest = error.config;
        
        // Handle 401 Unauthorized with token refresh
        if (error.response?.status === 401 && !originalRequest._retry) {
          // MVP Mode: Never handle 401, just pass through
          if (import.meta.env.VITE_MVP_MODE === 'true') {
            console.log('[API Client] MVP Mode - ignoring 401 error');
            return Promise.reject(error);
          }
          
          if (this.isRefreshing) {
            // Token refresh is already in progress, queue this request
            return new Promise((resolve, reject) => {
              this.failedQueue.push({ resolve, reject });
            }).then((token) => {
              originalRequest.headers.Authorization = `Bearer ${token}`;
              return this.client(originalRequest);
            }).catch((err) => {
              return Promise.reject(err);
            });
          }
          
          originalRequest._retry = true;
          this.isRefreshing = true;
          
          try {
            // Get auth service instance
            const authService = await authServiceManager.getAuthService();
            
            // In development mode with auth disabled, skip refresh
            if (import.meta.env.VITE_AUTH_ENABLED !== 'true') {
              console.log('[API Client] Auth disabled in dev mode, skipping token refresh');
              const currentToken = tokenService.getAccessToken();
              if (currentToken) {
                this.processQueue(null, currentToken);
                originalRequest.headers.Authorization = `Bearer ${currentToken}`;
                return this.client(originalRequest);
              }
            }
            
            // Attempt token refresh
            const tokens = await authService.refreshAccessToken();
            this.processQueue(null, tokens.access_token);
            
            originalRequest.headers.Authorization = `Bearer ${tokens.access_token}`;
            return this.client(originalRequest);
          } catch (refreshError) {
            this.processQueue(refreshError, null);
            
            // In development mode, don't logout on 401
            if (import.meta.env.VITE_AUTH_ENABLED === 'true') {
              // Refresh failed, logout user
              store.dispatch(logout());
              tokenService.clearTokens();
              
              // Redirect to login
              window.location.href = '/login';
            } else {
              console.error('[API Client] Token refresh failed in dev mode:', refreshError);
            }
            
            return Promise.reject(refreshError);
          } finally {
            this.isRefreshing = false;
          }
        }
        
        // Check if we should retry for other errors
        if (this.shouldRetry(error, originalRequest)) {
          originalRequest._retryCount = (originalRequest._retryCount || 0) + 1;
          
          // Calculate delay with exponential backoff
          const delay = this.calculateRetryDelay(originalRequest._retryCount, originalRequest._retryDelay);
          
          console.log(`Retrying request (attempt ${originalRequest._retryCount}/${originalRequest._maxRetries}) after ${delay}ms`);
          
          await this.delay(delay);
          return this.client(originalRequest);
        }

        // Handle specific error cases
        this.handleError(error);
        return Promise.reject(error);
      }
    );
  }

  private shouldRetry(error: AxiosError, config: any): boolean {
    const retryCount = config._retryCount || 0;
    const maxRetries = config._maxRetries || this.defaultRetryConfig.retries;
    const retryCondition = config._retryCondition || this.defaultRetryConfig.retryCondition;

    return retryCount < maxRetries! && retryCondition!(error);
  }

  private calculateRetryDelay(retryCount: number, baseDelay?: number): number {
    const delay = baseDelay || this.defaultRetryConfig.retryDelay!;
    // Exponential backoff with jitter
    const exponentialDelay = delay * Math.pow(2, retryCount - 1);
    const jitter = Math.random() * 1000; // Add up to 1 second of jitter
    return Math.min(exponentialDelay + jitter, 30000); // Max 30 seconds
  }

  private delay(ms: number): Promise<void> {
    return new Promise((resolve) => setTimeout(resolve, ms));
  }

  private processQueue(error: any, token: string | null = null): void {
    this.failedQueue.forEach((prom) => {
      if (error) {
        prom.reject(error);
      } else {
        prom.resolve(token!);
      }
    });
    
    this.failedQueue = [];
  }

  private handleError(error: AxiosError): void {
    if (!error.response) {
      // Network error
      store.dispatch(addToast({
        message: 'Network error. Please check your connection and try again.',
        severity: 'error',
      }));
    } else if (error.response.status === 403) {
      // Forbidden
      store.dispatch(addToast({
        message: 'You do not have permission to perform this action.',
        severity: 'error',
      }));
    } else if (error.response.status === 404) {
      // Not found
      store.dispatch(addToast({
        message: 'The requested resource was not found.',
        severity: 'error',
      }));
    } else if (error.response.status >= 500) {
      // Server error
      store.dispatch(addToast({
        message: 'Server error. Please try again later.',
        severity: 'error',
      }));
    }
  }

  // HTTP methods with retry support
  async get<T = any>(url: string, config?: AxiosRequestConfig & RetryConfig): Promise<AxiosResponse<T>> {
    return this.request<T>({ ...config, method: 'GET', url });
  }

  async post<T = any>(url: string, data?: any, config?: AxiosRequestConfig & RetryConfig): Promise<AxiosResponse<T>> {
    return this.request<T>({ ...config, method: 'POST', url, data });
  }

  async put<T = any>(url: string, data?: any, config?: AxiosRequestConfig & RetryConfig): Promise<AxiosResponse<T>> {
    return this.request<T>({ ...config, method: 'PUT', url, data });
  }

  async delete<T = any>(url: string, config?: AxiosRequestConfig & RetryConfig): Promise<AxiosResponse<T>> {
    return this.request<T>({ ...config, method: 'DELETE', url });
  }

  async patch<T = any>(url: string, data?: any, config?: AxiosRequestConfig & RetryConfig): Promise<AxiosResponse<T>> {
    return this.request<T>({ ...config, method: 'PATCH', url, data });
  }

  private async request<T = any>(config: AxiosRequestConfig & RetryConfig): Promise<AxiosResponse<T>> {
    // Add retry configuration to the request
    const requestConfig = {
      ...config,
      _maxRetries: config.retries || this.defaultRetryConfig.retries,
      _retryDelay: config.retryDelay || this.defaultRetryConfig.retryDelay,
      _retryCondition: config.retryCondition || this.defaultRetryConfig.retryCondition,
    };

    return this.client.request<T>(requestConfig);
  }

  // Method to create a new instance with different configuration
  createInstance(config: AxiosRequestConfig): AxiosInstance {
    return axios.create({ ...this.client.defaults, ...config });
  }
}

// Export singleton instance
export const apiClient = new ApiClient();

// Export types for use in other files
export type { RetryConfig, AxiosError, AxiosResponse };