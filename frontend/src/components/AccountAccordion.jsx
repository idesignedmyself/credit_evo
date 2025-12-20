/**
 * Credit Engine 2.0 - Account Accordion Component
 * Expandable card showing account details across all bureaus
 */
import React from 'react';
import {
  Box,
  Paper,
  Typography,
  Collapse,
  IconButton,
  Chip,
  Table,
  TableBody,
  TableCell,
  TableContainer,
  TableHead,
  TableRow,
} from '@mui/material';
import ExpandMoreIcon from '@mui/icons-material/ExpandMore';
import ExpandLessIcon from '@mui/icons-material/ExpandLess';

const BUREAUS = ['transunion', 'experian', 'equifax'];

const BUREAU_COLORS = {
  transunion: '#0D47A1',
  experian: '#B71C1C',
  equifax: '#1B5E20',
};

const formatDate = (dateStr) => {
  if (!dateStr) return '-';
  try {
    const d = new Date(dateStr);
    return d.toLocaleDateString('en-US', { month: '2-digit', day: '2-digit', year: 'numeric' });
  } catch {
    return dateStr;
  }
};

const formatCurrency = (value) => {
  if (value === null || value === undefined) return '-';
  return new Intl.NumberFormat('en-US', { style: 'currency', currency: 'USD' }).format(value);
};

const getBureauValue = (account, bureau, field) => {
  const bureauData = account.bureaus?.[bureau];
  if (!bureauData) return '-';
  return bureauData[field];
};

const AccountAccordion = React.memo(({ account, embedded = false }) => {
  const [expanded, setExpanded] = React.useState(embedded);

  // Only show bureaus that have data for this account
  const activeBureaus = BUREAUS.filter(bureau => account.bureaus?.[bureau]);

  const rows = [
    { label: 'Account #:', field: 'account_number_masked', isAccountLevel: true },
    { label: 'Account Type:', field: 'account_type' },
    { label: 'Account Type - Detail:', field: 'account_type_detail' },
    { label: 'Bureau Code:', field: 'bureau_code' },
    { label: 'Account Status:', field: 'account_status_raw' },
    { label: 'Monthly Payment:', field: 'monthly_payment', format: 'currency' },
    { label: 'Date Opened:', field: 'date_opened', format: 'date' },
    { label: 'Balance:', field: 'balance', format: 'currency' },
    { label: 'No. of Months (terms):', field: 'term_months' },
    { label: 'High Credit:', field: 'high_credit', format: 'currency' },
    { label: 'Credit Limit:', field: 'credit_limit', format: 'currency' },
    { label: 'Past Due:', field: 'past_due_amount', format: 'currency' },
    { label: 'Payment Status:', field: 'payment_status' },
    { label: 'Last Reported:', field: 'date_reported', format: 'date' },
    { label: 'Comments:', field: 'remarks' },
    { label: 'Date Last Active:', field: 'date_last_activity', format: 'date' },
    { label: 'Date of Last Payment:', field: 'date_last_payment', format: 'date' },
  ];

  const getValue = (bureau, row) => {
    if (row.isAccountLevel) {
      return account[row.field] || '-';
    }
    const raw = getBureauValue(account, bureau, row.field);
    if (raw === null || raw === undefined || raw === '') return '-';
    if (row.format === 'date') return formatDate(raw);
    if (row.format === 'currency') return formatCurrency(raw);
    return raw;
  };

  const getPaymentHistory = (bureau) => {
    return account.bureaus?.[bureau]?.payment_history || [];
  };

  const buildPaymentTimeline = () => {
    const allMonths = new Set();
    activeBureaus.forEach(bureau => {
      const history = getPaymentHistory(bureau);
      history.forEach(entry => {
        const key = `${entry.month}-${entry.year}`;
        allMonths.add(key);
      });
    });

    const monthOrder = ['Jan', 'Feb', 'Mar', 'Apr', 'May', 'Jun', 'Jul', 'Aug', 'Sep', 'Oct', 'Nov', 'Dec'];
    const sorted = Array.from(allMonths).sort((a, b) => {
      const [monthA, yearA] = a.split('-');
      const [monthB, yearB] = b.split('-');
      if (yearA !== yearB) return parseInt(yearB) - parseInt(yearA);
      return monthOrder.indexOf(monthB) - monthOrder.indexOf(monthA);
    });

    return sorted.slice(0, 24);
  };

  const paymentTimeline = buildPaymentTimeline();

  const getStatusForMonth = (bureau, monthKey) => {
    const history = getPaymentHistory(bureau);
    const [month, year] = monthKey.split('-');
    const entry = history.find(h => h.month === month && String(h.year) === year);
    return entry?.status || '';
  };

  const getStatusColor = (status) => {
    if (!status) return 'transparent';
    const s = status.toUpperCase();
    if (s === 'OK' || s === 'CURRENT') return '#4CAF50';
    if (s.includes('30') || s.includes('LATE')) return '#FFC107';
    if (s.includes('60')) return '#FF9800';
    if (s.includes('90') || s.includes('120') || s.includes('CO')) return '#F44336';
    return '#9E9E9E';
  };

  const getAccountType = () => {
    for (const bureau of BUREAUS) {
      const type = account.bureaus?.[bureau]?.account_type;
      if (type) return type;
    }
    return null;
  };

  const accountType = getAccountType();

  // Content section (bureau table + payment history)
  const contentSection = (
    <Box>
      <TableContainer>
        <Table size="small" sx={{ tableLayout: 'fixed' }}>
          <TableHead>
            <TableRow>
              <TableCell sx={{ width: '25%', fontWeight: 'bold', backgroundColor: 'grey.50' }} />
              {activeBureaus.map(bureau => (
                <TableCell
                  key={bureau}
                  align="center"
                  sx={{
                    width: `${75 / activeBureaus.length}%`,
                    fontWeight: 'bold',
                    color: 'white',
                    backgroundColor: BUREAU_COLORS[bureau],
                    textTransform: 'capitalize',
                  }}
                >
                  {bureau.charAt(0).toUpperCase() + bureau.slice(1)}
                </TableCell>
              ))}
            </TableRow>
          </TableHead>
          <TableBody>
            {rows.map((row, idx) => (
              <TableRow key={row.field} sx={{ backgroundColor: idx % 2 === 0 ? 'white' : 'grey.50' }}>
                <TableCell sx={{ fontWeight: 'medium', fontSize: '0.85rem' }}>
                  {row.label}
                </TableCell>
                {activeBureaus.map(bureau => (
                  <TableCell key={bureau} align="center" sx={{ fontSize: '0.85rem' }}>
                    {getValue(bureau, row)}
                  </TableCell>
                ))}
              </TableRow>
            ))}
          </TableBody>
        </Table>
      </TableContainer>

      {paymentTimeline.length > 0 && (
        <Box sx={{ p: 2, borderTop: '1px solid', borderColor: 'grey.200' }}>
          <Typography variant="subtitle2" sx={{ fontWeight: 'bold', mb: 1 }}>
            Two-Year Payment History
          </Typography>
          <Box sx={{ overflowX: 'auto' }}>
            <Table size="small">
              <TableHead>
                {/* Month row */}
                <TableRow>
                  <TableCell sx={{ minWidth: 80, fontSize: '0.75rem', backgroundColor: 'grey.50' }}>Month</TableCell>
                  {paymentTimeline.map(monthKey => {
                    const [month] = monthKey.split('-');
                    return (
                      <TableCell key={`month-${monthKey}`} align="center" sx={{ minWidth: 40, p: 0.5, fontSize: '0.7rem' }}>
                        {month}
                      </TableCell>
                    );
                  })}
                </TableRow>
                {/* Year row */}
                <TableRow>
                  <TableCell sx={{ minWidth: 80, fontSize: '0.75rem' }}>Year</TableCell>
                  {paymentTimeline.map(monthKey => {
                    const [, year] = monthKey.split('-');
                    return (
                      <TableCell key={`year-${monthKey}`} align="center" sx={{ minWidth: 40, p: 0.5, fontSize: '0.7rem', color: 'text.secondary' }}>
                        {year?.slice(-2)}
                      </TableCell>
                    );
                  })}
                </TableRow>
              </TableHead>
              <TableBody>
                {activeBureaus.map(bureau => (
                  <TableRow key={bureau}>
                    <TableCell sx={{ fontSize: '0.75rem', textTransform: 'capitalize' }}>
                      {bureau}
                    </TableCell>
                    {paymentTimeline.map(monthKey => {
                      const status = getStatusForMonth(bureau, monthKey);
                      return (
                        <TableCell
                          key={monthKey}
                          align="center"
                          sx={{
                            p: 0.5,
                            fontSize: '0.65rem',
                            backgroundColor: getStatusColor(status),
                            color: status && getStatusColor(status) !== 'transparent' ? 'white' : 'inherit',
                            fontWeight: 'bold',
                          }}
                        >
                          {status || ''}
                        </TableCell>
                      );
                    })}
                  </TableRow>
                ))}
              </TableBody>
            </Table>
          </Box>
        </Box>
      )}
    </Box>
  );

  // Embedded mode: just return content directly
  if (embedded) {
    return contentSection;
  }

  // Standalone mode: full Paper with header
  return (
    <Paper
      sx={{
        p: 2,
        mb: 1,
        border: '1px solid',
        borderColor: 'grey.200',
        backgroundColor: 'background.paper',
        transition: 'all 0.2s ease',
      }}
    >
      <Box
        sx={{ display: 'flex', alignItems: 'flex-start', gap: 1, cursor: 'pointer' }}
        onClick={() => setExpanded(!expanded)}
      >
        <Box sx={{ flex: 1 }}>
          <Box sx={{ display: 'flex', alignItems: 'center', gap: 1, mb: 0.5 }}>
            <Typography variant="subtitle1" sx={{ fontWeight: 'bold' }}>
              {account.creditor_name || 'Unknown Creditor'}
            </Typography>
            {accountType && (
              <Chip
                label={accountType}
                size="small"
                color="primary"
                variant="outlined"
              />
            )}
          </Box>
          <Typography variant="body2" color="text.secondary">
            {account.account_number_masked || 'Account'}
          </Typography>
        </Box>

        <IconButton
          size="small"
          onClick={(e) => {
            e.stopPropagation();
            setExpanded(!expanded);
          }}
          sx={{ ml: 1 }}
        >
          {expanded ? <ExpandLessIcon /> : <ExpandMoreIcon />}
        </IconButton>
      </Box>

      <Collapse in={expanded}>
        <Box sx={{ mt: 2, pl: 1, borderLeft: '3px solid', borderColor: 'grey.300' }}>
          {contentSection}
        </Box>
      </Collapse>
    </Paper>
  );
});

export default AccountAccordion;
