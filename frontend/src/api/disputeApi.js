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
 * This starts the clock on the dispute tracking process
 */
export const createDisputeFromLetter = async (letterId, letterData) => {
  const disputeData = {
    letter_id: letterId,
    entity_type: letterData.entity_type || 'CRA',
    entity_name: letterData.entity_name || letterData.bureau,
    dispute_date: letterData.dispute_date || new Date().toISOString().split('T')[0],
    source: letterData.source || 'DIRECT',
    violation_ids: letterData.violation_ids || [],
    violation_data: letterData.violation_data || null,
  };
  const response = await apiClient.post('/disputes', disputeData);
  return response.data;
};

/**
 * Get all disputes for current user
 */
export const getDisputes = async (filters = {}) => {
  const params = new URLSearchParams();
  if (filters.status) params.append('status', filters.status);
  if (filters.state) params.append('state', filters.state);

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

export const RESPONSE_TYPES = {
  DELETED: { value: 'DELETED', label: 'Deleted', description: 'Entity removed the disputed item' },
  VERIFIED: { value: 'VERIFIED', label: 'Verified', description: 'Entity claims information is accurate' },
  UPDATED: { value: 'UPDATED', label: 'Updated', description: 'Entity modified the reported data' },
  INVESTIGATING: { value: 'INVESTIGATING', label: 'Investigating', description: 'Entity claims investigation is ongoing' },
  NO_RESPONSE: { value: 'NO_RESPONSE', label: 'No Response', description: 'Deadline passed with no communication' },
  REJECTED: { value: 'REJECTED', label: 'Rejected / Frivolous', description: 'Entity refuses to investigate' },
};

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
