/**
 * OverrideController - Manages batch override state
 *
 * Orchestrates the override flow:
 * - First override: Show confirmation dialog
 * - Subsequent overrides: Show toast notification
 * - Logs all overrides to the execution ledger
 */
import React, { useState, useCallback } from 'react';

import { useCopilotStore } from '../../state';
import OverrideConfirmDialog from './OverrideConfirmDialog';
import OverrideToast from './OverrideToast';

/**
 * Override controller hook - use in components that handle violation selection
 * @returns {Object} Override controller utilities
 */
export function useOverrideController() {
  const [dialogOpen, setDialogOpen] = useState(false);
  const [toastOpen, setToastOpen] = useState(false);
  const [pendingViolation, setPendingViolation] = useState(null);
  const [pendingCallback, setPendingCallback] = useState(null);

  const {
    getViolationStatus,
    getHumanRationale,
    shouldShowOverrideDialog,
    logOverride,
    sessionOverrideCount,
    incrementOverrideCount,
    recommendation,
  } = useCopilotStore();

  /**
   * Check if a violation toggle should trigger override flow
   * @param {string} violationId - Violation being toggled
   * @param {Object} violation - Full violation object
   * @param {Function} onProceed - Callback if override is confirmed/allowed
   * @returns {boolean} True if override flow was triggered
   */
  const checkOverride = useCallback(
    (violationId, violation, onProceed) => {
      // No recommendation loaded - proceed without override
      if (!recommendation) {
        onProceed();
        return false;
      }

      const status = getViolationStatus(violationId);

      // If recommended or no status, proceed without override
      if (!status || status === 'recommended') {
        onProceed();
        return false;
      }

      // Store pending state
      setPendingViolation(violation);
      setPendingCallback(() => onProceed);

      // First override - show dialog
      if (shouldShowOverrideDialog()) {
        setDialogOpen(true);
        return true;
      }

      // Subsequent override - show toast and proceed
      logOverride(violationId);
      setToastOpen(true);
      onProceed();
      return true;
    },
    [recommendation, getViolationStatus, shouldShowOverrideDialog, logOverride]
  );

  /**
   * Handle dialog confirmation
   */
  const handleDialogConfirm = useCallback(() => {
    if (pendingViolation && pendingCallback) {
      logOverride(pendingViolation.violation_id);
      incrementOverrideCount();
      pendingCallback();
    }
    setDialogOpen(false);
    setPendingViolation(null);
    setPendingCallback(null);
  }, [pendingViolation, pendingCallback, logOverride, incrementOverrideCount]);

  /**
   * Handle dialog cancel
   */
  const handleDialogClose = useCallback(() => {
    setDialogOpen(false);
    setPendingViolation(null);
    setPendingCallback(null);
  }, []);

  /**
   * Handle toast close
   */
  const handleToastClose = useCallback(() => {
    setToastOpen(false);
  }, []);

  return {
    checkOverride,
    // Dialog props
    dialogOpen,
    pendingViolation,
    copilotAdvice: pendingViolation
      ? getViolationStatus(pendingViolation.violation_id)
      : null,
    rationale: pendingViolation
      ? getHumanRationale(pendingViolation.violation_id)
      : null,
    onDialogConfirm: handleDialogConfirm,
    onDialogClose: handleDialogClose,
    // Toast props
    toastOpen,
    overrideCount: sessionOverrideCount,
    onToastClose: handleToastClose,
  };
}

/**
 * OverrideController component - renders dialog and toast
 * Use with the useOverrideController hook
 */
export default function OverrideController({ controller }) {
  const {
    dialogOpen,
    pendingViolation,
    copilotAdvice,
    rationale,
    onDialogConfirm,
    onDialogClose,
    toastOpen,
    overrideCount,
    onToastClose,
  } = controller;

  return (
    <>
      <OverrideConfirmDialog
        open={dialogOpen}
        onClose={onDialogClose}
        onConfirm={onDialogConfirm}
        violation={pendingViolation}
        copilotAdvice={copilotAdvice}
        rationale={rationale}
      />
      <OverrideToast
        open={toastOpen}
        onClose={onToastClose}
        violation={pendingViolation}
        overrideCount={overrideCount}
      />
    </>
  );
}
