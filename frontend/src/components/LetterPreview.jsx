/**
 * Credit Engine 2.0 - Letter Preview Component
 * Displays generated letter with download options
 */
import React from 'react';
import {
  Box,
  Paper,
  Typography,
  Button,
  Divider,
  Chip,
  CircularProgress,
  Alert,
} from '@mui/material';
import DownloadIcon from '@mui/icons-material/Download';
import ContentCopyIcon from '@mui/icons-material/ContentCopy';
import PrintIcon from '@mui/icons-material/Print';
import { useUIStore } from '../state';
import {
  downloadLetterAsText,
  copyLetterToClipboard,
  getLetterStats,
  formatToneLabel,
} from '../utils';

const LetterPreview = ({ letter, isLoading, error }) => {
  const [copied, setCopied] = React.useState(false);
  const { selectedTone } = useUIStore();

  const handleDownload = () => {
    if (letter) {
      const filename = `dispute_letter_${new Date().toISOString().split('T')[0]}.txt`;
      downloadLetterAsText(letter, filename);
    }
  };

  const handleCopy = async () => {
    if (letter) {
      const success = await copyLetterToClipboard(letter);
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
          <pre style="white-space: pre-wrap; font-family: inherit;">${letter?.content || ''}</pre>
        </body>
      </html>
    `);
    printWindow.document.close();
    printWindow.print();
  };

  if (isLoading) {
    return (
      <Paper sx={{ p: 4, textAlign: 'center' }}>
        <CircularProgress sx={{ mb: 2 }} />
        <Typography variant="body1">Generating your dispute letter...</Typography>
      </Paper>
    );
  }

  if (error) {
    return (
      <Alert severity="error" sx={{ mb: 2 }}>
        {error}
      </Alert>
    );
  }

  if (!letter) {
    return (
      <Paper sx={{ p: 4, textAlign: 'center', backgroundColor: 'grey.50' }}>
        <Typography variant="body1" color="text.secondary">
          Select violations and click "Generate Letter" to preview your dispute letter.
        </Typography>
      </Paper>
    );
  }

  const stats = getLetterStats(letter);

  return (
    <Box>
      <Paper sx={{ p: 3, mb: 2 }}>
        <Box sx={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', mb: 2 }}>
          <Typography variant="h6">Generated Letter</Typography>
          <Box sx={{ display: 'flex', gap: 1 }}>
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
              onClick={handleDownload}
              variant="contained"
            >
              Download
            </Button>
          </Box>
        </Box>

        <Box sx={{ display: 'flex', gap: 1, mb: 2 }}>
          <Chip label={`${stats?.wordCount || 0} words`} size="small" />
          <Chip label={`${stats?.violationsCited || 0} violations`} size="small" />
          <Chip label={`${stats?.accountsDisputed || 0} accounts`} size="small" />
          <Chip label={formatToneLabel(selectedTone)} size="small" variant="outlined" />
        </Box>

        <Divider sx={{ mb: 2 }} />

        <Paper
          variant="outlined"
          sx={{
            p: 3,
            backgroundColor: 'grey.50',
            fontFamily: '"Times New Roman", serif',
            fontSize: '14px',
            lineHeight: 1.8,
            maxHeight: '600px',
            overflow: 'auto',
          }}
        >
          <pre style={{ whiteSpace: 'pre-wrap', margin: 0, fontFamily: 'inherit' }}>
            {letter.content}
          </pre>
        </Paper>
      </Paper>
    </Box>
  );
};

export default LetterPreview;
