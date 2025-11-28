/**
 * Credit Engine 2.0 - Letter Page
 * Letter customization and generation
 */
import React, { useEffect } from 'react';
import { useParams, useNavigate } from 'react-router-dom';
import {
  Container,
  Box,
  Typography,
  Button,
  Stepper,
  Step,
  StepLabel,
  Paper,
  Alert,
} from '@mui/material';
import ArrowBackIcon from '@mui/icons-material/ArrowBack';
import HomeIcon from '@mui/icons-material/Home';
import { ToneSelector, LetterPreview } from '../components';
import { useViolationStore, useUIStore } from '../state';

const steps = ['Upload Report', 'Review Violations', 'Generate Letter'];

const LetterPage = () => {
  const { reportId } = useParams();
  const navigate = useNavigate();
  const { selectedViolationIds, violations, fetchAuditResults } = useViolationStore();
  const {
    currentLetter,
    isGeneratingLetter,
    error,
    generateLetter,
    clearLetter,
    fetchTones,
  } = useUIStore();

  useEffect(() => {
    fetchTones();
    // If no violations selected, redirect back to audit
    if (selectedViolationIds.length === 0) {
      fetchAuditResults(reportId);
    }
  }, [reportId, selectedViolationIds.length, fetchAuditResults, fetchTones]);

  const handleBack = () => {
    navigate(`/audit/${reportId}`);
  };

  const handleGenerate = async () => {
    try {
      await generateLetter(reportId, selectedViolationIds);
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

  return (
    <Container maxWidth="lg">
      <Box sx={{ py: 4 }}>
        <Typography variant="h4" component="h1" gutterBottom align="center">
          Credit Engine 2.0
        </Typography>

        <Stepper activeStep={2} sx={{ mb: 4 }}>
          {steps.map((label) => (
            <Step key={label}>
              <StepLabel>{label}</StepLabel>
            </Step>
          ))}
        </Stepper>

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
          <Box sx={{ display: 'flex', justifyContent: 'center', mt: 4 }}>
            <Button
              variant="outlined"
              startIcon={<HomeIcon />}
              onClick={handleStartOver}
            >
              Start Over with New Report
            </Button>
          </Box>
        )}
      </Box>
    </Container>
  );
};

export default LetterPage;
