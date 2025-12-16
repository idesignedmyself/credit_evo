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
  Timeline,
  TimelineItem,
  TimelineSeparator,
  TimelineConnector,
  TimelineContent,
  TimelineDot,
  TimelineOppositeContent,
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

      <Timeline position="right">
        {timeline.map((event, index) => (
          <TimelineItem key={event.id}>
            <TimelineOppositeContent sx={{ flex: 0.2, minWidth: 100 }}>
              <Typography variant="caption" color="text.secondary">
                {new Date(event.timestamp).toLocaleDateString()}
              </Typography>
              <Typography variant="caption" display="block" color="text.secondary">
                {new Date(event.timestamp).toLocaleTimeString()}
              </Typography>
            </TimelineOppositeContent>

            <TimelineSeparator>
              <TimelineDot color={EVENT_COLORS[event.event_type] || 'grey'}>
                {EVENT_ICONS[event.event_type] || <SystemIcon />}
              </TimelineDot>
              {index < timeline.length - 1 && <TimelineConnector />}
            </TimelineSeparator>

            <TimelineContent>
              <Paper
                elevation={1}
                sx={{
                  p: 2,
                  borderLeft: event.actor === 'SYSTEM' ? '3px solid #1976d2' : '3px solid #757575',
                  bgcolor: event.actor === 'SYSTEM' ? 'rgba(25, 118, 210, 0.04)' : 'inherit',
                }}
              >
                <Box sx={{ display: 'flex', alignItems: 'center', gap: 1, mb: 1 }}>
                  <Tooltip title={ACTOR_TOOLTIPS[event.actor] || ''} arrow>
                    <Chip
                      label={ACTOR_LABELS[event.actor] || event.actor}
                      size="small"
                      color={event.actor === 'SYSTEM' ? 'info' : 'default'}
                      variant={event.actor === 'SYSTEM' ? 'filled' : 'outlined'}
                      icon={event.actor === 'SYSTEM' ? <AutomatedIcon fontSize="small" /> : <UserIcon fontSize="small" />}
                    />
                  </Tooltip>
                  {event.artifact_type && (
                    <Chip
                      label={event.artifact_type}
                      size="small"
                      color="secondary"
                      icon={<ArtifactIcon />}
                    />
                  )}
                </Box>

                <Typography variant="body1">
                  {event.description}
                </Typography>

                {event.evidence_hash && (
                  <Typography variant="caption" color="text.secondary" display="block" sx={{ mt: 1 }}>
                    Evidence Hash: {event.evidence_hash.substring(0, 16)}...
                  </Typography>
                )}

                {event.metadata && Object.keys(event.metadata).length > 0 && (
                  <Box sx={{ mt: 1, p: 1, bgcolor: 'action.hover', borderRadius: 1 }}>
                    <Typography variant="caption" color="text.secondary">
                      {JSON.stringify(event.metadata, null, 2)}
                    </Typography>
                  </Box>
                )}
              </Paper>
            </TimelineContent>
          </TimelineItem>
        ))}
      </Timeline>
    </Paper>
  );
};

export default DisputeTimeline;
