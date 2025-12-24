/**
 * DisputeIntel - Population-level dispute analytics
 */
import React, { useEffect } from 'react';
import {
  Box,
  Typography,
  Grid,
  Card,
  CardContent,
  Select,
  MenuItem,
  FormControl,
  InputLabel,
  Table,
  TableBody,
  TableCell,
  TableContainer,
  TableHead,
  TableRow,
  LinearProgress,
  Alert,
  Chip,
} from '@mui/material';
import { StatCard } from '../../components/admin';
import { useAdminStore } from '../../state';

function OutcomeBar({ label, value, total, color }) {
  const percentage = total > 0 ? (value / total) * 100 : 0;

  return (
    <Box sx={{ mb: 2 }}>
      <Box sx={{ display: 'flex', justifyContent: 'space-between', mb: 0.5 }}>
        <Typography variant="body2" sx={{ color: '#a2a2a2' }}>
          {label}
        </Typography>
        <Typography variant="body2" sx={{ color: '#fff', fontWeight: 600 }}>
          {value} ({percentage.toFixed(1)}%)
        </Typography>
      </Box>
      <LinearProgress
        variant="determinate"
        value={percentage}
        sx={{
          height: 8,
          borderRadius: 1,
          bgcolor: '#0f3460',
          '& .MuiLinearProgress-bar': {
            bgcolor: color,
            borderRadius: 1,
          },
        }}
      />
    </Box>
  );
}

export default function DisputeIntel() {
  const {
    disputeIntel,
    disputeIntelDays,
    isLoadingDisputeIntel,
    error,
    fetchDisputeIntel,
    setDisputeIntelDays,
  } = useAdminStore();

  useEffect(() => {
    fetchDisputeIntel();
  }, [fetchDisputeIntel]);

  const handleDaysChange = (event) => {
    setDisputeIntelDays(event.target.value);
  };

  return (
    <Box>
      {/* Header */}
      <Box sx={{ display: 'flex', justifyContent: 'space-between', alignItems: 'flex-start', mb: 4 }}>
        <Box>
          <Typography variant="h4" sx={{ color: '#fff', fontWeight: 700, mb: 1 }}>
            Dispute Intelligence
          </Typography>
          <Typography variant="body1" sx={{ color: '#a2a2a2' }}>
            Population-level outcome analytics from Execution Ledger
          </Typography>
        </Box>

        <FormControl size="small" sx={{ minWidth: 120 }}>
          <InputLabel sx={{ color: '#a2a2a2' }}>Time Range</InputLabel>
          <Select
            value={disputeIntelDays}
            onChange={handleDaysChange}
            label="Time Range"
            sx={{
              color: '#fff',
              '& .MuiOutlinedInput-notchedOutline': { borderColor: '#0f3460' },
              '&:hover .MuiOutlinedInput-notchedOutline': { borderColor: '#e94560' },
              '&.Mui-focused .MuiOutlinedInput-notchedOutline': { borderColor: '#e94560' },
            }}
          >
            <MenuItem value={30}>30 Days</MenuItem>
            <MenuItem value={60}>60 Days</MenuItem>
            <MenuItem value={90}>90 Days</MenuItem>
            <MenuItem value={180}>180 Days</MenuItem>
            <MenuItem value={365}>1 Year</MenuItem>
          </Select>
        </FormControl>
      </Box>

      {/* Error Alert */}
      {error && (
        <Alert severity="error" sx={{ mb: 3, bgcolor: '#1a1a2e', color: '#ef4444' }}>
          {error}
        </Alert>
      )}

      {/* Loading */}
      {isLoadingDisputeIntel && (
        <LinearProgress sx={{ mb: 3, bgcolor: '#0f3460', '& .MuiLinearProgress-bar': { bgcolor: '#e94560' } }} />
      )}

      {/* Overall Stats */}
      <Grid container spacing={3} sx={{ mb: 4 }}>
        <Grid item xs={12} sm={4}>
          <StatCard
            title="Total Executions"
            value={disputeIntel?.total_executions || 0}
            subtitle={`Last ${disputeIntelDays} days`}
            color="#3b82f6"
            loading={isLoadingDisputeIntel}
          />
        </Grid>
        <Grid item xs={12} sm={4}>
          <StatCard
            title="Overall Deletion Rate"
            value={`${disputeIntel?.overall_deletion_rate || 0}%`}
            subtitle="Items successfully removed"
            color="#10b981"
            loading={isLoadingDisputeIntel}
          />
        </Grid>
        <Grid item xs={12} sm={4}>
          <StatCard
            title="Verification Rate"
            value={`${disputeIntel?.overall_verification_rate || 0}%`}
            subtitle="Items verified as accurate"
            color="#ef4444"
            loading={isLoadingDisputeIntel}
          />
        </Grid>
      </Grid>

      <Grid container spacing={3}>
        {/* By Bureau */}
        <Grid item xs={12} md={6}>
          <Card sx={{ bgcolor: '#16213e', border: '1px solid #0f3460', borderRadius: 2, height: '100%' }}>
            <CardContent>
              <Typography variant="h6" sx={{ color: '#fff', fontWeight: 600, mb: 3 }}>
                Outcomes by Bureau
              </Typography>

              {disputeIntel?.by_bureau && disputeIntel.by_bureau.length > 0 ? (
                disputeIntel.by_bureau.map((bureau) => (
                  <Box key={bureau.bureau} sx={{ mb: 3 }}>
                    <Box sx={{ display: 'flex', alignItems: 'center', gap: 1, mb: 1 }}>
                      <Typography variant="subtitle2" sx={{ color: '#fff', fontWeight: 600 }}>
                        {bureau.bureau}
                      </Typography>
                      <Chip
                        label={`${bureau.total_executions} total`}
                        size="small"
                        sx={{ bgcolor: '#0f3460', color: '#a2a2a2', fontSize: '0.65rem' }}
                      />
                    </Box>
                    <OutcomeBar
                      label="Deleted"
                      value={bureau.deleted}
                      total={bureau.total_executions}
                      color="#10b981"
                    />
                    <OutcomeBar
                      label="Verified"
                      value={bureau.verified}
                      total={bureau.total_executions}
                      color="#ef4444"
                    />
                    <OutcomeBar
                      label="Updated"
                      value={bureau.updated}
                      total={bureau.total_executions}
                      color="#f59e0b"
                    />
                  </Box>
                ))
              ) : (
                <Typography variant="body2" sx={{ color: '#6b7280', textAlign: 'center', py: 4 }}>
                  No bureau data available
                </Typography>
              )}
            </CardContent>
          </Card>
        </Grid>

        {/* Top Furnishers */}
        <Grid item xs={12} md={6}>
          <Card sx={{ bgcolor: '#16213e', border: '1px solid #0f3460', borderRadius: 2, height: '100%' }}>
            <CardContent>
              <Typography variant="h6" sx={{ color: '#fff', fontWeight: 600, mb: 3 }}>
                Top Furnishers
              </Typography>

              {disputeIntel?.top_furnishers && disputeIntel.top_furnishers.length > 0 ? (
                <TableContainer>
                  <Table size="small">
                    <TableHead>
                      <TableRow sx={{ '& th': { borderColor: '#0f3460' } }}>
                        <TableCell sx={{ color: '#6b7280' }}>Furnisher</TableCell>
                        <TableCell align="right" sx={{ color: '#6b7280' }}>Executions</TableCell>
                        <TableCell align="right" sx={{ color: '#6b7280' }}>Deletion %</TableCell>
                      </TableRow>
                    </TableHead>
                    <TableBody sx={{ '& td': { borderColor: '#0f3460' } }}>
                      {disputeIntel.top_furnishers.map((f) => (
                        <TableRow key={f.furnisher_name}>
                          <TableCell sx={{ color: '#fff' }}>
                            {f.furnisher_name.length > 25
                              ? `${f.furnisher_name.substring(0, 25)}...`
                              : f.furnisher_name}
                          </TableCell>
                          <TableCell align="right" sx={{ color: '#a2a2a2' }}>
                            {f.total_executions}
                          </TableCell>
                          <TableCell align="right">
                            <Chip
                              label={`${f.deletion_rate}%`}
                              size="small"
                              sx={{
                                bgcolor: f.deletion_rate >= 50 ? '#10b98120' : '#ef444420',
                                color: f.deletion_rate >= 50 ? '#10b981' : '#ef4444',
                                fontSize: '0.7rem',
                              }}
                            />
                          </TableCell>
                        </TableRow>
                      ))}
                    </TableBody>
                  </Table>
                </TableContainer>
              ) : (
                <Typography variant="body2" sx={{ color: '#6b7280', textAlign: 'center', py: 4 }}>
                  No furnisher data available
                </Typography>
              )}
            </CardContent>
          </Card>
        </Grid>
      </Grid>
    </Box>
  );
}
