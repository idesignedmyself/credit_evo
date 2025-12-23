/**
 * LetterTrace - "Why this letter?" trace component
 *
 * Shows Copilot's reasoning for letter generation:
 * - Actions taken (with human_rationale)
 * - Items skipped (with human_rationale)
 * - Overall strategy explanation
 */
import React from 'react';
import {
  Paper,
  Box,
  Typography,
  Accordion,
  AccordionSummary,
  AccordionDetails,
  Chip,
  Divider,
  List,
  ListItem,
  ListItemIcon,
  ListItemText,
} from '@mui/material';
import ExpandMoreIcon from '@mui/icons-material/ExpandMore';
import SmartToyIcon from '@mui/icons-material/SmartToy';
import CheckCircleIcon from '@mui/icons-material/CheckCircle';
import DoNotDisturbIcon from '@mui/icons-material/DoNotDisturb';
import InfoOutlinedIcon from '@mui/icons-material/InfoOutlined';

import { useCopilotStore } from '../../state';
import RationaleCard from './RationaleCard';

/**
 * Shows why Copilot recommended the current letter's violations
 * @param {Object} props
 * @param {Array} props.includedViolationIds - IDs of violations in the letter
 */
export default function LetterTrace({ includedViolationIds = [] }) {
  const {
    recommendation,
    isPassiveMode,
    selectedGoal,
  } = useCopilotStore();

  // No recommendation - show minimal state
  if (!recommendation || isPassiveMode) {
    return (
      <Paper
        variant="outlined"
        sx={{
          p: 2,
          mt: 4,
          bgcolor: 'action.hover',
          borderRadius: 2,
        }}
      >
        <Box sx={{ display: 'flex', alignItems: 'center', gap: 1, mb: 1 }}>
          <SmartToyIcon sx={{ color: 'text.disabled' }} />
          <Typography variant="subtitle2" color="text.secondary">
            Copilot Analysis
          </Typography>
        </Box>
        <Typography variant="body2" color="text.secondary">
          Copilot is observing. This letter was generated based on your selections.
        </Typography>
      </Paper>
    );
  }

  // Find which included violations have actions vs skips
  const includedActions = recommendation.actions?.filter(
    (a) => includedViolationIds.includes(a.blocker_source_id)
  ) || [];

  const includedSkips = recommendation.skips?.filter(
    (s) => includedViolationIds.includes(s.source_id)
  ) || [];

  const hasOverrides = includedSkips.length > 0;

  return (
    <Paper
      variant="outlined"
      sx={{
        mt: 4,
        borderRadius: 2,
        overflow: 'hidden',
      }}
    >
      <Accordion defaultExpanded={false}>
        <AccordionSummary
          expandIcon={<ExpandMoreIcon />}
          sx={{
            bgcolor: 'background.paper',
            borderBottom: '1px solid',
            borderColor: 'divider',
          }}
        >
          <Box sx={{ display: 'flex', alignItems: 'center', gap: 1.5 }}>
            <SmartToyIcon sx={{ color: 'primary.main' }} />
            <Box>
              <Typography variant="subtitle1" fontWeight={600}>
                Why this letter?
              </Typography>
              <Typography variant="caption" color="text.secondary">
                Copilot's analysis for your {selectedGoal.replace(/_/g, ' ')} goal
              </Typography>
            </Box>
            {hasOverrides && (
              <Chip
                size="small"
                label={`${includedSkips.length} override${includedSkips.length > 1 ? 's' : ''}`}
                color="warning"
                sx={{ ml: 'auto' }}
              />
            )}
          </Box>
        </AccordionSummary>

        <AccordionDetails sx={{ p: 0 }}>
          {/* Sequencing Rationale */}
          {recommendation.sequencing_rationale && (
            <Box sx={{ p: 2, bgcolor: 'action.hover' }}>
              <Box sx={{ display: 'flex', alignItems: 'flex-start', gap: 1 }}>
                <InfoOutlinedIcon fontSize="small" sx={{ mt: 0.5, color: 'info.main' }} />
                <Typography variant="body2" color="text.secondary">
                  {recommendation.sequencing_rationale}
                </Typography>
              </Box>
            </Box>
          )}

          <Divider />

          {/* Recommended Actions */}
          {includedActions.length > 0 && (
            <Box sx={{ p: 2 }}>
              <Box sx={{ display: 'flex', alignItems: 'center', gap: 1, mb: 1.5 }}>
                <CheckCircleIcon fontSize="small" sx={{ color: 'success.main' }} />
                <Typography variant="subtitle2">
                  Recommended Actions ({includedActions.length})
                </Typography>
              </Box>
              <List dense disablePadding>
                {includedActions.map((action, i) => (
                  <ListItem key={action.action_id || i} sx={{ pl: 4 }}>
                    <ListItemText
                      primary={
                        <Typography variant="body2" fontWeight={500}>
                          {action.creditor_name || 'Unknown'}
                        </Typography>
                      }
                      secondary={
                        <Typography variant="caption" color="text.secondary">
                          {action.rationale}
                        </Typography>
                      }
                    />
                  </ListItem>
                ))}
              </List>
            </Box>
          )}

          {/* User Overrides */}
          {includedSkips.length > 0 && (
            <>
              <Divider />
              <Box sx={{ p: 2, bgcolor: 'warning.50' }}>
                <Box sx={{ display: 'flex', alignItems: 'center', gap: 1, mb: 1.5 }}>
                  <DoNotDisturbIcon fontSize="small" sx={{ color: 'warning.main' }} />
                  <Typography variant="subtitle2" color="warning.dark">
                    Your Overrides ({includedSkips.length})
                  </Typography>
                </Box>
                <Typography variant="caption" color="text.secondary" sx={{ display: 'block', mb: 1.5 }}>
                  You chose to include these items despite Copilot's advice:
                </Typography>
                <List dense disablePadding>
                  {includedSkips.map((skip, i) => (
                    <ListItem key={skip.source_id || i} sx={{ pl: 4 }}>
                      <ListItemText
                        primary={
                          <Typography variant="body2" fontWeight={500}>
                            {skip.creditor_name || 'Unknown'}
                          </Typography>
                        }
                        secondary={
                          <Box>
                            <Chip
                              size="small"
                              label={skip.code?.replace(/_/g, ' ')}
                              color="error"
                              variant="outlined"
                              sx={{ mb: 0.5, fontSize: '0.65rem', height: 18 }}
                            />
                            <Typography variant="caption" color="text.secondary" display="block">
                              {skip.rationale}
                            </Typography>
                          </Box>
                        }
                      />
                    </ListItem>
                  ))}
                </List>
              </Box>
            </>
          )}

          {/* Gap Summary */}
          {recommendation.current_gap_summary && (
            <>
              <Divider />
              <Box sx={{ p: 2, bgcolor: 'action.hover' }}>
                <Typography variant="caption" color="text.secondary">
                  <strong>Goal Gap:</strong> {recommendation.current_gap_summary}
                </Typography>
              </Box>
            </>
          )}
        </AccordionDetails>
      </Accordion>
    </Paper>
  );
}
