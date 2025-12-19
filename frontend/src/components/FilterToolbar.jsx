/**
 * Credit Engine 2.0 - Filter Toolbar Component
 * "Clean Fintech" style - Dense, authoritative filtering UI
 * Dynamic extraction - auto-detects violation types from data
 */
import React, { useState } from 'react';
import {
  Box,
  Paper,
  Typography,
  Chip,
  Stack,
  Divider,
  Button,
  Collapse,
  IconButton,
  TextField,
  InputAdornment,
} from '@mui/material';
import FilterListIcon from '@mui/icons-material/FilterList';
import CloseIcon from '@mui/icons-material/Close';
import ExpandMoreIcon from '@mui/icons-material/ExpandMore';
import ExpandLessIcon from '@mui/icons-material/ExpandLess';
import KeyboardArrowDownIcon from '@mui/icons-material/KeyboardArrowDown';
import KeyboardArrowUpIcon from '@mui/icons-material/KeyboardArrowUp';
import SearchIcon from '@mui/icons-material/Search';
import { getViolationLabel } from '../utils/formatViolation';

const VISIBLE_LIMIT = 8; // Show top 8 categories by default

const FilterToolbar = ({
  filters,
  filterOptions,
  toggleFilter,
  clearFilters,
  hasActiveFilters,
  filteredCount,
  totalCount,
  searchTerm = '',
  setSearchTerm,
}) => {
  const [isExpanded, setIsExpanded] = useState(true);
  const [showAllCategories, setShowAllCategories] = useState(false);

  // Sort categories alphabetically
  const sortedCategories = [...(filterOptions.categories || [])].sort();
  const visibleCategories = showAllCategories
    ? sortedCategories
    : sortedCategories.slice(0, VISIBLE_LIMIT);
  const hiddenCount = sortedCategories.length - VISIBLE_LIMIT;

  // Helper to render a group of selectable chips
  const renderFilterGroup = (label, type, options) => {
    if (!options || options.length === 0) return null;

    return (
      <Box>
        <Typography
          variant="caption"
          sx={{
            color: 'text.secondary',
            fontWeight: 700,
            display: 'block',
            mb: 1,
            textTransform: 'uppercase',
            letterSpacing: '0.05em',
            fontSize: '0.65rem',
          }}
        >
          {label} ({options.length})
        </Typography>
        <Stack direction="row" spacing={1} flexWrap="wrap" useFlexGap sx={{ gap: 0.75 }}>
          {options.map((option) => {
            const isSelected = filters[type].includes(option);
            return (
              <Chip
                key={option}
                label={option}
                onClick={() => toggleFilter(type, option)}
                size="small"
                sx={{
                  borderRadius: '6px',
                  fontWeight: 500,
                  fontSize: '0.75rem',
                  height: 28,
                  border: isSelected ? 'none' : '1px solid #E2E8F0',
                  bgcolor: isSelected ? '#2563EB' : 'transparent',
                  color: isSelected ? '#fff' : 'text.primary',
                  transition: 'all 0.15s ease',
                  '&:hover': {
                    bgcolor: isSelected ? '#1D4ED8' : '#F1F5F9',
                  },
                }}
              />
            );
          })}
        </Stack>
      </Box>
    );
  };

  return (
    <Paper
      elevation={0}
      sx={{
        p: 2,
        mb: 2,
        border: '1px solid #E2E8F0',
        borderRadius: 3,
        bgcolor: '#FFFFFF',
      }}
    >
      {/* Header Row */}
      <Box
        sx={{
          display: 'flex',
          justifyContent: 'space-between',
          alignItems: 'center',
          cursor: 'pointer',
        }}
        onClick={() => setIsExpanded(!isExpanded)}
      >
        <Stack direction="row" spacing={1.5} alignItems="center">
          <FilterListIcon sx={{ color: '#0F172A', fontSize: 20 }} />
          <Typography variant="subtitle1" sx={{ fontWeight: 700, color: '#0F172A' }}>
            Filter Violations
          </Typography>
          <Chip
            label={hasActiveFilters ? `${filteredCount} of ${totalCount}` : `${totalCount} total`}
            size="small"
            sx={{
              bgcolor: hasActiveFilters ? '#2563EB' : '#F1F5F9',
              color: hasActiveFilters ? '#fff' : '#64748B',
              fontWeight: 600,
              fontSize: '0.7rem',
              height: 24,
            }}
          />
        </Stack>

        <Stack direction="row" spacing={2} alignItems="center">
          {/* Search Input */}
          {setSearchTerm && (
            <TextField
              size="small"
              placeholder="Search accounts..."
              value={searchTerm}
              onChange={(e) => setSearchTerm(e.target.value)}
              onClick={(e) => e.stopPropagation()}
              InputProps={{
                startAdornment: (
                  <InputAdornment position="start">
                    <SearchIcon sx={{ fontSize: 18, color: '#94A3B8' }} />
                  </InputAdornment>
                ),
                endAdornment: searchTerm && (
                  <InputAdornment position="end">
                    <IconButton
                      size="small"
                      onClick={(e) => {
                        e.stopPropagation();
                        setSearchTerm('');
                      }}
                      sx={{ p: 0.25 }}
                    >
                      <CloseIcon sx={{ fontSize: 16 }} />
                    </IconButton>
                  </InputAdornment>
                ),
              }}
              sx={{
                width: 220,
                '& .MuiOutlinedInput-root': {
                  borderRadius: 2,
                  bgcolor: '#F8FAFC',
                  fontSize: '0.85rem',
                  '& fieldset': { borderColor: '#E2E8F0' },
                  '&:hover fieldset': { borderColor: '#CBD5E1' },
                  '&.Mui-focused fieldset': { borderColor: '#2563EB' },
                },
                '& .MuiInputBase-input': {
                  py: 0.75,
                },
              }}
            />
          )}
          {/* Clear Button */}
          {hasActiveFilters && (
            <Button
              size="small"
              startIcon={<CloseIcon sx={{ fontSize: 16 }} />}
              onClick={(e) => {
                e.stopPropagation();
                clearFilters();
              }}
              sx={{
                color: 'text.secondary',
                fontSize: '0.75rem',
                '&:hover': { bgcolor: '#FEE2E2', color: '#991B1B' },
              }}
            >
              Clear All
            </Button>
          )}
          <IconButton size="small">
            {isExpanded ? <ExpandLessIcon /> : <ExpandMoreIcon />}
          </IconButton>
        </Stack>
      </Box>

      {/* Collapsible Filter Groups */}
      <Collapse in={isExpanded}>
        <Divider sx={{ my: 2 }} />
        <Stack spacing={2.5}>
          {renderFilterGroup('Bureau', 'bureaus', filterOptions.bureaus)}
          {renderFilterGroup('Severity', 'severities', filterOptions.severities)}

          {/* Violation Types with Show More/Less */}
          {sortedCategories.length > 0 && (
            <Box>
              <Typography
                variant="caption"
                sx={{
                  color: 'text.secondary',
                  fontWeight: 700,
                  display: 'block',
                  mb: 1,
                  textTransform: 'uppercase',
                  letterSpacing: '0.05em',
                  fontSize: '0.65rem',
                }}
              >
                Violation Type ({sortedCategories.length})
              </Typography>
              <Stack direction="row" spacing={1} flexWrap="wrap" useFlexGap sx={{ gap: 0.75 }}>
                {visibleCategories.map((option) => {
                  const isSelected = filters.categories.includes(option);
                  return (
                    <Chip
                      key={option}
                      label={getViolationLabel(option)}
                      onClick={() => toggleFilter('categories', option)}
                      size="small"
                      sx={{
                        borderRadius: '6px',
                        fontWeight: 500,
                        fontSize: '0.75rem',
                        height: 28,
                        border: isSelected ? 'none' : '1px solid #E2E8F0',
                        bgcolor: isSelected ? '#2563EB' : 'transparent',
                        color: isSelected ? '#fff' : 'text.primary',
                        transition: 'all 0.15s ease',
                        '&:hover': {
                          bgcolor: isSelected ? '#1D4ED8' : '#F1F5F9',
                        },
                      }}
                    />
                  );
                })}
              </Stack>

              {/* Show More / Show Less Button */}
              {hiddenCount > 0 && (
                <Button
                  size="small"
                  onClick={(e) => {
                    e.stopPropagation();
                    setShowAllCategories(!showAllCategories);
                  }}
                  endIcon={showAllCategories ? <KeyboardArrowUpIcon /> : <KeyboardArrowDownIcon />}
                  sx={{
                    mt: 1.5,
                    textTransform: 'none',
                    color: '#64748B',
                    fontSize: '0.75rem',
                    '&:hover': { bgcolor: '#F1F5F9' },
                  }}
                >
                  {showAllCategories ? 'Show Less' : `Show ${hiddenCount} More Types`}
                </Button>
              )}
            </Box>
          )}
        </Stack>
      </Collapse>
    </Paper>
  );
};

export default FilterToolbar;
