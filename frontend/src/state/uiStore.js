/**
 * Credit Engine 2.0 - UI Store
 * Manages UI state (loading, modals, notifications) using Zustand
 */
import { create } from 'zustand';
import { letterApi } from '../api';

const useUIStore = create((set, get) => ({
  // State
  letterType: 'civilian', // 'civilian' or 'legal'
  selectedTone: 'formal',
  groupingStrategy: 'by_violation_type',
  selectedBureau: 'transunion',
  availableTones: ['formal', 'assertive', 'conversational', 'narrative'],
  legalTones: ['professional', 'strict_legal', 'soft_legal', 'aggressive'],
  availableBureaus: [
    { id: 'transunion', name: 'TransUnion' },
    { id: 'experian', name: 'Experian' },
    { id: 'equifax', name: 'Equifax' },
  ],
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
  setLetterType: (type) => {
    const state = get();
    // Clear existing letter when letter type changes
    if (state.currentLetter) {
      set({
        letterType: type,
        // Reset tone to appropriate default when switching types
        selectedTone: type === 'legal' ? 'professional' : 'formal',
        currentLetter: null,
        currentLetterId: null,
        editableLetter: null,
        hasUnsavedChanges: false,
        lastSaved: null,
      });
    } else {
      set({
        letterType: type,
        // Reset tone to appropriate default when switching types
        selectedTone: type === 'legal' ? 'professional' : 'formal',
      });
    }
  },

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

  setBureau: (bureau) => {
    const state = get();
    // Clear existing letter when bureau changes so user must regenerate
    if (state.currentLetter) {
      set({
        selectedBureau: bureau,
        currentLetter: null,
        currentLetterId: null,
        editableLetter: null,
        hasUnsavedChanges: false,
        lastSaved: null,
      });
    } else {
      set({ selectedBureau: bureau });
    }
  },

  fetchBureaus: async () => {
    try {
      const result = await letterApi.getBureaus();
      set({ availableBureaus: result.bureaus });
      return result.bureaus;
    } catch (error) {
      console.error('Failed to fetch bureaus:', error);
      // Keep defaults on error
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
      const isLegal = state.letterType === 'legal';
      const letter = await letterApi.generate({
        report_id: reportId,
        selected_violations: selectedViolationIds,
        tone: state.selectedTone,
        grouping_strategy: state.groupingStrategy,
        bureau: state.selectedBureau,
        use_legal: isLegal,
        use_copilot: !isLegal,
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
      letterType: 'civilian',
      selectedTone: 'formal',
      groupingStrategy: 'by_violation_type',
      selectedBureau: 'transunion',
      availableTones: ['formal', 'assertive', 'conversational', 'narrative'],
      legalTones: ['professional', 'strict_legal', 'soft_legal', 'aggressive'],
      availableBureaus: [
        { id: 'transunion', name: 'TransUnion' },
        { id: 'experian', name: 'Experian' },
        { id: 'equifax', name: 'Equifax' },
      ],
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
