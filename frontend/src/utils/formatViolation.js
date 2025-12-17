/**
 * Credit Engine 2.0 - Violation Formatting Utilities
 * Converts violation types and data into plain English
 */

// Violation type to plain English mapping
// NOTE: Dropdown filters are dynamically populated based on violations in audit results.
// Only violation types that exist in the current audit will appear in the filter dropdown.
const VIOLATION_LABELS = {
  // Single-bureau violations
  missing_dofd: 'Missing Date Of First Delinquency',
  missing_date_opened: 'Missing Account Open Date',
  missing_dla: 'Missing Date Of Last Activity',
  missing_payment_status: 'Missing Payment Status',
  missing_scheduled_payment: 'Missing Scheduled Payment',
  missing_original_creditor: 'Missing Original Creditor Name',
  negative_balance: 'Invalid Negative Balance',
  negative_credit_limit: 'Invalid Negative Credit Limit',
  past_due_exceeds_balance: 'Past Due Exceeds Total Balance',
  balance_exceeds_high_credit: 'Balance Exceeds High Credit',
  balance_exceeds_credit_limit: 'Balance Exceeds Credit Limit',
  future_date: 'Future Date Reported',
  dofd_after_date_opened: 'DOFD After Date Opened',
  invalid_metro2_code: 'Invalid Metro 2 Code',
  closed_oc_reporting_balance: 'Closed Account Shows Balance',
  closed_oc_reporting_past_due: 'Closed Account Shows Past Due',
  chargeoff_missing_dofd: 'Charge-Off Missing DOFD',
  status_payment_history_mismatch: 'Status Payment History Mismatch',
  phantom_late_payment: 'Phantom Late Payment',
  paid_status_with_balance: 'Paid Status With Balance',
  zero_balance_not_paid: 'Zero Balance Not Paid',
  delinquency_jump: 'Delinquency Jump',
  stagnant_delinquency: 'Stagnant Delinquency',
  double_jeopardy: 'Double Jeopardy Reporting',

  // Cross-bureau violations
  dofd_mismatch: 'DOFD Differs Across Bureaus',
  date_opened_mismatch: 'Open Date Differs Across Bureaus',
  balance_mismatch: 'Balance Differs Across Bureaus',
  status_mismatch: 'Status Differs Across Bureaus',
  payment_history_mismatch: 'Payment History Differs',
  past_due_mismatch: 'Past Due Differs Across Bureaus',
  closed_vs_open_conflict: 'Open/Closed Status Conflict',
  creditor_name_mismatch: 'Creditor Name Mismatch',
  account_number_mismatch: 'Account Number Mismatch',
  dispute_flag_mismatch: 'Dispute Flag Mismatch',
  ecoa_code_mismatch: 'ECOA Code Mismatch',
  authorized_user_derogatory: 'Authorized User With Derogatory',

  // Temporal violations
  stale_reporting: 'Stale/Outdated Data',
  re_aging: 'Re-Aging Violation',
  dofd_replaced_with_date_opened: 'DOFD Replaced With Date Opened',
  impossible_timeline: 'Impossible Date Sequence',
  obsolete_account: 'Account Past 7-Year Limit',
  time_barred_debt_risk: 'Time-Barred Debt Risk',

  // Inquiry violations
  unauthorized_hard_inquiry: 'Unauthorized Hard Inquiry',
  inquiry_misclassification: 'Inquiry Misclassification',
  collection_fishing_inquiry: 'Collection Fishing Inquiry',
  duplicate_inquiry: 'Duplicate Inquiry',

  // Metro 2 Portfolio Type violations
  metro2_portfolio_mismatch: 'Student Loan Portfolio Mismatch',

  // Student Loan / Installment Account Balance Reviews
  student_loan_capitalized_interest: 'Student Loan Balance Review (Capitalized Interest)',
  mortgage_balance_review: 'Mortgage Balance Review (Escrow/Amortization)',

  // Identity Integrity violations
  identity_suffix_mismatch: 'Identity Suffix Mismatch',
  identity_name_mismatch: 'Identity Name Mismatch',
  identity_ssn_mismatch: 'Identity SSN Mismatch',
  identity_address_mismatch: 'Identity Address Mismatch',
  mixed_file_indicator: 'Mixed File Indicator',
  deceased_indicator_error: 'Deceased Indicator Error',
  child_identity_theft: 'Child Identity Theft',

  // Public Record violations
  judgment_not_updated: 'Judgment Not Updated',
  ncap_violation_judgment: 'NCAP Violation (Judgment)',
  bankruptcy_date_error: 'Bankruptcy Date Error',
  bankruptcy_obsolete: 'Bankruptcy Obsolete',

  // FDCPA Collection violations
  collection_balance_inflation: 'Collection Balance Inflation',
  false_debt_status: 'False Debt Status',
  unverified_debt_reporting: 'Unverified Debt Reporting',
};

// Severity to color/label mapping
const SEVERITY_CONFIG = {
  HIGH: { color: 'error', label: 'High Priority' },
  MEDIUM: { color: 'warning', label: 'Medium Priority' },
  LOW: { color: 'info', label: 'Low Priority' },
};

// =============================================================================
// UI SEMANTIC LAYER - Violations vs Advisories (B6)
// =============================================================================
// This layer controls HOW items are presented to users without changing
// backend detection logic, severity, or legal rules.
//
// UI Modes:
// - "violation" → MEDIUM/HIGH severity → actionable, dispute-ready
// - "advisory"  → LOW severity → informational, review-only
// =============================================================================

/**
 * Type-specific UI overrides for special violation types.
 * These provide custom titles/icons for specific scenarios.
 * Types not listed here use default severity-based rendering.
 */
const UI_TYPE_OVERRIDES = {
  // Balance review types (typically LOW severity, advisory mode)
  student_loan_capitalized_interest: {
    title: 'Balance Review (Capitalized Interest)',
    icon: 'ℹ️',
  },
  mortgage_balance_review: {
    title: 'Mortgage Balance Check',
    icon: 'ℹ️',
  },

  // Legal violation types (typically HIGH severity)
  collection_balance_inflation: {
    title: 'Potential FDCPA Violation',
    icon: '⛔',
  },
  false_debt_status: {
    title: 'Potential FDCPA Violation',
    icon: '⛔',
  },
  unverified_debt_reporting: {
    title: 'Potential FDCPA Violation',
    icon: '⛔',
  },
  re_aging: {
    title: 'Re-Aging Violation (FCRA)',
    icon: '⛔',
  },
  obsolete_account: {
    title: 'Obsolete Account (7-Year Limit)',
    icon: '⛔',
  },
  child_identity_theft: {
    title: 'Potential Identity Theft',
    icon: '⛔',
  },
  deceased_indicator_error: {
    title: 'Critical Identity Error',
    icon: '⛔',
  },
};

/**
 * Get UI rendering configuration based on violation type and severity.
 * Implements semantic layer that distinguishes violations from advisories.
 *
 * @param {string} violationType - The violation_type from backend
 * @param {string} severity - HIGH, MEDIUM, or LOW
 * @returns {Object} UI configuration for rendering
 */
export const getViolationUI = (violationType, severity) => {
  const normalizedSeverity = severity?.toUpperCase() || 'MEDIUM';
  const typeOverride = UI_TYPE_OVERRIDES[violationType] || {};

  // Determine UI mode based on severity
  const isAdvisory = normalizedSeverity === 'LOW';

  if (isAdvisory) {
    // ADVISORY MODE - Informational, review-only
    return {
      mode: 'advisory',
      headerText: typeOverride.title
        ? `${typeOverride.icon || 'ℹ️'} ${typeOverride.title.toUpperCase()}`
        : 'ℹ️ ACCOUNT REVIEW SIGNAL',
      boxTitle: 'Review Details',
      expectedLabel: 'Reference',
      actualLabel: 'Reported',
      expectedColor: '#6B7280',  // Gray - neutral
      actualColor: '#6B7280',    // Gray - neutral
      ctaText: 'Verify Accuracy',
      ctaShow: false,  // Don't encourage disputes for advisories
      borderColor: '#E5E7EB',
      bgColor: '#F9FAFB',
      iconColor: '#6B7280',
    };
  }

  if (normalizedSeverity === 'HIGH') {
    // HIGH SEVERITY - Potential legal violation
    return {
      mode: 'violation',
      headerText: typeOverride.title
        ? `${typeOverride.icon || '⛔'} ${typeOverride.title.toUpperCase()}`
        : '⛔ POTENTIAL LEGAL VIOLATION',
      boxTitle: 'Discrepancy Detected',
      expectedLabel: 'Expected',
      actualLabel: 'Actual Reporting',
      expectedColor: '#10B981',  // Green
      actualColor: '#EF4444',    // Red
      ctaText: 'Dispute Immediately',
      ctaShow: true,
      borderColor: '#FCA5A5',
      bgColor: '#FEF2F2',
      iconColor: '#DC2626',
    };
  }

  // MEDIUM SEVERITY - Standard discrepancy
  return {
    mode: 'violation',
    headerText: typeOverride.title
      ? `${typeOverride.icon || '⚠️'} ${typeOverride.title.toUpperCase()}`
      : '⚠️ DISCREPANCY DETECTED',
    boxTitle: 'Discrepancy Detected',
    expectedLabel: 'Expected',
    actualLabel: 'Actual Reporting',
    expectedColor: '#10B981',  // Green
    actualColor: '#EF4444',    // Red
    ctaText: 'Dispute This Item',
    ctaShow: true,
    borderColor: '#FCD34D',
    bgColor: '#FFFBEB',
    iconColor: '#D97706',
  };
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
    // Normalize Metro 2 field citation to prevent "Field Field" duplication
    metroDisplay: violation.metro2_field
      ? `Metro 2 Field ${violation.metro2_field.replace(/^Field\s+/i, '')}`
      : null,
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
  getViolationUI,
  getSeverityConfig,
  formatViolation,
  groupViolationsByType,
  groupViolationsByAccount,
  groupViolationsByBureau,
};
