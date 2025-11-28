/**
 * Credit Engine 2.0 - Upload Page
 * Main entry point for uploading credit reports
 */
import React from 'react';
import { useNavigate } from 'react-router-dom';
import {
  Container,
  Box,
  Typography,
  Paper,
  Stepper,
  Step,
  StepLabel,
} from '@mui/material';
import { FileUploader } from '../components';

const steps = ['Upload Report', 'Review Violations', 'Generate Letter'];

const UploadPage = () => {
  const navigate = useNavigate();

  const handleUploadSuccess = (result) => {
    // Navigate to audit page with the report ID
    navigate(`/audit/${result.report_id}`);
  };

  return (
    <Container maxWidth="md">
      <Box sx={{ py: 4 }}>
        <Typography variant="h4" component="h1" gutterBottom align="center">
          Credit Engine 2.0
        </Typography>
        <Typography variant="subtitle1" color="text.secondary" align="center" sx={{ mb: 4 }}>
          Upload your credit report to identify and dispute inaccuracies
        </Typography>

        <Stepper activeStep={0} sx={{ mb: 4 }}>
          {steps.map((label) => (
            <Step key={label}>
              <StepLabel>{label}</StepLabel>
            </Step>
          ))}
        </Stepper>

        <FileUploader onUploadSuccess={handleUploadSuccess} />

        <Paper sx={{ p: 3, mt: 4, backgroundColor: 'grey.50' }}>
          <Typography variant="h6" gutterBottom>
            How It Works
          </Typography>
          <Box component="ol" sx={{ pl: 2 }}>
            <li>
              <Typography variant="body2" sx={{ mb: 1 }}>
                <strong>Upload your credit report</strong> - We accept HTML reports from IdentityIQ or similar services
              </Typography>
            </li>
            <li>
              <Typography variant="body2" sx={{ mb: 1 }}>
                <strong>Review detected violations</strong> - Our engine identifies Metro 2 and FCRA compliance issues
              </Typography>
            </li>
            <li>
              <Typography variant="body2" sx={{ mb: 1 }}>
                <strong>Generate dispute letter</strong> - Create a professional dispute letter citing specific violations
              </Typography>
            </li>
          </Box>
        </Paper>

        <Box sx={{ mt: 4, textAlign: 'center' }}>
          <Typography variant="caption" color="text.secondary">
            Your data is processed locally and never stored permanently.
            <br />
            Credit Engine 2.0 uses FCRA-compliant violation detection.
          </Typography>
        </Box>
      </Box>
    </Container>
  );
};

export default UploadPage;
