import { createTheme } from '@mui/material/styles';

export const theme = createTheme({
  palette: {
    primary: {
      main: '#1a365d', // legal navy
      light: '#2c5282',
      dark: '#102a43',
      contrastText: '#ffffff',
    },
    secondary: {
      main: '#d69e2e', // legal gold
      light: '#ecc94b',
      dark: '#b7791f',
      contrastText: '#000000',
    },
    background: {
      default: '#f7fafc',
      paper: '#ffffff',
    },
    text: {
      primary: '#1a202c',
      secondary: '#4a5568',
    },
    error: {
      main: '#e53e3e',
    },
    warning: {
      main: '#dd6b20',
    },
    info: {
      main: '#3182ce',
    },
    success: {
      main: '#38a169',
    },
  },
  typography: {
    fontFamily: '"Inter", "system-ui", sans-serif',
    h1: {
      fontFamily: '"Merriweather", "Georgia", serif',
      fontWeight: 700,
    },
    h2: {
      fontFamily: '"Merriweather", "Georgia", serif',
      fontWeight: 700,
    },
    h3: {
      fontFamily: '"Merriweather", "Georgia", serif',
      fontWeight: 600,
    },
    h4: {
      fontFamily: '"Merriweather", "Georgia", serif',
      fontWeight: 600,
    },
    h5: {
      fontFamily: '"Merriweather", "Georgia", serif',
      fontWeight: 500,
    },
    h6: {
      fontFamily: '"Merriweather", "Georgia", serif',
      fontWeight: 500,
    },
    button: {
      textTransform: 'none',
      fontWeight: 500,
    },
  },
  shape: {
    borderRadius: 8,
  },
  components: {
    MuiButton: {
      styleOverrides: {
        root: {
          borderRadius: 6,
          padding: '8px 16px',
        },
        containedPrimary: {
          boxShadow: 'none',
          '&:hover': {
            boxShadow: '0 2px 4px rgba(0,0,0,0.1)',
          },
        },
      },
    },
    MuiCard: {
      styleOverrides: {
        root: {
          boxShadow: '0 1px 3px rgba(0,0,0,0.1)',
        },
      },
    },
    MuiTextField: {
      defaultProps: {
        variant: 'outlined',
        size: 'small',
      },
    },
  },
});