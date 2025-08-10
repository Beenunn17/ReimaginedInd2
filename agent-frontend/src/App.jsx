import React, { useState } from 'react';
import { BrowserRouter, Routes, Route, Link } from 'react-router-dom';
import { createTheme, ThemeProvider } from '@mui/material/styles';
import {
  CssBaseline, AppBar, Toolbar, Typography,
  Box, IconButton, Menu, MenuItem
} from '@mui/material';
import MenuIcon from '@mui/icons-material/Menu';
import './App.css';

// Import all your page components
import HomePage from './HomePage';
// import ChatPage from './ChatPage'; // Chat is temporarily disabled
import SEOptimizerPage from './SEOptimizerPage';
import ForecastPage from './ForecastPage';
// Import the new Creative Hub page instead of the old CreativePage
import CreativeHubPage from './CreativeHubPage'; 

// Updated theme to match the "Reimagined Industries" brand guide
const darkTheme = createTheme({
  palette: {
    mode: 'dark',
    primary: {
      main: '#c2cbd4', // Light Blue Gray from your slide
    },
    background: {
      default: '#000000', // Black background
      paper: '#1E1E1E',   // A slightly lighter black for elevated surfaces like cards
    },
    text: {
      primary: '#f8f9fa',   // Light Gray 3 for primary text
      secondary: '#c2cbd4', // Light Blue Gray for secondary text
    },
  },
  typography: {
    // Set the site-wide font to Helvetica Neue
    fontFamily: '"Helvetica Neue", Arial, sans-serif',
    
    // Apply styles to all typography variants to match the brand guide
    allVariants: {
      textTransform: 'uppercase', // Set text to uppercase globally
      fontWeight: 700, // Use bold weight to match "Helvetica Neue Bold"
    },
    // Override body2 specifically for non-uppercase text where needed (like in reports)
    body2: {
        textTransform: 'none',
        fontWeight: 400,
    }
  },
  components: {
    // Component-specific overrides
    MuiButton: {
      styleOverrides: {
        root: {
          fontWeight: 700, // Ensure buttons are also bold
        },
      },
    },
  },
});


function App() {
  const [anchorEl, setAnchorEl] = useState(null);
  const handleMenu = (event) => setAnchorEl(event.currentTarget);
  const handleClose = () => setAnchorEl(null);

  return (
    <ThemeProvider theme={darkTheme}>
      <CssBaseline />
      <BrowserRouter>
        <Box sx={{
          display: 'flex',
          flexDirection: 'column',
          minHeight: '100vh',
          bgcolor: 'background.default',
          color: 'text.primary',
        }}>
          <AppBar position="fixed" sx={{ backgroundColor: 'rgba(0,0,0,0.8)', backdropFilter: 'blur(10px)'}}>
            <Toolbar>
              <IconButton edge="start" color="inherit" aria-label="menu" sx={{ mr: 2 }} onClick={handleMenu}>
                <MenuIcon />
              </IconButton>
              <Menu anchorEl={anchorEl} open={Boolean(anchorEl)} onClose={handleClose}>
                <MenuItem component={Link} to="/" onClick={handleClose}>Home</MenuItem>
                {/* <MenuItem component={Link} to="/chat" onClick={handleClose}>Marketing Agent</MenuItem> */}
                <MenuItem component={Link} to="/seo-optimizer" onClick={handleClose}>SEO Optimizer</MenuItem>
                <MenuItem component={Link} to="/forecast" onClick={handleClose}>Data Science Agent</MenuItem>
                <MenuItem component={Link} to="/creative" onClick={handleClose}>Creative Agent</MenuItem>
              </Menu>
              <Box sx={{ flexGrow: 1 }} />
              <img src="/logo.png" alt="Braid.ai Logo" style={{ height: '40px', borderRadius: '50%' }} />
            </Toolbar>
          </AppBar>

          <Box component="main" sx={{ flexGrow: 1, pt: '64px', width: '100%' }}>
            <Routes>
              {/* <Route path="/chat" element={<ChatPage />} /> */}
              <Route path="/forecast" element={<ForecastPage />} />
              <Route path="/seo-optimizer" element={<SEOptimizerPage />} />
                  {/* === THIS IS THE IMPORTANT CHANGE === */}
              <Route path="/creative" element={<CreativeHubPage />} /> 
              <Route path="/" element={<HomePage />} />
            </Routes>
          </Box>
        </Box>
      </BrowserRouter>
    </ThemeProvider>
  );
}

export default App;