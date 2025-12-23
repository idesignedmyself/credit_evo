/**
 * CopilotBadge - Per-violation status badge
 *
 * Displays Copilot recommendation status inline with violations:
 * - Recommended (green)
 * - Deferred (yellow)
 * - Advised Against (red)
 *
 * Includes tooltip with human_rationale.
 */
import React from 'react';
import { Chip, Tooltip, Box } from '@mui/material';
import CheckCircleIcon from '@mui/icons-material/CheckCircle';
import AccessTimeIcon from '@mui/icons-material/AccessTime';
import DoNotDisturbIcon from '@mui/icons-material/DoNotDisturb';

import { useCopilotStore } from '../../state';

const BADGE_CONFIG = {
  recommended: {
    label: 'Recommended',
    color: 'success',
    icon: CheckCircleIcon,
    emoji: '',
  },
  deferred: {
    label: 'Deferred',
    color: 'warning',
    icon: AccessTimeIcon,
    emoji: '',
  },
  advised_against: {
    label: 'Advised Against',
    color: 'error',
    icon: DoNotDisturbIcon,
    emoji: '',
  },
};

/**
 * Badge component for violation Copilot status
 * @param {Object} props
 * @param {string} props.violationId - ID of the violation
 * @param {string} [props.size] - Badge size ('small' | 'medium')
 * @param {boolean} [props.showLabel] - Whether to show label text
 */
export default function CopilotBadge({ violationId, size = 'small', showLabel = false }) {
  const getViolationStatus = useCopilotStore((state) => state.getViolationStatus);
  const getHumanRationale = useCopilotStore((state) => state.getHumanRationale);
  const recommendation = useCopilotStore((state) => state.recommendation);

  // No recommendation loaded or no status for this violation
  if (!recommendation) return null;

  const status = getViolationStatus(violationId);
  if (!status) return null;

  const config = BADGE_CONFIG[status];
  if (!config) return null;

  const rationale = getHumanRationale(violationId);
  const Icon = config.icon;

  const badge = (
    <Chip
      size={size}
      icon={<Icon fontSize="inherit" />}
      label={showLabel ? config.label : undefined}
      color={config.color}
      variant="filled"
      sx={{
        height: size === 'small' ? 20 : 24,
        fontSize: size === 'small' ? '0.65rem' : '0.75rem',
        '& .MuiChip-icon': {
          fontSize: size === 'small' ? '0.75rem' : '0.875rem',
          ml: showLabel ? 0.5 : 0,
        },
        '& .MuiChip-label': {
          px: showLabel ? 1 : 0.5,
          display: showLabel ? 'block' : 'none',
        },
        // Icon-only styling
        ...(showLabel
          ? {}
          : {
              minWidth: size === 'small' ? 20 : 24,
              '& .MuiChip-label': { display: 'none' },
            }),
      }}
    />
  );

  // Wrap in tooltip if we have rationale
  if (rationale) {
    return (
      <Tooltip
        title={
          <Box>
            <Box sx={{ fontWeight: 600, mb: 0.5 }}>{config.label}</Box>
            <Box sx={{ fontSize: '0.75rem' }}>{rationale}</Box>
          </Box>
        }
        arrow
        placement="top"
      >
        {badge}
      </Tooltip>
    );
  }

  return badge;
}

/**
 * Inline badge for use in compact spaces (like table cells)
 */
export function CopilotBadgeInline({ violationId }) {
  return <CopilotBadge violationId={violationId} size="small" showLabel={false} />;
}

/**
 * Badge with label for use in expanded views
 */
export function CopilotBadgeLabeled({ violationId }) {
  return <CopilotBadge violationId={violationId} size="small" showLabel={true} />;
}
