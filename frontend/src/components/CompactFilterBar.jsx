/**
 * Credit Engine 2.0 - Compact Filter Bar Component
 * Dropdown-based filtering UI that saves vertical space
 */
import React, { useState } from 'react';
import {
  Box,
  Button,
  Menu,
  MenuItem,
  Checkbox,
  ListItemText,
  Chip,
  Stack,
  Typography,
  Divider,
} from '@mui/material';
import KeyboardArrowDownIcon from '@mui/icons-material/KeyboardArrowDown';
import CloseIcon from '@mui/icons-material/Close';
import AccountBalanceIcon from '@mui/icons-material/AccountBalance';
import WarningIcon from '@mui/icons-material/Warning';
import { getViolationLabel } from '../utils/formatViolation';

const CompactFilterBar = ({
  filters,
  filterOptions,
  toggleFilter,
  clearFilters,
  hasActiveFilters,
  filteredCount,
  totalCount,
  stats = {},
}) => {
  const totalAccounts = stats.totalAccounts || 0;
  const violationsFound = stats.violationsFound || 0;

  // Menu anchor states for each dropdown
  const [bureauAnchor, setBureauAnchor] = useState(null);
  const [severityAnchor, setSeverityAnchor] = useState(null);
  const [typeAnchor, setTypeAnchor] = useState(null);
  const [accountAnchor, setAccountAnchor] = useState(null);

  // Format label for display (generic - for bureau, severity, accounts)
  const formatLabel = (str) => {
    return str
      .split('_')
      .map(word => word.charAt(0).toUpperCase() + word.slice(1).toLowerCase())
      .join(' ');
  };

  // Format label for violation types using the proper mapping
  const formatTypeLabel = (str, filterType) => {
    if (filterType === 'categories') {
      return getViolationLabel(str);
    }
    return formatLabel(str);
  };

  // Render a dropdown button with selection count
  const renderFilterButton = (label, options, selectedItems, anchorEl, setAnchor, filterType) => {
    const selectedCount = selectedItems.length;
    const isOpen = Boolean(anchorEl);

    return (
      <>
        <Button
          variant="outlined"
          size="small"
          onClick={(e) => setAnchor(e.currentTarget)}
          endIcon={<KeyboardArrowDownIcon />}
          sx={{
            borderRadius: '8px',
            textTransform: 'none',
            fontWeight: 500,
            fontSize: '0.8rem',
            px: 1.5,
            py: 0.75,
            minWidth: 100,
            borderColor: selectedCount > 0 ? '#2563EB' : '#E2E8F0',
            bgcolor: selectedCount > 0 ? '#EFF6FF' : 'transparent',
            color: selectedCount > 0 ? '#2563EB' : '#64748B',
            '&:hover': {
              borderColor: '#2563EB',
              bgcolor: '#EFF6FF',
            },
          }}
        >
          {label}
          {selectedCount > 0 && (
            <Chip
              label={selectedCount}
              size="small"
              sx={{
                ml: 0.75,
                height: 18,
                minWidth: 18,
                fontSize: '0.65rem',
                fontWeight: 600,
                bgcolor: '#2563EB',
                color: '#fff',
              }}
            />
          )}
        </Button>
        <Menu
          anchorEl={anchorEl}
          open={isOpen}
          onClose={() => setAnchor(null)}
          PaperProps={{
            sx: {
              mt: 0.5,
              borderRadius: 2,
              boxShadow: '0 4px 20px rgba(0,0,0,0.1)',
              maxHeight: 300,
              minWidth: 180,
            },
          }}
        >
          {options && options.length > 0 ? (
            options.map((option) => {
              const isSelected = selectedItems.includes(option);
              return (
                <MenuItem
                  key={option}
                  onClick={() => toggleFilter(filterType, option)}
                  sx={{
                    py: 0.5,
                    '&:hover': { bgcolor: '#F1F5F9' },
                  }}
                >
                  <Checkbox
                    checked={isSelected}
                    size="small"
                    sx={{
                      p: 0.5,
                      mr: 1,
                      color: '#CBD5E1',
                      '&.Mui-checked': { color: '#2563EB' },
                    }}
                  />
                  <ListItemText
                    primary={formatTypeLabel(option, filterType)}
                    primaryTypographyProps={{
                      fontSize: '0.8rem',
                      fontWeight: isSelected ? 600 : 400,
                    }}
                  />
                </MenuItem>
              );
            })
          ) : (
            <MenuItem disabled>
              <Typography variant="body2" color="text.secondary">
                No options
              </Typography>
            </MenuItem>
          )}
        </Menu>
      </>
    );
  };

  return (
    <Box
      sx={{
        display: 'flex',
        alignItems: 'center',
        justifyContent: 'space-between',
        py: 1.5,
        px: 2,
        mb: 2,
        bgcolor: 'white',
        borderRadius: 3,
        boxShadow: '0 2px 8px rgba(0,0,0,0.08)',
      }}
    >
      {/* Left side: Filter dropdowns */}
      <Stack direction="row" spacing={1.5} alignItems="center">
        {renderFilterButton(
          'Bureau',
          filterOptions.bureaus,
          filters.bureaus,
          bureauAnchor,
          setBureauAnchor,
          'bureaus'
        )}

        {renderFilterButton(
          'Severity',
          filterOptions.severities,
          filters.severities,
          severityAnchor,
          setSeverityAnchor,
          'severities'
        )}

        {renderFilterButton(
          'Type',
          filterOptions.categories,
          filters.categories,
          typeAnchor,
          setTypeAnchor,
          'categories'
        )}

        {renderFilterButton(
          'Account',
          filterOptions.accounts,
          filters.accounts,
          accountAnchor,
          setAccountAnchor,
          'accounts'
        )}
      </Stack>

      {/* Right side: Stats + Clear button */}
      <Stack direction="row" spacing={2} alignItems="center">
        {/* Stats */}
        <Stack direction="row" spacing={2.5} alignItems="center">
          <Stack direction="row" spacing={0.75} alignItems="center">
            <AccountBalanceIcon sx={{ fontSize: 18, color: '#3b82f6' }} />
            <Typography variant="body2" sx={{ fontWeight: 600, color: '#1a1a1a' }}>
              {totalAccounts}
            </Typography>
            <Typography variant="caption" sx={{ color: '#64748B' }}>
              Accounts
            </Typography>
          </Stack>

          <Stack direction="row" spacing={0.75} alignItems="center">
            <WarningIcon sx={{ fontSize: 18, color: '#f59e0b' }} />
            <Typography variant="body2" sx={{ fontWeight: 600, color: '#1a1a1a' }}>
              {violationsFound}
            </Typography>
            <Typography variant="caption" sx={{ color: '#64748B' }}>
              Violations
            </Typography>
          </Stack>

        </Stack>

        {/* Clear button */}
        {hasActiveFilters && (
          <>
            <Divider orientation="vertical" flexItem />
            <Button
              size="small"
              startIcon={<CloseIcon sx={{ fontSize: 14 }} />}
              onClick={clearFilters}
              sx={{
                textTransform: 'none',
                color: '#64748B',
                fontSize: '0.75rem',
                '&:hover': {
                  bgcolor: '#FEE2E2',
                  color: '#DC2626',
                },
              }}
            >
              Clear Filters
            </Button>
          </>
        )}
      </Stack>
    </Box>
  );
};

export default CompactFilterBar;
