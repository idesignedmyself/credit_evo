/**
 * Credit Engine 2.0 - Audit Page
 * Displays audit results with bureau score dashboard and violations
 * Layout: KPIs -> Compact Filters -> Action Bar -> Violations List
 */
import React, { useEffect, useMemo } from 'react';
import { useParams, useNavigate } from 'react-router-dom';
import {
  Box,
  Button,
  Alert,
  Paper,
  Typography,
} from '@mui/material';
import ArrowForwardIcon from '@mui/icons-material/ArrowForward';
import ScoreDashboard from '../components/ScoreDashboard';
import AuditSkeleton from '../components/AuditSkeleton';
import CompactFilterBar from '../components/CompactFilterBar';
import { ViolationList } from '../components';
import { useReportStore, useViolationStore } from '../state';
import { useCreditFilter } from '../hooks/useCreditFilter';

const AuditPage = () => {
  const { reportId } = useParams();
  const navigate = useNavigate();
  const { currentReport, fetchReport } = useReportStore();
  const {
    violations,
    selectedViolationIds,
    isLoading,
    error,
    fetchAuditResults,
  } = useViolationStore();

  // Use filter hook at page level for CompactFilterBar
  const {
    filters,
    filterOptions,
    toggleFilter,
    clearFilters,
    hasActiveFilters,
    totalCount,
    filteredCount,
  } = useCreditFilter(violations);

  useEffect(() => {
    // Fetch data for this report - stores handle their own caching
    // Each store checks if it already has data for this reportId
    if (reportId) {
      fetchReport(reportId);
      fetchAuditResults(reportId);
    }
  }, [reportId]); // Only depend on reportId - store state is checked inside

  // Extract scores from report data (backend returns credit_scores)
  const scores = useMemo(() => {
    if (!currentReport?.credit_scores) return {};
    return currentReport.credit_scores;
  }, [currentReport]);

  // Calculate stats
  const stats = useMemo(() => {
    const totalAccounts = currentReport?.accounts?.length || 0;
    const violationsFound = violations?.length || 0;

    // Count accounts with violations
    const accountsWithViolations = new Set(
      violations.map(v => v.account_id).filter(Boolean)
    ).size;

    const cleanAccounts = Math.max(0, totalAccounts - accountsWithViolations);

    // Count critical (HIGH severity) violations
    const criticalViolations = violations.filter(
      v => v.severity === 'HIGH' || v.severity === 'CRITICAL'
    ).length;

    return {
      totalAccounts,
      violationsFound,
      cleanAccounts,
      criticalViolations,
    };
  }, [currentReport, violations]);

  const handleContinue = () => {
    navigate(`/letter/${reportId}`);
  };

  // Show skeleton on first load (no cached data), show real content instantly if cached
  if (isLoading && violations.length === 0) {
    return <AuditSkeleton />;
  }

  return (
    <Box>
      {error && (
        <Alert severity="error" sx={{ mb: 3, borderRadius: 2 }}>
          {error}
        </Alert>
      )}

      {/* LEVEL 1: Score Dashboard */}
      <ScoreDashboard scores={scores} />

      {/* LEVEL 2: Compact Filter Bar with Stats */}
      {violations.length > 0 && (
        <CompactFilterBar
          filters={filters}
          filterOptions={filterOptions}
          toggleFilter={toggleFilter}
          clearFilters={clearFilters}
          hasActiveFilters={hasActiveFilters}
          filteredCount={filteredCount}
          totalCount={totalCount}
          stats={stats}
        />
      )}

      {/* LEVEL 3: Action Bar (original styling) */}
      {violations.length > 0 && (
        <Paper
          elevation={0}
          sx={{
            p: 2,
            mb: 3,
            bgcolor: '#e3f2fd',
            border: '1px solid #bbdefb',
            borderRadius: 2,
            display: 'flex',
            justifyContent: 'space-between',
            alignItems: 'center',
          }}
        >
          <Box>
            <Typography variant="subtitle1" color="primary.main" sx={{ fontWeight: 'bold' }}>
              Ready to Generate
            </Typography>
            <Typography variant="caption" color="text.secondary">
              {selectedViolationIds.length} violations selected
            </Typography>
          </Box>
          <Button
            variant="contained"
            size="large"
            endIcon={<ArrowForwardIcon />}
            onClick={handleContinue}
            disabled={selectedViolationIds.length === 0}
            disableElevation
          >
            Generate Letter
          </Button>
        </Paper>
      )}

      {/* LEVEL 4: Violations List */}
      <ViolationList hideFilters hideHeader />
    </Box>
  );
};

export default AuditPage;
