/**
 * Credit Engine 2.0 - Batch Override Modal
 * Confirmation dialog when user proceeds with locked/recommended batch override
 */
import React from 'react';
import {
  Dialog,
  DialogTitle,
  DialogContent,
  DialogActions,
  Button,
  Typography,
  Box,
  Alert,
  List,
  ListItem,
  ListItemIcon,
  ListItemText,
} from '@mui/material';
import WarningAmberIcon from '@mui/icons-material/WarningAmber';
import CheckCircleOutlineIcon from '@mui/icons-material/CheckCircleOutline';
import LockOpenIcon from '@mui/icons-material/LockOpen';

export default function BatchOverrideModal({
  open,
  onClose,
  onConfirm,
  batch,
  overrideType, // 'proceed_locked' | 'skip_recommended'
}) {
  if (!batch) return null;

  const isLocked = overrideType === 'proceed_locked';

  const getTitle = () => {
    if (isLocked) {
      return 'Proceed Without Waiting?';
    }
    return 'Skip Recommended Batch?';
  };

  const getDescription = () => {
    if (isLocked) {
      return `This batch is locked because ${batch.lock_reason === 'pending_previous_wave'
        ? 'the previous wave hasn\'t received a response yet'
        : 'there are pending disputes awaiting bureau response'
      }. Proceeding now may reduce dispute effectiveness.`;
    }
    return 'This batch contains violations that Copilot recommends disputing. Skipping may delay your credit improvement progress.';
  };

  const getUnlockConditions = () => {
    if (!isLocked) return null;
    return (
      <Box sx={{ mt: 2 }}>
        <Typography variant="subtitle2" fontWeight={600} sx={{ mb: 1 }}>
          Normal Unlock Conditions:
        </Typography>
        <List dense disablePadding>
          {(batch.unlock_conditions || []).map((condition, idx) => (
            <ListItem key={idx} disableGutters sx={{ py: 0.5 }}>
              <ListItemIcon sx={{ minWidth: 32 }}>
                <CheckCircleOutlineIcon fontSize="small" color="success" />
              </ListItemIcon>
              <ListItemText
                primary={condition}
                primaryTypographyProps={{ variant: 'body2' }}
              />
            </ListItem>
          ))}
        </List>
      </Box>
    );
  };

  return (
    <Dialog
      open={open}
      onClose={onClose}
      maxWidth="sm"
      fullWidth
      PaperProps={{
        sx: { borderRadius: 3 }
      }}
    >
      <DialogTitle sx={{ pb: 1 }}>
        <Box sx={{ display: 'flex', alignItems: 'center', gap: 1.5 }}>
          {isLocked ? (
            <LockOpenIcon color="warning" />
          ) : (
            <WarningAmberIcon color="warning" />
          )}
          <Typography variant="h6" fontWeight={600}>
            {getTitle()}
          </Typography>
        </Box>
      </DialogTitle>

      <DialogContent>
        <Alert severity="warning" sx={{ mb: 2 }}>
          {getDescription()}
        </Alert>

        <Box sx={{ bgcolor: '#f8fafc', borderRadius: 2, p: 2 }}>
          <Typography variant="subtitle2" fontWeight={600} color="text.secondary" sx={{ mb: 1 }}>
            Batch Details
          </Typography>
          <Typography variant="body2">
            <strong>Bureau:</strong> {batch.bureau}
          </Typography>
          <Typography variant="body2">
            <strong>Wave:</strong> {batch.batch_number}
          </Typography>
          <Typography variant="body2">
            <strong>Strategy:</strong> {batch.goal_summary}
          </Typography>
          <Typography variant="body2">
            <strong>Violations:</strong> {batch.violation_ids?.length || 0}
          </Typography>
        </Box>

        {getUnlockConditions()}

        <Typography variant="body2" color="text.secondary" sx={{ mt: 2 }}>
          Your decision will be logged for your dispute history.
        </Typography>
      </DialogContent>

      <DialogActions sx={{ px: 3, pb: 3 }}>
        <Button
          onClick={onClose}
          variant="outlined"
          sx={{ borderRadius: 2 }}
        >
          Wait for Unlock
        </Button>
        <Button
          onClick={onConfirm}
          variant="contained"
          color="warning"
          sx={{ borderRadius: 2 }}
        >
          {isLocked ? 'Proceed Anyway' : 'Skip Batch'}
        </Button>
      </DialogActions>
    </Dialog>
  );
}
