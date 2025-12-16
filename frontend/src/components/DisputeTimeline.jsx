/**
 * Dispute Timeline
 * Displays the immutable paper trail for a dispute
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
} from '@mui/material';
import {
  Person as UserIcon,
  Settings as SystemIcon,
  Business as EntityIcon,
  Description as ArtifactIcon,
  Warning as ViolationIcon,
  CheckCircle as SuccessIcon,
  Error as ErrorIcon,
} from '@mui/icons-material';
import { getDisputeTimeline } from '../api/disputeApi';

const EVENT_ICONS = {
  dispute_created: <UserIcon />,
  mailing_confirmed: <UserIcon />,
  response_logged: <UserIcon />,
  response_evaluated: <SystemIcon />,
  deadline_breach: <ErrorIcon />,
  deadline_recalculated: <SystemIcon />,
  state_transition: <SystemIcon />,
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
  USER: 'You',
  SYSTEM: 'System',
  ENTITY: 'Entity',
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
              <Paper elevation={1} sx={{ p: 2 }}>
                <Box sx={{ display: 'flex', alignItems: 'center', gap: 1, mb: 1 }}>
                  <Chip
                    label={ACTOR_LABELS[event.actor] || event.actor}
                    size="small"
                    color={event.actor === 'SYSTEM' ? 'info' : 'default'}
                    variant="outlined"
                  />
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
