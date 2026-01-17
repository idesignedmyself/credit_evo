/**
 * Credit Engine 2.0 - Violation List Component (Clean SPA Version)
 * Unified table layout with integrated tabs
 */

import React, { useState, useMemo } from 'react';
import { useNavigate } from 'react-router-dom';
import {
  Box,
  Typography,
  Paper,
  Tabs,
  Tab,
  Table,
  TableBody,
  TableCell,
  TableContainer,
  TableRow,
  Collapse,
  IconButton,
  CircularProgress,
  Alert
} from '@mui/material';
import ExpandMoreIcon from '@mui/icons-material/ExpandMore';
import ChevronRightIcon from '@mui/icons-material/ChevronRight';
import AutoAwesomeIcon from '@mui/icons-material/AutoAwesome';
import Chip from '@mui/material/Chip';

import {
  useViolationStore,
  useReportStore,
  useUIStore
} from '../state';

import { useCreditFilter } from '../hooks/useCreditFilter';
import ViolationToggle from './ViolationToggle';
import DiscrepancyToggle from './DiscrepancyToggle';
import AccountAccordion from './AccountAccordion';
import FilterToolbar from './FilterToolbar';
import { OverrideController, useOverrideController, RecommendedPlanTab } from './copilot';

/**
 * Collapsible row for Cross-Bureau and Accounts tabs
 */
const CollapsibleTableRow = ({ label, count, isExpanded, onToggle, children }) => (
  <>
    <TableRow
      onClick={onToggle}
      sx={{
        cursor: 'pointer',
        bgcolor: isExpanded ? '#f8fafc' : 'transparent',
        '&:hover': { bgcolor: '#f1f5f9' },
      }}
    >
      <TableCell sx={{ py: 2, fontWeight: 600, borderBottom: '1px solid', borderColor: 'divider' }}>
        <Box sx={{ display: 'flex', alignItems: 'center', gap: 1 }}>
          <IconButton size="small" sx={{ p: 0 }}>
            {isExpanded ? <ExpandMoreIcon fontSize="small" /> : <ChevronRightIcon fontSize="small" />}
          </IconButton>
          {label}
        </Box>
      </TableCell>
      <TableCell align="right" sx={{ py: 2, fontWeight: 500, color: 'text.secondary', width: 80, borderBottom: '1px solid', borderColor: 'divider' }}>
        {count}
      </TableCell>
    </TableRow>
    <TableRow>
      <TableCell colSpan={2} sx={{ p: 0, border: 'none' }}>
        <Collapse in={isExpanded} timeout="auto" unmountOnExit>
          <Box sx={{ pl: 4, pr: 2, py: 2, bgcolor: '#fafafa' }}>
            {children}
          </Box>
        </Collapse>
      </TableCell>
    </TableRow>
  </>
);

const ViolationList = ({ hideFilters = false, hideHeader = false, activeTab, onTabChange }) => {
  // Use controlled state if props provided, otherwise local state
  const [localGroupBy, setLocalGroupBy] = useState("all");
  const groupBy = activeTab !== undefined ? activeTab : localGroupBy;
  const setGroupBy = onTabChange || setLocalGroupBy;
  const [expandedItems, setExpandedItems] = useState({});
  const navigate = useNavigate();

  const {
    violations,
    discrepancies,
    selectedViolationIds,
    selectedDiscrepancyIds,
    toggleViolation,
    toggleDiscrepancy,
    isLoading,
    error
  } = useViolationStore();

  // Override flow controller for Copilot integration
  const overrideController = useOverrideController();

  /**
   * Handle violation toggle with Copilot override check
   * If Copilot advises against, shows dialog/toast before proceeding
   */
  const handleViolationToggle = (violationId) => {
    const violation = violations.find(v => v.violation_id === violationId);
    if (!violation) {
      toggleViolation(violationId);
      return;
    }

    // Check if this is selecting a violation that Copilot advises against
    const isCurrentlySelected = selectedViolationIds.includes(violationId);

    // Only check override when SELECTING (not deselecting)
    if (!isCurrentlySelected) {
      overrideController.checkOverride(
        violationId,
        violation,
        () => toggleViolation(violationId)
      );
    } else {
      // Deselecting - no override check needed
      toggleViolation(violationId);
    }
  };

  const { currentReport } = useReportStore();
  const accounts = currentReport?.accounts || [];

  // FILTERING ENGINE
  const {
    filteredData,
    filters,
    filterOptions,
    toggleFilter,
    clearFilters,
    hasActiveFilters,
    totalCount,
    filteredCount,
    searchTerm,
    setSearchTerm,
  } = useCreditFilter(violations);

  // Group discrepancies by account (with search and filter support)
  const groupedDiscrepancies = useMemo(() => {
    if (!discrepancies?.length) return {};
    const searchLower = searchTerm.toLowerCase().trim();

    return discrepancies.reduce((acc, d) => {
      // Apply search filter
      if (searchLower) {
        const nameMatch = d.creditor_name?.toLowerCase().includes(searchLower);
        const numberMatch = d.account_number_masked?.toLowerCase().includes(searchLower);
        if (!nameMatch && !numberMatch) return acc;
      }

      // Apply bureau filter - discrepancies use values_by_bureau object
      if (filters.bureaus.length > 0) {
        const discBureaus = d.values_by_bureau ? Object.keys(d.values_by_bureau).map(b => b.toLowerCase()) : [];
        const bureauMatch = filters.bureaus.some(b => discBureaus.includes(b.toLowerCase()));
        if (!bureauMatch) return acc;
      }

      // Apply severity filter (case-insensitive)
      if (filters.severities.length > 0) {
        const severityMatch = filters.severities.some(s =>
          s?.toLowerCase() === d.severity?.toLowerCase()
        );
        if (!severityMatch) return acc;
      }

      // Apply category/type filter (case-insensitive)
      if (filters.categories.length > 0) {
        const categoryMatch = filters.categories.some(c =>
          c?.toLowerCase() === d.violation_type?.toLowerCase()
        );
        if (!categoryMatch) return acc;
      }

      // Apply account filter
      if (filters.accounts.length > 0) {
        if (!filters.accounts.includes(d.creditor_name)) return acc;
      }

      const key = d.creditor_name || 'Unknown';
      if (!acc[key]) acc[key] = [];
      acc[key].push(d);
      return acc;
    }, {});
  }, [discrepancies, searchTerm, filters.bureaus, filters.severities, filters.categories, filters.accounts]);

  // Filter accounts for Tri-Merge tab (with search and filter support)
  const filteredAccounts = useMemo(() => {
    if (!accounts?.length) return [];
    const searchLower = searchTerm.toLowerCase().trim();

    return accounts.filter(a => {
      // Apply search filter
      if (searchLower) {
        const nameMatch = a.creditor_name?.toLowerCase().includes(searchLower);
        const numberMatch = a.account_number_masked?.toLowerCase().includes(searchLower);
        if (!nameMatch && !numberMatch) return false;
      }

      // Apply bureau filter - check if account has data for selected bureaus
      if (filters.bureaus.length > 0) {
        const accountBureaus = Object.keys(a.bureaus || {}).map(b => b.toLowerCase());
        const bureauMatch = filters.bureaus.some(b => accountBureaus.includes(b));
        if (!bureauMatch) return false;
      }

      // Apply account filter
      if (filters.accounts.length > 0) {
        if (!filters.accounts.includes(a.creditor_name)) return false;
      }

      return true;
    });
  }, [accounts, searchTerm, filters.bureaus, filters.accounts]);

  // Group ALL accounts with their violations (including clean accounts with 0 violations)
  // When filters are active, only show accounts that have matching violations
  // Search term filters by creditor name or account number
  const allAccountsGrouped = useMemo(() => {
    if (!accounts?.length) return {};

    const grouped = {};
    const searchLower = searchTerm.toLowerCase().trim();

    // Check if any filters are active (excluding search - search is handled separately)
    const filtersActive = filters.bureaus.length > 0 || filters.severities.length > 0 ||
                          filters.categories.length > 0 || filters.accounts.length > 0;

    // Helper to check if account matches search
    const matchesSearch = (account) => {
      if (!searchLower) return true;
      const nameMatch = account.creditor_name?.toLowerCase().includes(searchLower);
      const numberMatch = account.account_number_masked?.toLowerCase().includes(searchLower);
      return nameMatch || numberMatch;
    };

    // First, add all accounts as keys (even if they have no violations)
    // But only if no filters are active - otherwise we'll only add accounts with matching violations
    if (!filtersActive) {
      accounts.forEach(account => {
        // Apply search filter
        if (!matchesSearch(account)) return;

        const creditorName = account.creditor_name || 'Unknown';
        if (!grouped[creditorName]) {
          grouped[creditorName] = [];
        }
      });
    }

    // Then, add violations to their respective accounts
    // Use filteredData to respect active filters
    filteredData.forEach(violation => {
      // Apply search filter to violations too
      if (searchLower) {
        const nameMatch = violation.creditor_name?.toLowerCase().includes(searchLower);
        const numberMatch = violation.account_number_masked?.toLowerCase().includes(searchLower);
        if (!nameMatch && !numberMatch) return;
      }

      const creditorName = violation.creditor_name || 'Unknown';
      if (!grouped[creditorName]) {
        grouped[creditorName] = [];
      }
      grouped[creditorName].push(violation);
    });

    // Sort by creditor name
    const sorted = {};
    Object.keys(grouped).sort().forEach(key => {
      sorted[key] = grouped[key];
    });

    return sorted;
  }, [accounts, filteredData, filters.bureaus, filters.severities, filters.categories, filters.accounts, searchTerm]);

  const toggleExpanded = (key) => {
    setExpandedItems(prev => ({ ...prev, [key]: !prev[key] }));
  };

  if (isLoading) {
    return (
      <Box sx={{ display: 'flex', justifyContent: 'center', p: 4 }}>
        <CircularProgress />
      </Box>
    );
  }

  if (error) {
    return (
      <Alert severity="error" sx={{ mb: 2 }}>
        {error}
      </Alert>
    );
  }

  return (
    <Box>
      {/* FILTER TOOLBAR - only show if not hidden */}
      {!hideFilters && violations.length > 0 && (
        <FilterToolbar
          filters={filters}
          filterOptions={filterOptions}
          toggleFilter={toggleFilter}
          clearFilters={clearFilters}
          hasActiveFilters={hasActiveFilters}
          filteredCount={filteredCount}
          totalCount={totalCount}
          searchTerm={searchTerm}
          setSearchTerm={setSearchTerm}
        />
      )}

      {/* HEADER - only show if not hidden */}
      {!hideHeader && (
        <Typography
          variant="h6"
          sx={{
            fontWeight: 'bold',
            mb: 2,
            pb: 1,
            borderBottom: '3px solid',
            borderColor: 'primary.main',
          }}
        >
          {hasActiveFilters ? `${filteredCount} of ${totalCount}` : totalCount} Violations Found
        </Typography>
      )}

      {/* UNIFIED TABLE CONTAINER */}
      <TableContainer
        component={Paper}
        elevation={0}
        sx={{
          borderRadius: 3,
          boxShadow: '0 2px 8px rgba(0,0,0,0.08)',
          overflow: 'hidden',
        }}
      >
        {/* TABS IN HEADER WITH COUNT */}
        <Box sx={{
          bgcolor: '#f9fafb',
          borderBottom: '1px solid',
          borderColor: 'divider',
          display: 'flex',
          alignItems: 'center',
          justifyContent: 'space-between',
          pr: 2,
        }}>
          <Tabs
            value={groupBy}
            onChange={(e, v) => setGroupBy(v)}
            sx={{
              minHeight: 48,
              '& .MuiTab-root': {
                fontWeight: 600,
                minHeight: 48,
                textTransform: 'none',
              },
            }}
          >
            <Tab
              value="recommended"
              label="Recommended Plan"
              icon={<AutoAwesomeIcon sx={{ fontSize: 18 }} />}
              iconPosition="start"
              sx={{ gap: 0.5 }}
            />
            <Tab value="all" label={`All Accounts (${Object.keys(allAccountsGrouped).length})`} />
            <Tab value="crossbureau" label={`Cross-Bureau (${Object.keys(groupedDiscrepancies).length})`} />
            <Tab value="trimerge" label={`Tri-Merge Accounts (${filteredAccounts.length})`} />
          </Tabs>
          <Typography variant="body2" sx={{ fontWeight: 600, color: 'text.primary' }}>
            Count
          </Typography>
        </Box>

        {/* TAB CONTENT */}
        {/* RECOMMENDED PLAN TAB - Batched copilot recommendations */}
        {groupBy === "recommended" && (
          <RecommendedPlanTab
            reportId={currentReport?.report_id}
            onGenerateLetter={(violationIds, contradictionIds) => {
              // Update violation store with selected items
              const violationStore = useViolationStore.getState();
              violationStore.setSelectedViolations(violationIds || []);
              violationStore.setSelectedDiscrepancies(contradictionIds || []);

              // Get bureau from the first selected violation (not from report - reports are multi-bureau)
              const selectedViolation = violations.find(v => violationIds?.includes(v.violation_id));
              const violationBureau = selectedViolation?.bureau?.toLowerCase();

              if (violationBureau) {
                const uiStore = useUIStore.getState();
                uiStore.setBureau(violationBureau);
              }

              // Navigate to letter page with channel
              navigate(`/letter/${currentReport?.report_id}?channel=MAILED`);
            }}
          />
        )}

        {/* ALL ACCOUNTS TAB - Shows all accounts with their violations */}
        {groupBy === "all" && (
          <>
            {Object.keys(allAccountsGrouped).length === 0 ? (
              <Box sx={{ p: 4, textAlign: 'center' }}>
                <Typography variant="body1" color="text.secondary">
                  No accounts found in this report.
                </Typography>
              </Box>
            ) : (
              <Table>
                <TableBody>
                  {Object.entries(allAccountsGrouped).map(([creditorName, accountViolations]) => {
                    const key = `all-${creditorName}`;
                    const isExpanded = expandedItems[key];
                    const violationCount = accountViolations.length;

                    return (
                      <React.Fragment key={key}>
                        <TableRow
                          onClick={() => toggleExpanded(key)}
                          sx={{
                            cursor: 'pointer',
                            bgcolor: isExpanded ? '#f8fafc' : 'transparent',
                            '&:hover': { bgcolor: '#f1f5f9' },
                          }}
                        >
                          <TableCell sx={{ py: 2, fontWeight: 600, borderBottom: '1px solid', borderColor: 'divider' }}>
                            <Box sx={{ display: 'flex', alignItems: 'center', gap: 1 }}>
                              <IconButton size="small" sx={{ p: 0 }}>
                                {isExpanded ? <ExpandMoreIcon fontSize="small" /> : <ChevronRightIcon fontSize="small" />}
                              </IconButton>
                              {creditorName}
                              {violationCount === 0 && (
                                <Chip
                                  label="Clean"
                                  size="small"
                                  color="success"
                                  variant="outlined"
                                  sx={{ ml: 1, height: 22, fontSize: '0.7rem' }}
                                />
                              )}
                            </Box>
                          </TableCell>
                          <TableCell align="right" sx={{ py: 2, fontWeight: 500, color: violationCount > 0 ? 'error.main' : 'success.main', width: 80, borderBottom: '1px solid', borderColor: 'divider' }}>
                            {violationCount}
                          </TableCell>
                        </TableRow>
                        <TableRow>
                          <TableCell colSpan={2} sx={{ p: 0, border: 'none' }}>
                            <Collapse in={isExpanded} timeout="auto" unmountOnExit>
                              <Box sx={{ pl: 4, pr: 2, py: 2, bgcolor: '#fafafa' }}>
                                {violationCount === 0 ? (
                                  <Typography variant="body2" color="text.secondary" sx={{ py: 1 }}>
                                    No violations found for this account.
                                  </Typography>
                                ) : (
                                  accountViolations.map((violation) => (
                                    <ViolationToggle
                                      key={violation.violation_id}
                                      violation={violation}
                                      isSelected={selectedViolationIds.includes(violation.violation_id)}
                                      onToggle={handleViolationToggle}
                                    />
                                  ))
                                )}
                              </Box>
                            </Collapse>
                          </TableCell>
                        </TableRow>
                      </React.Fragment>
                    );
                  })}
                </TableBody>
              </Table>
            )}
          </>
        )}

        {/* CROSS-BUREAU TAB */}
        {groupBy === "crossbureau" && (
          <>
            {Object.keys(groupedDiscrepancies).length === 0 ? (
              <Box sx={{ p: 4, textAlign: 'center' }}>
                <Typography variant="body1" color="text.secondary">
                  {searchTerm ? 'No discrepancies match your search.' : 'No cross-bureau discrepancies found. Accounts are reported consistently across all bureaus.'}
                </Typography>
              </Box>
            ) : (
              <Table>
                <TableBody>
                  {Object.entries(groupedDiscrepancies).sort(([a], [b]) => a.localeCompare(b)).map(([creditor, items]) => (
                    <CollapsibleTableRow
                      key={creditor}
                      label={creditor}
                      count={items.length}
                      isExpanded={expandedItems[`disc-${creditor}`]}
                      onToggle={() => toggleExpanded(`disc-${creditor}`)}
                    >
                      {items.map((discrepancy, index) => (
                        <DiscrepancyToggle
                          key={discrepancy.discrepancy_id || index}
                          discrepancy={discrepancy}
                          isSelected={selectedDiscrepancyIds.includes(discrepancy.discrepancy_id)}
                          onToggle={toggleDiscrepancy}
                        />
                      ))}
                    </CollapsibleTableRow>
                  ))}
                </TableBody>
              </Table>
            )}
          </>
        )}

        {/* TRI-MERGE ACCOUNTS TAB */}
        {groupBy === "trimerge" && (
          <>
            {filteredAccounts.length === 0 ? (
              <Box sx={{ p: 4, textAlign: 'center' }}>
                <Typography variant="body1" color="text.secondary">
                  {searchTerm ? 'No accounts match your search.' : 'No accounts found in this report.'}
                </Typography>
              </Box>
            ) : (
              <Table>
                <TableBody>
                  {[...filteredAccounts].sort((a, b) => (a.creditor_name || '').localeCompare(b.creditor_name || '')).map((account, index) => (
                    <CollapsibleTableRow
                      key={account.account_id || index}
                      label={account.creditor_name || 'Unknown Account'}
                      count={account.bureaus ? Object.keys(account.bureaus).length : 1}
                      isExpanded={expandedItems[`acc-${account.account_id}`]}
                      onToggle={() => toggleExpanded(`acc-${account.account_id}`)}
                    >
                      <AccountAccordion account={account} embedded />
                    </CollapsibleTableRow>
                  ))}
                </TableBody>
              </Table>
            )}
          </>
        )}
      </TableContainer>

      {/* Override flow dialog and toast */}
      <OverrideController controller={overrideController} />
    </Box>
  );
};

export default ViolationList;
