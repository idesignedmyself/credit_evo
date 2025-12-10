/**
 * Credit Engine 2.0 - Violation List Component
 * Simple non-virtualized list (virtualization removed due to react-window compatibility issues)
 */
import React from 'react';
import { Box, Typography } from '@mui/material';
import ViolationToggle from './ViolationToggle';

/**
 * Group header component for grouped violations
 */
const GroupHeader = ({ group, count }) => (
  <Typography
    variant="subtitle1"
    sx={{
      fontWeight: 'bold',
      mb: 1,
      pb: 1,
      borderBottom: '2px solid',
      borderColor: 'primary.main',
    }}
  >
    {group} ({count})
  </Typography>
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

          return (
            <Box key={group} sx={{ mb: 3 }}>
              <GroupHeader group={group} count={safeItems.length} />
              <StandardViolationList
                violations={safeItems}
                selectedViolationIds={safeSelectedIds}
                toggleViolation={toggleViolation}
              />
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
