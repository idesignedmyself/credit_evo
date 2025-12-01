/**
 * Credit Engine 2.0 - Main App Component
 * Sets up routing and Material UI theme
 */
import React from 'react';
import { BrowserRouter as Router, Routes, Route, Navigate, Link, useLocation } from 'react-router-dom';
import { ThemeProvider, createTheme, CssBaseline, AppBar, Toolbar, Typography, Button, Box } from '@mui/material';
import HistoryIcon from '@mui/icons-material/History';
import UploadFileIcon from '@mui/icons-material/UploadFile';
import LogoutIcon from '@mui/icons-material/Logout';
import { UploadPage, AuditPage, LetterPage, ReportHistoryPage, LoginPage, RegisterPage } from './pages';
import useAuthStore from './state/authStore';

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

// Protected Route Component
const ProtectedRoute = ({ children }) => {
  const { isAuthenticated } = useAuthStore();
  const location = useLocation();

  if (!isAuthenticated) {
    return <Navigate to="/login" state={{ from: location }} replace />;
  }

  return children;
};

// Navigation Bar Component
const NavBar = () => {
  const location = useLocation();
  const { isAuthenticated, user, logout } = useAuthStore();
  const isActive = (path) => location.pathname === path || location.pathname.startsWith(path + '/');

  const handleLogout = () => {
    logout();
    window.location.href = '/login';
  };

  return (
    <AppBar position="static" color="default" elevation={1} sx={{ mb: 2 }}>
      <Toolbar>
        <Typography variant="h6" component={Link} to="/upload" sx={{ flexGrow: 1, textDecoration: 'none', color: 'inherit' }}>
          Credit Engine 2.0
        </Typography>
        <Box sx={{ display: 'flex', gap: 1, alignItems: 'center' }}>
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
          {isAuthenticated && (
            <>
              <Typography variant="body2" sx={{ mx: 1, color: 'text.secondary' }}>
                {user?.username || user?.email}
              </Typography>
              <Button
                onClick={handleLogout}
                startIcon={<LogoutIcon />}
                size="small"
                color="inherit"
              >
                Logout
              </Button>
            </>
          )}
        </Box>
      </Toolbar>
    </AppBar>
  );
};

// App Layout with NavBar inside Router
const AppLayout = () => {
  const { isAuthenticated } = useAuthStore();

  return (
    <>
      <Routes>
        {/* Public routes */}
        <Route path="/login" element={isAuthenticated ? <Navigate to="/reports" replace /> : <LoginPage />} />
        <Route path="/register" element={isAuthenticated ? <Navigate to="/reports" replace /> : <RegisterPage />} />

        {/* Protected routes with NavBar */}
        <Route path="/upload" element={
          <ProtectedRoute>
            <NavBar />
            <UploadPage />
          </ProtectedRoute>
        } />
        <Route path="/reports" element={
          <ProtectedRoute>
            <NavBar />
            <ReportHistoryPage />
          </ProtectedRoute>
        } />
        <Route path="/audit/:reportId" element={
          <ProtectedRoute>
            <NavBar />
            <AuditPage />
          </ProtectedRoute>
        } />
        <Route path="/letter/:reportId" element={
          <ProtectedRoute>
            <NavBar />
            <LetterPage />
          </ProtectedRoute>
        } />

        {/* Default redirect */}
        <Route path="/" element={<Navigate to="/reports" replace />} />
        <Route path="*" element={<Navigate to="/reports" replace />} />
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
