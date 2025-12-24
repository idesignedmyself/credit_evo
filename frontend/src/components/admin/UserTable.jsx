/**
 * UserTable - Data table component for admin users list
 */
import React from 'react';
import {
  Table,
  TableBody,
  TableCell,
  TableContainer,
  TableHead,
  TableRow,
  Paper,
  Typography,
  Chip,
  IconButton,
  Tooltip,
  Box,
  Skeleton,
} from '@mui/material';
import VisibilityIcon from '@mui/icons-material/Visibility';
import { useNavigate } from 'react-router-dom';

const GOAL_LABELS = {
  credit_hygiene: 'Hygiene',
  mortgage: 'Mortgage',
  auto_loan: 'Auto',
  prime_credit_card: 'Credit Card',
  apartment_rental: 'Rental',
  employment: 'Employment',
};

function UserTableRow({ user, onViewDetail }) {
  const navigate = useNavigate();

  const handleView = () => {
    if (onViewDetail) {
      onViewDetail(user.id);
    } else {
      navigate(`/admin/users/${user.id}`);
    }
  };

  return (
    <TableRow
      hover
      sx={{
        '&:hover': { bgcolor: 'rgba(233, 69, 96, 0.05)' },
        cursor: 'pointer',
      }}
      onClick={handleView}
    >
      <TableCell sx={{ color: '#fff' }}>
        <Box>
          <Typography variant="body2" fontWeight={500}>
            {user.first_name && user.last_name
              ? `${user.first_name} ${user.last_name}`
              : user.username}
          </Typography>
          <Typography variant="caption" sx={{ color: '#a2a2a2' }}>
            {user.email}
          </Typography>
        </Box>
      </TableCell>
      <TableCell>
        {user.credit_goal && (
          <Chip
            label={GOAL_LABELS[user.credit_goal] || user.credit_goal}
            size="small"
            sx={{
              bgcolor: '#0f3460',
              color: '#fff',
              fontSize: '0.7rem',
            }}
          />
        )}
      </TableCell>
      <TableCell sx={{ color: '#a2a2a2' }}>
        {user.last_activity
          ? new Date(user.last_activity).toLocaleDateString()
          : 'Never'}
      </TableCell>
      <TableCell sx={{ color: '#fff', fontWeight: 600 }}>
        {user.execution_count}
      </TableCell>
      <TableCell sx={{ color: '#a2a2a2' }}>
        {user.letter_count}
      </TableCell>
      <TableCell align="right">
        <Tooltip title="View Details">
          <IconButton size="small" sx={{ color: '#e94560' }}>
            <VisibilityIcon fontSize="small" />
          </IconButton>
        </Tooltip>
      </TableCell>
    </TableRow>
  );
}

function LoadingRows({ count = 5 }) {
  return Array.from({ length: count }).map((_, i) => (
    <TableRow key={i}>
      <TableCell><Skeleton variant="text" sx={{ bgcolor: '#0f3460' }} /></TableCell>
      <TableCell><Skeleton variant="rounded" width={60} height={24} sx={{ bgcolor: '#0f3460' }} /></TableCell>
      <TableCell><Skeleton variant="text" width={80} sx={{ bgcolor: '#0f3460' }} /></TableCell>
      <TableCell><Skeleton variant="text" width={40} sx={{ bgcolor: '#0f3460' }} /></TableCell>
      <TableCell><Skeleton variant="text" width={40} sx={{ bgcolor: '#0f3460' }} /></TableCell>
      <TableCell><Skeleton variant="circular" width={24} height={24} sx={{ bgcolor: '#0f3460' }} /></TableCell>
    </TableRow>
  ));
}

export default function UserTable({ users, loading = false, onViewDetail }) {
  return (
    <TableContainer
      component={Paper}
      sx={{
        bgcolor: '#16213e',
        border: '1px solid #0f3460',
        borderRadius: 2,
      }}
    >
      <Table>
        <TableHead>
          <TableRow sx={{ '& th': { borderColor: '#0f3460' } }}>
            <TableCell sx={{ color: '#a2a2a2', fontWeight: 600 }}>User</TableCell>
            <TableCell sx={{ color: '#a2a2a2', fontWeight: 600 }}>Goal</TableCell>
            <TableCell sx={{ color: '#a2a2a2', fontWeight: 600 }}>Last Activity</TableCell>
            <TableCell sx={{ color: '#a2a2a2', fontWeight: 600 }}>Executions</TableCell>
            <TableCell sx={{ color: '#a2a2a2', fontWeight: 600 }}>Letters</TableCell>
            <TableCell align="right" sx={{ color: '#a2a2a2', fontWeight: 600 }}>Actions</TableCell>
          </TableRow>
        </TableHead>
        <TableBody sx={{ '& td': { borderColor: '#0f3460' } }}>
          {loading ? (
            <LoadingRows />
          ) : users.length === 0 ? (
            <TableRow>
              <TableCell colSpan={6} align="center" sx={{ py: 4, color: '#a2a2a2' }}>
                No users found
              </TableCell>
            </TableRow>
          ) : (
            users.map((user) => (
              <UserTableRow key={user.id} user={user} onViewDetail={onViewDetail} />
            ))
          )}
        </TableBody>
      </Table>
    </TableContainer>
  );
}
