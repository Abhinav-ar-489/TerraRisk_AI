import axios from 'axios';

/**
 * TerraRisk AI - Centralized Production API Client
 * - Uses relative /api path (proxied by Vite in dev and Nginx in production),
 *   or custom VITE_API_BASE_URL when provided.
 * - Automatically injects JWT Bearer authorization header from localStorage.
 * - Handles unauthorized 401 session expirations gracefully.
 */

export const API_BASE_URL = import.meta.env.VITE_API_BASE_URL || '';

const api = axios.create({
  baseURL: API_BASE_URL,
  headers: {
    'Content-Type': 'application/json',
  },
  timeout: 30000,
});

// Request interceptor: Attach JWT token if available
api.interceptors.request.use(
  (config) => {
    const token = localStorage.getItem('terrarisk_token');
    if (token && !config.headers.Authorization) {
      config.headers.Authorization = `Bearer ${token.trim()}`;
    }
    return config;
  },
  (error) => Promise.reject(error)
);

// Response interceptor: Handle expired tokens
api.interceptors.response.use(
  (response) => response,
  (error) => {
    if (error.response && error.response.status === 401) {
      // Token is expired or invalid
      const hasToken = !!localStorage.getItem('terrarisk_token');
      if (hasToken) {
        console.warn('[API] Received 401 Unauthorized. Clearing expired session token.');
        localStorage.removeItem('terrarisk_token');
        localStorage.removeItem('terrarisk_user');
      }
    }
    return Promise.reject(error);
  }
);

export default api;
