/**
 * Credit Engine 2.0 - Tone Selector Component
 * Allows user to select letter type and tone
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
  ToggleButtonGroup,
  ToggleButton,
  Chip,
} from '@mui/material';
import GavelIcon from '@mui/icons-material/Gavel';
import PersonIcon from '@mui/icons-material/Person';
import { useUIStore } from '../state';
import { formatToneLabel } from '../utils';

const civilianToneDescriptions = {
  formal: 'Professional language citing specific FCRA sections and legal requirements.',
  assertive: 'Direct and demanding tone emphasizing compliance obligations.',
  conversational: 'Friendly and approachable language that clearly explains the issues.',
  narrative: 'Storytelling approach that explains the situation in detail.',
};

const legalToneDescriptions = {
  professional: 'Balanced legal language with FCRA citations and Metro-2 references.',
  strict_legal: 'Formal legal terminology with comprehensive case law citations.',
  soft_legal: 'Consumer-friendly legal language with educational tone.',
  aggressive: 'Strong legal language with explicit damage warnings and compliance demands.',
};

const ToneSelector = () => {
  const {
    letterType,
    selectedTone,
    selectedBureau,
    availableTones,
    legalTones,
    availableBureaus,
    setLetterType,
    setTone,
  } = useUIStore();

  // Get the bureau display name
  const bureauName = availableBureaus.find(b => b.id === selectedBureau)?.name || selectedBureau;

  // Get the current tones and descriptions based on letter type
  const currentTones = letterType === 'legal' ? legalTones : availableTones;
  const currentDescriptions = letterType === 'legal' ? legalToneDescriptions : civilianToneDescriptions;

  const handleLetterTypeChange = (event, newType) => {
    if (newType !== null) {
      setLetterType(newType);
    }
  };

  return (
    <Paper
      elevation={2}
      sx={{
        p: 3,
        borderRadius: 3,
        boxShadow: '0 1px 3px rgba(0,0,0,0.12)',
      }}
    >
      <Box sx={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', mb: 3 }}>
        <Typography variant="h6">
          Letter Customization
        </Typography>
        <Typography variant="body2" color="text.secondary">
          Sending to: <strong>{bureauName}</strong>
        </Typography>
      </Box>

      {/* Letter Type Toggle */}
      <Box sx={{ mb: 3 }}>
        <Typography variant="subtitle2" sx={{ mb: 1, fontWeight: 600 }}>
          Letter Type
        </Typography>
        <ToggleButtonGroup
          value={letterType}
          exclusive
          onChange={handleLetterTypeChange}
          fullWidth
          sx={{
            '& .MuiToggleButton-root': {
              py: 1.5,
              textTransform: 'none',
              fontSize: '0.95rem',
            },
          }}
        >
          <ToggleButton value="civilian" sx={{ gap: 1 }}>
            <PersonIcon fontSize="small" />
            Civilian
          </ToggleButton>
          <ToggleButton value="legal" sx={{ gap: 1 }}>
            <GavelIcon fontSize="small" />
            Legal
          </ToggleButton>
        </ToggleButtonGroup>
        <Typography variant="caption" color="text.secondary" sx={{ mt: 1, display: 'block' }}>
          {letterType === 'legal'
            ? 'Legal letters include FCRA citations, case law, Metro-2 compliance, and Method of Verification (MOV) demands.'
            : 'Civilian letters use natural, human-readable language to explain your dispute clearly.'}
        </Typography>
      </Box>

      {/* Letter Tone Selector */}
      <FormControl fullWidth>
        <InputLabel>Letter Tone</InputLabel>
        <Select
          value={selectedTone}
          label="Letter Tone"
          onChange={(e) => setTone(e.target.value)}
        >
          {currentTones.map((tone) => (
            <MenuItem key={tone} value={tone}>
              {formatToneLabel(tone)}
            </MenuItem>
          ))}
        </Select>
      </FormControl>
      <Typography variant="caption" color="text.secondary" sx={{ mt: 1, display: 'block' }}>
        {currentDescriptions[selectedTone] || 'Choose a tone for your letter.'}
      </Typography>

      {/* Legal Letter Badge */}
      {letterType === 'legal' && (
        <Box sx={{ mt: 2, display: 'flex', gap: 1, flexWrap: 'wrap' }}>
          <Chip size="small" label="FCRA Citations" color="primary" variant="outlined" />
          <Chip size="small" label="Case Law" color="primary" variant="outlined" />
          <Chip size="small" label="Metro-2" color="primary" variant="outlined" />
          <Chip size="small" label="MOV Demands" color="primary" variant="outlined" />
        </Box>
      )}
    </Paper>
  );
};

export default ToneSelector;
