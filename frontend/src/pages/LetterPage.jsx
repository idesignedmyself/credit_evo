/**
 * Credit Engine 2.0 - Letter Page
 * Letter customization and generation with modern UI
 * Unified dispute flow - everything happens on this page
 */
import React, { useEffect, useState } from 'react';
import { useParams, useNavigate, useSearchParams } from 'react-router-dom';
import {
  Box,
  Typography,
  Button,
  Paper,
  Alert,
  Chip,
  Stack,
  Accordion,
  AccordionSummary,
  AccordionDetails,
  TextField,
  FormControl,
  InputLabel,
  Select,
  MenuItem,
  Tooltip,
  CircularProgress,
  Divider,
} from '@mui/material';
import { DatePicker } from '@mui/x-date-pickers/DatePicker';
import { LocalizationProvider } from '@mui/x-date-pickers/LocalizationProvider';
import { AdapterDayjs } from '@mui/x-date-pickers/AdapterDayjs';
import dayjs from 'dayjs';
import { jsPDF } from 'jspdf';
import ExpandMoreIcon from '@mui/icons-material/ExpandMore';
import LockIcon from '@mui/icons-material/Lock';
import CheckCircleIcon from '@mui/icons-material/CheckCircle';
import MailOutlineIcon from '@mui/icons-material/MailOutline';
import AccountBalanceIcon from '@mui/icons-material/AccountBalance';
import GavelIcon from '@mui/icons-material/Gavel';
import ArrowBackIcon from '@mui/icons-material/ArrowBack';
import HomeIcon from '@mui/icons-material/Home';
import AutoAwesomeIcon from '@mui/icons-material/AutoAwesome';
import SaveIcon from '@mui/icons-material/Save';
import EditIcon from '@mui/icons-material/Edit';
import VisibilityIcon from '@mui/icons-material/Visibility';
import ContentCopyIcon from '@mui/icons-material/ContentCopy';
import DownloadIcon from '@mui/icons-material/Download';
import DescriptionIcon from '@mui/icons-material/Description';
import { LetterPreview } from '../components';
import { useViolationStore, useUIStore } from '../state';
import { getViolationLabel } from '../utils';
import {
  createDisputeFromLetter,
  startTracking,
  logResponse,
  generateResponseLetter,
  saveResponseLetter,
  RESPONSE_TYPES,
} from '../api/disputeApi';

// =============================================================================
// VIOLATION RESPONSE CARD - Shows violation info with response dropdown
// =============================================================================
const ViolationResponseCard = ({
  violation,
  responseType,
  onResponseTypeChange,
  trackingStarted,
  deadlineDate,
  isLocked,
}) => {
  const isNoResponseAvailable = () => {
    if (!trackingStarted || !deadlineDate) return false;
    const deadline = new Date(deadlineDate);
    const today = new Date();
    today.setHours(0, 0, 0, 0);
    deadline.setHours(0, 0, 0, 0);
    return today > deadline;
  };

  const getResponseChipColor = (type) => {
    switch (type) {
      case 'DELETED': return 'success';
      case 'VERIFIED': return 'warning';
      case 'NO_RESPONSE': return 'error';
      case 'REJECTED': return 'error';
      case 'REINSERTION': return 'error';
      default: return 'default';
    }
  };

  return (
    <Box
      sx={{
        p: 2.5,
        bgcolor: 'white',
        borderRadius: 2,
        border: '1px solid',
        borderColor: 'divider',
        mb: 2,
      }}
    >
      <Box sx={{ mb: 2, display: 'flex', justifyContent: 'space-between', alignItems: 'flex-start' }}>
        <Box>
          <Typography variant="subtitle2" sx={{ fontWeight: 600, mb: 0.5 }}>
            {violation.creditor_name || violation.creditorName || 'Unknown Creditor'}
            {(violation.account_number_masked || violation.accountNumber) && (
              <Typography component="span" variant="body2" color="text.secondary" sx={{ ml: 1, fontWeight: 400 }}>
                ({violation.account_number_masked || violation.accountNumber})
              </Typography>
            )}
          </Typography>
          <Stack direction="row" spacing={1} alignItems="center">
            <Chip
              label={violation.violation_type?.replace(/_/g, ' ') || getViolationLabel(violation.violation_type) || 'Violation'}
              size="small"
              color="error"
              variant="outlined"
              sx={{ textTransform: 'capitalize' }}
            />
            {violation.severity && (
              <Chip
                label={violation.severity}
                size="small"
                sx={{ height: 22, fontSize: '0.7rem' }}
                color={violation.severity === 'HIGH' ? 'error' : violation.severity === 'MEDIUM' ? 'warning' : 'default'}
                variant="outlined"
              />
            )}
            {responseType && (
              <Chip
                label={RESPONSE_TYPES[responseType]?.label || responseType}
                size="small"
                color={getResponseChipColor(responseType)}
                variant="filled"
                sx={{ height: 22, fontSize: '0.7rem' }}
              />
            )}
          </Stack>
        </Box>
      </Box>

      <FormControl size="small" sx={{ minWidth: 220 }}>
        <InputLabel>Response *</InputLabel>
        <Select
          value={responseType}
          label="Response *"
          onChange={(e) => onResponseTypeChange(violation.violation_id, e.target.value)}
          disabled={isLocked || !!violation.logged_response}
        >
          <MenuItem value="">
            <em>Select outcome...</em>
          </MenuItem>
          {Object.entries(RESPONSE_TYPES).map(([key, config]) => {
            const isNoResponseBlocked = key === 'NO_RESPONSE' && !isNoResponseAvailable();

            if (isNoResponseBlocked) {
              const disabledReason = !trackingStarted ? 'Start tracking first' : 'Deadline has not passed';
              return (
                <Tooltip key={key} title={disabledReason} placement="right" arrow>
                  <span>
                    <MenuItem value={key} disabled>
                      {config.label}
                    </MenuItem>
                  </span>
                </Tooltip>
              );
            }

            return (
              <MenuItem key={key} value={key} title={config.description}>
                {config.label}
                {!config.enforcement && ' (resolution)'}
              </MenuItem>
            );
          })}
        </Select>
      </FormControl>

      {violation.logged_response && (
        <Alert severity="info" sx={{ mt: 1.5, py: 0.5 }} icon={<LockIcon />}>
          <Typography variant="caption">
            Response logged as <strong>{RESPONSE_TYPES[violation.logged_response]?.label || violation.logged_response}</strong>.
          </Typography>
        </Alert>
      )}

      {responseType === 'VERIFIED' && !violation.logged_response && (
        <Alert severity="info" sx={{ mt: 1.5, py: 0.5 }} icon={false}>
          <Typography variant="caption">
            <strong>Strategic note:</strong> "Verified" means the bureau claims the furnisher confirmed the data.
            You may demand their Method of Verification and challenge the substantive accuracy.
          </Typography>
        </Alert>
      )}
      {responseType === 'NO_RESPONSE' && !violation.logged_response && (
        <Alert severity="warning" sx={{ mt: 1.5, py: 0.5 }} icon={false}>
          <Typography variant="caption">
            <strong>Strategic note:</strong> No response within the statutory deadline is a procedural violation.
            Generate an enforcement letter citing 15 U.S.C. §1681i(a)(1) failure to investigate.
          </Typography>
        </Alert>
      )}
    </Box>
  );
};

const LetterPage = () => {
  const { reportId } = useParams();
  const [searchParams] = useSearchParams();
  const letterId = searchParams.get('letterId');
  const letterType = searchParams.get('type'); // 'response' for response letters
  const responseTypeFromUrl = searchParams.get('responseType'); // REINSERTION, VERIFIED, etc.
  const isResponseLetter = letterType === 'response';
  const navigate = useNavigate();

  // Dispute tracking state
  const [activeDispute, setActiveDispute] = useState(null);
  const [expandedStage, setExpandedStage] = useState('initial');
  const [stageData, setStageData] = useState({
    initial: { status: 'ready', sentDate: null },
    response: { status: 'locked', responseDate: null },
    final: { status: 'locked', responseDate: null },
    cfpb1: { status: 'locked' },
    cfpb2: { status: 'locked' },
    legal: { status: 'locked' },
  });
  const [isStartingTracking, setIsStartingTracking] = useState(false);

  // Response logging state
  const [responseTypes, setResponseTypes] = useState({});
  const [sharedResponseDate, setSharedResponseDate] = useState(null);
  const [submittingResponse, setSubmittingResponse] = useState(false);
  const [responseSuccess, setResponseSuccess] = useState(false);
  const [responseError, setResponseError] = useState(null);

  // Inline letter generation state
  const [generatedRebuttalLetter, setGeneratedRebuttalLetter] = useState(null);
  const [rebuttalLetterLoading, setRebuttalLetterLoading] = useState(false);
  const [editableRebuttalContent, setEditableRebuttalContent] = useState('');
  const [isEditingRebuttal, setIsEditingRebuttal] = useState(false);
  const [isSavingRebuttal, setIsSavingRebuttal] = useState(false);
  const [rebuttalCopied, setRebuttalCopied] = useState(false);
  const { selectedViolationIds, selectedDiscrepancyIds, violations, auditResult, fetchAuditResults } = useViolationStore();
  const {
    currentLetter,
    isGeneratingLetter,
    error,
    generateLetter,
    clearLetter,
    loadSavedLetter,
    setBureau,
    documentChannel,
    setDocumentChannel,
  } = useUIStore();

  // Read channel from URL param and set it
  const channelFromUrl = searchParams.get('channel');
  useEffect(() => {
    if (channelFromUrl && ['MAILED', 'CFPB'].includes(channelFromUrl)) {
      setDocumentChannel(channelFromUrl);
    }
  }, [channelFromUrl, setDocumentChannel]);

  useEffect(() => {
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
  }, [reportId, letterId, selectedViolationIds.length, fetchAuditResults, loadSavedLetter, clearLetter]);

  // Auto-set bureau from audit result when loaded
  useEffect(() => {
    if (auditResult?.bureau) {
      setBureau(auditResult.bureau.toLowerCase());
    }
  }, [auditResult, setBureau]);

  // Auto-generate letter when arriving with channel param from AuditPage
  const hasAutoGenerated = React.useRef(false);
  useEffect(() => {
    if (
      channelFromUrl &&
      selectedViolationIds.length > 0 &&
      !currentLetter &&
      !isGeneratingLetter &&
      !letterId &&
      !hasAutoGenerated.current
    ) {
      hasAutoGenerated.current = true;
      generateLetter(reportId, selectedViolationIds, selectedDiscrepancyIds);
    }
  }, [channelFromUrl, selectedViolationIds, currentLetter, isGeneratingLetter, letterId, reportId, selectedDiscrepancyIds, generateLetter]);

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

  // Build violation data from letter for dispute creation
  const buildViolationData = () => {
    if (selectedViolations.length > 0) {
      return selectedViolations.map(v => ({
        violation_id: v.violation_id,
        violation_type: v.violation_type,
        creditor_name: v.creditor_name,
        account_number_masked: v.account_number_masked,
        severity: v.severity,
      }));
    } else if (currentLetter?.violations_cited || currentLetter?.accounts_disputed) {
      const violationTypes = currentLetter.violations_cited || [];
      const accounts = currentLetter.accounts_disputed || [];
      const accountNumbers = currentLetter.account_numbers || [];
      const maxLen = Math.max(violationTypes.length, accounts.length);
      const data = [];
      for (let i = 0; i < maxLen; i++) {
        data.push({
          violation_id: `${currentLetter.letter_id}-v${i}`,
          violation_type: violationTypes[i] || 'unknown',
          creditor_name: accounts[i] || 'Unknown',
          account_number_masked: accountNumbers[i] || null,
          severity: 'MEDIUM',
        });
      }
      return data;
    }
    return [];
  };

  // Start tracking: creates dispute record AND starts the deadline clock
  const handleStartTracking = async () => {
    if (!currentLetter || !stageData.initial.sentDate) return;

    setIsStartingTracking(true);
    try {
      const violationData = buildViolationData();

      // Create dispute from letter
      const dispute = await createDisputeFromLetter(currentLetter.letter_id, {
        entity_type: 'CRA',
        entity_name: currentLetter.bureau || auditResult?.bureau,
        violation_ids: violationData.map(v => v.violation_id),
        violation_data: violationData,
      });

      // Start tracking with the sent date
      await startTracking(dispute.id, stageData.initial.sentDate, null);

      // Update local state
      setActiveDispute({
        ...dispute,
        tracking_started: true,
        dispute_date: stageData.initial.sentDate,
        deadline_date: dayjs(stageData.initial.sentDate).add(30, 'day').format('YYYY-MM-DD'),
        violation_data: violationData,
      });

      // Initialize response types for violations
      const initialTypes = {};
      violationData.forEach(v => { initialTypes[v.violation_id] = ''; });
      setResponseTypes(initialTypes);

      // Unlock the response stage
      setStageData(prev => ({
        ...prev,
        initial: { ...prev.initial, status: 'complete' },
        response: { ...prev.response, status: 'ready' },
      }));
      setExpandedStage('response');
    } catch (err) {
      console.error('Failed to start tracking:', err);
      setResponseError(err.message || 'Failed to create dispute');
    } finally {
      setIsStartingTracking(false);
    }
  };

  // Handle response type change for a violation
  const handleResponseTypeChange = (violationId, newType) => {
    setResponseTypes(prev => ({ ...prev, [violationId]: newType }));
  };

  // Save all responses and auto-generate letter if needed
  const handleSaveAndLog = async () => {
    if (!activeDispute) return;

    const violationData = activeDispute.violation_data || [];
    const pendingResponses = violationData.filter(
      v => responseTypes[v.violation_id] && !v.logged_response
    );

    if (pendingResponses.length === 0) {
      setResponseError('Please select at least one response type');
      return;
    }

    setSubmittingResponse(true);
    setResponseError(null);

    try {
      const responseDate = sharedResponseDate
        ? sharedResponseDate.format('YYYY-MM-DD')
        : dayjs().format('YYYY-MM-DD');

      // Log each response
      for (const v of pendingResponses) {
        await logResponse(activeDispute.id, {
          violation_id: v.violation_id,
          response_type: responseTypes[v.violation_id],
          response_date: responseDate,
        });
      }

      // Check if any require enforcement letter
      const hasEnforcement = pendingResponses.some(
        v => ['NO_RESPONSE', 'VERIFIED', 'REJECTED', 'REINSERTION'].includes(responseTypes[v.violation_id])
      );

      // Auto-generate rebuttal letter if enforcement response
      if (hasEnforcement) {
        setRebuttalLetterLoading(true);
        const enforcementItem = pendingResponses.find(
          v => ['NO_RESPONSE', 'VERIFIED', 'REJECTED', 'REINSERTION'].includes(responseTypes[v.violation_id])
        );
        if (enforcementItem) {
          try {
            const result = await generateResponseLetter(activeDispute.id, {
              response_type: responseTypes[enforcementItem.violation_id],
              violation_id: enforcementItem.violation_id,
              include_willful_notice: true,
            });
            setGeneratedRebuttalLetter(result);
            setEditableRebuttalContent(result.content);
          } catch (letterErr) {
            console.error('Failed to generate rebuttal letter:', letterErr);
          } finally {
            setRebuttalLetterLoading(false);
          }
        }
      }

      // Mark violations as logged in local state
      setActiveDispute(prev => ({
        ...prev,
        violation_data: prev.violation_data.map(v => ({
          ...v,
          logged_response: responseTypes[v.violation_id] || v.logged_response,
        })),
      }));

      setResponseSuccess(true);
      setTimeout(() => setResponseSuccess(false), 2000);

      // Unlock final stage
      setStageData(prev => ({
        ...prev,
        response: { ...prev.response, status: 'complete' },
        final: { ...prev.final, status: 'ready' },
      }));
    } catch (err) {
      console.error('Failed to save responses:', err);
      setResponseError(err.message || 'Failed to save responses');
    } finally {
      setSubmittingResponse(false);
    }
  };

  // Copy rebuttal letter to clipboard
  const handleCopyRebuttal = async () => {
    try {
      await navigator.clipboard.writeText(editableRebuttalContent);
      setRebuttalCopied(true);
      setTimeout(() => setRebuttalCopied(false), 2000);
    } catch (err) {
      console.error('Failed to copy:', err);
    }
  };

  // Download rebuttal letter as PDF
  const handleDownloadRebuttalPDF = () => {
    if (!editableRebuttalContent) return;
    const pdf = new jsPDF({ unit: 'pt', format: 'letter' });
    const margin = 50;
    const pageWidth = pdf.internal.pageSize.getWidth();
    const pageHeight = pdf.internal.pageSize.getHeight();
    pdf.setFont('times', 'normal');
    pdf.setFontSize(12);
    const lines = pdf.splitTextToSize(editableRebuttalContent, pageWidth - (margin * 2));
    let y = margin;
    lines.forEach((line) => {
      if (y + 18 > pageHeight - margin) { pdf.addPage(); y = margin; }
      pdf.text(line, margin, y);
      y += 18;
    });
    pdf.save(`rebuttal_letter_${dayjs().format('YYYY-MM-DD')}.pdf`);
  };

  // Save rebuttal letter
  const handleSaveRebuttal = async () => {
    if (!activeDispute || !editableRebuttalContent) return;
    setIsSavingRebuttal(true);
    try {
      await saveResponseLetter(activeDispute.id, {
        content: editableRebuttalContent,
        response_type: generatedRebuttalLetter?.response_type,
      });
    } catch (err) {
      console.error('Failed to save rebuttal:', err);
    } finally {
      setIsSavingRebuttal(false);
    }
  };
  const stats = {
    violations: selectedViolations.length,
    accounts: [...new Set(selectedViolations.map(v => v.account_id))].length,
  };

  // Group discrepancies by field name for display
  const discrepanciesByField = React.useMemo(() => {
    const discrepancies = currentLetter?.discrepancies_cited || [];
    if (discrepancies.length === 0) return {};

    return discrepancies.reduce((acc, d) => {
      const fieldName = d.field_name || 'Unknown Field';
      if (!acc[fieldName]) {
        acc[fieldName] = [];
      }
      acc[fieldName].push({
        creditorName: d.creditor_name || 'Unknown Creditor',
        accountNumber: d.account_number_masked || '',
      });
      return acc;
    }, {});
  }, [currentLetter]);

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


      {error && (
        <Alert severity="error" sx={{ mb: 3, borderRadius: 2 }}>
          {error}
        </Alert>
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
              {currentLetter
                ? (documentChannel === 'CFPB' ? 'CFPB Complaint Generated' : 'Mailed Letter Generated')
                : 'Ready to Generate'}
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

      {currentLetter && (
        <>
          {/* Dispute Tracking Stages - Hide for response letters */}
          {!isResponseLetter && (
            <Paper
              elevation={0}
              sx={{
                mt: 4,
                borderRadius: 3,
                border: '1px solid',
                borderColor: 'divider',
                overflow: 'hidden',
              }}
            >
              <Box sx={{ p: 2, bgcolor: '#f5f5f5', borderBottom: '1px solid', borderColor: 'divider' }}>
                <Typography variant="h6" sx={{ fontWeight: 'bold' }}>
                  Dispute Tracking
                </Typography>
                <Typography variant="caption" color="text.secondary">
                  {documentChannel === 'MAILED' ? 'Mail-First Path' : 'CFPB-First Path'}
                </Typography>
              </Box>

              {/* MAIL-FIRST STAGES */}
              {documentChannel === 'MAILED' && (
                <>
                  {/* Stage 1: Initial Letter */}
                  <Accordion
                    expanded={expandedStage === 'initial'}
                    onChange={() => setExpandedStage(expandedStage === 'initial' ? null : 'initial')}
                    disableGutters
                    elevation={0}
                    sx={{ '&:before': { display: 'none' } }}
                  >
                    <AccordionSummary
                      expandIcon={<ExpandMoreIcon />}
                      sx={{ bgcolor: stageData.initial.status === 'complete' ? '#e8f5e9' : '#e3f2fd' }}
                    >
                      <Box sx={{ display: 'flex', alignItems: 'center', gap: 1.5 }}>
                        {stageData.initial.status === 'complete' ? (
                          <CheckCircleIcon color="success" />
                        ) : (
                          <MailOutlineIcon color="primary" />
                        )}
                        <Box>
                          <Typography variant="subtitle2" sx={{ fontWeight: 600 }}>
                            Initial Letter
                          </Typography>
                          <Typography variant="caption" color="text.secondary">
                            {stageData.initial.status === 'complete' ? 'Sent & Tracking' : 'Ready to send'}
                          </Typography>
                        </Box>
                      </Box>
                    </AccordionSummary>
                    <AccordionDetails sx={{ p: 0 }}>
                      {/* Letter Preview inside accordion */}
                      <LetterPreview
                        letter={{
                          ...currentLetter,
                          response_type: currentLetter?.response_type || responseTypeFromUrl,
                        }}
                        isLoading={isGeneratingLetter}
                        error={error}
                        onRegenerate={currentLetter ? handleRegenerate : null}
                        isRegenerating={isGeneratingLetter}
                        stats={stats}
                        isResponseLetter={isResponseLetter}
                        compact
                      />

                      {/* Tracking section */}
                      <Box sx={{ p: 3, bgcolor: '#f8f9fa', borderTop: '1px solid', borderColor: 'divider' }}>
                        {responseError && (
                          <Alert severity="error" sx={{ mb: 2 }} onClose={() => setResponseError(null)}>
                            {responseError}
                          </Alert>
                        )}
                        <Stack direction="row" spacing={2} alignItems="center">
                          <TextField
                            type="date"
                            label="Date Mailed"
                            size="small"
                            InputLabelProps={{ shrink: true }}
                            sx={{ width: 180, bgcolor: 'white' }}
                            onChange={(e) => setStageData(prev => ({
                              ...prev,
                              initial: { ...prev.initial, sentDate: e.target.value }
                            }))}
                          />
                          <Button
                            variant="contained"
                            onClick={handleStartTracking}
                            disabled={!stageData.initial.sentDate || isStartingTracking}
                            startIcon={isStartingTracking ? <CircularProgress size={18} color="inherit" /> : null}
                          >
                            {isStartingTracking ? 'Starting...' : 'Start Tracking'}
                          </Button>
                        </Stack>
                        {stageData.initial.sentDate && (
                          <Typography variant="caption" color="text.secondary" sx={{ mt: 1, display: 'block' }}>
                            Deadline will be: {dayjs(stageData.initial.sentDate).add(30, 'day').format('MMMM D, YYYY')}
                          </Typography>
                        )}
                      </Box>
                    </AccordionDetails>
                  </Accordion>

                  {/* Stage 2: Initial Response */}
                  <Accordion
                    expanded={expandedStage === 'response'}
                    onChange={() => stageData.response.status !== 'locked' && setExpandedStage(expandedStage === 'response' ? null : 'response')}
                    disabled={stageData.response.status === 'locked'}
                    disableGutters
                    elevation={0}
                    sx={{ '&:before': { display: 'none' } }}
                  >
                    <AccordionSummary
                      expandIcon={stageData.response.status === 'locked' ? <LockIcon /> : <ExpandMoreIcon />}
                      sx={{ bgcolor: stageData.response.status === 'complete' ? '#e8f5e9' : stageData.response.status === 'locked' ? '#fafafa' : '#fff3e0' }}
                    >
                      <Box sx={{ display: 'flex', alignItems: 'center', gap: 1.5 }}>
                        {stageData.response.status === 'complete' ? (
                          <CheckCircleIcon color="success" />
                        ) : stageData.response.status === 'locked' ? (
                          <LockIcon color="disabled" />
                        ) : (
                          <MailOutlineIcon color="warning" />
                        )}
                        <Box>
                          <Typography variant="subtitle2" sx={{ fontWeight: 600, color: stageData.response.status === 'locked' ? 'text.disabled' : 'inherit' }}>
                            Initial Response
                          </Typography>
                          <Typography variant="caption" color="text.secondary">
                            {stageData.response.status === 'locked' ? 'Complete previous stage first' : 'Log their response & generate rebuttal'}
                          </Typography>
                        </Box>
                      </Box>
                    </AccordionSummary>
                    <AccordionDetails sx={{ p: 3, bgcolor: '#fafafa' }}>
                      {/* Dispute Details */}
                      {activeDispute && (
                        <Box sx={{ display: 'flex', gap: 4, mb: 3, flexWrap: 'wrap' }}>
                          <Box>
                            <Typography variant="caption" color="text.secondary">Deadline</Typography>
                            <Typography variant="body2" sx={{ fontWeight: 500 }}>
                              {activeDispute.deadline_date ? dayjs(activeDispute.deadline_date).format('MMMM D, YYYY') : '—'}
                            </Typography>
                          </Box>
                          <Box>
                            <Typography variant="caption" color="text.secondary">Days Remaining</Typography>
                            <Typography variant="body2" sx={{ fontWeight: 500 }}>
                              {activeDispute.deadline_date ? dayjs(activeDispute.deadline_date).diff(dayjs(), 'day') : '—'} days
                            </Typography>
                          </Box>
                          <Box>
                            <Typography variant="caption" color="text.secondary">Entity</Typography>
                            <Typography variant="body2" sx={{ fontWeight: 500 }}>
                              {activeDispute.entity_name || currentLetter?.bureau}
                            </Typography>
                          </Box>
                        </Box>
                      )}

                      <Divider sx={{ mb: 3 }} />

                      {/* Response Section Header */}
                      <Typography variant="subtitle2" sx={{ fontWeight: 600, mb: 0.5 }}>
                        Log Response from {activeDispute?.entity_name || currentLetter?.bureau}
                      </Typography>
                      <Typography variant="caption" color="text.secondary" sx={{ display: 'block', mb: 2 }}>
                        Select how the bureau responded to each violation in your dispute letter
                      </Typography>

                      {responseError && (
                        <Alert severity="error" sx={{ mb: 2 }} onClose={() => setResponseError(null)}>
                          {responseError}
                        </Alert>
                      )}

                      {/* Violation Cards */}
                      {activeDispute?.violation_data?.map((v, idx) => (
                        <ViolationResponseCard
                          key={v.violation_id || idx}
                          violation={v}
                          responseType={responseTypes[v.violation_id] || ''}
                          onResponseTypeChange={handleResponseTypeChange}
                          trackingStarted={activeDispute?.tracking_started}
                          deadlineDate={activeDispute?.deadline_date}
                          isLocked={false}
                        />
                      ))}

                      {/* Consolidated Save Section */}
                      <Paper
                        sx={{
                          p: 3,
                          bgcolor: '#f0f9ff',
                          border: '1px solid',
                          borderColor: 'primary.light',
                          borderRadius: 2,
                          mt: 2,
                        }}
                      >
                        <Stack direction={{ xs: 'column', sm: 'row' }} spacing={2} alignItems="center">
                          <LocalizationProvider dateAdapter={AdapterDayjs}>
                            <DatePicker
                              label="Response Date"
                              value={sharedResponseDate}
                              onChange={setSharedResponseDate}
                              maxDate={dayjs()}
                              slotProps={{
                                textField: {
                                  size: 'small',
                                  sx: { minWidth: 200, bgcolor: 'white' },
                                  placeholder: 'Select date received',
                                },
                              }}
                            />
                          </LocalizationProvider>

                          <Button
                            variant="contained"
                            size="large"
                            onClick={handleSaveAndLog}
                            disabled={submittingResponse || Object.values(responseTypes).every(v => !v)}
                            disableElevation
                            startIcon={submittingResponse ? <CircularProgress size={18} color="inherit" /> : <SaveIcon />}
                            sx={{ minWidth: 160, height: 42 }}
                          >
                            {submittingResponse ? 'Saving...' : 'Save & Log'}
                          </Button>

                          {responseSuccess && (
                            <Chip label="Saved!" size="small" color="success" variant="filled" sx={{ height: 28 }} />
                          )}
                        </Stack>

                        {Object.values(responseTypes).some(v => v) && (
                          <Typography variant="caption" color="text.secondary" sx={{ display: 'block', mt: 1.5 }}>
                            {Object.values(responseTypes).filter(v => v).length} response(s) selected.
                            {Object.values(responseTypes).some(v => ['NO_RESPONSE', 'VERIFIED', 'REJECTED', 'REINSERTION'].includes(v)) &&
                              ' A rebuttal letter will be generated after saving.'}
                          </Typography>
                        )}
                      </Paper>

                      {/* Inline Generated Rebuttal Letter */}
                      {rebuttalLetterLoading && (
                        <Paper sx={{ p: 4, mt: 3, textAlign: 'center', borderRadius: 2 }}>
                          <CircularProgress size={24} sx={{ mb: 2 }} />
                          <Typography variant="body2" color="text.secondary">
                            Generating rebuttal letter...
                          </Typography>
                        </Paper>
                      )}

                      {generatedRebuttalLetter && !rebuttalLetterLoading && (
                        <Paper sx={{ mt: 3, borderRadius: 2, overflow: 'hidden' }}>
                          <Box sx={{ p: 2, bgcolor: 'grey.50', borderBottom: '1px solid', borderColor: 'divider' }}>
                            <Box sx={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', flexWrap: 'wrap', gap: 1 }}>
                              <Box sx={{ display: 'flex', alignItems: 'center', gap: 1 }}>
                                <DescriptionIcon color="primary" />
                                <Typography variant="subtitle2" sx={{ fontWeight: 600 }}>
                                  Generated Rebuttal Letter
                                </Typography>
                                <Chip label={`${editableRebuttalContent.split(/\s+/).filter(w => w).length} words`} size="small" variant="outlined" />
                              </Box>
                              <Stack direction="row" spacing={1}>
                                <Button size="small" startIcon={isEditingRebuttal ? <VisibilityIcon /> : <EditIcon />} onClick={() => setIsEditingRebuttal(!isEditingRebuttal)} variant="outlined">
                                  {isEditingRebuttal ? 'View' : 'Edit'}
                                </Button>
                                <Button size="small" startIcon={<ContentCopyIcon />} onClick={handleCopyRebuttal} variant="outlined" color={rebuttalCopied ? 'success' : 'inherit'}>
                                  {rebuttalCopied ? 'Copied!' : 'Copy'}
                                </Button>
                                <Button size="small" startIcon={<DownloadIcon />} onClick={handleDownloadRebuttalPDF} variant="contained" disableElevation>
                                  Download
                                </Button>
                                <Button size="small" startIcon={isSavingRebuttal ? <CircularProgress size={14} /> : <SaveIcon />} onClick={handleSaveRebuttal} variant="contained" color="success" disabled={isSavingRebuttal} disableElevation>
                                  Save
                                </Button>
                              </Stack>
                            </Box>
                          </Box>
                          <Box sx={{ p: 3, maxHeight: 400, overflow: 'auto' }}>
                            {isEditingRebuttal ? (
                              <TextField
                                fullWidth
                                multiline
                                minRows={15}
                                value={editableRebuttalContent}
                                onChange={(e) => setEditableRebuttalContent(e.target.value)}
                                variant="outlined"
                                sx={{ '& .MuiInputBase-root': { fontFamily: '"Times New Roman", serif', fontSize: '11pt', lineHeight: 1.6 } }}
                              />
                            ) : (
                              <Box sx={{ fontFamily: '"Times New Roman", serif', fontSize: '11pt', lineHeight: 1.8, whiteSpace: 'pre-wrap', color: '#111' }}>
                                {editableRebuttalContent}
                              </Box>
                            )}
                          </Box>
                        </Paper>
                      )}
                    </AccordionDetails>
                  </Accordion>

                  {/* Stage 3: Final Response */}
                  <Accordion
                    expanded={expandedStage === 'final'}
                    onChange={() => stageData.final.status !== 'locked' && setExpandedStage(expandedStage === 'final' ? null : 'final')}
                    disabled={stageData.final.status === 'locked'}
                    disableGutters
                    elevation={0}
                    sx={{ '&:before': { display: 'none' } }}
                  >
                    <AccordionSummary
                      expandIcon={stageData.final.status === 'locked' ? <LockIcon /> : <ExpandMoreIcon />}
                      sx={{ bgcolor: stageData.final.status === 'complete' ? '#e8f5e9' : stageData.final.status === 'locked' ? '#fafafa' : '#ffebee' }}
                    >
                      <Box sx={{ display: 'flex', alignItems: 'center', gap: 1.5 }}>
                        {stageData.final.status === 'complete' ? (
                          <CheckCircleIcon color="success" />
                        ) : stageData.final.status === 'locked' ? (
                          <LockIcon color="disabled" />
                        ) : (
                          <MailOutlineIcon color="error" />
                        )}
                        <Box>
                          <Typography variant="subtitle2" sx={{ fontWeight: 600, color: stageData.final.status === 'locked' ? 'text.disabled' : 'inherit' }}>
                            Final Response
                          </Typography>
                          <Typography variant="caption" color="text.secondary">
                            {stageData.final.status === 'locked' ? 'Complete previous stage first' : 'Log final response & escalate'}
                          </Typography>
                        </Box>
                      </Box>
                    </AccordionSummary>
                    <AccordionDetails sx={{ p: 3 }}>
                      <Typography variant="body2" color="text.secondary">
                        Log the final response and generate escalation letter if needed.
                      </Typography>
                    </AccordionDetails>
                  </Accordion>
                </>
              )}

              {/* CFPB STAGES (shown for both routes, but first for CFPB-First) */}
              <Accordion
                expanded={expandedStage === 'cfpb1'}
                onChange={() => {
                  const isUnlocked = documentChannel === 'CFPB' || stageData.final.status === 'complete';
                  if (isUnlocked) setExpandedStage(expandedStage === 'cfpb1' ? null : 'cfpb1');
                }}
                disabled={documentChannel === 'MAILED' && stageData.final.status !== 'complete'}
                disableGutters
                elevation={0}
                sx={{ '&:before': { display: 'none' } }}
              >
                <AccordionSummary
                  expandIcon={documentChannel === 'CFPB' || stageData.final.status === 'complete' ? <ExpandMoreIcon /> : <LockIcon />}
                  sx={{ bgcolor: stageData.cfpb1.status === 'complete' ? '#e8f5e9' : documentChannel === 'CFPB' ? '#fff3e0' : '#fafafa' }}
                >
                  <Box sx={{ display: 'flex', alignItems: 'center', gap: 1.5 }}>
                    {stageData.cfpb1.status === 'complete' ? (
                      <CheckCircleIcon color="success" />
                    ) : documentChannel === 'CFPB' ? (
                      <AccountBalanceIcon color="warning" />
                    ) : (
                      <LockIcon color="disabled" />
                    )}
                    <Box>
                      <Typography variant="subtitle2" sx={{ fontWeight: 600 }}>
                        CFPB Stage 1
                      </Typography>
                      <Typography variant="caption" color="text.secondary">
                        File complaint with regulator
                      </Typography>
                    </Box>
                  </Box>
                </AccordionSummary>
                <AccordionDetails sx={{ p: 3 }}>
                  <Typography variant="body2" color="text.secondary">
                    Generate and file your CFPB complaint.
                  </Typography>
                </AccordionDetails>
              </Accordion>

              {/* CFPB Stage 2 */}
              <Accordion
                expanded={expandedStage === 'cfpb2'}
                onChange={() => stageData.cfpb1.status === 'complete' && setExpandedStage(expandedStage === 'cfpb2' ? null : 'cfpb2')}
                disabled={stageData.cfpb1.status !== 'complete'}
                disableGutters
                elevation={0}
                sx={{ '&:before': { display: 'none' } }}
              >
                <AccordionSummary
                  expandIcon={stageData.cfpb1.status === 'complete' ? <ExpandMoreIcon /> : <LockIcon />}
                  sx={{ bgcolor: stageData.cfpb2.status === 'complete' ? '#e8f5e9' : '#fafafa' }}
                >
                  <Box sx={{ display: 'flex', alignItems: 'center', gap: 1.5 }}>
                    {stageData.cfpb2.status === 'complete' ? (
                      <CheckCircleIcon color="success" />
                    ) : (
                      <LockIcon color="disabled" />
                    )}
                    <Box>
                      <Typography variant="subtitle2" sx={{ fontWeight: 600, color: stageData.cfpb1.status !== 'complete' ? 'text.disabled' : 'inherit' }}>
                        CFPB Stage 2
                      </Typography>
                      <Typography variant="caption" color="text.secondary">
                        Escalate if unresolved
                      </Typography>
                    </Box>
                  </Box>
                </AccordionSummary>
                <AccordionDetails sx={{ p: 3 }}>
                  <Typography variant="body2" color="text.secondary">
                    File follow-up complaint if not resolved.
                  </Typography>
                </AccordionDetails>
              </Accordion>

              {/* Legal Packet */}
              <Accordion
                expanded={expandedStage === 'legal'}
                onChange={() => {
                  const isUnlocked = (documentChannel === 'MAILED' && stageData.final.status === 'complete') ||
                                     (documentChannel === 'CFPB' && stageData.cfpb2.status === 'complete');
                  if (isUnlocked) setExpandedStage(expandedStage === 'legal' ? null : 'legal');
                }}
                disabled={!((documentChannel === 'MAILED' && stageData.final.status === 'complete') ||
                           (documentChannel === 'CFPB' && stageData.cfpb2.status === 'complete'))}
                disableGutters
                elevation={0}
                sx={{ '&:before': { display: 'none' } }}
              >
                <AccordionSummary
                  expandIcon={<LockIcon />}
                  sx={{ bgcolor: '#fafafa' }}
                >
                  <Box sx={{ display: 'flex', alignItems: 'center', gap: 1.5 }}>
                    <GavelIcon color="disabled" />
                    <Box>
                      <Typography variant="subtitle2" sx={{ fontWeight: 600, color: 'text.disabled' }}>
                        Legal Packet
                      </Typography>
                      <Typography variant="caption" color="text.secondary">
                        Attorney-ready evidence bundle
                      </Typography>
                    </Box>
                  </Box>
                </AccordionSummary>
                <AccordionDetails sx={{ p: 3 }}>
                  <Typography variant="body2" color="text.secondary">
                    Generate comprehensive legal packet for attorney review.
                  </Typography>
                </AccordionDetails>
              </Accordion>
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

          {/* Cross-Bureau Discrepancies Summary */}
          {Object.keys(discrepanciesByField).length > 0 && (
            <Paper
              elevation={0}
              sx={{
                p: 3,
                mt: 3,
                borderRadius: 3,
                border: '1px solid',
                borderColor: '#ffc107',
                backgroundColor: '#fffde7',
              }}
            >
              <Typography
                variant="subtitle1"
                sx={{
                  fontWeight: 'bold',
                  mb: 2,
                  pb: 1,
                  borderBottom: '2px solid',
                  borderColor: '#ffc107',
                }}
              >
                Cross-Bureau Discrepancies ({currentLetter?.discrepancy_count || Object.values(discrepanciesByField).flat().length})
              </Typography>
              <Stack spacing={2}>
                {Object.entries(discrepanciesByField)
                  .sort((a, b) => b[1].length - a[1].length)
                  .map(([fieldName, accounts]) => (
                    <Box key={fieldName}>
                      <Stack direction="row" spacing={1} alignItems="center" sx={{ mb: 0.5 }}>
                        <Typography variant="body2" sx={{ fontWeight: 600 }}>
                          {fieldName} Mismatch
                        </Typography>
                        <Chip label={accounts.length} size="small" sx={{ bgcolor: '#ffc107', color: '#000' }} />
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
