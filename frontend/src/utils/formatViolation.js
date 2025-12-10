/**
 * Credit Engine 2.0 - Violation Formatting Utilities
 * Converts violation types and data into plain English
 */

// Violation type to plain English mapping
const VIOLATION_LABELS = {
  missing_dofd: 'Missing Date of First Delinquency',
  missing_date_opened: 'Missing Account Open Date',
  missing_dla: 'Missing Date of Last Activity',
  missing_original_creditor: 'Missing Original Creditor Name',
  negative_balance: 'Invalid Negative Balance',
  past_due_exceeds_balance: 'Past Due Exceeds Total Balance',
  balance_exceeds_high_credit: 'Balance Exceeds Credit Limit',
  negative_credit_limit: 'Invalid Negative Credit Limit',
  obsolete_account: 'Account Past 7-Year Limit',
  future_date: 'Future Date Reported',
  stale_reporting: 'Stale/Outdated Data',
  impossible_timeline: 'Impossible Date Sequence',
  closed_oc_reporting_balance: 'Closed Account Shows Balance',
  closed_oc_reporting_past_due: 'Closed Account Shows Past Due',
  chargeoff_missing_dofd: 'Charge-Off Missing DOFD',
  dofd_mismatch: 'DOFD Differs Across Bureaus',
  date_opened_mismatch: 'Open Date Differs Across Bureaus',
  balance_mismatch: 'Balance Differs Across Bureaus',
  status_mismatch: 'Status Differs Across Bureaus',
  payment_history_mismatch: 'Payment History Differs',
  past_due_mismatch: 'Past Due Differs Across Bureaus',
  closed_vs_open_conflict: 'Open/Closed Status Conflict',
  creditor_name_mismatch: 'Creditor Name Mismatch',
  account_number_mismatch: 'Account Number Mismatch',
};

// Severity to color/label mapping
const SEVERITY_CONFIG = {
  HIGH: { color: 'error', label: 'High Priority' },
  MEDIUM: { color: 'warning', label: 'Medium Priority' },
  LOW: { color: 'info', label: 'Low Priority' },
};

/**
 * Get human-readable label for violation type
 * @param {string} violationType - The violation type enum value
 * @returns {string} Human-readable label
 */
export const getViolationLabel = (violationType) => {
  return VIOLATION_LABELS[violationType] || violationType.replace(/_/g, ' ').replace(/\b\w/g, c => c.toUpperCase());
};

/**
 * Get severity configuration
 * @param {string} severity - HIGH, MEDIUM, or LOW
 * @returns {{color: string, label: string}}
 */
export const getSeverityConfig = (severity) => {
  return SEVERITY_CONFIG[severity?.toUpperCase()] || SEVERITY_CONFIG.MEDIUM;
};

/**
 * Format violation for display
 * @param {Object} violation - Violation object from API
 * @returns {Object} Formatted violation with display properties
 */
export const formatViolation = (violation) => {
  // Guard against null/undefined violation
  if (!violation) return null;

  const severityConfig = getSeverityConfig(violation.severity);

  return {
    ...violation,
    displayLabel: getViolationLabel(violation.violation_type),
    severityColor: severityConfig.color,
    severityLabel: severityConfig.label,
    displayDescription: violation.description || 'No description available',
    accountDisplay: violation.creditor_name || 'Unknown Account',
    fcraDisplay: violation.fcra_section ? `FCRA §${violation.fcra_section}` : null,
    metroDisplay: violation.metro2_field ? `Metro 2 Field ${violation.metro2_field}` : null,
  };
};

/**
 * Group violations by type for display
 * @param {Array} violations - Array of violation objects
 * @returns {Object} Grouped violations by type
 */
export const groupViolationsByType = (violations) => {
  const safeViolations = violations ?? [];
  if (!Array.isArray(safeViolations)) return {};

  const grouped = {};
  safeViolations.forEach(v => {
    if (!v) return;
    const label = getViolationLabel(v.violation_type);
    if (!grouped[label]) {
      grouped[label] = [];
    }
    const formatted = formatViolation(v);
    if (formatted) grouped[label].push(formatted);
  });
  return grouped;
};

/**
 * Group violations by account for display
 * @param {Array} violations - Array of violation objects
 * @returns {Object} Grouped violations by account
 */
export const groupViolationsByAccount = (violations) => {
  const safeViolations = violations ?? [];
  if (!Array.isArray(safeViolations)) return {};

  const grouped = {};
  safeViolations.forEach(v => {
    if (!v) return;
    const key = v.creditor_name || 'Unknown Account';
    if (!grouped[key]) {
      grouped[key] = [];
    }
    const formatted = formatViolation(v);
    if (formatted) grouped[key].push(formatted);
  });
  return grouped;
};

// Bureau name formatting
const BUREAU_LABELS = {
  transunion: 'TransUnion',
  experian: 'Experian',
  equifax: 'Equifax',
};

/**
 * Group violations by bureau for display
 * @param {Array} violations - Array of violation objects
 * @returns {Object} Grouped violations by bureau
 */
export const groupViolationsByBureau = (violations) => {
  const safeViolations = violations ?? [];
  if (!Array.isArray(safeViolations)) return {};

  const grouped = {};
  safeViolations.forEach(v => {
    if (!v) return;
    const bureauKey = v.bureau?.toLowerCase() || 'unknown';
    const label = BUREAU_LABELS[bureauKey] || bureauKey.charAt(0).toUpperCase() + bureauKey.slice(1);
    if (!grouped[label]) {
      grouped[label] = [];
    }
    const formatted = formatViolation(v);
    if (formatted) grouped[label].push(formatted);
  });
  return grouped;
};

export default {
  getViolationLabel,
  getSeverityConfig,
  formatViolation,
  groupViolationsByType,
  groupViolationsByAccount,
  groupViolationsByBureau,
};
