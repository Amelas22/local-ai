import type { AxiosError } from 'axios';
import { store } from '@/store/store';
import { addToast } from '@/store/slices/uiSlice';

export interface ErrorDetail {
  message: string;
  code?: string;
  field?: string;
  details?: any;
}

export interface ApiErrorResponse {
  detail?: string | ErrorDetail | ErrorDetail[];
  message?: string;
  error?: string;
  errors?: ErrorDetail[];
}

export class ApiError extends Error {
  public statusCode?: number;
  public code?: string;
  public details?: any;

  constructor(message: string, statusCode?: number, code?: string, details?: any) {
    super(message);
    this.name = 'ApiError';
    this.statusCode = statusCode;
    this.code = code;
    this.details = details;
  }
}

export function parseApiError(error: AxiosError<ApiErrorResponse>): ApiError {
  if (!error.response) {
    return new ApiError('Network error. Please check your connection.', 0, 'NETWORK_ERROR');
  }

  const { status, data } = error.response;
  let message = 'An unexpected error occurred';
  let code = 'UNKNOWN_ERROR';
  let details = null;

  // Try to extract error message from various possible formats
  if (data) {
    if (typeof data.detail === 'string') {
      message = data.detail;
    } else if (Array.isArray(data.detail)) {
      message = data.detail.map((d) => (typeof d === 'string' ? d : d.message)).join(', ');
      details = data.detail;
    } else if (typeof data.detail === 'object' && data.detail.message) {
      message = data.detail.message;
      code = data.detail.code || code;
      details = data.detail;
    } else if (data.message) {
      message = data.message;
    } else if (data.error) {
      message = data.error;
    } else if (data.errors && Array.isArray(data.errors)) {
      message = data.errors.map((e) => e.message || e).join(', ');
      details = data.errors;
    }
  }

  // Add status-specific messages
  switch (status) {
    case 400:
      code = 'BAD_REQUEST';
      break;
    case 401:
      code = 'UNAUTHORIZED';
      message = message || 'Please log in to continue';
      break;
    case 403:
      code = 'FORBIDDEN';
      message = message || 'You do not have permission to perform this action';
      break;
    case 404:
      code = 'NOT_FOUND';
      message = message || 'The requested resource was not found';
      break;
    case 408:
      code = 'TIMEOUT';
      message = message || 'Request timed out. Please try again';
      break;
    case 409:
      code = 'CONFLICT';
      break;
    case 422:
      code = 'VALIDATION_ERROR';
      break;
    case 429:
      code = 'RATE_LIMITED';
      message = message || 'Too many requests. Please slow down';
      break;
    case 500:
      code = 'SERVER_ERROR';
      message = message || 'Internal server error. Please try again later';
      break;
    case 502:
      code = 'BAD_GATEWAY';
      message = message || 'Server is temporarily unavailable';
      break;
    case 503:
      code = 'SERVICE_UNAVAILABLE';
      message = message || 'Service is temporarily unavailable';
      break;
  }

  return new ApiError(message, status, code, details);
}

export function handleApiError(error: AxiosError<ApiErrorResponse>, showToast = true): ApiError {
  const apiError = parseApiError(error);

  if (showToast) {
    const severity = apiError.statusCode === 401 ? 'warning' : 'error';
    store.dispatch(
      addToast({
        message: apiError.message,
        severity,
      })
    );
  }

  // Log error for debugging
  console.error('API Error:', {
    message: apiError.message,
    statusCode: apiError.statusCode,
    code: apiError.code,
    details: apiError.details,
  });

  return apiError;
}

// Utility function to check if an error is retryable
export function isRetryableError(error: AxiosError): boolean {
  if (!error.response) {
    // Network errors are retryable
    return true;
  }

  const status = error.response.status;
  
  // These status codes are typically retryable
  const retryableStatuses = [
    408, // Request Timeout
    429, // Too Many Requests
    500, // Internal Server Error
    502, // Bad Gateway
    503, // Service Unavailable
    504, // Gateway Timeout
  ];

  return retryableStatuses.includes(status);
}

// Utility function to get user-friendly error messages
export function getUserFriendlyErrorMessage(error: ApiError): string {
  const errorMessages: Record<string, string> = {
    NETWORK_ERROR: 'Unable to connect to the server. Please check your internet connection.',
    UNAUTHORIZED: 'Your session has expired. Please log in again.',
    FORBIDDEN: 'You do not have permission to perform this action.',
    NOT_FOUND: 'The requested resource could not be found.',
    VALIDATION_ERROR: 'Please check your input and try again.',
    RATE_LIMITED: 'You are making too many requests. Please wait a moment and try again.',
    SERVER_ERROR: 'Something went wrong on our end. Please try again later.',
    SERVICE_UNAVAILABLE: 'The service is temporarily unavailable. Please try again later.',
  };

  return errorMessages[error.code || ''] || error.message;
}