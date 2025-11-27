/**
 * Credit Engine 2.0 - Report Summary Component
 * Displays parsed report overview and statistics
 */
import React from 'react';
import {
  Box,
  Paper,
  Typography,
  Grid,
  Chip,
  Divider,
} from '@mui/material';
import AccountBalanceIcon from '@mui/icons-material/AccountBalance';
import WarningIcon from '@mui/icons-material/Warning';
import CheckCircleIcon from '@mui/icons-material/CheckCircle';
import CalendarTodayIcon from '@mui/icons-material/CalendarToday';
import { formatDate } from '../utils';

const StatCard = ({ icon, label, value, color = 'primary' }) => (
  <Paper sx={{ p: 2, textAlign: 'center' }}>
    <Box sx={{ color: `${color}.main`, mb: 1 }}>
      {icon}
    </Box>
    <Typography variant="h4" sx={{ fontWeight: 'bold' }}>
      {value}
    </Typography>
    <Typography variant="body2" color="text.secondary">
      {label}
    </Typography>
  </Paper>
);

const BureauChip = ({ bureau }) => {
  const colors = {
    transunion: '#0066CC',
    experian: '#CC0000',
    equifax: '#006600',
  };

  return (
    <Chip
      label={bureau?.toUpperCase() || 'Unknown'}
      sx={{
        backgroundColor: colors[bureau?.toLowerCase()] || '#666',
        color: 'white',
        fontWeight: 'bold',
      }}
    />
  );
};

const ReportSummary = ({ report, auditResult }) => {
  if (!report && !auditResult) {
    return null;
  }

  const accountsCount = auditResult?.total_accounts_audited || report?.accounts_found || 0;
  const violationsCount = auditResult?.total_violations_found || report?.violations_found || 0;
  const cleanCount = auditResult?.clean_accounts?.length || 0;
  const bureau = report?.bureau || auditResult?.bureau;
  const reportDate = report?.report_date || report?.parse_timestamp;

  return (
    <Box>
      <Paper sx={{ p: 3, mb: 3 }}>
        <Box sx={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', mb: 2 }}>
          <Typography variant="h5" sx={{ fontWeight: 'bold' }}>
            Credit Report Summary
          </Typography>
          <BureauChip bureau={bureau} />
        </Box>

        <Divider sx={{ my: 2 }} />

        <Grid container spacing={3}>
          <Grid item xs={6} sm={3}>
            <StatCard
              icon={<AccountBalanceIcon fontSize="large" />}
              label="Total Accounts"
              value={accountsCount}
              color="primary"
            />
          </Grid>
          <Grid item xs={6} sm={3}>
            <StatCard
              icon={<WarningIcon fontSize="large" />}
              label="Violations Found"
              value={violationsCount}
              color="error"
            />
          </Grid>
          <Grid item xs={6} sm={3}>
            <StatCard
              icon={<CheckCircleIcon fontSize="large" />}
              label="Clean Accounts"
              value={cleanCount}
              color="success"
            />
          </Grid>
          <Grid item xs={6} sm={3}>
            <StatCard
              icon={<CalendarTodayIcon fontSize="large" />}
              label="Report Date"
              value={reportDate ? formatDate(reportDate, { month: 'short', day: 'numeric' }) : 'N/A'}
              color="info"
            />
          </Grid>
        </Grid>
      </Paper>

      {violationsCount > 0 && (
        <Paper sx={{ p: 2, backgroundColor: 'warning.light' }}>
          <Typography variant="body1">
            <strong>{violationsCount} violations</strong> were detected that may be disputed.
            Review and select the violations you want to include in your dispute letter.
          </Typography>
        </Paper>
      )}

      {violationsCount === 0 && (
        <Paper sx={{ p: 2, backgroundColor: 'success.light' }}>
          <Typography variant="body1">
            <strong>No violations detected.</strong> Your credit report appears to be accurate.
          </Typography>
        </Paper>
      )}
    </Box>
  );
};

export default ReportSummary;
