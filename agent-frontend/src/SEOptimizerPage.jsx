import React, { useState, useEffect, useRef, useMemo } from 'react';
import { useNavigate } from 'react-router-dom';
import {
  Box, Button, Typography, Paper, Grid, TextField, CircularProgress, List, ListItem, ListItemText,
  ListItemIcon, Accordion, AccordionSummary, AccordionDetails, Alert
} from '@mui/material';
import CheckCircleIcon from '@mui/icons-material/CheckCircle';
import AutoFixHighIcon from '@mui/icons-material/AutoFixHigh';
import WarningIcon from '@mui/icons-material/Warning';
import TravelExploreIcon from '@mui/icons-material/TravelExplore';
import ExpandMoreIcon from '@mui/icons-material/ExpandMore';
import ScienceIcon from '@mui/icons-material/Science';

const API_BASE_URL = import.meta.env.VITE_API_BASE_URL || 'http://127.0.0.1:8000';

const ScopeSection = ({ yourSite, setYourSite, competitorSites, setCompetitorSites, onValidate, isValidating, sitemapStatus, setSitemapStatus }) => {
  const handleManualSitemapChange = (index, value) => {
    const newStatus = [...sitemapStatus];
    newStatus[index].manual_sitemap_url = value;
    setSitemapStatus(newStatus);
  };

  return (
    <>
      <Typography variant="h6" component="h2" gutterBottom>1. Define Scope</Typography>
      <TextField
        label="Your Website URL"
        fullWidth
        margin="normal"
        value={yourSite}
        onChange={e => setYourSite(e.target.value)}
        placeholder="https://www.your-example.com"
      />
      <TextField
        label="Competitor URLs (comma separated)"
        fullWidth
        margin="normal"
        value={competitorSites}
        onChange={e => setCompetitorSites(e.target.value)}
        placeholder="https://www.competitor-a.com"
      />
      <Button
        variant="contained"
        startIcon={isValidating ? <CircularProgress size={20} /> : <TravelExploreIcon />}
        onClick={onValidate}
        disabled={isValidating || !yourSite}
      >
        Validate Sitemaps
      </Button>
      {sitemapStatus.length > 0 && (
        <Box sx={{ mt: 2, maxHeight: '200px', overflowY: 'auto' }}>
          {sitemapStatus.map((status, index) => (
            <Paper key={index} variant="outlined" sx={{ p: 2, mt: 1, borderColor: status.status === 'found' ? 'success.main' : 'warning.main' }}>
              <Typography variant="subtitle2" sx={{ wordBreak: 'break-all' }}>{status.url}</Typography>
              {status.status === 'found' ? (
                <Typography color="success.main" variant="body2">✅ Sitemap Found: {status.sitemap_url}</Typography>
              ) : (
                <TextField
                  label="Sitemap URL Not Found - Please provide manually"
                  fullWidth
                  size="small"
                  margin="dense"
                  value={status.manual_sitemap_url || ''}
                  onChange={(e) => handleManualSitemapChange(index, e.target.value)}
                  placeholder="https://www.your-example.com/sitemap.xml"
                />
              )}
            </Paper>
          ))}
        </Box>
      )}
    </>
  );
};

const PromptSection = ({ prompts, onGenerate, isGenerating, error }) => (
  <>
    <Typography variant="h6" component="h2" sx={{ mt: 3 }} gutterBottom>2. Authority Analysis Prompts</Typography>
    <Button
      variant="outlined"
      size="small"
      startIcon={isGenerating ? <CircularProgress size={16} /> : <AutoFixHighIcon />}
      onClick={onGenerate}
      disabled={isGenerating}
    >
      {isGenerating ? 'Generating...' : 'Auto-Generate Prompts'}
    </Button>

    {prompts && (
      <Box sx={{ mt: 2, maxHeight: '300px', overflowY: 'auto' }}>
        {Object.entries(prompts).map(([category, promptList]) => (
          <Accordion key={category} defaultExpanded sx={{ backgroundColor: '#2a2a2a', color: 'white' }}>
            <AccordionSummary expandIcon={<ExpandMoreIcon sx={{ color: 'white' }} />}>
              <Typography variant="subtitle1" sx={{ textTransform: 'capitalize' }}>{category.replace(/_/g, ' ')}</Typography>
            </AccordionSummary>
            <AccordionDetails>
              <List dense>
                {Array.isArray(promptList) && promptList.map((prompt, index) => (
                  <ListItem key={index}><ListItemText primary={`- ${prompt}`} /></ListItem>
                ))}
              </List>
            </AccordionDetails>
          </Accordion>
        ))}
      </Box>
    )}
    {error && <Alert severity="error" sx={{ mt: 2 }}>{error}</Alert>}
  </>
);

function SEOptimizerPage() {
  const navigate = useNavigate();
  const [yourSite, setYourSite] = useState('');
  const [competitorSites, setCompetitorSites] = useState('');
  const [prompts, setPrompts] = useState(null);
  const [sitemapStatus, setSitemapStatus] = useState([]);
  const [logs, setLogs] = useState([]);
  const [isGeneratingPrompts, setIsGeneratingPrompts] = useState(false);
  const [isValidating, setIsValidating] = useState(false);
  const [isAnalyzing, setIsAnalyzing] = useState(false);
  const [error, setError] = useState(null);
  const ws = useRef(null);

  const competitorUrlList = useMemo(() => 
    competitorSites.split(',').map(s => s.trim()).filter(Boolean),
    [competitorSites]
  );

  useEffect(() => {
    return () => {
      if (ws.current && ws.current.readyState === WebSocket.OPEN) {
        ws.current.close();
      }
    };
  }, []);

  const handleValidateSitemaps = async () => {
    const allUrls = [yourSite, ...competitorUrlList];
    setIsValidating(true);
    setError(null);
    const formData = new FormData();
    allUrls.forEach(url => formData.append('urls', url));
    try {
      const response = await fetch(`${API_BASE_URL}/validate-sitemaps`, { method: 'POST', body: formData });
      if (!response.ok) throw new Error(`HTTP error! Status: ${response.status}`);
      const data = await response.json();
      setSitemapStatus(data.results.map(r => ({...r, manual_sitemap_url: ''})));
    } catch (e) {
      setError(`Failed to validate sitemaps: ${e.message}`);
    } finally {
      setIsValidating(false);
    }
  };

  const handleAutoGeneratePrompts = async () => {
    if (!yourSite) {
      setError("Please enter your website URL first.");
      return;
    }
    setIsGeneratingPrompts(true);
    setError(null);
    setPrompts(null);
    const formData = new FormData();
    formData.append('url', yourSite);
    formData.append('competitors', competitorSites);
    try {
      const response = await fetch(`${API_BASE_URL}/generate-prompts`, { method: 'POST', body: formData });
      const data = await response.json();
      if (!response.ok) {
        throw new Error(data.detail || 'Failed to generate prompts.');
      }
      setPrompts(data.prompts);
    } catch (e) {
      setError(`Failed to generate prompts: ${e.message}`);
    } finally {
      setIsGeneratingPrompts(false);
    }
  };

  const handleRunAnalysis = () => {
    setIsAnalyzing(true);
    setLogs([]);
    setError(null);
    ws.current = new WebSocket(`wss://${API_BASE_URL.replace(/^https?:\/\//, '')}/ws/seo-analysis`);

    ws.current.onopen = () => {
      const getSitemapForUrl = (url) => {
        const status = sitemapStatus.find(s => s.url === url);
        return status?.manual_sitemap_url || status?.sitemap_url || null;
      };
      const payload = {
        yourSite: { url: yourSite, sitemap: getSitemapForUrl(yourSite) },
        competitors: competitorUrlList.map(url => ({ url, sitemap: getSitemapForUrl(url) })),
        prompts: prompts
      };
      ws.current.send(JSON.stringify(payload));
    };

    ws.current.onmessage = (event) => {
      const data = JSON.parse(event.data);
      if (data.log) {
        setLogs(prev => [...prev, { status: 'running', message: data.log, timestamp: new Date() }]);
      } else if (data.report) {
        navigate('/seo-report', { state: { report: data.report } });
        setIsAnalyzing(false);
        ws.current.close();
      } else if (data.status === 'error') {
        const errorMessage = data.message || 'An unknown error occurred.';
        setError(`Analysis Error: ${errorMessage}`);
        setLogs(prev => [...prev, { status: 'error', message: errorMessage, timestamp: new Date() }]);
        setIsAnalyzing(false);
      }
    };
    ws.current.onerror = () => {
      setError('WebSocket connection failed. Check backend logs.');
      setIsAnalyzing(false);
    };
    ws.current.onclose = () => {
      setIsAnalyzing(false);
    };
  };

  return (
    <Box sx={{ p: 4, color: 'white', maxWidth: '1200px', mx: 'auto' }}>
      <Typography variant="h4" component="h1" gutterBottom>LLM Optimization Agent</Typography>
      {error && <Alert severity="error" onClose={() => setError(null)} sx={{ mb: 2 }}>{error}</Alert>}
      <Paper sx={{ p: 3, backgroundColor: '#1E1E1E', color: 'white' }}>
        <Grid container spacing={4}>
          <Grid item xs={12} md={6}>
            <ScopeSection {...{ yourSite, setYourSite, competitorSites, setCompetitorSites, onValidate: handleValidateSitemaps, isValidating, sitemapStatus, setSitemapStatus }} />
            <PromptSection {...{ prompts, onGenerate: handleAutoGeneratePrompts, isGenerating: isGeneratingPrompts, error: prompts?.error }} />
          </Grid>
          <Grid item xs={12} md={6}>
            <Typography variant="h6" component="h2" gutterBottom>3. Agent Status</Typography>
            <Paper variant="outlined" sx={{ p: 2, height: '450px', backgroundColor: '#0d1117', overflowY: 'auto' }}>
              <List dense>
                {logs.length === 0 && !isAnalyzing && <ListItemText primary="Logs will appear here..." sx={{ color: 'grey.500' }} />}
                {isAnalyzing && logs.length === 0 && <Box sx={{ display: 'flex', justifyContent: 'center' }}><CircularProgress /></Box>}
                {logs.map((log, index) => (
                  <ListItem key={log.timestamp.getTime() + index}>
                    <ListItemIcon sx={{ minWidth: '32px' }}>
                      {log.status === 'success' ? <CheckCircleIcon color="success" fontSize="small" /> : log.status === 'error' ? <WarningIcon color="error" fontSize="small" /> : <CircularProgress color="inherit" size={16} />}
                    </ListItemIcon>
                    <ListItemText primary={log.message} />
                  </ListItem>
                ))}
              </List>
            </Paper>
            <Button
              variant="contained"
              color="primary"
              fullWidth
              sx={{ mt: 2, py: 1.5, fontSize: '1rem' }}
              onClick={handleRunAnalysis}
              disabled={isAnalyzing || !yourSite || !prompts}
              startIcon={isAnalyzing ? <CircularProgress color="inherit" size={24} /> : <ScienceIcon />}
            >
              {isAnalyzing ? 'Analysis in Progress...' : 'Run Full Analysis'}
            </Button>
          </Grid>
        </Grid>
      </Paper>
    </Box>
  );
}

export default SEOptimizerPage;