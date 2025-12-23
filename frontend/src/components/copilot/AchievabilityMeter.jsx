/**
 * AchievabilityMeter - Visual indicator for goal achievability
 *
 * Displays ACHIEVABLE / CHALLENGING / UNLIKELY status with
 * color coding and gap summary.
 */
import React from 'react';
import { Box, Typography, LinearProgress, Chip, Tooltip } from '@mui/material';
import CheckCircleIcon from '@mui/icons-material/CheckCircle';
import WarningIcon from '@mui/icons-material/Warning';
import ErrorIcon from '@mui/icons-material/Error';
import VisibilityIcon from '@mui/icons-material/Visibility';

const ACHIEVABILITY_CONFIG = {
  ACHIEVABLE: {
    color: 'success',
    icon: CheckCircleIcon,
    label: 'Achievable',
    progress: 85,
    description: 'Goal is within reach with recommended actions',
  },
  CHALLENGING: {
    color: 'warning',
    icon: WarningIcon,
    label: 'Challenging',
    progress: 50,
    description: 'Goal requires significant effort but is possible',
  },
  UNLIKELY: {
    color: 'error',
    icon: ErrorIcon,
    label: 'Unlikely',
    progress: 20,
    description: 'Major blockers prevent goal achievement',
  },
  PASSIVE: {
    color: 'default',
    icon: VisibilityIcon,
    label: 'Observing',
    progress: 100,
    description: 'No blockers detected',
  },
};

export default function AchievabilityMeter({ level, gapSummary }) {
  // Normalize level to uppercase
  const normalizedLevel = (level || 'PASSIVE').toUpperCase();
  const config = ACHIEVABILITY_CONFIG[normalizedLevel] || ACHIEVABILITY_CONFIG.PASSIVE;
  const Icon = config.icon;

  // Determine progress bar color
  const getProgressColor = () => {
    switch (config.color) {
      case 'success':
        return 'success';
      case 'warning':
        return 'warning';
      case 'error':
        return 'error';
      default:
        return 'primary';
    }
  };

  return (
    <Box>
      {/* Header with chip */}
      <Box sx={{ display: 'flex', alignItems: 'center', mb: 1.5 }}>
        <Tooltip title={config.description}>
          <Chip
            icon={<Icon />}
            label={config.label}
            color={config.color === 'default' ? 'default' : config.color}
            variant={config.color === 'default' ? 'outlined' : 'filled'}
            size="small"
          />
        </Tooltip>
      </Box>

      {/* Progress bar */}
      <Box sx={{ mb: 1.5 }}>
        <LinearProgress
          variant="determinate"
          value={config.progress}
          color={getProgressColor()}
          sx={{
            height: 8,
            borderRadius: 4,
            bgcolor: 'action.hover',
            '& .MuiLinearProgress-bar': {
              borderRadius: 4,
            },
          }}
        />
      </Box>

      {/* Gap summary */}
      {gapSummary && (
        <Typography
          variant="body2"
          color="text.secondary"
          sx={{
            fontSize: '0.8rem',
            lineHeight: 1.4,
          }}
        >
          {gapSummary}
        </Typography>
      )}
    </Box>
  );
}
