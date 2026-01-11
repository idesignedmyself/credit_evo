/**
 * CFPB Channel API
 * Frontend functions for CFPB complaint lifecycle
 */
import axios from 'axios';

const API_BASE = import.meta.env.VITE_API_URL || 'http://localhost:8000/api';

// Get auth header
const getAuthHeader = () => {
  const token = localStorage.getItem('token');
  return token ? { Authorization: `Bearer ${token}` } : {};
};

/**
 * Generate CFPB complaint letter
 * @param {string} disputeSessionId - Links to existing dispute
 * @param {string} stage - 'initial' | 'escalation' | 'final'
 */
export const generateCFPBLetter = async (disputeSessionId, stage = 'initial') => {
  const response = await axios.post(
    `${API_BASE}/cfpb/letters/generate`,
    {
      dispute_session_id: disputeSessionId,
      cfpb_stage: stage,
    },
    { headers: getAuthHeader() }
  );
  return response.data;
};

/**
 * Submit CFPB complaint (advances state)
 * @param {string} disputeSessionId - Links to existing dispute
 * @param {string} stage - 'initial' | 'escalation' | 'final'
 * @param {object} payload - { complaint_text, attachments }
 * @param {string} cfpbCaseNumber - Optional CFPB portal case number
 */
export const submitCFPBComplaint = async (disputeSessionId, stage, payload, cfpbCaseNumber = null) => {
  const response = await axios.post(
    `${API_BASE}/cfpb/complaints/submit`,
    {
      dispute_session_id: disputeSessionId,
      cfpb_stage: stage,
      submission_payload: payload,
      cfpb_case_number: cfpbCaseNumber,
    },
    { headers: getAuthHeader() }
  );
  return response.data;
};

/**
 * Log CFPB response from company/CRA
 * @param {string} cfpbCaseId - CFPB case ID
 * @param {string} responseText - Response text from entity
 * @param {string} respondingEntity - 'CRA' | 'Furnisher'
 * @param {string} responseDate - ISO8601 date (YYYY-MM-DD)
 */
export const logCFPBResponse = async (cfpbCaseId, responseText, respondingEntity, responseDate) => {
  const response = await axios.post(
    `${API_BASE}/cfpb/complaints/response`,
    {
      cfpb_case_id: cfpbCaseId,
      response_text: responseText,
      responding_entity: respondingEntity,
      response_date: responseDate,
    },
    { headers: getAuthHeader() }
  );
  return response.data;
};

/**
 * Evaluate CFPB response (read-only)
 * @param {string} cfpbCaseId - CFPB case ID
 */
export const evaluateCFPBResponse = async (cfpbCaseId) => {
  const response = await axios.post(
    `${API_BASE}/cfpb/evaluate`,
    { cfpb_case_id: cfpbCaseId },
    { headers: getAuthHeader() }
  );
  return response.data;
};

/**
 * Get CFPB case details
 * @param {string} cfpbCaseId - CFPB case ID
 */
export const getCFPBCase = async (cfpbCaseId) => {
  const response = await axios.get(
    `${API_BASE}/cfpb/cases/${cfpbCaseId}`,
    { headers: getAuthHeader() }
  );
  return response.data;
};

/**
 * Get CFPB case event history
 * @param {string} cfpbCaseId - CFPB case ID
 */
export const getCFPBEvents = async (cfpbCaseId) => {
  const response = await axios.get(
    `${API_BASE}/cfpb/cases/${cfpbCaseId}/events`,
    { headers: getAuthHeader() }
  );
  return response.data;
};

/**
 * List all CFPB cases for current user
 */
export const listCFPBCases = async () => {
  const response = await axios.get(
    `${API_BASE}/cfpb/cases`,
    { headers: getAuthHeader() }
  );
  return response.data;
};

/**
 * CFPB Response types for UI dropdowns
 */
export const CFPB_RESPONSE_TYPES = {
  RELIEF_PROVIDED: {
    value: 'RELIEF_PROVIDED',
    label: 'Company Provided Relief',
    description: 'Company corrected the issue or provided monetary relief',
    resolved: true,
  },
  EXPLANATION_ONLY: {
    value: 'EXPLANATION_ONLY',
    label: 'Explanation Only (No Relief)',
    description: 'Company responded but did not provide relief',
    resolved: false,
  },
  NO_RESPONSE: {
    value: 'NO_RESPONSE',
    label: 'No Response',
    description: 'Company did not respond within deadline',
    resolved: false,
  },
  CFPB_CLOSED: {
    value: 'CFPB_CLOSED',
    label: 'CFPB Closed Case',
    description: 'CFPB closed the case with explanation',
    resolved: true,
  },
};

export default {
  generateCFPBLetter,
  submitCFPBComplaint,
  logCFPBResponse,
  evaluateCFPBResponse,
  getCFPBCase,
  getCFPBEvents,
  listCFPBCases,
  CFPB_RESPONSE_TYPES,
};
