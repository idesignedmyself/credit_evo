/**
 * LetterTierSection - Collapsible section for organizing letters by tier
 * Used within LettersPage tabs (Mailed Disputes, CFPB Complaints)
 */
import React, { useState } from 'react';
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
  Chip,
  Collapse,
  Stack,
  Tooltip,
  CircularProgress,
  Accordion,
  AccordionSummary,
  AccordionDetails,
} from '@mui/material';
import ExpandMoreIcon from '@mui/icons-material/ExpandMore';
import ExpandLessIcon from '@mui/icons-material/ExpandLess';
import VisibilityIcon from '@mui/icons-material/Visibility';
import DeleteIcon from '@mui/icons-material/Delete';
import TrackChangesIcon from '@mui/icons-material/TrackChanges';

// Utility to detect if string is a UUID (old data format)
const isUUID = (str) => {
  if (!str || typeof str !== 'string') return false;
  const uuidRegex = /^[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}$/i;
  return uuidRegex.test(str);
};

// Format violation type for display
const formatViolationType = (violation) => {
  if (!violation) return null;
  // Handle case where violation is an object (CFPB letters)
  if (typeof violation === 'object') {
    return violation.violation_type
      ? violation.violation_type.replace(/_/g, ' ').replace(/\b\w/g, (c) => c.toUpperCase())
      : null;
  }
  // Handle string violation types
  if (typeof violation !== 'string') return null;
  if (isUUID(violation)) return null;
  return violation
    .replace(/_/g, ' ')
    .replace(/\b\w/g, (c) => c.toUpperCase());
};

const TIER_CONFIG = {
  0: {
    title: 'Initial Letters',
    subtitle: 'First contact dispute letters',
    color: '#1976d2',
    bgColor: '#e3f2fd',
  },
  1: {
    title: 'Tier-1 Response Letters',
    subtitle: 'Follow-up letters before supervisory notice',
    color: '#ed6c02',
    bgColor: '#fff3e0',
  },
  2: {
    title: 'Tier-2 Final Response Letters',
    subtitle: 'Escalation letters after supervisory notice deadline',
    color: '#d32f2f',
    bgColor: '#ffebee',
  },
};

const LetterTierSection = ({
  tier,
  letters,
  onView,
  onDelete,
  onTrack,
  deletingId,
  trackingId,
  formatDateTime,
}) => {
  const [expanded, setExpanded] = useState(true);
  const [expandedRowId, setExpandedRowId] = useState(null);

  const config = TIER_CONFIG[tier] || TIER_CONFIG[0];
  const letterCount = letters?.length || 0;

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

  const handleToggleRow = (letterId) => {
    setExpandedRowId(expandedRowId === letterId ? null : letterId);
  };

  return (
    <Accordion
      expanded={expanded}
      onChange={() => setExpanded(!expanded)}
      disableGutters
      elevation={0}
      sx={{
        border: '1px solid',
        borderColor: 'divider',
        borderRadius: '12px !important',
        mb: 2,
        '&:before': { display: 'none' },
        overflow: 'hidden',
      }}
    >
      <AccordionSummary
        expandIcon={<ExpandMoreIcon />}
        sx={{
          bgcolor: config.bgColor,
          '&:hover': { bgcolor: config.bgColor },
          minHeight: 56,
        }}
      >
        <Box sx={{ display: 'flex', alignItems: 'center', gap: 2, width: '100%' }}>
          <Box sx={{ flex: 1 }}>
            <Typography variant="subtitle1" sx={{ fontWeight: 600, color: config.color }}>
              {config.title}
            </Typography>
            <Typography variant="caption" color="text.secondary">
              {config.subtitle}
            </Typography>
          </Box>
          <Chip
            label={letterCount}
            size="small"
            sx={{
              bgcolor: config.color,
              color: 'white',
              fontWeight: 600,
              minWidth: 32,
            }}
          />
        </Box>
      </AccordionSummary>

      <AccordionDetails sx={{ p: 0 }}>
        {letterCount === 0 ? (
          <Box sx={{ p: 4, textAlign: 'center' }}>
            <Typography variant="body2" color="text.secondary">
              No {config.title.toLowerCase()} yet
            </Typography>
          </Box>
        ) : (
          <TableContainer>
            <Table size="small">
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
                {(letters || []).map((letter, index) => {
                  if (!letter || !letter.letter_id) return null;
                  return (
                  <React.Fragment key={letter.letter_id}>
                    <TableRow
                      sx={{
                        cursor: 'pointer',
                        bgcolor: expandedRowId === letter.letter_id ? '#f0f7ff' : 'inherit',
                      }}
                      hover
                      onClick={() => handleToggleRow(letter.letter_id)}
                    >
                      <TableCell>
                        <IconButton size="small">
                          {expandedRowId === letter.letter_id ? <ExpandLessIcon /> : <ExpandMoreIcon />}
                        </IconButton>
                      </TableCell>
                      <TableCell>
                        <Chip
                          label={letters.length - index}
                          size="small"
                          variant="outlined"
                          sx={{ fontWeight: 600 }}
                        />
                      </TableCell>
                      <TableCell sx={{ fontWeight: 500 }}>
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
                          onClick={() => onView(letter)}
                          title="View Letter"
                        >
                          <VisibilityIcon />
                        </IconButton>
                        {onTrack && (
                          <IconButton
                            color="success"
                            size="small"
                            onClick={() => onTrack(letter)}
                            disabled={trackingId === letter.letter_id}
                            title="Track Dispute"
                          >
                            {trackingId === letter.letter_id ? (
                              <CircularProgress size={20} />
                            ) : (
                              <TrackChangesIcon />
                            )}
                          </IconButton>
                        )}
                        <IconButton
                          color="error"
                          size="small"
                          onClick={() => onDelete(letter.letter_id)}
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
                      <TableCell colSpan={8} sx={{ p: 0, borderBottom: expandedRowId === letter.letter_id ? '1px solid' : 0, borderColor: 'divider' }}>
                        <Collapse in={expandedRowId === letter.letter_id} timeout="auto" unmountOnExit>
                          <Box sx={{ p: 3, bgcolor: '#fafafa' }}>
                            <Typography variant="subtitle2" sx={{ fontWeight: 600, mb: 2 }}>
                              Violations Disputed
                            </Typography>
                            {(() => {
                              const violationTypes = (letter.violations_cited || []).filter(v => !isUUID(v));
                              const accounts = letter.accounts_disputed || [];
                              const accountNumbers = letter.account_numbers || [];

                              if (violationTypes.length > 0 || accounts.length > 0) {
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
                                return (
                                  <Typography variant="body2" color="text.secondary">
                                    {letter.violation_count} violation(s) disputed (legacy format)
                                  </Typography>
                                );
                              } else {
                                return (
                                  <Typography variant="body2" color="text.secondary">
                                    No specific violation types recorded.
                                  </Typography>
                                );
                              }
                            })()}

                            {/* Cross-Bureau Discrepancies */}
                            {Array.isArray(letter.discrepancies_cited) && letter.discrepancies_cited.length > 0 && (
                              <Box sx={{ mt: 3 }}>
                                <Typography variant="subtitle2" sx={{ fontWeight: 600, mb: 2, color: '#f57c00' }}>
                                  Cross-Bureau Discrepancies ({letter.discrepancy_count || letter.discrepancies_cited.length})
                                </Typography>
                                <Stack spacing={1.5}>
                                  {letter.discrepancies_cited.map((disc, i) => (
                                    <Box key={i} sx={{ display: 'flex', alignItems: 'center', gap: 1.5 }}>
                                      <Typography variant="body2" sx={{ fontWeight: 500, minWidth: 160 }}>
                                        {disc.creditor_name || 'Unknown'}
                                        {disc.account_number_masked && (
                                          <Typography component="span" variant="body2" color="text.secondary" sx={{ ml: 1 }}>
                                            ({disc.account_number_masked})
                                          </Typography>
                                        )}
                                      </Typography>
                                      <Chip
                                        label={`${disc.field_name || 'Field'} Mismatch`}
                                        size="small"
                                        sx={{ bgcolor: '#fff3e0', color: '#e65100', border: '1px solid #ffb74d' }}
                                      />
                                    </Box>
                                  ))}
                                </Stack>
                              </Box>
                            )}
                          </Box>
                        </Collapse>
                      </TableCell>
                    </TableRow>
                  </React.Fragment>
                  );
                })}
              </TableBody>
            </Table>
          </TableContainer>
        )}
      </AccordionDetails>
    </Accordion>
  );
};

export default LetterTierSection;
