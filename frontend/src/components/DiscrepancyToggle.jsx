/**
 * Credit Engine 2.0 - Discrepancy Toggle Component
 * Individual cross-bureau discrepancy card with toggle functionality
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

const getSeverityConfig = (severity) => {
  switch (severity?.toUpperCase()) {
    case 'HIGH':
      return { color: 'error', label: 'high' };
    case 'MEDIUM':
      return { color: 'warning', label: 'medium' };
    case 'LOW':
      return { color: 'info', label: 'low' };
    default:
      return { color: 'default', label: severity || 'unknown' };
  }
};

const formatViolationType = (type) => {
  if (!type) return 'Unknown';
  return type
    .replace(/_/g, ' ')
    .replace(/\b\w/g, (c) => c.toUpperCase());
};

const DiscrepancyToggle = React.memo(({ discrepancy, isSelected, onToggle }) => {
  const [expanded, setExpanded] = React.useState(false);
  const severityConfig = getSeverityConfig(discrepancy.severity);

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
          onChange={() => onToggle(discrepancy.discrepancy_id)}
          color="primary"
        />

        <Box sx={{ flex: 1 }}>
          <Box sx={{ display: 'flex', alignItems: 'center', gap: 1, mb: 0.5 }}>
            <Typography variant="subtitle1" sx={{ fontWeight: 'bold' }}>
              {formatViolationType(discrepancy.violation_type)}
            </Typography>
            <Chip
              label={severityConfig.label}
              size="small"
              color={severityConfig.color}
            />
          </Box>

          <Typography variant="body2" color="text.secondary">
            {discrepancy.creditor_name}
            {discrepancy.field_name && ` - ${discrepancy.field_name}`}
          </Typography>

          <Collapse in={expanded}>
            <Box sx={{ mt: 2, pl: 1, borderLeft: '3px solid', borderColor: 'grey.300' }}>
              <Typography variant="body2" sx={{ mb: 1 }}>
                {discrepancy.description}
              </Typography>

              {/* Bureau values comparison */}
              {discrepancy.values_by_bureau && (
                <Box sx={{ mt: 1 }}>
                  <Typography variant="caption" color="text.secondary" sx={{ fontWeight: 'bold', display: 'block', mb: 0.5 }}>
                    Values by Bureau:
                  </Typography>
                  {Object.entries(discrepancy.values_by_bureau).map(([bureau, value]) => (
                    <Box key={bureau} sx={{ display: 'flex', gap: 1, mb: 0.25 }}>
                      <Typography variant="caption" sx={{ fontWeight: 'bold', minWidth: 80 }}>
                        {bureau.toUpperCase()}:
                      </Typography>
                      <Typography variant="caption">
                        {value}
                      </Typography>
                    </Box>
                  ))}
                </Box>
              )}

              <Chip
                label={`Cross-Bureau • ${discrepancy.field_name || 'Data Mismatch'}`}
                size="small"
                variant="outlined"
                sx={{ mt: 1 }}
              />
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
});

export default DiscrepancyToggle;
