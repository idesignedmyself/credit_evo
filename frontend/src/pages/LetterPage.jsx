/**
 * Credit Engine 2.0 - Letter Page
 * Letter customization and generation
 */
import React, { useEffect } from 'react';
import { useParams, useNavigate, useSearchParams } from 'react-router-dom';
import {
  Container,
  Box,
  Typography,
  Button,
  Paper,
  Alert,
} from '@mui/material';
import ArrowBackIcon from '@mui/icons-material/ArrowBack';
import HomeIcon from '@mui/icons-material/Home';
import Chip from '@mui/material/Chip';
import { ToneSelector, LetterPreview } from '../components';
import { useViolationStore, useUIStore } from '../state';
import { getViolationLabel } from '../utils';

const LetterPage = () => {
  const { reportId } = useParams();
  const [searchParams] = useSearchParams();
  const letterId = searchParams.get('letterId');
  const navigate = useNavigate();
  const { selectedViolationIds, selectedDiscrepancyIds, violations, auditResult, fetchAuditResults } = useViolationStore();
  const {
    currentLetter,
    isGeneratingLetter,
    error,
    generateLetter,
    clearLetter,
    fetchTones,
    loadSavedLetter,
    setBureau,
  } = useUIStore();

  useEffect(() => {
    fetchTones();

    // If we have a letterId, load the saved letter
    if (letterId) {
      loadSavedLetter(letterId);
      return;
    }

    // Otherwise, if no violations selected, fetch audit results
    if (selectedViolationIds.length === 0) {
      fetchAuditResults(reportId);
    }
  }, [reportId, letterId, selectedViolationIds.length, fetchAuditResults, fetchTones, loadSavedLetter]);

  // Auto-set bureau from audit result when loaded
  useEffect(() => {
    if (auditResult?.bureau) {
      setBureau(auditResult.bureau.toLowerCase());
    }
  }, [auditResult, setBureau]);

  const handleBack = () => {
    navigate(`/audit/${reportId}`);
  };

  const handleGenerate = async () => {
    try {
      await generateLetter(reportId, selectedViolationIds, selectedDiscrepancyIds);
    } catch (err) {
      // Error handled by store
    }
  };

  const handleRegenerate = () => {
    clearLetter();
    handleGenerate();
  };

  const handleStartOver = () => {
    clearLetter();
    navigate('/upload');
  };

  // Calculate stats from SELECTED violations only
  const selectedViolations = violations.filter(v => selectedViolationIds.includes(v.violation_id));
  const stats = {
    violations: selectedViolations.length,
    accounts: [...new Set(selectedViolations.map(v => v.account_id))].length,
  };

  // Group selected violations by type with account details
  const violationsByType = selectedViolations.reduce((acc, v) => {
    const label = getViolationLabel(v.violation_type);
    if (!acc[label]) {
      acc[label] = [];
    }
    acc[label].push({
      creditorName: v.creditor_name || 'Unknown Creditor',
      accountNumber: v.account_number_masked || '',
    });
    return acc;
  }, {});

  return (
    <Container maxWidth="lg">
      <Box sx={{ py: 4 }}>
        {error && (
          <Alert severity="error" sx={{ mb: 3, borderRadius: 2 }}>
            {error}
          </Alert>
        )}

        {/* Letter Customization Section - Above Everything */}
        <Box sx={{ mb: 4 }}>
          <ToneSelector />
        </Box>

        {/* Generate Section */}
        <Paper
          elevation={2}
          sx={{
            p: 3,
            mb: 4,
            borderRadius: 3,
            boxShadow: '0 1px 3px rgba(0,0,0,0.12)',
          }}
        >
          <Box sx={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', flexWrap: 'wrap', gap: 2 }}>
            <Box>
              <Typography variant="h6" gutterBottom sx={{ mb: 0.5 }}>
                Ready to Generate
              </Typography>
              <Typography variant="body2" color="text.secondary">
                {selectedViolationIds.length} violation{selectedViolationIds.length !== 1 ? 's' : ''} selected for your dispute letter.
              </Typography>
            </Box>
            <Box sx={{ display: 'flex', gap: 2, alignItems: 'center' }}>
              <Button
                variant="text"
                startIcon={<ArrowBackIcon />}
                onClick={handleBack}
              >
                Back to Violations
              </Button>
              <Button
                variant="contained"
                size="large"
                onClick={handleGenerate}
                disabled={isGeneratingLetter || selectedViolationIds.length === 0 || currentLetter}
              >
                {isGeneratingLetter ? 'Generating...' : 'Generate Letter'}
              </Button>
            </Box>
          </Box>
        </Paper>

        {/* Letter Preview - Full Width */}
        <LetterPreview
          letter={currentLetter}
          isLoading={isGeneratingLetter}
          error={error}
          onRegenerate={currentLetter ? handleRegenerate : null}
          isRegenerating={isGeneratingLetter}
          stats={stats}
        />

        {currentLetter && (
          <>
            {/* Violation Types Summary */}
            {Object.keys(violationsByType).length > 0 && (
              <Paper
                elevation={1}
                sx={{
                  p: 3,
                  mt: 4,
                  borderRadius: 2,
                  backgroundColor: 'grey.50',
                }}
              >
                <Typography
                  variant="subtitle1"
                  sx={{
                    fontWeight: 'bold',
                    mb: 2,
                    pb: 1,
                    borderBottom: '2px solid',
                    borderColor: 'primary.main',
                  }}
                >
                  Violation Types Included ({selectedViolations.length})
                </Typography>
                {Object.entries(violationsByType)
                  .sort((a, b) => b[1].length - a[1].length)
                  .map(([type, accounts]) => (
                    <Box key={type} sx={{ mb: 2 }}>
                      <Typography variant="body2" sx={{ fontWeight: 'bold', mb: 0.5 }}>
                        {type}
                      </Typography>
                      <Box sx={{ pl: 2 }}>
                        {accounts.map((account, idx) => (
                          <Typography
                            key={idx}
                            variant="body2"
                            color="text.secondary"
                            sx={{ fontSize: '0.85rem' }}
                          >
                            {account.creditorName}
                            {account.accountNumber && ` (${account.accountNumber})`}
                          </Typography>
                        ))}
                      </Box>
                    </Box>
                  ))}
              </Paper>
            )}

            <Box sx={{ display: 'flex', justifyContent: 'center', mt: 4 }}>
              <Button
                variant="outlined"
                startIcon={<HomeIcon />}
                onClick={handleStartOver}
              >
                Start Over with New Report
              </Button>
            </Box>
          </>
        )}
      </Box>
    </Container>
  );
};

export default LetterPage;
