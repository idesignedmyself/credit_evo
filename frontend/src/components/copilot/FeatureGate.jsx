/**
 * FeatureGate - Wrapper for tier-gated features
 *
 * Currently a no-op - all authenticated users see Copilot.
 * Future: Hook into subscription/tier system.
 */
import React from 'react';

/**
 * Feature gate wrapper
 * @param {Object} props
 * @param {React.ReactNode} props.children - Content to render
 * @param {string} [props.feature] - Feature flag name (for future use)
 * @param {React.ReactNode} [props.fallback] - Fallback content for gated users
 */
export default function FeatureGate({ children, feature, fallback = null }) {
  // For now, all authenticated users have access
  // Future: Check user tier/subscription
  const hasAccess = true;

  if (!hasAccess) {
    return fallback;
  }

  return <>{children}</>;
}
