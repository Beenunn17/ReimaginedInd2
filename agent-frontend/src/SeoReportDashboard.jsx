import React from 'react';
import { useLocation, Link } from 'react-router-dom';
import { Box, Typography, Paper, Grid, Accordion, AccordionSummary, AccordionDetails, List, ListItem, ListItemText, Button } from '@mui/material';
import ExpandMoreIcon from '@mui/icons-material/ExpandMore';
import PageviewIcon from '@mui/icons-material/Pageview';
import ContentPasteSearchIcon from '@mui/icons-material/ContentPasteSearch';
import TravelExploreIcon from '@mui/icons-material/TravelExplore';

// A resilient helper component to render sections of the report
const ReportSection = ({ title, data, icon }) => {
  // Don't render the section if data is missing or empty
  if (!data || (Array.isArray(data) && data.length === 0)) {
    return null;
  }

  const renderListItems = (items) => {
    if (!Array.isArray(items)) {
        return <ListItem><ListItemText primary={items.toString()} /></ListItem>;
    }
    return items.map((item, index) => (
      <ListItem key={index}>
        <ListItemText 
          primary={typeof item === 'object' ? item.point || JSON.stringify(item) : item} 
        />
      </ListItem>
    ));
  };

  return (
    <Grid item xs={12} md={6}>
      <Accordion defaultExpanded sx={{ backgroundColor: '#2a2a2a', color: 'white' }}>
        <AccordionSummary expandIcon={<ExpandMoreIcon sx={{ color: 'white' }} />}>
          {icon}
          <Typography sx={{ ml: 1, fontWeight: 'bold' }}>{title}</Typography>
        </AccordionSummary>
        <AccordionDetails>
          <List dense>
            {renderListItems(data)}
          </List>
        </AccordionDetails>
      </Accordion>
    </Grid>
  );
};


function SeoReportDashboard() {
  const location = useLocation();
  // Use optional chaining (?.) to safely access nested state
  const report = location.state?.report;

  if (!report) {
    return (
      <Box sx={{ padding: 4, textAlign: 'center', color: 'white' }}>
        <Typography variant="h5" gutterBottom>No Report Data Found</Typography>
        <Typography>The analysis may have completed without generating a report, or you may have accessed this page directly.</Typography>
        <Button component={Link} to="/seo-optimizer" variant="contained" sx={{ mt: 2 }}>
          Run a New Analysis
        </Button>
      </Box>
    );
  }
  
  // Safely destructure the report using optional chaining
  const { reportTitle, schemaAudit, authorityAudit, authorityAnalysis } = report;

  return (
    <Box sx={{ padding: { xs: 2, sm: 4 }, color: 'white', maxWidth: '1200px', margin: 'auto' }}>
      <Typography variant="h4" component="h1" gutterBottom>
        {reportTitle || 'SEO Analysis Report'}
      </Typography>
      <Paper sx={{ p: { xs: 2, sm: 3 }, backgroundColor: '#1E1E1E', color: 'white' }}>
        <Grid container spacing={3}>
          {/* Main Audit Sections - Safely access nested properties */}
          <ReportSection title="Schema Audit" data={schemaAudit?.summary ? [schemaAudit.summary] : null} icon={<PageviewIcon color="primary"/>} />
          <ReportSection title="Authority Audit" data={authorityAudit?.insights} icon={<TravelExploreIcon color="primary"/>} />

          {/* Detailed Gemini Analysis - Safely access nested properties */}
          {Object.entries(authorityAnalysis?.gemini || {}).map(([category, results]) => (
            <ReportSection 
              key={`gemini-${category}`}
              title={`Gemini: ${category.replace(/_/g, ' ')}`}
              data={results}
              icon={<ContentPasteSearchIcon color="secondary"/>} 
            />
          ))}
          
          {/* Detailed OpenAI Analysis - Safely access nested properties */}
          {Object.entries(authorityAnalysis?.openai || {}).map(([category, results]) => (
            <ReportSection 
              key={`openai-${category}`}
              title={`OpenAI: ${category.replace(/_/g, ' ')}`}
              data={results}
              icon={<ContentPasteSearchIcon color="action"/>} 
            />
          ))}
        </Grid>
      </Paper>
    </Box>
  );
}

export default SeoReportDashboard;