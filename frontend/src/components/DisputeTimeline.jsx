/**
 * Dispute Timeline
 *
 * Displays the immutable paper trail for a dispute.
 *
 * AUTHORITY SEPARATION:
 * - USER actions: dispute_created, mailing_confirmed, response_logged, reinsertion_notice_logged
 * - SYSTEM actions: response_evaluated, deadline_breach, state_transition, reinsertion_detected
 *
 * User can VIEW all events but cannot modify the timeline.
 * System actions are automatic and cannot be canceled by user.
 */
import React, { useEffect, useState } from 'react';
import {
  Box,
  Paper,
  Typography,
  Chip,
  Skeleton,
  Alert,
  Tooltip,
} from '@mui/material';
import {
  Person as UserIcon,
  Settings as SystemIcon,
  Business as EntityIcon,
  Description as ArtifactIcon,
  Warning as ViolationIcon,
  CheckCircle as SuccessIcon,
  Error as ErrorIcon,
  SmartToy as AutomatedIcon,
  FiberManualRecord as DotIcon,
} from '@mui/icons-material';
import { getDisputeTimeline } from '../api/disputeApi';

// USER-AUTHORIZED events: User initiated these actions
const USER_EVENTS = [
  'dispute_created',
  'mailing_confirmed',
  'response_logged',
  'reinsertion_notice_logged',
  'artifact_requested',
];

// SYSTEM-AUTHORITATIVE events: System detected/created these automatically
const SYSTEM_EVENTS = [
  'response_evaluated',
  'deadline_breach',
  'deadline_recalculated',
  'state_transition',
  'reinsertion_detected',
  'cross_entity_pattern_detected',
];

const EVENT_ICONS = {
  dispute_created: <UserIcon />,
  mailing_confirmed: <UserIcon />,
  response_logged: <UserIcon />,
  response_evaluated: <AutomatedIcon />,
  deadline_breach: <ErrorIcon />,
  deadline_recalculated: <AutomatedIcon />,
  state_transition: <AutomatedIcon />,
  reinsertion_detected: <ViolationIcon />,
  reinsertion_notice_logged: <UserIcon />,
  cross_entity_pattern_detected: <ViolationIcon />,
  artifact_requested: <ArtifactIcon />,
};

const EVENT_COLORS = {
  dispute_created: 'primary',
  mailing_confirmed: 'primary',
  response_logged: 'primary',
  response_evaluated: 'info',
  deadline_breach: 'error',
  deadline_recalculated: 'warning',
  state_transition: 'info',
  reinsertion_detected: 'error',
  reinsertion_notice_logged: 'warning',
  cross_entity_pattern_detected: 'error',
  artifact_requested: 'secondary',
};

const ACTOR_LABELS = {
  USER: 'Your Action',
  SYSTEM: 'System (Automatic)',
  ENTITY: 'Entity',
};

const ACTOR_TOOLTIPS = {
  USER: 'You initiated this action',
  SYSTEM: 'System detected or created this automatically - no user confirmation required',
  ENTITY: 'Action by the responding entity',
};

const DisputeTimeline = ({ disputeId }) => {
  const [timeline, setTimeline] = useState([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);

  useEffect(() => {
    const fetchTimeline = async () => {
      try {
        const data = await getDisputeTimeline(disputeId);
        setTimeline(data);
      } catch (err) {
        setError(err.message);
      } finally {
        setLoading(false);
      }
    };

    fetchTimeline();
  }, [disputeId]);

  if (loading) {
    return (
      <Paper sx={{ p: 3 }}>
        <Typography variant="h6" gutterBottom>
          Dispute Timeline
        </Typography>
        {[1, 2, 3].map((i) => (
          <Box key={i} sx={{ display: 'flex', gap: 2, mb: 2 }}>
            <Skeleton variant="circular" width={40} height={40} />
            <Box sx={{ flex: 1 }}>
              <Skeleton variant="text" width="60%" />
              <Skeleton variant="text" width="80%" />
            </Box>
          </Box>
        ))}
      </Paper>
    );
  }

  if (error) {
    return (
      <Alert severity="error">Failed to load timeline: {error}</Alert>
    );
  }

  if (timeline.length === 0) {
    return (
      <Paper sx={{ p: 3 }}>
        <Typography variant="h6" gutterBottom>
          Dispute Timeline
        </Typography>
        <Typography color="text.secondary">
          No events recorded yet.
        </Typography>
      </Paper>
    );
  }

  return (
    <Paper sx={{ p: 3 }}>
      <Typography variant="h6" gutterBottom>
        Dispute Timeline
      </Typography>
      <Typography variant="body2" color="text.secondary" sx={{ mb: 2 }}>
        Immutable record of all dispute events. This timeline cannot be modified.
      </Typography>

      <Box sx={{ position: 'relative', pl: 3 }}>
        {/* Vertical line */}
        <Box
          sx={{
            position: 'absolute',
            left: 12,
            top: 0,
            bottom: 0,
            width: 2,
            bgcolor: 'divider',
          }}
        />

        {timeline.map((event, index) => {
          const colorMap = {
            primary: '#1976d2',
            info: '#0288d1',
            error: '#d32f2f',
            warning: '#ed6c02',
            secondary: '#9c27b0',
          };
          const eventColor = colorMap[EVENT_COLORS[event.event_type]] || '#757575';

          return (
            <Box key={event.id} sx={{ position: 'relative', mb: 3 }}>
              {/* Dot on the line */}
              <Box
                sx={{
                  position: 'absolute',
                  left: -24,
                  top: 4,
                  width: 24,
                  height: 24,
                  borderRadius: '50%',
                  bgcolor: eventColor,
                  display: 'flex',
                  alignItems: 'center',
                  justifyContent: 'center',
                  color: 'white',
                  fontSize: 14,
                }}
              >
                {EVENT_ICONS[event.event_type] ? (
                  React.cloneElement(EVENT_ICONS[event.event_type], { sx: { fontSize: 14 } })
                ) : (
                  <DotIcon sx={{ fontSize: 10 }} />
                )}
              </Box>

              {/* Content card */}
              <Paper
                elevation={1}
                sx={{
                  p: 2,
                  ml: 2,
                  borderLeft: event.actor === 'SYSTEM' ? '3px solid #1976d2' : '3px solid #757575',
                  bgcolor: event.actor === 'SYSTEM' ? 'rgba(25, 118, 210, 0.04)' : 'inherit',
                }}
              >
                {/* Time and actor row */}
                <Box sx={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', mb: 1 }}>
                  <Typography variant="caption" color="text.secondary">
                    {new Date(event.timestamp).toLocaleString()}
                  </Typography>
                  <Tooltip title={ACTOR_TOOLTIPS[event.actor] || ''} arrow>
                    <Chip
                      label={ACTOR_LABELS[event.actor] || event.actor}
                      size="small"
                      color={event.actor === 'SYSTEM' ? 'info' : 'default'}
                      variant={event.actor === 'SYSTEM' ? 'filled' : 'outlined'}
                      icon={event.actor === 'SYSTEM' ? <AutomatedIcon fontSize="small" /> : <UserIcon fontSize="small" />}
                    />
                  </Tooltip>
                </Box>

                <Typography variant="body1">
                  {event.description}
                </Typography>

                {event.evidence_hash && (
                  <Typography variant="caption" color="text.secondary" display="block" sx={{ mt: 1 }}>
                    Evidence Hash: {event.evidence_hash.substring(0, 16)}...
                  </Typography>
                )}

                {event.artifact_type && (
                  <Chip
                    label={event.artifact_type}
                    size="small"
                    color="secondary"
                    icon={<ArtifactIcon />}
                    sx={{ mt: 1 }}
                  />
                )}
              </Paper>
            </Box>
          );
        })}
      </Box>
    </Paper>
  );
};

export default DisputeTimeline;
