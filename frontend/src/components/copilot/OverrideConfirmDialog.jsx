/**
 * OverrideConfirmDialog - First-override confirmation dialog
 *
 * Shows when user first attempts to select a violation that
 * Copilot advises against. Requires acknowledgment before proceeding.
 *
 * "Copilot recommends. You decide."
 */
import React, { useState } from 'react';
import {
  Dialog,
  DialogTitle,
  DialogContent,
  DialogActions,
  Button,
  Typography,
  Box,
  FormControlLabel,
  Checkbox,
  Alert,
  Chip,
  Divider,
} from '@mui/material';
import WarningAmberIcon from '@mui/icons-material/WarningAmber';
import DoNotDisturbIcon from '@mui/icons-material/DoNotDisturb';

/**
 * First-override confirmation dialog
 * @param {Object} props
 * @param {boolean} props.open - Dialog open state
 * @param {Function} props.onClose - Close handler (cancel)
 * @param {Function} props.onConfirm - Confirm handler (proceed with override)
 * @param {Object} props.violation - Violation being overridden
 * @param {string} props.copilotAdvice - Copilot's advice ('advised_against' | 'deferred')
 * @param {string} props.rationale - Copilot's human_rationale for the advice
 */
export default function OverrideConfirmDialog({
  open,
  onClose,
  onConfirm,
  violation,
  copilotAdvice,
  rationale,
}) {
  const [acknowledged, setAcknowledged] = useState(false);

  const handleConfirm = () => {
    if (acknowledged) {
      onConfirm();
      setAcknowledged(false); // Reset for next time
    }
  };

  const handleClose = () => {
    setAcknowledged(false);
    onClose();
  };

  const isAdvisedAgainst = copilotAdvice === 'advised_against';

  return (
    <Dialog
      open={open}
      onClose={handleClose}
      maxWidth="sm"
      fullWidth
      PaperProps={{
        sx: {
          borderRadius: 2,
          borderTop: '4px solid',
          borderColor: isAdvisedAgainst ? 'error.main' : 'warning.main',
        },
      }}
    >
      <DialogTitle sx={{ pb: 1 }}>
        <Box sx={{ display: 'flex', alignItems: 'center', gap: 1 }}>
          <WarningAmberIcon color={isAdvisedAgainst ? 'error' : 'warning'} />
          <Typography variant="h6" component="span">
            Proceed Against Copilot Advice?
          </Typography>
        </Box>
      </DialogTitle>

      <DialogContent>
        {/* Violation Details */}
        <Box
          sx={{
            bgcolor: 'action.hover',
            p: 2,
            borderRadius: 1,
            mb: 2,
          }}
        >
          <Typography variant="subtitle2" gutterBottom>
            {violation?.creditor_name || 'Unknown Account'}
          </Typography>
          <Typography variant="body2" color="text.secondary">
            {violation?.account_number_masked}
          </Typography>
          <Box sx={{ mt: 1 }}>
            <Chip
              size="small"
              icon={<DoNotDisturbIcon />}
              label={isAdvisedAgainst ? 'Advised Against' : 'Deferred'}
              color={isAdvisedAgainst ? 'error' : 'warning'}
            />
          </Box>
        </Box>

        {/* Copilot Rationale */}
        <Alert
          severity={isAdvisedAgainst ? 'error' : 'warning'}
          icon={false}
          sx={{ mb: 2 }}
        >
          <Typography variant="subtitle2" gutterBottom>
            Copilot's Analysis:
          </Typography>
          <Typography variant="body2">
            {rationale || 'Copilot recommends against disputing this item at this time.'}
          </Typography>
        </Alert>

        <Divider sx={{ my: 2 }} />

        {/* Consequences */}
        <Typography variant="subtitle2" gutterBottom>
          What this means:
        </Typography>
        <Box component="ul" sx={{ pl: 2, mb: 2, '& li': { mb: 0.5 } }}>
          <Typography component="li" variant="body2" color="text.secondary">
            You are choosing to proceed independently of Copilot's recommendation
          </Typography>
          <Typography component="li" variant="body2" color="text.secondary">
            This decision will be logged for your records
          </Typography>
          <Typography component="li" variant="body2" color="text.secondary">
            Subsequent overrides in this session will show a brief notification instead
          </Typography>
        </Box>

        {/* Acknowledgment */}
        <FormControlLabel
          control={
            <Checkbox
              checked={acknowledged}
              onChange={(e) => setAcknowledged(e.target.checked)}
              color="primary"
            />
          }
          label={
            <Typography variant="body2">
              I understand Copilot's advice and choose to proceed independently
            </Typography>
          }
          sx={{ mt: 1 }}
        />
      </DialogContent>

      <DialogActions sx={{ px: 3, pb: 2 }}>
        <Button onClick={handleClose} color="inherit">
          Cancel
        </Button>
        <Button
          onClick={handleConfirm}
          variant="contained"
          color={isAdvisedAgainst ? 'error' : 'warning'}
          disabled={!acknowledged}
        >
          Proceed Independently
        </Button>
      </DialogActions>
    </Dialog>
  );
}
