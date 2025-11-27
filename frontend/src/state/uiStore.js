/**
 * Credit Engine 2.0 - UI Store
 * Manages UI state (loading, modals, notifications) using Zustand
 */
import { create } from 'zustand';
import { letterApi } from '../api';

const useUIStore = create((set, get) => ({
  // State
  selectedTone: 'formal',
  groupingStrategy: 'by_violation_type',
  availableTones: ['formal', 'assertive', 'conversational', 'narrative'],
  currentLetter: null,
  isGeneratingLetter: false,
  notification: null,
  error: null,

  // Actions
  setTone: (tone) => {
    set({ selectedTone: tone });
  },

  setGroupingStrategy: (strategy) => {
    set({ groupingStrategy: strategy });
  },

  fetchTones: async () => {
    try {
      const result = await letterApi.getTones();
      // API returns [{id, name, description}], extract just the IDs
      const toneIds = result.tones.map(t => typeof t === 'string' ? t : t.id);
      set({ availableTones: toneIds });
      return toneIds;
    } catch (error) {
      console.error('Failed to fetch tones:', error);
      // Keep defaults on error
    }
  },

  generateLetter: async (reportId, selectedViolationIds) => {
    set({ isGeneratingLetter: true, error: null });
    try {
      const state = get();
      const letter = await letterApi.generate({
        report_id: reportId,
        selected_violations: selectedViolationIds,
        tone: state.selectedTone,
        grouping_strategy: state.groupingStrategy,
      });
      set({ currentLetter: letter, isGeneratingLetter: false });
      return letter;
    } catch (error) {
      set({ error: error.message, isGeneratingLetter: false });
      throw error;
    }
  },

  clearLetter: () => {
    set({ currentLetter: null, error: null });
  },

  showNotification: (message, type = 'info') => {
    set({ notification: { message, type } });
    // Auto-clear after 5 seconds
    setTimeout(() => {
      set({ notification: null });
    }, 5000);
  },

  clearNotification: () => {
    set({ notification: null });
  },

  clearError: () => {
    set({ error: null });
  },
}));

export default useUIStore;
