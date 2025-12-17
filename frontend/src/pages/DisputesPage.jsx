/**
 * Credit Engine 2.0 - Disputes Page
 * Human-in-the-Loop UI for enforcement automation system
 *
 * AUTHORITY SEPARATION:
 * - User-authorized actions: Report facts (response type, date, evidence)
 * - System-authoritative actions: Deadlines, reinsertion detection, escalation
 *
 * The user is a FACTUAL REPORTER, not a legal decision-maker.
 * The system handles statutes, escalation, and enforcement automatically.
 */
import React, { useState, useEffect } from 'react';
import {
  Box,
  Paper,
  Typography,
  Grid,
  FormControl,
  InputLabel,
  Select,
  MenuItem,
  Button,
  TextField,
  Alert,
  Divider,
  Chip,
  Stack,
  Dialog,
  DialogTitle,
  DialogContent,
  DialogActions,
  CircularProgress,
} from '@mui/material';
import { DatePicker } from '@mui/x-date-pickers/DatePicker';
import { LocalizationProvider } from '@mui/x-date-pickers/LocalizationProvider';
import { AdapterDayjs } from '@mui/x-date-pickers/AdapterDayjs';
import dayjs from 'dayjs';
import InfoIcon from '@mui/icons-material/Info';
import WarningIcon from '@mui/icons-material/Warning';
import GavelIcon from '@mui/icons-material/Gavel';

import DisputeList from '../components/DisputeList';
import DisputeTimeline from '../components/DisputeTimeline';
import DisputeStateIndicator from '../components/DisputeStateIndicator';
import {
  getDisputes,
  getDispute,
  logResponse,
  ENTITY_TYPES,
  RESPONSE_TYPES,
} from '../api/disputeApi';

// =============================================================================
// RESPONSE INPUT PANEL
// Per B6 prompt: Only 3 dropdowns + date + optional evidence
// =============================================================================

const ResponseInputPanel = ({ disputeId, entityType, entityName, onResponseLogged }) => {
  const [responseType, setResponseType] = useState('');
  const [responseDate, setResponseDate] = useState(null);
  const [submitting, setSubmitting] = useState(false);
  const [error, setError] = useState(null);
  const [success, setSuccess] = useState(false);

  const handleSubmit = async () => {
    if (!responseType) {
      setError('Please select a response type');
      return;
    }

    setSubmitting(true);
    setError(null);

    try {
      await logResponse(disputeId, {
        response_type: responseType,
        response_date: responseDate ? responseDate.format('YYYY-MM-DD') : null,
      });
      setSuccess(true);
      setResponseType('');
      setResponseDate(null);
      onResponseLogged?.();
    } catch (err) {
      setError(err.message || 'Failed to log response');
    } finally {
      setSubmitting(false);
    }
  };

  return (
    <Paper sx={{ p: 3, mb: 3 }}>
      <Typography variant="h6" gutterBottom>
        Log Response
      </Typography>
      <Typography variant="body2" color="text.secondary" sx={{ mb: 3 }}>
        Report the response received from {entityName}. The system will evaluate the response
        and determine any resulting violations or escalations automatically.
      </Typography>

      {error && (
        <Alert severity="error" sx={{ mb: 2 }} onClose={() => setError(null)}>
          {error}
        </Alert>
      )}

      {success && (
        <Alert severity="success" sx={{ mb: 2 }} onClose={() => setSuccess(false)}>
          Response logged successfully. System is evaluating...
        </Alert>
      )}

      <Grid container spacing={2} alignItems="flex-end">
        {/* Entity Info (Read-only) */}
        <Grid item xs={12} sm={6} md={3}>
          <TextField
            label="Entity Type"
            value={entityType || ''}
            disabled
            fullWidth
            size="small"
          />
        </Grid>

        <Grid item xs={12} sm={6} md={3}>
          <TextField
            label="Entity Name"
            value={entityName || ''}
            disabled
            fullWidth
            size="small"
          />
        </Grid>

        {/* Response Outcome Dropdown - MANDATORY */}
        <Grid item xs={12} sm={6} md={3}>
          <FormControl fullWidth size="small" required>
            <InputLabel>Response Outcome</InputLabel>
            <Select
              value={responseType}
              label="Response Outcome"
              onChange={(e) => setResponseType(e.target.value)}
            >
              {Object.entries(RESPONSE_TYPES).map(([key, config]) => (
                <MenuItem key={key} value={key}>
                  <Box>
                    <Typography variant="body2">{config.label}</Typography>
                    <Typography variant="caption" color="text.secondary">
                      {config.description}
                    </Typography>
                  </Box>
                </MenuItem>
              ))}
            </Select>
          </FormControl>
        </Grid>

        {/* Response Date (Optional) */}
        <Grid item xs={12} sm={6} md={3}>
          <LocalizationProvider dateAdapter={AdapterDayjs}>
            <DatePicker
              label="Response Date"
              value={responseDate}
              onChange={setResponseDate}
              maxDate={dayjs()}
              slotProps={{
                textField: {
                  size: 'small',
                  fullWidth: true,
                  helperText: 'Optional - date response received',
                },
              }}
            />
          </LocalizationProvider>
        </Grid>
      </Grid>

      <Box sx={{ mt: 3, display: 'flex', justifyContent: 'flex-end' }}>
        <Button
          variant="contained"
          onClick={handleSubmit}
          disabled={submitting || !responseType}
        >
          {submitting ? <CircularProgress size={20} /> : 'Log Response'}
        </Button>
      </Box>

      {/* Authority Notice */}
      <Alert severity="info" sx={{ mt: 3 }} icon={<InfoIcon />}>
        <Typography variant="body2">
          <strong>What happens next:</strong> The system will automatically evaluate this response,
          detect any violations, calculate new deadlines, and escalate if necessary.
          You do not need to select statutes or escalation paths.
        </Typography>
      </Alert>
    </Paper>
  );
};

// =============================================================================
// SYSTEM EVENTS PANEL (Read-only)
// =============================================================================

const SystemEventsPanel = ({ events }) => {
  if (!events || Object.keys(events).length === 0) {
    return null;
  }

  return (
    <Paper sx={{ p: 3, mb: 3, bgcolor: '#FEF3C7', border: '1px solid #F59E0B' }}>
      <Stack direction="row" alignItems="center" spacing={1} sx={{ mb: 2 }}>
        <WarningIcon sx={{ color: '#D97706' }} />
        <Typography variant="h6" sx={{ color: '#92400E' }}>
          System-Detected Events
        </Typography>
      </Stack>
      <Typography variant="body2" color="text.secondary" sx={{ mb: 2 }}>
        These events were detected automatically by the system. They cannot be modified.
      </Typography>

      <Stack spacing={1}>
        {events.pending_deadlines?.map((deadline, i) => (
          <Chip
            key={i}
            label={`Deadline: ${deadline.type} - ${deadline.date}`}
            color="warning"
            variant="outlined"
          />
        ))}
        {events.reinsertion_watches?.map((watch, i) => (
          <Chip
            key={i}
            label={`Reinsertion Watch: ${watch.account}`}
            color="error"
            variant="outlined"
          />
        ))}
        {events.auto_escalations?.map((esc, i) => (
          <Chip
            key={i}
            label={`Auto-Escalation: ${esc.reason}`}
            color="error"
            variant="filled"
          />
        ))}
      </Stack>
    </Paper>
  );
};

// =============================================================================
// AUTHORITY BOUNDARY NOTICE
// =============================================================================

const AuthorityBoundaryNotice = () => (
  <Alert
    severity="info"
    sx={{ mb: 3 }}
    icon={<GavelIcon />}
  >
    <Typography variant="subtitle2" gutterBottom>
      Authority Separation
    </Typography>
    <Typography variant="body2">
      <strong>You control:</strong> Reporting facts (what response was received)
      <br />
      <strong>System controls:</strong> Statute selection, deadline enforcement, reinsertion detection, escalation paths
      <br />
      <em>Escalation occurs automatically when conditions are met - no user confirmation required.</em>
    </Typography>
  </Alert>
);

// =============================================================================
// MAIN DISPUTES PAGE
// =============================================================================

const DisputesPage = () => {
  const [selectedDisputeId, setSelectedDisputeId] = useState(null);
  const [selectedDispute, setSelectedDispute] = useState(null);
  const [systemEvents, setSystemEvents] = useState(null);
  const [loading, setLoading] = useState(false);
  const [refreshKey, setRefreshKey] = useState(0);

  // Fetch dispute details when selected
  useEffect(() => {
    const fetchDisputeDetails = async () => {
      if (!selectedDisputeId) {
        setSelectedDispute(null);
        setSystemEvents(null);
        return;
      }

      setLoading(true);
      try {
        const [dispute, events] = await Promise.all([
          getDispute(selectedDisputeId),
          // getSystemEvents(selectedDisputeId), // Uncomment when endpoint is ready
        ]);
        setSelectedDispute(dispute);
        // setSystemEvents(events);
      } catch (err) {
        console.error('Failed to fetch dispute details:', err);
      } finally {
        setLoading(false);
      }
    };

    fetchDisputeDetails();
  }, [selectedDisputeId, refreshKey]);

  const handleResponseLogged = () => {
    // Refresh the dispute data
    setRefreshKey((k) => k + 1);
  };

  return (
    <Box sx={{ maxWidth: 1400, mx: 'auto' }}>
      <Typography variant="h4" gutterBottom sx={{ fontWeight: 700 }}>
        Dispute Tracking
      </Typography>
      <Typography variant="body1" color="text.secondary" sx={{ mb: 3 }}>
        Track dispute responses and view enforcement status. Report what responses you receive -
        the system handles legal evaluation and escalation automatically.
      </Typography>

      <AuthorityBoundaryNotice />

      <Grid container spacing={3}>
        {/* Left Column - Dispute List */}
        <Grid item xs={12} md={selectedDisputeId ? 5 : 12}>
          <DisputeList
            key={refreshKey}
            onSelectDispute={setSelectedDisputeId}
          />
        </Grid>

        {/* Right Column - Detail View */}
        {selectedDisputeId && (
          <Grid item xs={12} md={7}>
            {loading ? (
              <Paper sx={{ p: 4, textAlign: 'center' }}>
                <CircularProgress />
                <Typography sx={{ mt: 2 }}>Loading dispute details...</Typography>
              </Paper>
            ) : selectedDispute ? (
              <>
                {/* State Indicator */}
                <DisputeStateIndicator
                  disputeId={selectedDisputeId}
                />

                {/* System Events (if any) */}
                <SystemEventsPanel events={systemEvents} />

                {/* Response Input Panel */}
                <ResponseInputPanel
                  disputeId={selectedDisputeId}
                  entityType={selectedDispute.entity_type}
                  entityName={selectedDispute.entity_name}
                  onResponseLogged={handleResponseLogged}
                />

                {/* Timeline */}
                <DisputeTimeline disputeId={selectedDisputeId} key={refreshKey} />
              </>
            ) : (
              <Paper sx={{ p: 4, textAlign: 'center' }}>
                <Typography color="text.secondary">
                  Failed to load dispute details
                </Typography>
              </Paper>
            )}
          </Grid>
        )}
      </Grid>

      {/* Non-Controls Notice */}
      <Paper sx={{ p: 2, mt: 3, bgcolor: '#F1F5F9' }}>
        <Typography variant="caption" color="text.secondary">
          <strong>This UI does NOT allow you to:</strong> Select statutes, select violations,
          select escalation paths, override deadlines, suppress system-detected events,
          or close enforcement states manually. These are controlled by the system based on
          applicable law and detected conditions.
        </Typography>
      </Paper>
    </Box>
  );
};

export default DisputesPage;
