/**
 * Credit Engine 2.0 - Saved Letters Component
 * Displays saved letters with view and delete actions
 */
import React, { useEffect, useState } from 'react';
import {
  Box,
  Paper,
  Typography,
  Table,
  TableHead,
  TableRow,
  TableCell,
  TableBody,
  TableContainer,
  IconButton,
  Chip,
  CircularProgress,
} from '@mui/material';
import VisibilityIcon from '@mui/icons-material/Visibility';
import DeleteIcon from '@mui/icons-material/Delete';
import { letterApi } from '../api';
import { useNavigate } from 'react-router-dom';

const SavedLetters = () => {
  const [letters, setLetters] = useState([]);
  const [isLoading, setIsLoading] = useState(true);
  const [deletingId, setDeletingId] = useState(null);
  const navigate = useNavigate();

  useEffect(() => {
    fetchLetters();
  }, []);

  const fetchLetters = async () => {
    setIsLoading(true);
    try {
      const res = await letterApi.getAllLetters();
      setLetters(res || []);
    } catch (err) {
      console.error('Failed to fetch letters:', err);
    } finally {
      setIsLoading(false);
    }
  };

  const handleDelete = async (id) => {
    if (!window.confirm('Delete this letter? This action cannot be undone.')) {
      return;
    }
    setDeletingId(id);
    try {
      await letterApi.deleteLetter(id);
      setLetters((prev) => prev.filter((l) => l.id !== id));
    } catch (err) {
      console.error('Failed to delete letter:', err);
    } finally {
      setDeletingId(null);
    }
  };

  const handleView = (reportId) => {
    navigate(`/audit/${reportId}`);
  };

  const formatDate = (dateString) => {
    try {
      return new Date(dateString).toLocaleString();
    } catch {
      return dateString;
    }
  };

  if (isLoading) {
    return (
      <Box sx={{ display: 'flex', justifyContent: 'center', py: 4 }}>
        <CircularProgress size={24} />
      </Box>
    );
  }

  if (letters.length === 0) {
    return (
      <Paper sx={{ p: 3, textAlign: 'center' }}>
        <Typography variant="body1" color="text.secondary">
          No letters generated yet. Upload a report and generate a dispute letter to see it here.
        </Typography>
      </Paper>
    );
  }

  return (
    <TableContainer component={Paper}>
      <Table>
        <TableHead>
          <TableRow>
            <TableCell>Created</TableCell>
            <TableCell>Bureau</TableCell>
            <TableCell>Tone</TableCell>
            <TableCell align="center">Violations</TableCell>
            <TableCell align="center">Edited</TableCell>
            <TableCell align="center">Actions</TableCell>
          </TableRow>
        </TableHead>

        <TableBody>
          {letters.map((letter) => (
            <TableRow key={letter.id} hover>
              <TableCell>
                <Typography variant="body2" color="text.secondary">
                  {formatDate(letter.created_at)}
                </Typography>
              </TableCell>

              <TableCell>
                <Chip
                  label={letter.bureau?.toUpperCase() || 'N/A'}
                  color="primary"
                  variant="outlined"
                  size="small"
                />
              </TableCell>

              <TableCell>
                <Typography variant="body2" sx={{ textTransform: 'capitalize' }}>
                  {letter.tone || 'N/A'}
                </Typography>
              </TableCell>

              <TableCell align="center">
                <Chip
                  label={letter.violations || 0}
                  color="warning"
                  size="small"
                />
              </TableCell>

              <TableCell align="center">
                {letter.has_edits ? (
                  <Chip label="Yes" color="success" size="small" />
                ) : (
                  <Chip label="No" variant="outlined" size="small" />
                )}
              </TableCell>

              <TableCell align="center">
                <IconButton
                  color="primary"
                  onClick={() => handleView(letter.report_id)}
                  title="View Letter"
                >
                  <VisibilityIcon />
                </IconButton>

                <IconButton
                  color="error"
                  onClick={() => handleDelete(letter.id)}
                  disabled={deletingId === letter.id}
                  title="Delete Letter"
                >
                  {deletingId === letter.id ? (
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
  );
};

export default SavedLetters;
