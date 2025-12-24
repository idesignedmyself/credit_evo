/**
 * AdminUsers - User list with search and pagination
 */
import React, { useEffect, useState } from 'react';
import {
  Box,
  Typography,
  TextField,
  InputAdornment,
  Pagination,
  CircularProgress,
  Alert,
} from '@mui/material';
import SearchIcon from '@mui/icons-material/Search';
import { UserTable } from '../../components/admin';
import { useAdminStore } from '../../state';

export default function AdminUsers() {
  const {
    users,
    usersTotal,
    usersPage,
    usersPageSize,
    usersSearch,
    isLoadingUsers,
    error,
    fetchUsers,
    setUsersPage,
    setUsersSearch,
  } = useAdminStore();

  const [searchInput, setSearchInput] = useState(usersSearch);
  const [searchTimeout, setSearchTimeout] = useState(null);

  useEffect(() => {
    fetchUsers();
  }, [fetchUsers]);

  // Debounced search
  const handleSearchChange = (e) => {
    const value = e.target.value;
    setSearchInput(value);

    if (searchTimeout) {
      clearTimeout(searchTimeout);
    }

    setSearchTimeout(
      setTimeout(() => {
        setUsersSearch(value);
      }, 300)
    );
  };

  const handlePageChange = (_, page) => {
    setUsersPage(page);
  };

  const totalPages = Math.ceil(usersTotal / usersPageSize);

  return (
    <Box>
      {/* Header */}
      <Box sx={{ mb: 4 }}>
        <Typography variant="h4" sx={{ color: '#fff', fontWeight: 700, mb: 1 }}>
          Users
        </Typography>
        <Typography variant="body1" sx={{ color: '#a2a2a2' }}>
          {usersTotal} total users with execution metrics
        </Typography>
      </Box>

      {/* Error Alert */}
      {error && (
        <Alert severity="error" sx={{ mb: 3, bgcolor: '#1a1a2e', color: '#ef4444' }}>
          {error}
        </Alert>
      )}

      {/* Search */}
      <Box sx={{ mb: 3 }}>
        <TextField
          fullWidth
          placeholder="Search by name, email, or username..."
          value={searchInput}
          onChange={handleSearchChange}
          InputProps={{
            startAdornment: (
              <InputAdornment position="start">
                <SearchIcon sx={{ color: '#6b7280' }} />
              </InputAdornment>
            ),
            endAdornment: isLoadingUsers && (
              <InputAdornment position="end">
                <CircularProgress size={20} sx={{ color: '#e94560' }} />
              </InputAdornment>
            ),
          }}
          sx={{
            '& .MuiOutlinedInput-root': {
              bgcolor: '#16213e',
              borderRadius: 2,
              '& fieldset': { borderColor: '#0f3460' },
              '&:hover fieldset': { borderColor: '#e94560' },
              '&.Mui-focused fieldset': { borderColor: '#e94560' },
            },
            '& .MuiInputBase-input': { color: '#fff' },
          }}
        />
      </Box>

      {/* Users Table */}
      <UserTable users={users} loading={isLoadingUsers} />

      {/* Pagination */}
      {totalPages > 1 && (
        <Box sx={{ display: 'flex', justifyContent: 'center', mt: 3 }}>
          <Pagination
            count={totalPages}
            page={usersPage}
            onChange={handlePageChange}
            sx={{
              '& .MuiPaginationItem-root': {
                color: '#a2a2a2',
                borderColor: '#0f3460',
                '&.Mui-selected': {
                  bgcolor: '#e94560',
                  color: '#fff',
                },
                '&:hover': {
                  bgcolor: 'rgba(233, 69, 96, 0.2)',
                },
              },
            }}
          />
        </Box>
      )}
    </Box>
  );
}
