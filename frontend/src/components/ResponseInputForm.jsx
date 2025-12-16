/**
 * Response Input Form
 * Form for logging entity responses to disputes
 */
import React, { useState } from 'react';
import {
  Box,
  Paper,
  Typography,
  TextField,
  Select,
  MenuItem,
  FormControl,
  InputLabel,
  Button,
  Checkbox,
  FormControlLabel,
  Alert,
  Divider,
  Collapse,
  CircularProgress,
} from '@mui/material';
import { DatePicker } from '@mui/x-date-pickers/DatePicker';
import { LocalizationProvider } from '@mui/x-date-pickers/LocalizationProvider';
import { AdapterDayjs } from '@mui/x-date-pickers/AdapterDayjs';
import dayjs from 'dayjs';
import {
  ENTITY_TYPES,
  RESPONSE_TYPES,
  logResponse,
} from '../api/disputeApi';

const ResponseInputForm = ({ disputeId, onResponseLogged, onCancel }) => {
  const [formData, setFormData] = useState({
    response_type: '',
    response_date: dayjs(),
    updated_fields: null,
    rejection_reason: '',
    has_5_day_notice: null,
    has_specific_reason: null,
    has_missing_info_request: null,
  });
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState(null);
  const [success, setSuccess] = useState(null);

  const handleChange = (field) => (event) => {
    const value = event.target?.value ?? event;
    setFormData((prev) => ({ ...prev, [field]: value }));
  };

  const handleCheckboxChange = (field) => (event) => {
    setFormData((prev) => ({ ...prev, [field]: event.target.checked }));
  };

  const handleSubmit = async (e) => {
    e.preventDefault();
    setLoading(true);
    setError(null);

    try {
      const payload = {
        response_type: formData.response_type,
        response_date: formData.response_date?.format('YYYY-MM-DD'),
      };

      // Add rejection fields if applicable
      if (formData.response_type === 'REJECTED') {
        payload.rejection_reason = formData.rejection_reason;
        payload.has_5_day_notice = formData.has_5_day_notice;
        payload.has_specific_reason = formData.has_specific_reason;
        payload.has_missing_info_request = formData.has_missing_info_request;
      }

      const result = await logResponse(disputeId, payload);
      setSuccess('Response logged successfully');

      if (onResponseLogged) {
        onResponseLogged(result);
      }
    } catch (err) {
      setError(err.message || 'Failed to log response');
    } finally {
      setLoading(false);
    }
  };

  const showRejectionFields = formData.response_type === 'REJECTED';

  return (
    <LocalizationProvider dateAdapter={AdapterDayjs}>
      <Paper sx={{ p: 3 }}>
        <Typography variant="h6" gutterBottom>
          Log Entity Response
        </Typography>
        <Typography variant="body2" color="text.secondary" sx={{ mb: 3 }}>
          Record the response received from the entity. The system will automatically
          evaluate the response and create any applicable violations.
        </Typography>

        {error && (
          <Alert severity="error" sx={{ mb: 2 }}>
            {error}
          </Alert>
        )}

        {success && (
          <Alert severity="success" sx={{ mb: 2 }}>
            {success}
          </Alert>
        )}

        <form onSubmit={handleSubmit}>
          <Box sx={{ display: 'flex', flexDirection: 'column', gap: 2 }}>
            {/* Response Type */}
            <FormControl fullWidth required>
              <InputLabel>Response Type</InputLabel>
              <Select
                value={formData.response_type}
                onChange={handleChange('response_type')}
                label="Response Type"
              >
                {Object.entries(RESPONSE_TYPES).map(([key, { value, label, description }]) => (
                  <MenuItem key={key} value={value}>
                    <Box>
                      <Typography variant="body1">{label}</Typography>
                      <Typography variant="caption" color="text.secondary">
                        {description}
                      </Typography>
                    </Box>
                  </MenuItem>
                ))}
              </Select>
            </FormControl>

            {/* Response Date */}
            <DatePicker
              label="Response Date"
              value={formData.response_date}
              onChange={handleChange('response_date')}
              maxDate={dayjs()}
              slotProps={{
                textField: {
                  fullWidth: true,
                  required: true,
                },
              }}
            />

            {/* Rejection-specific fields */}
            <Collapse in={showRejectionFields}>
              <Box sx={{ display: 'flex', flexDirection: 'column', gap: 2, mt: 1 }}>
                <Divider>
                  <Typography variant="caption" color="text.secondary">
                    Rejection Details (FCRA § 611(a)(3))
                  </Typography>
                </Divider>

                <TextField
                  label="Rejection Reason Given"
                  value={formData.rejection_reason}
                  onChange={handleChange('rejection_reason')}
                  multiline
                  rows={2}
                  fullWidth
                  helperText="What reason did the entity give for rejecting the dispute?"
                />

                <Typography variant="body2" color="text.secondary">
                  Did the entity comply with procedural requirements?
                </Typography>

                <FormControlLabel
                  control={
                    <Checkbox
                      checked={formData.has_5_day_notice || false}
                      onChange={handleCheckboxChange('has_5_day_notice')}
                    />
                  }
                  label="Received 5-day notice of rejection"
                />

                <FormControlLabel
                  control={
                    <Checkbox
                      checked={formData.has_specific_reason || false}
                      onChange={handleCheckboxChange('has_specific_reason')}
                    />
                  }
                  label="Notice included specific reason for rejection"
                />

                <FormControlLabel
                  control={
                    <Checkbox
                      checked={formData.has_missing_info_request || false}
                      onChange={handleCheckboxChange('has_missing_info_request')}
                    />
                  }
                  label="Notice identified what information is needed"
                />

                <Alert severity="info" variant="outlined">
                  <Typography variant="body2">
                    Under FCRA § 611(a)(3), a CRA that determines a dispute is frivolous
                    must provide notice within 5 business days that includes the specific
                    reason and identifies any information needed to investigate.
                  </Typography>
                </Alert>
              </Box>
            </Collapse>

            {/* Action Buttons */}
            <Box sx={{ display: 'flex', gap: 2, mt: 2 }}>
              <Button
                type="submit"
                variant="contained"
                disabled={loading || !formData.response_type}
                sx={{ flex: 1 }}
              >
                {loading ? <CircularProgress size={24} /> : 'Log Response'}
              </Button>
              {onCancel && (
                <Button variant="outlined" onClick={onCancel}>
                  Cancel
                </Button>
              )}
            </Box>
          </Box>
        </form>
      </Paper>
    </LocalizationProvider>
  );
};

export default ResponseInputForm;
