/**
 * Credit Engine 2.0 - Score Dashboard Component
 * Displays bureau scores and summary statistics
 */
import React from 'react';
import { Box, Grid, Card, CardContent, Typography } from '@mui/material';
import AccountBalanceIcon from '@mui/icons-material/AccountBalance';
import WarningIcon from '@mui/icons-material/Warning';
import CheckCircleIcon from '@mui/icons-material/CheckCircle';
import ErrorIcon from '@mui/icons-material/Error';
import { BUREAU_COLORS } from '../theme';

// Reusable stat card component
function StatCard({ icon, value, label, color }) {
  return (
    <Card sx={{ display: 'flex', alignItems: 'center', p: 2, height: '100%' }}>
      <Box sx={{ mr: 2, color: color || 'primary.main' }}>{icon}</Box>
      <Box>
        <Typography variant="h5" sx={{ fontWeight: 'bold' }}>{value}</Typography>
        <Typography variant="body2" color="text.secondary">{label}</Typography>
      </Box>
    </Card>
  );
}

// Get score status text
function getScoreStatus(score) {
  if (!score || score === 0) return 'No Score';
  if (score >= 750) return 'Excellent';
  if (score >= 700) return 'Good';
  if (score >= 650) return 'Fair';
  if (score >= 600) return 'Poor';
  return 'Very Poor';
}

export default function ScoreDashboard({ scores = {}, stats = {} }) {
  // Default scores from report data
  const bureauScores = [
    {
      name: 'TransUnion',
      key: 'TU',
      score: scores.TU || scores.transunion || 0,
      color: BUREAU_COLORS.TU
    },
    {
      name: 'Experian',
      key: 'EXP',
      score: scores.EXP || scores.experian || 0,
      color: BUREAU_COLORS.EXP
    },
    {
      name: 'Equifax',
      key: 'EQ',
      score: scores.EQ || scores.equifax || 0,
      color: BUREAU_COLORS.EQ
    }
  ];

  // Calculate stats
  const totalAccounts = stats.totalAccounts || 0;
  const violationsFound = stats.violationsFound || 0;
  const cleanAccounts = stats.cleanAccounts || 0;
  const criticalViolations = stats.criticalViolations || 0;

  return (
    <Box sx={{ mb: 4 }}>
      <Typography variant="h5" sx={{ mb: 3, fontWeight: 'bold' }}>
        Credit Report Summary
      </Typography>

      {/* Bureau Scores Row */}
      <Grid container spacing={3} sx={{ mb: 3 }}>
        {bureauScores.map((bureau) => (
          <Grid item xs={12} sm={4} key={bureau.name}>
            <Card sx={{ borderTop: `6px solid ${bureau.color}`, height: '100%' }}>
              <CardContent sx={{ textAlign: 'center' }}>
                <Typography
                  variant="h2"
                  sx={{
                    color: bureau.score > 0 ? bureau.color : 'text.disabled',
                    fontWeight: 'bold'
                  }}
                >
                  {bureau.score > 0 ? bureau.score : '—'}
                </Typography>
                <Typography variant="subtitle1" sx={{ fontWeight: 600, color: 'text.secondary' }}>
                  {bureau.name}
                </Typography>
                <Typography
                  variant="caption"
                  sx={{
                    color: 'text.secondary',
                    textTransform: 'uppercase',
                    fontWeight: 500
                  }}
                >
                  {getScoreStatus(bureau.score)}
                </Typography>
              </CardContent>
            </Card>
          </Grid>
        ))}
      </Grid>

      {/* Stats Row */}
      <Grid container spacing={3}>
        <Grid item xs={12} sm={6} md={3}>
          <StatCard
            icon={<AccountBalanceIcon fontSize="large" />}
            value={totalAccounts}
            label="Total Accounts"
            color="primary.main"
          />
        </Grid>
        <Grid item xs={12} sm={6} md={3}>
          <StatCard
            icon={<WarningIcon fontSize="large" />}
            value={violationsFound}
            label="Violations Found"
            color="warning.main"
          />
        </Grid>
        <Grid item xs={12} sm={6} md={3}>
          <StatCard
            icon={<ErrorIcon fontSize="large" />}
            value={criticalViolations}
            label="Critical Issues"
            color="error.main"
          />
        </Grid>
        <Grid item xs={12} sm={6} md={3}>
          <StatCard
            icon={<CheckCircleIcon fontSize="large" />}
            value={cleanAccounts}
            label="Clean Accounts"
            color="success.main"
          />
        </Grid>
      </Grid>
    </Box>
  );
}

export { StatCard };
