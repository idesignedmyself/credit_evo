/**
 * Dispute List
 * Displays all disputes for the current user
 */
import React, { useEffect, useState } from 'react';
import {
  Box,
  Paper,
  Typography,
  Table,
  TableBody,
  TableCell,
  TableContainer,
  TableHead,
  TableRow,
  Chip,
  IconButton,
  Skeleton,
  Alert,
  Button,
  Tooltip,
} from '@mui/material';
import {
  Visibility as ViewIcon,
  Add as AddIcon,
  Warning as WarningIcon,
  CheckCircle as SuccessIcon,
} from '@mui/icons-material';
import { getDisputes, ESCALATION_STATES } from '../api/disputeApi';

const DisputeList = ({ onSelectDispute, onCreateDispute }) => {
  const [disputes, setDisputes] = useState([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);

  useEffect(() => {
    fetchDisputes();
  }, []);

  const fetchDisputes = async () => {
    try {
      const data = await getDisputes();
      setDisputes(data || []);
      setError(null);
    } catch (err) {
      // Handle gracefully: network errors or 404 = no disputes yet
      // Only show error for unexpected server issues (5xx)
      const status = err.response?.status;
      if (status >= 500) {
        setError('Server error. Please try again later.');
      } else {
        // Network error, 404, or other client errors = treat as empty
        setDisputes([]);
        setError(null);
      }
    } finally {
      setLoading(false);
    }
  };

  const getDeadlineStatus = (daysRemaining) => {
    if (daysRemaining === null) return null;
    if (daysRemaining < 0) return { label: 'Overdue', color: 'error' };
    if (daysRemaining < 7) return { label: `${daysRemaining} days`, color: 'warning' };
    return { label: `${daysRemaining} days`, color: 'default' };
  };

  if (loading) {
    return (
      <Paper sx={{ p: 3 }}>
        <Box sx={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', mb: 2 }}>
          <Typography variant="h6">My Disputes</Typography>
        </Box>
        {[1, 2, 3].map((i) => (
          <Skeleton key={i} variant="rectangular" height={60} sx={{ mb: 1 }} />
        ))}
      </Paper>
    );
  }

  if (error) {
    return (
      <Alert severity="error" action={
        <Button color="inherit" size="small" onClick={fetchDisputes}>
          Retry
        </Button>
      }>
        Failed to load disputes: {error}
      </Alert>
    );
  }

  return (
    <Paper sx={{ p: 3 }}>
      <Box sx={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', mb: 2 }}>
        <Typography variant="h6">My Disputes</Typography>
        {onCreateDispute && (
          <Button
            variant="contained"
            startIcon={<AddIcon />}
            onClick={onCreateDispute}
            size="small"
          >
            New Dispute
          </Button>
        )}
      </Box>

      {disputes.length === 0 ? (
        <Box sx={{ textAlign: 'center', py: 4 }}>
          <Typography color="text.secondary" gutterBottom>
            No disputes yet
          </Typography>
          <Typography variant="body2" color="text.secondary" sx={{ maxWidth: 400, mx: 'auto' }}>
            Disputes are created automatically when you generate and send a dispute letter.
            Upload a credit report, review violations, and generate a letter to get started.
          </Typography>
        </Box>
      ) : (
        <TableContainer>
          <Table size="small">
            <TableHead>
              <TableRow sx={{ bgcolor: '#f9fafb' }}>
                <TableCell>Entity</TableCell>
                <TableCell>State</TableCell>
                <TableCell>Deadline</TableCell>
                <TableCell>Status</TableCell>
                <TableCell align="right">Actions</TableCell>
              </TableRow>
            </TableHead>
            <TableBody>
              {disputes.map((dispute) => {
                const stateConfig = ESCALATION_STATES[dispute.current_state] || {};
                const deadlineStatus = getDeadlineStatus(dispute.days_to_deadline);

                return (
                  <TableRow
                    key={dispute.id}
                    hover
                    sx={{ cursor: 'pointer' }}
                    onClick={() => onSelectDispute?.(dispute.id)}
                  >
                    <TableCell>
                      <Box>
                        <Typography variant="body2" fontWeight={500}>
                          {dispute.entity_name}
                        </Typography>
                        <Typography variant="caption" color="text.secondary">
                          {dispute.entity_type}
                        </Typography>
                      </Box>
                    </TableCell>
                    <TableCell>
                      <Chip
                        label={stateConfig.label || dispute.current_state}
                        size="small"
                        color={stateConfig.color || 'default'}
                        variant="outlined"
                      />
                    </TableCell>
                    <TableCell>
                      {deadlineStatus ? (
                        <Chip
                          label={deadlineStatus.label}
                          size="small"
                          color={deadlineStatus.color}
                          icon={deadlineStatus.color === 'error' ? <WarningIcon /> : undefined}
                        />
                      ) : (
                        <Typography variant="body2" color="text.secondary">
                          N/A
                        </Typography>
                      )}
                    </TableCell>
                    <TableCell>
                      <Chip
                        label={dispute.status}
                        size="small"
                        color={
                          dispute.status === 'CLOSED' ? 'success' :
                          dispute.status === 'BREACHED' ? 'error' :
                          'default'
                        }
                        variant="outlined"
                      />
                    </TableCell>
                    <TableCell align="right">
                      <Tooltip title="View Details">
                        <IconButton
                          size="small"
                          onClick={(e) => {
                            e.stopPropagation();
                            onSelectDispute?.(dispute.id);
                          }}
                        >
                          <ViewIcon fontSize="small" />
                        </IconButton>
                      </Tooltip>
                    </TableCell>
                  </TableRow>
                );
              })}
            </TableBody>
          </Table>
        </TableContainer>
      )}
    </Paper>
  );
};

export default DisputeList;
