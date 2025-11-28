/**
 * Credit Engine 2.0 - Violation List Component
 * Displays all violations with selection controls
 */
import React from 'react';
import {
  Box,
  Typography,
  Button,
  Paper,
  Tabs,
  Tab,
  CircularProgress,
  Alert,
} from '@mui/material';
import SelectAllIcon from '@mui/icons-material/SelectAll';
import DeselectIcon from '@mui/icons-material/Deselect';
import ViolationToggle from './ViolationToggle';
import { useViolationStore } from '../state';
import { groupViolationsByType, groupViolationsByAccount } from '../utils';

const ViolationList = () => {
  const [groupBy, setGroupBy] = React.useState('type');
  const {
    violations,
    selectedViolationIds,
    isLoading,
    error,
    toggleViolation,
    selectAll,
    deselectAll,
  } = useViolationStore();

  if (isLoading) {
    return (
      <Box sx={{ display: 'flex', justifyContent: 'center', p: 4 }}>
        <CircularProgress />
      </Box>
    );
  }

  if (error) {
    return (
      <Alert severity="error" sx={{ mb: 2 }}>
        {error}
      </Alert>
    );
  }

  if (!violations || violations.length === 0) {
    return (
      <Paper sx={{ p: 3, textAlign: 'center' }}>
        <Typography variant="body1" color="text.secondary">
          No violations found in this report.
        </Typography>
      </Paper>
    );
  }

  const groupedByType = groupViolationsByType(violations);
  const groupedByAccount = groupViolationsByAccount(violations);
  const grouped = groupBy === 'type' ? groupedByType : groupedByAccount;

  return (
    <Box>
      <Paper sx={{ p: 2, mb: 2 }}>
        <Box sx={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', flexWrap: 'wrap', gap: 2 }}>
          <Typography variant="h6">
            {violations.length} Violations Found
          </Typography>

          <Box sx={{ display: 'flex', gap: 1 }}>
            <Button
              size="small"
              startIcon={<SelectAllIcon />}
              onClick={selectAll}
              variant="outlined"
            >
              Select All
            </Button>
            <Button
              size="small"
              startIcon={<DeselectIcon />}
              onClick={deselectAll}
              variant="outlined"
            >
              Deselect All
            </Button>
          </Box>
        </Box>

        <Typography variant="body2" color="text.secondary" sx={{ mt: 1 }}>
          {selectedViolationIds.length} selected · {violations.length} total
        </Typography>
      </Paper>

      <Tabs
        value={groupBy}
        onChange={(e, v) => setGroupBy(v)}
        sx={{ mb: 2 }}
      >
        <Tab value="type" label="Group by Type" />
        <Tab value="account" label="Group by Account" />
      </Tabs>

      {Object.entries(grouped).map(([groupName, groupViolations]) => (
        <Box key={groupName} sx={{ mb: 3 }}>
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
            {groupName} ({groupViolations.length})
          </Typography>

          {groupViolations.map((violation) => (
            <ViolationToggle
              key={violation.violation_id}
              violation={violation}
              isSelected={selectedViolationIds.includes(violation.violation_id)}
              onToggle={toggleViolation}
            />
          ))}
        </Box>
      ))}
    </Box>
  );
};

export default ViolationList;
