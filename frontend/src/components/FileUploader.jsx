/**
 * Credit Engine 2.0 - File Uploader Component
 * Handles credit report file upload with drag-and-drop support
 */
import React, { useCallback, useState } from 'react';
import {
  Box,
  Paper,
  Typography,
  Button,
  LinearProgress,
  Alert,
} from '@mui/material';
import CloudUploadIcon from '@mui/icons-material/CloudUpload';
import InsertDriveFileIcon from '@mui/icons-material/InsertDriveFile';
import { useReportStore } from '../state';

const FileUploader = ({ onUploadSuccess }) => {
  const [dragActive, setDragActive] = useState(false);
  const [selectedFile, setSelectedFile] = useState(null);
  const { uploadReport, isUploading, uploadProgress, error, clearError } = useReportStore();

  const handleDrag = useCallback((e) => {
    e.preventDefault();
    e.stopPropagation();
    if (e.type === 'dragenter' || e.type === 'dragover') {
      setDragActive(true);
    } else if (e.type === 'dragleave') {
      setDragActive(false);
    }
  }, []);

  const handleDrop = useCallback((e) => {
    e.preventDefault();
    e.stopPropagation();
    setDragActive(false);

    const file = e.dataTransfer?.files?.[0];
    if (file) {
      validateAndSetFile(file);
    }
  }, []);

  const handleFileSelect = useCallback((e) => {
    const file = e.target.files?.[0];
    if (file) {
      validateAndSetFile(file);
    }
  }, []);

  const validateAndSetFile = (file) => {
    clearError();
    const validTypes = ['text/html', 'application/pdf', '.html', '.htm', '.pdf'];
    const isValid = validTypes.some(type =>
      file.type.includes(type) || file.name.toLowerCase().endsWith(type)
    );

    if (!isValid) {
      return;
    }

    setSelectedFile(file);
  };

  const handleUpload = async () => {
    if (!selectedFile) return;

    try {
      const result = await uploadReport(selectedFile);
      setSelectedFile(null);
      if (onUploadSuccess) {
        onUploadSuccess(result);
      }
    } catch (err) {
      // Error is handled by store
    }
  };

  return (
    <Box>
      <Paper
        sx={{
          p: 4,
          textAlign: 'center',
          border: '2px dashed',
          borderColor: dragActive ? 'primary.main' : 'grey.300',
          backgroundColor: dragActive ? 'action.hover' : 'background.paper',
          cursor: 'pointer',
          transition: 'all 0.2s ease',
          '&:hover': {
            borderColor: 'primary.light',
            backgroundColor: 'action.hover',
          },
        }}
        onDragEnter={handleDrag}
        onDragLeave={handleDrag}
        onDragOver={handleDrag}
        onDrop={handleDrop}
      >
        <input
          type="file"
          id="file-upload"
          accept=".html,.htm,.pdf"
          onChange={handleFileSelect}
          style={{ display: 'none' }}
        />

        <label htmlFor="file-upload" style={{ cursor: 'pointer', display: 'block' }}>
          <CloudUploadIcon sx={{ fontSize: 64, color: 'primary.main', mb: 2 }} />
          <Typography variant="h6" gutterBottom>
            Drop your credit report here
          </Typography>
          <Typography variant="body2" color="text.secondary" sx={{ mb: 2 }}>
            or click to browse files
          </Typography>
          <Typography variant="caption" color="text.secondary">
            Supports HTML and PDF formats
          </Typography>
        </label>
      </Paper>

      {selectedFile && (
        <Paper sx={{ p: 2, mt: 2 }}>
          <Box sx={{ display: 'flex', alignItems: 'center', gap: 2 }}>
            <InsertDriveFileIcon color="primary" />
            <Box sx={{ flex: 1 }}>
              <Typography variant="body1">{selectedFile.name}</Typography>
              <Typography variant="caption" color="text.secondary">
                {(selectedFile.size / 1024).toFixed(1)} KB
              </Typography>
            </Box>
            <Button
              variant="contained"
              onClick={handleUpload}
              disabled={isUploading}
            >
              {isUploading ? 'Uploading...' : 'Upload'}
            </Button>
          </Box>

          {isUploading && (
            <LinearProgress
              variant="determinate"
              value={uploadProgress}
              sx={{ mt: 2 }}
            />
          )}
        </Paper>
      )}

      {error && (
        <Alert severity="error" sx={{ mt: 2 }} onClose={clearError}>
          {error}
        </Alert>
      )}
    </Box>
  );
};

export default FileUploader;
