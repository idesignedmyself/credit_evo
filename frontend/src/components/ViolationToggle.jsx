/**
 * Credit Engine 2.0 - Violation Toggle Component
 * Accordion-style violation card with toggle functionality
 */
import React from 'react';
import {
  Accordion,
  AccordionSummary,
  AccordionDetails,
  Box,
  Typography,
  Checkbox,
  Chip,
  Stack,
} from '@mui/material';
import ExpandMoreIcon from '@mui/icons-material/ExpandMore';
import { formatViolation, getSeverityConfig } from '../utils';

const ViolationToggle = React.memo(({ violation, isSelected, onToggle }) => {
  const formatted = formatViolation(violation);
  const severityConfig = getSeverityConfig(violation.severity);

  const handleCheckboxClick = (e) => {
    e.stopPropagation();
    onToggle(violation.violation_id);
  };

  return (
    <Accordion
      disableGutters
      sx={{
        mb: 1,
        border: '1px solid',
        borderColor: isSelected ? 'primary.main' : 'divider',
        borderRadius: '8px !important',
        backgroundColor: isSelected ? 'action.selected' : 'background.paper',
        '&:before': { display: 'none' },
        '&.Mui-expanded': { margin: '0 0 8px 0' },
      }}
    >
      <AccordionSummary
        expandIcon={<ExpandMoreIcon />}
        sx={{
          '& .MuiAccordionSummary-content': {
            alignItems: 'center',
            gap: 1,
          },
        }}
      >
        <Checkbox
          checked={isSelected}
          onClick={handleCheckboxClick}
          color="primary"
          size="small"
        />

        <Stack
          direction={{ xs: 'column', sm: 'row' }}
          alignItems={{ xs: 'flex-start', sm: 'center' }}
          spacing={1}
          sx={{ flexGrow: 1 }}
        >
          <Box sx={{ flexGrow: 1 }}>
            <Stack direction="row" alignItems="center" spacing={1}>
              <Typography variant="subtitle1" sx={{ fontWeight: 600 }}>
                {formatted.displayLabel}
              </Typography>
              <Chip
                label={violation.severity}
                size="small"
                color={severityConfig.color}
                variant="outlined"
              />
            </Stack>
            <Typography variant="caption" color="text.secondary">
              {formatted.accountDisplay}
              {violation.account_number_masked && ` (${violation.account_number_masked})`}
            </Typography>
          </Box>
        </Stack>
      </AccordionSummary>

      <AccordionDetails sx={{ bgcolor: '#fafafa', p: 3 }}>
        <Typography variant="body2" sx={{ mb: 2 }}>
          {formatted.displayDescription}
        </Typography>

        {/* Legal Tags */}
        <Stack direction="row" spacing={1} sx={{ mb: 2, flexWrap: 'wrap', gap: 1 }}>
          {formatted.fcraDisplay && (
            <Chip
              label={formatted.fcraDisplay}
              size="small"
              sx={{ bgcolor: '#e3f2fd', color: '#1565c0', border: 'none' }}
            />
          )}
          {formatted.metroDisplay && (
            <Chip
              label={formatted.metroDisplay}
              size="small"
              sx={{ bgcolor: '#f3e5f5', color: '#7b1fa2', border: 'none' }}
            />
          )}
        </Stack>

        {/* Expected vs Actual */}
        {(violation.expected_value || violation.actual_value) && (
          <Box>
            {violation.expected_value && (
              <Typography variant="caption" display="block">
                <strong>Expected:</strong> {violation.expected_value}
              </Typography>
            )}
            {violation.actual_value && (
              <Typography variant="caption" display="block">
                <strong>Actual:</strong> {violation.actual_value}
              </Typography>
            )}
          </Box>
        )}
      </AccordionDetails>
    </Accordion>
  );
});

export default ViolationToggle;
