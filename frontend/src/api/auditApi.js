/**
 * Credit Engine 2.0 - Audit API
 * Handles audit results retrieval
 */
import apiClient from './apiClient';

export const auditApi = {
  /**
   * Get audit results for a report
   * @param {string} reportId - The report UUID
   * @returns {Promise<AuditResult>}
   */
  getAuditResults: async (reportId) => {
    const response = await apiClient.get(`/reports/${reportId}/audit`);
    return response.data;
  },

  /**
   * Get violation details
   * @param {string} reportId - The report UUID
   * @param {string} violationId - The violation UUID
   * @returns {Promise<Violation>}
   */
  getViolation: async (reportId, violationId) => {
    const response = await apiClient.get(`/reports/${reportId}/violations/${violationId}`);
    return response.data;
  },
};

export default auditApi;
