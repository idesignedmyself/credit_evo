/**
 * Credit Engine 2.0 - Virtualized Violation List Component
 * Uses react-window for 60FPS rendering of large violation lists
 * Falls back to standard rendering for small lists (<50 items)
 */
import React, { useMemo } from 'react';
import { List } from 'react-window';
import AutoSizer from 'react-virtualized-auto-sizer';
import { Box, Typography } from '@mui/material';
import ViolationToggle from './ViolationToggle';

// Height constants for violation items
const ITEM_HEIGHT = 90; // Collapsed accordion height with margin

// Threshold for using virtualization (small lists render faster without it)
const VIRTUALIZATION_THRESHOLD = 50;

/**
 * Row renderer for virtualized list
 */
const ViolationRow = React.memo(({ data, index, style }) => {
  const { violations, selectedViolationIds, toggleViolation } = data;
  const violation = violations[index];
  const isSelected = selectedViolationIds.includes(violation.violation_id);

  return (
    <div style={{ ...style, paddingRight: 8, paddingBottom: 8 }}>
      <ViolationToggle
        violation={violation}
        isSelected={isSelected}
        onToggle={toggleViolation}
      />
    </div>
  );
});

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
 * Standard (non-virtualized) violation list for small datasets
 */
const StandardViolationList = React.memo(({ violations, selectedViolationIds, toggleViolation }) => (
  <>
    {violations.map((violation) => (
      <ViolationToggle
        key={violation.violation_id}
        violation={violation}
        isSelected={selectedViolationIds.includes(violation.violation_id)}
        onToggle={toggleViolation}
      />
    ))}
  </>
));

/**
 * Virtualized list for large datasets (>50 violations)
 */
const VirtualizedList = React.memo(({ violations, selectedViolationIds, toggleViolation }) => {
  const itemData = useMemo(() => ({
    violations,
    selectedViolationIds,
    toggleViolation,
  }), [violations, selectedViolationIds, toggleViolation]);

  return (
    <Box sx={{ height: 'calc(100vh - 400px)', minHeight: 400 }}>
      <AutoSizer>
        {({ height, width }) => (
          <List
            height={height}
            width={width}
            itemCount={violations.length}
            itemSize={ITEM_HEIGHT}
            itemData={itemData}
            overscanCount={5}
          >
            {ViolationRow}
          </List>
        )}
      </AutoSizer>
    </Box>
  );
});

/**
 * Main VirtualizedViolationList Component
 * Automatically chooses between virtualized and standard rendering based on item count
 */
const VirtualizedViolationList = ({
  violations,
  selectedViolationIds,
  toggleViolation,
  groupedData = null,
  forceVirtualize = false,
}) => {
  // Use virtualization for large lists or when forced
  const shouldVirtualize = forceVirtualize || violations.length > VIRTUALIZATION_THRESHOLD;

  // If grouped data is provided, render groups with their violations
  if (groupedData && Object.keys(groupedData).length > 0) {
    return (
      <>
        {Object.entries(groupedData).map(([group, items]) => (
          <Box key={group} sx={{ mb: 3 }}>
            <GroupHeader group={group} count={items.length} />
            {items.length > VIRTUALIZATION_THRESHOLD ? (
              <VirtualizedList
                violations={items}
                selectedViolationIds={selectedViolationIds}
                toggleViolation={toggleViolation}
              />
            ) : (
              <StandardViolationList
                violations={items}
                selectedViolationIds={selectedViolationIds}
                toggleViolation={toggleViolation}
              />
            )}
          </Box>
        ))}
      </>
    );
  }

  // Flat list rendering
  if (shouldVirtualize) {
    return (
      <VirtualizedList
        violations={violations}
        selectedViolationIds={selectedViolationIds}
        toggleViolation={toggleViolation}
      />
    );
  }

  return (
    <StandardViolationList
      violations={violations}
      selectedViolationIds={selectedViolationIds}
      toggleViolation={toggleViolation}
    />
  );
};

export default React.memo(VirtualizedViolationList);
