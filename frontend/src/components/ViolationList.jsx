/**
 * Credit Engine 2.0 - Violation List Component
 * Displays all violations with selection controls and accounts tab
 */
import React from 'react';
import {
  Box,
  Typography,
  Button,
  Paper,
  Tabs,
  Tab,
  CircularProgress,
  Alert,
} from '@mui/material';
import CheckBoxIcon from '@mui/icons-material/CheckBox';
import CheckBoxOutlineBlankIcon from '@mui/icons-material/CheckBoxOutlineBlank';
import ViolationToggle from './ViolationToggle';
import AccountAccordion from './AccountAccordion';
import { useViolationStore, useReportStore } from '../state';
import { groupViolationsByType, groupViolationsByAccount, groupViolationsByBureau } from '../utils';

const ViolationList = () => {
  const [groupBy, setGroupBy] = React.useState('type');
  const {
    violations,
    selectedViolationIds,
    isLoading,
    error,
    toggleViolation,
    selectAll,
    deselectAll,
  } = useViolationStore();
  const { currentReport } = useReportStore();
  const accounts = currentReport?.accounts || [];

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

  if (!violations || violations.length === 0) {
    return (
      <Paper sx={{ p: 3, textAlign: 'center' }}>
        <Typography variant="body1" color="text.secondary">
          No violations found in this report.
        </Typography>
      </Paper>
    );
  }

  const groupedByType = groupViolationsByType(violations);
  const groupedByAccount = groupViolationsByAccount(violations);
  const groupedByBureau = groupViolationsByBureau(violations);
  const grouped = groupBy === 'type' ? groupedByType : groupBy === 'account' ? groupedByAccount : groupedByBureau;

  return (
    <Box>
      <Paper sx={{ p: 2, mb: 2 }}>
        <Box sx={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', flexWrap: 'wrap', gap: 2 }}>
          <Typography variant="h6">
            {violations.length} Violations Found
          </Typography>

          <Button
            size="small"
            startIcon={selectedViolationIds.length === violations.length ? <CheckBoxIcon /> : <CheckBoxOutlineBlankIcon />}
            onClick={selectedViolationIds.length === violations.length ? deselectAll : selectAll}
            variant="outlined"
          >
            {selectedViolationIds.length === violations.length ? 'Deselect All' : 'Select All'}
          </Button>
        </Box>

        <Typography variant="body2" color="text.secondary" sx={{ mt: 1 }}>
          {selectedViolationIds.length} selected · {violations.length} total
        </Typography>
      </Paper>

      <Tabs
        value={groupBy}
        onChange={(e, v) => setGroupBy(v)}
        sx={{ mb: 2 }}
      >
        <Tab value="type" label="Group by Type" />
        <Tab value="account" label="Group by Account" />
        <Tab value="bureau" label="Group by Bureau" />
        <Tab value="accounts" label={`Accounts (${accounts.length})`} />
      </Tabs>

      {/* Show accounts when Accounts tab is selected */}
      {groupBy === 'accounts' ? (
        <Box>
          {accounts.length === 0 ? (
            <Paper sx={{ p: 3, textAlign: 'center' }}>
              <Typography variant="body1" color="text.secondary">
                No accounts found in this report.
              </Typography>
            </Paper>
          ) : (
            accounts.map((account, index) => (
              <AccountAccordion key={account.account_id || index} account={account} />
            ))
          )}
        </Box>
      ) : (
        /* Show violations grouped by type/account/bureau */
        Object.entries(grouped).map(([groupName, groupViolations]) => (
          <Box key={groupName} sx={{ mb: 3 }}>
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
              {groupName} ({groupViolations.length})
            </Typography>

            {groupViolations.map((violation) => (
              <ViolationToggle
                key={violation.violation_id}
                violation={violation}
                isSelected={selectedViolationIds.includes(violation.violation_id)}
                onToggle={toggleViolation}
              />
            ))}
          </Box>
        ))
      )}
    </Box>
  );
};

export default ViolationList;
