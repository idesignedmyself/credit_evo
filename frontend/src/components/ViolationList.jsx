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
  const [groupBy, setGroupBy] = useState("type");
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
            <Tab value="type" label="Group by Type" />
            <Tab value="account" label="Group by Account" />
            <Tab value="bureau" label="Group by Bureau" />
            <Tab value="crossbureau" label={`Cross-Bureau (${discrepancies?.length || 0})`} />
            <Tab value="accounts" label={`Tri-Merge Accounts (${accounts.length})`} />
          </Tabs>
          <Typography variant="body2" sx={{ fontWeight: 600, color: 'text.primary' }}>
            Count
          </Typography>
        </Box>

        {/* TAB CONTENT */}
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

        {/* ACCOUNTS TAB */}
        {groupBy === "accounts" && (
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
