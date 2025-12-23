/**
 * CopilotDrawer - Persistent Side Drawer for Credit Copilot
 *
 * "Copilot recommends. You decide."
 *
 * Architecture:
 * - 380px right-anchored persistent drawer
 * - Never blocks interaction (non-modal)
 * - Smooth CSS transitions
 * - Supports passive/ghost mode when no blockers
 */
import React, { useEffect } from 'react';
import {
  Box,
  Drawer,
  IconButton,
  Typography,
  Divider,
  Tabs,
  Tab,
  List,
  ListItem,
  ListItemText,
  Chip,
  CircularProgress,
  Alert,
  Tooltip,
  useTheme,
  useMediaQuery,
} from '@mui/material';
import CloseIcon from '@mui/icons-material/Close';
import SmartToyIcon from '@mui/icons-material/SmartToy';
import BlockIcon from '@mui/icons-material/Block';
import CheckCircleIcon from '@mui/icons-material/CheckCircle';
import DoNotDisturbIcon from '@mui/icons-material/DoNotDisturb';
import VisibilityIcon from '@mui/icons-material/Visibility';

import { useCopilotStore, useAuthStore } from '../../state';
import AchievabilityMeter from './AchievabilityMeter';

// Goal display names mapping
const GOAL_NAMES = {
  credit_hygiene: 'General Credit Hygiene',
  auto_loan: 'Auto Loan',
  mortgage: 'Mortgage',
  credit_card: 'Credit Card',
  personal_loan: 'Personal Loan',
  rental: 'Rental Application',
  employment: 'Employment Check',
};

const DRAWER_WIDTH = 380;

/**
 * Tab panel component
 */
function TabPanel({ children, value, index, ...other }) {
  return (
    <div
      role="tabpanel"
      hidden={value !== index}
      id={`copilot-tabpanel-${index}`}
      aria-labelledby={`copilot-tab-${index}`}
      {...other}
    >
      {value === index && <Box sx={{ p: 2 }}>{children}</Box>}
    </div>
  );
}

/**
 * Blocker list item
 */
function BlockerItem({ blocker }) {
  return (
    <ListItem
      sx={{
        bgcolor: 'background.paper',
        mb: 1,
        borderRadius: 1,
        border: '1px solid',
        borderColor: 'divider',
        flexDirection: 'column',
        alignItems: 'flex-start',
      }}
    >
      <Box sx={{ display: 'flex', alignItems: 'center', width: '100%', mb: 0.5 }}>
        <Chip
          size="small"
          label={blocker.category}
          color={blocker.blocks_goal ? 'error' : 'warning'}
          sx={{ mr: 1 }}
        />
        {blocker.creditor_name && (
          <Typography variant="caption" color="text.secondary">
            {blocker.creditor_name}
          </Typography>
        )}
      </Box>
      <Typography variant="body2" fontWeight={500}>
        {blocker.title}
      </Typography>
      <Typography variant="caption" color="text.secondary">
        {blocker.description}
      </Typography>
      {blocker.risk_factors?.length > 0 && (
        <Box sx={{ mt: 0.5, display: 'flex', gap: 0.5, flexWrap: 'wrap' }}>
          {blocker.risk_factors.slice(0, 2).map((factor, i) => (
            <Chip
              key={i}
              size="small"
              label={factor}
              variant="outlined"
              sx={{ fontSize: '0.65rem', height: 20 }}
            />
          ))}
        </Box>
      )}
    </ListItem>
  );
}

/**
 * Action list item
 */
function ActionItem({ action }) {
  return (
    <ListItem
      sx={{
        bgcolor: 'success.50',
        mb: 1,
        borderRadius: 1,
        border: '1px solid',
        borderColor: 'success.200',
        flexDirection: 'column',
        alignItems: 'flex-start',
      }}
    >
      <Box sx={{ display: 'flex', alignItems: 'center', width: '100%', mb: 0.5 }}>
        <Chip
          size="small"
          icon={<CheckCircleIcon />}
          label={`Priority ${action.sequence_order}`}
          color="success"
          sx={{ mr: 1 }}
        />
        {action.creditor_name && (
          <Typography variant="caption" color="text.secondary">
            {action.creditor_name}
          </Typography>
        )}
      </Box>
      <Typography variant="body2" fontWeight={500}>
        {action.action_type.replace(/_/g, ' ')}
      </Typography>
      <Typography variant="caption" color="text.secondary">
        {action.rationale}
      </Typography>
    </ListItem>
  );
}

/**
 * Skip list item
 */
function SkipItem({ skip }) {
  return (
    <ListItem
      sx={{
        bgcolor: 'error.50',
        mb: 1,
        borderRadius: 1,
        border: '1px solid',
        borderColor: 'error.200',
        flexDirection: 'column',
        alignItems: 'flex-start',
      }}
    >
      <Box sx={{ display: 'flex', alignItems: 'center', width: '100%', mb: 0.5 }}>
        <Chip
          size="small"
          icon={<DoNotDisturbIcon />}
          label={skip.code.replace(/_/g, ' ')}
          color="error"
          sx={{ mr: 1 }}
        />
        {skip.creditor_name && (
          <Typography variant="caption" color="text.secondary">
            {skip.creditor_name}
          </Typography>
        )}
      </Box>
      <Typography variant="caption" color="text.secondary">
        {skip.rationale}
      </Typography>
    </ListItem>
  );
}

/**
 * Passive mode display (ghost state)
 */
function PassiveMode() {
  return (
    <Box
      sx={{
        display: 'flex',
        flexDirection: 'column',
        alignItems: 'center',
        justifyContent: 'center',
        py: 6,
        px: 3,
        textAlign: 'center',
      }}
    >
      <VisibilityIcon sx={{ fontSize: 48, color: 'text.disabled', mb: 2 }} />
      <Typography variant="h6" color="text.secondary" gutterBottom>
        Copilot is observing
      </Typography>
      <Typography variant="body2" color="text.secondary">
        No specific blockers detected for your goal. Your report looks clean!
      </Typography>
    </Box>
  );
}

/**
 * Main CopilotDrawer component
 */
export default function CopilotDrawer() {
  const theme = useTheme();
  const isMobile = useMediaQuery(theme.breakpoints.down('md'));

  const {
    drawerOpen,
    closeDrawer,
    recommendation,
    isLoadingRecommendation,
    isPassiveMode,
    error,
    activeSection,
    setActiveSection,
  } = useCopilotStore();

  // Get user's goal from profile
  const { user } = useAuthStore();
  const userGoal = user?.credit_goal || 'credit_hygiene';
  const goalDisplayName = GOAL_NAMES[userGoal] || userGoal;

  // Tab index mapping
  const tabIndex =
    activeSection === 'blockers' ? 0 : activeSection === 'actions' ? 1 : 2;

  const handleTabChange = (_, newValue) => {
    const sections = ['blockers', 'actions', 'skips'];
    setActiveSection(sections[newValue]);
  };

  // Counts for tab badges
  const blockerCount = recommendation?.blockers?.length || 0;
  const actionCount = recommendation?.actions?.length || 0;
  const skipCount = recommendation?.skips?.length || 0;

  return (
    <Drawer
      anchor="right"
      open={drawerOpen}
      onClose={closeDrawer}
      variant={isMobile ? 'temporary' : 'persistent'}
      sx={{
        '& .MuiDrawer-paper': {
          width: DRAWER_WIDTH,
          boxSizing: 'border-box',
          bgcolor: 'background.default',
          borderLeft: '1px solid',
          borderColor: 'divider',
        },
      }}
    >
      {/* Header */}
      <Box
        sx={{
          display: 'flex',
          alignItems: 'center',
          justifyContent: 'space-between',
          p: 2,
          borderBottom: '1px solid',
          borderColor: 'divider',
          bgcolor: 'background.paper',
        }}
      >
        <Box sx={{ display: 'flex', alignItems: 'center' }}>
          <SmartToyIcon sx={{ mr: 1, color: 'primary.main' }} />
          <Typography variant="h6" fontWeight={600}>
            Credit Copilot
          </Typography>
        </Box>
        <IconButton onClick={closeDrawer} size="small">
          <CloseIcon />
        </IconButton>
      </Box>

      {/* Goal Display (read-only - set in Profile) */}
      <Box sx={{ px: 2, py: 1.5, bgcolor: 'grey.50', borderBottom: '1px solid', borderColor: 'divider' }}>
        <Typography variant="caption" color="text.secondary" display="block">
          Your Credit Goal
        </Typography>
        <Typography variant="body2" fontWeight={600} color="primary.main">
          {goalDisplayName}
        </Typography>
      </Box>

      {/* Content */}
      <Box sx={{ flexGrow: 1, overflow: 'auto' }}>
        {/* Loading State */}
        {isLoadingRecommendation && (
          <Box
            sx={{
              display: 'flex',
              flexDirection: 'column',
              alignItems: 'center',
              justifyContent: 'center',
              py: 6,
            }}
          >
            <CircularProgress size={32} sx={{ mb: 2 }} />
            <Typography variant="body2" color="text.secondary">
              Analyzing your report...
            </Typography>
          </Box>
        )}

        {/* Error State */}
        {error && !isLoadingRecommendation && (
          <Box sx={{ p: 2 }}>
            <Alert severity="warning" sx={{ mb: 2 }}>
              {error}
            </Alert>
            <PassiveMode />
          </Box>
        )}

        {/* Passive Mode */}
        {!isLoadingRecommendation && !error && isPassiveMode && <PassiveMode />}

        {/* Active Mode - Has Recommendation */}
        {!isLoadingRecommendation && !error && !isPassiveMode && recommendation && (
          <>
            {/* Achievability Meter */}
            <Box sx={{ p: 2 }}>
              <AchievabilityMeter
                level={recommendation.goal_achievability}
                gapSummary={recommendation.current_gap_summary}
              />
            </Box>

            <Divider />

            {/* Tabs */}
            <Tabs
              value={tabIndex}
              onChange={handleTabChange}
              variant="fullWidth"
              sx={{
                borderBottom: 1,
                borderColor: 'divider',
                '& .MuiTab-root': {
                  minHeight: 48,
                  textTransform: 'none',
                },
              }}
            >
              <Tab
                icon={<BlockIcon fontSize="small" />}
                iconPosition="start"
                label={
                  <Box sx={{ display: 'flex', alignItems: 'center', gap: 0.5 }}>
                    Blockers
                    {blockerCount > 0 && (
                      <Chip
                        size="small"
                        label={blockerCount}
                        color="error"
                        sx={{ height: 18, fontSize: '0.7rem' }}
                      />
                    )}
                  </Box>
                }
              />
              <Tab
                icon={<CheckCircleIcon fontSize="small" />}
                iconPosition="start"
                label={
                  <Box sx={{ display: 'flex', alignItems: 'center', gap: 0.5 }}>
                    Actions
                    {actionCount > 0 && (
                      <Chip
                        size="small"
                        label={actionCount}
                        color="success"
                        sx={{ height: 18, fontSize: '0.7rem' }}
                      />
                    )}
                  </Box>
                }
              />
              <Tab
                icon={<DoNotDisturbIcon fontSize="small" />}
                iconPosition="start"
                label={
                  <Box sx={{ display: 'flex', alignItems: 'center', gap: 0.5 }}>
                    Skips
                    {skipCount > 0 && (
                      <Chip
                        size="small"
                        label={skipCount}
                        sx={{ height: 18, fontSize: '0.7rem' }}
                      />
                    )}
                  </Box>
                }
              />
            </Tabs>

            {/* Tab Panels */}
            <TabPanel value={tabIndex} index={0}>
              {blockerCount === 0 ? (
                <Typography variant="body2" color="text.secondary" textAlign="center">
                  No blockers detected for your goal.
                </Typography>
              ) : (
                <List disablePadding>
                  {recommendation.blockers.map((blocker, i) => (
                    <BlockerItem key={blocker.source_id || i} blocker={blocker} />
                  ))}
                </List>
              )}
            </TabPanel>

            <TabPanel value={tabIndex} index={1}>
              {actionCount === 0 ? (
                <Typography variant="body2" color="text.secondary" textAlign="center">
                  No recommended actions at this time.
                </Typography>
              ) : (
                <List disablePadding>
                  {recommendation.actions.map((action, i) => (
                    <ActionItem key={action.action_id || i} action={action} />
                  ))}
                </List>
              )}
            </TabPanel>

            <TabPanel value={tabIndex} index={2}>
              {skipCount === 0 ? (
                <Typography variant="body2" color="text.secondary" textAlign="center">
                  No items to skip.
                </Typography>
              ) : (
                <List disablePadding>
                  {recommendation.skips.map((skip, i) => (
                    <SkipItem key={skip.source_id || i} skip={skip} />
                  ))}
                </List>
              )}
            </TabPanel>
          </>
        )}

        {/* No recommendation yet */}
        {!isLoadingRecommendation && !error && !recommendation && !isPassiveMode && (
          <Box sx={{ p: 3, textAlign: 'center' }}>
            <Typography variant="body2" color="text.secondary">
              Select a report to see Copilot recommendations.
            </Typography>
          </Box>
        )}
      </Box>

      {/* Footer */}
      {recommendation && (
        <Box
          sx={{
            p: 1.5,
            borderTop: '1px solid',
            borderColor: 'divider',
            bgcolor: 'background.paper',
          }}
        >
          <Typography variant="caption" color="text.disabled" display="block">
            Recommendation ID: {recommendation.recommendation_id?.slice(0, 8)}...
          </Typography>
          {recommendation.sequencing_rationale && (
            <Tooltip title={recommendation.sequencing_rationale}>
              <Typography
                variant="caption"
                color="text.secondary"
                sx={{
                  display: 'block',
                  overflow: 'hidden',
                  textOverflow: 'ellipsis',
                  whiteSpace: 'nowrap',
                  cursor: 'help',
                }}
              >
                {recommendation.sequencing_rationale}
              </Typography>
            </Tooltip>
          )}
        </Box>
      )}
    </Drawer>
  );
}
