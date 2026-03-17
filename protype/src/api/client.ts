/**
 * API client for TokenMachine backend.
 *
 * This module provides HTTP client functions for communicating
 * with the backend API.
 */

import config from '../config/env';

/**
 * API request options
 */
interface RequestOptions {
  method?: 'GET' | 'POST' | 'PUT' | 'DELETE' | 'PATCH';
  headers?: Record<string, string>;
  body?: any;
  timeout?: number;
  signal?: AbortSignal;
}

/**
 * API response
 */
interface ApiResponse<T = any> {
  data?: T;
  error?: string;
  status: number;
  headers: Headers;
}

/**
 * API error
 */
export class ApiError extends Error {
  status: number;
  statusText: string;
  data?: any;

  constructor(status: number, statusText: string, data?: any) {
    super(`API Error ${status}: ${statusText}`);
    this.name = 'ApiError';
    this.status = status;
    this.statusText = statusText;
    this.data = data;
  }
}

/**
 * Build full URL for API endpoint
 */
const buildUrl = (endpoint: string): string => {
  const baseUrl = config.apiBaseUrl;
  // Remove leading slash from endpoint if present
  const path = endpoint.startsWith('/') ? endpoint.slice(1) : endpoint;
  // Ensure baseUrl doesn't end with slash
  const base = baseUrl.endsWith('/') ? baseUrl.slice(0, -1) : baseUrl;
  return `${base}/${path}`;
};

/**
 * Perform API request
 */
export const request = async <T = any>(
  endpoint: string,
  options: RequestOptions = {}
): Promise<ApiResponse<T>> => {
  const {
    method = 'GET',
    headers = {},
    body,
    timeout = config.apiTimeout,
    signal,
  } = options;

  const url = buildUrl(endpoint);

  // Build request headers
  const requestHeaders: Record<string, string> = {
    'Content-Type': 'application/json',
    ...headers,
  };

  // Add authorization header if token exists
  const token = localStorage.getItem('auth_token');
  if (token) {
    requestHeaders['Authorization'] = `Bearer ${token}`;
  }

  // Build request init
  const requestInit: RequestInit = {
    method,
    headers: requestHeaders,
  };

  if (body) {
    requestInit.body = JSON.stringify(body);
  }

  // Create abort controller for timeout
  const controller = new AbortController();
  const timeoutId = setTimeout(() => controller.abort(), timeout);

  try {
    const response = await fetch(url, {
      ...requestInit,
      signal: signal || controller.signal,
    });

    clearTimeout(timeoutId);

    const responseData = response.headers.get('content-type')?.includes('application/json')
      ? await response.json().catch(() => null)
      : await response.text().catch(() => null);

    if (!response.ok) {
      throw new ApiError(
        response.status,
        response.statusText,
        responseData
      );
    }

    return {
      data: responseData,
      status: response.status,
      headers: response.headers,
    };
  } catch (error) {
    clearTimeout(timeoutId);

    if (error instanceof ApiError) {
      throw error;
    }

    if (error instanceof Error) {
      if (error.name === 'AbortError') {
        throw new ApiError(408, 'Request Timeout');
      }
      throw new ApiError(0, error.message);
    }

    throw new ApiError(0, 'Unknown error');
  }
};

/**
 * Convenience methods
 */
export const api = {
  get: <T = any>(endpoint: string, options?: Omit<RequestOptions, 'method'>) =>
    request<T>(endpoint, { ...options, method: 'GET' }),

  post: <T = any>(endpoint: string, data?: any, options?: Omit<RequestOptions, 'method' | 'body'>) =>
    request<T>(endpoint, { ...options, method: 'POST', body: data }),

  put: <T = any>(endpoint: string, data?: any, options?: Omit<RequestOptions, 'method' | 'body'>) =>
    request<T>(endpoint, { ...options, method: 'PUT', body: data }),

  patch: <T = any>(endpoint: string, data?: any, options?: Omit<RequestOptions, 'method' | 'body'>) =>
    request<T>(endpoint, { ...options, method: 'PATCH', body: data }),

  delete: <T = any>(endpoint: string, options?: Omit<RequestOptions, 'method'>) =>
    request<T>(endpoint, { ...options, method: 'DELETE' }),
};

export default api;
