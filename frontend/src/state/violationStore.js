/**
 * Credit Engine 2.0 - Violation Store
 * Manages violations and selection state using Zustand
 */
import { create } from 'zustand';
import { auditApi } from '../api';

const useViolationStore = create((set, get) => ({
  // State
  auditResult: null,
  violations: [],
  selectedViolationIds: [],
  isLoading: false,
  error: null,

  // Actions
  fetchAuditResults: async (reportId) => {
    set({ isLoading: true, error: null });
    try {
      const result = await auditApi.getAuditResults(reportId);
      set({
        auditResult: result,
        violations: result.violations || [],
        selectedViolationIds: (result.violations || []).map(v => v.violation_id),
        isLoading: false,
      });
      return result;
    } catch (error) {
      set({ error: error.message, isLoading: false });
      throw error;
    }
  },

  toggleViolation: (violationId) => {
    set((state) => {
      const isSelected = state.selectedViolationIds.includes(violationId);
      return {
        selectedViolationIds: isSelected
          ? state.selectedViolationIds.filter(id => id !== violationId)
          : [...state.selectedViolationIds, violationId],
      };
    });
  },

  selectAll: () => {
    set((state) => ({
      selectedViolationIds: state.violations.map(v => v.violation_id),
    }));
  },

  deselectAll: () => {
    set({ selectedViolationIds: [] });
  },

  selectByBureau: (bureau) => {
    set((state) => {
      const bureauViolationIds = state.violations
        .filter(v => v.bureau?.toLowerCase() === bureau.toLowerCase())
        .map(v => v.violation_id);
      // Add bureau violations to existing selection (merge, don't replace)
      const newSelection = [...new Set([...state.selectedViolationIds, ...bureauViolationIds])];
      return { selectedViolationIds: newSelection };
    });
  },

  deselectByBureau: (bureau) => {
    set((state) => {
      const bureauViolationIds = state.violations
        .filter(v => v.bureau?.toLowerCase() === bureau.toLowerCase())
        .map(v => v.violation_id);
      return {
        selectedViolationIds: state.selectedViolationIds.filter(
          id => !bureauViolationIds.includes(id)
        ),
      };
    });
  },

  isViolationSelected: (violationId) => {
    return get().selectedViolationIds.includes(violationId);
  },

  getSelectedViolations: () => {
    const state = get();
    return state.violations.filter(v =>
      state.selectedViolationIds.includes(v.violation_id)
    );
  },

  getViolationsByAccount: () => {
    const violations = get().violations;
    const grouped = {};
    violations.forEach(v => {
      const key = v.account_id || 'unknown';
      if (!grouped[key]) {
        grouped[key] = [];
      }
      grouped[key].push(v);
    });
    return grouped;
  },

  getViolationsByType: () => {
    const violations = get().violations;
    const grouped = {};
    violations.forEach(v => {
      const key = v.violation_type || 'unknown';
      if (!grouped[key]) {
        grouped[key] = [];
      }
      grouped[key].push(v);
    });
    return grouped;
  },

  clearViolations: () => {
    set({
      auditResult: null,
      violations: [],
      selectedViolationIds: [],
      error: null,
    });
  },

  clearError: () => {
    set({ error: null });
  },

  resetState: () => {
    set({
      auditResult: null,
      violations: [],
      selectedViolationIds: [],
      isLoading: false,
      error: null,
    });
  },
}));

export default useViolationStore;
