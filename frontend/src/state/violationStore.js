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
  discrepancies: [],  // Cross-bureau discrepancies
  selectedViolationIds: [],
  selectedDiscrepancyIds: [],  // Selected cross-bureau discrepancies
  isLoading: false,
  error: null,
  currentReportId: null,  // Track which report the violations belong to

  // Actions
  fetchAuditResults: async (reportId) => {
    // Skip if we already have data for this report
    const state = get();
    if (state.currentReportId === reportId && state.violations.length > 0) {
      return state.auditResult;
    }

    set({ isLoading: true, error: null });
    try {
      const result = await auditApi.getAuditResults(reportId);
      set({
        auditResult: result,
        violations: result.violations || [],
        discrepancies: result.discrepancies || [],  // Store discrepancies
        selectedViolationIds: [],
        selectedDiscrepancyIds: [],
        isLoading: false,
        currentReportId: reportId,  // Track which report this data belongs to
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

  // Set specific violations as selected (replaces current selection)
  setSelectedViolations: (violationIds) => {
    set({ selectedViolationIds: violationIds || [] });
  },

  // Set specific discrepancies as selected (replaces current selection)
  setSelectedDiscrepancies: (discrepancyIds) => {
    set({ selectedDiscrepancyIds: discrepancyIds || [] });
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

  // Discrepancy selection actions
  toggleDiscrepancy: (discrepancyId) => {
    set((state) => {
      const isSelected = state.selectedDiscrepancyIds.includes(discrepancyId);
      return {
        selectedDiscrepancyIds: isSelected
          ? state.selectedDiscrepancyIds.filter(id => id !== discrepancyId)
          : [...state.selectedDiscrepancyIds, discrepancyId],
      };
    });
  },

  selectAllDiscrepancies: () => {
    set((state) => ({
      selectedDiscrepancyIds: state.discrepancies.map(d => d.discrepancy_id),
    }));
  },

  deselectAllDiscrepancies: () => {
    set({ selectedDiscrepancyIds: [] });
  },

  isDiscrepancySelected: (discrepancyId) => {
    return get().selectedDiscrepancyIds.includes(discrepancyId);
  },

  getSelectedDiscrepancies: () => {
    const state = get();
    return state.discrepancies.filter(d =>
      state.selectedDiscrepancyIds.includes(d.discrepancy_id)
    );
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
      discrepancies: [],
      selectedViolationIds: [],
      selectedDiscrepancyIds: [],
      error: null,
      currentReportId: null,
    });
  },

  clearError: () => {
    set({ error: null });
  },

  resetState: () => {
    set({
      auditResult: null,
      violations: [],
      discrepancies: [],
      selectedViolationIds: [],
      selectedDiscrepancyIds: [],
      isLoading: false,
      error: null,
    });
  },
}));

export default useViolationStore;
