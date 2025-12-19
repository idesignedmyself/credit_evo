/**
 * Credit Engine 2.0 - Violation List Component (Clean SPA Version)
 * Unified table layout with integrated tabs
 */

import React, { useState, useMemo } from 'react';
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
import Chip from '@mui/material/Chip';

import {
  useViolationStore,
  useReportStore
} from '../state';

import {
  groupViolationsByType,
  groupViolationsByAccount,
  groupViolationsByBureau
} from '../utils';

import { useCreditFilter } from '../hooks/useCreditFilter';
import ViolationToggle from './ViolationToggle';
import DiscrepancyToggle from './DiscrepancyToggle';
import AccountAccordion from './AccountAccordion';
import FilterToolbar from './FilterToolbar';
import VirtualizedViolationList from './VirtualizedViolationList';

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

const ViolationList = ({ hideFilters = false, hideHeader = false }) => {
  const [groupBy, setGroupBy] = useState("all");
  const [expandedItems, setExpandedItems] = useState({});

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
    filteredCount
  } = useCreditFilter(violations);

  // PRE-COMPUTE GROUPINGS ONCE (using filtered data)
  const groupedByType = useMemo(() => groupViolationsByType(filteredData), [filteredData]);
  const groupedByAccount = useMemo(() => groupViolationsByAccount(filteredData), [filteredData]);
  const groupedByBureau = useMemo(() => groupViolationsByBureau(filteredData), [filteredData]);

  // Group discrepancies by account
  const groupedDiscrepancies = useMemo(() => {
    if (!discrepancies?.length) return {};
    return discrepancies.reduce((acc, d) => {
      const key = d.creditor_name || 'Unknown';
      if (!acc[key]) acc[key] = [];
      acc[key].push(d);
      return acc;
    }, {});
  }, [discrepancies]);

  // Group accounts by first letter or type
  const groupedAccounts = useMemo(() => {
    if (!accounts?.length) return {};
    return accounts.reduce((acc, a) => {
      const key = a.creditor_name?.[0]?.toUpperCase() || '#';
      if (!acc[key]) acc[key] = [];
      acc[key].push(a);
      return acc;
    }, {});
  }, [accounts]);

  // Get set of creditors that have violations matching current severity/category filters
  // Returns null if no filtering needed (show all accounts)
  // Returns Set of creditor names if filtering is active
  const creditorsWithMatchingViolations = useMemo(() => {
    // If no severity or category filters active, show all accounts (no violation-based filtering)
    if (filters.severities.length === 0 && filters.categories.length === 0) {
      return null; // null means "all match" - don't filter by violations
    }
    // Filters are active - find creditors with matching violations
    if (!violations?.length) {
      // No violations exist but filters are active - return empty set (nothing matches)
      return new Set();
    }
    const matching = new Set();
    violations.forEach(v => {
      const severityMatch = filters.severities.length === 0 || filters.severities.includes(v.severity);
      const categoryMatch = filters.categories.length === 0 || filters.categories.includes(v.violation_type);
      if (severityMatch && categoryMatch) {
        matching.add(v.creditor_name);
      }
    });
    return matching;
  }, [violations, filters.severities, filters.categories]);

  // Flatten all accounts from all bureaus into individual rows
  // Apply all filters (bureau, creditor, severity, category via violations)
  const allAccountsFlattened = useMemo(() => {
    if (!accounts?.length) return [];
    const flattened = [];
    accounts.forEach(account => {
      const bureaus = account.bureaus || {};
      Object.entries(bureaus).forEach(([bureauName, bureauData]) => {
        // Skip if no bureau data or empty object (must have at least some actual fields)
        if (!bureauData || typeof bureauData !== 'object') return;
        // Check if bureau data has any meaningful content (not just empty object)
        const hasData = bureauData.account_status_raw || bureauData.balance != null ||
                        bureauData.account_type || bureauData.date_opened || bureauData.date_reported;
        if (!hasData) return;

        // Apply bureau filter
        if (filters.bureaus.length > 0 && !filters.bureaus.includes(bureauName)) {
          return;
        }
        // Apply creditor/account filter
        if (filters.accounts.length > 0 && !filters.accounts.includes(account.creditor_name)) {
          return;
        }
        // Apply severity/category filter (via violations for this creditor)
        if (creditorsWithMatchingViolations !== null && !creditorsWithMatchingViolations.has(account.creditor_name)) {
          return;
        }
        flattened.push({
          ...bureauData,
          creditor_name: account.creditor_name,
          account_number_masked: account.account_number_masked || bureauData.account_number_masked,
          account_id: account.account_id,
          bureau: bureauName,
          _originalAccount: account, // Keep reference for detailed view
        });
      });
    });
    return flattened;
  }, [accounts, filters.bureaus, filters.accounts, creditorsWithMatchingViolations]);

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
            <Tab value="all" label={`All Accounts (${allAccountsFlattened.length})`} />
            <Tab value="type" label="Group by Type" />
            <Tab value="account" label="Group by Account" />
            <Tab value="bureau" label="Group by Bureau" />
            <Tab value="crossbureau" label={`Cross-Bureau (${discrepancies?.length || 0})`} />
            <Tab value="trimerge" label={`Tri-Merge Accounts (${accounts.length})`} />
          </Tabs>
          <Typography variant="body2" sx={{ fontWeight: 600, color: 'text.primary' }}>
            Count
          </Typography>
        </Box>

        {/* TAB CONTENT */}
        {/* ALL ACCOUNTS TAB - Shows every account from every bureau */}
        {groupBy === "all" && (
          <>
            {allAccountsFlattened.length === 0 ? (
              <Box sx={{ p: 4, textAlign: 'center' }}>
                <Typography variant="body1" color="text.secondary">
                  No accounts found in this report.
                </Typography>
              </Box>
            ) : (
              <Table>
                <TableBody>
                  {allAccountsFlattened.map((account, index) => {
                    const bureauColors = {
                      transunion: '#0D47A1',
                      experian: '#B71C1C',
                      equifax: '#1B5E20',
                    };
                    const key = `all-${account.account_id}-${account.bureau}-${index}`;
                    return (
                      <CollapsibleTableRow
                        key={key}
                        label={
                          <Box sx={{ display: 'flex', alignItems: 'center', gap: 1.5 }}>
                            <span>{account.creditor_name || 'Unknown Account'}</span>
                            <Chip
                              label={account.bureau?.charAt(0).toUpperCase() + account.bureau?.slice(1)}
                              size="small"
                              sx={{
                                bgcolor: bureauColors[account.bureau] || '#666',
                                color: 'white',
                                fontWeight: 600,
                                fontSize: '0.7rem',
                                height: 22,
                              }}
                            />
                            {account.account_number_masked && (
                              <Typography variant="body2" color="text.secondary" component="span">
                                ({account.account_number_masked})
                              </Typography>
                            )}
                          </Box>
                        }
                        count={account.account_type || '-'}
                        isExpanded={expandedItems[key]}
                        onToggle={() => toggleExpanded(key)}
                      >
                        <Box sx={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fill, minmax(200px, 1fr))', gap: 2 }}>
                          <Box>
                            <Typography variant="caption" color="text.secondary">Account Status</Typography>
                            <Typography variant="body2" sx={{ fontWeight: 500 }}>{account.account_status_raw || '-'}</Typography>
                          </Box>
                          <Box>
                            <Typography variant="caption" color="text.secondary">Balance</Typography>
                            <Typography variant="body2" sx={{ fontWeight: 500 }}>
                              {account.balance != null ? `$${account.balance.toLocaleString()}` : '-'}
                            </Typography>
                          </Box>
                          <Box>
                            <Typography variant="caption" color="text.secondary">Credit Limit</Typography>
                            <Typography variant="body2" sx={{ fontWeight: 500 }}>
                              {account.credit_limit != null ? `$${account.credit_limit.toLocaleString()}` : '-'}
                            </Typography>
                          </Box>
                          <Box>
                            <Typography variant="caption" color="text.secondary">High Credit</Typography>
                            <Typography variant="body2" sx={{ fontWeight: 500 }}>
                              {account.high_credit != null ? `$${account.high_credit.toLocaleString()}` : '-'}
                            </Typography>
                          </Box>
                          <Box>
                            <Typography variant="caption" color="text.secondary">Past Due</Typography>
                            <Typography variant="body2" sx={{ fontWeight: 500, color: account.past_due_amount > 0 ? 'error.main' : 'inherit' }}>
                              {account.past_due_amount != null ? `$${account.past_due_amount.toLocaleString()}` : '-'}
                            </Typography>
                          </Box>
                          <Box>
                            <Typography variant="caption" color="text.secondary">Payment Status</Typography>
                            <Typography variant="body2" sx={{ fontWeight: 500 }}>{account.payment_status || '-'}</Typography>
                          </Box>
                          <Box>
                            <Typography variant="caption" color="text.secondary">Date Opened</Typography>
                            <Typography variant="body2" sx={{ fontWeight: 500 }}>
                              {account.date_opened ? new Date(account.date_opened).toLocaleDateString() : '-'}
                            </Typography>
                          </Box>
                          <Box>
                            <Typography variant="caption" color="text.secondary">Last Reported</Typography>
                            <Typography variant="body2" sx={{ fontWeight: 500 }}>
                              {account.date_reported ? new Date(account.date_reported).toLocaleDateString() : '-'}
                            </Typography>
                          </Box>
                          {account.remarks && (
                            <Box sx={{ gridColumn: 'span 2' }}>
                              <Typography variant="caption" color="text.secondary">Comments</Typography>
                              <Typography variant="body2" sx={{ fontWeight: 500 }}>{account.remarks}</Typography>
                            </Box>
                          )}
                        </Box>
                      </CollapsibleTableRow>
                    );
                  })}
                </TableBody>
              </Table>
            )}
          </>
        )}

        {groupBy === "type" && (
          <VirtualizedViolationList
            violations={filteredData}
            selectedViolationIds={selectedViolationIds}
            toggleViolation={toggleViolation}
            groupedData={groupedByType}
          />
        )}

        {groupBy === "account" && (
          <VirtualizedViolationList
            violations={filteredData}
            selectedViolationIds={selectedViolationIds}
            toggleViolation={toggleViolation}
            groupedData={groupedByAccount}
          />
        )}

        {groupBy === "bureau" && (
          <VirtualizedViolationList
            violations={filteredData}
            selectedViolationIds={selectedViolationIds}
            toggleViolation={toggleViolation}
            groupedData={groupedByBureau}
          />
        )}

        {/* CROSS-BUREAU TAB */}
        {groupBy === "crossbureau" && (
          <>
            {(!discrepancies || discrepancies.length === 0) ? (
              <Box sx={{ p: 4, textAlign: 'center' }}>
                <Typography variant="body1" color="text.secondary">
                  No cross-bureau discrepancies found. Accounts are reported consistently across all bureaus.
                </Typography>
              </Box>
            ) : (
              <Table>
                <TableBody>
                  {Object.entries(groupedDiscrepancies).map(([creditor, items]) => (
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
            {accounts.length === 0 ? (
              <Box sx={{ p: 4, textAlign: 'center' }}>
                <Typography variant="body1" color="text.secondary">
                  No accounts found in this report.
                </Typography>
              </Box>
            ) : (
              <Table>
                <TableBody>
                  {accounts.map((account, index) => (
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
    </Box>
  );
};

export default ViolationList;
