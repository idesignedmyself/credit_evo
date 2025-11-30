/**
 * Credit Engine 2.0 - Account List Component
 * Displays all accounts with expandable details
 */
import React from 'react';
import { Box, Typography, Paper } from '@mui/material';
import AccountAccordion from './AccountAccordion';
import { useReportStore } from '../state';

const AccountList = () => {
  const { currentReport } = useReportStore();
  const accounts = currentReport?.accounts || [];

  if (accounts.length === 0) {
    return (
      <Paper sx={{ p: 3, textAlign: 'center' }}>
        <Typography variant="body1" color="text.secondary">
          No accounts found in this report.
        </Typography>
      </Paper>
    );
  }

  return (
    <Box>
      <Paper sx={{ p: 2, mb: 2 }}>
        <Typography variant="h6">
          {accounts.length} Accounts
        </Typography>
        <Typography variant="body2" color="text.secondary">
          Click on an account to view detailed information across all bureaus
        </Typography>
      </Paper>

      {accounts.map((account, index) => (
        <AccountAccordion key={account.account_id || index} account={account} />
      ))}
    </Box>
  );
};

export default AccountList;
