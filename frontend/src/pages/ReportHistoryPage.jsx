/**
 * Credit Engine 2.0 - Report History Page
 * View, select, and delete uploaded reports
 */
import React, { useEffect, useState } from 'react';
import { useNavigate } from 'react-router-dom';
import {
  Container,
  Box,
  Typography,
  Paper,
  Table,
  TableBody,
  TableCell,
  TableContainer,
  TableHead,
  TableRow,
  Button,
  IconButton,
  Alert,
  CircularProgress,
  Chip,
} from '@mui/material';
import DeleteIcon from '@mui/icons-material/Delete';
import VisibilityIcon from '@mui/icons-material/Visibility';
import AddIcon from '@mui/icons-material/Add';
import DeleteSweepIcon from '@mui/icons-material/DeleteSweep';
import { reportApi } from '../api';
import { SavedLetters, FileUploader } from '../components';
import { useViolationStore } from '../state';

const ReportHistoryPage = () => {
  const navigate = useNavigate();
  const { clearViolations } = useViolationStore();
  const [reports, setReports] = useState([]);
  const [isLoading, setIsLoading] = useState(true);
  const [error, setError] = useState(null);
  const [deletingId, setDeletingId] = useState(null);

  const fetchReports = async () => {
    setIsLoading(true);
    setError(null);
    try {
      const data = await reportApi.listReports();
      setReports(data);
    } catch (err) {
      setError(err.message || 'Failed to load reports');
    } finally {
      setIsLoading(false);
    }
  };

  useEffect(() => {
    fetchReports();
  }, []);

  const handleView = (reportId) => {
    navigate(`/audit/${reportId}`);
  };

  const handleDelete = async (reportId) => {
    if (!window.confirm('Delete this report? This action cannot be undone.')) {
      return;
    }
    setDeletingId(reportId);
    try {
      await reportApi.deleteReport(reportId);
      setReports(reports.filter((r) => r.report_id !== reportId));
      // Clear cached violations to prevent stale data
      clearViolations();
    } catch (err) {
      setError(err.message || 'Failed to delete report');
    } finally {
      setDeletingId(null);
    }
  };

  const handleDeleteAll = async () => {
    if (!window.confirm('Delete ALL reports? This action cannot be undone.')) {
      return;
    }
    setIsLoading(true);
    try {
      await reportApi.deleteAllReports();
      setReports([]);
      // Clear cached violations to prevent stale data
      clearViolations();
    } catch (err) {
      setError(err.message || 'Failed to delete reports');
    } finally {
      setIsLoading(false);
    }
  };

  const formatDate = (dateString) => {
    try {
      return new Date(dateString).toLocaleString();
    } catch {
      return dateString;
    }
  };

  return (
    <Container maxWidth="lg">
      <Box sx={{ py: 4 }}>
        <Box sx={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', mb: 3 }}>
          <Typography variant="h4" component="h1">
            Report History
          </Typography>
          <Box sx={{ display: 'flex', gap: 2 }}>
            {reports.length > 0 && (
              <Button
                variant="outlined"
                color="error"
                startIcon={<DeleteSweepIcon />}
                onClick={handleDeleteAll}
                disabled={isLoading}
              >
                Delete All
              </Button>
            )}
            <Button
              variant="contained"
              startIcon={<AddIcon />}
              onClick={() => navigate('/upload')}
            >
              Upload New Report
            </Button>
          </Box>
        </Box>

        {error && (
          <Alert severity="error" sx={{ mb: 3 }} onClose={() => setError(null)}>
            {error}
          </Alert>
        )}

        {isLoading ? (
          <Box sx={{ display: 'flex', justifyContent: 'center', py: 8 }}>
            <CircularProgress />
          </Box>
        ) : reports.length === 0 ? (
          <Paper sx={{ p: 4, textAlign: 'center' }}>
            <Typography variant="body1" color="text.secondary" sx={{ mb: 2 }}>
              No reports uploaded yet.
            </Typography>
            <Button
              variant="contained"
              startIcon={<AddIcon />}
              onClick={() => navigate('/upload')}
            >
              Upload Your First Report
            </Button>
          </Paper>
        ) : (
          <TableContainer component={Paper}>
            <Table>
              <TableHead>
                <TableRow>
                  <TableCell>Filename</TableCell>
                  <TableCell>Uploaded</TableCell>
                  <TableCell align="center">Accounts</TableCell>
                  <TableCell align="center">Violations</TableCell>
                  <TableCell align="right">Actions</TableCell>
                </TableRow>
              </TableHead>
              <TableBody>
                {reports.map((report) => (
                  <TableRow key={report.report_id} hover>
                    <TableCell>
                      <Typography variant="body2" fontWeight="medium">
                        {report.filename}
                      </Typography>
                    </TableCell>
                    <TableCell>
                      <Typography variant="body2" color="text.secondary">
                        {formatDate(report.uploaded)}
                      </Typography>
                    </TableCell>
                    <TableCell align="center">
                      <Chip label={report.accounts} size="small" />
                    </TableCell>
                    <TableCell align="center">
                      <Chip
                        label={report.violations}
                        size="small"
                        color={report.violations > 0 ? 'warning' : 'success'}
                      />
                    </TableCell>
                    <TableCell align="right">
                      <IconButton
                        color="primary"
                        onClick={() => handleView(report.report_id)}
                        title="View Report"
                      >
                        <VisibilityIcon />
                      </IconButton>
                      <IconButton
                        color="error"
                        onClick={() => handleDelete(report.report_id)}
                        disabled={deletingId === report.report_id}
                        title="Delete Report"
                      >
                        {deletingId === report.report_id ? (
                          <CircularProgress size={20} />
                        ) : (
                          <DeleteIcon />
                        )}
                      </IconButton>
                    </TableCell>
                  </TableRow>
                ))}
              </TableBody>
            </Table>
          </TableContainer>
        )}

        {/* Saved Letters Section */}
        <Box sx={{ mt: 4 }}>
          <Typography variant="h5" component="h2" sx={{ mb: 2 }}>
            Saved Letters
          </Typography>
          <SavedLetters />
        </Box>

        {/* Upload Section */}
        <Box sx={{ mt: 4 }}>
          <FileUploader onUploadSuccess={(result) => {
            fetchReports();
            navigate(`/audit/${result.report_id}`);
          }} />

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
      </Box>
    </Container>
  );
};

export default ReportHistoryPage;
