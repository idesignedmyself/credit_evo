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
  currentLetterId: null,
  editableLetter: null,
  isGeneratingLetter: false,
  isSavingLetter: false,
  lastSaved: null,
  hasUnsavedChanges: false,
  notification: null,
  error: null,

  // Actions
  setTone: (tone) => {
    const state = get();
    // Clear existing letter when tone changes so user must regenerate
    if (state.currentLetter) {
      set({
        selectedTone: tone,
        currentLetter: null,
        currentLetterId: null,
        editableLetter: null,
        hasUnsavedChanges: false,
        lastSaved: null,
      });
    } else {
      set({ selectedTone: tone });
    }
  },

  setGroupingStrategy: (strategy) => {
    const state = get();
    // Clear existing letter when grouping changes so user must regenerate
    if (state.currentLetter) {
      set({
        groupingStrategy: strategy,
        currentLetter: null,
        currentLetterId: null,
        editableLetter: null,
        hasUnsavedChanges: false,
        lastSaved: null,
      });
    } else {
      set({ groupingStrategy: strategy });
    }
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

  loadSavedLetter: async (letterId) => {
    set({ isGeneratingLetter: true, error: null });
    try {
      const letter = await letterApi.getLetter(letterId);
      set({
        currentLetter: letter,
        currentLetterId: letter.letter_id || letterId,
        editableLetter: letter.edited_content || letter.content,
        selectedTone: letter.tone || 'formal',
        groupingStrategy: letter.grouping_strategy || 'by_violation_type',
        isGeneratingLetter: false,
        hasUnsavedChanges: false,
        lastSaved: letter.updated_at ? new Date(letter.updated_at) : null,
      });
      return letter;
    } catch (error) {
      set({ error: error.message, isGeneratingLetter: false });
      throw error;
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
      set({
        currentLetter: letter,
        currentLetterId: letter.letter_id,
        editableLetter: letter.content,
        isGeneratingLetter: false,
        hasUnsavedChanges: false,
        lastSaved: null,
      });
      return letter;
    } catch (error) {
      set({ error: error.message, isGeneratingLetter: false });
      throw error;
    }
  },

  saveLetter: async () => {
    const state = get();
    if (!state.currentLetterId || !state.editableLetter) {
      return;
    }

    set({ isSavingLetter: true, error: null });
    try {
      const result = await letterApi.saveLetter(state.currentLetterId, state.editableLetter);
      set({
        isSavingLetter: false,
        hasUnsavedChanges: false,
        lastSaved: new Date(),
      });
      return result;
    } catch (error) {
      set({ error: error.message, isSavingLetter: false });
      throw error;
    }
  },

  clearLetter: () => {
    set({
      currentLetter: null,
      currentLetterId: null,
      editableLetter: null,
      error: null,
      hasUnsavedChanges: false,
      lastSaved: null,
    });
  },

  updateEditableLetter: (content) => {
    const state = get();
    const hasChanges = content !== state.currentLetter?.content;
    set({ editableLetter: content, hasUnsavedChanges: hasChanges });
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

  resetState: () => {
    set({
      selectedTone: 'formal',
      groupingStrategy: 'by_violation_type',
      availableTones: ['formal', 'assertive', 'conversational', 'narrative'],
      currentLetter: null,
      currentLetterId: null,
      editableLetter: null,
      isGeneratingLetter: false,
      isSavingLetter: false,
      lastSaved: null,
      hasUnsavedChanges: false,
      notification: null,
      error: null,
    });
  },
}));

export default useUIStore;
