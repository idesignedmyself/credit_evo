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
import WarningAmberIcon from '@mui/icons-material/WarningAmber';

const RISK_COLORS = {
  LOW: { bg: '#e8f5e9', color: '#2e7d32', label: 'Low Risk' },
  MEDIUM: { bg: '#fff3e0', color: '#ef6c00', label: 'Medium Risk' },
  HIGH: { bg: '#ffebee', color: '#c62828', label: 'High Risk' },
};

// Severity colors for deletability badges
const SEVERITY_COLORS = {
  LOW: { bg: '#e3f2fd', color: '#1976d2', label: 'low' },
  MEDIUM: { bg: '#fff3e0', color: '#ef6c00', label: 'medium' },
  HIGH: { bg: '#ffebee', color: '#c62828', label: 'high' },
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
              {strategy.label} • {batch.actions?.length || 0} item{batch.actions?.length !== 1 ? 's' : ''} • {batch.recommended_window}
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
      <Collapse in={expanded} timeout={150} unmountOnExit>
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

          {/* Items in this batch - separated by type */}
          {(() => {
            const violations = (batch.actions || []).filter(a => a.source_type !== 'CONTRADICTION');
            const contradictions = (batch.actions || []).filter(a => a.source_type === 'CONTRADICTION');

            return (
              <>
                {/* Violations - will be in letter */}
                {violations.length > 0 && (
                  <>
                    <Typography variant="caption" fontWeight={600} color="text.secondary" sx={{ mb: 1, display: 'block' }}>
                      VIOLATIONS IN LETTER ({violations.length})
                    </Typography>
                    <Box sx={{ display: 'flex', flexDirection: 'column', gap: 1, mb: contradictions.length > 0 ? 2 : 0 }}>
                      {violations.map((action, idx) => {
                        const severity = SEVERITY_COLORS[action.deletability?.toUpperCase()] || SEVERITY_COLORS.MEDIUM;
                        const displayTitle = action.blocker_title || action.action_type?.replace(/_/g, ' ');

                        return (
                          <Box
                            key={action.action_id || idx}
                            sx={{
                              p: 1.5,
                              bgcolor: 'white',
                              borderRadius: 1,
                              border: '1px solid',
                              borderColor: 'success.light',
                            }}
                          >
                            <Box sx={{ display: 'flex', alignItems: 'center', gap: 1, mb: 0.5 }}>
                              <Typography variant="body2" fontWeight={600} sx={{ flex: 1 }}>
                                {displayTitle}
                              </Typography>
                              <Chip
                                label={severity.label}
                                size="small"
                                sx={{
                                  bgcolor: severity.bg,
                                  color: severity.color,
                                  fontWeight: 500,
                                  fontSize: '0.65rem',
                                  height: 20,
                                }}
                              />
                            </Box>
                            <Typography variant="caption" color="text.secondary" sx={{ display: 'block' }}>
                              {action.creditor_name || 'Unknown Account'}
                              {(action.account_number_masked || action.account_id) && (
                                <> ({action.account_number_masked || action.account_id})</>
                              )}
                            </Typography>
                          </Box>
                        );
                      })}
                    </Box>
                  </>
                )}

                {/* Cross-Bureau Contradictions - will be included in letter */}
                {contradictions.length > 0 && (
                  <>
                    <Typography variant="caption" fontWeight={600} color="text.secondary" sx={{ mb: 1, display: 'block' }}>
                      CROSS-BUREAU DISCREPANCIES ({contradictions.length})
                      <Typography component="span" variant="caption" color="success.main" sx={{ ml: 1 }}>
                        (included in letter)
                      </Typography>
                    </Typography>
                    <Box sx={{ display: 'flex', flexDirection: 'column', gap: 1 }}>
                      {contradictions.map((action, idx) => {
                        const severity = SEVERITY_COLORS[action.deletability?.toUpperCase()] || SEVERITY_COLORS.MEDIUM;
                        const displayTitle = action.blocker_title || action.action_type?.replace(/_/g, ' ');
                        const hasValuesByBureau = action.values_by_bureau && Object.keys(action.values_by_bureau).length > 0;

                        return (
                          <Box
                            key={action.action_id || idx}
                            sx={{
                              p: 1.5,
                              bgcolor: '#fff8e1',
                              borderRadius: 1,
                              border: '1px solid',
                              borderColor: 'warning.light',
                            }}
                          >
                            {/* Header row: Title + Severity badge */}
                            <Box sx={{ display: 'flex', alignItems: 'center', gap: 1, mb: 0.5 }}>
                              <Typography variant="body2" fontWeight={600} sx={{ flex: 1 }}>
                                {displayTitle}
                              </Typography>
                              <Chip
                                label={severity.label}
                                size="small"
                                sx={{
                                  bgcolor: severity.bg,
                                  color: severity.color,
                                  fontWeight: 500,
                                  fontSize: '0.65rem',
                                  height: 20,
                                }}
                              />
                            </Box>

                            {/* Account info */}
                            <Typography variant="caption" color="text.secondary" sx={{ display: 'block' }}>
                              {action.creditor_name || 'Unknown Account'}
                              {(action.account_number_masked || action.account_id) && (
                                <> ({action.account_number_masked || action.account_id})</>
                              )}
                            </Typography>

                            {/* Description (if available) */}
                            {action.blocker_description && (
                              <Typography
                                variant="caption"
                                color="text.secondary"
                                sx={{
                                  display: 'block',
                                  mt: 1,
                                  pl: 1,
                                  borderLeft: '2px solid',
                                  borderColor: 'divider',
                                  lineHeight: 1.4,
                                }}
                              >
                                {action.blocker_description}
                              </Typography>
                            )}

                            {/* Values by Bureau section (for cross-bureau discrepancies) */}
                            {hasValuesByBureau && (
                              <Box sx={{ mt: 1.5 }}>
                                <Typography
                                  variant="caption"
                                  color="primary.main"
                                  fontWeight={600}
                                  sx={{ display: 'block', mb: 0.5 }}
                                >
                                  Values by Bureau:
                                </Typography>
                                <Box sx={{ pl: 1 }}>
                                  {Object.entries(action.values_by_bureau).map(([bureau, value]) => (
                                    <Box key={bureau} sx={{ display: 'flex', gap: 1, mb: 0.25 }}>
                                      <Typography
                                        variant="caption"
                                        fontWeight={600}
                                        sx={{ minWidth: 90, textTransform: 'uppercase' }}
                                      >
                                        {bureau}:
                                      </Typography>
                                      <Typography variant="caption" color="text.secondary">
                                        {value || 'Not Reported'}
                                      </Typography>
                                    </Box>
                                  ))}
                                </Box>
                              </Box>
                            )}

                            {/* Type chip */}
                            <Box sx={{ mt: 1 }}>
                              <Chip
                                label="Cross-Bureau Discrepancy"
                                size="small"
                                variant="outlined"
                                sx={{
                                  fontSize: '0.65rem',
                                  height: 20,
                                  borderColor: 'warning.main',
                                  color: 'warning.dark',
                                }}
                              />
                            </Box>
                          </Box>
                        );
                      })}
                    </Box>
                  </>
                )}

                {/* No items fallback */}
                {violations.length === 0 && contradictions.length === 0 && (
                  <Typography variant="caption" color="text.secondary">
                    No items in this batch
                  </Typography>
                )}
              </>
            );
          })()}
        </Box>
      </Collapse>
    </Box>
  );
}
