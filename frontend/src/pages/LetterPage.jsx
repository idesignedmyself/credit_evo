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
  Grid,
  Paper,
  Alert,
} from '@mui/material';
import ArrowBackIcon from '@mui/icons-material/ArrowBack';
import AutorenewIcon from '@mui/icons-material/Autorenew';
import HomeIcon from '@mui/icons-material/Home';
import { ToneSelector, LetterPreview } from '../components';
import { useViolationStore, useUIStore } from '../state';

const steps = ['Upload Report', 'Review Violations', 'Generate Letter'];

const LetterPage = () => {
  const { reportId } = useParams();
  const navigate = useNavigate();
  const { selectedViolationIds, fetchAuditResults } = useViolationStore();
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
          <Alert severity="error" sx={{ mb: 3 }}>
            {error}
          </Alert>
        )}

        <Grid container spacing={3}>
          <Grid item xs={12} md={4}>
            <ToneSelector />

            <Paper sx={{ p: 3, mt: 3 }}>
              <Typography variant="h6" gutterBottom>
                Selected Violations
              </Typography>
              <Typography variant="body2" color="text.secondary" sx={{ mb: 2 }}>
                {selectedViolationIds.length} violation{selectedViolationIds.length !== 1 ? 's' : ''} will be included in your letter.
              </Typography>

              {!currentLetter ? (
                <Button
                  variant="contained"
                  fullWidth
                  onClick={handleGenerate}
                  disabled={isGeneratingLetter || selectedViolationIds.length === 0}
                >
                  {isGeneratingLetter ? 'Generating...' : 'Generate Letter'}
                </Button>
              ) : (
                <Button
                  variant="outlined"
                  fullWidth
                  startIcon={<AutorenewIcon />}
                  onClick={handleRegenerate}
                  disabled={isGeneratingLetter}
                >
                  Regenerate Letter
                </Button>
              )}
            </Paper>

            <Box sx={{ mt: 3 }}>
              <Button
                variant="text"
                startIcon={<ArrowBackIcon />}
                onClick={handleBack}
                fullWidth
              >
                Back to Violations
              </Button>
            </Box>
          </Grid>

          <Grid item xs={12} md={8}>
            <LetterPreview
              letter={currentLetter}
              isLoading={isGeneratingLetter}
              error={error}
            />
          </Grid>
        </Grid>

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
