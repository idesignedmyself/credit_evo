/**
 * Credit Engine 2.0 - Letters Page
 * Displays all saved dispute letters for the user
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
import { jsPDF } from 'jspdf';
import { letterApi } from '../api';
import { createDisputeFromLetter, RESPONSE_TYPES } from '../api/disputeApi';

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

  // Response letter dialog state
  const [viewDialogOpen, setViewDialogOpen] = useState(false);
  const [viewingLetter, setViewingLetter] = useState(null);

  // Separate letters by category
  const disputeLetters = useMemo(() => {
    return letters.filter(l => !l.letter_category || l.letter_category === 'dispute');
  }, [letters]);

  const responseLetters = useMemo(() => {
    return letters.filter(l => l.letter_category === 'response');
  }, [letters]);

  const fetchLetters = async () => {
    setIsLoading(true);
    setError(null);
    try {
      const data = await letterApi.getAllLetters();
      setLetters(data || []);
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
        {/* Dispute Letters Section */}
        {disputeLetters.length > 0 && (
        <TableContainer
          component={Paper}
          elevation={0}
          sx={{ border: '1px solid', borderColor: 'divider', borderRadius: 3 }}
        >
          <Table sx={{ minWidth: 650 }}>
            <TableHead sx={{ bgcolor: '#f9fafb' }}>
              <TableRow>
                <TableCell sx={{ fontWeight: 'bold', width: 50 }}></TableCell>
                <TableCell sx={{ fontWeight: 'bold', width: 80 }}>ID</TableCell>
                <TableCell sx={{ fontWeight: 'bold' }}>Bureau</TableCell>
                <TableCell sx={{ fontWeight: 'bold' }}>Type</TableCell>
                <TableCell sx={{ fontWeight: 'bold' }}>Tone</TableCell>
                <TableCell align="center" sx={{ fontWeight: 'bold' }}>Violations</TableCell>
                <TableCell sx={{ fontWeight: 'bold' }}>Created</TableCell>
                <TableCell align="right" sx={{ fontWeight: 'bold' }}>Actions</TableCell>
              </TableRow>
            </TableHead>
            <TableBody>
              {disputeLetters.map((letter, index) => (
                <React.Fragment key={letter.letter_id}>
                  {/* Main Row */}
                  <TableRow
                    sx={{
                      cursor: 'pointer',
                      '&:last-child td, &:last-child th': { border: expandedId === letter.letter_id ? 0 : undefined },
                      bgcolor: expandedId === letter.letter_id ? '#f0f7ff' : 'inherit',
                    }}
                    hover
                    onClick={() => handleToggleExpand(letter.letter_id)}
                  >
                    <TableCell>
                      <IconButton size="small">
                        {expandedId === letter.letter_id ? <ExpandLessIcon /> : <ExpandMoreIcon />}
                      </IconButton>
                    </TableCell>
                    <TableCell>
                      <Chip
                        label={disputeLetters.length - index}
                        size="small"
                        variant="outlined"
                        sx={{ fontWeight: 600 }}
                      />
                    </TableCell>
                    <TableCell component="th" scope="row" sx={{ fontWeight: 500 }}>
                      {letter.bureau?.toUpperCase() || 'N/A'}
                    </TableCell>
                    <TableCell>{getLetterTypeChip(letter.letter_type)}</TableCell>
                    <TableCell>{getToneChip(letter.tone)}</TableCell>
                    <TableCell align="center">
                      <Tooltip title={`${letter.violation_count || 0} violation(s) disputed`}>
                        <Chip
                          label={letter.violation_count || 0}
                          size="small"
                          color="error"
                          variant="filled"
                          sx={{ minWidth: 40 }}
                        />
                      </Tooltip>
                    </TableCell>
                    <TableCell color="text.secondary">
                      {formatDateTime(letter.created_at)}
                    </TableCell>
                    <TableCell align="right" onClick={(e) => e.stopPropagation()}>
                      <IconButton
                        color="primary"
                        size="small"
                        onClick={() => handleView(letter)}
                        title="View Letter"
                      >
                        <VisibilityIcon />
                      </IconButton>
                      <IconButton
                        color="success"
                        size="small"
                        onClick={() => handleTrack(letter)}
                        disabled={trackingId === letter.letter_id}
                        title="Track Dispute"
                      >
                        {trackingId === letter.letter_id ? (
                          <CircularProgress size={20} />
                        ) : (
                          <TrackChangesIcon />
                        )}
                      </IconButton>
                      <IconButton
                        color="error"
                        size="small"
                        onClick={() => handleDelete(letter.letter_id)}
                        disabled={deletingId === letter.letter_id}
                        title="Delete Letter"
                      >
                        {deletingId === letter.letter_id ? (
                          <CircularProgress size={20} />
                        ) : (
                          <DeleteIcon />
                        )}
                      </IconButton>
                    </TableCell>
                  </TableRow>

                  {/* Expanded Content Row */}
                  <TableRow>
                    <TableCell colSpan={8} sx={{ p: 0, borderBottom: expandedId === letter.letter_id ? '1px solid' : 0, borderColor: 'divider' }}>
                      <Collapse in={expandedId === letter.letter_id} timeout="auto" unmountOnExit>
                        <Box sx={{ p: 3, bgcolor: '#fafafa' }}>
                          <Typography variant="subtitle2" sx={{ fontWeight: 600, mb: 2 }}>
                            Violations Disputed in Letter {disputeLetters.length - index}
                          </Typography>
                          {(() => {
                            // Filter violation types, excluding UUIDs (old data)
                            const violationTypes = (letter.violations_cited || []).filter(v => !isUUID(v));
                            const accounts = letter.accounts_disputed || [];
                            const accountNumbers = letter.account_numbers || [];

                            if (violationTypes.length > 0 || accounts.length > 0) {
                              // Combine violations with accounts - use whichever is longer
                              const maxLen = Math.max(violationTypes.length, accounts.length);
                              const combined = [];
                              for (let i = 0; i < maxLen; i++) {
                                combined.push({
                                  creditor: accounts[i] || 'Unknown',
                                  type: violationTypes[i] || null,
                                  accountNumber: accountNumbers[i] || null,
                                });
                              }

                              return (
                                <Stack spacing={1.5}>
                                  {combined.map((item, i) => (
                                    <Box key={i} sx={{ display: 'flex', alignItems: 'center', gap: 1.5 }}>
                                      <Typography variant="body2" sx={{ fontWeight: 500, minWidth: 160 }}>
                                        {item.creditor}
                                        {item.accountNumber && (
                                          <Typography component="span" variant="body2" color="text.secondary" sx={{ ml: 1 }}>
                                            ({item.accountNumber})
                                          </Typography>
                                        )}
                                      </Typography>
                                      {item.type && (
                                        <Chip
                                          label={formatViolationType(item.type)}
                                          size="small"
                                          variant="outlined"
                                          color="error"
                                        />
                                      )}
                                    </Box>
                                  ))}
                                </Stack>
                              );
                            } else if (letter.violation_count > 0) {
                              // Old letter with UUIDs - show count instead
                              return (
                                <Typography variant="body2" color="text.secondary">
                                  {letter.violation_count} violation(s) disputed (legacy format - regenerate letter to see details)
                                </Typography>
                              );
                            } else {
                              return (
                                <Typography variant="body2" color="text.secondary">
                                  No specific violation types recorded for this letter.
                                </Typography>
                              );
                            }
                          })()}
                        </Box>
                      </Collapse>
                    </TableCell>
                  </TableRow>
                </React.Fragment>
              ))}
            </TableBody>
          </Table>
        </TableContainer>
        )}

        {/* Response Letters Section */}
        {responseLetters.length > 0 && (
          <>
            <Divider sx={{ my: 4 }} />
            <Box sx={{ display: 'flex', alignItems: 'center', gap: 1.5, mb: 3 }}>
              <GavelIcon color="primary" />
              <Typography variant="h6" sx={{ fontWeight: 'bold' }}>
                Response Letters
              </Typography>
              <Chip label={responseLetters.length} size="small" color="primary" />
            </Box>
            <TableContainer
              component={Paper}
              elevation={0}
              sx={{ border: '1px solid', borderColor: 'divider', borderRadius: 3 }}
            >
              <Table sx={{ minWidth: 650 }}>
                <TableHead sx={{ bgcolor: '#f9fafb' }}>
                  <TableRow>
                    <TableCell sx={{ fontWeight: 'bold', width: 50 }}></TableCell>
                    <TableCell sx={{ fontWeight: 'bold', width: 80 }}>ID</TableCell>
                    <TableCell sx={{ fontWeight: 'bold' }}>Entity</TableCell>
                    <TableCell sx={{ fontWeight: 'bold' }}>Response Type</TableCell>
                    <TableCell align="center" sx={{ fontWeight: 'bold' }}>Word Count</TableCell>
                    <TableCell sx={{ fontWeight: 'bold' }}>Created</TableCell>
                    <TableCell align="right" sx={{ fontWeight: 'bold' }}>Actions</TableCell>
                  </TableRow>
                </TableHead>
                <TableBody>
                  {responseLetters.map((letter, index) => (
                    <React.Fragment key={letter.letter_id}>
                      {/* Main Row */}
                      <TableRow
                        sx={{
                          cursor: 'pointer',
                          '&:last-child td, &:last-child th': { border: expandedResponseId === letter.letter_id ? 0 : undefined },
                          bgcolor: expandedResponseId === letter.letter_id ? '#f0f7ff' : 'inherit',
                        }}
                        hover
                        onClick={() => handleToggleResponseExpand(letter.letter_id)}
                      >
                        <TableCell>
                          <IconButton size="small">
                            {expandedResponseId === letter.letter_id ? <ExpandLessIcon /> : <ExpandMoreIcon />}
                          </IconButton>
                        </TableCell>
                        <TableCell>
                          <Chip
                            label={responseLetters.length - index}
                            size="small"
                            variant="outlined"
                            color="primary"
                            sx={{ fontWeight: 600 }}
                          />
                        </TableCell>
                        <TableCell component="th" scope="row" sx={{ fontWeight: 500 }}>
                          {letter.bureau?.toUpperCase() || 'N/A'}
                        </TableCell>
                        <TableCell>{getResponseTypeChip(letter.response_type)}</TableCell>
                        <TableCell align="center">
                          <Chip
                            label={letter.word_count || 0}
                            size="small"
                            variant="outlined"
                          />
                        </TableCell>
                        <TableCell color="text.secondary">
                          {formatDateTime(letter.created_at)}
                        </TableCell>
                        <TableCell align="right" onClick={(e) => e.stopPropagation()}>
                          <IconButton
                            color="primary"
                            size="small"
                            onClick={() => handleView(letter)}
                            title="View Letter"
                          >
                            <VisibilityIcon />
                          </IconButton>
                          <IconButton
                            color="error"
                            size="small"
                            onClick={() => handleDelete(letter.letter_id)}
                            disabled={deletingId === letter.letter_id}
                            title="Delete Letter"
                          >
                            {deletingId === letter.letter_id ? (
                              <CircularProgress size={20} />
                            ) : (
                              <DeleteIcon />
                            )}
                          </IconButton>
                        </TableCell>
                      </TableRow>

                      {/* Expanded Content Row */}
                      <TableRow>
                        <TableCell colSpan={7} sx={{ p: 0, borderBottom: expandedResponseId === letter.letter_id ? '1px solid' : 0, borderColor: 'divider' }}>
                          <Collapse in={expandedResponseId === letter.letter_id} timeout="auto" unmountOnExit>
                            <Box sx={{ p: 3, bgcolor: '#fafafa' }}>
                              <Typography variant="subtitle2" sx={{ fontWeight: 600, mb: 2 }}>
                                Letter Preview
                              </Typography>
                              <Paper
                                variant="outlined"
                                sx={{
                                  p: 2,
                                  maxHeight: 200,
                                  overflow: 'auto',
                                  bgcolor: 'white',
                                  fontFamily: 'monospace',
                                  fontSize: '0.85rem',
                                  whiteSpace: 'pre-wrap',
                                }}
                              >
                                {letter.content?.substring(0, 500) || 'No content available'}
                                {letter.content?.length > 500 && '...'}
                              </Paper>
                            </Box>
                          </Collapse>
                        </TableCell>
                      </TableRow>
                    </React.Fragment>
                  ))}
                </TableBody>
              </Table>
            </TableContainer>
          </>
        )}
        </>
      )}
    </Box>
  );
};

export default LettersPage;
