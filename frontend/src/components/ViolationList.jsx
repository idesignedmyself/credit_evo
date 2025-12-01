/**
 * Credit Engine 2.0 - Violation List Component (Clean SPA Version)
 * Instant tab switching (no animations, no URL delays)
 */

import React, { useState, useMemo } from 'react';
import {
  Box,
  Typography,
  Paper,
  Tabs,
  Tab,
  CircularProgress,
  Alert,
  Checkbox,
  FormControlLabel
} from '@mui/material';

import {
  useViolationStore,
  useReportStore
} from '../state';

import {
  groupViolationsByType,
  groupViolationsByAccount,
  groupViolationsByBureau
} from '../utils';

import ViolationToggle from './ViolationToggle';
import AccountAccordion from './AccountAccordion';

const ViolationList = () => {
  const [groupBy, setGroupBy] = useState("type");

  const {
    violations,
    selectedViolationIds,
    toggleViolation,
    selectByBureau,
    deselectByBureau,
    isLoading,
    error
  } = useViolationStore();

  const { currentReport } = useReportStore();
  const accounts = currentReport?.accounts || [];

  // PRE-COMPUTE GROUPINGS ONCE
  const groupedByType = useMemo(() => {
    return groupViolationsByType(violations);
  }, [violations]);

  const groupedByAccount = useMemo(() => {
    return groupViolationsByAccount(violations);
  }, [violations]);

  const groupedByBureau = useMemo(() => {
    return groupViolationsByBureau(violations);
  }, [violations]);

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

  const totalViolations = violations.length;

  // Helper function to check bureau selection state
  const getBureauSelectionState = (bureau, items) => {
    const bureauViolationIds = items.map(v => v.violation_id);
    const selectedInBureau = bureauViolationIds.filter(id => selectedViolationIds.includes(id));
    const allSelected = selectedInBureau.length === bureauViolationIds.length;
    const someSelected = selectedInBureau.length > 0 && selectedInBureau.length < bureauViolationIds.length;
    return { allSelected, someSelected, selectedCount: selectedInBureau.length, totalCount: bureauViolationIds.length };
  };

  // Handle per-bureau select all toggle
  const handleBureauSelectToggle = (bureau, items) => {
    const { allSelected } = getBureauSelectionState(bureau, items);
    if (allSelected) {
      deselectByBureau(bureau);
    } else {
      selectByBureau(bureau);
    }
  };

  return (
    <Box>
      {/* HEADER */}
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
        {totalViolations} Violations Found
      </Typography>

      {/* TABS */}
      <Box sx={{ mb: 2 }}>
        <Tabs
          value={groupBy}
          onChange={(e, v) => setGroupBy(v)}
        >
          <Tab value="type" label="Group by Type" />
          <Tab value="account" label="Group by Account" />
          <Tab value="bureau" label="Group by Bureau" />
          <Tab value="accounts" label={`Accounts (${accounts.length})`} />
        </Tabs>
      </Box>

      {/* ------- SPA INSTANT TABS (no unmounting) ------- */}

      {/* TYPE TAB */}
      <Box hidden={groupBy !== "type"}>
        {Object.entries(groupedByType).map(([group, items]) => (
          <Box key={group} sx={{ mb: 3 }}>
            <Typography
              variant="subtitle1"
              sx={{
                fontWeight: 'bold',
                mb: 1,
                pb: 1,
                borderBottom: '2px solid',
                borderColor: 'primary.main',
              }}
            >
              {group} ({items.length})
            </Typography>

            {items.map((violation) => (
              <ViolationToggle
                key={violation.violation_id}
                violation={violation}
                isSelected={selectedViolationIds.includes(violation.violation_id)}
                onToggle={toggleViolation}
              />
            ))}
          </Box>
        ))}
      </Box>

      {/* ACCOUNT TAB */}
      <Box hidden={groupBy !== "account"}>
        {Object.entries(groupedByAccount).map(([group, items]) => (
          <Box key={group} sx={{ mb: 3 }}>
            <Typography
              variant="subtitle1"
              sx={{
                fontWeight: 'bold',
                mb: 1,
                pb: 1,
                borderBottom: '2px solid',
                borderColor: 'primary.main',
              }}
            >
              {group} ({items.length})
            </Typography>

            {items.map((violation) => (
              <ViolationToggle
                key={violation.violation_id}
                violation={violation}
                isSelected={selectedViolationIds.includes(violation.violation_id)}
                onToggle={toggleViolation}
              />
            ))}
          </Box>
        ))}
      </Box>

      {/* BUREAU TAB */}
      <Box hidden={groupBy !== "bureau"}>
        {Object.entries(groupedByBureau).map(([group, items]) => {
          const { allSelected, someSelected, selectedCount, totalCount } = getBureauSelectionState(group, items);
          return (
            <Box key={group} sx={{ mb: 3 }}>
              <Box sx={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', mb: 1, pb: 1, borderBottom: '2px solid', borderColor: 'primary.main' }}>
                <Typography variant="subtitle1" sx={{ fontWeight: 'bold' }}>
                  {group} ({items.length})
                </Typography>
                <FormControlLabel
                  control={
                    <Checkbox
                      checked={allSelected}
                      indeterminate={someSelected}
                      onChange={() => handleBureauSelectToggle(group, items)}
                      color="primary"
                      size="small"
                    />
                  }
                  label={`Select All ${group} (${selectedCount}/${totalCount})`}
                  sx={{ mr: 0 }}
                />
              </Box>

              {items.map((violation) => (
                <ViolationToggle
                  key={violation.violation_id}
                  violation={violation}
                  isSelected={selectedViolationIds.includes(violation.violation_id)}
                  onToggle={toggleViolation}
                />
              ))}
            </Box>
          );
        })}
      </Box>

      {/* ACCOUNTS TAB */}
      <Box hidden={groupBy !== "accounts"}>
        {accounts.length === 0 ? (
          <Paper sx={{ p: 3, textAlign: 'center' }}>
            <Typography variant="body1" color="text.secondary">
              No accounts found in this report.
            </Typography>
          </Paper>
        ) : (
          <Box sx={{ mb: 3 }}>
            <Typography
              variant="subtitle1"
              sx={{
                fontWeight: 'bold',
                mb: 1,
                pb: 1,
                borderBottom: '2px solid',
                borderColor: 'primary.main',
              }}
            >
              All Accounts ({accounts.length})
            </Typography>

            {accounts.map((account, index) => (
              <AccountAccordion
                key={account.account_id || index}
                account={account}
              />
            ))}
          </Box>
        )}
      </Box>
    </Box>
  );
};

export default ViolationList;
