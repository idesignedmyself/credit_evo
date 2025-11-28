/**
 * Credit Engine 2.0 - Letter Preview Component
 * Displays generated letter with download, edit, and save options
 */
import React, { useEffect, useRef } from 'react';
import {
  Box,
  Paper,
  Typography,
  Button,
  Divider,
  Chip,
  CircularProgress,
  Alert,
  TextField,
} from '@mui/material';
import DownloadIcon from '@mui/icons-material/Download';
import ContentCopyIcon from '@mui/icons-material/ContentCopy';
import PrintIcon from '@mui/icons-material/Print';
import AutorenewIcon from '@mui/icons-material/Autorenew';
import EditIcon from '@mui/icons-material/Edit';
import VisibilityIcon from '@mui/icons-material/Visibility';
import SaveIcon from '@mui/icons-material/Save';
import { jsPDF } from 'jspdf';
import { useUIStore } from '../state';
import { copyLetterToClipboard, formatToneLabel } from '../utils';

const LetterPreview = ({ letter, isLoading, error, onRegenerate, isRegenerating, stats }) => {
  const [copied, setCopied] = React.useState(false);
  const [isEditing, setIsEditing] = React.useState(false);
  const autosaveTimerRef = useRef(null);

  const {
    selectedTone,
    editableLetter,
    updateEditableLetter,
    saveLetter,
    isSavingLetter,
    hasUnsavedChanges,
    lastSaved,
    currentLetter,
  } = useUIStore();

  // Autosave every 30 seconds if there are unsaved changes
  useEffect(() => {
    if (hasUnsavedChanges && editableLetter) {
      autosaveTimerRef.current = setTimeout(() => {
        saveLetter();
      }, 30000);
    }

    return () => {
      if (autosaveTimerRef.current) {
        clearTimeout(autosaveTimerRef.current);
      }
    };
  }, [hasUnsavedChanges, editableLetter, saveLetter]);

  const handleSave = async () => {
    try {
      await saveLetter();
    } catch (err) {
      console.error('Failed to save letter:', err);
    }
  };

  const handleDownloadPDF = () => {
    if (editableLetter) {
      const pdf = new jsPDF({ unit: 'pt', format: 'letter' });
      const margin = 50;
      const pageWidth = pdf.internal.pageSize.getWidth();
      const pageHeight = pdf.internal.pageSize.getHeight();
      const maxWidth = pageWidth - (margin * 2);

      pdf.setFont('times', 'normal');
      pdf.setFontSize(12);

      const lines = pdf.splitTextToSize(editableLetter, maxWidth);
      let y = margin;
      const lineHeight = 18;

      lines.forEach((line) => {
        if (y + lineHeight > pageHeight - margin) {
          pdf.addPage();
          y = margin;
        }
        pdf.text(line, margin, y);
        y += lineHeight;
      });

      const filename = `dispute_letter_${new Date().toISOString().split('T')[0]}.pdf`;
      pdf.save(filename);
    }
  };

  const handleCopy = async () => {
    if (editableLetter) {
      const success = await copyLetterToClipboard({ content: editableLetter });
      if (success) {
        setCopied(true);
        setTimeout(() => setCopied(false), 2000);
      }
    }
  };

  const handlePrint = () => {
    const printWindow = window.open('', '_blank');
    printWindow.document.write(`
      <html>
        <head>
          <title>Dispute Letter</title>
          <style>
            body { font-family: 'Times New Roman', serif; font-size: 12pt; line-height: 1.6; margin: 1in; }
            p { margin-bottom: 1em; }
          </style>
        </head>
        <body>
          <pre style="white-space: pre-wrap; font-family: inherit;">${editableLetter || ''}</pre>
        </body>
      </html>
    `);
    printWindow.document.close();
    printWindow.print();
  };

  if (isLoading) {
    return (
      <Paper
        elevation={2}
        sx={{
          p: 4,
          textAlign: 'center',
          borderRadius: 3,
          boxShadow: '0 1px 3px rgba(0,0,0,0.12)',
        }}
      >
        <CircularProgress sx={{ mb: 2 }} />
        <Typography variant="body1">Generating your dispute letter...</Typography>
      </Paper>
    );
  }

  if (error) {
    return (
      <Alert severity="error" sx={{ mb: 2, borderRadius: 2 }}>
        {error}
      </Alert>
    );
  }

  if (!letter) {
    return (
      <Paper
        elevation={2}
        sx={{
          p: 4,
          textAlign: 'center',
          backgroundColor: 'grey.50',
          borderRadius: 3,
          boxShadow: '0 1px 3px rgba(0,0,0,0.12)',
        }}
      >
        <Typography variant="body1" color="text.secondary">
          Click "Generate Letter" to create your dispute letter.
        </Typography>
      </Paper>
    );
  }

  // Calculate word count from editable letter, use passed stats for violations/accounts
  const wordCount = editableLetter ? editableLetter.split(/\s+/).filter(w => w).length : 0;
  const violationsCount = stats?.violations || 0;
  const accountsCount = stats?.accounts || 0;

  return (
    <Box>
      <Paper
        elevation={2}
        sx={{
          p: 3,
          mb: 2,
          borderRadius: 3,
          boxShadow: '0 1px 3px rgba(0,0,0,0.12)',
        }}
      >
        {/* Action Bar - All buttons together */}
        <Box sx={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', mb: 2, flexWrap: 'wrap', gap: 1 }}>
          <Typography variant="h6">Generated Letter</Typography>
          <Box sx={{ display: 'flex', gap: 1, flexWrap: 'wrap', justifyContent: 'flex-end' }}>
            {onRegenerate && (
              <Button
                size="small"
                startIcon={<AutorenewIcon />}
                onClick={onRegenerate}
                variant="outlined"
                color="primary"
                disabled={isRegenerating}
              >
                {isRegenerating ? 'Regenerating...' : 'Regenerate'}
              </Button>
            )}
            <Button
              size="small"
              startIcon={isEditing ? <VisibilityIcon /> : <EditIcon />}
              onClick={() => setIsEditing(!isEditing)}
              variant="outlined"
            >
              {isEditing ? 'View' : 'Edit'}
            </Button>
            <Button
              size="small"
              startIcon={<ContentCopyIcon />}
              onClick={handleCopy}
              variant="outlined"
            >
              {copied ? 'Copied!' : 'Copy'}
            </Button>
            <Button
              size="small"
              startIcon={<PrintIcon />}
              onClick={handlePrint}
              variant="outlined"
            >
              Print
            </Button>
            <Button
              size="small"
              startIcon={<DownloadIcon />}
              onClick={handleDownloadPDF}
              variant="contained"
            >
              Download
            </Button>
            <Button
              size="small"
              startIcon={isSavingLetter ? <CircularProgress size={16} /> : <SaveIcon />}
              onClick={handleSave}
              variant="contained"
              color="success"
              disabled={isSavingLetter || !hasUnsavedChanges}
            >
              {isSavingLetter ? 'Saving...' : 'Save'}
            </Button>
          </Box>
        </Box>

        {/* Stats Chips - Only show if > 0 */}
        <Box sx={{ display: 'flex', gap: 1, mb: 2, flexWrap: 'wrap', alignItems: 'center' }}>
          {wordCount > 0 && (
            <Chip label={`${wordCount} words`} size="small" />
          )}
          {violationsCount > 0 && (
            <Chip label={`${violationsCount} violations`} size="small" />
          )}
          {accountsCount > 0 && (
            <Chip label={`${accountsCount} accounts`} size="small" />
          )}
          <Chip label={formatToneLabel(selectedTone)} size="small" variant="outlined" />
          {lastSaved && (
            <Typography variant="caption" color="text.secondary" sx={{ ml: 'auto' }}>
              Last saved: {lastSaved.toLocaleTimeString()}
            </Typography>
          )}
          {hasUnsavedChanges && (
            <Chip label="Unsaved changes" size="small" color="warning" variant="outlined" />
          )}
        </Box>

        <Divider sx={{ mb: 2 }} />

        {/* Letter Content - Edit or View Mode */}
        {isEditing ? (
          <TextField
            fullWidth
            multiline
            minRows={25}
            maxRows={40}
            value={editableLetter || ''}
            onChange={(e) => updateEditableLetter(e.target.value)}
            variant="outlined"
            placeholder="Edit your letter here..."
            sx={{
              '& .MuiInputBase-root': {
                fontFamily: '"SF Mono", "Consolas", monospace',
                fontSize: '14px',
                lineHeight: 1.6,
                backgroundColor: '#ffffff',
              },
              '& .MuiOutlinedInput-notchedOutline': {
                borderColor: 'primary.main',
              },
            }}
          />
        ) : (
          <Box
            sx={{
              fontFamily: '"Times New Roman", serif',
              fontSize: '14px',
              lineHeight: 1.8,
              backgroundColor: '#ffffff',
              border: '1px solid #dce3ed',
              borderRadius: 2,
              p: 3,
              whiteSpace: 'pre-wrap',
              minHeight: 500,
              maxHeight: 700,
              overflowY: 'auto',
            }}
          >
            {editableLetter || 'No letter content available.'}
          </Box>
        )}
      </Paper>
    </Box>
  );
};

export default LetterPreview;
