/**
 * Credit Engine 2.0 - Letter API
 * Handles letter generation and retrieval
 */
import apiClient from './apiClient';

export const letterApi = {
  /**
   * Get all letters for the current user
   * @param {Object} filters - Optional filters
   * @param {string} filters.channel - Filter by channel: CRA, CFPB, LAWYER
   * @param {number} filters.tier - Filter by tier: 0=initial, 1=tier-1, 2=tier-2
   * @returns {Promise<Array>} List of letter summaries
   */
  getAllLetters: async (filters = {}) => {
    const params = new URLSearchParams();
    if (filters.channel) params.append('channel', filters.channel);
    if (filters.tier !== undefined) params.append('tier', filters.tier);
    const queryString = params.toString();
    const url = queryString ? `/letters/all?${queryString}` : '/letters/all';
    const response = await apiClient.get(url);
    return response.data;
  },

  /**
   * Get letter counts by channel and tier
   * @returns {Promise<Object>} Counts: {CRA: {total, tier_0, tier_1, tier_2}, CFPB: {...}, LAWYER: {...}}
   */
  getLetterCounts: async () => {
    const response = await apiClient.get('/letters/counts');
    return response.data;
  },

  /**
   * Generate a dispute letter
   * @param {Object} params - Letter generation parameters
   * @param {string} params.report_id - The report UUID
   * @param {Array<string>} params.selected_violations - Optional violation IDs to include
   * @param {Array<string>} params.selected_discrepancies - Optional discrepancy IDs to include (cross-bureau)
   * @param {string} params.tone - Letter tone (formal|assertive|conversational|narrative for civilian, professional|strict_legal|soft_legal|aggressive for legal)
   * @param {string} params.grouping_strategy - Grouping strategy
   * @param {string} params.bureau - Target bureau (transunion|experian|equifax)
   * @param {boolean} params.use_legal - Use Legal/Metro-2 structured letter generator
   * @param {boolean} params.use_copilot - Use Credit Copilot human-language generator
   * @param {string} params.channel - Document channel: MAILED, CFPB, or LITIGATION
   * @returns {Promise<DisputeLetter>}
   */
  generate: async ({
    report_id,
    selected_violations,
    selected_discrepancies,
    tone = 'formal',
    grouping_strategy = 'by_violation_type',
    bureau = 'transunion',
    use_legal = false,
    use_copilot = true,
    channel = 'MAILED',
  }) => {
    const payload = {
      report_id,
      tone,
      grouping_strategy,
      bureau,
      use_legal,
      use_copilot,
      channel,
    };

    if (selected_violations && selected_violations.length > 0) {
      payload.selected_violations = selected_violations;
    }

    if (selected_discrepancies && selected_discrepancies.length > 0) {
      payload.selected_discrepancies = selected_discrepancies;
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
   * Get available bureaus
   * @returns {Promise<{bureaus: Array<{id: string, name: string, address: string}>}>}
   */
  getBureaus: async () => {
    const response = await apiClient.get('/letters/bureaus');
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

  /**
   * Generate legal packet for attorney consultation
   * @param {string} letterId - The letter UUID
   * @param {string} format - Output format: 'document' (printable) or 'json' (structured data)
   * @returns {Promise<string|Object>} - Document text or JSON packet data
   */
  getLegalPacket: async (letterId, format = 'json') => {
    const response = await apiClient.get(`/letters/${letterId}/legal-packet?format=${format}`);
    return response.data;
  },
};

export default letterApi;
