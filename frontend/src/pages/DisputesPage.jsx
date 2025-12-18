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
  RESPONSE_TYPES,
  ESCALATION_STATES,
} from '../api/disputeApi';
import DeleteIcon from '@mui/icons-material/Delete';

// =============================================================================
// EXPANDABLE ROW CONTENT
// =============================================================================

// =============================================================================
// SINGLE VIOLATION RESPONSE ROW
// =============================================================================

const ViolationResponseRow = ({ violation, disputeId, onResponseLogged }) => {
  const [responseType, setResponseType] = useState(violation.logged_response || '');
  const [responseDate, setResponseDate] = useState(null);
  const [submitting, setSubmitting] = useState(false);
  const [success, setSuccess] = useState(false);
  const [error, setError] = useState(null);

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

  const getResponseColor = (type) => {
    switch (type) {
      case 'DELETED': return 'success';
      case 'VERIFIED': return 'warning';
      case 'UPDATED': return 'info';
      case 'NO_RESPONSE': return 'error';
      case 'REJECTED': return 'error';
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
      <Box sx={{ mb: 2.5 }}>
        <Typography variant="subtitle2" sx={{ fontWeight: 600, mb: 0.5 }}>
          {violation.creditor_name || 'Unknown Creditor'}
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
        </Stack>
      </Box>

      {error && (
        <Alert severity="error" sx={{ mb: 2, py: 0.5 }} onClose={() => setError(null)}>
          {error}
        </Alert>
      )}

      {/* Response Form */}
      <Stack direction={{ xs: 'column', sm: 'row' }} spacing={2} alignItems="flex-start">
        <FormControl size="small" sx={{ minWidth: 180 }}>
          <InputLabel>Response *</InputLabel>
          <Select
            value={responseType}
            label="Response *"
            onChange={(e) => setResponseType(e.target.value)}
            disabled={submitting}
          >
            <MenuItem value="">
              <em>Select...</em>
            </MenuItem>
            {Object.entries(RESPONSE_TYPES).map(([key, config]) => (
              <MenuItem key={key} value={key}>
                {config.label}
              </MenuItem>
            ))}
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
    </Box>
  );
};

const ExpandedRowContent = ({ dispute, onResponseLogged }) => {
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
      {/* Dispute Details */}
      <Box sx={{ display: 'flex', gap: 4, mb: 3, flexWrap: 'wrap' }}>
        <Box>
          <Typography variant="caption" color="text.secondary">Deadline</Typography>
          <Typography variant="body2" sx={{ fontWeight: 500 }}>
            {dispute.deadline_date}
          </Typography>
        </Box>
        <Box>
          <Typography variant="caption" color="text.secondary">Days Remaining</Typography>
          <Typography variant="body2" sx={{ fontWeight: 500 }}>
            {dispute.days_to_deadline} days
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
      <Typography variant="subtitle2" sx={{ fontWeight: 600, mb: 1 }}>
        Log Response from {dispute.entity_name}
      </Typography>
      <Typography variant="caption" color="text.secondary" sx={{ display: 'block', mb: 2 }}>
        Select how the bureau responded to each violation in your dispute letter
      </Typography>

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
              onResponseLogged={onResponseLogged}
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

  const getDeadlineChip = (days) => {
    if (days === null) return <Chip label="N/A" size="small" variant="outlined" />;

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
        label={`${days} days`}
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
                <TableCell sx={{ fontWeight: 'bold', width: 80 }}>#</TableCell>
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
                        label={`#${disputes.length - index}`}
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
                    <TableCell align="center">{getDeadlineChip(dispute.days_to_deadline)}</TableCell>
                    <TableCell>{getStatusChip(dispute.status)}</TableCell>
                    <TableCell>
                      {formatDateTime(dispute.created_at)}
                    </TableCell>
                    <TableCell align="right" onClick={(e) => e.stopPropagation()}>
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
    </Box>
  );
};

export default DisputesPage;
