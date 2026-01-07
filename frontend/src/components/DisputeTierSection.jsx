/**
 * DisputeTierSection - Collapsible section for organizing disputes by tier
 * Used within DisputesPage to group disputes by escalation tier
 */
import React, { useState } from 'react';
import {
  Box,
  Typography,
  Table,
  TableBody,
  TableCell,
  TableContainer,
  TableHead,
  TableRow,
  IconButton,
  Chip,
  Collapse,
  Tooltip,
  CircularProgress,
  Accordion,
  AccordionSummary,
  AccordionDetails,
} from '@mui/material';
import ExpandMoreIcon from '@mui/icons-material/ExpandMore';
import ExpandLessIcon from '@mui/icons-material/ExpandLess';
import DeleteIcon from '@mui/icons-material/Delete';
import PlayArrowIcon from '@mui/icons-material/PlayArrow';
import LockIcon from '@mui/icons-material/Lock';

const TIER_CONFIG = {
  0: {
    title: 'Initial Disputes',
    subtitle: 'First contact disputes - awaiting response',
    color: '#1976d2',
    bgColor: '#e3f2fd',
  },
  1: {
    title: 'Tier-1 Response Disputes',
    subtitle: 'Response received - follow-up or enforcement available',
    color: '#ed6c02',
    bgColor: '#fff3e0',
  },
  2: {
    title: 'Tier-2 Final Disputes',
    subtitle: 'After supervisory notice - final adjudication',
    color: '#d32f2f',
    bgColor: '#ffebee',
  },
};

// State chip styling
const getStateChip = (state) => {
  const stateConfig = {
    DETECTED: { color: 'info', variant: 'outlined' },
    DISPUTED: { color: 'info', variant: 'outlined' },
    RESPONDED: { color: 'primary', variant: 'outlined' },
    NO_RESPONSE: { color: 'warning', variant: 'filled' },
    EVALUATED: { color: 'info', variant: 'outlined' },
    NON_COMPLIANT: { color: 'error', variant: 'outlined' },
    PROCEDURAL_ENFORCEMENT: { color: 'error', variant: 'filled' },
    SUBSTANTIVE_ENFORCEMENT: { color: 'error', variant: 'filled' },
    REGULATORY_ESCALATION: { color: 'error', variant: 'filled' },
    LITIGATION_READY: { color: 'error', variant: 'filled' },
    RESOLVED_DELETED: { color: 'success', variant: 'filled' },
    RESOLVED_CURED: { color: 'success', variant: 'filled' },
  };

  const config = stateConfig[state] || { color: 'default', variant: 'outlined' };
  const label = state?.replace(/_/g, ' ') || 'Unknown';

  return (
    <Chip
      label={label}
      size="small"
      color={config.color}
      variant={config.variant}
      sx={{ textTransform: 'capitalize', fontSize: '0.7rem' }}
    />
  );
};

// Format deadline date for display
const formatDeadlineDate = (dateStr) => {
  if (!dateStr) return null;
  try {
    const date = new Date(dateStr + 'T00:00:00');
    return date.toLocaleDateString('en-US', {
      year: 'numeric',
      month: 'short',
      day: 'numeric',
    });
  } catch {
    return dateStr;
  }
};

const DisputeTierSection = ({
  tier,
  disputes,
  onExpand,
  expandedId,
  onDelete,
  onStartTracking,
  deletingId,
  formatDateTime,
  ExpandedRowContent,
  expandedRowProps,
}) => {
  const [sectionExpanded, setSectionExpanded] = useState(true);

  const config = TIER_CONFIG[tier] || TIER_CONFIG[0];

  // Determine the "active" tier for a dispute (where it currently lives)
  // Delete button only shows when viewing dispute in its active tier
  const getActiveTier = (dispute) => {
    if (dispute.tier2_notice_sent) return 2;
    const hasLoggedResponse =
      dispute.violation_data?.some(v => v.logged_response) ||
      dispute.discrepancies_data?.some(d => d.logged_response);
    if (hasLoggedResponse) return 1;
    return 0;
  };
  const disputeCount = disputes?.length || 0;

  const getDeadlineChip = (days, trackingStarted, deadlineDate) => {
    if (!trackingStarted || deadlineDate === null) {
      return <Chip label="Not tracking" size="small" color="info" variant="outlined" />;
    }
    if (days === null) {
      return <Chip label="Not tracking" size="small" color="info" variant="outlined" />;
    }

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

  return (
    <Accordion
      expanded={sectionExpanded}
      onChange={() => setSectionExpanded(!sectionExpanded)}
      disableGutters
      elevation={0}
      sx={{
        border: '1px solid',
        borderColor: 'divider',
        borderRadius: '12px !important',
        mb: 2,
        '&:before': { display: 'none' },
        overflow: 'hidden',
      }}
    >
      <AccordionSummary
        expandIcon={<ExpandMoreIcon />}
        sx={{
          bgcolor: config.bgColor,
          '&:hover': { bgcolor: config.bgColor },
          minHeight: 56,
        }}
      >
        <Box sx={{ display: 'flex', alignItems: 'center', gap: 2, width: '100%' }}>
          <Box sx={{ flex: 1 }}>
            <Typography variant="subtitle1" sx={{ fontWeight: 600, color: config.color }}>
              {config.title}
            </Typography>
            <Typography variant="caption" color="text.secondary">
              {config.subtitle}
            </Typography>
          </Box>
          <Chip
            label={disputeCount}
            size="small"
            sx={{
              bgcolor: config.color,
              color: 'white',
              fontWeight: 600,
              minWidth: 32,
            }}
          />
        </Box>
      </AccordionSummary>

      <AccordionDetails sx={{ p: 0 }}>
        {disputeCount === 0 ? (
          <Box sx={{ p: 4, textAlign: 'center' }}>
            <Typography variant="body2" color="text.secondary">
              No {config.title.toLowerCase()} yet
            </Typography>
          </Box>
        ) : (
          <TableContainer>
            <Table size="small">
              <TableHead sx={{ bgcolor: '#f9fafb' }}>
                <TableRow>
                  <TableCell sx={{ fontWeight: 'bold', width: 50 }}></TableCell>
                  <TableCell sx={{ fontWeight: 'bold', width: 80 }}>ID</TableCell>
                  <TableCell sx={{ fontWeight: 'bold' }}>Entity</TableCell>
                  <TableCell sx={{ fontWeight: 'bold' }}>Type</TableCell>
                  <TableCell align="center" sx={{ fontWeight: 'bold' }}>Violations</TableCell>
                  <TableCell sx={{ fontWeight: 'bold' }}>State</TableCell>
                  <TableCell align="center" sx={{ fontWeight: 'bold' }}>Deadline</TableCell>
                  <TableCell sx={{ fontWeight: 'bold' }}>Created</TableCell>
                  <TableCell align="right" sx={{ fontWeight: 'bold' }}>Actions</TableCell>
                </TableRow>
              </TableHead>
              <TableBody>
                {disputes.map((dispute, index) => (
                  <React.Fragment key={dispute.id}>
                    <TableRow
                      sx={{
                        cursor: 'pointer',
                        bgcolor: expandedId === dispute.id ? '#f0f7ff' : 'inherit',
                      }}
                      hover
                      onClick={() => onExpand(dispute.id)}
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
                        <Box sx={{ display: 'flex', alignItems: 'center', gap: 1 }}>
                          <Box>
                            <Typography variant="body2" sx={{ fontWeight: 500 }}>
                              {dispute.entity_name?.toUpperCase()}
                            </Typography>
                            <Typography variant="caption" color="text.secondary">
                              {dispute.entity_type}
                            </Typography>
                          </Box>
                          {/* Show "History" badge when viewing in non-active tier */}
                          {tier !== getActiveTier(dispute) && (
                            <Chip
                              label="History"
                              size="small"
                              variant="outlined"
                              sx={{
                                fontSize: '0.65rem',
                                height: 20,
                                color: 'text.secondary',
                                borderColor: 'divider'
                              }}
                            />
                          )}
                        </Box>
                      </TableCell>
                      <TableCell>
                        <Chip
                          label={dispute.entity_type}
                          size="small"
                          color="primary"
                          variant="filled"
                        />
                      </TableCell>
                      <TableCell align="center">
                        <Tooltip title={`${dispute.violation_data?.length || 0} violation(s) disputed`}>
                          <Chip
                            label={dispute.violation_data?.length || 0}
                            size="small"
                            color="error"
                            variant="filled"
                            sx={{ minWidth: 40 }}
                          />
                        </Tooltip>
                      </TableCell>
                      <TableCell>
                        {getStateChip(dispute.current_state)}
                      </TableCell>
                      <TableCell align="center">
                        {getDeadlineChip(
                          dispute.days_to_deadline,
                          dispute.tracking_started,
                          dispute.deadline_date
                        )}
                      </TableCell>
                      <TableCell>
                        {formatDateTime(dispute.created_at)}
                      </TableCell>
                      <TableCell align="right" onClick={(e) => e.stopPropagation()}>
                        {/* Tier-3 locked indicator */}
                        {dispute.tier_reached >= 3 && (
                          <Tooltip title="Dispute locked at Tier-3">
                            <LockIcon sx={{ fontSize: 18, color: 'error.main', mr: 1 }} />
                          </Tooltip>
                        )}
                        {/* Start Tracking button for tier 0 */}
                        {!dispute.tracking_started && onStartTracking && (
                          <Tooltip title="Start Tracking">
                            <IconButton
                              color="primary"
                              size="small"
                              onClick={() => onStartTracking(dispute)}
                            >
                              <PlayArrowIcon />
                            </IconButton>
                          </Tooltip>
                        )}
                        {/* Only show delete in the dispute's active tier (not in history view) */}
                        {tier === getActiveTier(dispute) && (
                          <IconButton
                            color="error"
                            size="small"
                            onClick={() => onDelete(dispute.id)}
                            disabled={deletingId === dispute.id}
                            title="Delete Dispute"
                          >
                            {deletingId === dispute.id ? (
                              <CircularProgress size={20} />
                            ) : (
                              <DeleteIcon />
                            )}
                          </IconButton>
                        )}
                      </TableCell>
                    </TableRow>

                    {/* Expanded Content Row */}
                    <TableRow>
                      <TableCell
                        colSpan={9}
                        sx={{
                          p: 0,
                          borderBottom: expandedId === dispute.id ? '1px solid' : 0,
                          borderColor: 'divider',
                        }}
                      >
                        <Collapse in={expandedId === dispute.id} timeout="auto" unmountOnExit>
                          {ExpandedRowContent && (
                            <ExpandedRowContent
                              dispute={dispute}
                              {...expandedRowProps}
                            />
                          )}
                        </Collapse>
                      </TableCell>
                    </TableRow>
                  </React.Fragment>
                ))}
              </TableBody>
            </Table>
          </TableContainer>
        )}
      </AccordionDetails>
    </Accordion>
  );
};

export default DisputeTierSection;
