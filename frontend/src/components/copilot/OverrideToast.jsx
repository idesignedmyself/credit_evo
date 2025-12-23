/**
 * OverrideToast - Subsequent override notification
 *
 * Shows a brief, non-blocking toast when user overrides
 * Copilot's advice (after the first override in a session).
 *
 * Anti-friction: No modal spam after first confirmation.
 */
import React, { useEffect } from 'react';
import { Snackbar, Alert, Typography, Box } from '@mui/material';
import DoNotDisturbIcon from '@mui/icons-material/DoNotDisturb';

/**
 * Toast notification for subsequent overrides
 * @param {Object} props
 * @param {boolean} props.open - Toast open state
 * @param {Function} props.onClose - Close handler
 * @param {Object} props.violation - Violation being overridden
 * @param {number} props.overrideCount - Current session override count
 */
export default function OverrideToast({ open, onClose, violation, overrideCount }) {
  // Auto-close after 3 seconds
  useEffect(() => {
    if (open) {
      const timer = setTimeout(() => {
        onClose();
      }, 3000);
      return () => clearTimeout(timer);
    }
  }, [open, onClose]);

  return (
    <Snackbar
      open={open}
      onClose={onClose}
      anchorOrigin={{ vertical: 'bottom', horizontal: 'right' }}
      sx={{ mb: 8 }} // Above the FAB
    >
      <Alert
        severity="warning"
        icon={<DoNotDisturbIcon />}
        onClose={onClose}
        sx={{
          minWidth: 300,
          '& .MuiAlert-message': { width: '100%' },
        }}
      >
        <Box>
          <Typography variant="body2" fontWeight={600}>
            Override logged
          </Typography>
          <Typography variant="caption" color="text.secondary">
            {violation?.creditor_name || 'Item'} added despite Copilot advice
            {overrideCount > 1 && ` (${overrideCount} overrides this session)`}
          </Typography>
        </Box>
      </Alert>
    </Snackbar>
  );
}
