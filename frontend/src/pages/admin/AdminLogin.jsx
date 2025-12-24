/**
 * Credit Engine 2.0 - Admin Login Page
 * Dedicated dark-themed login for admin console access.
 */
import React, { useState } from 'react';
import { useNavigate } from 'react-router-dom';
import {
  Box, Container, Typography, Button, TextField, Paper,
  Stack, InputAdornment, IconButton, Alert
} from '@mui/material';
import Visibility from '@mui/icons-material/Visibility';
import VisibilityOff from '@mui/icons-material/VisibilityOff';
import AdminPanelSettingsIcon from '@mui/icons-material/AdminPanelSettings';
import LockIcon from '@mui/icons-material/Lock';
import useAuthStore from '../../state/authStore';
import { login, getMe } from '../../api/authApi';

export default function AdminLogin() {
  const navigate = useNavigate();
  const { login: storeLogin, logout, isAuthenticated, user } = useAuthStore();
  const [email, setEmail] = useState('');
  const [password, setPassword] = useState('');
  const [showPassword, setShowPassword] = useState(false);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState(null);

  // On mount: if authenticated as admin, redirect; otherwise clear stale non-admin session
  React.useEffect(() => {
    if (isAuthenticated) {
      if (user?.role === 'admin') {
        navigate('/admin');
      } else {
        // Clear non-admin session to prevent interference
        logout();
      }
    }
  }, [isAuthenticated, user, navigate, logout]);

  const handleSubmit = async (e) => {
    e.preventDefault();
    setError(null);
    setLoading(true);

    try {
      const tokenData = await login(email, password);
      localStorage.setItem('credit_engine_token', tokenData.access_token);
      const userData = await getMe();

      // Check if user is admin
      if (userData.role !== 'admin') {
        localStorage.removeItem('credit_engine_token');
        setError('Access denied. Admin privileges required.');
        setLoading(false);
        return;
      }

      storeLogin(tokenData.access_token, userData);
      navigate('/admin');
    } catch (err) {
      setError(err.message || 'Invalid credentials');
    } finally {
      setLoading(false);
    }
  };

  return (
    <Box
      sx={{
        minHeight: '100vh',
        width: '100%',
        bgcolor: '#0f0f1a',
        display: 'flex',
        alignItems: 'center',
        justifyContent: 'center',
      }}
    >
      <Container maxWidth="sm">
        <Paper
          elevation={0}
          sx={{
            p: { xs: 4, md: 6 },
            borderRadius: 3,
            bgcolor: '#16213e',
            border: '1px solid #0f3460',
            maxWidth: '450px',
            mx: 'auto',
          }}
        >
          {/* Header */}
          <Box sx={{ textAlign: 'center', mb: 4 }}>
            <Box
              sx={{
                display: 'inline-flex',
                alignItems: 'center',
                justifyContent: 'center',
                width: 64,
                height: 64,
                bgcolor: 'rgba(233, 69, 96, 0.1)',
                borderRadius: '16px',
                mb: 2,
              }}
            >
              <AdminPanelSettingsIcon sx={{ fontSize: 36, color: '#e94560' }} />
            </Box>
            <Typography variant="h5" fontWeight="bold" sx={{ color: '#fff', mb: 1 }}>
              Admin Console
            </Typography>
            <Typography variant="body2" sx={{ color: '#a2a2a2' }}>
              Sign in with your administrator credentials
            </Typography>
          </Box>

          {error && (
            <Alert
              severity="error"
              sx={{
                mb: 3,
                bgcolor: 'rgba(233, 69, 96, 0.1)',
                color: '#e94560',
                border: '1px solid rgba(233, 69, 96, 0.3)',
                '& .MuiAlert-icon': { color: '#e94560' }
              }}
            >
              {error}
            </Alert>
          )}

          <Box component="form" onSubmit={handleSubmit}>
            <Stack spacing={3}>
              <Box>
                <Typography variant="caption" fontWeight="600" sx={{ mb: 1, display: 'block', color: '#a2a2a2' }}>
                  Email Address
                </Typography>
                <TextField
                  fullWidth
                  placeholder="admin@example.com"
                  variant="outlined"
                  type="email"
                  autoComplete="email"
                  required
                  value={email}
                  onChange={(e) => setEmail(e.target.value)}
                  sx={{
                    '& .MuiOutlinedInput-root': {
                      bgcolor: '#1a1a2e',
                      borderRadius: 2,
                      color: '#fff',
                      '& fieldset': { borderColor: '#0f3460' },
                      '&:hover fieldset': { borderColor: '#e94560' },
                      '&.Mui-focused fieldset': { borderColor: '#e94560' },
                    },
                    '& .MuiInputBase-input::placeholder': { color: '#666' },
                  }}
                />
              </Box>

              <Box>
                <Typography variant="caption" fontWeight="600" sx={{ mb: 1, display: 'block', color: '#a2a2a2' }}>
                  Password
                </Typography>
                <TextField
                  fullWidth
                  type={showPassword ? 'text' : 'password'}
                  placeholder="Enter your password"
                  variant="outlined"
                  autoComplete="current-password"
                  required
                  value={password}
                  onChange={(e) => setPassword(e.target.value)}
                  sx={{
                    '& .MuiOutlinedInput-root': {
                      bgcolor: '#1a1a2e',
                      borderRadius: 2,
                      color: '#fff',
                      '& fieldset': { borderColor: '#0f3460' },
                      '&:hover fieldset': { borderColor: '#e94560' },
                      '&.Mui-focused fieldset': { borderColor: '#e94560' },
                    },
                    '& .MuiInputBase-input::placeholder': { color: '#666' },
                  }}
                  InputProps={{
                    endAdornment: (
                      <InputAdornment position="end">
                        <IconButton
                          onClick={() => setShowPassword(!showPassword)}
                          edge="end"
                          sx={{ color: '#666' }}
                        >
                          {showPassword ? <VisibilityOff fontSize="small" /> : <Visibility fontSize="small" />}
                        </IconButton>
                      </InputAdornment>
                    ),
                  }}
                />
              </Box>

              <Button
                type="submit"
                fullWidth
                variant="contained"
                size="large"
                disabled={loading}
                startIcon={<LockIcon />}
                sx={{
                  bgcolor: '#e94560',
                  py: 1.5,
                  borderRadius: 2,
                  fontSize: '1rem',
                  fontWeight: 600,
                  textTransform: 'none',
                  boxShadow: 'none',
                  '&:hover': { bgcolor: '#d63353', boxShadow: 'none' },
                  '&:disabled': { bgcolor: 'rgba(233, 69, 96, 0.5)', color: '#fff' }
                }}
              >
                {loading ? 'Authenticating...' : 'Access Admin Console'}
              </Button>
            </Stack>
          </Box>

          {/* Footer */}
          <Box sx={{ textAlign: 'center', mt: 4, pt: 3, borderTop: '1px solid #0f3460' }}>
            <Typography variant="caption" sx={{ color: '#666' }}>
              Protected area. Unauthorized access is prohibited.
            </Typography>
          </Box>
        </Paper>
      </Container>
    </Box>
  );
}
