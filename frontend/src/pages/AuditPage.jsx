/**
 * Credit Engine 2.0 - Audit Page
 * Displays audit results and violation selection
 */
import React, { useEffect } from 'react';
import { useParams, useNavigate } from 'react-router-dom';
import {
  Container,
  Box,
  Button,
  CircularProgress,
  Alert,
} from '@mui/material';
import ArrowBackIcon from '@mui/icons-material/ArrowBack';
import ArrowForwardIcon from '@mui/icons-material/ArrowForward';
import { ReportSummary, ViolationList } from '../components';
import { useReportStore, useViolationStore } from '../state';

const AuditPage = () => {
  const { reportId } = useParams();
  const navigate = useNavigate();
  const { currentReport, fetchReport } = useReportStore();
  const {
    auditResult,
    violations,
    selectedViolationIds,
    isLoading,
    error,
    fetchAuditResults,
    clearViolations,
  } = useViolationStore();

  useEffect(() => {
    if (reportId) {
      // Clear old violations before fetching new report data
      clearViolations();
      // Fetch both report and audit results
      fetchReport(reportId);
      fetchAuditResults(reportId);
    }
  }, [reportId, fetchReport, fetchAuditResults, clearViolations]);

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
          <CircularProgress />
        </Box>
      </Container>
    );
  }

  return (
    <Container maxWidth="lg">
      <Box sx={{ py: 4 }}>
        {error && (
          <Alert severity="error" sx={{ mb: 3 }}>
            {error}
          </Alert>
        )}

        {/* Create Dispute Letter button at top */}
        {violations.length > 0 && (
          <Box sx={{ display: 'flex', justifyContent: 'center', mb: 3 }}>
            <Button
              variant="contained"
              size="large"
              endIcon={<ArrowForwardIcon />}
              onClick={handleContinue}
              disabled={selectedViolationIds.length === 0}
              sx={{ px: 4, py: 1.5 }}
            >
              Create Dispute Letter ({selectedViolationIds.length} items)
            </Button>
          </Box>
        )}

        <ReportSummary report={currentReport} auditResult={auditResult} />

        <Box sx={{ mt: 4 }}>
          <ViolationList />
        </Box>

        <Box sx={{ display: 'flex', justifyContent: 'flex-start', mt: 4 }}>
          <Button
            variant="outlined"
            startIcon={<ArrowBackIcon />}
            onClick={handleBack}
          >
            Upload New Report
          </Button>
        </Box>
      </Box>
    </Container>
  );
};

export default AuditPage;
