/**
 * Dispute System API
 * Endpoints for enforcement automation system
 */
import apiClient from './apiClient';

// =============================================================================
// DISPUTE MANAGEMENT
// =============================================================================

/**
 * Create a new dispute
 */
export const createDispute = async (disputeData) => {
  const response = await apiClient.post('/disputes', disputeData);
  return response.data;
};

/**
 * Create a dispute from a generated letter
 * Creates dispute in "pending tracking" state - clock doesn't start until user calls startTracking
 */
export const createDisputeFromLetter = async (letterId, letterData) => {
  const disputeData = {
    letter_id: letterId,
    entity_type: letterData.entity_type || 'CRA',
    entity_name: letterData.entity_name || letterData.bureau,
    // Don't set dispute_date - user will set it when they start tracking
    dispute_date: null,
    source: letterData.source || 'DIRECT',
    violation_ids: letterData.violation_ids || [],
    violation_data: letterData.violation_data || null,
  };
  const response = await apiClient.post('/disputes', disputeData);
  return response.data;
};

/**
 * Start tracking a dispute (set the send date and start the deadline clock)
 */
export const startTracking = async (disputeId, sendDate, trackingNumber = null) => {
  const response = await apiClient.post(`/disputes/${disputeId}/confirm-sent`, {
    mailed_date: sendDate,
    tracking_number: trackingNumber,
  });
  return response.data;
};

/**
 * Get dispute counts by tier
 * @returns {Object} { tier_0, tier_1, tier_2, total }
 */
export const getDisputeCounts = async () => {
  const response = await apiClient.get('/disputes/counts');
  return response.data;
};

/**
 * Get all disputes for current user
 * @param {Object} filters - Optional filters
 * @param {string} filters.status - Filter by status
 * @param {string} filters.state - Filter by escalation state
 * @param {number} filters.tier - Filter by tier (0=initial, 1=response, 2=final)
 */
export const getDisputes = async (filters = {}) => {
  const params = new URLSearchParams();
  if (filters.status) params.append('status', filters.status);
  if (filters.state) params.append('state', filters.state);
  if (filters.tier !== undefined && filters.tier !== null) params.append('tier', filters.tier);

  const response = await apiClient.get(`/disputes?${params.toString()}`);
  return response.data;
};

/**
 * Get a specific dispute
 */
export const getDispute = async (disputeId) => {
  const response = await apiClient.get(`/disputes/${disputeId}`);
  return response.data;
};

/**
 * Get dispute timeline (paper trail)
 */
export const getDisputeTimeline = async (disputeId) => {
  const response = await apiClient.get(`/disputes/${disputeId}/timeline`);
  return response.data;
};

/**
 * Get dispute current state
 */
export const getDisputeState = async (disputeId) => {
  const response = await apiClient.get(`/disputes/${disputeId}/state`);
  return response.data;
};

/**
 * Get system-triggered events for a dispute
 */
export const getSystemEvents = async (disputeId) => {
  const response = await apiClient.get(`/disputes/${disputeId}/system-events`);
  return response.data;
};

/**
 * Get available artifacts for current state
 */
export const getAvailableArtifacts = async (disputeId) => {
  const response = await apiClient.get(`/disputes/${disputeId}/artifacts`);
  return response.data;
};

// =============================================================================
// RESPONSE LOGGING
// =============================================================================

/**
 * Log an entity response
 */
export const logResponse = async (disputeId, responseData) => {
  const response = await apiClient.post(`/disputes/${disputeId}/response`, responseData);
  return response.data;
};

/**
 * Confirm letter was mailed
 */
export const confirmMailing = async (disputeId, mailingData) => {
  const response = await apiClient.post(`/disputes/${disputeId}/confirm-sent`, mailingData);
  return response.data;
};

/**
 * Log reinsertion notice received
 */
export const logReinsertionNotice = async (disputeId, noticeData) => {
  const response = await apiClient.post(`/disputes/${disputeId}/reinsertion-notice`, noticeData);
  return response.data;
};

/**
 * Mark Tier-2 supervisory notice as sent
 * This is the authoritative event that transitions the dispute to Tier-2.
 * After this, the Tier-2 adjudication UI becomes visible.
 * @param {string} disputeId - ID of the dispute
 */
export const markTier2NoticeSent = async (disputeId) => {
  const response = await apiClient.post(`/disputes/${disputeId}/mark-tier2-sent`);
  return response.data;
};

/**
 * Log final Tier-2 supervisory response
 * Tier-2 is exhausted after exactly ONE response evaluation.
 * - CURED → Close as CURED_AT_TIER_2
 * - Others → Auto-promote to Tier-3 (lock + classify + ledger write)
 * @param {string} disputeId - ID of the dispute
 * @param {Object} responseData - Tier-2 response data
 * @param {string} responseData.response_type - CURED, REPEAT_VERIFIED, DEFLECTION_FRIVOLOUS, NO_RESPONSE_AFTER_CURE_WINDOW
 * @param {string} responseData.response_date - Date response was received (YYYY-MM-DD)
 */
export const logTier2Response = async (disputeId, responseData) => {
  const response = await apiClient.post(`/disputes/${disputeId}/tier2-response`, {
    response_type: responseData.response_type,
    response_date: responseData.response_date,
  });
  return response.data;
};

/**
 * Delete a dispute
 */
export const deleteDispute = async (disputeId) => {
  const response = await apiClient.delete(`/disputes/${disputeId}`);
  return response.data;
};

// =============================================================================
// ARTIFACT GENERATION
// =============================================================================

/**
 * Request artifact generation
 */
export const requestArtifact = async (disputeId, artifactType) => {
  const response = await apiClient.post(`/disputes/${disputeId}/artifacts?artifact_type=${artifactType}`);
  return response.data;
};

// =============================================================================
// RESPONSE LETTER GENERATION
// =============================================================================

/**
 * Generate a response/enforcement letter based on dispute state
 * @param {string} disputeId - ID of the dispute
 * @param {Object} options - Letter generation options
 * @param {string} options.letter_type - Type of letter (enforcement, follow_up, mov_demand, reinsertion)
 * @param {string} options.response_type - Response type to generate letter for (NO_RESPONSE, VERIFIED, etc.)
 * @param {string} options.violation_id - Specific violation to generate letter for
 * @param {boolean} options.include_willful_notice - Include willful noncompliance notice under §616
 * @param {boolean} options.test_context - Test mode: bypasses deadline, appends test footer, blocks save/mail
 */
export const generateResponseLetter = async (disputeId, options = {}) => {
  const response = await apiClient.post(`/disputes/${disputeId}/generate-response-letter`, {
    letter_type: options.letter_type || 'enforcement',
    response_type: options.response_type || null,
    violation_id: options.violation_id || null,
    include_willful_notice: options.include_willful_notice !== false, // Default true
    test_context: options.test_context || false,
  });
  return response.data;
};

/**
 * Audit an enforcement letter for regulatory compliance
 * @param {string} disputeId - ID of the dispute
 * @param {Object} options - Audit options
 * @param {string} options.letter_content - Full letter text to audit
 * @param {boolean} options.strict_mode - If true, removes speculative language; if false, only flags it
 */
export const auditLetter = async (disputeId, options = {}) => {
  const response = await apiClient.post(`/disputes/${disputeId}/audit-letter`, {
    letter_content: options.letter_content,
    strict_mode: options.strict_mode !== false, // Default true
  });
  return response.data;
};

/**
 * Save a response/enforcement letter to the letters table
 * @param {string} disputeId - ID of the dispute
 * @param {Object} options - Save options
 * @param {string} options.content - Letter content to save
 * @param {string} options.response_type - Response type (NO_RESPONSE, VERIFIED, etc.)
 * @param {string} options.violation_id - Specific violation this letter addresses
 * @param {boolean} options.test_context - If true, will be blocked - test letters cannot be saved
 */
export const saveResponseLetter = async (disputeId, options = {}) => {
  const response = await apiClient.post(`/disputes/${disputeId}/save-response-letter`, {
    content: options.content,
    response_type: options.response_type,
    violation_id: options.violation_id || null,
    test_context: options.test_context || false,
  });
  return response.data;
};

/**
 * Letter type options for UI
 */
export const LETTER_TYPES = {
  enforcement: { value: 'enforcement', label: 'Enforcement Letter', description: 'General enforcement correspondence' },
  follow_up: { value: 'follow_up', label: 'Follow-Up Letter', description: 'Follow-up to previous correspondence' },
  mov_demand: { value: 'mov_demand', label: 'Method of Verification Demand', description: 'Demand disclosure of verification method' },
  reinsertion: { value: 'reinsertion', label: 'Reinsertion Violation Notice', description: 'Notice of reinsertion without proper notice' },
};

// =============================================================================
// CONSTANTS
// =============================================================================

export const ENTITY_TYPES = {
  CRA: 'CRA',
  FURNISHER: 'FURNISHER',
  COLLECTOR: 'COLLECTOR',
};

export const ENTITY_NAMES = {
  CRA: ['Equifax', 'Experian', 'TransUnion'],
  FURNISHER: [], // Populated from violations
  COLLECTOR: [], // Populated from violations
};

// ENFORCEMENT-READY response types only
// INVESTIGATING and UPDATED are states, not enforcement outcomes - removed from UI
export const RESPONSE_TYPES = {
  DELETED: { value: 'DELETED', label: 'Deleted', description: 'Entity removed the disputed item', enforcement: false },
  VERIFIED: { value: 'VERIFIED', label: 'Verified', description: 'Entity claims information is accurate', enforcement: true },
  NO_RESPONSE: { value: 'NO_RESPONSE', label: 'No Response', description: 'Deadline passed with no communication', enforcement: true },
  REJECTED: { value: 'REJECTED', label: 'Rejected / Frivolous', description: 'Entity refuses to investigate', enforcement: true },
  REINSERTION: { value: 'REINSERTION', label: 'Reinsertion', description: 'Previously deleted item reappeared without notice', enforcement: true },
};

// For dropdowns that should only show enforcement-ready outcomes
export const ENFORCEMENT_OUTCOMES = Object.fromEntries(
  Object.entries(RESPONSE_TYPES).filter(([_, v]) => v.enforcement)
);

export const DISPUTE_SOURCES = {
  DIRECT: { value: 'DIRECT', label: 'Direct to Entity', days: 30 },
  ANNUAL_CREDIT_REPORT: { value: 'ANNUAL_CREDIT_REPORT', label: 'AnnualCreditReport.com', days: 45 },
};

export const ESCALATION_STATES = {
  DETECTED: { label: 'Detected', tone: 'informational', color: 'info' },
  DISPUTED: { label: 'Disputed', tone: 'informational', color: 'info' },
  RESPONDED: { label: 'Responded', tone: 'informational', color: 'info' },
  NO_RESPONSE: { label: 'No Response', tone: 'assertive', color: 'warning' },
  EVALUATED: { label: 'Evaluated', tone: 'informational', color: 'info' },
  NON_COMPLIANT: { label: 'Non-Compliant', tone: 'assertive', color: 'error' },
  PROCEDURAL_ENFORCEMENT: { label: 'Procedural Enforcement', tone: 'enforcement', color: 'error' },
  SUBSTANTIVE_ENFORCEMENT: { label: 'Substantive Enforcement', tone: 'enforcement', color: 'error' },
  REGULATORY_ESCALATION: { label: 'Regulatory Escalation', tone: 'regulatory', color: 'error' },
  LITIGATION_READY: { label: 'Litigation Ready', tone: 'litigation', color: 'error' },
  RESOLVED_DELETED: { label: 'Resolved - Deleted', tone: 'informational', color: 'success' },
  RESOLVED_CURED: { label: 'Resolved - Cured', tone: 'informational', color: 'success' },
};

// Tier-2 Supervisory Response Types
// Used after Tier-2 letter has been sent - final response evaluation
export const TIER2_RESPONSE_TYPES = {
  CURED: {
    value: 'CURED',
    label: 'Cured',
    description: 'Entity corrected the violation',
    outcome: 'close',
  },
  REPEAT_VERIFIED: {
    value: 'REPEAT_VERIFIED',
    label: 'Repeat Verified',
    description: 'Entity re-verified without correction',
    outcome: 'tier3',
  },
  DEFLECTION_FRIVOLOUS: {
    value: 'DEFLECTION_FRIVOLOUS',
    label: 'Deflection / Frivolous',
    description: 'Entity called dispute frivolous',
    outcome: 'tier3',
  },
  NO_RESPONSE_AFTER_CURE_WINDOW: {
    value: 'NO_RESPONSE_AFTER_CURE_WINDOW',
    label: 'No Response (Cure Window)',
    description: 'Entity failed to respond within cure window',
    outcome: 'tier3',
  },
};
