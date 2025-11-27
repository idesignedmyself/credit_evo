/**
 * Credit Engine 2.0 - Main App Component
 * Sets up routing and Material UI theme
 */
import React from 'react';
import { BrowserRouter as Router, Routes, Route, Navigate } from 'react-router-dom';
import { ThemeProvider, createTheme, CssBaseline } from '@mui/material';
import { UploadPage, AuditPage, LetterPage } from './pages';

// Create a clean, modern theme
const theme = createTheme({
  palette: {
    mode: 'light',
    primary: {
      main: '#1976d2',
    },
    secondary: {
      main: '#dc004e',
    },
    background: {
      default: '#f5f5f5',
    },
  },
  typography: {
    fontFamily: [
      '-apple-system',
      'BlinkMacSystemFont',
      '"Segoe UI"',
      'Roboto',
      '"Helvetica Neue"',
      'Arial',
      'sans-serif',
    ].join(','),
  },
  components: {
    MuiButton: {
      styleOverrides: {
        root: {
          textTransform: 'none',
        },
      },
    },
    MuiPaper: {
      styleOverrides: {
        root: {
          borderRadius: 8,
        },
      },
    },
  },
});

function App() {
  return (
    <ThemeProvider theme={theme}>
      <CssBaseline />
      <Router>
        <Routes>
          <Route path="/upload" element={<UploadPage />} />
          <Route path="/audit/:reportId" element={<AuditPage />} />
          <Route path="/letter/:reportId" element={<LetterPage />} />
          <Route path="/" element={<Navigate to="/upload" replace />} />
          <Route path="*" element={<Navigate to="/upload" replace />} />
        </Routes>
      </Router>
    </ThemeProvider>
  );
}

export default App;
