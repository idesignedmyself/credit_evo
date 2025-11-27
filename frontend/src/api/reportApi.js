/**
 * Credit Engine 2.0 - Report API
 * Handles credit report upload and retrieval
 */
import apiClient from './apiClient';

export const reportApi = {
  /**
   * Upload a credit report file (HTML/PDF)
   * @param {File} file - The credit report file
   * @returns {Promise<{report_id, bureau, accounts_found, violations_found}>}
   */
  upload: async (file) => {
    const formData = new FormData();
    formData.append('file', file);

    const response = await apiClient.post('/reports/upload', formData, {
      headers: {
        'Content-Type': 'multipart/form-data',
      },
    });
    return response.data;
  },

  /**
   * Get a parsed report by ID
   * @param {string} reportId - The report UUID
   * @returns {Promise<NormalizedReport>}
   */
  getReport: async (reportId) => {
    const response = await apiClient.get(`/reports/${reportId}`);
    return response.data;
  },

  /**
   * List all uploaded reports
   * @returns {Promise<Array>}
   */
  listReports: async () => {
    const response = await apiClient.get('/reports');
    return response.data;
  },
};

export default reportApi;
