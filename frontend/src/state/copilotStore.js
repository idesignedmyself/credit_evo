/**
 * Credit Engine 2.0 - Copilot Store
 * Manages Copilot state and recommendations using Zustand
 *
 * Architecture:
 * - Recommendations are NOT persisted across sessions
 * - Override tracking resets on goal/report change
 * - Passive/ghost mode when no blockers detected
 * - Goal syncs from user profile
 */
import { create } from 'zustand';
import * as copilotApi from '../api/copilotApi';
import useAuthStore from './authStore';

const useCopilotStore = create((set, get) => ({
  // ==========================================================================
  // STATE
  // ==========================================================================

  // Core data (not persisted across sessions)
  recommendation: null,           // CopilotRecommendation with full data
  goals: [],                      // Available credit goals
  selectedGoal: 'credit_hygiene', // Current selected goal

  // Version tracking (for overrides)
  correlationId: null,            // dispute_session_id
  versionHash: null,              // copilot_version_id

  // UI state
  drawerOpen: false,
  activeSection: 'overview',      // 'blockers' | 'actions' | 'skips'
  isPassiveMode: false,           // Ghost state when no blockers

  // Override tracking (batch logic)
  sessionOverrideCount: 0,        // Reset on goal change

  // Loading
  currentReportId: null,
  isLoadingRecommendation: false,
  isLoadingGoals: false,
  error: null,

  // ==========================================================================
  // ACTIONS - GOALS
  // ==========================================================================

  /**
   * Fetch available credit goals
   */
  fetchGoals: async () => {
    const state = get();
    if (state.goals.length > 0) return state.goals;

    set({ isLoadingGoals: true, error: null });
    try {
      const response = await copilotApi.getGoals();
      set({ goals: response.goals, isLoadingGoals: false });
      return response.goals;
    } catch (error) {
      set({ error: error.message, isLoadingGoals: false });
      throw error;
    }
  },

  /**
   * Set the selected goal (resets override count)
   */
  setSelectedGoal: (goal) => {
    set({
      selectedGoal: goal,
      sessionOverrideCount: 0, // Reset on goal change
      recommendation: null,    // Clear stale recommendation
    });
  },

  /**
   * Sync goal from user's profile (authStore)
   * Called when opening drawer or fetching recommendation
   */
  syncGoalFromProfile: () => {
    const authState = useAuthStore.getState();
    const userGoal = authState.user?.credit_goal;
    if (userGoal && userGoal !== get().selectedGoal) {
      set({
        selectedGoal: userGoal,
        sessionOverrideCount: 0,
        recommendation: null, // Clear stale recommendation for different goal
      });
      return userGoal;
    }
    return get().selectedGoal;
  },

  // ==========================================================================
  // ACTIONS - RECOMMENDATIONS
  // ==========================================================================

  /**
   * Fetch recommendation for a report
   * @param {string} reportId - Report to analyze
   * @param {string} [goalOverride] - Optional goal override
   */
  fetchRecommendation: async (reportId, goalOverride = null) => {
    // Sync goal from user profile first (unless override provided)
    if (!goalOverride) {
      get().syncGoalFromProfile();
    }
    const state = get();
    const goal = goalOverride || state.selectedGoal;

    // Skip if already loaded for this report+goal combo
    if (
      state.currentReportId === reportId &&
      state.recommendation?.goal === goal &&
      state.recommendation
    ) {
      return state.recommendation;
    }

    set({
      isLoadingRecommendation: true,
      error: null,
      currentReportId: reportId,
    });

    try {
      const recommendation = await copilotApi.getRecommendation(reportId, goal);

      // Determine passive mode
      const hasBlockers = recommendation.blockers?.length > 0;
      const isPassive = !hasBlockers;

      set({
        recommendation,
        correlationId: recommendation.recommendation_id,
        versionHash: recommendation.recommendation_id, // Use as version hash
        isLoadingRecommendation: false,
        isPassiveMode: isPassive,
        sessionOverrideCount: 0, // Reset on new recommendation
      });

      return recommendation;
    } catch (error) {
      set({
        error: error.message,
        isLoadingRecommendation: false,
        isPassiveMode: true, // Fail gracefully to passive mode
      });
      throw error;
    }
  },

  /**
   * Clear recommendation (on report change or logout)
   */
  clearRecommendation: () => {
    set({
      recommendation: null,
      correlationId: null,
      versionHash: null,
      currentReportId: null,
      isPassiveMode: false,
      sessionOverrideCount: 0,
    });
  },

  // ==========================================================================
  // ACTIONS - UI
  // ==========================================================================

  /**
   * Toggle drawer open/closed (syncs goal from profile when opening)
   */
  toggleDrawer: () => {
    const state = get();
    if (!state.drawerOpen) {
      // Opening - sync goal from profile
      get().syncGoalFromProfile();
    }
    set({ drawerOpen: !state.drawerOpen });
  },

  /**
   * Open drawer (syncs goal from profile first)
   */
  openDrawer: () => {
    get().syncGoalFromProfile();
    set({ drawerOpen: true });
  },

  /**
   * Close drawer
   */
  closeDrawer: () => {
    set({ drawerOpen: false });
  },

  /**
   * Set active section in drawer
   */
  setActiveSection: (section) => {
    set({ activeSection: section });
  },

  // ==========================================================================
  // ACTIONS - VIOLATION STATUS
  // ==========================================================================

  /**
   * Get Copilot status for a violation
   * @param {string} violationId - Violation ID to check
   * @returns {'recommended' | 'deferred' | 'advised_against' | null}
   */
  getViolationStatus: (violationId) => {
    const state = get();
    if (!state.recommendation) return null;

    // Check if violation is in actions (recommended)
    const inActions = state.recommendation.actions?.some(
      (a) => a.blocker_source_id === violationId
    );
    if (inActions) return 'recommended';

    // Check if violation is in skips (advised_against)
    const inSkips = state.recommendation.skips?.some(
      (s) => s.source_id === violationId
    );
    if (inSkips) return 'advised_against';

    // Check if violation has a blocker but no action yet (deferred)
    const hasBlocker = state.recommendation.blockers?.some(
      (b) => b.source_id === violationId
    );
    if (hasBlocker) return 'deferred';

    return null;
  },

  /**
   * Get human rationale for a violation
   * @param {string} violationId - Violation ID
   * @returns {string | null}
   */
  getHumanRationale: (violationId) => {
    const state = get();
    if (!state.recommendation) return null;

    // Check actions first
    const action = state.recommendation.actions?.find(
      (a) => a.blocker_source_id === violationId
    );
    if (action) return action.rationale;

    // Check skips
    const skip = state.recommendation.skips?.find(
      (s) => s.source_id === violationId
    );
    if (skip) return skip.rationale;

    // Check blockers
    const blocker = state.recommendation.blockers?.find(
      (b) => b.source_id === violationId
    );
    if (blocker) return blocker.description;

    return null;
  },

  /**
   * Get blocker for a violation
   * @param {string} violationId - Violation ID
   * @returns {Object | null}
   */
  getBlocker: (violationId) => {
    const state = get();
    return state.recommendation?.blockers?.find(
      (b) => b.source_id === violationId
    ) || null;
  },

  /**
   * Get action for a violation
   * @param {string} violationId - Violation ID
   * @returns {Object | null}
   */
  getAction: (violationId) => {
    const state = get();
    return state.recommendation?.actions?.find(
      (a) => a.blocker_source_id === violationId
    ) || null;
  },

  /**
   * Get skip for a violation
   * @param {string} violationId - Violation ID
   * @returns {Object | null}
   */
  getSkip: (violationId) => {
    const state = get();
    return state.recommendation?.skips?.find(
      (s) => s.source_id === violationId
    ) || null;
  },

  // ==========================================================================
  // ACTIONS - OVERRIDE LOGGING
  // ==========================================================================

  /**
   * Log an override event to the ledger
   * @param {string} violationId - Violation being overridden
   * @returns {Promise<void>}
   */
  logOverride: async (violationId) => {
    const state = get();

    if (!state.recommendation || !state.versionHash) {
      console.warn('Cannot log override: no active recommendation');
      return;
    }

    const copilotAdvice = state.getViolationStatus(violationId);
    if (!copilotAdvice || copilotAdvice === 'recommended') {
      // Not an override if it's recommended
      return;
    }

    try {
      await copilotApi.logOverride({
        dispute_session_id: state.correlationId,
        copilot_version_id: state.versionHash,
        report_id: state.currentReportId,
        violation_id: violationId,
        copilot_advice: copilotAdvice,
        user_action: 'proceed',
      });

      // Increment counter
      set((state) => ({
        sessionOverrideCount: state.sessionOverrideCount + 1,
      }));
    } catch (error) {
      console.error('Failed to log override:', error);
      // Don't throw - override logging failure shouldn't block user
    }
  },

  /**
   * Check if override dialog should be shown (first override in session)
   * @returns {boolean}
   */
  shouldShowOverrideDialog: () => {
    return get().sessionOverrideCount === 0;
  },

  /**
   * Increment override count (after dialog confirmation)
   */
  incrementOverrideCount: () => {
    set((state) => ({
      sessionOverrideCount: state.sessionOverrideCount + 1,
    }));
  },

  // ==========================================================================
  // COMPUTED / GETTERS
  // ==========================================================================

  /**
   * Get recommended violations (for quick filtering)
   */
  getRecommendedViolationIds: () => {
    const state = get();
    return state.recommendation?.actions?.map((a) => a.blocker_source_id) || [];
  },

  /**
   * Get deferred violations
   */
  getDeferredViolationIds: () => {
    const state = get();
    const actionIds = new Set(
      state.recommendation?.actions?.map((a) => a.blocker_source_id) || []
    );
    const skipIds = new Set(
      state.recommendation?.skips?.map((s) => s.source_id) || []
    );
    return (
      state.recommendation?.blockers
        ?.filter((b) => !actionIds.has(b.source_id) && !skipIds.has(b.source_id))
        ?.map((b) => b.source_id) || []
    );
  },

  /**
   * Get advised-against violations (skips)
   */
  getAdvisedAgainstViolationIds: () => {
    const state = get();
    return state.recommendation?.skips?.map((s) => s.source_id) || [];
  },

  // ==========================================================================
  // ERROR HANDLING
  // ==========================================================================

  /**
   * Clear error
   */
  clearError: () => {
    set({ error: null });
  },

  /**
   * Reset all state
   */
  resetState: () => {
    set({
      recommendation: null,
      goals: [],
      selectedGoal: 'credit_hygiene',
      correlationId: null,
      versionHash: null,
      drawerOpen: false,
      activeSection: 'overview',
      isPassiveMode: false,
      sessionOverrideCount: 0,
      currentReportId: null,
      isLoadingRecommendation: false,
      isLoadingGoals: false,
      error: null,
    });
  },
}));

export default useCopilotStore;
