/**
 * Credit Engine 2.0 - Disputes Page
 * Matches the exact style of LettersPage with expandable rows
 */
import React, { useState, useEffect } from 'react';
import {
  Box,
  Typography,
  Paper,
  Table,
  TableBody,
  TableCell,
  TableContainer,
  TableHead,
  TableRow,
  IconButton,
  Alert,
  CircularProgress,
  Chip,
  Collapse,
  FormControl,
  InputLabel,
  Select,
  MenuItem,
  Stack,
  Divider,
  Tooltip,
  Button,
  Dialog,
  DialogTitle,
  DialogContent,
  DialogActions,
  TextField,
  Switch,
  FormControlLabel,
} from '@mui/material';
import ExpandMoreIcon from '@mui/icons-material/ExpandMore';
import ExpandLessIcon from '@mui/icons-material/ExpandLess';
import { DatePicker } from '@mui/x-date-pickers/DatePicker';
import { LocalizationProvider } from '@mui/x-date-pickers/LocalizationProvider';
import { AdapterDayjs } from '@mui/x-date-pickers/AdapterDayjs';
import dayjs from 'dayjs';

import {
  getDisputes,
  getDisputeTimeline,
  logResponse,
  deleteDispute,
  startTracking,
  generateResponseLetter,
  saveResponseLetter,
  RESPONSE_TYPES,
  ESCALATION_STATES,
  LETTER_TYPES,
  TIER2_RESPONSE_TYPES,
  markTier2NoticeSent,
  logTier2Response,
} from '../api/disputeApi';
import DeleteIcon from '@mui/icons-material/Delete';
import PlayArrowIcon from '@mui/icons-material/PlayArrow';
import DescriptionIcon from '@mui/icons-material/Description';
import ContentCopyIcon from '@mui/icons-material/ContentCopy';
import DownloadIcon from '@mui/icons-material/Download';
import PrintIcon from '@mui/icons-material/Print';
import AutorenewIcon from '@mui/icons-material/Autorenew';
import EditIcon from '@mui/icons-material/Edit';
import VisibilityIcon from '@mui/icons-material/Visibility';
import SaveIcon from '@mui/icons-material/Save';
import SendIcon from '@mui/icons-material/Send';
import LockIcon from '@mui/icons-material/Lock';
import CheckCircleIcon from '@mui/icons-material/CheckCircle';
import WarningIcon from '@mui/icons-material/Warning';
import { jsPDF } from 'jspdf';

// =============================================================================
// HELPER FUNCTIONS
// =============================================================================

/**
 * Format date string from YYYY-MM-DD to "Month DD, YYYY"
 */
const formatDeadlineDate = (dateStr) => {
  if (!dateStr) return null;
  try {
    const date = new Date(dateStr + 'T00:00:00'); // Ensure local timezone
    return date.toLocaleDateString('en-US', {
      year: 'numeric',
      month: 'long',
      day: 'numeric',
    });
  } catch {
    return dateStr;
  }
};

// =============================================================================
// EXPANDABLE ROW CONTENT
// =============================================================================

// =============================================================================
// SINGLE VIOLATION RESPONSE ROW
// =============================================================================

const ViolationResponseRow = ({
  violation,
  disputeId,
  entityName,
  onResponseLogged,
  onGenerateLetter,
  trackingStarted,
  deadlineDate,
  testMode,
  // Tier-2 props (passed from dispute level)
  tier2NoticeSent: initialTier2Sent,
  tier2NoticeSentAt: initialTier2SentAt,
  disputeLocked,
  disputeTierReached,
}) => {
  const [responseType, setResponseType] = useState(violation.logged_response || '');
  const [responseDate, setResponseDate] = useState(null);
  const [submitting, setSubmitting] = useState(false);
  const [success, setSuccess] = useState(false);
  const [error, setError] = useState(null);

  // Tier-2 state (local for UI updates)
  const [tier2NoticeSent, setTier2NoticeSent] = useState(initialTier2Sent || false);
  const [tier2NoticeSentAt, setTier2NoticeSentAt] = useState(initialTier2SentAt || null);
  const [markingSent, setMarkingSent] = useState(false);
  const [tier2ResponseType, setTier2ResponseType] = useState('');
  const [tier2ResponseDate, setTier2ResponseDate] = useState(null);
  const [submittingTier2, setSubmittingTier2] = useState(false);
  const [tier2Result, setTier2Result] = useState(null);

  // Sync state with props when violation data changes (after data refresh)
  useEffect(() => {
    if (violation.logged_response && violation.logged_response !== responseType) {
      setResponseType(violation.logged_response);
    }
  }, [violation.logged_response]);

  // Sync tier2 state with props
  useEffect(() => {
    setTier2NoticeSent(initialTier2Sent || false);
    setTier2NoticeSentAt(initialTier2SentAt || null);
  }, [initialTier2Sent, initialTier2SentAt]);

  // Check if this violation has an enforcement response
  const hasEnforcementResponse = ['VERIFIED', 'NO_RESPONSE', 'REJECTED', 'REINSERTION'].includes(responseType);
  const isLocked = disputeLocked || disputeTierReached >= 3;

  // Tier-2 handlers
  const handleMarkTier2Sent = async () => {
    setMarkingSent(true);
    setError(null);
    try {
      const response = await markTier2NoticeSent(disputeId);
      setTier2NoticeSent(true);
      setTier2NoticeSentAt(response.tier2_notice_sent_at);
      onResponseLogged?.();
    } catch (err) {
      setError(err.response?.data?.detail || err.message || 'Failed to mark Tier-2 notice as sent');
    } finally {
      setMarkingSent(false);
    }
  };

  const handleSubmitTier2Response = async () => {
    if (!tier2ResponseType) {
      setError('Please select a Tier-2 response type');
      return;
    }
    setSubmittingTier2(true);
    setError(null);
    try {
      const response = await logTier2Response(disputeId, {
        response_type: tier2ResponseType,
        response_date: tier2ResponseDate ? tier2ResponseDate.format('YYYY-MM-DD') : dayjs().format('YYYY-MM-DD'),
      });
      setTier2Result(response);
      onResponseLogged?.();
    } catch (err) {
      setError(err.response?.data?.detail || err.message || 'Failed to log Tier-2 response');
    } finally {
      setSubmittingTier2(false);
    }
  };

  // NO_RESPONSE is only available if:
  // 1. testMode is enabled (bypass deadline check), OR
  // 2. tracking started AND deadline has passed
  const isNoResponseAvailable = () => {
    if (testMode) return true; // Bypass in test mode
    if (!trackingStarted || !deadlineDate) return false;
    const deadline = new Date(deadlineDate);
    const today = new Date();
    today.setHours(0, 0, 0, 0);
    deadline.setHours(0, 0, 0, 0);
    return today > deadline;
  };

  const handleLogResponse = async () => {
    if (!responseType) {
      setError('Please select a response type');
      return;
    }
    setSubmitting(true);
    setError(null);
    try {
      await logResponse(disputeId, {
        violation_id: violation.violation_id,
        response_type: responseType,
        response_date: responseDate ? responseDate.format('YYYY-MM-DD') : new Date().toISOString().split('T')[0],
      });
      setSuccess(true);
      onResponseLogged?.();
      setTimeout(() => setSuccess(false), 2000);
    } catch (err) {
      console.error('Failed to log response:', err);
      setError('Failed to save response');
    } finally {
      setSubmitting(false);
    }
  };

  // Determine if this response type warrants enforcement letter
  const canGenerateLetter = responseType && ['NO_RESPONSE', 'VERIFIED', 'REJECTED', 'REINSERTION'].includes(responseType);

  const getResponseChipColor = (type) => {
    switch (type) {
      case 'DELETED': return 'success';
      case 'VERIFIED': return 'warning';
      case 'NO_RESPONSE': return 'error';
      case 'REJECTED': return 'error';
      case 'REINSERTION': return 'error';
      default: return 'default';
    }
  };

  return (
    <Box
      sx={{
        p: 2.5,
        bgcolor: 'white',
        borderRadius: 2,
        border: '1px solid',
        borderColor: success ? 'success.light' : 'divider',
        mb: 2,
      }}
    >
      {/* Violation Info - Creditor name prominent */}
      <Box sx={{ mb: 2.5, display: 'flex', justifyContent: 'space-between', alignItems: 'flex-start' }}>
        <Box>
          <Typography variant="subtitle2" sx={{ fontWeight: 600, mb: 0.5 }}>
            {violation.creditor_name || 'Unknown Creditor'}
            {violation.account_number_masked && (
              <Typography component="span" variant="body2" color="text.secondary" sx={{ ml: 1, fontWeight: 400 }}>
                ({violation.account_number_masked})
              </Typography>
            )}
          </Typography>
          <Stack direction="row" spacing={1} alignItems="center">
            <Chip
              label={violation.violation_type?.replace(/_/g, ' ') || 'Unknown Violation'}
              size="small"
              color="error"
              variant="outlined"
              sx={{ textTransform: 'capitalize' }}
            />
            {violation.severity && (
              <Chip
                label={violation.severity}
                size="small"
                sx={{ height: 22, fontSize: '0.7rem' }}
                color={violation.severity === 'HIGH' ? 'error' : violation.severity === 'MEDIUM' ? 'warning' : 'default'}
                variant="outlined"
              />
            )}
            {responseType && (
              <Chip
                label={RESPONSE_TYPES[responseType]?.label || responseType}
                size="small"
                color={getResponseChipColor(responseType)}
                variant="filled"
                sx={{ height: 22, fontSize: '0.7rem' }}
              />
            )}
          </Stack>
        </Box>

        {/* Generate Letter Button - only for actionable responses */}
        {canGenerateLetter && (
          <Tooltip title={`Generate ${RESPONSE_TYPES[responseType]?.label} letter for this violation`}>
            <Button
              variant="outlined"
              size="small"
              startIcon={<DescriptionIcon />}
              onClick={() => onGenerateLetter(violation, responseType)}
              sx={{ ml: 2, whiteSpace: 'nowrap' }}
            >
              Generate Letter
            </Button>
          </Tooltip>
        )}
      </Box>

      {error && (
        <Alert severity="error" sx={{ mb: 2, py: 0.5 }} onClose={() => setError(null)}>
          {error}
        </Alert>
      )}

      {/* Response Form */}
      <Stack direction={{ xs: 'column', sm: 'row' }} spacing={2} alignItems="flex-start">
        <FormControl size="small" sx={{ minWidth: 220 }}>
          <InputLabel>Response *</InputLabel>
          <Select
            value={responseType}
            label="Response *"
            onChange={(e) => setResponseType(e.target.value)}
            disabled={submitting}
          >
            <MenuItem value="">
              <em>Select outcome...</em>
            </MenuItem>
            {Object.entries(RESPONSE_TYPES).map(([key, config]) => {
              const isNoResponseBlocked = key === 'NO_RESPONSE' && !isNoResponseAvailable();

              // Disabled items: Use Tooltip + span wrapper (needed for tooltip on disabled element)
              // Selection doesn't matter since the item is disabled anyway
              if (isNoResponseBlocked) {
                const disabledReason = !trackingStarted ? 'Start tracking first' : 'Deadline has not passed';
                return (
                  <Tooltip key={key} title={disabledReason} placement="right" arrow>
                    <span>
                      <MenuItem value={key} disabled>
                        {config.label}
                      </MenuItem>
                    </span>
                  </Tooltip>
                );
              }

              // Enabled items: Plain MenuItem with native title attribute
              // NO wrapper elements - this is critical for Select click handling to work
              return (
                <MenuItem key={key} value={key} title={config.description}>
                  {config.label}
                  {!config.enforcement && ' (resolution)'}
                </MenuItem>
              );
            })}
          </Select>
        </FormControl>

        <LocalizationProvider dateAdapter={AdapterDayjs}>
          <DatePicker
            label="Response Date"
            value={responseDate}
            onChange={setResponseDate}
            maxDate={dayjs()}
            slotProps={{
              textField: {
                size: 'small',
                sx: { minWidth: 170 },
              },
            }}
          />
        </LocalizationProvider>

        <Button
          variant="contained"
          size="medium"
          onClick={handleLogResponse}
          disabled={submitting || !responseType}
          disableElevation
          sx={{ minWidth: 90, height: 40 }}
        >
          {submitting ? <CircularProgress size={18} /> : 'Save'}
        </Button>

        {success && (
          <Chip label="Saved!" size="small" color="success" variant="filled" sx={{ height: 28 }} />
        )}
      </Stack>

      {/* Strategic framing for response types */}
      {responseType === 'DELETED' && (
        <Typography variant="caption" color="text.secondary" sx={{ display: 'block', mt: 1.5 }}>
          Item deleted - no enforcement letter needed. A 90-day reinsertion watch will be created.
        </Typography>
      )}
      {responseType === 'VERIFIED' && (
        <Alert severity="info" sx={{ mt: 1.5, py: 0.5 }} icon={false}>
          <Typography variant="caption">
            <strong>Strategic note:</strong> "Verified" means the bureau claims the furnisher confirmed the data.
            This does <strong>not</strong> mean the information is accurate. You may demand their Method of Verification
            and challenge the substantive accuracy.
          </Typography>
        </Alert>
      )}
      {responseType === 'NO_RESPONSE' && (
        <Alert severity="warning" sx={{ mt: 1.5, py: 0.5 }} icon={false}>
          <Typography variant="caption">
            <strong>Strategic note:</strong> No response within the statutory deadline is a procedural violation.
            Generate an enforcement letter citing 15 U.S.C. §1681i(a)(1) failure to investigate.
          </Typography>
        </Alert>
      )}
      {responseType === 'REJECTED' && (
        <Alert severity="error" sx={{ mt: 1.5, py: 0.5 }} icon={false}>
          <Typography variant="caption">
            <strong>Strategic note:</strong> "Frivolous/Rejected" disputes trigger specific FCRA rights.
            The bureau must provide their reason in writing. Challenge their determination if unsupported.
          </Typography>
        </Alert>
      )}
      {responseType === 'REINSERTION' && (
        <Alert severity="error" sx={{ mt: 1.5, py: 0.5 }} icon={false}>
          <Typography variant="caption">
            <strong>Strategic note:</strong> Reinsertion without proper notice is a separate FCRA violation.
            Under §1681i(a)(5), they must certify accuracy and provide 5-day written notice.
          </Typography>
        </Alert>
      )}

      {/* Tier-2 Section - only show for violations with enforcement responses */}
      {hasEnforcementResponse && !isLocked && (
        <Box sx={{ mt: 2, pt: 2, borderTop: '1px dashed', borderColor: 'divider' }}>
          <Typography variant="caption" sx={{ fontWeight: 600, color: 'text.secondary', display: 'block', mb: 1 }}>
            Tier-2 Supervisory Escalation
          </Typography>

          {tier2Result ? (
            // Show result after Tier-2 response submitted
            <Alert
              severity={tier2Result.status === 'CURED_AT_TIER_2' ? 'success' : 'error'}
              icon={tier2Result.status === 'CURED_AT_TIER_2' ? <CheckCircleIcon /> : <LockIcon />}
            >
              <Typography variant="body2">
                {tier2Result.status === 'CURED_AT_TIER_2'
                  ? 'Violation cured at Tier-2. Dispute closed.'
                  : `Promoted to Tier-3 (Locked). Classification: ${tier2Result.ledger_entry?.examiner_classification || 'N/A'}`}
              </Typography>
            </Alert>
          ) : !tier2NoticeSent ? (
            // Mark as Sent button
            <Stack direction="row" spacing={2} alignItems="center">
              <Button
                variant="outlined"
                size="small"
                color="warning"
                startIcon={markingSent ? <CircularProgress size={16} color="inherit" /> : <SendIcon />}
                onClick={handleMarkTier2Sent}
                disabled={markingSent}
              >
                {markingSent ? 'Marking...' : 'Mark Tier-2 Notice Sent'}
              </Button>
              <Typography variant="caption" color="text.secondary">
                Click after sending your Tier-2 supervisory letter
              </Typography>
            </Stack>
          ) : (
            // Tier-2 adjudication form
            <Box>
              <Alert severity="success" sx={{ mb: 1.5, py: 0 }}>
                <Typography variant="caption">
                  Tier-2 notice sent on {new Date(tier2NoticeSentAt).toLocaleDateString()}
                </Typography>
              </Alert>
              <Alert severity="warning" sx={{ mb: 1.5, py: 0 }}>
                <Typography variant="caption">
                  <strong>Warning:</strong> ONE response only. Non-CURED → Tier-3 (locked).
                </Typography>
              </Alert>
              <Stack direction="row" spacing={1.5} alignItems="center">
                <FormControl size="small" sx={{ minWidth: 200 }}>
                  <InputLabel>Tier-2 Response *</InputLabel>
                  <Select
                    value={tier2ResponseType}
                    label="Tier-2 Response *"
                    onChange={(e) => setTier2ResponseType(e.target.value)}
                    disabled={submittingTier2}
                  >
                    <MenuItem value=""><em>Select...</em></MenuItem>
                    {Object.entries(TIER2_RESPONSE_TYPES).map(([key, { value, label }]) => (
                      <MenuItem key={key} value={value}>{label}</MenuItem>
                    ))}
                  </Select>
                </FormControl>
                <LocalizationProvider dateAdapter={AdapterDayjs}>
                  <DatePicker
                    label="Response Date"
                    value={tier2ResponseDate}
                    onChange={setTier2ResponseDate}
                    maxDate={dayjs()}
                    slotProps={{ textField: { size: 'small', sx: { minWidth: 170 } } }}
                  />
                </LocalizationProvider>
                <Button
                  variant="contained"
                  size="small"
                  color={tier2ResponseType && TIER2_RESPONSE_TYPES[tier2ResponseType]?.outcome === 'tier3' ? 'error' : 'primary'}
                  onClick={handleSubmitTier2Response}
                  disabled={submittingTier2 || !tier2ResponseType}
                >
                  {submittingTier2 ? <CircularProgress size={18} /> : 'Log Response'}
                </Button>
              </Stack>
            </Box>
          )}
        </Box>
      )}

      {/* Show locked state if at Tier-3 */}
      {hasEnforcementResponse && isLocked && (
        <Box sx={{ mt: 2, pt: 2, borderTop: '1px dashed', borderColor: 'divider' }}>
          <Alert severity="error" icon={<LockIcon />}>
            <Typography variant="body2">
              <strong>Tier-3 Locked</strong> — This violation has been promoted to Tier-3. Record is immutable.
            </Typography>
          </Alert>
        </Box>
      )}
    </Box>
  );
};

// =============================================================================
// TIER-2 SUPERVISORY RESPONSE SECTION
// =============================================================================

const Tier2ResponseSection = ({ dispute, onResponseLogged }) => {
  const [tier2NoticeSent, setTier2NoticeSent] = useState(dispute.tier2_notice_sent || false);
  const [tier2NoticeSentAt, setTier2NoticeSentAt] = useState(dispute.tier2_notice_sent_at || null);
  const [markingSent, setMarkingSent] = useState(false);
  const [submittingResponse, setSubmittingResponse] = useState(false);
  const [error, setError] = useState(null);
  const [tier2ResponseType, setTier2ResponseType] = useState('');
  const [tier2ResponseDate, setTier2ResponseDate] = useState(null);
  const [result, setResult] = useState(null);

  // Check if any violation has an enforcement response logged (VERIFIED, NO_RESPONSE, REJECTED, REINSERTION)
  const violations = dispute.violation_data || [];
  const hasEnforcementResponse = violations.some(v =>
    ['VERIFIED', 'NO_RESPONSE', 'REJECTED', 'REINSERTION'].includes(v.logged_response)
  );

  // Don't show if dispute is at Tier-3 (locked) and already has a result
  const isLocked = dispute.locked || dispute.tier_reached >= 3;

  // Don't show section if no enforcement response has been logged
  if (!hasEnforcementResponse) {
    return null;
  }

  const handleMarkSent = async () => {
    setMarkingSent(true);
    setError(null);
    try {
      const response = await markTier2NoticeSent(dispute.id);
      setTier2NoticeSent(true);
      setTier2NoticeSentAt(response.tier2_notice_sent_at);
      onResponseLogged?.();
    } catch (err) {
      setError(err.response?.data?.detail || err.message || 'Failed to mark Tier-2 notice as sent');
    } finally {
      setMarkingSent(false);
    }
  };

  const handleSubmitTier2Response = async () => {
    if (!tier2ResponseType) {
      setError('Please select a response type');
      return;
    }
    setSubmittingResponse(true);
    setError(null);
    try {
      const response = await logTier2Response(dispute.id, {
        response_type: tier2ResponseType,
        response_date: tier2ResponseDate ? tier2ResponseDate.format('YYYY-MM-DD') : dayjs().format('YYYY-MM-DD'),
      });
      setResult(response);
      onResponseLogged?.();
    } catch (err) {
      setError(err.response?.data?.detail || err.message || 'Failed to log Tier-2 response');
    } finally {
      setSubmittingResponse(false);
    }
  };

  const selectedType = tier2ResponseType ? TIER2_RESPONSE_TYPES[tier2ResponseType] : null;

  // Show result after submission
  if (result) {
    const isCured = result.status === 'CURED_AT_TIER_2';
    return (
      <Box sx={{ mb: 3 }}>
        <Divider sx={{ mb: 3 }} />
        <Paper sx={{ p: 3, textAlign: 'center', bgcolor: isCured ? 'success.50' : 'error.50' }}>
          {isCured ? (
            <>
              <CheckCircleIcon sx={{ fontSize: 48, color: 'success.main', mb: 1 }} />
              <Typography variant="h6" color="success.main" gutterBottom>
                Violation Cured at Tier-2
              </Typography>
              <Typography variant="body2" color="text.secondary">
                The entity has corrected the violation. This dispute is now closed.
              </Typography>
              <Chip label={`Tier ${result.tier_reached} - Resolved`} color="success" sx={{ mt: 2 }} />
            </>
          ) : (
            <>
              <LockIcon sx={{ fontSize: 48, color: 'error.main', mb: 1 }} />
              <Typography variant="h6" color="error.main" gutterBottom>
                Promoted to Tier-3
              </Typography>
              <Typography variant="body2" color="text.secondary">
                The violation has been locked and classified. Ledger entry created.
              </Typography>
              <Chip label={`Tier ${result.tier_reached} - Locked`} color="error" icon={<LockIcon />} sx={{ mt: 2 }} />
            </>
          )}
        </Paper>
      </Box>
    );
  }

  // Show locked state if already at Tier-3
  if (isLocked) {
    return (
      <Box sx={{ mb: 3 }}>
        <Divider sx={{ mb: 3 }} />
        <Paper sx={{ p: 3, bgcolor: '#fef2f2', border: '1px solid', borderColor: 'error.light' }}>
          <Box sx={{ display: 'flex', alignItems: 'center', gap: 1 }}>
            <LockIcon color="error" />
            <Typography variant="subtitle2" color="error.main" sx={{ fontWeight: 600 }}>
              Tier-3 — Violation Locked
            </Typography>
          </Box>
          <Typography variant="body2" color="text.secondary" sx={{ mt: 1 }}>
            This violation has been promoted to Tier-3. The record is locked and no further modifications are allowed.
          </Typography>
        </Paper>
      </Box>
    );
  }

  // Get violations with enforcement responses for context
  const escalatedViolations = violations.filter(v =>
    ['VERIFIED', 'NO_RESPONSE', 'REJECTED', 'REINSERTION'].includes(v.logged_response)
  );

  return (
    <Box sx={{ mb: 3 }}>
      <Divider sx={{ mb: 3 }} />
      <Typography variant="subtitle2" sx={{ fontWeight: 600, mb: 2 }}>
        Tier-2 Supervisory Response
      </Typography>

      {/* Show which violations are being escalated */}
      <Paper sx={{ p: 2, mb: 2, bgcolor: 'grey.50', border: '1px solid', borderColor: 'grey.200' }}>
        <Typography variant="body2" color="text.secondary" sx={{ mb: 1 }}>
          <strong>Violations with enforcement responses:</strong>
        </Typography>
        {escalatedViolations.map((v, idx) => (
          <Box key={idx} sx={{ display: 'flex', alignItems: 'center', gap: 1, mb: 0.5 }}>
            <Typography variant="body2" sx={{ fontWeight: 500 }}>
              {v.creditor_name || 'Unknown'}
            </Typography>
            {v.account_number_masked && (
              <Typography variant="body2" color="text.secondary">
                ({v.account_number_masked})
              </Typography>
            )}
            <Chip
              label={v.violation_type?.replace(/_/g, ' ') || 'Violation'}
              size="small"
              variant="outlined"
              sx={{ textTransform: 'capitalize', height: 20, fontSize: '0.7rem' }}
            />
            <Chip
              label={v.logged_response}
              size="small"
              color={v.logged_response === 'VERIFIED' ? 'warning' : 'error'}
              sx={{ height: 20, fontSize: '0.7rem' }}
            />
          </Box>
        ))}
      </Paper>

      {error && (
        <Alert severity="error" sx={{ mb: 2 }} onClose={() => setError(null)}>
          {error}
        </Alert>
      )}

      {/* If notice not sent, show "Mark as Sent" button */}
      {!tier2NoticeSent ? (
        <Paper sx={{ p: 3, bgcolor: '#f0f9ff', border: '1px solid', borderColor: 'info.light' }}>
          <Typography variant="body2" color="text.secondary" sx={{ mb: 2 }}>
            After sending your Tier-2 supervisory notice letter, mark it as sent to begin the cure window.
          </Typography>
          <Alert severity="info" variant="outlined" sx={{ mb: 2 }}>
            <Typography variant="body2">
              Once marked as sent, you can log the entity's final response.
              The cure window will be anchored to the sent date.
            </Typography>
          </Alert>
          <Button
            variant="contained"
            color="primary"
            startIcon={markingSent ? <CircularProgress size={20} color="inherit" /> : <SendIcon />}
            onClick={handleMarkSent}
            disabled={markingSent}
            size="large"
          >
            {markingSent ? 'Marking as Sent...' : 'Mark Tier-2 Supervisory Notice as Sent'}
          </Button>
        </Paper>
      ) : (
        /* Notice sent, show adjudication UI */
        <Paper sx={{ p: 3, bgcolor: '#f0fdf4', border: '1px solid', borderColor: 'success.light' }}>
          <Alert severity="success" variant="outlined" sx={{ mb: 2 }}>
            <Typography variant="body2">
              Tier-2 notice marked as sent
              {tier2NoticeSentAt && ` on ${new Date(tier2NoticeSentAt).toLocaleDateString()}`}
            </Typography>
          </Alert>

          <Typography variant="body2" color="text.secondary" sx={{ mb: 2 }}>
            Log the final response to your Tier-2 supervisory notice.
          </Typography>

          <Alert severity="warning" variant="outlined" sx={{ mb: 2 }}>
            <Typography variant="body2">
              <strong>Warning:</strong> Tier-2 is exhausted after ONE response.
              Non-CURED responses auto-promote to Tier-3 (locked record).
            </Typography>
          </Alert>

          <Stack direction={{ xs: 'column', sm: 'row' }} spacing={2} alignItems="flex-start">
            <FormControl size="small" sx={{ minWidth: 280 }}>
              <InputLabel>Tier-2 Response *</InputLabel>
              <Select
                value={tier2ResponseType}
                label="Tier-2 Response *"
                onChange={(e) => setTier2ResponseType(e.target.value)}
                disabled={submittingResponse}
              >
                <MenuItem value="">
                  <em>Select response...</em>
                </MenuItem>
                {Object.entries(TIER2_RESPONSE_TYPES).map(([key, { value, label, description, outcome }]) => (
                  <MenuItem key={key} value={value}>
                    <Box sx={{ display: 'flex', alignItems: 'center', gap: 1, width: '100%' }}>
                      <Box sx={{ flex: 1 }}>
                        <Typography variant="body2">{label}</Typography>
                        <Typography variant="caption" color="text.secondary">
                          {description}
                        </Typography>
                      </Box>
                      <Chip
                        size="small"
                        label={outcome === 'close' ? 'Closes' : 'Tier-3'}
                        color={outcome === 'close' ? 'success' : 'error'}
                        variant="outlined"
                      />
                    </Box>
                  </MenuItem>
                ))}
              </Select>
            </FormControl>

            <LocalizationProvider dateAdapter={AdapterDayjs}>
              <DatePicker
                label="Response Date"
                value={tier2ResponseDate}
                onChange={setTier2ResponseDate}
                maxDate={dayjs()}
                slotProps={{
                  textField: {
                    size: 'small',
                    sx: { minWidth: 170 },
                  },
                }}
              />
            </LocalizationProvider>

            <Button
              variant="contained"
              color={selectedType?.outcome === 'tier3' ? 'error' : 'primary'}
              onClick={handleSubmitTier2Response}
              disabled={submittingResponse || !tier2ResponseType}
              sx={{ minWidth: 140, height: 40 }}
            >
              {submittingResponse ? (
                <CircularProgress size={20} />
              ) : selectedType?.outcome === 'tier3' ? (
                'Promote to Tier-3'
              ) : (
                'Log Response'
              )}
            </Button>
          </Stack>

          {/* Show outcome preview */}
          {selectedType && (
            <Alert
              severity={selectedType.outcome === 'close' ? 'success' : 'warning'}
              icon={selectedType.outcome === 'close' ? <CheckCircleIcon /> : <WarningIcon />}
              sx={{ mt: 2 }}
            >
              {selectedType.outcome === 'close' ? (
                <Typography variant="body2">
                  This will close the dispute as <strong>CURED_AT_TIER_2</strong>.
                </Typography>
              ) : (
                <Typography variant="body2">
                  This will <strong>promote to Tier-3</strong>: lock the violation record,
                  classify the examiner failure, and write an immutable ledger entry.
                </Typography>
              )}
            </Alert>
          )}
        </Paper>
      )}
    </Box>
  );
};

const ExpandedRowContent = ({ dispute, onResponseLogged, onStartTracking, onGenerateLetter, testMode, onTestModeChange }) => {
  const [timeline, setTimeline] = useState([]);
  const [loadingTimeline, setLoadingTimeline] = useState(true);
  const [error, setError] = useState(null);

  // Get violations from dispute data
  const violations = dispute.violation_data || [];

  useEffect(() => {
    const fetchTimeline = async () => {
      try {
        const data = await getDisputeTimeline(dispute.id);
        setTimeline(data || []);
      } catch (err) {
        console.error('Failed to fetch timeline:', err);
        setTimeline([]);
      } finally {
        setLoadingTimeline(false);
      }
    };
    fetchTimeline();
  }, [dispute.id]);

  const stateConfig = ESCALATION_STATES[dispute.current_state] || {};

  return (
    <Box sx={{ p: 3, bgcolor: '#fafafa' }}>
      {/* Show Start Tracking prompt if not yet tracking */}
      {!dispute.tracking_started && (
        <Alert
          severity="info"
          sx={{ mb: 3, borderRadius: 2 }}
          action={
            <Button
              color="primary"
              variant="contained"
              size="small"
              startIcon={<PlayArrowIcon />}
              onClick={() => onStartTracking(dispute)}
              disableElevation
            >
              Start Tracking
            </Button>
          }
        >
          <Typography variant="subtitle2" sx={{ fontWeight: 600 }}>
            Tracking not started
          </Typography>
          <Typography variant="body2">
            Click "Start Tracking" and enter the date you mailed the letter to start the deadline clock.
          </Typography>
        </Alert>
      )}

      {/* Dispute Details - only show if tracking started */}
      {dispute.tracking_started && (
        <Box sx={{ display: 'flex', gap: 4, mb: 3, flexWrap: 'wrap' }}>
          <Box>
            <Typography variant="caption" color="text.secondary">Deadline</Typography>
            <Typography variant="body2" sx={{ fontWeight: 500 }}>
              {formatDeadlineDate(dispute.deadline_date) || 'Clock not started'}
            </Typography>
          </Box>
          <Box>
            <Typography variant="caption" color="text.secondary">Days Remaining</Typography>
            <Typography variant="body2" sx={{ fontWeight: 500 }}>
              {dispute.days_to_deadline !== null ? `${dispute.days_to_deadline} days` : '—'}
            </Typography>
          </Box>
          <Box>
            <Typography variant="caption" color="text.secondary">Dispute Date</Typography>
            <Typography variant="body2" sx={{ fontWeight: 500 }}>
              {dispute.dispute_date}
            </Typography>
          </Box>
          <Box>
            <Typography variant="caption" color="text.secondary">Current State</Typography>
            <Typography variant="body2" sx={{ fontWeight: 500 }}>
              {stateConfig.label || dispute.current_state}
            </Typography>
          </Box>
        </Box>
      )}

      <Divider sx={{ mb: 3 }} />

      {/* Violations Summary */}
      {violations.length > 0 && (
        <Box sx={{ mb: 3 }}>
          <Typography variant="subtitle2" sx={{ fontWeight: 600, mb: 1.5 }}>
            Violations Being Disputed ({violations.length})
          </Typography>
          <Stack spacing={1}>
            {violations.map((v, i) => (
              <Box key={i} sx={{ display: 'flex', alignItems: 'center', gap: 1.5 }}>
                <Typography variant="body2" sx={{ fontWeight: 500, minWidth: 140 }}>
                  {v.creditor_name || 'Unknown'}
                  {v.account_number_masked && (
                    <Typography component="span" variant="body2" color="text.secondary" sx={{ ml: 1 }}>
                      ({v.account_number_masked})
                    </Typography>
                  )}
                </Typography>
                <Chip
                  label={v.violation_type?.replace(/_/g, ' ') || 'Unknown'}
                  size="small"
                  color="error"
                  variant="outlined"
                  sx={{ textTransform: 'capitalize' }}
                />
              </Box>
            ))}
          </Stack>
        </Box>
      )}

      <Divider sx={{ mb: 3 }} />

      {/* Per-Violation Response Section */}
      <Box sx={{ display: 'flex', justifyContent: 'space-between', alignItems: 'flex-start', mb: 1 }}>
        <Box>
          <Typography variant="subtitle2" sx={{ fontWeight: 600 }}>
            Log Response from {dispute.entity_name}
          </Typography>
          <Typography variant="caption" color="text.secondary" sx={{ display: 'block', mb: 2 }}>
            Select how the bureau responded to each violation in your dispute letter
          </Typography>
        </Box>
        <Tooltip title="Test mode: Bypass deadline checks to preview NO_RESPONSE letters before deadline passes">
          <FormControlLabel
            control={
              <Switch
                size="small"
                checked={testMode}
                onChange={(e) => onTestModeChange?.(e.target.checked)}
                color="warning"
              />
            }
            label={<Typography variant="caption" color={testMode ? 'warning.main' : 'text.secondary'}>Test Mode</Typography>}
            labelPlacement="start"
            sx={{ m: 0 }}
          />
        </Tooltip>
      </Box>

      {error && (
        <Alert severity="error" sx={{ mb: 2 }} onClose={() => setError(null)}>
          {error}
        </Alert>
      )}

      {violations.length === 0 ? (
        <Alert severity="info" sx={{ mb: 3 }}>
          No violation data available for this dispute. This may be an older dispute created before tracking was enabled.
        </Alert>
      ) : (
        <Box sx={{ mb: 3 }}>
          {violations.map((violation, idx) => (
            <ViolationResponseRow
              key={violation.violation_id || idx}
              violation={violation}
              disputeId={dispute.id}
              entityName={dispute.entity_name}
              onResponseLogged={onResponseLogged}
              onGenerateLetter={(v, responseType) => onGenerateLetter(dispute, v, responseType)}
              trackingStarted={dispute.tracking_started}
              deadlineDate={dispute.deadline_date}
              testMode={testMode}
              // Tier-2 props
              tier2NoticeSent={dispute.tier2_notice_sent}
              tier2NoticeSentAt={dispute.tier2_notice_sent_at}
              disputeLocked={dispute.locked}
              disputeTierReached={dispute.tier_reached}
            />
          ))}
        </Box>
      )}

      <Divider sx={{ mb: 3 }} />

      {/* Timeline */}
      <Typography variant="subtitle2" sx={{ fontWeight: 600, mb: 2 }}>
        Timeline
      </Typography>

      {loadingTimeline ? (
        <CircularProgress size={20} />
      ) : timeline.length === 0 ? (
        <Typography variant="body2" color="text.secondary">
          No events yet
        </Typography>
      ) : (
        <Stack spacing={1}>
          {timeline.map((entry, i) => (
            <Box
              key={entry.id || i}
              sx={{
                p: 2,
                bgcolor: 'white',
                borderRadius: 1,
                borderLeft: '3px solid',
                borderLeftColor: entry.actor === 'SYSTEM' ? 'warning.main' : 'primary.main',
              }}
            >
              <Typography variant="body2">{entry.description}</Typography>
              <Typography variant="caption" color="text.secondary">
                {new Date(entry.timestamp).toLocaleString()} • {entry.actor === 'SYSTEM' ? 'System' : 'You'}
              </Typography>
            </Box>
          ))}
        </Stack>
      )}
    </Box>
  );
};

// =============================================================================
// MAIN DISPUTES PAGE
// =============================================================================

const DisputesPage = () => {
  const [disputes, setDisputes] = useState([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);
  const [expandedId, setExpandedId] = useState(null);
  const [refreshKey, setRefreshKey] = useState(0);
  const [deletingId, setDeletingId] = useState(null);

  // Start Tracking Dialog State
  const [trackingDialogOpen, setTrackingDialogOpen] = useState(false);
  const [trackingDispute, setTrackingDispute] = useState(null);
  const [trackingSendDate, setTrackingSendDate] = useState(dayjs());
  const [trackingNumber, setTrackingNumber] = useState('');
  const [startingTracking, setStartingTracking] = useState(false);

  // Response Letter Dialog State
  const [letterDialogOpen, setLetterDialogOpen] = useState(false);
  const [letterDispute, setLetterDispute] = useState(null);
  const [letterViolation, setLetterViolation] = useState(null);
  const [letterContent, setLetterContent] = useState('');
  const [editableContent, setEditableContent] = useState('');
  const [letterLoading, setLetterLoading] = useState(false);
  const [letterError, setLetterError] = useState(null);
  const [letterResponseType, setLetterResponseType] = useState('');
  const [copiedToClipboard, setCopiedToClipboard] = useState(false);
  const [isEditing, setIsEditing] = useState(false);
  const [isSaving, setIsSaving] = useState(false);
  const [lastSaved, setLastSaved] = useState(null);
  const [letterWordCount, setLetterWordCount] = useState(0);
  const [testMode, setTestMode] = useState(false);  // Test mode - bypasses deadline, blocks save

  useEffect(() => {
    const fetchDisputes = async () => {
      setLoading(true);
      try {
        const data = await getDisputes();
        setDisputes(data || []);
        setError(null);
      } catch (err) {
        const status = err.response?.status;
        if (status >= 500) {
          setError('Server error. Please try again later.');
        } else {
          setDisputes([]);
          setError(null);
        }
      } finally {
        setLoading(false);
      }
    };
    fetchDisputes();
  }, [refreshKey]);

  const handleToggleExpand = (disputeId) => {
    setExpandedId(expandedId === disputeId ? null : disputeId);
  };

  const handleResponseLogged = () => {
    setRefreshKey((k) => k + 1);
  };

  const handleDelete = async (disputeId) => {
    if (!window.confirm('Delete this dispute? This action cannot be undone.')) {
      return;
    }
    setDeletingId(disputeId);
    try {
      await deleteDispute(disputeId);
      setDisputes(disputes.filter((d) => d.id !== disputeId));
    } catch (err) {
      setError(err.message || 'Failed to delete dispute');
    } finally {
      setDeletingId(null);
    }
  };

  // Start Tracking Dialog Handlers
  const handleOpenTrackingDialog = (dispute) => {
    setTrackingDispute(dispute);
    setTrackingSendDate(dayjs());
    setTrackingNumber('');
    setTrackingDialogOpen(true);
  };

  const handleCloseTrackingDialog = () => {
    setTrackingDialogOpen(false);
    setTrackingDispute(null);
  };

  const handleStartTracking = async () => {
    if (!trackingDispute || !trackingSendDate) return;

    setStartingTracking(true);
    setError(null);
    try {
      await startTracking(
        trackingDispute.id,
        trackingSendDate.format('YYYY-MM-DD'),
        trackingNumber || null
      );
      handleCloseTrackingDialog();
      setRefreshKey((k) => k + 1); // Refresh disputes list
    } catch (err) {
      console.error('Failed to start tracking:', err);
      setError(err.response?.data?.detail || err.message || 'Failed to start tracking');
    } finally {
      setStartingTracking(false);
    }
  };

  // Response Letter Dialog Handlers
  const handleOpenLetterDialog = (dispute, violation, responseType) => {
    setLetterDispute(dispute);
    setLetterViolation(violation);
    setLetterContent('');
    setEditableContent('');
    setLetterError(null);
    setLetterResponseType(responseType || '');
    setCopiedToClipboard(false);
    setIsEditing(false);
    setLastSaved(null);
    setLetterWordCount(0);
    setLetterDialogOpen(true);
  };

  const handleCloseLetterDialog = () => {
    setLetterDialogOpen(false);
    setLetterDispute(null);
    setLetterViolation(null);
    setLetterContent('');
    setEditableContent('');
    setLetterError(null);
    setIsEditing(false);
    setLastSaved(null);
  };

  const handleGenerateLetter = async () => {
    if (!letterDispute) return;

    setLetterLoading(true);
    setLetterError(null);
    setCopiedToClipboard(false);

    try {
      const result = await generateResponseLetter(letterDispute.id, {
        response_type: letterResponseType || null,
        violation_id: letterViolation?.violation_id || null,
        include_willful_notice: true,
        test_context: testMode,
      });
      setLetterContent(result.content);
      setEditableContent(result.content);
      setLetterWordCount(result.word_count || result.content.split(/\s+/).filter(w => w).length);
      setLastSaved(null); // Reset last saved when generating new
    } catch (err) {
      console.error('Failed to generate letter:', err);
      setLetterError(err.response?.data?.detail || err.message || 'Failed to generate letter');
    } finally {
      setLetterLoading(false);
    }
  };

  const handleCopyLetter = async () => {
    try {
      await navigator.clipboard.writeText(editableContent || letterContent);
      setCopiedToClipboard(true);
      setTimeout(() => setCopiedToClipboard(false), 2000);
    } catch (err) {
      console.error('Failed to copy:', err);
    }
  };

  const handlePrintLetter = () => {
    const printWindow = window.open('', '_blank');
    printWindow.document.write(`
      <html>
        <head>
          <title>Enforcement Letter</title>
          <style>
            body { font-family: 'Times New Roman', serif; font-size: 12pt; line-height: 1.6; margin: 1in; }
            p { margin-bottom: 1em; }
          </style>
        </head>
        <body>
          <pre style="white-space: pre-wrap; font-family: inherit;">${editableContent || letterContent || ''}</pre>
        </body>
      </html>
    `);
    printWindow.document.close();
    printWindow.print();
  };

  const handleDownloadPDF = () => {
    const content = editableContent || letterContent;
    if (!content) return;

    const pdf = new jsPDF({ unit: 'pt', format: 'letter' });
    const margin = 50;
    const pageWidth = pdf.internal.pageSize.getWidth();
    const pageHeight = pdf.internal.pageSize.getHeight();
    const maxWidth = pageWidth - (margin * 2);

    pdf.setFont('times', 'normal');
    pdf.setFontSize(12);

    const lines = pdf.splitTextToSize(content, maxWidth);
    let y = margin;
    const lineHeight = 18;

    lines.forEach((line) => {
      if (y + lineHeight > pageHeight - margin) {
        pdf.addPage();
        y = margin;
      }
      pdf.text(line, margin, y);
      y += lineHeight;
    });

    // Build filename based on response type
    const typeMap = {
      'NO_RESPONSE': 'no_response',
      'VERIFIED': 'verified',
      'REJECTED': 'frivolous_rejected',
      'REINSERTION': 'reinsertion',
      'REINSERTION_NO_NOTICE': 'reinsertion',
      'DELETED': 'deleted',
      'UPDATED': 'updated',
      'INVESTIGATING': 'investigating',
    };
    const dateStr = new Date().toISOString().split('T')[0];
    const typePrefix = letterResponseType ? (typeMap[letterResponseType] || letterResponseType.toLowerCase()) : '';
    const filename = typePrefix
      ? `${typePrefix}_dispute_letter_${dateStr}.pdf`
      : `dispute_letter_${dateStr}.pdf`;

    pdf.save(filename);
  };

  const handleSaveLetter = async () => {
    if (!letterDispute || !editableContent) return;

    // Block save in test mode
    if (testMode) {
      setLetterError('Test letters cannot be saved. Disable test mode to save.');
      return;
    }

    setIsSaving(true);
    setLetterError(null);

    try {
      await saveResponseLetter(letterDispute.id, {
        content: editableContent,
        response_type: letterResponseType,
        violation_id: letterViolation?.violation_id || null,
        test_context: testMode,
      });
      setLastSaved(new Date());
      setLetterWordCount(editableContent.split(/\s+/).filter(w => w).length);
    } catch (err) {
      console.error('Failed to save letter:', err);
      setLetterError(err.response?.data?.detail || err.message || 'Failed to save letter');
    } finally {
      setIsSaving(false);
    }
  };

  const handleEditableContentChange = (newContent) => {
    setEditableContent(newContent);
    setLetterWordCount(newContent.split(/\s+/).filter(w => w).length);
  };

  const getStateChip = (state) => {
    const config = ESCALATION_STATES[state] || {};
    return (
      <Chip
        label={config.label || state}
        size="small"
        color={config.color || 'default'}
        variant="outlined"
      />
    );
  };

  const getDeadlineChip = (days, trackingStarted, deadlineDate) => {
    if (!trackingStarted || deadlineDate === null) {
      return <Chip label="Clock not started" size="small" color="info" variant="outlined" />;
    }
    if (days === null) return <Chip label="Clock not started" size="small" color="info" variant="outlined" />;

    let color = 'default';
    let variant = 'outlined';
    if (days < 0) {
      color = 'error';
      variant = 'filled';
    } else if (days < 7) {
      color = 'warning';
    }

    return (
      <Chip
        label={formatDeadlineDate(deadlineDate)}
        size="small"
        color={color}
        variant={variant}
      />
    );
  };

  const getStatusChip = (status) => {
    return (
      <Chip
        label={status}
        size="small"
        color={status === 'CLOSED' ? 'success' : 'default'}
        variant="outlined"
      />
    );
  };

  const formatDateTime = (dateString) => {
    try {
      // Backend stores UTC timestamps without 'Z' suffix - add it for proper timezone conversion
      let normalizedDate = dateString;
      if (dateString && !dateString.endsWith('Z') && !dateString.includes('+')) {
        normalizedDate = dateString + 'Z';
      }
      const date = new Date(normalizedDate);
      return date.toLocaleString('en-US', {
        month: 'numeric',
        day: 'numeric',
        year: 'numeric',
        hour: 'numeric',
        minute: '2-digit',
        hour12: true,
      });
    } catch {
      return dateString;
    }
  };

  return (
    <Box>
      {/* Header - matches LettersPage exactly */}
      <Box sx={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', mb: 3 }}>
        <Typography variant="h5" sx={{ fontWeight: 'bold' }}>
          My Disputes
        </Typography>
      </Box>

      {/* Error Alert */}
      {error && (
        <Alert severity="error" sx={{ mb: 3, borderRadius: 2 }} onClose={() => setError(null)}>
          {error}
        </Alert>
      )}

      {/* Loading State */}
      {loading ? (
        <Box sx={{ display: 'flex', justifyContent: 'center', py: 8 }}>
          <CircularProgress />
        </Box>
      ) : disputes.length === 0 ? (
        /* Empty State */
        <Paper sx={{ p: 6, textAlign: 'center', borderRadius: 3 }}>
          <Typography variant="h6" color="text.secondary" sx={{ mb: 2 }}>
            No disputes yet
          </Typography>
          <Typography variant="body2" color="text.secondary" sx={{ mb: 3 }}>
            Disputes are created when you track a letter from the My Letters page
          </Typography>
        </Paper>
      ) : (
        /* Disputes Table - matches LettersPage style exactly */
        <TableContainer
          component={Paper}
          elevation={0}
          sx={{ border: '1px solid', borderColor: 'divider', borderRadius: 3 }}
        >
          <Table sx={{ minWidth: 650 }}>
            <TableHead sx={{ bgcolor: '#f9fafb' }}>
              <TableRow>
                <TableCell sx={{ fontWeight: 'bold', width: 50 }}></TableCell>
                <TableCell sx={{ fontWeight: 'bold', width: 80 }}>ID</TableCell>
                <TableCell sx={{ fontWeight: 'bold' }}>Entity</TableCell>
                <TableCell sx={{ fontWeight: 'bold' }}>Type</TableCell>
                <TableCell align="center" sx={{ fontWeight: 'bold' }}>Violations</TableCell>
                <TableCell sx={{ fontWeight: 'bold' }}>State</TableCell>
                <TableCell align="center" sx={{ fontWeight: 'bold' }}>Deadline</TableCell>
                <TableCell sx={{ fontWeight: 'bold' }}>Status</TableCell>
                <TableCell sx={{ fontWeight: 'bold' }}>Created</TableCell>
                <TableCell align="right" sx={{ fontWeight: 'bold' }}>Actions</TableCell>
              </TableRow>
            </TableHead>
            <TableBody>
              {disputes.map((dispute, index) => (
                <React.Fragment key={dispute.id}>
                  {/* Main Row */}
                  <TableRow
                    hover
                    sx={{
                      cursor: 'pointer',
                      '&:last-child td, &:last-child th': { border: expandedId === dispute.id ? 0 : undefined },
                      bgcolor: expandedId === dispute.id ? '#f0f7ff' : 'inherit',
                    }}
                    onClick={() => handleToggleExpand(dispute.id)}
                  >
                    <TableCell>
                      <IconButton size="small">
                        {expandedId === dispute.id ? <ExpandLessIcon /> : <ExpandMoreIcon />}
                      </IconButton>
                    </TableCell>
                    <TableCell>
                      <Chip
                        label={disputes.length - index}
                        size="small"
                        variant="outlined"
                        sx={{ fontWeight: 600 }}
                      />
                    </TableCell>
                    <TableCell>
                      <Typography variant="body2" sx={{ fontWeight: 500 }}>
                        {dispute.entity_name?.toUpperCase()}
                      </Typography>
                      <Typography variant="caption" color="text.secondary">
                        {dispute.entity_type}
                      </Typography>
                    </TableCell>
                    <TableCell>
                      <Chip label={dispute.entity_type} size="small" color="primary" variant="filled" />
                    </TableCell>
                    <TableCell align="center">
                      <Chip
                        label={dispute.violation_data?.length || 0}
                        size="small"
                        color="error"
                        variant="filled"
                        sx={{ minWidth: 40 }}
                      />
                    </TableCell>
                    <TableCell>{getStateChip(dispute.current_state)}</TableCell>
                    <TableCell align="center">{getDeadlineChip(dispute.days_to_deadline, dispute.tracking_started, dispute.deadline_date)}</TableCell>
                    <TableCell>{getStatusChip(dispute.status)}</TableCell>
                    <TableCell>
                      {formatDateTime(dispute.created_at)}
                    </TableCell>
                    <TableCell align="right" onClick={(e) => e.stopPropagation()}>
                      {!dispute.tracking_started && (
                        <Tooltip title="Start Tracking">
                          <IconButton
                            color="primary"
                            size="small"
                            onClick={() => handleOpenTrackingDialog(dispute)}
                          >
                            <PlayArrowIcon />
                          </IconButton>
                        </Tooltip>
                      )}
                      <IconButton
                        color="error"
                        size="small"
                        onClick={() => handleDelete(dispute.id)}
                        disabled={deletingId === dispute.id}
                        title="Delete Dispute"
                      >
                        {deletingId === dispute.id ? (
                          <CircularProgress size={20} />
                        ) : (
                          <DeleteIcon />
                        )}
                      </IconButton>
                    </TableCell>
                  </TableRow>

                  {/* Expanded Content Row */}
                  <TableRow>
                    <TableCell colSpan={10} sx={{ p: 0, borderBottom: expandedId === dispute.id ? '1px solid' : 0, borderColor: 'divider' }}>
                      <Collapse in={expandedId === dispute.id} timeout="auto" unmountOnExit>
                        <ExpandedRowContent
                          dispute={dispute}
                          onResponseLogged={handleResponseLogged}
                          onStartTracking={handleOpenTrackingDialog}
                          onGenerateLetter={handleOpenLetterDialog}
                          testMode={testMode}
                          onTestModeChange={setTestMode}
                        />
                      </Collapse>
                    </TableCell>
                  </TableRow>
                </React.Fragment>
              ))}
            </TableBody>
          </Table>
        </TableContainer>
      )}

      {/* Start Tracking Dialog */}
      <Dialog
        open={trackingDialogOpen}
        onClose={handleCloseTrackingDialog}
        maxWidth="sm"
        fullWidth
      >
        <DialogTitle sx={{ fontWeight: 600 }}>
          Start Tracking
        </DialogTitle>
        <DialogContent>
          <Typography variant="body2" color="text.secondary" sx={{ mb: 3 }}>
            Enter the date you mailed the dispute letter to start the deadline clock.
          </Typography>

          <LocalizationProvider dateAdapter={AdapterDayjs}>
            <DatePicker
              label="Date Letter Was Mailed *"
              value={trackingSendDate}
              onChange={setTrackingSendDate}
              maxDate={dayjs()}
              slotProps={{
                textField: {
                  fullWidth: true,
                  sx: { mb: 2 },
                },
              }}
            />
          </LocalizationProvider>

          <TextField
            label="Tracking Number (Optional)"
            value={trackingNumber}
            onChange={(e) => setTrackingNumber(e.target.value)}
            fullWidth
            placeholder="e.g., USPS Certified Mail tracking"
            helperText="Enter tracking number if you sent via certified mail"
          />

          {trackingSendDate && (
            <Alert severity="info" sx={{ mt: 2 }}>
              <Typography variant="body2">
                <strong>Deadline:</strong>{' '}
                {trackingSendDate.add(30, 'day').format('MMMM D, YYYY')}
              </Typography>
            </Alert>
          )}
        </DialogContent>
        <DialogActions sx={{ p: 2.5 }}>
          <Button onClick={handleCloseTrackingDialog} disabled={startingTracking}>
            Cancel
          </Button>
          <Button
            variant="contained"
            onClick={handleStartTracking}
            disabled={!trackingSendDate || startingTracking}
            disableElevation
          >
            {startingTracking ? <CircularProgress size={20} /> : 'Start Tracking'}
          </Button>
        </DialogActions>
      </Dialog>

      {/* Response Letter Generation Dialog */}
      <Dialog
        open={letterDialogOpen}
        onClose={handleCloseLetterDialog}
        maxWidth="md"
        fullWidth
      >
        <DialogContent sx={{ p: 0 }}>
          {letterError && (
            <Alert severity="error" sx={{ m: 2, mb: 0 }} onClose={() => setLetterError(null)}>
              {letterError}
            </Alert>
          )}

          {!letterContent ? (
            <Box sx={{ p: 3 }}>
              {/* Pre-generation view */}
              <Typography variant="h6" sx={{ fontWeight: 600, mb: 2 }}>
                Generate Enforcement Letter
              </Typography>

              {/* Show violation info */}
              <Paper variant="outlined" sx={{ p: 2, mb: 3, bgcolor: '#f9fafb' }}>
                <Typography variant="caption" color="text.secondary" sx={{ display: 'block', mb: 0.5 }}>
                  Generating letter for:
                </Typography>
                <Typography variant="subtitle2" sx={{ fontWeight: 600 }}>
                  {letterViolation?.creditor_name || 'Unknown Creditor'}
                  {letterViolation?.account_number_masked && (
                    <Typography component="span" variant="body2" color="text.secondary" sx={{ ml: 1, fontWeight: 400 }}>
                      ({letterViolation.account_number_masked})
                    </Typography>
                  )}
                </Typography>
                <Stack direction="row" spacing={1} sx={{ mt: 1 }}>
                  <Chip
                    label={letterViolation?.violation_type?.replace(/_/g, ' ') || 'Unknown Violation'}
                    size="small"
                    color="error"
                    variant="outlined"
                    sx={{ textTransform: 'capitalize' }}
                  />
                  <Chip
                    label={RESPONSE_TYPES[letterResponseType]?.label || letterResponseType}
                    size="small"
                    color="warning"
                    variant="filled"
                  />
                </Stack>
                <Typography variant="body2" color="text.secondary" sx={{ mt: 1 }}>
                  To: <strong>{letterDispute?.entity_name}</strong> ({letterDispute?.entity_type})
                </Typography>
              </Paper>

              <Alert severity="info">
                <Typography variant="body2">
                  <strong>Letter will include:</strong>
                </Typography>
                <ul style={{ margin: '8px 0', paddingLeft: 20 }}>
                  <li>Statutory violation citations (15 U.S.C. format)</li>
                  <li>Timeline of events establishing breach</li>
                  <li>Demanded remedial actions</li>
                  <li>Willful noncompliance notice (§616)</li>
                </ul>
              </Alert>

              {/* Test Mode Toggle */}
              <Paper
                variant="outlined"
                sx={{
                  p: 2,
                  mt: 2,
                  bgcolor: testMode ? '#fff3e0' : '#f9fafb',
                  borderColor: testMode ? 'warning.main' : 'divider',
                }}
              >
                <FormControlLabel
                  control={
                    <Switch
                      checked={testMode}
                      onChange={(e) => setTestMode(e.target.checked)}
                      color="warning"
                    />
                  }
                  label={
                    <Box>
                      <Typography variant="body2" sx={{ fontWeight: 600 }}>
                        Test Mode
                      </Typography>
                      <Typography variant="caption" color="text.secondary">
                        Bypasses deadline validation for preview. Letter cannot be saved or mailed.
                      </Typography>
                    </Box>
                  }
                />
              </Paper>

              <Box sx={{ display: 'flex', justifyContent: 'flex-end', mt: 3, gap: 1 }}>
                <Button onClick={handleCloseLetterDialog}>
                  Cancel
                </Button>
                <Button
                  variant="contained"
                  onClick={handleGenerateLetter}
                  disabled={letterLoading}
                  disableElevation
                  color={testMode ? 'warning' : 'primary'}
                  startIcon={letterLoading ? <CircularProgress size={16} /> : <DescriptionIcon />}
                >
                  {letterLoading ? 'Generating...' : testMode ? 'Generate Test Letter' : 'Generate Letter'}
                </Button>
              </Box>
            </Box>
          ) : (
            <Box>
              {/* Test Mode Banner */}
              {testMode && (
                <Alert
                  severity="warning"
                  sx={{
                    borderRadius: 0,
                    '& .MuiAlert-message': { width: '100%' },
                  }}
                >
                  <Box sx={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', width: '100%' }}>
                    <Typography variant="body2" sx={{ fontWeight: 600 }}>
                      TEST DOCUMENT – NOT FOR MAILING
                    </Typography>
                    <Chip label="Test Mode" size="small" color="warning" />
                  </Box>
                </Alert>
              )}

              {/* Post-generation view with full toolbar */}
              <Paper
                elevation={0}
                sx={{
                  p: 2,
                  borderBottom: '1px solid',
                  borderColor: 'divider',
                }}
              >
                {/* Header with title and action buttons */}
                <Box sx={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', mb: 2, flexWrap: 'wrap', gap: 1 }}>
                  <Typography variant="h6" sx={{ fontWeight: 600 }}>
                    {testMode ? 'Test Letter Preview' : 'Generated Letter'}
                  </Typography>
                  <Box sx={{ display: 'flex', gap: 1, flexWrap: 'wrap', justifyContent: 'flex-end' }}>
                    <Button
                      size="small"
                      startIcon={<AutorenewIcon />}
                      onClick={() => {
                        setLetterContent('');
                        setEditableContent('');
                        setLastSaved(null);
                      }}
                      variant="outlined"
                    >
                      Regenerate
                    </Button>
                    <Button
                      size="small"
                      startIcon={isEditing ? <VisibilityIcon /> : <EditIcon />}
                      onClick={() => setIsEditing(!isEditing)}
                      variant="outlined"
                    >
                      {isEditing ? 'View' : 'Edit'}
                    </Button>
                    <Button
                      size="small"
                      startIcon={<ContentCopyIcon />}
                      onClick={handleCopyLetter}
                      variant="outlined"
                      color={copiedToClipboard ? 'success' : 'inherit'}
                    >
                      {copiedToClipboard ? 'Copied!' : 'Copy'}
                    </Button>
                    <Button
                      size="small"
                      startIcon={<PrintIcon />}
                      onClick={handlePrintLetter}
                      variant="outlined"
                    >
                      Print
                    </Button>
                    <Button
                      size="small"
                      startIcon={<DownloadIcon />}
                      onClick={handleDownloadPDF}
                      variant="contained"
                    >
                      Download
                    </Button>
                    <Tooltip
                      title={testMode ? 'Test letters cannot be saved. Disable test mode first.' : ''}
                      arrow
                    >
                      <span>
                        <Button
                          size="small"
                          startIcon={isSaving ? <CircularProgress size={16} /> : <SaveIcon />}
                          onClick={handleSaveLetter}
                          variant="contained"
                          color="success"
                          disabled={isSaving || !editableContent || testMode}
                        >
                          {isSaving ? 'Saving...' : 'Save'}
                        </Button>
                      </span>
                    </Tooltip>
                  </Box>
                </Box>

                {/* Stats row */}
                <Box sx={{ display: 'flex', gap: 1, alignItems: 'center', flexWrap: 'wrap' }}>
                  <Chip label={`${letterWordCount} words`} size="small" />
                  {lastSaved && (
                    <Typography variant="caption" color="success.main" sx={{ ml: 'auto' }}>
                      Last saved: {lastSaved.toLocaleTimeString()}
                    </Typography>
                  )}
                </Box>
              </Paper>

              <Divider />

              {/* Letter Content - Edit or View Mode */}
              <Box sx={{ p: 2 }}>
                {isEditing ? (
                  <TextField
                    fullWidth
                    multiline
                    minRows={20}
                    maxRows={30}
                    value={editableContent}
                    onChange={(e) => handleEditableContentChange(e.target.value)}
                    variant="outlined"
                    placeholder="Edit your letter here..."
                    sx={{
                      '& .MuiInputBase-root': {
                        fontFamily: '"Times New Roman", Times, serif',
                        fontSize: '12pt',
                        lineHeight: 1.6,
                        backgroundColor: '#ffffff',
                      },
                    }}
                  />
                ) : (
                  <Box
                    sx={{
                      bgcolor: '#f8fafc',
                      border: '1px solid #e2e8f0',
                      borderRadius: 2,
                      p: 3,
                      maxHeight: 500,
                      overflow: 'auto',
                    }}
                  >
                    <Box
                      sx={{
                        bgcolor: 'white',
                        color: '#111',
                        fontFamily: '"Times New Roman", Times, serif',
                        fontSize: '12pt',
                        lineHeight: 1.8,
                        whiteSpace: 'pre-wrap',
                      }}
                    >
                      {editableContent || letterContent}
                    </Box>
                  </Box>
                )}
              </Box>

              {/* Footer actions */}
              <Box sx={{ display: 'flex', justifyContent: 'flex-end', p: 2, borderTop: '1px solid', borderColor: 'divider' }}>
                <Button onClick={handleCloseLetterDialog}>
                  Close
                </Button>
              </Box>
            </Box>
          )}
        </DialogContent>
      </Dialog>
    </Box>
  );
};

export default DisputesPage;
