/**
 * Credit Engine 2.0 - Batch Accordion Component
 * Displays a single dispute wave/batch with violations
 */
import React, { useState } from 'react';
import {
  Box,
  Typography,
  IconButton,
  Collapse,
  Chip,
  Button,
  Tooltip,
  Divider,
} from '@mui/material';
import ExpandMoreIcon from '@mui/icons-material/ExpandMore';
import ChevronRightIcon from '@mui/icons-material/ChevronRight';
import LockIcon from '@mui/icons-material/Lock';
import CheckCircleIcon from '@mui/icons-material/CheckCircle';
import ScheduleIcon from '@mui/icons-material/Schedule';
import WarningAmberIcon from '@mui/icons-material/WarningAmber';

const RISK_COLORS = {
  LOW: { bg: '#e8f5e9', color: '#2e7d32', label: 'Low Risk' },
  MEDIUM: { bg: '#fff3e0', color: '#ef6c00', label: 'Medium Risk' },
  HIGH: { bg: '#ffebee', color: '#c62828', label: 'High Risk' },
};

const STRATEGY_ICONS = {
  DELETE_DEMAND: { emoji: '', label: 'Deletion' },
  CORRECT_DEMAND: { emoji: '', label: 'Correction' },
  MOV_DEMAND: { emoji: '', label: 'Verification' },
  OWNERSHIP_CHAIN_DEMAND: { emoji: '', label: 'Ownership' },
  DOFD_DEMAND: { emoji: '', label: 'DOFD' },
  PROCEDURAL_DEMAND: { emoji: '', label: 'Procedural' },
  DEFER: { emoji: '', label: 'Deferred' },
};

export default function BatchAccordion({
  batch,
  isSelected,
  isDimmed,
  onSelect,
  onOverride,
  violations = [],
  renderViolation,
}) {
  const [expanded, setExpanded] = useState(false);

  const handleToggle = (e) => {
    e.stopPropagation();
    setExpanded(prev => !prev);
  };

  const risk = RISK_COLORS[batch.risk_level] || RISK_COLORS.LOW;
  const strategy = STRATEGY_ICONS[batch.strategy] || { label: batch.strategy };

  const handleSelect = () => {
    if (batch.is_locked) {
      // Show override modal
      onOverride?.(batch, 'proceed_locked');
    } else {
      onSelect?.(batch);
    }
  };

  // Get matching violations for this batch
  const batchViolations = violations.filter(v =>
    batch.violation_ids?.includes(v.violation_id)
  );

  return (
    <Box
      sx={{
        borderBottom: '1px solid',
        borderColor: 'divider',
        bgcolor: isSelected ? 'rgba(25, 118, 210, 0.04)' : 'background.paper',
        opacity: isDimmed ? 0.5 : 1,
        transition: 'all 0.15s ease',
        '&:last-child': { borderBottom: 'none' },
      }}
    >
      {/* Batch Header */}
      <Box
        sx={{
          display: 'flex',
          alignItems: 'center',
          justifyContent: 'space-between',
          py: 1.5,
          px: 2,
          cursor: 'pointer',
          '&:hover': { bgcolor: 'rgba(0,0,0,0.02)' },
        }}
        onClick={handleToggle}
      >
        <Box sx={{ display: 'flex', alignItems: 'center', gap: 1.5, flex: 1 }}>
          <IconButton size="small" sx={{ p: 0 }}>
            {expanded ? (
              <ExpandMoreIcon fontSize="small" />
            ) : (
              <ChevronRightIcon fontSize="small" />
            )}
          </IconButton>

          <Box sx={{ flex: 1 }}>
            <Typography variant="body2" fontWeight={600}>
              Wave {batch.batch_number}: {batch.furnisher_name || 'Unknown'}
              {batch.is_single_item && (
                <Typography component="span" variant="caption" sx={{ ml: 1, color: 'text.secondary', fontStyle: 'italic' }}>
                  (Isolated step)
                </Typography>
              )}
            </Typography>
            <Typography variant="caption" color="text.secondary">
              {strategy.label} • {batch.violation_ids?.length || 0} violation{batch.violation_ids?.length !== 1 ? 's' : ''} • {batch.recommended_window}
            </Typography>
          </Box>
        </Box>

        {/* Status chips */}
        <Box sx={{ display: 'flex', alignItems: 'center', gap: 1 }}>
          {/* Risk chip - outlined style */}
          <Chip
            label={risk.label}
            size="small"
            variant="outlined"
            sx={{
              borderColor: risk.color,
              color: risk.color,
              fontWeight: 500,
              fontSize: '0.7rem',
            }}
          />

          {/* Lock status - outlined style */}
          {batch.is_locked ? (
            <Tooltip title={batch.lock_reason === 'pending_previous_wave'
              ? 'Waiting for previous wave response'
              : 'Pending disputes in progress'
            }>
              <Chip
                label="Locked"
                size="small"
                variant="outlined"
                sx={{
                  borderColor: 'warning.main',
                  color: 'warning.main',
                  fontWeight: 500,
                  fontSize: '0.7rem',
                }}
              />
            </Tooltip>
          ) : (
            <Chip
              label="Ready"
              size="small"
              variant="outlined"
              sx={{
                borderColor: 'success.main',
                color: 'success.main',
                fontWeight: 500,
                fontSize: '0.7rem',
              }}
            />
          )}

          {/* Select button */}
          <Button
            variant={isSelected ? 'contained' : 'outlined'}
            size="small"
            onClick={(e) => {
              e.stopPropagation();
              handleSelect();
            }}
            sx={{
              textTransform: 'none',
              fontWeight: 600,
              minWidth: 72,
              fontSize: '0.75rem',
            }}
          >
            {isSelected ? 'Selected' : batch.is_locked ? 'Override' : 'Select'}
          </Button>
        </Box>
      </Box>

      {/* Expanded content */}
      <Collapse in={expanded}>
        <Divider />
        <Box sx={{ p: 2, bgcolor: '#fafafa' }}>
          {/* Strategy info */}
          <Box sx={{ mb: 2 }}>
            <Typography variant="caption" fontWeight={600} color="text.secondary">
              STRATEGY
            </Typography>
            <Typography variant="body2">
              {batch.goal_summary}
            </Typography>
          </Box>

          {/* Lock info if locked */}
          {batch.is_locked && (
            <Box sx={{ mb: 2, p: 1.5, bgcolor: '#fff3e0', borderRadius: 1 }}>
              <Box sx={{ display: 'flex', alignItems: 'center', gap: 1, mb: 1 }}>
                <WarningAmberIcon fontSize="small" color="warning" />
                <Typography variant="caption" fontWeight={600} color="warning.dark">
                  UNLOCK CONDITIONS
                </Typography>
              </Box>
              <Box component="ul" sx={{ m: 0, pl: 2.5 }}>
                {(batch.unlock_conditions || []).map((condition, idx) => (
                  <Typography component="li" variant="caption" key={idx}>
                    {condition}
                  </Typography>
                ))}
              </Box>
            </Box>
          )}

          {/* Violations in this batch */}
          <Typography variant="caption" fontWeight={600} color="text.secondary" sx={{ mb: 1, display: 'block' }}>
            VIOLATIONS IN THIS BATCH
          </Typography>
          <Box sx={{ display: 'flex', flexDirection: 'column', gap: 1 }}>
            {batchViolations.length > 0 ? (
              batchViolations.map((violation) => (
                <Box
                  key={violation.violation_id}
                  sx={{
                    p: 1.5,
                    bgcolor: 'white',
                    borderRadius: 1,
                    border: '1px solid',
                    borderColor: 'divider',
                  }}
                >
                  {renderViolation ? (
                    renderViolation(violation)
                  ) : (
                    <Box sx={{ display: 'flex', flexDirection: 'column', gap: 0.25 }}>
                      <Typography variant="body2" fontWeight={600}>
                        {violation.creditor_name || 'Unknown Account'}
                      </Typography>
                      {(violation.account_number_masked || violation.account_id) && (
                        <Typography variant="caption" color="text.secondary" sx={{ display: 'block' }}>
                          Account#: {violation.account_number_masked || violation.account_id}
                        </Typography>
                      )}
                      <Typography variant="caption" color="text.secondary" sx={{ display: 'block' }}>
                        {violation.violation_type} • {violation.bureau}
                      </Typography>
                    </Box>
                  )}
                </Box>
              ))
            ) : (
              <Typography variant="caption" color="text.secondary">
                No violations loaded for this batch
              </Typography>
            )}
          </Box>

          {/* Actions preview */}
          {batch.actions?.length > 0 && (
            <Box sx={{ mt: 2 }}>
              <Typography variant="caption" fontWeight={600} color="text.secondary" sx={{ mb: 1, display: 'block' }}>
                PLANNED ACTIONS
              </Typography>
              {batch.actions.map((action, idx) => (
                <Box key={action.action_id || idx} sx={{ display: 'flex', alignItems: 'center', gap: 1, mb: 0.5 }}>
                  <ScheduleIcon sx={{ fontSize: 14, color: 'text.secondary' }} />
                  <Typography variant="caption">
                    {action.action_type}: {action.rationale}
                  </Typography>
                </Box>
              ))}
            </Box>
          )}
        </Box>
      </Collapse>
    </Box>
  );
}
