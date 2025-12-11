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
import FilterListIcon from '@mui/icons-material/FilterList';
import KeyboardArrowDownIcon from '@mui/icons-material/KeyboardArrowDown';
import CloseIcon from '@mui/icons-material/Close';

const CompactFilterBar = ({
  filters,
  filterOptions,
  toggleFilter,
  clearFilters,
  hasActiveFilters,
  filteredCount,
  totalCount,
}) => {
  // Menu anchor states for each dropdown
  const [bureauAnchor, setBureauAnchor] = useState(null);
  const [severityAnchor, setSeverityAnchor] = useState(null);
  const [typeAnchor, setTypeAnchor] = useState(null);

  const bureauOpen = Boolean(bureauAnchor);
  const severityOpen = Boolean(severityAnchor);
  const typeOpen = Boolean(typeAnchor);

  // Format label for display
  const formatLabel = (str) => {
    return str
      .split('_')
      .map(word => word.charAt(0).toUpperCase() + word.slice(1).toLowerCase())
      .join(' ');
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
                    primary={formatLabel(option)}
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
        bgcolor: '#FAFBFC',
        border: '1px solid #E2E8F0',
        borderRadius: 2,
      }}
    >
      {/* Left side: Filter icon + dropdowns */}
      <Stack direction="row" spacing={1.5} alignItems="center">
        <FilterListIcon sx={{ color: '#64748B', fontSize: 20 }} />

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

        {/* Divider + Count */}
        <Divider orientation="vertical" flexItem sx={{ mx: 1 }} />
        <Typography variant="body2" sx={{ color: '#64748B', fontWeight: 500 }}>
          {hasActiveFilters ? (
            <>
              <Box component="span" sx={{ color: '#2563EB', fontWeight: 600 }}>
                {filteredCount}
              </Box>
              {' of '}
              {totalCount}
            </>
          ) : (
            `${totalCount} total`
          )}
        </Typography>
      </Stack>

      {/* Right side: Clear button */}
      {hasActiveFilters && (
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
      )}
    </Box>
  );
};

export default CompactFilterBar;
