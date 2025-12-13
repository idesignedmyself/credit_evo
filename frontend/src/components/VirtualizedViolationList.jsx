/**
 * Credit Engine 2.0 - Violation List Component
 * Simple non-virtualized list with collapsible group headers
 */
import React, { useState } from 'react';
import { Box, Typography, Collapse, IconButton } from '@mui/material';
import ExpandMoreIcon from '@mui/icons-material/ExpandMore';
import ExpandLessIcon from '@mui/icons-material/ExpandLess';
import ViolationToggle from './ViolationToggle';

/**
 * Collapsible group header component for grouped violations
 */
const CollapsibleGroupHeader = ({ group, count, isExpanded, onToggle }) => (
  <Box
    onClick={onToggle}
    sx={{
      display: 'flex',
      alignItems: 'center',
      justifyContent: 'space-between',
      cursor: 'pointer',
      mb: 1,
      pb: 1,
      borderBottom: '2px solid',
      borderColor: 'primary.main',
      '&:hover': {
        bgcolor: 'action.hover',
        borderRadius: 1,
        mx: -1,
        px: 1,
      },
    }}
  >
    <Typography
      variant="subtitle1"
      sx={{
        fontWeight: 'bold',
      }}
    >
      {group} ({count})
    </Typography>
    <IconButton size="small" sx={{ ml: 1 }}>
      {isExpanded ? <ExpandLessIcon /> : <ExpandMoreIcon />}
    </IconButton>
  </Box>
);

/**
 * Standard violation list
 */
const StandardViolationList = React.memo(({ violations, selectedViolationIds, toggleViolation }) => {
  // Guard against null/undefined
  const safeViolations = Array.isArray(violations) ? violations : [];
  const safeSelectedIds = Array.isArray(selectedViolationIds) ? selectedViolationIds : [];

  if (safeViolations.length === 0) return null;

  return (
    <>
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
    </>
  );
});

/**
 * Main VirtualizedViolationList Component
 * (Name kept for backward compatibility, but virtualization is disabled)
 */
const VirtualizedViolationList = ({
  violations = [],
  selectedViolationIds = [],
  toggleViolation,
  groupedData = null,
}) => {
  // Track expanded/collapsed state for each group (all collapsed by default)
  const [expandedGroups, setExpandedGroups] = useState({});

  // Toggle a specific group's expanded state
  const toggleGroup = (group) => {
    setExpandedGroups((prev) => ({
      ...prev,
      [group]: !prev[group],
    }));
  };

  // Guard against null/undefined
  const safeViolations = Array.isArray(violations) ? violations : [];
  const safeSelectedIds = Array.isArray(selectedViolationIds) ? selectedViolationIds : [];
  const safeGroupedData = groupedData && typeof groupedData === 'object' ? groupedData : null;

  // If grouped data is provided, render groups with their violations
  if (safeGroupedData && Object.keys(safeGroupedData).length > 0) {
    return (
      <>
        {Object.entries(safeGroupedData).map(([group, items]) => {
          // Guard against non-array items
          const safeItems = Array.isArray(items) ? items : [];
          if (safeItems.length === 0) return null;

          const isExpanded = expandedGroups[group] === true; // Default to collapsed

          return (
            <Box key={group} sx={{ mb: 3 }}>
              <CollapsibleGroupHeader
                group={group}
                count={safeItems.length}
                isExpanded={isExpanded}
                onToggle={() => toggleGroup(group)}
              />
              <Collapse in={isExpanded} timeout="auto" unmountOnExit>
                <StandardViolationList
                  violations={safeItems}
                  selectedViolationIds={safeSelectedIds}
                  toggleViolation={toggleViolation}
                />
              </Collapse>
            </Box>
          );
        })}
      </>
    );
  }

  // Flat list rendering
  return (
    <StandardViolationList
      violations={safeViolations}
      selectedViolationIds={safeSelectedIds}
      toggleViolation={toggleViolation}
    />
  );
};

export default React.memo(VirtualizedViolationList);
