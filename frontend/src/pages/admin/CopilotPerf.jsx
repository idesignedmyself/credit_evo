/**
 * CopilotPerf - Copilot performance metrics
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
  LinearProgress,
  Alert,
  Chip,
  Table,
  TableBody,
  TableCell,
  TableContainer,
  TableHead,
  TableRow,
} from '@mui/material';
import { StatCard } from '../../components/admin';
import { useAdminStore } from '../../state';

const GOAL_LABELS = {
  credit_hygiene: 'Credit Hygiene',
  mortgage: 'Mortgage',
  auto_loan: 'Auto Loan',
  prime_credit_card: 'Credit Card',
  apartment_rental: 'Rental',
  employment: 'Employment',
};

function ComparisonBar({ label, followed, overridden }) {
  return (
    <Box sx={{ mb: 3 }}>
      <Typography variant="body2" sx={{ color: '#fff', fontWeight: 500, mb: 1 }}>
        {label}
      </Typography>
      <Box sx={{ display: 'flex', gap: 2 }}>
        <Box sx={{ flexGrow: 1 }}>
          <Box sx={{ display: 'flex', justifyContent: 'space-between', mb: 0.5 }}>
            <Typography variant="caption" sx={{ color: '#10b981' }}>
              Followed Copilot
            </Typography>
            <Typography variant="caption" sx={{ color: '#10b981', fontWeight: 600 }}>
              {followed}%
            </Typography>
          </Box>
          <LinearProgress
            variant="determinate"
            value={followed}
            sx={{
              height: 8,
              borderRadius: 1,
              bgcolor: '#0f3460',
              '& .MuiLinearProgress-bar': { bgcolor: '#10b981', borderRadius: 1 },
            }}
          />
        </Box>
        <Box sx={{ flexGrow: 1 }}>
          <Box sx={{ display: 'flex', justifyContent: 'space-between', mb: 0.5 }}>
            <Typography variant="caption" sx={{ color: '#f59e0b' }}>
              Overrode Copilot
            </Typography>
            <Typography variant="caption" sx={{ color: '#f59e0b', fontWeight: 600 }}>
              {overridden}%
            </Typography>
          </Box>
          <LinearProgress
            variant="determinate"
            value={overridden}
            sx={{
              height: 8,
              borderRadius: 1,
              bgcolor: '#0f3460',
              '& .MuiLinearProgress-bar': { bgcolor: '#f59e0b', borderRadius: 1 },
            }}
          />
        </Box>
      </Box>
    </Box>
  );
}

export default function CopilotPerf() {
  const {
    copilotPerf,
    copilotPerfDays,
    isLoadingCopilotPerf,
    error,
    fetchCopilotPerf,
    setCopilotPerfDays,
  } = useAdminStore();

  useEffect(() => {
    fetchCopilotPerf();
  }, [fetchCopilotPerf]);

  const handleDaysChange = (event) => {
    setCopilotPerfDays(event.target.value);
  };

  return (
    <Box>
      {/* Header */}
      <Box sx={{ display: 'flex', justifyContent: 'space-between', alignItems: 'flex-start', mb: 4 }}>
        <Box>
          <Typography variant="h4" sx={{ color: '#fff', fontWeight: 700, mb: 1 }}>
            Copilot Performance
          </Typography>
          <Typography variant="body1" sx={{ color: '#a2a2a2' }}>
            Recommendation follow rates and outcome comparison
          </Typography>
        </Box>

        <FormControl size="small" sx={{ minWidth: 120 }}>
          <InputLabel sx={{ color: '#a2a2a2' }}>Time Range</InputLabel>
          <Select
            value={copilotPerfDays}
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
      {isLoadingCopilotPerf && (
        <LinearProgress sx={{ mb: 3, bgcolor: '#0f3460', '& .MuiLinearProgress-bar': { bgcolor: '#e94560' } }} />
      )}

      {/* Stats */}
      <Grid container spacing={3} sx={{ mb: 4 }}>
        <Grid item xs={12} sm={6} md={3}>
          <StatCard
            title="Total Recommendations"
            value={copilotPerf?.total_recommendations || 0}
            subtitle={`Last ${copilotPerfDays} days`}
            color="#3b82f6"
            loading={isLoadingCopilotPerf}
          />
        </Grid>
        <Grid item xs={12} sm={6} md={3}>
          <StatCard
            title="Follow Rate"
            value={`${copilotPerf?.follow_rate || 0}%`}
            subtitle="Users followed advice"
            color="#10b981"
            loading={isLoadingCopilotPerf}
          />
        </Grid>
        <Grid item xs={12} sm={6} md={3}>
          <StatCard
            title="Override Rate"
            value={`${copilotPerf?.override_rate || 0}%`}
            subtitle="Users overrode advice"
            color="#f59e0b"
            loading={isLoadingCopilotPerf}
          />
        </Grid>
        <Grid item xs={12} sm={6} md={3}>
          <StatCard
            title="Followed Deletion Rate"
            value={`${copilotPerf?.followed_deletion_rate || 0}%`}
            subtitle="When advice followed"
            color="#e94560"
            loading={isLoadingCopilotPerf}
          />
        </Grid>
      </Grid>

      <Grid container spacing={3}>
        {/* Outcome Comparison */}
        <Grid item xs={12} md={6}>
          <Card sx={{ bgcolor: '#16213e', border: '1px solid #0f3460', borderRadius: 2, height: '100%' }}>
            <CardContent>
              <Typography variant="h6" sx={{ color: '#fff', fontWeight: 600, mb: 3 }}>
                Outcome Comparison
              </Typography>

              <ComparisonBar
                label="Deletion Rate"
                followed={copilotPerf?.followed_deletion_rate || 0}
                overridden={copilotPerf?.overridden_deletion_rate || 0}
              />

              <Box sx={{ mt: 4, p: 2, bgcolor: '#0f3460', borderRadius: 1 }}>
                <Typography variant="caption" sx={{ color: '#6b7280' }}>
                  Note: Override deletion rate reflects outcomes when users proceeded against Copilot advice.
                  Lower rates indicate Copilot's value in guiding enforcement strategy.
                </Typography>
              </Box>
            </CardContent>
          </Card>
        </Grid>

        {/* By Goal */}
        <Grid item xs={12} md={6}>
          <Card sx={{ bgcolor: '#16213e', border: '1px solid #0f3460', borderRadius: 2, height: '100%' }}>
            <CardContent>
              <Typography variant="h6" sx={{ color: '#fff', fontWeight: 600, mb: 3 }}>
                Performance by Goal
              </Typography>

              {copilotPerf?.by_goal && Object.keys(copilotPerf.by_goal).length > 0 ? (
                <TableContainer>
                  <Table size="small">
                    <TableHead>
                      <TableRow sx={{ '& th': { borderColor: '#0f3460' } }}>
                        <TableCell sx={{ color: '#6b7280' }}>Goal</TableCell>
                        <TableCell align="right" sx={{ color: '#6b7280' }}>Executions</TableCell>
                        <TableCell align="right" sx={{ color: '#6b7280' }}>Deletion Rate</TableCell>
                      </TableRow>
                    </TableHead>
                    <TableBody sx={{ '& td': { borderColor: '#0f3460' } }}>
                      {Object.entries(copilotPerf.by_goal)
                        .sort((a, b) => b[1].total - a[1].total)
                        .map(([goal, data]) => (
                          <TableRow key={goal}>
                            <TableCell sx={{ color: '#fff' }}>
                              {GOAL_LABELS[goal] || goal}
                            </TableCell>
                            <TableCell align="right" sx={{ color: '#a2a2a2' }}>
                              {data.total}
                            </TableCell>
                            <TableCell align="right">
                              <Chip
                                label={`${data.deletion_rate}%`}
                                size="small"
                                sx={{
                                  bgcolor: data.deletion_rate >= 50 ? '#10b98120' : '#ef444420',
                                  color: data.deletion_rate >= 50 ? '#10b981' : '#ef4444',
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
                  No goal data available
                </Typography>
              )}
            </CardContent>
          </Card>
        </Grid>
      </Grid>

      {/* Truth Notice */}
      <Box
        sx={{
          mt: 4,
          p: 2,
          bgcolor: '#16213e',
          border: '1px solid #0f3460',
          borderRadius: 2,
        }}
      >
        <Typography variant="caption" sx={{ color: '#6b7280' }}>
          Copilot performance metrics are derived from the Execution Ledger's suppression events (USER_OVERRIDE)
          and outcome records. Follow rate approximates recommendation adherence based on execution patterns.
        </Typography>
      </Box>
    </Box>
  );
}
