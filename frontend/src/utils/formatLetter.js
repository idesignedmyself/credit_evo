/**
 * Credit Engine 2.0 - Letter Formatting Utilities
 * Handles letter content formatting and download
 */

/**
 * Format letter content for display (preserves line breaks)
 * @param {string} content - Raw letter content
 * @returns {string} HTML-safe content with preserved formatting
 */
export const formatLetterContent = (content) => {
  if (!content) return '';
  // Preserve paragraphs and line breaks
  return content
    .split('\n\n')
    .map(para => `<p>${para.replace(/\n/g, '<br/>')}</p>`)
    .join('');
};

/**
 * Get letter as plain text for download
 * @param {Object} letter - Letter object from API
 * @returns {string} Plain text content
 */
export const getLetterPlainText = (letter) => {
  return letter?.content || '';
};

/**
 * Download letter as text file
 * @param {Object} letter - Letter object from API
 * @param {string} filename - Optional filename
 */
export const downloadLetterAsText = (letter, filename = 'dispute_letter.txt') => {
  const content = getLetterPlainText(letter);
  const blob = new Blob([content], { type: 'text/plain;charset=utf-8' });
  const url = URL.createObjectURL(blob);
  const link = document.createElement('a');
  link.href = url;
  link.download = filename;
  document.body.appendChild(link);
  link.click();
  document.body.removeChild(link);
  URL.revokeObjectURL(url);
};

/**
 * Copy letter content to clipboard
 * @param {Object} letter - Letter object from API
 * @returns {Promise<boolean>} Success status
 */
export const copyLetterToClipboard = async (letter) => {
  const content = getLetterPlainText(letter);
  try {
    await navigator.clipboard.writeText(content);
    return true;
  } catch (error) {
    console.error('Failed to copy to clipboard:', error);
    return false;
  }
};

/**
 * Get letter summary stats
 * @param {Object} letter - Letter object from API
 * @returns {Object} Summary statistics
 */
export const getLetterStats = (letter) => {
  if (!letter) return null;

  return {
    wordCount: letter.metadata?.word_count || letter.word_count || 0,
    violationsCited: letter.violations_cited?.length || 0,
    accountsDisputed: letter.accounts_disputed?.length || 0,
    tone: letter.metadata?.tone_used || 'formal',
  };
};

/**
 * Format tone label for display
 * @param {string} tone - Tone value
 * @returns {string} Display label
 */
export const formatToneLabel = (tone) => {
  const labels = {
    formal: 'Formal & Professional',
    assertive: 'Assertive & Direct',
    conversational: 'Conversational & Friendly',
    narrative: 'Narrative & Explanatory',
  };
  return labels[tone] || tone;
};

/**
 * Format grouping strategy label for display
 * @param {string} strategy - Strategy value
 * @returns {string} Display label
 */
export const formatGroupingLabel = (strategy) => {
  const labels = {
    by_violation_type: 'Group by Violation Type',
    by_account: 'Group by Account',
    by_bureau: 'Group by Bureau',
  };
  return labels[strategy] || strategy;
};

export default {
  formatLetterContent,
  getLetterPlainText,
  downloadLetterAsText,
  copyLetterToClipboard,
  getLetterStats,
  formatToneLabel,
  formatGroupingLabel,
};
