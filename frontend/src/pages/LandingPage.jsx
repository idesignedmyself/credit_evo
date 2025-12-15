/**
 * Credit Engine 2.0 - Landing Page
 * "Credit Copilot" Marketing Landing Page with Hero, Features, Pricing, About
 */
import React, { useState } from 'react';
import { useNavigate, Link as RouterLink } from 'react-router-dom';
import {
  Box, Container, Typography, Button, TextField, Grid, Paper,
  Stack, Link, InputAdornment, IconButton, Divider, Checkbox, FormControlLabel, Alert
} from '@mui/material';
import Visibility from '@mui/icons-material/Visibility';
import VisibilityOff from '@mui/icons-material/VisibilityOff';
import SmartToyIcon from '@mui/icons-material/SmartToy';
import CompareArrowsIcon from '@mui/icons-material/CompareArrows';
import BugReportIcon from '@mui/icons-material/BugReport';
import SettingsIcon from '@mui/icons-material/Settings';
import EditIcon from '@mui/icons-material/Edit';
import LockIcon from '@mui/icons-material/Lock';
import CheckIcon from '@mui/icons-material/Check';
import DescriptionIcon from '@mui/icons-material/Description';
import useAuthStore from '../state/authStore';
import { login, getMe } from '../api/authApi';

// Shared gradient background
const GRADIENT_BG = 'linear-gradient(135deg, #0F172A 0%, #1E3A5F 50%, #1E40AF 100%)';

// ============================================================================
// NAVBAR COMPONENT - Transparent to blend with gradient
// ============================================================================
const Navbar = () => (
  <Box
    sx={{
      position: 'fixed',
      top: 0,
      left: 0,
      right: 0,
      zIndex: 1000,
      // Transparent background - blends with the page gradient
      bgcolor: 'transparent',
    }}
  >
    <Box sx={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', py: 2.5, px: { xs: 3, md: 6 } }}>
      <Link
        href="#"
        onClick={(e) => {
          e.preventDefault();
          window.scrollTo({ top: 0, behavior: 'smooth' });
        }}
        underline="none"
        sx={{ display: 'flex', alignItems: 'center', gap: 1.5, cursor: 'pointer' }}
      >
        <DescriptionIcon sx={{ color: '#60A5FA', fontSize: 28 }} />
        <Typography variant="h6" fontWeight="bold" sx={{ color: 'white' }}>
          Credit Copilot
        </Typography>
      </Link>
      <Stack direction="row" spacing={5} sx={{ display: { xs: 'none', md: 'flex' } }}>
        <Link href="#features" underline="none" sx={{ color: '#94A3B8', fontWeight: 500, '&:hover': { color: 'white' } }}>
          Features
        </Link>
        <Link href="#pricing" underline="none" sx={{ color: '#94A3B8', fontWeight: 500, '&:hover': { color: 'white' } }}>
          Pricing
        </Link>
        <Link href="#about" underline="none" sx={{ color: '#94A3B8', fontWeight: 500, '&:hover': { color: 'white' } }}>
          About
        </Link>
      </Stack>
    </Box>
  </Box>
);

// ============================================================================
// HERO SECTION WITH LOGIN FORM - Matching LoginPage proportions
// ============================================================================
const HeroSection = () => {
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
      const tokenData = await login(email, password);
      localStorage.setItem('credit_engine_token', tokenData.access_token);
      const userData = await getMe();
      storeLogin(tokenData.access_token, userData);
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
        background: GRADIENT_BG,
        display: 'flex',
        alignItems: 'center',
        pt: 8, // Account for navbar
      }}
    >
      <Box sx={{ width: '100%', px: { xs: 3, md: 6 } }}>
        <Grid container spacing={8} alignItems="center">
          {/* Left Side - Marketing Copy (hidden on mobile) */}
          <Grid item xs={12} md={6} sx={{ display: { xs: 'none', md: 'block' }, color: 'white' }}>
            <Box sx={{ mb: 4, display: 'flex', alignItems: 'center', gap: 2 }}>
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

          {/* Right Side - Login Form (matching LoginPage exactly) */}
          <Grid item xs={12} md={6} sx={{ display: 'flex', justifyContent: 'flex-end' }}>
            <Paper
              elevation={0}
              sx={{
                p: { xs: 3, md: 6 },
                borderRadius: 4,
                bgcolor: 'white',
                maxWidth: '500px',
                width: '100%',
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
                      py: 1.8,
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
      </Box>
    </Box>
  );
};

// ============================================================================
// FEATURES SECTION
// ============================================================================
const features = [
  {
    icon: <SmartToyIcon sx={{ fontSize: 32, color: '#60A5FA' }} />,
    title: 'AI-Powered Dispute Letters',
    description: 'Generate professionally written, statute-grounded dispute letters. Per-bureau targeting, strong legal basis, and PDF export.',
    bullets: ['Per-bureau letters (TU/EX/EQ)', 'FCRA/FDCPA citations + MOV', 'PDF generation & download']
  },
  {
    icon: <CompareArrowsIcon sx={{ fontSize: 32, color: '#60A5FA' }} />,
    title: 'Tri-Merge Parsing (IdentityIQ)',
    description: 'Side-by-side comparison across TransUnion, Experian, and Equifax. Detect mismatches and select exact bureaus to dispute.',
    bullets: ['Cross-bureau comparison table', 'Mismatch highlighting', '"Select mismatches" toggle']
  },
  {
    icon: <BugReportIcon sx={{ fontSize: 32, color: '#60A5FA' }} />,
    title: 'Error Detection & Mapping',
    description: 'Maps detected issues (duplicates, status mismatches, re-aging, missing info) to the right legal statutes and dispute strategy.',
    bullets: ['Error classification', 'Statute mapping', 'Clear dispute context']
  },
  {
    icon: <SettingsIcon sx={{ fontSize: 32, color: '#60A5FA' }} />,
    title: 'Local LLM Streaming',
    description: 'Works with Ollama (local), vLLM, or OpenAI-compatible servers. Streams text live so you can review and stop early if desired.',
    bullets: ['Ollama / vLLM / OpenAI-compatible', 'Fast streaming preview', 'Configurable tokens & timeouts']
  },
  {
    icon: <EditIcon sx={{ fontSize: 32, color: '#60A5FA' }} />,
    title: 'Edit & Manage Letters',
    description: 'Open any letter, edit the content or title, and regenerate the PDF with one click. View history from the dashboard.',
    bullets: ['Letter detail view', 'Inline editing', 'Instant PDF re-render']
  },
  {
    icon: <LockIcon sx={{ fontSize: 32, color: '#60A5FA' }} />,
    title: 'Secure by Design',
    description: 'JWT auth + CSRF protection. Files stored locally. Knowledge Base search enhances prompts with statute context.',
    bullets: ['JWT + CSRF', 'Local storage', 'KB-enhanced prompts']
  }
];

const FeaturesSection = () => (
  <Box id="features" sx={{ py: 12, background: GRADIENT_BG }}>
    <Container maxWidth="lg">
      <Box sx={{ textAlign: 'center', mb: 8 }}>
        <Typography variant="h3" fontWeight="800" sx={{ color: 'white', mb: 2 }}>
          Powerful Features for<br />
          <Box component="span" sx={{ color: '#60A5FA' }}>Credit Success</Box>
        </Typography>
        <Typography variant="body1" sx={{ color: '#94A3B8', maxWidth: 600, mx: 'auto' }}>
          Upload reports, compare bureaus, select mismatches, and generate statute-backed dispute letters - all with fast, local AI.
        </Typography>
      </Box>

      <Grid container spacing={4}>
        {features.map((feature, index) => (
          <Grid item xs={12} md={4} key={index}>
            <Paper
              sx={{
                p: 4,
                height: '100%',
                bgcolor: 'rgba(30, 58, 95, 0.5)',
                border: '1px solid rgba(96, 165, 250, 0.2)',
                borderRadius: 3,
              }}
            >
              <Box sx={{ display: 'flex', alignItems: 'center', gap: 2, mb: 2 }}>
                <Box sx={{ p: 1.5, bgcolor: 'rgba(96, 165, 250, 0.1)', borderRadius: 2 }}>
                  {feature.icon}
                </Box>
                <Typography variant="h6" fontWeight="bold" sx={{ color: '#60A5FA' }}>
                  {feature.title}
                </Typography>
              </Box>
              <Typography variant="body2" sx={{ color: '#94A3B8', mb: 2, lineHeight: 1.7 }}>
                {feature.description}
              </Typography>
              <Stack spacing={0.75}>
                {feature.bullets.map((bullet, i) => (
                  <Typography key={i} variant="body2" sx={{ color: '#60A5FA', display: 'flex', alignItems: 'center', gap: 1 }}>
                    <Box sx={{ width: 5, height: 5, bgcolor: '#60A5FA', borderRadius: '50%' }} />
                    {bullet}
                  </Typography>
                ))}
              </Stack>
            </Paper>
          </Grid>
        ))}
      </Grid>
    </Container>
  </Box>
);

// ============================================================================
// PRICING SECTION
// ============================================================================
const pricingPlans = [
  {
    name: 'Plus',
    tagline: 'Your AI assistant for smarter disputes.',
    price: '$49',
    features: [
      'Upload IdentityIQ tri-merge -> full parsing + all errors identified.',
      'Copilot drafts complete letters with citations (user reviews/approves).',
      '1 certified letter included/month (extra $12.50 each).',
      'Basic timeline (mailed/delivered status).'
    ]
  },
  {
    name: 'Pro',
    tagline: 'Your AI Case Manager - disputes that run on rails.',
    price: '$99',
    popular: true,
    features: [
      'Everything in Plus.',
      'Copilot tracks 30-day SLA deadlines.',
      'Auto-prepares follow-up MOV/623 letters.',
      'Push/email reminders: "Deadline approaching - approve next letter."',
      '3 certified letters included/month (extra $12 each).'
    ]
  },
  {
    name: 'Premium',
    tagline: 'Hands-off autopilot - your AI fights every battle.',
    price: '$149',
    features: [
      'Everything in Pro.',
      'Autopilot mode: continuous cycles until items are deleted/corrected.',
      'Handles multiple accounts in bulk.',
      'Generates full evidence packet + timeline reports.',
      '6 certified letters included/month (extra $11.50 each).'
    ]
  }
];

const PricingSection = () => (
  <Box id="pricing" sx={{ py: 12, background: GRADIENT_BG }}>
    <Container maxWidth="lg">
      <Box sx={{ textAlign: 'center', mb: 8 }}>
        <Typography variant="h3" fontWeight="800" sx={{ color: 'white', mb: 2 }}>
          Choose Your<br />
          <Box component="span" sx={{ color: '#60A5FA' }}>Copilot Plan</Box>
        </Typography>
        <Typography variant="body1" sx={{ color: '#94A3B8', maxWidth: 600, mx: 'auto' }}>
          Select the perfect plan for your credit copilot journey. All plans include our AI-powered dispute letter generation and comprehensive credit error detection.
        </Typography>
      </Box>

      <Grid container spacing={4} justifyContent="center">
        {pricingPlans.map((plan, index) => (
          <Grid item xs={12} md={4} key={index}>
            <Paper
              sx={{
                p: 4,
                height: '100%',
                bgcolor: 'white',
                borderRadius: 3,
                position: 'relative',
                border: plan.popular ? '2px solid #2563EB' : 'none',
                transform: plan.popular ? 'scale(1.02)' : 'none',
              }}
            >
              {plan.popular && (
                <Box
                  sx={{
                    position: 'absolute',
                    top: -12,
                    left: '50%',
                    transform: 'translateX(-50%)',
                    bgcolor: '#2563EB',
                    color: 'white',
                    px: 3,
                    py: 0.5,
                    borderRadius: 2,
                    fontSize: '0.75rem',
                    fontWeight: 600
                  }}
                >
                  Most Popular
                </Box>
              )}

              <Box sx={{ textAlign: 'center', mb: 3 }}>
                <Typography variant="h5" fontWeight="bold" sx={{ mb: 0.5 }}>
                  {plan.name}
                </Typography>
                <Typography variant="body2" color="text.secondary" sx={{ mb: 2, minHeight: 40 }}>
                  {plan.tagline}
                </Typography>
                <Typography variant="h3" fontWeight="800" sx={{ color: '#0F172A' }}>
                  {plan.price}<Typography component="span" variant="body1" color="text.secondary">/mo</Typography>
                </Typography>
              </Box>

              <Divider sx={{ my: 3 }} />

              <Typography variant="subtitle2" fontWeight="bold" sx={{ mb: 2 }}>
                What you get
              </Typography>
              <Stack spacing={1.5}>
                {plan.features.map((feature, i) => (
                  <Box key={i} sx={{ display: 'flex', gap: 1.5 }}>
                    <CheckIcon sx={{ fontSize: 18, color: '#10B981', flexShrink: 0, mt: 0.3 }} />
                    <Typography variant="body2" color="text.secondary">
                      {feature}
                    </Typography>
                  </Box>
                ))}
              </Stack>

              <Button
                fullWidth
                variant="contained"
                sx={{
                  mt: 4,
                  bgcolor: '#2563EB',
                  py: 1.5,
                  borderRadius: 2,
                  textTransform: 'none',
                  fontWeight: 600,
                  '&:hover': { bgcolor: '#1D4ED8' }
                }}
              >
                Get Started
              </Button>
            </Paper>
          </Grid>
        ))}
      </Grid>
    </Container>
  </Box>
);

// ============================================================================
// ABOUT SECTION
// ============================================================================
const AboutSection = () => (
  <Box id="about" sx={{ py: 12, background: GRADIENT_BG }}>
    <Container maxWidth="lg">
      <Box sx={{ textAlign: 'center', mb: 6 }}>
        <Typography variant="h3" fontWeight="800" sx={{ color: 'white', mb: 2 }}>
          About<br />
          <Box component="span" sx={{ color: '#60A5FA' }}>Credit Copilot</Box>
        </Typography>
        <Typography variant="body1" sx={{ color: '#94A3B8', maxWidth: 700, mx: 'auto' }}>
          We're on a mission to make credit repair accessible, effective, and transparent for everyone.
          Our AI-powered platform combines cutting-edge technology with human expertise to deliver results.
        </Typography>
      </Box>

      <Paper
        sx={{
          p: 6,
          bgcolor: 'rgba(30, 58, 95, 0.5)',
          border: '1px solid rgba(96, 165, 250, 0.2)',
          borderRadius: 4,
        }}
      >
        <Grid container spacing={4} alignItems="center">
          <Grid item xs={12} md={6}>
            <Typography variant="h4" fontWeight="bold" sx={{ color: 'white', mb: 3 }}>
              Our Story
            </Typography>
            <Typography variant="body1" sx={{ color: '#94A3B8', lineHeight: 1.8, mb: 2 }}>
              Founded in 2023, Credit Copilot emerged from a simple observation: traditional credit repair
              was outdated, expensive, and often ineffective. Our founders, coming from backgrounds in
              fintech and AI, saw an opportunity to revolutionize the industry.
            </Typography>
            <Typography variant="body1" sx={{ color: '#94A3B8', lineHeight: 1.8 }}>
              Today, we've helped over 50,000 customers improve their credit scores using our proprietary
              AI algorithms and expert-crafted dispute strategies. We're not just a software company -
              we're your partner in financial empowerment.
            </Typography>
          </Grid>
          <Grid item xs={12} md={6}>
            <Paper
              sx={{
                p: 4,
                bgcolor: 'rgba(15, 23, 42, 0.6)',
                borderRadius: 3,
              }}
            >
              <Grid container spacing={3}>
                {[
                  { value: '50,000+', label: 'Happy Customers' },
                  { value: '150+', label: 'Average Score Improvement' },
                  { value: '95%', label: 'Success Rate' },
                  { value: '24/7', label: 'Support Available' }
                ].map((stat, i) => (
                  <Grid item xs={6} key={i}>
                    <Box sx={{ textAlign: 'center' }}>
                      <Typography variant="h4" fontWeight="bold" sx={{ color: '#60A5FA' }}>
                        {stat.value}
                      </Typography>
                      <Typography variant="body2" sx={{ color: '#94A3B8' }}>
                        {stat.label}
                      </Typography>
                    </Box>
                  </Grid>
                ))}
              </Grid>
            </Paper>
          </Grid>
        </Grid>
      </Paper>
    </Container>
  </Box>
);

// ============================================================================
// FOOTER
// ============================================================================
const Footer = () => (
  <Box sx={{ py: 4, background: GRADIENT_BG, borderTop: '1px solid rgba(255,255,255,0.1)' }}>
    <Container maxWidth="lg">
      <Box sx={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', flexWrap: 'wrap', gap: 2 }}>
        <Stack direction="row" alignItems="center" spacing={1.5}>
          <DescriptionIcon sx={{ color: '#60A5FA', fontSize: 24 }} />
          <Typography variant="body1" fontWeight="bold" sx={{ color: 'white' }}>
            Credit Copilot
          </Typography>
        </Stack>
        <Typography variant="body2" sx={{ color: '#64748B' }}>
          2024 Credit Copilot. All rights reserved.
        </Typography>
      </Box>
    </Container>
  </Box>
);

// ============================================================================
// MAIN LANDING PAGE COMPONENT
// ============================================================================
export default function LandingPage() {
  return (
    <Box sx={{ background: GRADIENT_BG }}>
      <Navbar />
      <HeroSection />
      <FeaturesSection />
      <PricingSection />
      <AboutSection />
      <Footer />
    </Box>
  );
}
