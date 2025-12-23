/**
 * RationaleCard - Displays human_rationale for a single item
 *
 * Used for showing Copilot's reasoning for actions or skips.
 */
import React from 'react';
import { Box, Typography, Chip, Paper } from '@mui/material';
import CheckCircleIcon from '@mui/icons-material/CheckCircle';
import DoNotDisturbIcon from '@mui/icons-material/DoNotDisturb';
import AccessTimeIcon from '@mui/icons-material/AccessTime';

/**
 * Card displaying rationale for a Copilot decision
 * @param {Object} props
 * @param {string} props.type - 'action' | 'skip' | 'deferred'
 * @param {string} props.title - Item title (creditor name, etc.)
 * @param {string} props.rationale - Human-readable rationale
 * @param {string} [props.code] - Skip code (for skips only)
 * @param {boolean} [props.compact] - Compact display mode
 */
export default function RationaleCard({
  type,
  title,
  rationale,
  code,
  compact = false,
}) {
  const config = {
    action: {
      color: 'success',
      icon: CheckCircleIcon,
      label: 'Recommended',
      bgcolor: 'success.50',
      borderColor: 'success.200',
    },
    skip: {
      color: 'error',
      icon: DoNotDisturbIcon,
      label: 'Advised Against',
      bgcolor: 'error.50',
      borderColor: 'error.200',
    },
    deferred: {
      color: 'warning',
      icon: AccessTimeIcon,
      label: 'Deferred',
      bgcolor: 'warning.50',
      borderColor: 'warning.200',
    },
  };

  const { color, icon: Icon, label, bgcolor, borderColor } = config[type] || config.action;

  if (compact) {
    return (
      <Box sx={{ display: 'flex', alignItems: 'flex-start', gap: 1, py: 0.5 }}>
        <Icon fontSize="small" color={color} sx={{ mt: 0.25 }} />
        <Box sx={{ flex: 1 }}>
          <Typography variant="body2" fontWeight={500}>
            {title}
          </Typography>
          <Typography variant="caption" color="text.secondary">
            {rationale}
          </Typography>
        </Box>
      </Box>
    );
  }

  return (
    <Paper
      variant="outlined"
      sx={{
        p: 2,
        mb: 1,
        bgcolor,
        borderColor,
        borderRadius: 1,
      }}
    >
      <Box sx={{ display: 'flex', alignItems: 'center', gap: 1, mb: 1 }}>
        <Chip
          size="small"
          icon={<Icon />}
          label={code ? code.replace(/_/g, ' ') : label}
          color={color}
        />
        <Typography variant="body2" fontWeight={600}>
          {title}
        </Typography>
      </Box>
      <Typography variant="body2" color="text.secondary">
        {rationale}
      </Typography>
    </Paper>
  );
}
