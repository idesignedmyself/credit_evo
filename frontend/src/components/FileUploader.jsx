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
  const [fileError, setFileError] = useState(null);
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
    setFileError(null);
    const validTypes = ['text/html', 'application/pdf', '.html', '.htm', '.pdf'];
    const isValid = validTypes.some(type =>
      file.type.includes(type) || file.name.toLowerCase().endsWith(type)
    );

    if (!isValid) {
      setFileError(`"${file.name}" is not supported. Please upload an HTML or PDF file.`);
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
      {/* Dropzone */}
      <Paper
        elevation={0}
        sx={{
          p: 6,
          textAlign: 'center',
          border: '2px dashed',
          borderColor: dragActive ? 'primary.main' : '#e0e0e0',
          borderRadius: 4,
          backgroundColor: dragActive ? '#f0f7ff' : '#fafafa',
          cursor: 'pointer',
          transition: 'all 0.2s ease',
          '&:hover': {
            borderColor: 'primary.main',
            backgroundColor: '#f0f7ff',
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
          <CloudUploadIcon sx={{ fontSize: 60, color: 'primary.main', mb: 2 }} />
          <Typography variant="h5" gutterBottom sx={{ fontWeight: 600 }}>
            Drop your credit report here
          </Typography>
          <Typography variant="body1" color="text.secondary" sx={{ mb: 3 }}>
            or click to browse files
          </Typography>
          <Typography variant="caption" display="block" color="text.disabled">
            Accepts HTML reports from IdentityIQ, Credit Karma, or Bureau downloads.
          </Typography>
        </label>
      </Paper>

      {/* Selected File */}
      {selectedFile && (
        <Paper sx={{ p: 2, mt: 2, borderRadius: 3 }}>
          <Box sx={{ display: 'flex', alignItems: 'center', gap: 2 }}>
            <InsertDriveFileIcon color="primary" sx={{ fontSize: 40 }} />
            <Box sx={{ flex: 1 }}>
              <Typography variant="body1" sx={{ fontWeight: 500 }}>{selectedFile.name}</Typography>
              <Typography variant="caption" color="text.secondary">
                {(selectedFile.size / 1024).toFixed(1)} KB
              </Typography>
            </Box>
            <Button
              variant="contained"
              size="large"
              onClick={handleUpload}
              disabled={isUploading}
              disableElevation
            >
              {isUploading ? 'Uploading...' : 'Upload & Analyze'}
            </Button>
          </Box>

          {isUploading && (
            <LinearProgress
              variant="determinate"
              value={uploadProgress}
              sx={{ mt: 2, borderRadius: 1 }}
            />
          )}
        </Paper>
      )}

      {/* Errors */}
      {fileError && (
        <Alert severity="warning" sx={{ mt: 2, borderRadius: 2 }} onClose={() => setFileError(null)}>
          {fileError}
        </Alert>
      )}

      {error && (
        <Alert severity="error" sx={{ mt: 2, borderRadius: 2 }} onClose={clearError}>
          {error}
        </Alert>
      )}
    </Box>
  );
};

export default FileUploader;
