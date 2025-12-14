/**
 * Credit Engine 2.0 - Violation List Component
 * Clean table-style layout with collapsible groups
 * No header - header is managed by parent ViolationList
 */
import React, { useState } from 'react';
import {
  Box,
  Table,
  TableBody,
  TableCell,
  TableRow,
  Collapse,
  IconButton,
  Typography,
  Paper,
} from '@mui/material';
import ExpandMoreIcon from '@mui/icons-material/ExpandMore';
import ChevronRightIcon from '@mui/icons-material/ChevronRight';
import ViolationToggle from './ViolationToggle';

/**
 * Table-style group header row (collapsible)
 */
const GroupHeaderRow = ({ group, count, isExpanded, onToggle }) => (
  <TableRow
    onClick={onToggle}
    sx={{
      cursor: 'pointer',
      bgcolor: isExpanded ? '#f8fafc' : 'transparent',
      '&:hover': {
        bgcolor: '#f1f5f9',
      },
    }}
  >
    <TableCell
      sx={{
        py: 2,
        fontWeight: 600,
        color: 'text.primary',
        borderBottom: '1px solid',
        borderColor: 'divider',
      }}
    >
      <Box sx={{ display: 'flex', alignItems: 'center', gap: 1 }}>
        <IconButton size="small" sx={{ p: 0 }}>
          {isExpanded ? (
            <ExpandMoreIcon fontSize="small" />
          ) : (
            <ChevronRightIcon fontSize="small" />
          )}
        </IconButton>
        {group}
      </Box>
    </TableCell>
    <TableCell
      align="right"
      sx={{
        py: 2,
        fontWeight: 500,
        color: 'text.secondary',
        borderBottom: '1px solid',
        borderColor: 'divider',
        width: 80,
      }}
    >
      {count}
    </TableCell>
  </TableRow>
);

/**
 * Standard violation list (rendered inside collapse)
 */
const StandardViolationList = React.memo(({ violations, selectedViolationIds, toggleViolation }) => {
  const safeViolations = Array.isArray(violations) ? violations : [];
  const safeSelectedIds = Array.isArray(selectedViolationIds) ? selectedViolationIds : [];

  if (safeViolations.length === 0) return null;

  return (
    <Box sx={{ pl: 4, pr: 2, py: 2, bgcolor: '#fafafa' }}>
      {safeViolations.map((violation) => {
        if (!violation) return null;
        return (
          <ViolationToggle
            key={violation.violation_id}
            violation={violation}
            isSelected={safeSelectedIds.includes(violation.violation_id)}
            onToggle={toggleViolation}
          />
        );
      })}
    </Box>
  );
});

/**
 * Main VirtualizedViolationList Component
 * Renders table body only - header managed by parent
 */
const VirtualizedViolationList = ({
  violations = [],
  selectedViolationIds = [],
  toggleViolation,
  groupedData = null,
}) => {
  // Track expanded/collapsed state for each group (all collapsed by default)
  const [expandedGroups, setExpandedGroups] = useState({});

  const toggleGroup = (group) => {
    setExpandedGroups((prev) => ({
      ...prev,
      [group]: !prev[group],
    }));
  };

  const safeViolations = Array.isArray(violations) ? violations : [];
  const safeSelectedIds = Array.isArray(selectedViolationIds) ? selectedViolationIds : [];
  const safeGroupedData = groupedData && typeof groupedData === 'object' ? groupedData : null;

  // If grouped data is provided, render table body with groups
  if (safeGroupedData && Object.keys(safeGroupedData).length > 0) {
    return (
      <Table>
        <TableBody>
          {Object.entries(safeGroupedData).map(([group, items]) => {
            const safeItems = Array.isArray(items) ? items : [];
            if (safeItems.length === 0) return null;

            const isExpanded = expandedGroups[group] === true;

            return (
              <React.Fragment key={group}>
                <GroupHeaderRow
                  group={group}
                  count={safeItems.length}
                  isExpanded={isExpanded}
                  onToggle={() => toggleGroup(group)}
                />
                <TableRow>
                  <TableCell colSpan={2} sx={{ p: 0, border: 'none' }}>
                    <Collapse in={isExpanded} timeout="auto" unmountOnExit>
                      <StandardViolationList
                        violations={safeItems}
                        selectedViolationIds={safeSelectedIds}
                        toggleViolation={toggleViolation}
                      />
                    </Collapse>
                  </TableCell>
                </TableRow>
              </React.Fragment>
            );
          })}
        </TableBody>
      </Table>
    );
  }

  // Flat list rendering (no groups)
  if (safeViolations.length === 0) {
    return (
      <Box sx={{ p: 4, textAlign: 'center' }}>
        <Typography variant="body1" color="text.secondary">
          No violations found
        </Typography>
      </Box>
    );
  }

  return (
    <Box sx={{ p: 2 }}>
      <StandardViolationList
        violations={safeViolations}
        selectedViolationIds={safeSelectedIds}
        toggleViolation={toggleViolation}
      />
    </Box>
  );
};

export default React.memo(VirtualizedViolationList);
