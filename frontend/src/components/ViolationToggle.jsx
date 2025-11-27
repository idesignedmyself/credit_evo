/**
 * Credit Engine 2.0 - Violation Toggle Component
 * Individual violation card with toggle functionality
 */
import React from 'react';
import {
  Box,
  Paper,
  Typography,
  Checkbox,
  Chip,
  Collapse,
  IconButton,
} from '@mui/material';
import ExpandMoreIcon from '@mui/icons-material/ExpandMore';
import ExpandLessIcon from '@mui/icons-material/ExpandLess';
import { formatViolation, getSeverityConfig } from '../utils';

const ViolationToggle = ({ violation, isSelected, onToggle }) => {
  const [expanded, setExpanded] = React.useState(false);
  const formatted = formatViolation(violation);
  const severityConfig = getSeverityConfig(violation.severity);

  return (
    <Paper
      sx={{
        p: 2,
        mb: 1,
        border: '1px solid',
        borderColor: isSelected ? 'primary.main' : 'grey.200',
        backgroundColor: isSelected ? 'action.selected' : 'background.paper',
        transition: 'all 0.2s ease',
      }}
    >
      <Box sx={{ display: 'flex', alignItems: 'flex-start', gap: 1 }}>
        <Checkbox
          checked={isSelected}
          onChange={() => onToggle(violation.violation_id)}
          color="primary"
        />

        <Box sx={{ flex: 1 }}>
          <Box sx={{ display: 'flex', alignItems: 'center', gap: 1, mb: 0.5 }}>
            <Typography variant="subtitle1" sx={{ fontWeight: 'bold' }}>
              {formatted.displayLabel}
            </Typography>
            <Chip
              label={violation.severity}
              size="small"
              color={severityConfig.color}
            />
          </Box>

          <Typography variant="body2" color="text.secondary">
            {formatted.accountDisplay}
            {violation.account_number_masked && ` (${violation.account_number_masked})`}
          </Typography>

          <Collapse in={expanded}>
            <Box sx={{ mt: 2, pl: 1, borderLeft: '3px solid', borderColor: 'grey.300' }}>
              <Typography variant="body2" sx={{ mb: 1 }}>
                {formatted.displayDescription}
              </Typography>

              {formatted.fcraDisplay && (
                <Chip
                  label={formatted.fcraDisplay}
                  size="small"
                  variant="outlined"
                  sx={{ mr: 1, mb: 1 }}
                />
              )}

              {formatted.metroDisplay && (
                <Chip
                  label={formatted.metroDisplay}
                  size="small"
                  variant="outlined"
                  sx={{ mr: 1, mb: 1 }}
                />
              )}

              {violation.expected_value && violation.actual_value && (
                <Box sx={{ mt: 1 }}>
                  <Typography variant="caption" color="text.secondary">
                    Expected: <strong>{violation.expected_value}</strong>
                  </Typography>
                  <br />
                  <Typography variant="caption" color="text.secondary">
                    Actual: <strong>{violation.actual_value}</strong>
                  </Typography>
                </Box>
              )}
            </Box>
          </Collapse>
        </Box>

        <IconButton
          size="small"
          onClick={() => setExpanded(!expanded)}
          sx={{ ml: 1 }}
        >
          {expanded ? <ExpandLessIcon /> : <ExpandMoreIcon />}
        </IconButton>
      </Box>
    </Paper>
  );
};

export default ViolationToggle;
