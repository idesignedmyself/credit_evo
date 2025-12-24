/**
 * AdminDashboard - Main admin dashboard with key metrics
 * Read-only intelligence sourced from Execution Ledger
 */
import React, { useEffect } from 'react';
import { Box, Typography, Grid, Alert } from '@mui/material';
import PeopleIcon from '@mui/icons-material/People';
import MailIcon from '@mui/icons-material/Mail';
import DeleteIcon from '@mui/icons-material/Delete';
import VerifiedIcon from '@mui/icons-material/Verified';
import TrendingUpIcon from '@mui/icons-material/TrendingUp';
import WarningIcon from '@mui/icons-material/Warning';
import PendingIcon from '@mui/icons-material/Pending';
import PercentIcon from '@mui/icons-material/Percent';
import { StatCard } from '../../components/admin';
import { useAdminStore } from '../../state';

export default function AdminDashboard() {
  const { dashboardStats, isLoadingDashboard, error, fetchDashboardStats } = useAdminStore();

  useEffect(() => {
    fetchDashboardStats();
  }, [fetchDashboardStats]);

  return (
    <Box>
      {/* Header */}
      <Box sx={{ mb: 4 }}>
        <Typography variant="h4" sx={{ color: '#fff', fontWeight: 700, mb: 1 }}>
          Dashboard
        </Typography>
        <Typography variant="body1" sx={{ color: '#a2a2a2' }}>
          Real-time intelligence from the Execution Ledger
        </Typography>
      </Box>

      {/* Error Alert */}
      {error && (
        <Alert severity="error" sx={{ mb: 3, bgcolor: '#1a1a2e', color: '#ef4444' }}>
          {error}
        </Alert>
      )}

      {/* Stats Grid */}
      <Grid container spacing={3}>
        {/* Users */}
        <Grid item xs={12} sm={6} md={3}>
          <StatCard
            title="Total Users"
            value={dashboardStats?.total_users || 0}
            subtitle={`${dashboardStats?.active_users_30d || 0} active (30d)`}
            icon={PeopleIcon}
            loading={isLoadingDashboard}
            color="#3b82f6"
          />
        </Grid>

        {/* Letters Sent */}
        <Grid item xs={12} sm={6} md={3}>
          <StatCard
            title="Letters Sent"
            value={dashboardStats?.total_letters_sent || 0}
            subtitle={`${dashboardStats?.letters_sent_30d || 0} this month`}
            icon={MailIcon}
            loading={isLoadingDashboard}
            color="#8b5cf6"
          />
        </Grid>

        {/* Total Executions */}
        <Grid item xs={12} sm={6} md={3}>
          <StatCard
            title="Total Executions"
            value={dashboardStats?.total_executions || 0}
            subtitle="Authority moments"
            icon={TrendingUpIcon}
            loading={isLoadingDashboard}
            color="#10b981"
          />
        </Grid>

        {/* Pending Responses */}
        <Grid item xs={12} sm={6} md={3}>
          <StatCard
            title="Pending Responses"
            value={dashboardStats?.pending_responses || 0}
            subtitle="Awaiting entity reply"
            icon={PendingIcon}
            loading={isLoadingDashboard}
            color="#f59e0b"
          />
        </Grid>

        {/* Deletion Rate */}
        <Grid item xs={12} sm={6} md={3}>
          <StatCard
            title="Deletion Rate"
            value={`${dashboardStats?.deletion_rate || 0}%`}
            subtitle="Items removed from reports"
            icon={DeleteIcon}
            loading={isLoadingDashboard}
            color="#10b981"
          />
        </Grid>

        {/* Verification Rate */}
        <Grid item xs={12} sm={6} md={3}>
          <StatCard
            title="Verification Rate"
            value={`${dashboardStats?.verification_rate || 0}%`}
            subtitle="Items verified by bureau"
            icon={VerifiedIcon}
            loading={isLoadingDashboard}
            color="#ef4444"
          />
        </Grid>

        {/* Override Rate */}
        <Grid item xs={12} sm={6} md={3}>
          <StatCard
            title="Override Rate"
            value={`${dashboardStats?.override_rate || 0}%`}
            subtitle="Users overrode Copilot"
            icon={WarningIcon}
            loading={isLoadingDashboard}
            color="#f59e0b"
          />
        </Grid>

        {/* Success Rate (calculated) */}
        <Grid item xs={12} sm={6} md={3}>
          <StatCard
            title="Success Rate"
            value={`${Math.max(0, 100 - (dashboardStats?.verification_rate || 0)).toFixed(1)}%`}
            subtitle="Non-verified outcomes"
            icon={PercentIcon}
            loading={isLoadingDashboard}
            color="#e94560"
          />
        </Grid>
      </Grid>

      {/* Ledger Truth Notice */}
      <Box
        sx={{
          mt: 4,
          p: 2,
          bgcolor: '#16213e',
          border: '1px solid #0f3460',
          borderRadius: 2,
        }}
      >
        <Typography variant="caption" sx={{ color: '#6b7280' }}>
          All metrics derived from the immutable Execution Ledger. Data reflects real enforcement
          outcomes at the authority moment (confirm_mailing).
        </Typography>
      </Box>
    </Box>
  );
}
