/**
 * Credit Engine 2.0 - Audit Page
 * Displays audit results and violation selection
 */
import React, { useEffect } from 'react';
import { useParams, useNavigate } from 'react-router-dom';
import {
  Container,
  Box,
  Typography,
  Button,
  Stepper,
  Step,
  StepLabel,
  CircularProgress,
  Alert,
} from '@mui/material';
import ArrowBackIcon from '@mui/icons-material/ArrowBack';
import ArrowForwardIcon from '@mui/icons-material/ArrowForward';
import { ReportSummary, ViolationList } from '../components';
import { useReportStore, useViolationStore } from '../state';

const steps = ['Upload Report', 'Review Violations', 'Generate Letter'];

const AuditPage = () => {
  const { reportId } = useParams();
  const navigate = useNavigate();
  const { currentReport } = useReportStore();
  const {
    auditResult,
    violations,
    selectedViolationIds,
    isLoading,
    error,
    fetchAuditResults,
  } = useViolationStore();

  useEffect(() => {
    if (reportId) {
      fetchAuditResults(reportId);
    }
  }, [reportId, fetchAuditResults]);

  const handleBack = () => {
    navigate('/upload');
  };

  const handleContinue = () => {
    navigate(`/letter/${reportId}`);
  };

  if (isLoading) {
    return (
      <Container maxWidth="md">
        <Box sx={{ py: 4, textAlign: 'center' }}>
          <CircularProgress sx={{ mb: 2 }} />
          <Typography>Analyzing your credit report...</Typography>
        </Box>
      </Container>
    );
  }

  return (
    <Container maxWidth="lg">
      <Box sx={{ py: 4 }}>
        <Typography variant="h4" component="h1" gutterBottom align="center">
          Credit Engine 2.0
        </Typography>

        <Stepper activeStep={1} sx={{ mb: 4 }}>
          {steps.map((label) => (
            <Step key={label}>
              <StepLabel>{label}</StepLabel>
            </Step>
          ))}
        </Stepper>

        {error && (
          <Alert severity="error" sx={{ mb: 3 }}>
            {error}
          </Alert>
        )}

        <ReportSummary report={currentReport} auditResult={auditResult} />

        <Box sx={{ mt: 4 }}>
          <ViolationList />
        </Box>

        {violations.length > 0 && selectedViolationIds.length === 0 && (
          <Alert severity="info" sx={{ mt: 4, mb: 2 }}>
            Select at least one violation to create your dispute letter.
          </Alert>
        )}

        <Box sx={{ display: 'flex', justifyContent: 'space-between', mt: violations.length > 0 && selectedViolationIds.length === 0 ? 0 : 4 }}>
          <Button
            variant="outlined"
            startIcon={<ArrowBackIcon />}
            onClick={handleBack}
          >
            Upload New Report
          </Button>

          <Button
            variant="contained"
            endIcon={<ArrowForwardIcon />}
            onClick={handleContinue}
            disabled={selectedViolationIds.length === 0}
          >
            Create Dispute Letter ({selectedViolationIds.length} items)
          </Button>
        </Box>
      </Box>
    </Container>
  );
};

export default AuditPage;
