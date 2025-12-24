/**
 * TimelineEvent - Timeline item component for user detail view
 */
import React from 'react';
import { Box, Typography, Chip } from '@mui/material';
import SendIcon from '@mui/icons-material/Send';
import InboxIcon from '@mui/icons-material/Inbox';
import CheckCircleIcon from '@mui/icons-material/CheckCircle';
import BlockIcon from '@mui/icons-material/Block';
import HelpIcon from '@mui/icons-material/Help';

const EVENT_CONFIG = {
  EXECUTION: {
    icon: SendIcon,
    color: '#3b82f6',
    label: 'Execution',
  },
  RESPONSE: {
    icon: InboxIcon,
    color: '#8b5cf6',
    label: 'Response',
  },
  OUTCOME: {
    icon: CheckCircleIcon,
    color: '#10b981',
    label: 'Outcome',
  },
  SUPPRESSION: {
    icon: BlockIcon,
    color: '#f59e0b',
    label: 'Suppression',
  },
  DEFAULT: {
    icon: HelpIcon,
    color: '#6b7280',
    label: 'Event',
  },
};

export default function TimelineEvent({ event, isLast = false }) {
  const config = EVENT_CONFIG[event.event_type] || EVENT_CONFIG.DEFAULT;
  const Icon = config.icon;

  const formatDate = (isoString) => {
    const date = new Date(isoString);
    return date.toLocaleString('en-US', {
      month: 'short',
      day: 'numeric',
      hour: 'numeric',
      minute: '2-digit',
      hour12: true,
    });
  };

  return (
    <Box sx={{ display: 'flex', position: 'relative' }}>
      {/* Timeline line */}
      {!isLast && (
        <Box
          sx={{
            position: 'absolute',
            left: 15,
            top: 32,
            bottom: -16,
            width: 2,
            bgcolor: '#0f3460',
          }}
        />
      )}

      {/* Icon */}
      <Box
        sx={{
          width: 32,
          height: 32,
          borderRadius: '50%',
          bgcolor: `${config.color}20`,
          display: 'flex',
          alignItems: 'center',
          justifyContent: 'center',
          flexShrink: 0,
          mr: 2,
          zIndex: 1,
        }}
      >
        <Icon sx={{ color: config.color, fontSize: 16 }} />
      </Box>

      {/* Content */}
      <Box sx={{ flexGrow: 1, pb: 3 }}>
        <Box sx={{ display: 'flex', alignItems: 'center', gap: 1, mb: 0.5 }}>
          <Chip
            label={config.label}
            size="small"
            sx={{
              bgcolor: `${config.color}20`,
              color: config.color,
              fontSize: '0.65rem',
              height: 20,
            }}
          />
          <Typography variant="caption" sx={{ color: '#6b7280' }}>
            {formatDate(event.timestamp)}
          </Typography>
        </Box>

        <Typography variant="body2" sx={{ color: '#fff', mb: 1 }}>
          {event.description}
        </Typography>

        {/* Metadata chips */}
        {event.metadata && Object.keys(event.metadata).length > 0 && (
          <Box sx={{ display: 'flex', gap: 0.5, flexWrap: 'wrap' }}>
            {Object.entries(event.metadata)
              .filter(([_, v]) => v !== null && v !== undefined)
              .slice(0, 4)
              .map(([key, value]) => (
                <Chip
                  key={key}
                  label={`${key.replace(/_/g, ' ')}: ${value}`}
                  size="small"
                  variant="outlined"
                  sx={{
                    borderColor: '#0f3460',
                    color: '#a2a2a2',
                    fontSize: '0.6rem',
                    height: 18,
                  }}
                />
              ))}
          </Box>
        )}
      </Box>
    </Box>
  );
}
