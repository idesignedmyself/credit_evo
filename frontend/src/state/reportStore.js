/**
 * Credit Engine 2.0 - Report Store
 * Manages report state using Zustand
 */
import { create } from 'zustand';
import { reportApi } from '../api';

const useReportStore = create((set, get) => ({
  // State
  currentReport: null,
  currentReportId: null,  // Track which report is loaded for caching
  reports: [],
  latestReportId: null,
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
        latestReportId: result.report_id,
        isUploading: false,
        uploadProgress: 100,
      }));
      return result;
    } catch (error) {
      set({ error: error.message, isUploading: false });
      throw error;
    }
  },

  fetchLatestReportId: async () => {
    try {
      const reports = await reportApi.listReports();
      if (reports && reports.length > 0) {
        set({ latestReportId: reports[0].report_id });
        return reports[0].report_id;
      }
      set({ latestReportId: null });
      return null;
    } catch (error) {
      set({ latestReportId: null });
      return null;
    }
  },

  setCurrentReport: (report) => {
    set({ currentReport: report });
  },

  fetchReport: async (reportId) => {
    // Skip if we already have this report cached
    const state = get();
    if (state.currentReportId === reportId && state.currentReport) {
      return state.currentReport;
    }

    set({ error: null });
    try {
      const report = await reportApi.getReport(reportId);
      set({ currentReport: report, currentReportId: reportId });
      return report;
    } catch (error) {
      set({ error: error.message });
      throw error;
    }
  },

  clearReport: () => {
    set({ currentReport: null, currentReportId: null, error: null });
  },

  clearError: () => {
    set({ error: null });
  },

  resetState: () => {
    set({
      currentReport: null,
      currentReportId: null,
      reports: [],
      latestReportId: null,
      uploadProgress: 0,
      isUploading: false,
      error: null,
    });
  },
}));

export default useReportStore;
