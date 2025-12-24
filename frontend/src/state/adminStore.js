/**
 * Credit Engine 2.0 - Admin Store
 * Manages Admin Console state using Zustand
 * Read-only intelligence console - data sourced from Execution Ledger
 */
import { create } from 'zustand';
import * as adminApi from '../api/adminApi';

const useAdminStore = create((set, get) => ({
  // ==========================================================================
  // STATE
  // ==========================================================================

  // Dashboard
  dashboardStats: null,
  isLoadingDashboard: false,

  // Users
  users: [],
  usersTotal: 0,
  usersPage: 1,
  usersPageSize: 20,
  usersSearch: '',
  isLoadingUsers: false,

  // User Detail
  userDetail: null,
  isLoadingUserDetail: false,

  // Dispute Intelligence
  disputeIntel: null,
  disputeIntelDays: 90,
  isLoadingDisputeIntel: false,

  // Copilot Performance
  copilotPerf: null,
  copilotPerfDays: 90,
  isLoadingCopilotPerf: false,

  // Error state
  error: null,

  // ==========================================================================
  // ACTIONS - DASHBOARD
  // ==========================================================================

  fetchDashboardStats: async () => {
    set({ isLoadingDashboard: true, error: null });
    try {
      const stats = await adminApi.getDashboardStats();
      set({ dashboardStats: stats, isLoadingDashboard: false });
      return stats;
    } catch (error) {
      set({ error: error.message, isLoadingDashboard: false });
      throw error;
    }
  },

  // ==========================================================================
  // ACTIONS - USERS
  // ==========================================================================

  fetchUsers: async (options = {}) => {
    const state = get();
    const page = options.page ?? state.usersPage;
    const pageSize = options.pageSize ?? state.usersPageSize;
    const search = options.search ?? state.usersSearch;

    set({ isLoadingUsers: true, error: null });
    try {
      const response = await adminApi.getUsers({ page, pageSize, search });
      set({
        users: response.users,
        usersTotal: response.total,
        usersPage: response.page,
        usersPageSize: response.page_size,
        usersSearch: search,
        isLoadingUsers: false
      });
      return response;
    } catch (error) {
      set({ error: error.message, isLoadingUsers: false });
      throw error;
    }
  },

  setUsersPage: (page) => {
    set({ usersPage: page });
    get().fetchUsers({ page });
  },

  setUsersSearch: (search) => {
    set({ usersSearch: search, usersPage: 1 });
    get().fetchUsers({ search, page: 1 });
  },

  fetchUserDetail: async (userId) => {
    set({ isLoadingUserDetail: true, error: null, userDetail: null });
    try {
      const detail = await adminApi.getUserDetail(userId);
      set({ userDetail: detail, isLoadingUserDetail: false });
      return detail;
    } catch (error) {
      set({ error: error.message, isLoadingUserDetail: false });
      throw error;
    }
  },

  clearUserDetail: () => {
    set({ userDetail: null });
  },

  // ==========================================================================
  // ACTIONS - DISPUTE INTELLIGENCE
  // ==========================================================================

  fetchDisputeIntel: async (days = null) => {
    const daysToFetch = days ?? get().disputeIntelDays;
    set({ isLoadingDisputeIntel: true, error: null });
    try {
      const intel = await adminApi.getDisputeIntelligence(daysToFetch);
      set({ disputeIntel: intel, disputeIntelDays: daysToFetch, isLoadingDisputeIntel: false });
      return intel;
    } catch (error) {
      set({ error: error.message, isLoadingDisputeIntel: false });
      throw error;
    }
  },

  setDisputeIntelDays: (days) => {
    set({ disputeIntelDays: days });
    get().fetchDisputeIntel(days);
  },

  // ==========================================================================
  // ACTIONS - COPILOT PERFORMANCE
  // ==========================================================================

  fetchCopilotPerf: async (days = null) => {
    const daysToFetch = days ?? get().copilotPerfDays;
    set({ isLoadingCopilotPerf: true, error: null });
    try {
      const perf = await adminApi.getCopilotPerformance(daysToFetch);
      set({ copilotPerf: perf, copilotPerfDays: daysToFetch, isLoadingCopilotPerf: false });
      return perf;
    } catch (error) {
      set({ error: error.message, isLoadingCopilotPerf: false });
      throw error;
    }
  },

  setCopilotPerfDays: (days) => {
    set({ copilotPerfDays: days });
    get().fetchCopilotPerf(days);
  },

  // ==========================================================================
  // ERROR HANDLING
  // ==========================================================================

  clearError: () => {
    set({ error: null });
  },

  resetState: () => {
    set({
      dashboardStats: null,
      isLoadingDashboard: false,
      users: [],
      usersTotal: 0,
      usersPage: 1,
      usersPageSize: 20,
      usersSearch: '',
      isLoadingUsers: false,
      userDetail: null,
      isLoadingUserDetail: false,
      disputeIntel: null,
      disputeIntelDays: 90,
      isLoadingDisputeIntel: false,
      copilotPerf: null,
      copilotPerfDays: 90,
      isLoadingCopilotPerf: false,
      error: null,
    });
  },
}));

export default useAdminStore;
