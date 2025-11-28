/**
 * Credit Engine 2.0 - Letter API
 * Handles letter generation and retrieval
 */
import apiClient from './apiClient';

export const letterApi = {
  /**
   * Get all letters for the current user
   * @returns {Promise<Array>} List of letter summaries
   */
  getAllLetters: async () => {
    const response = await apiClient.get('/letters/all');
    return response.data;
  },

  /**
   * Generate a dispute letter
   * @param {Object} params - Letter generation parameters
   * @param {string} params.report_id - The report UUID
   * @param {Array<string>} params.selected_violations - Optional violation IDs to include
   * @param {string} params.tone - Letter tone (formal|assertive|conversational|narrative)
   * @param {string} params.grouping_strategy - Grouping strategy
   * @returns {Promise<DisputeLetter>}
   */
  generate: async ({ report_id, selected_violations, tone = 'formal', grouping_strategy = 'by_violation_type' }) => {
    const payload = {
      report_id,
      tone,
      grouping_strategy,
    };

    if (selected_violations && selected_violations.length > 0) {
      payload.selected_violations = selected_violations;
    }

    const response = await apiClient.post('/letters/generate', payload);
    return response.data;
  },

  /**
   * Get available letter tones
   * @returns {Promise<{tones: Array<string>}>}
   */
  getTones: async () => {
    const response = await apiClient.get('/letters/tones');
    return response.data;
  },

  /**
   * Get a previously generated letter
   * @param {string} letterId - The letter UUID
   * @returns {Promise<DisputeLetter>}
   */
  getLetter: async (letterId) => {
    const response = await apiClient.get(`/letters/${letterId}`);
    return response.data;
  },

  /**
   * Save edited letter content
   * @param {string} letterId - The letter UUID
   * @param {string} editedContent - The edited letter content
   * @returns {Promise<{status: string, letter_id: string, word_count: number}>}
   */
  saveLetter: async (letterId, editedContent) => {
    const response = await apiClient.put(`/letters/${letterId}`, {
      edited_content: editedContent,
    });
    return response.data;
  },

  /**
   * Delete a letter
   * @param {string} letterId - The letter UUID
   * @returns {Promise<{status: string}>}
   */
  deleteLetter: async (letterId) => {
    const response = await apiClient.delete(`/letters/${letterId}`);
    return response.data;
  },
};

export default letterApi;
