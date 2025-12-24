/**
 * Copilot API
 * Endpoints for the Credit Copilot goal-oriented recommendation system
 */
import apiClient from './apiClient';

// =============================================================================
// GOALS
// =============================================================================

/**
 * Get all available credit goals
 * @returns {Promise<{goals: Array<{code: string, name: string, description: string}>}>}
 */
export const getGoals = async () => {
  const response = await apiClient.get('/copilot/goals');
  return response.data;
};

/**
 * Get target requirements for a specific goal
 * @param {string} goalCode - Goal code (e.g., 'mortgage', 'auto_loan')
 * @returns {Promise<Object>} Target state requirements
 */
export const getGoalRequirements = async (goalCode) => {
  const response = await apiClient.get(`/copilot/goals/${goalCode}/requirements`);
  return response.data;
};

// =============================================================================
// RECOMMENDATIONS
// =============================================================================

/**
 * Get copilot recommendation for a report
 * @param {string} reportId - Report ID
 * @param {string} [goal] - Optional goal override (uses user's saved goal if not provided)
 * @returns {Promise<Object>} Full recommendation with blockers, actions, skips
 */
export const getRecommendation = async (reportId, goal = null) => {
  const params = goal ? `?goal=${encodeURIComponent(goal)}` : '';
  const response = await apiClient.get(`/copilot/recommendation/${reportId}${params}`);
  return response.data;
};

/**
 * Get batched copilot recommendation organized by bureau and wave
 * @param {string} reportId - Report ID
 * @param {string} [goal] - Optional goal override
 * @returns {Promise<Object>} Batched recommendation with waves per bureau
 */
export const getBatchedRecommendation = async (reportId, goal = null) => {
  const params = goal ? `?goal=${encodeURIComponent(goal)}` : '';
  const response = await apiClient.get(`/copilot/recommendation/${reportId}/batched${params}`);
  return response.data;
};

// =============================================================================
// OVERRIDE LOGGING
// =============================================================================

/**
 * Log when user proceeds against Copilot advice
 * @param {Object} overrideData - Override details
 * @param {string} overrideData.dispute_session_id - Correlation ID for the session
 * @param {string} overrideData.copilot_version_id - Version hash of the recommendation
 * @param {string} overrideData.report_id - Report being analyzed
 * @param {string} [overrideData.violation_id] - Specific violation being overridden
 * @param {string} overrideData.copilot_advice - What Copilot recommended ('skip' | 'defer' | 'advised_against')
 * @param {string} overrideData.user_action - What user chose ('proceed' | 'include')
 * @returns {Promise<{status: string}>}
 */
export const logOverride = async (overrideData) => {
  const response = await apiClient.post('/copilot/override', overrideData);
  return response.data;
};

/**
 * Log batch-level override (e.g., proceeding with locked batch)
 * @param {Object} overrideData - Batch override details
 * @param {string} overrideData.batch_id - Batch ID being overridden
 * @param {string} overrideData.report_id - Report being analyzed
 * @param {string} overrideData.override_type - 'proceed_locked' | 'skip_recommended' | 'reorder'
 * @param {string} overrideData.copilot_advice - What Copilot recommended
 * @param {string} overrideData.user_action - What user chose to do
 * @returns {Promise<{status: string, batch_id: string, override_type: string}>}
 */
export const logBatchOverride = async (overrideData) => {
  const response = await apiClient.post('/copilot/override/batch', overrideData);
  return response.data;
};

// =============================================================================
// CONSTANTS
// =============================================================================

/**
 * Copilot achievability levels for UI display
 */
export const ACHIEVABILITY_LEVELS = {
  ACHIEVABLE: {
    value: 'ACHIEVABLE',
    label: 'Achievable',
    color: 'success',
    description: 'Goal is within reach with recommended actions',
  },
  CHALLENGING: {
    value: 'CHALLENGING',
    label: 'Challenging',
    color: 'warning',
    description: 'Goal requires significant effort but is possible',
  },
  UNLIKELY: {
    value: 'UNLIKELY',
    label: 'Unlikely',
    color: 'error',
    description: 'Major blockers prevent goal achievement',
  },
};

/**
 * Copilot violation status for badges
 */
export const VIOLATION_STATUS = {
  RECOMMENDED: {
    value: 'recommended',
    label: 'Recommended',
    color: 'success',
    emoji: '🟢',
    description: 'Copilot recommends disputing this item',
  },
  DEFERRED: {
    value: 'deferred',
    label: 'Deferred',
    color: 'warning',
    emoji: '🟡',
    description: 'Copilot suggests waiting on this item',
  },
  ADVISED_AGAINST: {
    value: 'advised_against',
    label: 'Advised Against',
    color: 'error',
    emoji: '🔴',
    description: 'Copilot advises against disputing this item',
  },
};

/**
 * Default export with all functions
 */
export default {
  getGoals,
  getGoalRequirements,
  getRecommendation,
  getBatchedRecommendation,
  logOverride,
  logBatchOverride,
  ACHIEVABILITY_LEVELS,
  VIOLATION_STATUS,
};
