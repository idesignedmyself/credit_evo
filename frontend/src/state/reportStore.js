/**
 * Credit Engine 2.0 - Report Store
 * Manages report state using Zustand
 */
import { create } from 'zustand';
import { reportApi } from '../api';

const useReportStore = create((set, get) => ({
  // State
  currentReport: null,
  reports: [],
  uploadProgress: 0,
  isUploading: false,
  error: null,

  // Actions
  uploadReport: async (file) => {
    set({ isUploading: true, error: null, uploadProgress: 0 });
    try {
      const result = await reportApi.upload(file);
      set((state) => ({
        currentReport: result,
        reports: [...state.reports, result],
        isUploading: false,
        uploadProgress: 100,
      }));
      return result;
    } catch (error) {
      set({ error: error.message, isUploading: false });
      throw error;
    }
  },

  setCurrentReport: (report) => {
    set({ currentReport: report });
  },

  fetchReport: async (reportId) => {
    set({ error: null });
    try {
      const report = await reportApi.getReport(reportId);
      set({ currentReport: report });
      return report;
    } catch (error) {
      set({ error: error.message });
      throw error;
    }
  },

  clearReport: () => {
    set({ currentReport: null, error: null });
  },

  clearError: () => {
    set({ error: null });
  },

  resetState: () => {
    set({
      currentReport: null,
      reports: [],
      uploadProgress: 0,
      isUploading: false,
      error: null,
    });
  },
}));

export default useReportStore;
