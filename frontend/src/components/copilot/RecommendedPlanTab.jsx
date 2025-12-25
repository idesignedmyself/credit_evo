/**
 * Credit Engine 2.0 - Recommended Plan Tab
 * Displays batched Copilot recommendations organized by bureau and wave
 */
import React, { useEffect, useState } from 'react';
import {
  Box,
  Typography,
  CircularProgress,
  Alert,
  Accordion,
  AccordionSummary,
  AccordionDetails,
  Chip,
  Button,
} from '@mui/material';
import ExpandMoreIcon from '@mui/icons-material/ExpandMore';
import AutoAwesomeIcon from '@mui/icons-material/AutoAwesome';

import useCopilotStore from '../../state/copilotStore';
import { useViolationStore } from '../../state';
import BatchAccordion from './BatchAccordion';
import BatchOverrideModal from './BatchOverrideModal';

export default function RecommendedPlanTab({ reportId, onGenerateLetter }) {
  const [expandedBureaus, setExpandedBureaus] = useState({});
  const [overrideModal, setOverrideModal] = useState({ open: false, batch: null, type: null });

  const {
    batchedRecommendation,
    isLoadingBatched,
    error,
    selectedBatchId,
    fetchBatchedRecommendation,
    setSelectedBatch,
    logBatchOverride,
    getBatch,
    getBatchViolationIds,
  } = useCopilotStore();

  const {
    violations,
    selectedViolationIds,
    setSelectedViolations,
    toggleViolation,
  } = useViolationStore();

  // Fetch batched recommendation on mount/reportId change
  useEffect(() => {
    if (reportId) {
      fetchBatchedRecommendation(reportId);
    }
  }, [reportId, fetchBatchedRecommendation]);

  // Toggle bureau accordion
  const toggleBureau = (bureau) => {
    setExpandedBureaus(prev => ({
      ...prev,
      [bureau]: prev[bureau] === true ? false : true,
    }));
  };

  // Handle batch selection
  const handleSelectBatch = (batch) => {
    if (selectedBatchId === batch.batch_id) {
      // Deselect
      setSelectedBatch(null);
      setSelectedViolations([]);
    } else {
      // Select batch and auto-select its violations
      setSelectedBatch(batch.batch_id);
      setSelectedViolations(batch.violation_ids || []);
    }
  };

  // Handle override request
  const handleOverrideRequest = (batch, type) => {
    setOverrideModal({ open: true, batch, type });
  };

  // Confirm override and proceed
  const handleOverrideConfirm = async () => {
    const { batch, type } = overrideModal;
    if (!batch) return;

    // Log the override
    await logBatchOverride(
      batch.batch_id,
      type,
      batch.is_locked ? 'wait_for_unlock' : 'follow_sequence',
      'proceed_anyway'
    );

    // Select the batch
    setSelectedBatch(batch.batch_id);
    setSelectedViolations(batch.violation_ids || []);

    setOverrideModal({ open: false, batch: null, type: null });
  };

  // Handle generate letter with selected batch
  const handleGenerateLetter = () => {
    if (selectedBatchId && onGenerateLetter) {
      const violationIds = getBatchViolationIds(selectedBatchId);
      onGenerateLetter(violationIds);
    }
  };

  if (isLoadingBatched) {
    return (
      <Box sx={{ display: 'flex', flexDirection: 'column', alignItems: 'center', justifyContent: 'center', py: 6 }}>
        <CircularProgress size={40} />
        <Typography variant="body2" color="text.secondary" sx={{ mt: 2 }}>
          Analyzing your report and creating dispute waves...
        </Typography>
      </Box>
    );
  }

  if (error) {
    return (
      <Alert severity="error" sx={{ m: 2 }}>
        Failed to load recommendations: {error}
      </Alert>
    );
  }

  if (!batchedRecommendation) {
    return (
      <Box sx={{ textAlign: 'center', py: 6, px: 4 }}>
        <AutoAwesomeIcon sx={{ fontSize: 48, color: 'text.disabled', mb: 2 }} />
        <Typography variant="h6" color="text.secondary">
          No Recommendations Available
        </Typography>
        <Typography variant="body2" color="text.secondary">
          Upload a credit report to see personalized dispute recommendations.
        </Typography>
      </Box>
    );
  }

  const { batches_by_bureau } = batchedRecommendation;

  return (
    <Box>
      {/* Bureau Accordions - Clean flat style matching All Accounts tab */}
      <Box>
        {Object.entries(batches_by_bureau || {}).map(([bureau, batches]) => {
          const isExpanded = expandedBureaus[bureau] === true; // Default closed
          const activeBatches = batches.filter(b => !b.is_locked).length;
          const lockedBatches = batches.filter(b => b.is_locked).length;

          return (
            <Accordion
              key={bureau}
              expanded={isExpanded}
              onChange={() => toggleBureau(bureau)}
              disableGutters
              TransitionProps={{ unmountOnExit: true, timeout: 150 }}
              sx={{
                boxShadow: 'none',
                borderBottom: '1px solid',
                borderColor: 'divider',
                '&:before': { display: 'none' },
                '&.Mui-expanded': { margin: 0 },
              }}
            >
              <AccordionSummary
                expandIcon={<ExpandMoreIcon />}
                sx={{
                  bgcolor: 'background.paper',
                  minHeight: 56,
                  '& .MuiAccordionSummary-content': {
                    alignItems: 'center',
                    gap: 2,
                    my: 1.5,
                  },
                }}
              >
                <Typography variant="subtitle1" fontWeight={600}>
                  {bureau}
                </Typography>
                <Box sx={{ display: 'flex', gap: 1, ml: 'auto', mr: 1 }}>
                  {activeBatches > 0 && (
                    <Chip
                      label={`${activeBatches} Ready`}
                      size="small"
                      variant="outlined"
                      sx={{
                        fontWeight: 500,
                        fontSize: '0.75rem',
                        color: 'success.main',
                        borderColor: 'success.main',
                      }}
                    />
                  )}
                  {lockedBatches > 0 && (
                    <Chip
                      label={`${lockedBatches} Locked`}
                      size="small"
                      variant="outlined"
                      sx={{
                        fontWeight: 500,
                        fontSize: '0.75rem',
                        color: 'warning.main',
                        borderColor: 'warning.main',
                      }}
                    />
                  )}
                </Box>
              </AccordionSummary>
              <AccordionDetails sx={{ p: 0, bgcolor: 'grey.50' }}>
                {batches.map((batch) => (
                  <BatchAccordion
                    key={batch.batch_id}
                    batch={batch}
                    isSelected={selectedBatchId === batch.batch_id}
                    isDimmed={selectedBatchId && selectedBatchId !== batch.batch_id}
                    onSelect={handleSelectBatch}
                    onOverride={handleOverrideRequest}
                    violations={violations}
                  />
                ))}
              </AccordionDetails>
            </Accordion>
          );
        })}

        {Object.keys(batches_by_bureau || {}).length === 0 && (
          <Box sx={{ textAlign: 'center', py: 4 }}>
            <Typography variant="body1" color="text.secondary">
              No violations to dispute for your current goal.
            </Typography>
          </Box>
        )}
      </Box>

      {/* Sticky CTA */}
      {selectedBatchId && (
        <Box
          sx={{
            position: 'sticky',
            bottom: 0,
            p: 2,
            bgcolor: 'white',
            borderTop: '1px solid',
            borderColor: 'divider',
            display: 'flex',
            alignItems: 'center',
            justifyContent: 'space-between',
            boxShadow: '0 -4px 12px rgba(0,0,0,0.08)',
          }}
        >
          <Box>
            <Typography variant="subtitle2" fontWeight={600}>
              {getBatchViolationIds(selectedBatchId).length} violations selected
            </Typography>
            <Typography variant="caption" color="text.secondary">
              From Wave {getBatch(selectedBatchId)?.batch_number}
            </Typography>
          </Box>
          <Button
            variant="contained"
            size="large"
            onClick={handleGenerateLetter}
            sx={{ borderRadius: 2, textTransform: 'none', fontWeight: 600, px: 4 }}
          >
            Generate Dispute Letter
          </Button>
        </Box>
      )}

      {/* Override Modal */}
      <BatchOverrideModal
        open={overrideModal.open}
        onClose={() => setOverrideModal({ open: false, batch: null, type: null })}
        onConfirm={handleOverrideConfirm}
        batch={overrideModal.batch}
        overrideType={overrideModal.type}
      />
    </Box>
  );
}
