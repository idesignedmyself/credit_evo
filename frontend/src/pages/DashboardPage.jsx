/**
 * Credit Engine 2.0 - Dashboard Page
 * Redirects to the most recent report's audit page, or shows empty state
 */
import React, { useEffect, useState } from 'react';
import { Navigate, useNavigate } from 'react-router-dom';
import {
  Box,
  Typography,
  Paper,
  Button,
} from '@mui/material';
import AddIcon from '@mui/icons-material/Add';
import useReportStore from '../state/reportStore';

const DashboardPage = () => {
  const navigate = useNavigate();
  const { latestReportId, fetchLatestReportId } = useReportStore();
  const [isChecking, setIsChecking] = useState(true);
  const [hasNoReports, setHasNoReports] = useState(false);

  useEffect(() => {
    // If we already have a latestReportId, no need to fetch
    if (latestReportId) {
      setIsChecking(false);
      return;
    }

    // Otherwise, fetch to check if there are any reports
    const checkReports = async () => {
      const reportId = await fetchLatestReportId();
      setIsChecking(false);
      if (!reportId) {
        setHasNoReports(true);
      }
    };

    checkReports();
  }, [latestReportId, fetchLatestReportId]);

  // If we have a latestReportId, redirect immediately via Navigate component
  if (latestReportId) {
    return <Navigate to={`/audit/${latestReportId}`} replace />;
  }

  // Still checking - render nothing to prevent flicker
  if (isChecking) {
    return null;
  }

  // No reports - show empty state
  if (hasNoReports) {
    return (
      <Box>
        <Typography variant="h4" sx={{ mb: 4, fontWeight: 'bold' }}>
          Dashboard
        </Typography>

        <Paper sx={{ p: 6, textAlign: 'center', borderRadius: 3 }}>
          <Typography variant="h6" color="text.secondary" sx={{ mb: 2 }}>
            No credit reports uploaded yet
          </Typography>
          <Typography variant="body2" color="text.secondary" sx={{ mb: 3 }}>
            Upload your first credit report to see your score summary and violations
          </Typography>
          <Button
            variant="contained"
            startIcon={<AddIcon />}
            onClick={() => navigate('/upload')}
            size="large"
            disableElevation
          >
            Upload Your First Report
          </Button>
        </Paper>
      </Box>
    );
  }

  return null;
};

export default DashboardPage;
