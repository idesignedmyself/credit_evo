/**
 * Credit Engine 2.0 - Date Formatting Utilities
 */

/**
 * Format date for display
 * @param {string|Date} date - Date to format
 * @param {Object} options - Intl.DateTimeFormat options
 * @returns {string} Formatted date string
 */
export const formatDate = (date, options = {}) => {
  if (!date) return 'N/A';

  const dateObj = typeof date === 'string' ? new Date(date) : date;

  if (isNaN(dateObj.getTime())) return 'Invalid Date';

  const defaultOptions = {
    year: 'numeric',
    month: 'long',
    day: 'numeric',
    ...options,
  };

  return dateObj.toLocaleDateString('en-US', defaultOptions);
};

/**
 * Format date as short format (MM/DD/YYYY)
 * @param {string|Date} date - Date to format
 * @returns {string} Formatted date string
 */
export const formatDateShort = (date) => {
  return formatDate(date, {
    year: 'numeric',
    month: '2-digit',
    day: '2-digit',
  });
};

/**
 * Format date as ISO string (YYYY-MM-DD)
 * @param {string|Date} date - Date to format
 * @returns {string} ISO date string
 */
export const formatDateISO = (date) => {
  if (!date) return null;
  const dateObj = typeof date === 'string' ? new Date(date) : date;
  if (isNaN(dateObj.getTime())) return null;
  return dateObj.toISOString().split('T')[0];
};

/**
 * Get relative time string (e.g., "3 days ago")
 * @param {string|Date} date - Date to compare
 * @returns {string} Relative time string
 */
export const getRelativeTime = (date) => {
  if (!date) return 'N/A';

  const dateObj = typeof date === 'string' ? new Date(date) : date;
  if (isNaN(dateObj.getTime())) return 'Invalid Date';

  const now = new Date();
  const diffMs = now - dateObj;
  const diffDays = Math.floor(diffMs / (1000 * 60 * 60 * 24));

  if (diffDays === 0) return 'Today';
  if (diffDays === 1) return 'Yesterday';
  if (diffDays < 7) return `${diffDays} days ago`;
  if (diffDays < 30) return `${Math.floor(diffDays / 7)} weeks ago`;
  if (diffDays < 365) return `${Math.floor(diffDays / 30)} months ago`;
  return `${Math.floor(diffDays / 365)} years ago`;
};

/**
 * Check if date is in the future
 * @param {string|Date} date - Date to check
 * @returns {boolean}
 */
export const isFutureDate = (date) => {
  if (!date) return false;
  const dateObj = typeof date === 'string' ? new Date(date) : date;
  return dateObj > new Date();
};

/**
 * Calculate years since date
 * @param {string|Date} date - Start date
 * @returns {number} Number of years
 */
export const yearsSince = (date) => {
  if (!date) return 0;
  const dateObj = typeof date === 'string' ? new Date(date) : date;
  const diffMs = new Date() - dateObj;
  return Math.floor(diffMs / (1000 * 60 * 60 * 24 * 365));
};

export default {
  formatDate,
  formatDateShort,
  formatDateISO,
  getRelativeTime,
  isFutureDate,
  yearsSince,
};
