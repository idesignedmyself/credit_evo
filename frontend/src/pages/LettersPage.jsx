/**
 * Credit Engine 2.0 - Letters Page
 * Displays all saved dispute letters organized by channel and tier
 */
import React, { useEffect, useState, useMemo } from 'react';
import { useNavigate } from 'react-router-dom';
import {
  Box,
  Typography,
  Paper,
  Table,
  TableBody,
  TableCell,
  TableContainer,
  TableHead,
  TableRow,
  IconButton,
  Alert,
  CircularProgress,
  Chip,
  Button,
  Tooltip,
  Collapse,
  Stack,
  Divider,
  Dialog,
  DialogTitle,
  DialogContent,
  DialogActions,
  TextField,
  Tabs,
  Tab,
} from '@mui/material';
import VisibilityIcon from '@mui/icons-material/Visibility';
import DeleteIcon from '@mui/icons-material/Delete';
import AddIcon from '@mui/icons-material/Add';
import TrackChangesIcon from '@mui/icons-material/TrackChanges';
import ExpandMoreIcon from '@mui/icons-material/ExpandMore';
import ExpandLessIcon from '@mui/icons-material/ExpandLess';
import GavelIcon from '@mui/icons-material/Gavel';
import ContentCopyIcon from '@mui/icons-material/ContentCopy';
import PrintIcon from '@mui/icons-material/Print';
import DownloadIcon from '@mui/icons-material/Download';
import CloseIcon from '@mui/icons-material/Close';
import MailOutlineIcon from '@mui/icons-material/MailOutline';
import AccountBalanceIcon from '@mui/icons-material/AccountBalance';
import { jsPDF } from 'jspdf';
import { letterApi } from '../api';
import { createDisputeFromLetter, RESPONSE_TYPES } from '../api/disputeApi';
import LetterTierSection from '../components/LetterTierSection';

// Utility to detect if string is a UUID (old data format)
const isUUID = (str) => {
  if (!str || typeof str !== 'string') return false;
  const uuidRegex = /^[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}$/i;
  return uuidRegex.test(str);
};

// Format violation type for display
const formatViolationType = (violation) => {
  if (!violation) return null;
  // Skip UUIDs (old data format) - they're not displayable
  if (isUUID(violation)) return null;
  // Convert snake_case to Title Case
  return violation
    .replace(/_/g, ' ')
    .replace(/\b\w/g, (c) => c.toUpperCase());
};

const LettersPage = () => {
  const navigate = useNavigate();
  const [letters, setLetters] = useState([]);
  const [isLoading, setIsLoading] = useState(true);
  const [error, setError] = useState(null);
  const [deletingId, setDeletingId] = useState(null);
  const [trackingId, setTrackingId] = useState(null);
  const [expandedId, setExpandedId] = useState(null);
  const [expandedResponseId, setExpandedResponseId] = useState(null);

  // Tab state
  const [activeTab, setActiveTab] = useState(0); // 0=Mailed, 1=CFPB, 2=Litigation
  const [counts, setCounts] = useState({
    CRA: { total: 0, tier_0: 0, tier_1: 0, tier_2: 0 },
    CFPB: { total: 0, tier_0: 0, tier_1: 0, tier_2: 0 },
    LAWYER: { total: 0, tier_0: 0, tier_1: 0, tier_2: 0 },
  });

  // Response letter dialog state
  const [viewDialogOpen, setViewDialogOpen] = useState(false);
  const [viewingLetter, setViewingLetter] = useState(null);

  // Filter letters by channel and tier
  const getLettersByChannelAndTier = useMemo(() => {
    const channelMap = {
      0: 'CRA',
      1: 'CFPB',
      2: 'LAWYER',
    };
    const channel = channelMap[activeTab] || 'CRA';
    const channelLetters = letters.filter(l => (l.channel || 'CRA') === channel);

    return {
      tier0: channelLetters.filter(l => (l.tier ?? 0) === 0),
      tier1: channelLetters.filter(l => (l.tier ?? 0) === 1),
      tier2: channelLetters.filter(l => (l.tier ?? 0) === 2),
    };
  }, [letters, activeTab]);

  // Legacy: Separate response letters (shown in all channels for now)
  const responseLetters = useMemo(() => {
    return letters.filter(l => l.letter_category === 'response');
  }, [letters]);

  const fetchLetters = async () => {
    setIsLoading(true);
    setError(null);
    try {
      const [lettersData, countsData] = await Promise.all([
        letterApi.getAllLetters(),
        letterApi.getLetterCounts(),
      ]);
      setLetters(lettersData || []);
      setCounts(countsData || {
        CRA: { total: 0, tier_0: 0, tier_1: 0, tier_2: 0 },
        CFPB: { total: 0, tier_0: 0, tier_1: 0, tier_2: 0 },
        LAWYER: { total: 0, tier_0: 0, tier_1: 0, tier_2: 0 },
      });
    } catch (err) {
      setError(err.message || 'Failed to load letters');
    } finally {
      setIsLoading(false);
    }
  };

  useEffect(() => {
    fetchLetters();
  }, []);

  const handleView = (letter) => {
    // Navigate to letter page with letterId
    // Use a placeholder report_id if null (orphaned letters still work via letterId query param)
    const reportId = letter.report_id || 'view';
    const isResponseLetter = letter.letter_category === 'response';
    const queryParams = new URLSearchParams({
      letterId: letter.letter_id,
      ...(isResponseLetter && { type: 'response', responseType: letter.response_type || '' }),
    });
    navigate(`/letter/${reportId}?${queryParams.toString()}`);
  };

  const handleDelete = async (letterId) => {
    if (!window.confirm('Delete this letter? This action cannot be undone.')) {
      return;
    }
    setDeletingId(letterId);
    try {
      await letterApi.deleteLetter(letterId);
      setLetters(letters.filter((l) => l.letter_id !== letterId));
    } catch (err) {
      setError(err.message || 'Failed to delete letter');
    } finally {
      setDeletingId(null);
    }
  };

  const handleTrack = async (letter) => {
    setTrackingId(letter.letter_id);
    setError(null);
    try {
      // Build violation_data from available letter info
      // Filter out UUIDs (old data) - only use valid violation type names
      const validViolations = (letter.violations_cited || []).filter(v => !isUUID(v));
      const accountNumbers = letter.account_numbers || [];

      const violationData = validViolations.map((violationType, idx) => ({
        violation_id: `${letter.letter_id}-v${idx}`, // Generate ID from letter + index
        violation_type: violationType,
        creditor_name: letter.accounts_disputed?.[idx] || 'Unknown',
        account_number_masked: accountNumbers[idx] || null,
        severity: 'MEDIUM',
      }));

      // If no valid violations, create at least one entry from accounts
      if (violationData.length === 0 && letter.accounts_disputed?.length > 0) {
        letter.accounts_disputed.forEach((account, idx) => {
          violationData.push({
            violation_id: `${letter.letter_id}-v${idx}`,
            violation_type: 'dispute_filed',
            creditor_name: account,
            account_number_masked: accountNumbers[idx] || null,
            severity: 'MEDIUM',
          });
        });
      }

      await createDisputeFromLetter(letter.letter_id, {
        entity_type: 'CRA',
        entity_name: letter.bureau,
        violation_ids: violationData.map(v => v.violation_id),
        violation_data: violationData,
      });
      navigate('/disputes');
    } catch (err) {
      console.error('Failed to create dispute:', err);
      setError(err.response?.data?.detail || err.message || 'Failed to create dispute tracking');
    } finally {
      setTrackingId(null);
    }
  };

  const formatDateTime = (dateString) => {
    try {
      // Backend stores UTC timestamps without 'Z' suffix - add it for proper timezone conversion
      let normalizedDate = dateString;
      if (dateString && !dateString.endsWith('Z') && !dateString.includes('+')) {
        normalizedDate = dateString + 'Z';
      }
      const date = new Date(normalizedDate);
      return date.toLocaleString('en-US', {
        month: 'numeric',
        day: 'numeric',
        year: 'numeric',
        hour: 'numeric',
        minute: '2-digit',
        hour12: true,
      });
    } catch {
      return dateString;
    }
  };

  const handleToggleExpand = (letterId) => {
    setExpandedId(expandedId === letterId ? null : letterId);
  };

  const handleToggleResponseExpand = (letterId) => {
    setExpandedResponseId(expandedResponseId === letterId ? null : letterId);
  };

  const getResponseTypeChip = (responseType) => {
    const typeInfo = RESPONSE_TYPES[responseType];
    const label = typeInfo?.label || responseType?.replace(/_/g, ' ').replace(/\b\w/g, c => c.toUpperCase()) || 'Unknown';

    // Color mapping based on response type
    const colorMap = {
      NO_RESPONSE: 'error',
      VERIFIED: 'warning',
      DELETED: 'success',
      UPDATED: 'info',
      INVESTIGATING: 'default',
      REJECTED: 'error',
    };

    return (
      <Chip
        label={label}
        size="small"
        color={colorMap[responseType] || 'default'}
        variant="filled"
      />
    );
  };

  const getLetterTypeChip = (letterType) => {
    return letterType === 'legal' ? (
      <Chip label="Legal" size="small" color="primary" variant="filled" />
    ) : (
      <Chip label="Civilian" size="small" sx={{ bgcolor: '#e8f5e9', color: '#2e7d32' }} />
    );
  };

  const getToneChip = (tone) => {
    const toneLabel = tone?.replace(/_/g, ' ').replace(/\b\w/g, c => c.toUpperCase()) || 'Standard';
    return <Chip label={toneLabel} size="small" variant="outlined" />;
  };

  return (
    <Box>
      {/* Header */}
      <Box sx={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', mb: 3 }}>
        <Typography variant="h5" sx={{ fontWeight: 'bold' }}>
          My Letters
        </Typography>
        <Button
          variant="contained"
          startIcon={<AddIcon />}
          onClick={() => navigate('/upload')}
          disableElevation
        >
          Create New Letter
        </Button>
      </Box>

      {/* Error Alert */}
      {error && (
        <Alert severity="error" sx={{ mb: 3, borderRadius: 2 }} onClose={() => setError(null)}>
          {error}
        </Alert>
      )}

      {/* Loading State */}
      {isLoading ? (
        <Box sx={{ display: 'flex', justifyContent: 'center', py: 8 }}>
          <CircularProgress />
        </Box>
      ) : letters.length === 0 ? (
        /* Empty State */
        <Paper sx={{ p: 6, textAlign: 'center', borderRadius: 3 }}>
          <Typography variant="h6" color="text.secondary" sx={{ mb: 2 }}>
            No letters generated yet
          </Typography>
          <Typography variant="body2" color="text.secondary" sx={{ mb: 3 }}>
            Upload a credit report and generate your first dispute letter
          </Typography>
          <Button
            variant="contained"
            startIcon={<AddIcon />}
            onClick={() => navigate('/upload')}
            disableElevation
          >
            Upload Report & Create Letter
          </Button>
        </Paper>
      ) : (
        <>
        {/* Tab Navigation */}
        <Box sx={{ borderBottom: 1, borderColor: 'divider', mb: 3 }}>
          <Tabs
            value={activeTab}
            onChange={(e, v) => setActiveTab(v)}
            sx={{
              minHeight: 48,
              '& .MuiTab-root': {
                fontWeight: 600,
                minHeight: 48,
                textTransform: 'none',
              },
            }}
          >
            <Tab
              value={0}
              icon={<MailOutlineIcon sx={{ fontSize: 18 }} />}
              iconPosition="start"
              label={`Mailed Disputes (${counts.CRA?.total || 0})`}
              sx={{ gap: 0.5 }}
            />
            <Tab
              value={1}
              icon={<AccountBalanceIcon sx={{ fontSize: 18 }} />}
              iconPosition="start"
              label={`CFPB Complaints (${counts.CFPB?.total || 0})`}
              sx={{ gap: 0.5 }}
            />
            <Tab
              value={2}
              icon={<GavelIcon sx={{ fontSize: 18 }} />}
              iconPosition="start"
              label="Litigation Packets"
              sx={{ gap: 0.5 }}
            />
          </Tabs>
        </Box>

        {/* Tab Content: Mailed Disputes (CRA) */}
        {activeTab === 0 && (
          <Box>
            <LetterTierSection
              tier={0}
              letters={getLettersByChannelAndTier.tier0}
              onView={handleView}
              onDelete={handleDelete}
              onTrack={handleTrack}
              deletingId={deletingId}
              trackingId={trackingId}
              formatDateTime={formatDateTime}
            />
            <LetterTierSection
              tier={1}
              letters={getLettersByChannelAndTier.tier1}
              onView={handleView}
              onDelete={handleDelete}
              onTrack={handleTrack}
              deletingId={deletingId}
              trackingId={trackingId}
              formatDateTime={formatDateTime}
            />
            <LetterTierSection
              tier={2}
              letters={getLettersByChannelAndTier.tier2}
              onView={handleView}
              onDelete={handleDelete}
              onTrack={handleTrack}
              deletingId={deletingId}
              trackingId={trackingId}
              formatDateTime={formatDateTime}
            />
          </Box>
        )}

        {/* Tab Content: CFPB Complaints */}
        {activeTab === 1 && (
          <Box>
            <LetterTierSection
              tier={0}
              letters={getLettersByChannelAndTier.tier0}
              onView={handleView}
              onDelete={handleDelete}
              deletingId={deletingId}
              formatDateTime={formatDateTime}
            />
            <LetterTierSection
              tier={1}
              letters={getLettersByChannelAndTier.tier1}
              onView={handleView}
              onDelete={handleDelete}
              deletingId={deletingId}
              formatDateTime={formatDateTime}
            />
            <LetterTierSection
              tier={2}
              letters={getLettersByChannelAndTier.tier2}
              onView={handleView}
              onDelete={handleDelete}
              deletingId={deletingId}
              formatDateTime={formatDateTime}
            />
          </Box>
        )}

        {/* Tab Content: Litigation Packets (Placeholder) */}
        {activeTab === 2 && (
          <Paper sx={{ p: 6, textAlign: 'center', borderRadius: 3, bgcolor: '#fafafa' }}>
            <GavelIcon sx={{ fontSize: 48, color: 'text.secondary', mb: 2 }} />
            <Typography variant="h6" color="text.secondary" sx={{ mb: 1 }}>
              Litigation Packets
            </Typography>
            <Typography variant="body2" color="text.secondary">
              Attorney case file generation coming soon.
            </Typography>
          </Paper>
        )}
        </>
      )}
    </Box>
  );
};

export default LettersPage;
