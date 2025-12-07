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

/**
 * Get full user profile
 */
export async function getProfile() {
  const response = await apiClient.get('/auth/profile');
  return response.data;
}

/**
 * Update user profile
 */
export async function updateProfile(profileData) {
  console.log('[authApi] updateProfile called with:', profileData);
  const response = await apiClient.put('/auth/profile', profileData);
  console.log('[authApi] updateProfile response:', response.data);
  return response.data;
}

/**
 * Change user password
 */
export async function changePassword(currentPassword, newPassword, confirmPassword) {
  const response = await apiClient.put('/auth/password', {
    current_password: currentPassword,
    new_password: newPassword,
    confirm_password: confirmPassword,
  });
  return response.data;
}

export default {
  register,
  login,
  getMe,
  getProfile,
  updateProfile,
  changePassword,
};
