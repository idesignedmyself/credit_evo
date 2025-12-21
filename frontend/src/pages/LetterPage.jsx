/**
 * Credit Engine 2.0 - Letter Page
 * Letter customization and generation with modern UI
 */
import React, { useEffect } from 'react';
import { useParams, useNavigate, useSearchParams } from 'react-router-dom';
import {
  Box,
  Typography,
  Button,
  Paper,
  Alert,
  Stepper,
  Step,
  StepLabel,
  Chip,
  Stack,
} from '@mui/material';
import ArrowBackIcon from '@mui/icons-material/ArrowBack';
import HomeIcon from '@mui/icons-material/Home';
import AutoAwesomeIcon from '@mui/icons-material/AutoAwesome';
import SendIcon from '@mui/icons-material/Send';
import { ToneSelector, LetterPreview } from '../components';
import { useViolationStore, useUIStore } from '../state';
import { getViolationLabel } from '../utils';
import { createDisputeFromLetter } from '../api/disputeApi';

const steps = ['Upload Report', 'Review Violations', 'Generate Letter'];

const LetterPage = () => {
  const { reportId } = useParams();
  const [searchParams] = useSearchParams();
  const letterId = searchParams.get('letterId');
  const letterType = searchParams.get('type'); // 'response' for response letters
  const isResponseLetter = letterType === 'response';
  const navigate = useNavigate();
  const [isCreatingDispute, setIsCreatingDispute] = React.useState(false);
  const [disputeError, setDisputeError] = React.useState(null);
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

    // No letterId means we're generating a new letter - clear any existing letter
    // so the user sees the "Ready to Generate" state
    clearLetter();

    // If no violations selected, fetch audit results
    if (selectedViolationIds.length === 0) {
      fetchAuditResults(reportId);
    }
  }, [reportId, letterId, selectedViolationIds.length, fetchAuditResults, fetchTones, loadSavedLetter, clearLetter]);

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

  const handleTrackDispute = async () => {
    if (!currentLetter) return;

    setIsCreatingDispute(true);
    setDisputeError(null);

    // Build violation data from the letter's stored data
    // When viewing a saved letter, selectedViolations may be empty,
    // so we use the letter's violations_cited and accounts_disputed
    let violationData = [];

    if (selectedViolations.length > 0) {
      // Use current selection if available (just generated)
      violationData = selectedViolations.map(v => ({
        violation_id: v.violation_id,
        violation_type: v.violation_type,
        creditor_name: v.creditor_name,
        account_number_masked: v.account_number_masked,
        severity: v.severity,
      }));
    } else if (currentLetter.violations_cited || currentLetter.accounts_disputed) {
      // Reconstruct from saved letter data
      const violationTypes = currentLetter.violations_cited || [];
      const accounts = currentLetter.accounts_disputed || [];
      const accountNumbers = currentLetter.account_numbers || [];
      const maxLen = Math.max(violationTypes.length, accounts.length);

      for (let i = 0; i < maxLen; i++) {
        violationData.push({
          violation_id: `${currentLetter.letter_id}-v${i}`,
          violation_type: violationTypes[i] || 'unknown',
          creditor_name: accounts[i] || 'Unknown',
          account_number_masked: accountNumbers[i] || null,
          severity: 'MEDIUM',
        });
      }
    }

    try {
      await createDisputeFromLetter(currentLetter.letter_id, {
        entity_type: 'CRA',
        entity_name: currentLetter.bureau || auditResult?.bureau,
        violation_ids: violationData.map(v => v.violation_id),
        violation_data: violationData,
      });
      // Navigate to disputes page after creating
      navigate('/disputes');
    } catch (err) {
      // If backend isn't ready, still navigate to disputes page
      // The dispute will need to be created when backend is available
      console.error('Failed to create dispute:', err);
      setDisputeError('Could not create dispute record. You can still track it manually on the Disputes page.');
      // Navigate anyway after a brief delay
      setTimeout(() => navigate('/disputes'), 2000);
    } finally {
      setIsCreatingDispute(false);
    }
  };
  const stats = {
    violations: selectedViolations.length,
    accounts: [...new Set(selectedViolations.map(v => v.account_id))].length,
  };

  // Group violations by type with account details
  // Use selectedViolations if available, otherwise reconstruct from letter data
  const violationsByType = React.useMemo(() => {
    if (selectedViolations.length > 0) {
      // Use current selection (just generated)
      return selectedViolations.reduce((acc, v) => {
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
    } else if (currentLetter?.violations_cited || currentLetter?.accounts_disputed) {
      // Reconstruct from saved letter data
      const violationTypes = currentLetter.violations_cited || [];
      const accounts = currentLetter.accounts_disputed || [];
      const accountNumbers = currentLetter.account_numbers || [];
      const result = {};

      // Build grouped structure from letter data
      violationTypes.forEach((type, idx) => {
        const label = getViolationLabel(type);
        if (!result[label]) {
          result[label] = [];
        }
        result[label].push({
          creditorName: accounts[idx] || 'Unknown Creditor',
          accountNumber: accountNumbers[idx] || '',
        });
      });

      // Handle case where accounts > violation types
      if (accounts.length > violationTypes.length) {
        for (let i = violationTypes.length; i < accounts.length; i++) {
          const label = 'Disputed Item';
          if (!result[label]) {
            result[label] = [];
          }
          result[label].push({
            creditorName: accounts[i] || 'Unknown Creditor',
            accountNumber: accountNumbers[i] || '',
          });
        }
      }

      return result;
    }
    return {};
  }, [selectedViolations, currentLetter]);

  return (
    <Box>
      {/* Page Header */}
      <Box sx={{ textAlign: 'center', mb: 4 }}>
        <Typography variant="h4" component="h1" gutterBottom sx={{ fontWeight: 'bold' }}>
          {isResponseLetter ? 'Generate Response Letter' : 'Generate Dispute Letter'}
        </Typography>
        <Typography variant="body1" color="text.secondary">
          {isResponseLetter
            ? 'View your FCRA enforcement correspondence'
            : 'Customize and generate your FCRA-compliant dispute letter'}
        </Typography>
      </Box>

      {/* Stepper - Hide for response letters */}
      {!isResponseLetter && (
        <Box sx={{ width: '100%', mb: 4, maxWidth: 600, mx: 'auto' }}>
          <Stepper activeStep={2} alternativeLabel>
            {steps.map((label) => (
              <Step key={label}>
                <StepLabel>{label}</StepLabel>
              </Step>
            ))}
          </Stepper>
        </Box>
      )}

      {error && (
        <Alert severity="error" sx={{ mb: 3, borderRadius: 2 }}>
          {error}
        </Alert>
      )}

      {/* Letter Customization Section - Hide for response letters */}
      {!isResponseLetter && (
        <Box sx={{ mb: 4 }}>
          <ToneSelector />
        </Box>
      )}

      {/* Action Bar - Different for response letters */}
      {isResponseLetter ? (
        <Paper
          elevation={0}
          sx={{
            p: 2,
            mb: 4,
            bgcolor: '#e8f5e9',
            border: '1px solid',
            borderColor: '#a5d6a7',
            borderRadius: 2,
            display: 'flex',
            justifyContent: 'space-between',
            alignItems: 'center',
          }}
        >
          <Box>
            <Typography variant="subtitle1" sx={{ fontWeight: 'bold', color: 'success.dark' }}>
              Response Letter
            </Typography>
            <Typography variant="caption" color="text.secondary">
              FCRA enforcement correspondence
            </Typography>
          </Box>
          <Button
            variant="text"
            startIcon={<ArrowBackIcon />}
            onClick={() => navigate('/letters')}
            size="small"
          >
            Back to Letters
          </Button>
        </Paper>
      ) : (
        <Paper
          elevation={0}
          sx={{
            p: 2,
            mb: 4,
            bgcolor: currentLetter ? '#e8f5e9' : '#e3f2fd',
            border: '1px solid',
            borderColor: currentLetter ? '#a5d6a7' : '#bbdefb',
            borderRadius: 2,
            display: 'flex',
            justifyContent: 'space-between',
            alignItems: 'center',
            flexWrap: 'wrap',
            gap: 2,
          }}
        >
          <Box>
            <Typography
              variant="subtitle1"
              sx={{ fontWeight: 'bold', color: currentLetter ? 'success.dark' : 'primary.main' }}
            >
              {currentLetter ? 'Letter Generated' : 'Ready to Generate'}
            </Typography>
            <Typography variant="caption" color="text.secondary">
              {selectedViolationIds.length} violation{selectedViolationIds.length !== 1 ? 's' : ''} selected
            </Typography>
          </Box>
          <Stack direction="row" spacing={1}>
            <Button
              variant="text"
              startIcon={<ArrowBackIcon />}
              onClick={handleBack}
              size="small"
            >
              Back
            </Button>
            {currentLetter ? (
              <Button
                variant="outlined"
                size="large"
                onClick={handleRegenerate}
                disabled={isGeneratingLetter}
                startIcon={<AutoAwesomeIcon />}
              >
                {isGeneratingLetter ? 'Regenerating...' : 'Regenerate'}
              </Button>
            ) : (
              <Button
                variant="contained"
                size="large"
                onClick={handleGenerate}
                disabled={isGeneratingLetter || selectedViolationIds.length === 0}
                startIcon={<AutoAwesomeIcon />}
                disableElevation
              >
                {isGeneratingLetter ? 'Generating...' : 'Generate Letter'}
              </Button>
            )}
          </Stack>
        </Paper>
      )}

      {/* Letter Preview */}
      <LetterPreview
        letter={currentLetter}
        isLoading={isGeneratingLetter}
        error={error}
        onRegenerate={currentLetter ? handleRegenerate : null}
        isRegenerating={isGeneratingLetter}
        stats={stats}
        isResponseLetter={isResponseLetter}
      />

      {currentLetter && (
        <>
          {/* Track Dispute CTA - Hide for response letters (already linked to dispute) */}
          {!isResponseLetter && (
            <Paper
              elevation={0}
              sx={{
                p: 3,
                mt: 4,
                borderRadius: 3,
                border: '2px solid',
                borderColor: 'primary.main',
                backgroundColor: '#e3f2fd',
                textAlign: 'center',
              }}
            >
              <Typography variant="h6" sx={{ fontWeight: 'bold', mb: 1 }}>
                Track This Dispute
              </Typography>
              <Typography variant="body2" color="text.secondary" sx={{ mb: 2, maxWidth: 500, mx: 'auto' }}>
                Click below to add this letter to your dispute tracker. You'll enter the send date
                on the Disputes page to start the 30-day response clock.
              </Typography>
              {disputeError && (
                <Alert severity="warning" sx={{ mb: 2, maxWidth: 500, mx: 'auto' }}>
                  {disputeError}
                </Alert>
              )}
              <Button
                variant="contained"
                size="large"
                startIcon={<SendIcon />}
                onClick={handleTrackDispute}
                disabled={isCreatingDispute}
                disableElevation
                sx={{ px: 4 }}
              >
                {isCreatingDispute ? 'Creating...' : 'Start Tracking Process'}
              </Button>
            </Paper>
          )}

          {/* Violation Types Summary */}
          {Object.keys(violationsByType).length > 0 && (
            <Paper
              elevation={0}
              sx={{
                p: 3,
                mt: 4,
                borderRadius: 3,
                border: '1px solid',
                borderColor: 'divider',
                backgroundColor: '#fafafa',
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
                Violations Included ({selectedViolations.length || currentLetter?.violation_count || Object.values(violationsByType).flat().length})
              </Typography>
              <Stack spacing={2}>
                {Object.entries(violationsByType)
                  .sort((a, b) => b[1].length - a[1].length)
                  .map(([type, accounts]) => (
                    <Box key={type}>
                      <Stack direction="row" spacing={1} alignItems="center" sx={{ mb: 0.5 }}>
                        <Typography variant="body2" sx={{ fontWeight: 600 }}>
                          {type}
                        </Typography>
                        <Chip label={accounts.length} size="small" color="primary" variant="outlined" />
                      </Stack>
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
              </Stack>
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
  );
};

export default LetterPage;
