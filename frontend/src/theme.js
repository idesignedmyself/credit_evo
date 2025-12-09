/**
 * Credit Engine 2.0 - Theme Configuration
 * Custom MUI theme with bureau colors and modern styling
 */
import { createTheme } from '@mui/material/styles';

const theme = createTheme({
  palette: {
    mode: 'light',
    primary: { main: '#2563EB' }, // Sharp, trust-building blue
    secondary: { main: '#dc004e' },
    background: {
      default: '#F3F4F6', // Light grey background makes white cards pop
      paper: '#FFFFFF'
    },
    // Custom bureau colors
    transunion: { main: '#00AEEF', contrastText: '#fff' },
    experian: { main: '#ED1C24', contrastText: '#fff' },
    equifax: { main: '#00B140', contrastText: '#fff' },
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
    MuiCard: {
      styleOverrides: {
        root: {
          borderRadius: 12, // Softer, modern corners
          boxShadow: '0px 4px 20px rgba(0, 0, 0, 0.05)', // Subtle elevation
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
    MuiChip: {
      styleOverrides: {
        root: {
          fontWeight: 600,
          borderRadius: 8
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

export default theme;
