/**
 * Credit Engine 2.0 - API Client
 * Base axios instance configured for backend communication
 * Includes JWT authentication interceptor
 */
import axios from 'axios';

const API_BASE_URL = import.meta.env.VITE_API_URL || 'http://localhost:8000';
const TOKEN_KEY = 'credit_engine_token';

const apiClient = axios.create({
  baseURL: API_BASE_URL,
  timeout: 30000,
  headers: {
    'Accept': 'application/json',
    'Content-Type': 'application/json',
  },
});

// Request interceptor for auth token and logging
apiClient.interceptors.request.use(
  (config) => {
    // Add auth token if available
    const token = localStorage.getItem(TOKEN_KEY);
    if (token) {
      config.headers.Authorization = `Bearer ${token}`;
    }

    console.log(`[API] ${config.method?.toUpperCase()} ${config.url}`);
    return config;
  },
  (error) => {
    console.error('[API] Request error:', error);
    return Promise.reject(error);
  }
);

// Response interceptor for error handling
apiClient.interceptors.response.use(
  (response) => {
    return response;
  },
  (error) => {
    const status = error.response?.status;
    const message = error.response?.data?.detail || error.message || 'An error occurred';

    // Handle 401 Unauthorized - redirect to login
    if (status === 401) {
      // Clear stored auth data
      localStorage.removeItem(TOKEN_KEY);
      localStorage.removeItem('credit_engine_user');

      // Redirect to login if not already there
      if (window.location.pathname !== '/login' && window.location.pathname !== '/register') {
        window.location.href = '/login';
      }
    }

    console.error('[API] Response error:', message);
    return Promise.reject(new Error(message));
  }
);

export default apiClient;
