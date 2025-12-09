/**
 * Credit Engine 2.0 - Premium Theme Configuration
 * "Bloomberg Terminal" / "High-End Fintech" aesthetic
 * Slate color palette with professional shadows and depth
 */
import { createTheme } from '@mui/material/styles';

const theme = createTheme({
  palette: {
    mode: 'light',
    primary: { main: '#0F172A' }, // Dark Slate Blue (Institutional, not bright blue)
    secondary: { main: '#3B82F6' }, // Bright Blue for accents/buttons only
    background: {
      default: '#F8FAFC', // Very light slate gray (cool tone, not warm)
      paper: '#FFFFFF',
    },
    text: {
      primary: '#1E293B', // Slate 900
      secondary: '#64748B', // Slate 500
    },
    success: { main: '#10B981', light: '#D1FAE5', contrastText: '#065F46' },
    warning: { main: '#F59E0B', light: '#FEF3C7', contrastText: '#92400E' },
    error: { main: '#EF4444', light: '#FEE2E2', contrastText: '#991B1B' },
    // Custom bureau colors (kept from original)
    transunion: { main: '#00AEEF', contrastText: '#fff' },
    experian: { main: '#ED1C24', contrastText: '#fff' },
    equifax: { main: '#00B140', contrastText: '#fff' },
  },
  typography: {
    fontFamily: '"Inter", "Roboto", "Helvetica", "Arial", sans-serif',
    h1: { fontWeight: 700 },
    h2: { fontWeight: 700, letterSpacing: '-0.02em' }, // Tight numbers look financial
    h4: { fontWeight: 700, letterSpacing: '-0.01em' },
    h5: { fontWeight: 600 },
    h6: { fontWeight: 600 },
    subtitle1: { fontWeight: 600 },
    button: { textTransform: 'none', fontWeight: 600 }, // No ALL CAPS buttons
  },
  components: {
    MuiCard: {
      styleOverrides: {
        root: {
          borderRadius: 16,
          boxShadow: '0px 1px 3px rgba(0, 0, 0, 0.05), 0px 10px 15px -5px rgba(0, 0, 0, 0.04)', // "Float" effect
          border: '1px solid #E2E8F0', // Subtle border
        },
      },
    },
    MuiPaper: {
      styleOverrides: {
        root: {
          borderRadius: 12,
        },
        elevation1: {
          boxShadow: '0px 1px 3px rgba(0, 0, 0, 0.05), 0px 4px 6px -2px rgba(0, 0, 0, 0.03)',
        },
        elevation2: {
          boxShadow: '0px 1px 3px rgba(0, 0, 0, 0.06), 0px 8px 12px -4px rgba(0, 0, 0, 0.05)',
        },
        elevation3: {
          boxShadow: '0px 1px 3px rgba(0, 0, 0, 0.08), 0px 12px 20px -6px rgba(0, 0, 0, 0.06)',
        },
      },
    },
    MuiButton: {
      styleOverrides: {
        root: {
          borderRadius: 8,
          boxShadow: 'none',
          fontWeight: 600,
        },
        contained: {
          backgroundColor: '#2563EB',
          '&:hover': {
            backgroundColor: '#1D4ED8',
            boxShadow: '0 4px 12px rgba(37, 99, 235, 0.25)',
          },
        },
        containedSuccess: {
          backgroundColor: '#10B981',
          '&:hover': {
            backgroundColor: '#059669',
            boxShadow: '0 4px 12px rgba(16, 185, 129, 0.25)',
          },
        },
        outlined: {
          borderColor: '#E2E8F0',
          '&:hover': {
            borderColor: '#CBD5E1',
            backgroundColor: '#F8FAFC',
          },
        },
      },
    },
    MuiChip: {
      styleOverrides: {
        root: {
          fontWeight: 500,
          borderRadius: 6,
        },
        filled: {
          border: '1px solid transparent',
        },
        outlined: {
          borderColor: '#E2E8F0',
          backgroundColor: '#fff',
        },
      },
    },
    MuiAccordion: {
      styleOverrides: {
        root: {
          boxShadow: '0px 1px 3px rgba(0, 0, 0, 0.04)',
          '&:before': { display: 'none' },
          border: '1px solid #E2E8F0',
        },
      },
    },
    MuiTab: {
      styleOverrides: {
        root: {
          fontWeight: 600,
          textTransform: 'none',
        },
      },
    },
    MuiDivider: {
      styleOverrides: {
        root: {
          borderColor: '#E2E8F0',
        },
      },
    },
    MuiDrawer: {
      styleOverrides: {
        paper: {
          borderRight: '1px solid #E2E8F0',
        },
      },
    },
  },
});

// Bureau color helper
export const BUREAU_COLORS = {
  TU: '#00AEEF',
  EXP: '#ED1C24',
  EQ: '#00B140',
  TransUnion: '#00AEEF',
  Experian: '#ED1C24',
  Equifax: '#00B140',
};

// Severity badge colors (fintech style)
export const SEVERITY_COLORS = {
  HIGH: { bg: '#FEE2E2', text: '#991B1B', border: '#FECACA' },
  MEDIUM: { bg: '#FEF3C7', text: '#92400E', border: '#FDE68A' },
  LOW: { bg: '#D1FAE5', text: '#065F46', border: '#A7F3D0' },
};

export default theme;
