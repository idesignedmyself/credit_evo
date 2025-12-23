/**
 * Credit Engine 2.0 - Audit Page
 * Displays audit results with bureau score dashboard and violations
 * Layout: KPIs -> Compact Filters -> Action Bar -> Violations List
 */
import React, { useEffect, useMemo, useState } from 'react';
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
import { CopilotStatusCard, FeatureGate } from '../components/copilot';
import { useReportStore, useViolationStore } from '../state';
import { useCreditFilter } from '../hooks/useCreditFilter';

const AuditPage = () => {
  const { reportId } = useParams();
  const navigate = useNavigate();
  const { currentReport, fetchReport } = useReportStore();
  const {
    violations,
    discrepancies,
    selectedViolationIds,
    isLoading,
    error,
    fetchAuditResults,
  } = useViolationStore();

  // Tab state lifted from ViolationList for filter coordination
  const [activeTab, setActiveTab] = useState('all');

  // Use filter hook at page level for CompactFilterBar
  const {
    filters,
    filterOptions: violationFilterOptions,
    toggleFilter,
    clearFilters,
    hasActiveFilters,
    totalCount,
    filteredCount,
    searchTerm,
    setSearchTerm,
  } = useCreditFilter(violations);

  // Extract discrepancy categories for Cross-Bureau tab
  const discrepancyFilterOptions = useMemo(() => {
    if (!discrepancies || discrepancies.length === 0) {
      return { bureaus: [], severities: [], categories: [], accounts: [] };
    }

    const bureaus = [...new Set(
      discrepancies.flatMap(d => d.values_by_bureau ? Object.keys(d.values_by_bureau) : [])
    )].filter(Boolean);
    const severities = [...new Set(discrepancies.map(d => d.severity).filter(Boolean))];
    const categories = [...new Set(discrepancies.map(d => d.violation_type).filter(Boolean))];
    const accounts = [...new Set(discrepancies.map(d => d.creditor_name).filter(Boolean))].sort();

    return { bureaus, severities, categories, accounts };
  }, [discrepancies]);

  // Dynamic filter options based on active tab
  const filterOptions = useMemo(() => {
    if (activeTab === 'crossbureau') {
      return discrepancyFilterOptions;
    }
    return violationFilterOptions;
  }, [activeTab, violationFilterOptions, discrepancyFilterOptions]);

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

      {/* LEVEL 1.5: Copilot Status Card */}
      <FeatureGate feature="copilot">
        <CopilotStatusCard reportId={reportId} />
      </FeatureGate>

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
          searchTerm={searchTerm}
          setSearchTerm={setSearchTerm}
        />
      )}

      {/* LEVEL 3: Action Bar */}
      {violations.length > 0 && (
        <Paper
          elevation={0}
          sx={{
            p: 2,
            mb: 3,
            bgcolor: 'white',
            borderRadius: 3,
            boxShadow: '0 2px 8px rgba(0,0,0,0.08)',
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
      <ViolationList hideFilters hideHeader activeTab={activeTab} onTabChange={setActiveTab} />
    </Box>
  );
};

export default AuditPage;
