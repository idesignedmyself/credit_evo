/**
 * Credit Engine 2.0 - Main App Component
 * Sets up routing and Material UI theme
 */
import React from 'react';
import { BrowserRouter as Router, Routes, Route, Navigate, Link, useLocation } from 'react-router-dom';
import { ThemeProvider, createTheme, CssBaseline, AppBar, Toolbar, Typography, Button, Box } from '@mui/material';
import HistoryIcon from '@mui/icons-material/History';
import UploadFileIcon from '@mui/icons-material/UploadFile';
import { UploadPage, AuditPage, LetterPage, ReportHistoryPage } from './pages';

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

// Navigation Bar Component
const NavBar = () => {
  const location = useLocation();
  const isActive = (path) => location.pathname === path || location.pathname.startsWith(path + '/');

  return (
    <AppBar position="static" color="default" elevation={1} sx={{ mb: 2 }}>
      <Toolbar>
        <Typography variant="h6" component={Link} to="/upload" sx={{ flexGrow: 1, textDecoration: 'none', color: 'inherit' }}>
          Credit Engine 2.0
        </Typography>
        <Box sx={{ display: 'flex', gap: 1 }}>
          <Button
            component={Link}
            to="/upload"
            startIcon={<UploadFileIcon />}
            variant={isActive('/upload') ? 'contained' : 'text'}
            size="small"
          >
            Upload
          </Button>
          <Button
            component={Link}
            to="/reports"
            startIcon={<HistoryIcon />}
            variant={isActive('/reports') ? 'contained' : 'text'}
            size="small"
          >
            Reports
          </Button>
        </Box>
      </Toolbar>
    </AppBar>
  );
};

// App Layout with NavBar inside Router
const AppLayout = () => {
  return (
    <>
      <NavBar />
      <Routes>
        <Route path="/upload" element={<UploadPage />} />
        <Route path="/reports" element={<ReportHistoryPage />} />
        <Route path="/audit/:reportId" element={<AuditPage />} />
        <Route path="/letter/:reportId" element={<LetterPage />} />
        <Route path="/" element={<Navigate to="/upload" replace />} />
        <Route path="*" element={<Navigate to="/upload" replace />} />
      </Routes>
    </>
  );
};

function App() {
  return (
    <ThemeProvider theme={theme}>
      <CssBaseline />
      <Router>
        <AppLayout />
      </Router>
    </ThemeProvider>
  );
}

export default App;
