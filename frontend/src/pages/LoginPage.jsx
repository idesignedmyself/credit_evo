/**
 * Credit Engine 2.0 - Login Page
 * Premium "Deep Navy" split-screen design
 */
import React, { useState } from 'react';
import { useNavigate, Link as RouterLink } from 'react-router-dom';
import {
  Box, Grid, Paper, Typography, TextField, Button,
  Container, Stack, Link, InputAdornment, IconButton,
  Checkbox, FormControlLabel, Alert
} from '@mui/material';
import Visibility from '@mui/icons-material/Visibility';
import VisibilityOff from '@mui/icons-material/VisibilityOff';
import useAuthStore from '../state/authStore';
import { login, getMe } from '../api/authApi';

function LoginPage() {
  const navigate = useNavigate();
  const { login: storeLogin, setError, error, clearError } = useAuthStore();

  const [email, setEmail] = useState('');
  const [password, setPassword] = useState('');
  const [showPassword, setShowPassword] = useState(false);
  const [loading, setLoading] = useState(false);
  const [rememberMe, setRememberMe] = useState(true);

  const handleSubmit = async (e) => {
    e.preventDefault();
    clearError();
    setLoading(true);

    try {
      // Login and get token
      const tokenData = await login(email, password);

      // Store token immediately so getMe can use it
      localStorage.setItem('credit_engine_token', tokenData.access_token);

      // Get user info
      const userData = await getMe();

      // Store in auth state (this also sets localStorage, but we needed it earlier)
      storeLogin(tokenData.access_token, userData);

      // Redirect to reports page
      navigate('/reports');
    } catch (err) {
      setError(err.message);
    } finally {
      setLoading(false);
    }
  };

  return (
    <Box
      sx={{
        minHeight: '100vh',
        width: '100%',
        bgcolor: '#020617', // Solid Deep Navy (No Gradient)
        display: 'flex',
        alignItems: 'center',
      }}
    >
      <Container maxWidth="lg">
        <Grid container spacing={8} alignItems="center">

          {/* --- LEFT SIDE: THE MARKETING PITCH --- */}
          {/* Hidden on mobile (xs: 'none'), Visible on desktop (md: 'block') */}
          <Grid item xs={12} md={6} sx={{ display: { xs: 'none', md: 'block' }, color: 'white' }}>
            <Box sx={{ mb: 4, display: 'flex', alignItems: 'center', gap: 2 }}>
               {/* Logo Placeholder */}
               <Box sx={{ width: 40, height: 40, bgcolor: '#3B82F6', borderRadius: 1 }} />
               <Typography variant="h6" fontWeight="bold">Credit Engine 2.0</Typography>
            </Box>

            <Typography variant="h2" fontWeight="800" sx={{ lineHeight: 1.1, mb: 3 }}>
              Credit Letter Generation <br />
              <Box component="span" sx={{ color: '#60A5FA' }}>Tailored To You.</Box>
            </Typography>

            <Typography variant="h6" sx={{ color: '#94A3B8', mb: 6, fontWeight: 400, lineHeight: 1.6, maxWidth: '500px' }}>
              Monitor your credit, analyze reports, and generate dispute letters with our industry-leading credit management solution.
            </Typography>

            {/* Trust Indicators / Stats */}
            <Stack direction="row" spacing={6} sx={{ borderTop: '1px solid #1E293B', pt: 4 }}>
               <Box>
                 <Typography variant="h4" fontWeight="bold">98%</Typography>
                 <Typography variant="body2" sx={{ color: '#94A3B8' }}>Success Rate</Typography>
               </Box>
               <Box>
                 <Typography variant="h4" fontWeight="bold">150+</Typography>
                 <Typography variant="body2" sx={{ color: '#94A3B8' }}>Violation Types</Typography>
               </Box>
               <Box>
                 <Typography variant="h4" fontWeight="bold">24/7</Typography>
                 <Typography variant="body2" sx={{ color: '#94A3B8' }}>Automated Monitoring</Typography>
               </Box>
            </Stack>
          </Grid>

          {/* --- RIGHT SIDE: THE LOGIN FORM --- */}
          <Grid item xs={12} md={6}>
            <Paper
              elevation={0}
              sx={{
                p: { xs: 3, md: 6 }, // More padding on desktop
                borderRadius: 4,
                bgcolor: 'white', // Pure white card
                maxWidth: '500px',
                mx: 'auto' // Center horizontally
              }}
            >
              <Box sx={{ mb: 4 }}>
                <Typography variant="h5" fontWeight="bold" sx={{ color: '#0F172A', mb: 1 }}>
                  Member Login
                </Typography>
                <Typography variant="body2" color="text.secondary">
                  Sign in to access your dashboard
                </Typography>
              </Box>

              {error && (
                <Alert severity="error" sx={{ mb: 3 }}>
                  {error}
                </Alert>
              )}

              <Box component="form" onSubmit={handleSubmit}>
                <Stack spacing={3}>
                  <Box>
                    <Typography variant="caption" fontWeight="bold" sx={{ mb: 1, display: 'block', color: '#475569' }}>
                      Email Address
                    </Typography>
                    <TextField
                      fullWidth
                      placeholder="name@example.com"
                      variant="outlined"
                      type="email"
                      autoComplete="email"
                      required
                      value={email}
                      onChange={(e) => setEmail(e.target.value)}
                      InputProps={{ sx: { borderRadius: 2, bgcolor: '#F8FAFC', '& fieldset': { borderColor: '#E2E8F0' } } }}
                    />
                  </Box>

                  <Box>
                    <Box sx={{ display: 'flex', justifyContent: 'space-between', mb: 1 }}>
                      <Typography variant="caption" fontWeight="bold" sx={{ color: '#475569' }}>
                        Password
                      </Typography>
                      <Link href="#" variant="caption" fontWeight="600" underline="hover" sx={{ color: '#2563EB' }}>
                        Forgot Password?
                      </Link>
                    </Box>
                    <TextField
                      fullWidth
                      type={showPassword ? 'text' : 'password'}
                      placeholder="Enter your password"
                      variant="outlined"
                      autoComplete="current-password"
                      required
                      value={password}
                      onChange={(e) => setPassword(e.target.value)}
                      InputProps={{
                        sx: { borderRadius: 2, bgcolor: '#F8FAFC', '& fieldset': { borderColor: '#E2E8F0' } },
                        endAdornment: (
                          <InputAdornment position="end">
                            <IconButton onClick={() => setShowPassword(!showPassword)} edge="end">
                              {showPassword ? <VisibilityOff fontSize="small" /> : <Visibility fontSize="small" />}
                            </IconButton>
                          </InputAdornment>
                        ),
                      }}
                    />
                  </Box>

                  <FormControlLabel
                    control={
                      <Checkbox
                        checked={rememberMe}
                        onChange={(e) => setRememberMe(e.target.checked)}
                        size="small"
                        sx={{ color: '#CBD5E1', '&.Mui-checked': { color: '#2563EB' } }}
                      />
                    }
                    label={<Typography variant="body2" color="text.secondary">Keep me logged in</Typography>}
                  />

                  <Button
                    type="submit"
                    fullWidth
                    variant="contained"
                    size="large"
                    disabled={loading}
                    sx={{
                      bgcolor: '#2563EB',
                      py: 1.8, // Taller button
                      borderRadius: 2,
                      fontSize: '1rem',
                      fontWeight: 600,
                      textTransform: 'none',
                      boxShadow: 'none',
                      '&:hover': { bgcolor: '#1D4ED8', boxShadow: 'none' },
                      '&:disabled': { bgcolor: '#93C5FD' }
                    }}
                  >
                    {loading ? 'Signing in...' : 'Log In'}
                  </Button>

                  <Box sx={{ textAlign: 'center', mt: 2 }}>
                     <Typography variant="body2" color="text.secondary">
                        New here?{' '}
                        <Link component={RouterLink} to="/register" fontWeight="bold" underline="hover" sx={{ color: '#2563EB' }}>
                          Create an account
                        </Link>
                     </Typography>
                  </Box>
                </Stack>
              </Box>
            </Paper>
          </Grid>

        </Grid>
      </Container>
    </Box>
  );
}

export default LoginPage;
