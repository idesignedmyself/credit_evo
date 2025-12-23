/**
 * CopilotStatusCard - Compact status card for AuditPage
 *
 * Shows at-a-glance Copilot status:
 * - Current goal achievability
 * - Blocker/action counts
 * - Quick link to open drawer
 * - Supports passive/ghost mode
 */
import React, { useEffect } from 'react';
import {
  Card,
  CardContent,
  Box,
  Typography,
  Button,
  Chip,
  Skeleton,
  Divider,
} from '@mui/material';
import SmartToyIcon from '@mui/icons-material/SmartToy';
import BlockIcon from '@mui/icons-material/Block';
import CheckCircleIcon from '@mui/icons-material/CheckCircle';
import DoNotDisturbIcon from '@mui/icons-material/DoNotDisturb';
import ArrowForwardIcon from '@mui/icons-material/ArrowForward';
import VisibilityIcon from '@mui/icons-material/Visibility';

import { useCopilotStore } from '../../state';
import AchievabilityMeter from './AchievabilityMeter';

/**
 * Status card for displaying Copilot summary on pages
 */
export default function CopilotStatusCard({ reportId, compact = false }) {
  const {
    recommendation,
    isLoadingRecommendation,
    isPassiveMode,
    error,
    selectedGoal,
    openDrawer,
    fetchRecommendation,
    currentReportId,
  } = useCopilotStore();

  // Fetch recommendation when reportId changes
  useEffect(() => {
    if (reportId && reportId !== currentReportId) {
      fetchRecommendation(reportId).catch(() => {
        // Error handled in store, fail silently to passive mode
      });
    }
  }, [reportId, currentReportId, fetchRecommendation]);

  // Loading state
  if (isLoadingRecommendation) {
    return (
      <Card variant="outlined" sx={{ mb: 2 }}>
        <CardContent>
          <Box sx={{ display: 'flex', alignItems: 'center', mb: 2 }}>
            <SmartToyIcon sx={{ mr: 1, color: 'primary.main' }} />
            <Typography variant="h6">Credit Copilot</Typography>
          </Box>
          <Skeleton variant="rectangular" height={60} sx={{ borderRadius: 1 }} />
        </CardContent>
      </Card>
    );
  }

  // Passive/Ghost mode
  if (isPassiveMode || error || !recommendation) {
    return (
      <Card variant="outlined" sx={{ mb: 2, bgcolor: 'action.hover' }}>
        <CardContent>
          <Box sx={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between' }}>
            <Box sx={{ display: 'flex', alignItems: 'center' }}>
              <VisibilityIcon sx={{ mr: 1, color: 'text.disabled' }} />
              <Box>
                <Typography variant="subtitle1" color="text.secondary">
                  Copilot is observing
                </Typography>
                <Typography variant="caption" color="text.disabled">
                  No specific blockers detected for your goal
                </Typography>
              </Box>
            </Box>
            <Button
              size="small"
              onClick={openDrawer}
              endIcon={<ArrowForwardIcon />}
              sx={{ textTransform: 'none' }}
            >
              View Details
            </Button>
          </Box>
        </CardContent>
      </Card>
    );
  }

  // Counts
  const blockerCount = recommendation.blockers?.length || 0;
  const actionCount = recommendation.actions?.length || 0;
  const skipCount = recommendation.skips?.length || 0;
  const hardBlockerCount = recommendation.hard_blocker_count || 0;

  // Compact mode for smaller displays
  if (compact) {
    return (
      <Card variant="outlined" sx={{ mb: 2 }}>
        <CardContent sx={{ py: 1.5, '&:last-child': { pb: 1.5 } }}>
          <Box sx={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between' }}>
            <Box sx={{ display: 'flex', alignItems: 'center', gap: 1 }}>
              <SmartToyIcon fontSize="small" sx={{ color: 'primary.main' }} />
              <Chip
                size="small"
                label={recommendation.goal_achievability}
                color={
                  recommendation.goal_achievability === 'ACHIEVABLE'
                    ? 'success'
                    : recommendation.goal_achievability === 'CHALLENGING'
                    ? 'warning'
                    : 'error'
                }
              />
              {blockerCount > 0 && (
                <Chip
                  size="small"
                  icon={<BlockIcon />}
                  label={blockerCount}
                  variant="outlined"
                  color="error"
                />
              )}
              {actionCount > 0 && (
                <Chip
                  size="small"
                  icon={<CheckCircleIcon />}
                  label={actionCount}
                  variant="outlined"
                  color="success"
                />
              )}
            </Box>
            <Button
              size="small"
              onClick={openDrawer}
              endIcon={<ArrowForwardIcon />}
              sx={{ textTransform: 'none' }}
            >
              Copilot
            </Button>
          </Box>
        </CardContent>
      </Card>
    );
  }

  // Full mode
  return (
    <Card variant="outlined" sx={{ mb: 2 }}>
      <CardContent>
        {/* Header */}
        <Box sx={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', mb: 2 }}>
          <Box sx={{ display: 'flex', alignItems: 'center' }}>
            <SmartToyIcon sx={{ mr: 1, color: 'primary.main' }} />
            <Typography variant="h6">Credit Copilot</Typography>
          </Box>
          <Button
            variant="outlined"
            size="small"
            onClick={openDrawer}
            endIcon={<ArrowForwardIcon />}
            sx={{ textTransform: 'none' }}
          >
            View Full Analysis
          </Button>
        </Box>

        {/* Achievability */}
        <Box sx={{ mb: 2 }}>
          <AchievabilityMeter
            level={recommendation.goal_achievability}
            gapSummary={recommendation.current_gap_summary}
          />
        </Box>

        <Divider sx={{ my: 2 }} />

        {/* Stats Row */}
        <Box sx={{ display: 'flex', gap: 2, flexWrap: 'wrap' }}>
          {/* Blockers */}
          <Box sx={{ display: 'flex', alignItems: 'center', gap: 0.5 }}>
            <BlockIcon fontSize="small" color={blockerCount > 0 ? 'error' : 'disabled'} />
            <Typography variant="body2">
              <strong>{blockerCount}</strong> blocker{blockerCount !== 1 ? 's' : ''}
              {hardBlockerCount > 0 && (
                <Typography component="span" variant="caption" color="error.main" sx={{ ml: 0.5 }}>
                  ({hardBlockerCount} hard)
                </Typography>
              )}
            </Typography>
          </Box>

          {/* Actions */}
          <Box sx={{ display: 'flex', alignItems: 'center', gap: 0.5 }}>
            <CheckCircleIcon fontSize="small" color={actionCount > 0 ? 'success' : 'disabled'} />
            <Typography variant="body2">
              <strong>{actionCount}</strong> recommended action{actionCount !== 1 ? 's' : ''}
            </Typography>
          </Box>

          {/* Skips */}
          {skipCount > 0 && (
            <Box sx={{ display: 'flex', alignItems: 'center', gap: 0.5 }}>
              <DoNotDisturbIcon fontSize="small" color="warning" />
              <Typography variant="body2">
                <strong>{skipCount}</strong> advised to skip
              </Typography>
            </Box>
          )}
        </Box>

        {/* Notes */}
        {recommendation.notes?.length > 0 && (
          <Box sx={{ mt: 2 }}>
            <Typography variant="caption" color="text.secondary">
              {recommendation.notes[0]}
            </Typography>
          </Box>
        )}
      </CardContent>
    </Card>
  );
}
