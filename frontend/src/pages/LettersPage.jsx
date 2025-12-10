/**
 * Credit Engine 2.0 - Letters Page
 * Displays all saved dispute letters for the user
 */
import React, { useEffect, useState } from 'react';
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
} from '@mui/material';
import VisibilityIcon from '@mui/icons-material/Visibility';
import DeleteIcon from '@mui/icons-material/Delete';
import AddIcon from '@mui/icons-material/Add';
import DownloadIcon from '@mui/icons-material/Download';
import { letterApi } from '../api';

const LettersPage = () => {
  const navigate = useNavigate();
  const [letters, setLetters] = useState([]);
  const [isLoading, setIsLoading] = useState(true);
  const [error, setError] = useState(null);
  const [deletingId, setDeletingId] = useState(null);

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
    navigate(`/letter/${reportId}?letterId=${letter.letter_id}`);
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

  const formatDate = (dateString) => {
    try {
      return new Date(dateString).toLocaleDateString('en-US', {
        month: 'numeric',
        day: 'numeric',
        year: 'numeric',
      });
    } catch {
      return dateString;
    }
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
        /* Letters Table */
        <TableContainer
          component={Paper}
          elevation={0}
          sx={{ border: '1px solid', borderColor: 'divider', borderRadius: 3 }}
        >
          <Table sx={{ minWidth: 650 }}>
            <TableHead sx={{ bgcolor: '#f9fafb' }}>
              <TableRow>
                <TableCell sx={{ fontWeight: 'bold' }}>Bureau</TableCell>
                <TableCell sx={{ fontWeight: 'bold' }}>Type</TableCell>
                <TableCell sx={{ fontWeight: 'bold' }}>Tone</TableCell>
                <TableCell align="center" sx={{ fontWeight: 'bold' }}>Violations</TableCell>
                <TableCell sx={{ fontWeight: 'bold' }}>Created</TableCell>
                <TableCell align="right" sx={{ fontWeight: 'bold' }}>Actions</TableCell>
              </TableRow>
            </TableHead>
            <TableBody>
              {letters.map((letter) => (
                <TableRow
                  key={letter.letter_id}
                  sx={{ '&:last-child td, &:last-child th': { border: 0 } }}
                  hover
                >
                  <TableCell component="th" scope="row" sx={{ fontWeight: 500 }}>
                    {letter.bureau?.toUpperCase() || 'N/A'}
                  </TableCell>
                  <TableCell>{getLetterTypeChip(letter.letter_type)}</TableCell>
                  <TableCell>{getToneChip(letter.tone)}</TableCell>
                  <TableCell align="center">
                    <Chip
                      label={letter.violation_count || 0}
                      size="small"
                      color="error"
                      variant="filled"
                      sx={{ minWidth: 40 }}
                    />
                  </TableCell>
                  <TableCell color="text.secondary">
                    {formatDate(letter.created_at)}
                  </TableCell>
                  <TableCell align="right">
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
              ))}
            </TableBody>
          </Table>
        </TableContainer>
      )}
    </Box>
  );
};

export default LettersPage;
