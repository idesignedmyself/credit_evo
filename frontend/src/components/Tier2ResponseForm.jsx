/**
 * Tier-2 Response Form
 * Form for marking Tier-2 notice as sent and logging final supervisory responses
 *
 * LIFECYCLE:
 * 1. Tier-2 letter generated (not yet sent)
 * 2. User clicks "Mark Tier-2 Notice Sent" → tier2_notice_sent = true
 * 3. Adjudication UI appears (dropdown + date picker)
 * 4. User logs final response → CURED or Tier-3 promotion
 *
 * Tier-2 is exhausted after exactly ONE response evaluation:
 * - CURED → Close as CURED_AT_TIER_2
 * - Others → Auto-promote to Tier-3 (lock + classify + ledger write)
 *
 * Tier-3 does NOT: Generate letters, Contact regulators, Trigger litigation
 */
import React, { useState } from 'react';
import {
  Box,
  Paper,
  Typography,
  TextField,
  Select,
  MenuItem,
  FormControl,
  InputLabel,
  Button,
  Alert,
  CircularProgress,
  Chip,
  Divider,
} from '@mui/material';
import LockIcon from '@mui/icons-material/Lock';
import CheckCircleIcon from '@mui/icons-material/CheckCircle';
import WarningIcon from '@mui/icons-material/Warning';
import SendIcon from '@mui/icons-material/Send';
import {
  TIER2_RESPONSE_TYPES,
  logTier2Response,
  markTier2NoticeSent,
} from '../api/disputeApi';

// Helper to format date as YYYY-MM-DD
const formatDate = (date) => {
  if (!date) return '';
  const d = new Date(date);
  return d.toISOString().split('T')[0];
};

// Get today's date in YYYY-MM-DD format
const getTodayString = () => formatDate(new Date());

const Tier2ResponseForm = ({
  disputeId,
  tier2NoticeSent = false,
  tier2NoticeSentAt = null,
  onNoticeSent,
  onResponseLogged,
  onCancel,
}) => {
  const [formData, setFormData] = useState({
    response_type: '',
    response_date: getTodayString(),
  });
  const [loading, setLoading] = useState(false);
  const [markingSent, setMarkingSent] = useState(false);
  const [error, setError] = useState(null);
  const [result, setResult] = useState(null);
  const [localNoticeSent, setLocalNoticeSent] = useState(tier2NoticeSent);
  const [localNoticeSentAt, setLocalNoticeSentAt] = useState(tier2NoticeSentAt);

  const handleChange = (field) => (event) => {
    const value = event.target?.value ?? event;
    setFormData((prev) => ({ ...prev, [field]: value }));
  };

  const handleMarkSent = async () => {
    setMarkingSent(true);
    setError(null);

    try {
      const response = await markTier2NoticeSent(disputeId);
      setLocalNoticeSent(true);
      setLocalNoticeSentAt(response.tier2_notice_sent_at);

      if (onNoticeSent) {
        onNoticeSent(response);
      }
    } catch (err) {
      setError(err.response?.data?.detail || err.message || 'Failed to mark Tier-2 notice as sent');
    } finally {
      setMarkingSent(false);
    }
  };

  const handleSubmit = async (e) => {
    e.preventDefault();
    setLoading(true);
    setError(null);

    try {
      const response = await logTier2Response(disputeId, {
        response_type: formData.response_type,
        response_date: formData.response_date,
      });
      setResult(response);

      if (onResponseLogged) {
        onResponseLogged(response);
      }
    } catch (err) {
      setError(err.response?.data?.detail || err.message || 'Failed to log Tier-2 response');
    } finally {
      setLoading(false);
    }
  };

  const selectedType = formData.response_type
    ? TIER2_RESPONSE_TYPES[formData.response_type]
    : null;

  // Show result screen after successful response submission
  if (result) {
    const isCured = result.status === 'CURED_AT_TIER_2';
    return (
      <Paper sx={{ p: 3 }}>
        <Box sx={{ textAlign: 'center' }}>
          {isCured ? (
            <>
              <CheckCircleIcon sx={{ fontSize: 64, color: 'success.main', mb: 2 }} />
              <Typography variant="h6" gutterBottom color="success.main">
                Violation Cured at Tier-2
              </Typography>
              <Typography variant="body2" color="text.secondary" sx={{ mb: 2 }}>
                The entity has corrected the violation. This dispute is now closed.
              </Typography>
              <Chip
                label={`Tier ${result.tier_reached} - Resolved`}
                color="success"
                sx={{ mb: 2 }}
              />
            </>
          ) : (
            <>
              <LockIcon sx={{ fontSize: 64, color: 'error.main', mb: 2 }} />
              <Typography variant="h6" gutterBottom color="error.main">
                Promoted to Tier-3
              </Typography>
              <Typography variant="body2" color="text.secondary" sx={{ mb: 2 }}>
                The violation has been locked and classified. Ledger entry created.
              </Typography>
              <Chip
                label={`Tier ${result.tier_reached} - Locked`}
                color="error"
                icon={<LockIcon />}
                sx={{ mb: 2 }}
              />
              {result.ledger_entry && (
                <Box
                  sx={{
                    mt: 2,
                    p: 2,
                    bgcolor: 'grey.100',
                    borderRadius: 1,
                    textAlign: 'left',
                  }}
                >
                  <Typography variant="subtitle2" gutterBottom>
                    Ledger Entry
                  </Typography>
                  <Typography variant="body2" component="pre" sx={{ fontSize: '0.75rem' }}>
                    {JSON.stringify(result.ledger_entry, null, 2)}
                  </Typography>
                </Box>
              )}
            </>
          )}
          <Button
            variant="contained"
            onClick={() => onCancel?.()}
            sx={{ mt: 2 }}
          >
            Close
          </Button>
        </Box>
      </Paper>
    );
  }

  // If notice not sent, show "Mark as Sent" button
  if (!localNoticeSent) {
    return (
      <Paper sx={{ p: 3 }}>
        <Typography variant="h6" gutterBottom>
          Tier-2 Supervisory Notice
        </Typography>
        <Typography variant="body2" color="text.secondary" sx={{ mb: 2 }}>
          Mark the Tier-2 supervisory notice as sent to begin the cure window.
        </Typography>

        {error && (
          <Alert severity="error" sx={{ mb: 2 }}>
            {error}
          </Alert>
        )}

        <Alert severity="info" variant="outlined" sx={{ mb: 3 }}>
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
          fullWidth
          size="large"
        >
          {markingSent ? 'Marking as Sent...' : 'Mark Tier-2 Supervisory Notice as Sent'}
        </Button>

        {onCancel && (
          <Button variant="outlined" onClick={onCancel} fullWidth sx={{ mt: 2 }}>
            Cancel
          </Button>
        )}
      </Paper>
    );
  }

  // Notice has been sent, show adjudication UI
  return (
    <Paper sx={{ p: 3 }}>
      <Box sx={{ display: 'flex', alignItems: 'center', gap: 1, mb: 2 }}>
        <CheckCircleIcon color="success" />
        <Typography variant="h6">
          Tier-2 Supervisory Response
        </Typography>
      </Box>

      <Alert severity="success" variant="outlined" sx={{ mb: 2 }}>
        <Typography variant="body2">
          Tier-2 notice marked as sent
          {localNoticeSentAt && ` on ${formatDate(localNoticeSentAt)}`}
        </Typography>
      </Alert>

      <Divider sx={{ my: 2 }} />

      <Typography variant="body2" color="text.secondary" sx={{ mb: 1 }}>
        Log the final response to your Tier-2 supervisory notice.
      </Typography>
      <Alert severity="warning" variant="outlined" sx={{ mb: 3 }}>
        <Typography variant="body2">
          <strong>Warning:</strong> Tier-2 is exhausted after ONE response.
          Non-CURED responses auto-promote to Tier-3 (locked record).
        </Typography>
      </Alert>

      {error && (
        <Alert severity="error" sx={{ mb: 2 }}>
          {error}
        </Alert>
      )}

      <form onSubmit={handleSubmit}>
        <Box sx={{ display: 'flex', flexDirection: 'column', gap: 2 }}>
          {/* Response Type */}
          <FormControl fullWidth required>
            <InputLabel>Tier-2 Response</InputLabel>
            <Select
              value={formData.response_type}
              onChange={handleChange('response_type')}
              label="Tier-2 Response"
            >
              {Object.entries(TIER2_RESPONSE_TYPES).map(([key, { value, label, description, outcome }]) => (
                <MenuItem key={key} value={value}>
                  <Box sx={{ display: 'flex', alignItems: 'center', gap: 1, width: '100%' }}>
                    <Box sx={{ flex: 1 }}>
                      <Typography variant="body1">{label}</Typography>
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

          {/* Show outcome preview */}
          {selectedType && (
            <Alert
              severity={selectedType.outcome === 'close' ? 'success' : 'warning'}
              icon={selectedType.outcome === 'close' ? <CheckCircleIcon /> : <WarningIcon />}
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

          {/* Response Date */}
          <TextField
            label="Response Date"
            type="date"
            value={formData.response_date}
            onChange={(e) => handleChange('response_date')(e.target.value)}
            InputLabelProps={{ shrink: true }}
            inputProps={{ max: getTodayString() }}
            fullWidth
            required
          />

          {/* Action Buttons */}
          <Box sx={{ display: 'flex', gap: 2, mt: 2 }}>
            <Button
              type="submit"
              variant="contained"
              color={selectedType?.outcome === 'tier3' ? 'error' : 'primary'}
              disabled={loading || !formData.response_type}
              sx={{ flex: 1 }}
            >
              {loading ? (
                <CircularProgress size={24} />
              ) : selectedType?.outcome === 'tier3' ? (
                'Promote to Tier-3'
              ) : (
                'Log Response'
              )}
            </Button>
            {onCancel && (
              <Button variant="outlined" onClick={onCancel}>
                Cancel
              </Button>
            )}
          </Box>
        </Box>
      </form>
    </Paper>
  );
};

export default Tier2ResponseForm;
