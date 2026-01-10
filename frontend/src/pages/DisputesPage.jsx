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
  Tabs,
  Tab,
} from '@mui/material';
import ExpandMoreIcon from '@mui/icons-material/ExpandMore';
import ExpandLessIcon from '@mui/icons-material/ExpandLess';
import MailOutlineIcon from '@mui/icons-material/MailOutline';
import AccountBalanceIcon from '@mui/icons-material/AccountBalance';
import GavelIcon from '@mui/icons-material/Gavel';
// Note: Table components kept for ExpandedRowContent's internal components
import { DatePicker } from '@mui/x-date-pickers/DatePicker';
import { LocalizationProvider } from '@mui/x-date-pickers/LocalizationProvider';
import { AdapterDayjs } from '@mui/x-date-pickers/AdapterDayjs';
import dayjs from 'dayjs';

import {
  getDisputes,
  getDisputeCounts,
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
import DisputeTierSection from '../components/DisputeTierSection';
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

/**
 * ViolationResponseCard - Simplified card for each violation
 * Only shows violation info and response type dropdown
 * Date picker and save button moved to consolidated section
 */
const ViolationResponseCard = ({
  violation,
  responseType,
  onResponseTypeChange,
  trackingStarted,
  deadlineDate,
  testMode,
  isLocked,
}) => {
  // NO_RESPONSE is only available if:
  // 1. testMode is enabled (bypass deadline check), OR
  // 2. tracking started AND deadline has passed
  const isNoResponseAvailable = () => {
    if (testMode) return true;
    if (!trackingStarted || !deadlineDate) return false;
    const deadline = new Date(deadlineDate);
    const today = new Date();
    today.setHours(0, 0, 0, 0);
    deadline.setHours(0, 0, 0, 0);
    return today > deadline;
  };

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
        borderColor: 'divider',
        mb: 2,
      }}
    >
      {/* Violation Info */}
      <Box sx={{ mb: 2, display: 'flex', justifyContent: 'space-between', alignItems: 'flex-start' }}>
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
      </Box>

      {/* Response Type Dropdown */}
      <FormControl size="small" sx={{ minWidth: 220 }}>
        <InputLabel>Response *</InputLabel>
        <Select
          value={responseType}
          label="Response *"
          onChange={(e) => onResponseTypeChange(violation.violation_id, e.target.value)}
          disabled={isLocked || !!violation.logged_response}
        >
          <MenuItem value="">
            <em>Select outcome...</em>
          </MenuItem>
          {Object.entries(RESPONSE_TYPES).map(([key, config]) => {
            const isNoResponseBlocked = key === 'NO_RESPONSE' && !isNoResponseAvailable();

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

            return (
              <MenuItem key={key} value={key} title={config.description}>
                {config.label}
                {!config.enforcement && ' (resolution)'}
              </MenuItem>
            );
          })}
        </Select>
      </FormControl>

      {/* Response Locked indicator when already logged */}
      {violation.logged_response && (
        <Alert severity="info" sx={{ mt: 1.5, py: 0.5 }} icon={<LockIcon />}>
          <Typography variant="caption">
            Response logged as <strong>{RESPONSE_TYPES[violation.logged_response]?.label || violation.logged_response}</strong>.
            This cannot be changed.
          </Typography>
        </Alert>
      )}

      {/* Strategic framing for response types */}
      {responseType === 'DELETED' && !violation.logged_response && (
        <Typography variant="caption" color="text.secondary" sx={{ display: 'block', mt: 1.5 }}>
          Item deleted - no enforcement letter needed. A 90-day reinsertion watch will be created.
        </Typography>
      )}
      {responseType === 'VERIFIED' && !violation.logged_response && (
        <Alert severity="info" sx={{ mt: 1.5, py: 0.5 }} icon={false}>
          <Typography variant="caption">
            <strong>Strategic note:</strong> "Verified" means the bureau claims the furnisher confirmed the data.
            This does <strong>not</strong> mean the information is accurate. You may demand their Method of Verification
            and challenge the substantive accuracy.
          </Typography>
        </Alert>
      )}
      {responseType === 'NO_RESPONSE' && !violation.logged_response && (
        <Alert severity="warning" sx={{ mt: 1.5, py: 0.5 }} icon={false}>
          <Typography variant="caption">
            <strong>Strategic note:</strong> No response within the statutory deadline is a procedural violation.
            Generate an enforcement letter citing 15 U.S.C. §1681i(a)(1) failure to investigate.
          </Typography>
        </Alert>
      )}
      {responseType === 'REJECTED' && !violation.logged_response && (
        <Alert severity="error" sx={{ mt: 1.5, py: 0.5 }} icon={false}>
          <Typography variant="caption">
            <strong>Strategic note:</strong> "Frivolous/Rejected" disputes trigger specific FCRA rights.
            The bureau must provide their reason in writing. Challenge their determination if unsupported.
          </Typography>
        </Alert>
      )}
      {responseType === 'REINSERTION' && !violation.logged_response && (
        <Alert severity="error" sx={{ mt: 1.5, py: 0.5 }} icon={false}>
          <Typography variant="caption">
            <strong>Strategic note:</strong> Reinsertion without proper notice is a separate FCRA violation.
            Under §1681i(a)(5), they must certify accuracy and provide 5-day written notice.
          </Typography>
        </Alert>
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
                Violation Cured at Tier-1
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
                Promoted to Tier-2
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

  // Show locked state if already at Tier-2 (locked)
  if (isLocked) {
    return (
      <Box sx={{ mb: 3 }}>
        <Divider sx={{ mb: 3 }} />
        <Paper sx={{ p: 3, bgcolor: '#fef2f2', border: '1px solid', borderColor: 'error.light' }}>
          <Box sx={{ display: 'flex', alignItems: 'center', gap: 1 }}>
            <LockIcon color="error" />
            <Typography variant="subtitle2" color="error.main" sx={{ fontWeight: 600 }}>
              Tier-2 — Violation Locked
            </Typography>
          </Box>
          <Typography variant="body2" color="text.secondary" sx={{ mt: 1 }}>
            This violation has been promoted to Tier-2. The record is locked and no further modifications are allowed.
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
        Tier-1 Supervisory Response
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
            After sending your Tier-1 supervisory notice letter, mark it as sent to begin the cure window.
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
            {markingSent ? 'Marking as Sent...' : 'Mark Tier-1 Supervisory Notice as Sent'}
          </Button>
        </Paper>
      ) : (
        /* Notice sent, show adjudication UI */
        <Paper sx={{ p: 3, bgcolor: '#f0fdf4', border: '1px solid', borderColor: 'success.light' }}>
          <Alert severity="success" variant="outlined" sx={{ mb: 2 }}>
            <Typography variant="body2">
              Tier-1 notice marked as sent
              {tier2NoticeSentAt && ` on ${new Date(tier2NoticeSentAt).toLocaleDateString()}`}
            </Typography>
          </Alert>

          <Typography variant="body2" color="text.secondary" sx={{ mb: 2 }}>
            Log the final response to your Tier-1 supervisory notice.
          </Typography>

          <Alert severity="warning" variant="outlined" sx={{ mb: 2 }}>
            <Typography variant="body2">
              <strong>Warning:</strong> Tier-1 is exhausted after ONE response.
              Non-CURED responses auto-promote to Tier-2 (locked record).
            </Typography>
          </Alert>

          <Stack direction={{ xs: 'column', sm: 'row' }} spacing={2} alignItems="flex-start">
            <FormControl size="small" sx={{ minWidth: 280 }}>
              <InputLabel>Tier-1 Response *</InputLabel>
              <Select
                value={tier2ResponseType}
                label="Tier-1 Response *"
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
                        label={outcome === 'close' ? 'Closes' : 'Tier-2'}
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
                'Promote to Tier-2'
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
                  This will close the dispute as <strong>Cured at Tier-1</strong>.
                </Typography>
              ) : (
                <Typography variant="body2">
                  This will <strong>promote to Tier-2</strong>: lock the violation record,
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
  const discrepancies = dispute.discrepancies_data || [];
  const allItems = [
    ...violations,
    ...discrepancies.map(d => ({
      violation_id: d.discrepancy_id,
      violation_type: 'CROSS_BUREAU',
      creditor_name: d.creditor_name,
      account_number_masked: d.account_number_masked,
      description: `${d.field_name} mismatch across bureaus`,
      logged_response: d.logged_response,
      severity: 'MEDIUM',
    })),
  ];

  // Consolidated response state - map of violation_id -> response_type
  const [responseTypes, setResponseTypes] = useState(() => {
    const initial = {};
    allItems.forEach(item => {
      initial[item.violation_id] = item.logged_response || '';
    });
    return initial;
  });
  const [sharedResponseDate, setSharedResponseDate] = useState(null);
  const [submitting, setSubmitting] = useState(false);
  const [success, setSuccess] = useState(false);

  // Inline letter state (replaces dialog)
  const [generatedLetter, setGeneratedLetter] = useState(null);
  const [letterLoading, setLetterLoading] = useState(false);
  const [editableContent, setEditableContent] = useState('');
  const [isEditing, setIsEditing] = useState(false);
  const [isSaving, setIsSaving] = useState(false);
  const [lastSaved, setLastSaved] = useState(null);
  const [copiedToClipboard, setCopiedToClipboard] = useState(false);

  const isLocked = dispute.locked || (dispute.tier_reached || 0) >= 3;

  // Check if any responses are pending (selected but not yet saved)
  const pendingResponses = allItems.filter(
    item => responseTypes[item.violation_id] && !item.logged_response
  );
  const hasPendingResponses = pendingResponses.length > 0;

  // Check if any pending responses require enforcement letter
  const hasEnforcementResponses = pendingResponses.some(
    item => ['NO_RESPONSE', 'VERIFIED', 'REJECTED', 'REINSERTION'].includes(responseTypes[item.violation_id])
  );

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

  // Update response types when dispute data changes
  useEffect(() => {
    const updated = {};
    allItems.forEach(item => {
      updated[item.violation_id] = item.logged_response || responseTypes[item.violation_id] || '';
    });
    setResponseTypes(updated);
  }, [dispute.violation_data, dispute.discrepancies_data]);

  const handleResponseTypeChange = (violationId, newType) => {
    setResponseTypes(prev => ({ ...prev, [violationId]: newType }));
  };

  const handleSaveAndLog = async () => {
    if (!hasPendingResponses) {
      setError('Please select at least one response type');
      return;
    }

    setSubmitting(true);
    setError(null);

    try {
      // Save all pending responses
      const responseDate = sharedResponseDate
        ? sharedResponseDate.format('YYYY-MM-DD')
        : new Date().toISOString().split('T')[0];

      for (const item of pendingResponses) {
        await logResponse(dispute.id, {
          violation_id: item.violation_id,
          response_type: responseTypes[item.violation_id],
          response_date: responseDate,
        });
      }

      setSuccess(true);

      // If enforcement responses, auto-generate letter inline
      if (hasEnforcementResponses) {
        const enforcementItem = pendingResponses.find(
          item => ['NO_RESPONSE', 'VERIFIED', 'REJECTED', 'REINSERTION'].includes(responseTypes[item.violation_id])
        );
        if (enforcementItem) {
          setLetterLoading(true);
          try {
            const result = await generateResponseLetter(dispute.id, {
              response_type: responseTypes[enforcementItem.violation_id],
              violation_id: enforcementItem.violation_id,
              include_willful_notice: true,
              test_context: testMode,
            });
            setGeneratedLetter(result);
            setEditableContent(result.content);
          } catch (letterErr) {
            console.error('Failed to generate letter:', letterErr);
          } finally {
            setLetterLoading(false);
          }
        }
      }

      onResponseLogged?.();
      setTimeout(() => setSuccess(false), 2000);
    } catch (err) {
      console.error('Failed to save responses:', err);
      setError('Failed to save responses');
    } finally {
      setSubmitting(false);
    }
  };

  const handleCopyLetter = async () => {
    try {
      await navigator.clipboard.writeText(editableContent);
      setCopiedToClipboard(true);
      setTimeout(() => setCopiedToClipboard(false), 2000);
    } catch (err) {
      console.error('Failed to copy:', err);
    }
  };

  const handleSaveLetter = async () => {
    if (!editableContent) return;
    setIsSaving(true);
    try {
      await saveResponseLetter(dispute.id, {
        content: editableContent,
        response_type: generatedLetter?.response_type,
        test_context: testMode,
      });
      setLastSaved(new Date());
    } catch (err) {
      console.error('Failed to save letter:', err);
    } finally {
      setIsSaving(false);
    }
  };

  const handleDownloadPDF = () => {
    if (!editableContent) return;
    const pdf = new jsPDF({ unit: 'pt', format: 'letter' });
    const margin = 50;
    const pageWidth = pdf.internal.pageSize.getWidth();
    const pageHeight = pdf.internal.pageSize.getHeight();
    const maxWidth = pageWidth - (margin * 2);
    pdf.setFont('times', 'normal');
    pdf.setFontSize(12);
    const lines = pdf.splitTextToSize(editableContent, maxWidth);
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
    pdf.save(`enforcement_letter_${new Date().toISOString().split('T')[0]}.pdf`);
  };

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

      {/* Tier Progress Indicator */}
      <Box sx={{ mb: 3 }}>
        <Typography variant="caption" color="text.secondary" sx={{ mb: 1, display: 'block' }}>
          Dispute Progress
        </Typography>
        <Box sx={{ display: 'flex', alignItems: 'center', gap: 1, flexWrap: 'wrap' }}>
          {/* Tier 0 - Initial */}
          <Chip
            label="Initial"
            size="small"
            color="primary"
            variant="filled"
            icon={<CheckCircleIcon />}
          />
          <Box sx={{ width: 24, height: 2, bgcolor: (dispute.tier_reached || 0) >= 1 ? 'primary.main' : 'divider' }} />

          {/* Tier 1 - Response */}
          <Chip
            label="Response"
            size="small"
            color={(dispute.tier_reached || 0) >= 1 ? 'primary' : 'default'}
            variant={(dispute.tier_reached || 0) >= 1 ? 'filled' : 'outlined'}
            icon={(dispute.tier_reached || 0) >= 1 ? <CheckCircleIcon /> : undefined}
          />
          <Box sx={{ width: 24, height: 2, bgcolor: (dispute.tier_reached || 0) >= 2 ? 'warning.main' : 'divider' }} />

          {/* Tier 2 - Supervisory */}
          <Chip
            label="Supervisory"
            size="small"
            color={(dispute.tier_reached || 0) >= 2 ? 'warning' : 'default'}
            variant={(dispute.tier_reached || 0) >= 2 ? 'filled' : 'outlined'}
            icon={(dispute.tier_reached || 0) >= 2 ? <CheckCircleIcon /> : undefined}
          />
          <Box sx={{ width: 24, height: 2, bgcolor: (dispute.tier_reached || 0) >= 3 ? 'error.main' : 'divider' }} />

          {/* Tier 3 - Litigation */}
          <Chip
            label="Litigation"
            size="small"
            color={(dispute.tier_reached || 0) >= 3 ? 'error' : 'default'}
            variant={(dispute.tier_reached || 0) >= 3 ? 'filled' : 'outlined'}
            icon={(dispute.tier_reached || 0) >= 3 ? <LockIcon /> : undefined}
          />
        </Box>
      </Box>

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
      </Box>

      {error && (
        <Alert severity="error" sx={{ mb: 2 }} onClose={() => setError(null)}>
          {error}
        </Alert>
      )}

      {allItems.length === 0 ? (
        <Alert severity="info" sx={{ mb: 3 }}>
          No violation data available for this dispute. This may be an older dispute created before tracking was enabled.
        </Alert>
      ) : (
        <Box sx={{ mb: 3 }}>
          {/* Violation Cards */}
          {allItems.map((item, idx) => (
            <ViolationResponseCard
              key={item.violation_id || idx}
              violation={item}
              responseType={responseTypes[item.violation_id] || ''}
              onResponseTypeChange={handleResponseTypeChange}
              trackingStarted={dispute.tracking_started}
              deadlineDate={dispute.deadline_date}
              testMode={testMode}
              isLocked={isLocked}
            />
          ))}

          {/* Consolidated Save Section */}
          {!isLocked && (
            <Paper
              sx={{
                p: 3,
                bgcolor: '#f0f9ff',
                border: '1px solid',
                borderColor: 'primary.light',
                borderRadius: 2,
              }}
            >
              <Stack direction={{ xs: 'column', sm: 'row' }} spacing={2} alignItems="center">
                <LocalizationProvider dateAdapter={AdapterDayjs}>
                  <DatePicker
                    label="Response Date"
                    value={sharedResponseDate}
                    onChange={setSharedResponseDate}
                    maxDate={dayjs()}
                    slotProps={{
                      textField: {
                        size: 'small',
                        sx: { minWidth: 200 },
                        placeholder: 'Select date received',
                      },
                    }}
                  />
                </LocalizationProvider>

                <Button
                  variant="contained"
                  size="large"
                  onClick={handleSaveAndLog}
                  disabled={submitting || !hasPendingResponses}
                  disableElevation
                  startIcon={submitting ? <CircularProgress size={18} color="inherit" /> : <SaveIcon />}
                  sx={{ minWidth: 160, height: 42 }}
                >
                  {submitting ? 'Saving...' : 'Save & Log'}
                </Button>

                {success && (
                  <Chip label="Saved!" size="small" color="success" variant="filled" sx={{ height: 28 }} />
                )}
              </Stack>

              {hasPendingResponses && (
                <Typography variant="caption" color="text.secondary" sx={{ display: 'block', mt: 1.5 }}>
                  {pendingResponses.length} response(s) selected.
                  {hasEnforcementResponses && ' A letter will be generated after saving.'}
                </Typography>
              )}
            </Paper>
          )}

          {/* Inline Generated Letter */}
          {letterLoading && (
            <Paper sx={{ p: 4, mt: 3, textAlign: 'center', borderRadius: 2 }}>
              <CircularProgress size={24} sx={{ mb: 2 }} />
              <Typography variant="body2" color="text.secondary">
                Generating enforcement letter...
              </Typography>
            </Paper>
          )}

          {generatedLetter && !letterLoading && (
            <Paper sx={{ mt: 3, borderRadius: 2, overflow: 'hidden' }}>
              {/* Letter Header */}
              <Box sx={{ p: 2, bgcolor: 'grey.50', borderBottom: '1px solid', borderColor: 'divider' }}>
                <Box sx={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', flexWrap: 'wrap', gap: 1 }}>
                  <Box sx={{ display: 'flex', alignItems: 'center', gap: 1 }}>
                    <DescriptionIcon color="primary" />
                    <Typography variant="subtitle2" sx={{ fontWeight: 600 }}>
                      Generated Letter
                    </Typography>
                    <Chip label={`${editableContent.split(/\s+/).filter(w => w).length} words`} size="small" variant="outlined" />
                  </Box>
                  <Stack direction="row" spacing={1}>
                    <Button size="small" startIcon={isEditing ? <VisibilityIcon /> : <EditIcon />} onClick={() => setIsEditing(!isEditing)} variant="outlined">
                      {isEditing ? 'View' : 'Edit'}
                    </Button>
                    <Button size="small" startIcon={<ContentCopyIcon />} onClick={handleCopyLetter} variant="outlined" color={copiedToClipboard ? 'success' : 'inherit'}>
                      {copiedToClipboard ? 'Copied!' : 'Copy'}
                    </Button>
                    <Button size="small" startIcon={<DownloadIcon />} onClick={handleDownloadPDF} variant="contained" disableElevation>
                      Download
                    </Button>
                    <Button size="small" startIcon={isSaving ? <CircularProgress size={14} /> : <SaveIcon />} onClick={handleSaveLetter} variant="contained" color="success" disabled={isSaving} disableElevation>
                      Save
                    </Button>
                  </Stack>
                </Box>
                {lastSaved && (
                  <Typography variant="caption" color="success.main" sx={{ mt: 1, display: 'block' }}>
                    Last saved: {lastSaved.toLocaleTimeString()}
                  </Typography>
                )}
              </Box>

              {/* Letter Content */}
              <Box sx={{ p: 3, maxHeight: 400, overflow: 'auto' }}>
                {isEditing ? (
                  <TextField
                    fullWidth
                    multiline
                    minRows={15}
                    value={editableContent}
                    onChange={(e) => setEditableContent(e.target.value)}
                    variant="outlined"
                    sx={{ '& .MuiInputBase-root': { fontFamily: '"Times New Roman", serif', fontSize: '11pt', lineHeight: 1.6 } }}
                  />
                ) : (
                  <Box sx={{ fontFamily: '"Times New Roman", serif', fontSize: '11pt', lineHeight: 1.8, whiteSpace: 'pre-wrap', color: '#111' }}>
                    {editableContent}
                  </Box>
                )}
              </Box>
            </Paper>
          )}
        </Box>
      )}

      {/* Activity Timeline - Elegant Design */}
      <Box sx={{ mt: 4 }}>
        <Typography variant="caption" sx={{ fontWeight: 600, color: 'text.secondary', textTransform: 'uppercase', letterSpacing: 0.5 }}>
          Activity
        </Typography>

        {loadingTimeline ? (
          <Box sx={{ py: 2 }}><CircularProgress size={16} /></Box>
        ) : timeline.length === 0 ? (
          <Typography variant="body2" color="text.secondary" sx={{ py: 2 }}>
            No activity yet
          </Typography>
        ) : (
          <Box sx={{ mt: 2, position: 'relative' }}>
            {/* Vertical timeline line */}
            <Box sx={{ position: 'absolute', left: 7, top: 8, bottom: 8, width: 2, bgcolor: 'divider', borderRadius: 1 }} />

            {timeline.slice(0, 10).map((entry, i) => (
              <Box key={entry.id || i} sx={{ display: 'flex', gap: 2, mb: 2, position: 'relative' }}>
                {/* Timeline dot */}
                <Box sx={{
                  width: 16,
                  height: 16,
                  borderRadius: '50%',
                  bgcolor: entry.actor === 'SYSTEM' ? 'warning.main' : 'primary.main',
                  border: '3px solid white',
                  boxShadow: '0 0 0 2px #e5e7eb',
                  flexShrink: 0,
                  zIndex: 1,
                }} />

                {/* Event content */}
                <Box sx={{ flex: 1, pb: 1 }}>
                  <Typography variant="body2" sx={{ color: 'text.primary', lineHeight: 1.4 }}>
                    {entry.description}
                  </Typography>
                  <Typography variant="caption" color="text.secondary">
                    {new Date(entry.timestamp).toLocaleDateString('en-US', { month: 'short', day: 'numeric', hour: 'numeric', minute: '2-digit' })}
                    {' · '}
                    <Box component="span" sx={{ color: entry.actor === 'SYSTEM' ? 'warning.main' : 'primary.main' }}>
                      {entry.actor === 'SYSTEM' ? 'System' : 'You'}
                    </Box>
                  </Typography>
                </Box>
              </Box>
            ))}

            {timeline.length > 10 && (
              <Typography variant="caption" color="text.secondary" sx={{ pl: 4 }}>
                + {timeline.length - 10} more events
              </Typography>
            )}
          </Box>
        )}
      </Box>
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

  // Tab state - matches LettersPage: 0=Mailed, 1=CFPB, 2=Litigation
  const [activeTab, setActiveTab] = useState(0);
  const [counts, setCounts] = useState({
    mailed: { total: 0, tier_0: 0, tier_1: 0, tier_2: 0 },
    cfpb: { total: 0 },
    litigation: { total: 0 },
  });

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

  // Categorize disputes by tier - disputes appear in all COMPLETED stages
  // This preserves history: a Tier-2 dispute also shows in Initial and Tier-1 sections
  const categorizeDisputesByTier = (disputeList) => {
    const tiers = { 0: [], 1: [], 2: [] };

    for (const dispute of disputeList) {
      // Tier 0 (Initial): Every dispute has completed the initial stage
      tiers[0].push(dispute);

      // Tier 1 (Response): Only if they've actually logged a response to their initial dispute
      const hasLoggedResponse =
        dispute.violation_data?.some(v => v.logged_response) ||
        dispute.discrepancies_data?.some(d => d.logged_response);

      if (hasLoggedResponse || dispute.tier2_notice_sent) {
        tiers[1].push(dispute);
      }

      // Tier 2 (Final): Only if tier2_notice_sent is true
      if (dispute.tier2_notice_sent) {
        tiers[2].push(dispute);
      }
    }

    return tiers;
  };

  // Get disputes filtered by current tab and organized by tier
  const getDisputesByTabAndTier = () => {
    // Mailed Disputes tab: ALL CRA disputes (including litigation - for history)
    if (activeTab === 0) {
      const mailedDisputes = disputes.filter(d => d.entity_type === 'CRA');
      return categorizeDisputesByTier(mailedDisputes);
    }
    // CFPB Complaints tab: placeholder for now (CFPB cases are separate)
    else if (activeTab === 1) {
      return { 0: [], 1: [], 2: [] };
    }
    // Litigation Packets tab: Tier-3+ disputes (tier_reached >= 3 in backend)
    else if (activeTab === 2) {
      const litigationDisputes = disputes.filter(d => (d.tier_reached || 0) >= 3);
      // All litigation disputes are shown in a single "Litigation Ready" section
      return { 0: litigationDisputes, 1: [], 2: [] };
    }
    return { 0: [], 1: [], 2: [] };
  };

  const disputesByTier = getDisputesByTabAndTier();

  useEffect(() => {
    const fetchDisputes = async () => {
      setLoading(true);
      try {
        const data = await getDisputes();
        const allDisputes = data || [];
        setDisputes(allDisputes);

        // Calculate counts for tabs
        const mailedDisputes = allDisputes.filter(d => d.entity_type === 'CRA');
        const mailedTiers = categorizeDisputesByTier(mailedDisputes);
        const litigationDisputes = allDisputes.filter(d => (d.tier_reached || 0) >= 3);

        setCounts({
          mailed: {
            total: mailedDisputes.length,
            tier_0: mailedTiers[0].length,
            tier_1: mailedTiers[1].length,
            tier_2: mailedTiers[2].length,
          },
          cfpb: { total: 0 }, // CFPB cases are separate
          litigation: { total: litigationDisputes.length },
        });

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
      // Remove from local state immediately for responsive UI
      const updatedDisputes = disputes.filter((d) => d.id !== disputeId);
      setDisputes(updatedDisputes);

      // Also update counts to keep UI in sync
      const mailedDisputes = updatedDisputes.filter(d => d.entity_type === 'CRA');
      const mailedTiers = categorizeDisputesByTier(mailedDisputes);
      const litigationDisputes = updatedDisputes.filter(d => (d.tier_reached || 0) >= 3);
      setCounts({
        mailed: {
          total: mailedDisputes.length,
          tier_0: mailedTiers[0].length,
          tier_1: mailedTiers[1].length,
          tier_2: mailedTiers[2].length,
        },
        cfpb: { total: 0 },
        litigation: { total: litigationDisputes.length },
      });
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
        <>
          {/* Tab Navigation - matches LettersPage */}
          <Box sx={{ borderBottom: 1, borderColor: 'divider', mb: 3 }}>
            <Tabs
              value={activeTab}
              onChange={(e, v) => setActiveTab(v)}
              sx={{
                minHeight: 48,
                '& .MuiTab-root': {
                  fontWeight: 600,
                  minHeight: 48,
                  textTransform: 'none',
                },
              }}
            >
              <Tab
                value={0}
                icon={<MailOutlineIcon sx={{ fontSize: 18 }} />}
                iconPosition="start"
                label={`Mailed Disputes (${counts.mailed?.total || 0})`}
                sx={{ gap: 0.5 }}
              />
              <Tab
                value={1}
                icon={<AccountBalanceIcon sx={{ fontSize: 18 }} />}
                iconPosition="start"
                label={`CFPB Complaints (${counts.cfpb?.total || 0})`}
                sx={{ gap: 0.5 }}
              />
              <Tab
                value={2}
                icon={<GavelIcon sx={{ fontSize: 18 }} />}
                iconPosition="start"
                label={`Litigation Packets (${counts.litigation?.total || 0})`}
                sx={{ gap: 0.5 }}
              />
            </Tabs>
          </Box>

          {/* Tab Content: Mailed Disputes (CRA) */}
          {activeTab === 0 && (
            <Box>
              <DisputeTierSection
                tier={0}
                disputes={disputesByTier[0]}
                onExpand={handleToggleExpand}
                expandedId={expandedId}
                onDelete={handleDelete}
                onStartTracking={handleOpenTrackingDialog}
                deletingId={deletingId}
                formatDateTime={formatDateTime}
                ExpandedRowContent={ExpandedRowContent}
                expandedRowProps={{
                  onResponseLogged: handleResponseLogged,
                  onStartTracking: handleOpenTrackingDialog,
                  onGenerateLetter: handleOpenLetterDialog,
                  testMode: testMode,
                  onTestModeChange: setTestMode,
                }}
              />
              <DisputeTierSection
                tier={1}
                disputes={disputesByTier[1]}
                onExpand={handleToggleExpand}
                expandedId={expandedId}
                onDelete={handleDelete}
                onStartTracking={handleOpenTrackingDialog}
                deletingId={deletingId}
                formatDateTime={formatDateTime}
                ExpandedRowContent={ExpandedRowContent}
                expandedRowProps={{
                  onResponseLogged: handleResponseLogged,
                  onStartTracking: handleOpenTrackingDialog,
                  onGenerateLetter: handleOpenLetterDialog,
                  testMode: testMode,
                  onTestModeChange: setTestMode,
                }}
              />
              <DisputeTierSection
                tier={2}
                disputes={disputesByTier[2]}
                onExpand={handleToggleExpand}
                expandedId={expandedId}
                onDelete={handleDelete}
                onStartTracking={handleOpenTrackingDialog}
                deletingId={deletingId}
                formatDateTime={formatDateTime}
                ExpandedRowContent={ExpandedRowContent}
                expandedRowProps={{
                  onResponseLogged: handleResponseLogged,
                  onStartTracking: handleOpenTrackingDialog,
                  onGenerateLetter: handleOpenLetterDialog,
                  testMode: testMode,
                  onTestModeChange: setTestMode,
                }}
              />
            </Box>
          )}

          {/* Tab Content: CFPB Complaints */}
          {activeTab === 1 && (
            <Paper sx={{ p: 6, textAlign: 'center', borderRadius: 3, bgcolor: '#fafafa' }}>
              <AccountBalanceIcon sx={{ fontSize: 48, color: 'text.secondary', mb: 2 }} />
              <Typography variant="h6" color="text.secondary" sx={{ mb: 1 }}>
                CFPB Complaints
              </Typography>
              <Typography variant="body2" color="text.secondary">
                CFPB complaint tracking coming soon. File complaints via the CFPB portal.
              </Typography>
            </Paper>
          )}

          {/* Tab Content: Litigation Packets */}
          {activeTab === 2 && (
            counts.litigation?.total > 0 ? (
              <Box>
                <DisputeTierSection
                  tier={0}
                  disputes={disputesByTier[0]}
                  onExpand={handleToggleExpand}
                  expandedId={expandedId}
                  onDelete={handleDelete}
                  deletingId={deletingId}
                  formatDateTime={formatDateTime}
                  ExpandedRowContent={ExpandedRowContent}
                  expandedRowProps={{
                    onResponseLogged: handleResponseLogged,
                    onStartTracking: handleOpenTrackingDialog,
                    onGenerateLetter: handleOpenLetterDialog,
                    testMode: testMode,
                    onTestModeChange: setTestMode,
                  }}
                />
              </Box>
            ) : (
              <Paper sx={{ p: 6, textAlign: 'center', borderRadius: 3, bgcolor: '#fafafa' }}>
                <GavelIcon sx={{ fontSize: 48, color: 'text.secondary', mb: 2 }} />
                <Typography variant="h6" color="text.secondary" sx={{ mb: 1 }}>
                  Litigation Packets
                </Typography>
                <Typography variant="body2" color="text.secondary">
                  No disputes have reached litigation stage yet. Disputes promoted to Tier-2 (locked) will appear here.
                </Typography>
              </Paper>
            )
          )}
        </>
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

              <Box sx={{ display: 'flex', justifyContent: 'flex-end', mt: 3, gap: 1 }}>
                <Button onClick={handleCloseLetterDialog}>
                  Cancel
                </Button>
                <Button
                  variant="contained"
                  onClick={handleGenerateLetter}
                  disabled={letterLoading}
                  disableElevation
                  color="primary"
                  startIcon={letterLoading ? <CircularProgress size={16} /> : <DescriptionIcon />}
                >
                  {letterLoading ? 'Generating...' : 'Generate Letter'}
                </Button>
              </Box>
            </Box>
          ) : (
            <Box>
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
                    Generated Letter
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
                    <Button
                      size="small"
                      startIcon={isSaving ? <CircularProgress size={16} /> : <SaveIcon />}
                      onClick={handleSaveLetter}
                      variant="contained"
                      color="success"
                      disabled={isSaving || !editableContent}
                    >
                      {isSaving ? 'Saving...' : 'Save'}
                    </Button>
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
