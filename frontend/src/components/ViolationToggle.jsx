/**
 * Credit Engine 2.0 - Violation Toggle Component
 * Premium "Fintech" accordion-style violation card with technical details grid
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
  Paper,
  Divider,
  Grid,
} from '@mui/material';
import ExpandMoreIcon from '@mui/icons-material/ExpandMore';
import { formatViolation, getSeverityConfig, getViolationUI } from '../utils';

const ViolationToggle = React.memo(({ violation, isSelected, onToggle }) => {
  // Guard against undefined/null violation
  if (!violation) return null;

  const formatted = formatViolation(violation);
  const severityConfig = getSeverityConfig(violation.severity);
  // Get UI semantic configuration (violations vs advisories)
  const uiConfig = getViolationUI(violation.violation_type, violation.severity);

  const handleCheckboxClick = (e) => {
    e.stopPropagation();
    onToggle(violation.violation_id);
  };

  return (
    <Accordion
      disableGutters
      sx={{
        mb: 1.5,
        border: '1px solid',
        borderColor: isSelected ? 'secondary.main' : '#E2E8F0',
        borderRadius: '12px !important',
        backgroundColor: isSelected ? 'rgba(59, 130, 246, 0.04)' : 'background.paper',
        '&:before': { display: 'none' },
        '&.Mui-expanded': { margin: '0 0 12px 0' },
        boxShadow: isSelected
          ? '0 0 0 1px rgba(59, 130, 246, 0.3), 0 4px 12px rgba(59, 130, 246, 0.1)'
          : '0px 1px 3px rgba(0, 0, 0, 0.04)',
        transition: 'all 0.15s ease',
      }}
    >
      <AccordionSummary
        expandIcon={<ExpandMoreIcon sx={{ color: 'text.secondary' }} />}
        sx={{
          px: 2,
          '& .MuiAccordionSummary-content': {
            alignItems: 'center',
            gap: 1,
            my: 1.5,
          },
        }}
      >
        <Checkbox
          checked={isSelected}
          onClick={handleCheckboxClick}
          color="primary"
          size="small"
          sx={{
            color: '#CBD5E1',
            '&.Mui-checked': { color: 'secondary.main' },
          }}
        />

        <Stack
          direction={{ xs: 'column', sm: 'row' }}
          alignItems={{ xs: 'flex-start', sm: 'center' }}
          spacing={1}
          sx={{ flexGrow: 1 }}
        >
          <Box sx={{ flexGrow: 1 }}>
            <Stack direction="row" alignItems="center" spacing={1} sx={{ mb: 0.5 }}>
              <Typography variant="subtitle1" sx={{ fontWeight: 600, color: 'text.primary' }}>
                {formatted.displayLabel}
              </Typography>
              <Chip
                label={violation.severity}
                size="small"
                sx={{
                  fontWeight: 600,
                  fontSize: '0.7rem',
                  height: 22,
                  bgcolor: severityConfig.color === 'error' ? '#FEE2E2'
                    : severityConfig.color === 'warning' ? '#FEF3C7'
                    : '#D1FAE5',
                  color: severityConfig.color === 'error' ? '#991B1B'
                    : severityConfig.color === 'warning' ? '#92400E'
                    : '#065F46',
                  border: 'none',
                }}
              />
            </Stack>
            <Typography variant="caption" color="text.secondary">
              {formatted.accountDisplay}
              {violation.account_number_masked && ` (${violation.account_number_masked})`}
            </Typography>
          </Box>
        </Stack>
      </AccordionSummary>

      <AccordionDetails sx={{ bgcolor: '#F8FAFC', p: 3, borderTop: '1px solid #E2E8F0' }}>
        {/* Description */}
        <Typography variant="body2" sx={{ mb: 3, color: 'text.secondary', maxWidth: '800px', lineHeight: 1.6 }}>
          {formatted.displayDescription}
        </Typography>

        {/* Technical Details Grid */}
        <Grid container spacing={2}>
          {/* Expected vs Actual Box - Uses semantic labels based on severity */}
          {(violation.expected_value || violation.actual_value) && (
            <Grid item xs={12} md={6}>
              <Paper
                variant="outlined"
                sx={{
                  p: 2.5,
                  bgcolor: uiConfig.mode === 'advisory' ? uiConfig.bgColor : '#fff',
                  borderColor: uiConfig.mode === 'advisory' ? uiConfig.borderColor : '#E2E8F0',
                  borderRadius: 2,
                }}
              >
                <Typography
                  variant="caption"
                  sx={{
                    textTransform: 'uppercase',
                    color: uiConfig.mode === 'advisory' ? uiConfig.iconColor : 'text.secondary',
                    fontWeight: 700,
                    letterSpacing: '0.05em',
                    fontSize: '0.65rem',
                  }}
                >
                  {uiConfig.boxTitle}
                </Typography>
                <Box sx={{ mt: 2, display: 'flex', justifyContent: 'space-between', gap: 2 }}>
                  {violation.expected_value && (
                    <Box sx={{ flex: 1 }}>
                      <Typography
                        variant="caption"
                        sx={{
                          fontWeight: 700,
                          color: uiConfig.expectedColor,
                          fontSize: '0.65rem',
                          textTransform: 'uppercase',
                          letterSpacing: '0.03em',
                        }}
                      >
                        {uiConfig.expectedLabel}
                      </Typography>
                      <Typography variant="body2" sx={{ fontWeight: 500, mt: 0.5, color: 'text.primary' }}>
                        {violation.expected_value}
                      </Typography>
                    </Box>
                  )}
                  {violation.expected_value && violation.actual_value && (
                    <Divider orientation="vertical" flexItem sx={{ borderColor: '#E2E8F0' }} />
                  )}
                  {violation.actual_value && (
                    <Box sx={{ flex: 1 }}>
                      <Typography
                        variant="caption"
                        sx={{
                          fontWeight: 700,
                          color: uiConfig.actualColor,
                          fontSize: '0.65rem',
                          textTransform: 'uppercase',
                          letterSpacing: '0.03em',
                        }}
                      >
                        {uiConfig.actualLabel}
                      </Typography>
                      <Typography variant="body2" sx={{ fontWeight: 500, mt: 0.5, color: 'text.primary' }}>
                        {violation.actual_value}
                      </Typography>
                    </Box>
                  )}
                </Box>
              </Paper>
            </Grid>
          )}

          {/* Legal Codes Box - Uses semantic labels based on severity */}
          {(formatted.fcraDisplay || formatted.metroDisplay) && (
            <Grid item xs={12} md={(violation.expected_value || violation.actual_value) ? 6 : 12}>
              <Paper
                variant="outlined"
                sx={{
                  p: 2.5,
                  bgcolor: uiConfig.mode === 'advisory' ? uiConfig.bgColor : '#fff',
                  height: '100%',
                  borderColor: uiConfig.mode === 'advisory' ? uiConfig.borderColor : '#E2E8F0',
                  borderRadius: 2,
                }}
              >
                <Typography
                  variant="caption"
                  sx={{
                    textTransform: 'uppercase',
                    color: uiConfig.mode === 'advisory' ? uiConfig.iconColor : 'text.secondary',
                    fontWeight: 700,
                    letterSpacing: '0.05em',
                    fontSize: '0.65rem',
                  }}
                >
                  {uiConfig.mode === 'advisory' ? 'Reference Standards' : 'Cited Statutes'}
                </Typography>
                <Stack direction="row" spacing={1} sx={{ mt: 1.5, flexWrap: 'wrap', gap: 1 }}>
                  {formatted.fcraDisplay && (
                    <Chip
                      label={formatted.fcraDisplay}
                      size="small"
                      sx={{
                        bgcolor: '#EFF6FF',
                        color: '#1E40AF',
                        fontWeight: 600,
                        borderRadius: 1,
                        fontSize: '0.75rem',
                        height: 26,
                      }}
                    />
                  )}
                  {formatted.metroDisplay && (
                    <Chip
                      label={formatted.metroDisplay}
                      size="small"
                      sx={{
                        bgcolor: '#F3E8FF',
                        color: '#6B21A8',
                        fontWeight: 600,
                        borderRadius: 1,
                        fontSize: '0.75rem',
                        height: 26,
                      }}
                    />
                  )}
                </Stack>
              </Paper>
            </Grid>
          )}
        </Grid>
      </AccordionDetails>
    </Accordion>
  );
});

export default ViolationToggle;
