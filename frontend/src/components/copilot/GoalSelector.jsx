/**
 * GoalSelector - Credit goal dropdown for Copilot
 *
 * Allows users to select their credit goal, which drives
 * Copilot's recommendations and prioritization.
 */
import React from 'react';
import {
  FormControl,
  InputLabel,
  Select,
  MenuItem,
  CircularProgress,
  Typography,
  Box,
} from '@mui/material';
import FlagIcon from '@mui/icons-material/Flag';

import { useCopilotStore } from '../../state';

export default function GoalSelector({ size = 'small', showLabel = true }) {
  const {
    goals,
    selectedGoal,
    setSelectedGoal,
    isLoadingGoals,
    currentReportId,
    fetchRecommendation,
  } = useCopilotStore();

  const handleChange = async (event) => {
    const newGoal = event.target.value;
    setSelectedGoal(newGoal);

    // Refetch recommendation with new goal if we have a report
    if (currentReportId) {
      try {
        await fetchRecommendation(currentReportId, newGoal);
      } catch (error) {
        console.error('Failed to fetch recommendation for new goal:', error);
      }
    }
  };

  if (isLoadingGoals) {
    return (
      <Box sx={{ display: 'flex', alignItems: 'center', gap: 1 }}>
        <CircularProgress size={16} />
        <Typography variant="body2" color="text.secondary">
          Loading goals...
        </Typography>
      </Box>
    );
  }

  return (
    <FormControl fullWidth size={size}>
      {showLabel && (
        <InputLabel id="goal-selector-label">
          <Box sx={{ display: 'flex', alignItems: 'center', gap: 0.5 }}>
            <FlagIcon fontSize="small" />
            Credit Goal
          </Box>
        </InputLabel>
      )}
      <Select
        labelId="goal-selector-label"
        id="goal-selector"
        value={selectedGoal}
        onChange={handleChange}
        label={showLabel ? 'Credit Goal' : undefined}
        displayEmpty={!showLabel}
      >
        {goals.map((goal) => (
          <MenuItem key={goal.code} value={goal.code}>
            <Box>
              <Typography variant="body2">{goal.name}</Typography>
              <Typography variant="caption" color="text.secondary">
                {goal.description}
              </Typography>
            </Box>
          </MenuItem>
        ))}
        {goals.length === 0 && (
          <MenuItem value="credit_hygiene">
            <Typography variant="body2">General Credit Hygiene</Typography>
          </MenuItem>
        )}
      </Select>
    </FormControl>
  );
}
