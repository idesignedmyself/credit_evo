/**
 * Admin API
 * Read-only endpoints for the Admin Intelligence Console
 * All data sourced from Execution Ledger truth.
 */
import apiClient from './apiClient';

// =============================================================================
// DASHBOARD
// =============================================================================

/**
 * Get dashboard statistics
 * @returns {Promise<Object>} Dashboard stats from Execution Ledger
 */
export const getDashboardStats = async () => {
  const response = await apiClient.get('/admin/dashboard/stats');
  return response.data;
};

// =============================================================================
// USERS
// =============================================================================

/**
 * Get paginated list of users
 * @param {Object} options - Pagination and search options
 * @param {number} [options.page=1] - Page number
 * @param {number} [options.pageSize=20] - Items per page
 * @param {string} [options.search] - Search term
 * @returns {Promise<Object>} Paginated user list with metrics
 */
export const getUsers = async ({ page = 1, pageSize = 20, search = '' } = {}) => {
  const params = new URLSearchParams({
    page: page.toString(),
    page_size: pageSize.toString(),
  });
  if (search) {
    params.append('search', search);
  }
  const response = await apiClient.get(`/admin/users?${params}`);
  return response.data;
};

/**
 * Get detailed user view with timeline
 * @param {string} userId - User ID
 * @returns {Promise<Object>} User detail with execution timeline
 */
export const getUserDetail = async (userId) => {
  const response = await apiClient.get(`/admin/users/${userId}`);
  return response.data;
};

// =============================================================================
// DISPUTE INTELLIGENCE
// =============================================================================

/**
 * Get dispute intelligence analytics
 * @param {number} [days=90] - Time window in days
 * @returns {Promise<Object>} Population-level dispute analytics
 */
export const getDisputeIntelligence = async (days = 90) => {
  const response = await apiClient.get(`/admin/intelligence/disputes?days=${days}`);
  return response.data;
};

// =============================================================================
// COPILOT PERFORMANCE
// =============================================================================

/**
 * Get Copilot performance metrics
 * @param {number} [days=90] - Time window in days
 * @returns {Promise<Object>} Copilot follow/override rates and outcome comparison
 */
export const getCopilotPerformance = async (days = 90) => {
  const response = await apiClient.get(`/admin/copilot/performance?days=${days}`);
  return response.data;
};

/**
 * Default export with all functions
 */
export default {
  getDashboardStats,
  getUsers,
  getUserDetail,
  getDisputeIntelligence,
  getCopilotPerformance,
};
