/**
 * Dispute State Indicator
 *
 * Shows current position in the escalation state machine.
 *
 * AUTHORITY MODEL:
 * - USER-ENTRY states: DISPUTED, RESPONDED, RESOLVED_DELETED, RESOLVED_CURED
 *   (User actions like initiating disputes or logging responses)
 * - SYSTEM-ENTRY states: DETECTED, NO_RESPONSE, EVALUATED, NON_COMPLIANT,
 *   PROCEDURAL_ENFORCEMENT, SUBSTANTIVE_ENFORCEMENT, REGULATORY_ESCALATION, LITIGATION_READY
 *   (System detects conditions and triggers automatic transitions)
 *
 * User can VIEW all state info but cannot manually change state.
 * State transitions are controlled by the state machine based on events.
 */
import React, { useEffect, useState } from 'react';
import {
  Box,
  Paper,
  Typography,
  Chip,
  LinearProgress,
  List,
  ListItem,
  ListItemIcon,
  ListItemText,
  Skeleton,
  Alert,
  Divider,
  Tooltip,
} from '@mui/material';
import {
  CheckCircle as CheckIcon,
  RadioButtonUnchecked as PendingIcon,
  Warning as WarningIcon,
  Error as ErrorIcon,
  Schedule as DeadlineIcon,
  Description as ArtifactIcon,
  ArrowForward as NextIcon,
  Person as UserIcon,
  SmartToy as SystemIcon,
} from '@mui/icons-material';
import { getDisputeState, ESCALATION_STATES } from '../api/disputeApi';

// State machine progression order
const STATE_ORDER = [
  'DETECTED',
  'DISPUTED',
  'RESPONDED',
  'EVALUATED',
  'NON_COMPLIANT',
  'PROCEDURAL_ENFORCEMENT',
  'SUBSTANTIVE_ENFORCEMENT',
  'REGULATORY_ESCALATION',
  'LITIGATION_READY',
];

// States where USER triggers entry
const USER_ENTRY_STATES = ['DISPUTED', 'RESPONDED', 'RESOLVED_DELETED', 'RESOLVED_CURED'];

// States where SYSTEM triggers entry (no user confirmation)
const SYSTEM_ENTRY_STATES = [
  'DETECTED',
  'NO_RESPONSE',
  'EVALUATED',
  'NON_COMPLIANT',
  'PROCEDURAL_ENFORCEMENT',
  'SUBSTANTIVE_ENFORCEMENT',
  'REGULATORY_ESCALATION',
  'LITIGATION_READY',
];

const DisputeStateIndicator = ({ disputeId }) => {
  const [state, setState] = useState(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);

  useEffect(() => {
    const fetchState = async () => {
      try {
        const data = await getDisputeState(disputeId);
        setState(data);
      } catch (err) {
        setError(err.message);
      } finally {
        setLoading(false);
      }
    };

    fetchState();
  }, [disputeId]);

  if (loading) {
    return (
      <Paper sx={{ p: 3 }}>
        <Skeleton variant="text" width="50%" height={32} />
        <Skeleton variant="rectangular" height={8} sx={{ my: 2 }} />
        <Skeleton variant="text" width="80%" />
        <Skeleton variant="text" width="60%" />
      </Paper>
    );
  }

  if (error) {
    return (
      <Alert severity="error">Failed to load state: {error}</Alert>
    );
  }

  if (!state) return null;

  const currentStateConfig = ESCALATION_STATES[state.current_state] || {};
  const currentIndex = STATE_ORDER.indexOf(state.current_state);
  const progress = ((currentIndex + 1) / STATE_ORDER.length) * 100;

  // Determine color based on state
  const getStateColor = () => {
    if (state.current_state.startsWith('RESOLVED')) return 'success';
    if (state.current_state === 'LITIGATION_READY') return 'error';
    if (['NON_COMPLIANT', 'REGULATORY_ESCALATION'].includes(state.current_state)) return 'error';
    if (['PROCEDURAL_ENFORCEMENT', 'SUBSTANTIVE_ENFORCEMENT'].includes(state.current_state)) return 'warning';
    return 'primary';
  };

  const isUserEntryState = USER_ENTRY_STATES.includes(state.current_state);
  const isSystemEntryState = SYSTEM_ENTRY_STATES.includes(state.current_state);

  return (
    <Paper sx={{ p: 3 }}>
      <Box sx={{ display: 'flex', alignItems: 'center', gap: 2, mb: 2 }}>
        <Typography variant="h6">Current State</Typography>
        <Chip
          label={currentStateConfig.label || state.current_state}
          color={getStateColor()}
          size="medium"
        />
        {/* Authority indicator */}
        <Tooltip
          title={
            isUserEntryState
              ? 'This state was entered due to your action (e.g., initiating dispute, logging response)'
              : 'This state was entered automatically by the system (e.g., deadline breach, evaluation)'
          }
          arrow
        >
          <Chip
            icon={isUserEntryState ? <UserIcon fontSize="small" /> : <SystemIcon fontSize="small" />}
            label={isUserEntryState ? 'User Action' : 'System (Auto)'}
            size="small"
            variant="outlined"
            color={isUserEntryState ? 'default' : 'info'}
          />
        </Tooltip>
      </Box>

      {/* Progress Bar */}
      {!state.current_state.startsWith('RESOLVED') && (
        <Box sx={{ mb: 3 }}>
          <LinearProgress
            variant="determinate"
            value={progress}
            color={getStateColor()}
            sx={{ height: 8, borderRadius: 4 }}
          />
          <Typography variant="caption" color="text.secondary" sx={{ mt: 0.5, display: 'block' }}>
            Escalation Progress
          </Typography>
        </Box>
      )}

      {/* State Description */}
      <Typography variant="body2" color="text.secondary" sx={{ mb: 2 }}>
        {state.state_description}
      </Typography>

      <Divider sx={{ my: 2 }} />

      {/* Key Information */}
      <List dense>
        {/* Deadline */}
        {state.deadline_date && (
          <ListItem>
            <ListItemIcon>
              <DeadlineIcon color={state.days_to_deadline < 0 ? 'error' : state.days_to_deadline < 7 ? 'warning' : 'inherit'} />
            </ListItemIcon>
            <ListItemText
              primary={`Deadline: ${state.deadline_date}`}
              secondary={
                state.days_to_deadline < 0
                  ? `${Math.abs(state.days_to_deadline)} days overdue`
                  : `${state.days_to_deadline} days remaining`
              }
            />
          </ListItem>
        )}

        {/* Tone Posture */}
        <ListItem>
          <ListItemIcon>
            {state.tone_posture === 'enforcement' ? <WarningIcon color="warning" /> :
             state.tone_posture === 'regulatory' ? <ErrorIcon color="error" /> :
             state.tone_posture === 'litigation' ? <ErrorIcon color="error" /> :
             <CheckIcon color="info" />}
          </ListItemIcon>
          <ListItemText
            primary="Communication Tone"
            secondary={state.tone_posture?.charAt(0).toUpperCase() + state.tone_posture?.slice(1)}
          />
        </ListItem>

        {/* Terminal State */}
        {state.is_terminal && (
          <ListItem>
            <ListItemIcon>
              <CheckIcon color="success" />
            </ListItemIcon>
            <ListItemText
              primary="Terminal State"
              secondary="This dispute has reached its final state"
            />
          </ListItem>
        )}
      </List>

      {/* Available Outputs */}
      {state.available_outputs?.length > 0 && (
        <>
          <Divider sx={{ my: 2 }} />
          <Typography variant="subtitle2" gutterBottom>
            Available Actions
          </Typography>
          <Box sx={{ display: 'flex', flexWrap: 'wrap', gap: 1 }}>
            {state.available_outputs.map((output) => (
              <Chip
                key={output}
                label={output.replace(/_/g, ' ')}
                size="small"
                icon={<ArtifactIcon />}
                variant="outlined"
              />
            ))}
          </Box>
        </>
      )}

      {/* Next States */}
      {state.next_states?.length > 0 && !state.is_terminal && (
        <>
          <Divider sx={{ my: 2 }} />
          <Typography variant="subtitle2" gutterBottom>
            Possible Next States
          </Typography>
          <Box sx={{ display: 'flex', flexWrap: 'wrap', gap: 1 }}>
            {state.next_states.map((nextState) => {
              const config = ESCALATION_STATES[nextState] || {};
              return (
                <Chip
                  key={nextState}
                  label={config.label || nextState}
                  size="small"
                  icon={<NextIcon />}
                  variant="outlined"
                  color={config.color || 'default'}
                />
              );
            })}
          </Box>
        </>
      )}

      {/* Entity Info */}
      <Divider sx={{ my: 2 }} />
      <Box sx={{ display: 'flex', gap: 2 }}>
        <Typography variant="body2" color="text.secondary">
          <strong>Entity:</strong> {state.entity_name}
        </Typography>
        <Typography variant="body2" color="text.secondary">
          <strong>Type:</strong> {state.entity_type}
        </Typography>
      </Box>
    </Paper>
  );
};

export default DisputeStateIndicator;
