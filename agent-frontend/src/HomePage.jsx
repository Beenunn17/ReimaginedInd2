// src/HomePage.jsx

import React from 'react';
import { Box, Typography, Grid, Paper } from '@mui/material';
import { Link } from 'react-router-dom';
import ScienceIcon from '@mui/icons-material/Science';
import TravelExploreIcon from '@mui/icons-material/TravelExplore';
import CampaignIcon from '@mui/icons-material/Campaign';
import AutoAwesomeIcon from '@mui/icons-material/AutoAwesome';

const agentCards = [
  {
    icon: <ScienceIcon sx={{ fontSize: 40 }} />,
    title: 'Data Science Agent',
    description: 'Leverage time-series forecasting and data analysis to predict trends and make informed decisions.',
    link: '/forecast'
  },
  {
    icon: <TravelExploreIcon sx={{ fontSize: 40 }} />,
    title: 'AI Search Agent',
    description: 'Integrate paid, organic, and marketplace search strategies driven by a unified AI core.',
    link: '#' // Placeholder link
  },
  {
    icon: <CampaignIcon sx={{ fontSize: 40 }} />,
    title: 'Campaign Automation Agent',
    description: 'Automate entire marketing campaigns from creative brief and audience creation to final trafficking.',
    link: '#' // Placeholder link
  },
  {
    icon: <AutoAwesomeIcon sx={{ fontSize: 40 }} />,
    title: 'Generative Marketing Agent',
    description: 'Your primary chat interface for brainstorming, content creation, and strategic marketing insights.',
    link: '/chat'
  }
];

function HomePage() {
  return (
    <Box className="homepage-container">
      {/* Hero Section */}
      <Box className="hero-section">
        <Typography variant="h2" component="h1" className="hero-title">
          Solving Complex Problems with AI
        </Typography>
        <Typography variant="h5" className="hero-subtitle">
          Braid.ai is a modern consultancy focused on integrating artificial intelligence to drive real-world results.
        </Typography>
      </Box>

      {/* Agent Cards Section */}
      <Grid container spacing={4} className="card-grid">
        {agentCards.map((agent) => (
          <Grid item key={agent.title} xs={12} sm={6} md={3}>
            <Link to={agent.link} className="card-link">
              <Paper className="agent-card">
                <Box className="card-icon">{agent.icon}</Box>
                <Typography variant="h6" component="h3" className="card-title">
                  {agent.title}
                </Typography>
                <Typography variant="body2" className="card-description">
                  {agent.description}
                </Typography>
              </Paper>
            </Link>
          </Grid>
        ))}
      </Grid>
    </Box>
  );
}

export default HomePage;