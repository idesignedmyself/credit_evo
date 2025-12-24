/**
 * AdminUserDetail - User drilldown with timeline
 */
import React, { useEffect } from 'react';
import { useParams, useNavigate } from 'react-router-dom';
import {
  Box,
  Typography,
  Grid,
  Card,
  CardContent,
  Button,
  Chip,
  CircularProgress,
  Alert,
  Divider,
} from '@mui/material';
import ArrowBackIcon from '@mui/icons-material/ArrowBack';
import PersonIcon from '@mui/icons-material/Person';
import { StatCard, TimelineEvent } from '../../components/admin';
import { useAdminStore } from '../../state';

const GOAL_LABELS = {
  credit_hygiene: 'General Credit Hygiene',
  mortgage: 'Mortgage',
  auto_loan: 'Auto Loan',
  prime_credit_card: 'Credit Card',
  apartment_rental: 'Rental',
  employment: 'Employment',
};

export default function AdminUserDetail() {
  const { userId } = useParams();
  const navigate = useNavigate();
  const { userDetail, isLoadingUserDetail, error, fetchUserDetail, clearUserDetail } = useAdminStore();

  useEffect(() => {
    if (userId) {
      fetchUserDetail(userId);
    }
    return () => clearUserDetail();
  }, [userId, fetchUserDetail, clearUserDetail]);

  if (isLoadingUserDetail) {
    return (
      <Box sx={{ display: 'flex', justifyContent: 'center', alignItems: 'center', minHeight: 400 }}>
        <CircularProgress sx={{ color: '#e94560' }} />
      </Box>
    );
  }

  if (error) {
    return (
      <Box>
        <Button
          startIcon={<ArrowBackIcon />}
          onClick={() => navigate('/admin/users')}
          sx={{ color: '#a2a2a2', mb: 3 }}
        >
          Back to Users
        </Button>
        <Alert severity="error" sx={{ bgcolor: '#1a1a2e', color: '#ef4444' }}>
          {error}
        </Alert>
      </Box>
    );
  }

  if (!userDetail) {
    return null;
  }

  return (
    <Box>
      {/* Back Button */}
      <Button
        startIcon={<ArrowBackIcon />}
        onClick={() => navigate('/admin/users')}
        sx={{ color: '#a2a2a2', mb: 3 }}
      >
        Back to Users
      </Button>

      {/* User Header */}
      <Card sx={{ bgcolor: '#16213e', border: '1px solid #0f3460', borderRadius: 2, mb: 3 }}>
        <CardContent>
          <Box sx={{ display: 'flex', alignItems: 'center', gap: 2, mb: 2 }}>
            <Box
              sx={{
                width: 56,
                height: 56,
                borderRadius: '50%',
                bgcolor: '#e94560',
                display: 'flex',
                alignItems: 'center',
                justifyContent: 'center',
              }}
            >
              <PersonIcon sx={{ color: '#fff', fontSize: 28 }} />
            </Box>
            <Box sx={{ flexGrow: 1 }}>
              <Typography variant="h5" sx={{ color: '#fff', fontWeight: 700 }}>
                {userDetail.first_name && userDetail.last_name
                  ? `${userDetail.first_name} ${userDetail.last_name}`
                  : userDetail.username}
              </Typography>
              <Typography variant="body2" sx={{ color: '#a2a2a2' }}>
                {userDetail.email}
              </Typography>
            </Box>
            {userDetail.credit_goal && (
              <Chip
                label={GOAL_LABELS[userDetail.credit_goal] || userDetail.credit_goal}
                sx={{ bgcolor: '#e94560', color: '#fff' }}
              />
            )}
          </Box>

          <Grid container spacing={2}>
            <Grid item xs={6} sm={3}>
              <Typography variant="caption" sx={{ color: '#6b7280' }}>
                Member Since
              </Typography>
              <Typography variant="body2" sx={{ color: '#fff' }}>
                {new Date(userDetail.created_at).toLocaleDateString()}
              </Typography>
            </Grid>
            <Grid item xs={6} sm={3}>
              <Typography variant="caption" sx={{ color: '#6b7280' }}>
                State
              </Typography>
              <Typography variant="body2" sx={{ color: '#fff' }}>
                {userDetail.state || 'Not set'}
              </Typography>
            </Grid>
            <Grid item xs={6} sm={3}>
              <Typography variant="caption" sx={{ color: '#6b7280' }}>
                Profile Complete
              </Typography>
              <Typography variant="body2" sx={{ color: '#fff' }}>
                {userDetail.profile_complete}%
              </Typography>
            </Grid>
            <Grid item xs={6} sm={3}>
              <Typography variant="caption" sx={{ color: '#6b7280' }}>
                Override Count
              </Typography>
              <Typography variant="body2" sx={{ color: userDetail.override_count > 0 ? '#f59e0b' : '#fff' }}>
                {userDetail.override_count}
              </Typography>
            </Grid>
          </Grid>
        </CardContent>
      </Card>

      {/* Stats Row */}
      <Grid container spacing={3} sx={{ mb: 3 }}>
        <Grid item xs={6} md={3}>
          <StatCard
            title="Reports"
            value={userDetail.total_reports}
            color="#3b82f6"
          />
        </Grid>
        <Grid item xs={6} md={3}>
          <StatCard
            title="Letters"
            value={userDetail.total_letters}
            color="#8b5cf6"
          />
        </Grid>
        <Grid item xs={6} md={3}>
          <StatCard
            title="Executions"
            value={userDetail.total_executions}
            color="#10b981"
          />
        </Grid>
        <Grid item xs={6} md={3}>
          <StatCard
            title="Deletion Rate"
            value={`${userDetail.deletion_rate}%`}
            color="#e94560"
          />
        </Grid>
      </Grid>

      {/* Timeline */}
      <Card sx={{ bgcolor: '#16213e', border: '1px solid #0f3460', borderRadius: 2 }}>
        <CardContent>
          <Typography variant="h6" sx={{ color: '#fff', fontWeight: 600, mb: 3 }}>
            Activity Timeline
          </Typography>

          {userDetail.timeline && userDetail.timeline.length > 0 ? (
            <Box>
              {userDetail.timeline.map((event, index) => (
                <TimelineEvent
                  key={event.id}
                  event={event}
                  isLast={index === userDetail.timeline.length - 1}
                />
              ))}
            </Box>
          ) : (
            <Typography variant="body2" sx={{ color: '#6b7280', textAlign: 'center', py: 4 }}>
              No activity recorded yet
            </Typography>
          )}
        </CardContent>
      </Card>
    </Box>
  );
}
