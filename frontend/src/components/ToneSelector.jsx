/**
 * Credit Engine 2.0 - Tone Selector Component
 * Allows user to select letter tone and grouping strategy
 */
import React from 'react';
import {
  Box,
  Paper,
  Typography,
  FormControl,
  InputLabel,
  Select,
  MenuItem,
  Grid,
} from '@mui/material';
import { useUIStore } from '../state';
import { formatToneLabel, formatGroupingLabel } from '../utils';

const toneDescriptions = {
  formal: 'Professional language citing specific FCRA sections and legal requirements.',
  assertive: 'Direct and demanding tone emphasizing compliance obligations.',
  conversational: 'Friendly and approachable language that clearly explains the issues.',
  narrative: 'Storytelling approach that explains the situation in detail.',
};

const groupingDescriptions = {
  by_violation_type: 'Groups all similar violations together (e.g., all missing DOFD issues).',
  by_account: 'Groups violations by each account, showing all issues per tradeline.',
  by_bureau: 'Groups violations by the reporting bureau.',
};

const ToneSelector = () => {
  const {
    selectedTone,
    groupingStrategy,
    availableTones,
    setTone,
    setGroupingStrategy,
  } = useUIStore();

  return (
    <Paper
      elevation={2}
      sx={{
        p: 3,
        borderRadius: 3,
        boxShadow: '0 1px 3px rgba(0,0,0,0.12)',
      }}
    >
      <Typography variant="h6" gutterBottom>
        Letter Customization
      </Typography>

      <Grid container spacing={3}>
        <Grid item xs={12} md={6}>
          <FormControl fullWidth>
            <InputLabel>Letter Tone</InputLabel>
            <Select
              value={selectedTone}
              label="Letter Tone"
              onChange={(e) => setTone(e.target.value)}
            >
              {availableTones.map((tone) => (
                <MenuItem key={tone} value={tone}>
                  {formatToneLabel(tone)}
                </MenuItem>
              ))}
            </Select>
          </FormControl>
          <Typography variant="caption" color="text.secondary" sx={{ mt: 1, display: 'block' }}>
            {toneDescriptions[selectedTone] || 'Choose a tone for your letter.'}
          </Typography>
        </Grid>

        <Grid item xs={12} md={6}>
          <FormControl fullWidth>
            <InputLabel>Organize Letter By</InputLabel>
            <Select
              value={groupingStrategy}
              label="Organize Letter By"
              onChange={(e) => setGroupingStrategy(e.target.value)}
            >
              <MenuItem value="by_violation_type">
                {formatGroupingLabel('by_violation_type')}
              </MenuItem>
              <MenuItem value="by_account">
                {formatGroupingLabel('by_account')}
              </MenuItem>
              <MenuItem value="by_bureau">
                {formatGroupingLabel('by_bureau')}
              </MenuItem>
            </Select>
          </FormControl>
          <Typography variant="caption" color="text.secondary" sx={{ mt: 1, display: 'block' }}>
            {groupingDescriptions[groupingStrategy] || 'Choose how to organize violations in your letter.'}
          </Typography>
        </Grid>
      </Grid>
    </Paper>
  );
};

export default ToneSelector;
