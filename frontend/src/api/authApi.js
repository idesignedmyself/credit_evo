/**
 * Credit Engine 2.0 - Auth API
 * Authentication endpoints (register, login, me)
 */
import apiClient from './apiClient';

/**
 * Register a new user
 */
export async function register(email, username, password) {
  const response = await apiClient.post('/auth/register', {
    email,
    username,
    password,
  });
  return response.data;
}

/**
 * Login user and get JWT token
 */
export async function login(email, password) {
  const response = await apiClient.post('/auth/login', {
    email,
    password,
  });
  return response.data;
}

/**
 * Get current user info
 */
export async function getMe() {
  const response = await apiClient.get('/auth/me');
  return response.data;
}

export default {
  register,
  login,
  getMe,
};
