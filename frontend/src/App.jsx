/**
 * Credit Engine 2.0 - Main App Component
 * Modern dashboard layout with sidebar navigation
 */
import React from 'react';
import { BrowserRouter as Router, Routes, Route, Navigate, useLocation } from 'react-router-dom';
import { ThemeProvider, CssBaseline } from '@mui/material';
import { DashboardPage, UploadPage, AuditPage, LetterPage, LettersPage, ReportHistoryPage, RegisterPage, ProfilePage, LandingPage, DisputesPage } from './pages';
import { AdminDashboard, AdminUsers, AdminUserDetail, DisputeIntel, CopilotPerf } from './pages/admin';
import DashboardLayout from './layouts/DashboardLayout';
import AdminLayout from './layouts/AdminLayout';
import theme from './theme';
import useAuthStore from './state/authStore';

// Protected Route Component
const ProtectedRoute = ({ children }) => {
  const { isAuthenticated } = useAuthStore();
  const location = useLocation();

  if (!isAuthenticated) {
    return <Navigate to="/" state={{ from: location }} replace />;
  }

  return children;
};

// Admin Route Component - requires admin role
const AdminRoute = ({ children }) => {
  const { isAuthenticated, user } = useAuthStore();
  const location = useLocation();

  if (!isAuthenticated) {
    return <Navigate to="/" state={{ from: location }} replace />;
  }

  if (user?.role !== 'admin') {
    return <Navigate to="/dashboard" replace />;
  }

  return children;
};

// App Layout with Routes
const AppLayout = () => {
  const { isAuthenticated } = useAuthStore();

  return (
    <Routes>
      {/* Public routes - /login redirects to landing page which has the login form */}
      <Route path="/login" element={isAuthenticated ? <Navigate to="/dashboard" replace /> : <Navigate to="/" replace />} />
      <Route path="/register" element={isAuthenticated ? <Navigate to="/dashboard" replace /> : <RegisterPage />} />

      {/* Protected routes with DashboardLayout */}
      <Route
        element={
          <ProtectedRoute>
            <DashboardLayout />
          </ProtectedRoute>
        }
      >
        <Route path="/dashboard" element={<DashboardPage />} />
        <Route path="/upload" element={<UploadPage />} />
        <Route path="/reports" element={<ReportHistoryPage />} />
        <Route path="/letters" element={<LettersPage />} />
        <Route path="/audit/:reportId" element={<AuditPage />} />
        <Route path="/letter/:reportId" element={<LetterPage />} />
        <Route path="/disputes" element={<DisputesPage />} />
        <Route path="/profile" element={<ProfilePage />} />
      </Route>

      {/* Admin routes with AdminLayout */}
      <Route
        element={
          <AdminRoute>
            <AdminLayout />
          </AdminRoute>
        }
      >
        <Route path="/admin" element={<AdminDashboard />} />
        <Route path="/admin/users" element={<AdminUsers />} />
        <Route path="/admin/users/:userId" element={<AdminUserDetail />} />
        <Route path="/admin/disputes" element={<DisputeIntel />} />
        <Route path="/admin/copilot" element={<CopilotPerf />} />
      </Route>

      {/* Default routes - show LandingPage for non-auth, redirect to dashboard for auth */}
      <Route path="/" element={isAuthenticated ? <Navigate to="/dashboard" replace /> : <LandingPage />} />
      <Route path="*" element={isAuthenticated ? <Navigate to="/dashboard" replace /> : <Navigate to="/" replace />} />
    </Routes>
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
