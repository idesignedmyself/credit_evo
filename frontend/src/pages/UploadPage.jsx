/**
 * Credit Engine 2.0 - Upload Page
 * Modern upload flow with dropzone
 */
import React from 'react';
import { useNavigate } from 'react-router-dom';
import {
  Container,
  Box,
  Typography,
  Paper,
} from '@mui/material';
import { FileUploader } from '../components';

const UploadPage = () => {
  const navigate = useNavigate();

  const handleUploadSuccess = (result) => {
    navigate(`/audit/${result.report_id}`);
  };

  return (
    <Container maxWidth="md" sx={{ py: 4 }}>
      {/* Page Header */}
      <Box sx={{ textAlign: 'center', mb: 4 }}>
        <Typography variant="h4" component="h1" gutterBottom sx={{ fontWeight: 'bold' }}>
          Upload Credit Report
        </Typography>
        <Typography variant="body1" color="text.secondary">
          Upload your credit report to identify and dispute inaccuracies
        </Typography>
      </Box>

      {/* File Uploader with Dropzone Styling */}
      <FileUploader onUploadSuccess={handleUploadSuccess} />

      {/* How It Works */}
      <Paper elevation={1} sx={{ mt: 4, p: 3, bgcolor: 'white', borderRadius: 3 }}>
        <Typography variant="h6" gutterBottom sx={{ fontWeight: 'bold' }}>
          How It Works
        </Typography>
        <Box component="ul" sx={{ pl: 2, m: 0 }}>
          <Typography component="li" variant="body2" sx={{ mb: 1 }}>
            <strong>Upload your credit report:</strong> We parse the HTML locally on your device.
          </Typography>
          <Typography component="li" variant="body2" sx={{ mb: 1 }}>
            <strong>Review detected violations:</strong> Our engine scans for Metro 2 and FCRA compliance errors.
          </Typography>
          <Typography component="li" variant="body2">
            <strong>Generate dispute letter:</strong> Create a professional letter citing specific legal codes.
          </Typography>
        </Box>
      </Paper>

      {/* Privacy Note */}
      <Box sx={{ mt: 4, textAlign: 'center' }}>
        <Typography variant="caption" color="text.secondary">
          Your data is processed securely. Credit Engine 2.0 uses FCRA-compliant violation detection.
        </Typography>
      </Box>
    </Container>
  );
};

export default UploadPage;
