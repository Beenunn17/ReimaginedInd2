import React, { useState, useEffect, useRef } from 'react';
import { Box, Button, Typography, Paper, Grid, TextField, CircularProgress, Link, Chip, List, ListItem, ListItemIcon, ListItemText, Table, TableBody, TableCell, TableContainer, TableHead, TableRow, ToggleButtonGroup, ToggleButton } from '@mui/material';
import CheckCircleIcon from '@mui/icons-material/CheckCircle';
import QuestionAnswerIcon from '@mui/icons-material/QuestionAnswer';
import ReactMarkdown from 'react-markdown';
import remarkGfm from 'remark-gfm';

// DEFINE THE API BASE URL AT THE TOP
const API_BASE_URL = import.meta.env.VITE_API_BASE_URL || 'http://127.0.0.1:8000';

// --- A dedicated component to render the beautiful report ---
const AnalysisReport = ({ result }) => {
  if (!result) return null;
  if (result.error) {
    return <Typography color="error" sx={{ mt: 2 }}>Error: {result.error}</Typography>;
  }

  return (
    <Paper sx={{ p: 3, backgroundColor: '#2a2a2a', mt: 2, border: '1px solid rgba(255,255,255,0.23)' }}>
      <Typography variant="h5" component="h3" gutterBottom fontWeight="bold">{result.reportTitle}</Typography>
      
      <Box sx={{ my: 3 }}>
        <Typography variant="h6" gutterBottom>Key Insights</Typography>
        <Box sx={{ display: 'flex', gap: 2, flexWrap: 'wrap' }}>
          {result.keyInsights?.map((item, index) => (
            <Chip key={index} label={`${item.insight} (${item.metric})`} variant="outlined" />
          ))}
        </Box>
      </Box>

      {result.visualization ? (
        <Box sx={{ my: 3 }}>
          <img src={result.visualization} alt="Analysis Plot" style={{ width: '100%', borderRadius: '8px', padding: '10px' }} />
        </Box>
      ) : (
        result.code_error && (
          <Box sx={{ my: 3 }}>
            <Typography variant="h6" gutterBottom>Visualization Error</Typography>
            <Paper component="pre" sx={{ p: 2, backgroundColor: '#000', whiteSpace: 'pre-wrap', wordBreak: 'break-all', color: 'error.main' }}>
              {result.code_error}
            </Paper>
          </Box>
        )
      )}

      <Box sx={{ my: 3 }}>
        <Typography variant="h6" gutterBottom>Summary</Typography>
        <Typography variant="body1" color="text.secondary">{result.summary}</Typography>
      </Box>

      {result.stepsTaken && result.stepsTaken.length > 0 && (
        <Box sx={{ my: 3 }}>
          <Typography variant="h6" gutterBottom>Steps Taken</Typography>
          <List dense>
            {result.stepsTaken.map((step, index) => (<ListItem key={index} disableGutters><ListItemIcon sx={{minWidth: '32px'}}><Typography color="primary">{index + 1}.</Typography></ListItemIcon><ListItemText primary={step} /></ListItem>))}
          </List>
        </Box>
      )}

      {result.recommendations && (
        <Box sx={{ my: 3 }}>
          <Typography variant="h6" gutterBottom>Recommendations</Typography>
          <List>
            {result.recommendations.map((rec, index) => (<ListItem key={index} disableGutters><ListItemIcon sx={{ minWidth: '32px' }}><CheckCircleIcon color="success" fontSize="small" /></ListItemIcon><ListItemText primary={rec} /></ListItem>))}
          </List>
        </Box>
      )}
    </Paper>
  );
};

// --- A component to render a preview of the data ---
const DataPreview = ({ data }) => {
  if (!data || !data.columns || !data.data) return <Box sx={{display: 'flex', justifyContent: 'center', my:2}}><CircularProgress size={24} /></Box>;
  return (
    <TableContainer component={Paper} variant="outlined" sx={{ mt: 2, backgroundColor: '#0d1117' }}>
      <Table size="small">
        <TableHead>
          <TableRow>{data.columns.map(col => <TableCell key={col} sx={{ fontWeight: 'bold' }}>{col}</TableCell>)}</TableRow>
        </TableHead>
        <TableBody>
          {data.data.map((row, rowIndex) => (<TableRow key={rowIndex}>{row.map((cell, cellIndex) => <TableCell key={cellIndex}>{cell}</TableCell>)}</TableRow>))}
        </TableBody>
      </Table>
    </TableContainer>
  );
};

const datasets = [
  { title: "Marketing Mix Model (Advanced)", filename: "mmm_advanced_data.csv", description: "Run a Bayesian MMM on a rich dataset with 10+ channels.", schemaDescription: `3 years of weekly data for sales, 10+ media channels, and external factors like competitor spend and inflation.`, samplePrompt: `Run a full Bayesian MMM to determine the ROI of each channel and provide an optimized budget mix for a revenue target of $3,000,000.` },
  { title: "Customer Churn", filename: "customer_churn.csv", description: "Analyze features affecting customer retention.", schemaDescription: `A table of customer data.\n- CustomerID: Unique identifier for each customer.\n- TenureMonths: How long the customer has been with the company.\n- MonthlyCharge: The customer's monthly bill.\n- FeaturesUsed: Number of premium features the customer uses.\n- SupportTickets: Number of support tickets filed.\n- Churn: 1 if the customer left, 0 otherwise.`, samplePrompt: `Which features are the strongest predictors of customer churn? Show a feature importance plot.` },
  { title: "Campaign Performance", filename: "campaign_performance.csv", description: "Optimize marketing spend and conversion rates.", schemaDescription: `Marketing campaign performance data.\n- Date: Day of the campaign activity.\n- CampaignID: Identifier for the campaign (A, B, C).\n- Impressions, Clicks, Spend, Conversions: Key performance metrics.`, samplePrompt: `What is the return on ad spend (ROAS) for each campaign? Calculate ROAS as (Conversions * 50) / Spend.` },
  { title: "Retail Sales", filename: "retail_sales.csv", description: "In-depth transactional data for sales analysis.", schemaDescription: `Transactional sales data for an e-commerce store.\n- Date: The date of the transaction.\n- SKU, ProductName, Category: Product details.\n- Cost: The cost of the product.\n- Sales: The final sale price.\n- Profit: The profit from the sale.\n- Promotion: Any promotion applied to the sale.\n- Weather: Weather on the day of the sale.\n- Holiday: 1 if the date was a major holiday.`, samplePrompt: `What is the correlation between weather and sales of hockey sticks? Plot the results.` },
  { title: "Predictive CLTV", filename: "cltv_data.csv", description: "Forecast Customer Lifetime Value from transactions.", schemaDescription: `Customer transaction history.\n- CustomerID: Unique customer identifier.\n- TransactionDate: The date of the purchase.\n- TransactionValue: The value of the purchase.`, samplePrompt: `Calculate the average lifetime value of a customer based on this transaction history. Assume a lifespan of 12 months.` },
  { title: "Product Recommendations", filename: "product_recommendations.csv", description: "Understand product ratings and categories.", schemaDescription: `Customer ratings for various products.\n- UserID, ProductID: Identifiers.\n- Category: The product category.\n- Rating: 1 to 5 star rating given by the user.`, samplePrompt: `What are the top 3 rated products in the Electronics category?` },
  { title: "Customer Behavior", filename: "customer_behavior.csv", description: "Analyze on-site user actions and conversion.", schemaDescription: `User session data from a website.\n- SessionID: Unique session identifier.\n- PagesViewed, TimeOnSiteMinutes: Engagement metrics.\n- Device: Mobile or Desktop.\n- Converted: 1 if the session resulted in a purchase.`, samplePrompt: `Is there a difference in conversion rate between Mobile and Desktop users? Frame the analysis as a report for the PuckPro marketing team.` },
];

function ForecastPage() {
  const [selectedDataset, setSelectedDataset] = useState(null);
  const [dataPreview, setDataPreview] = useState(null);
  const [prompt, setPrompt] = useState('');
  const [isLoading, setIsLoading] = useState(false);
  const [analysisResult, setAnalysisResult] = useState(null);
  const [modelType, setModelType] = useState('standard');
  const [revenueTarget, setRevenueTarget] = useState('');
  
  const [followUpInput, setFollowUpInput] = useState('');
  const [followUpHistory, setFollowUpHistory] = useState([]);
  const [isFollowUpLoading, setIsFollowUpLoading] = useState(false);
  const followUpEndRef = useRef(null);

  useEffect(() => {
    if (followUpEndRef.current) {
      followUpEndRef.current.scrollIntoView({ behavior: 'smooth' });
    }
  }, [followUpHistory, isFollowUpLoading]);

  useEffect(() => {
    if (selectedDataset) {
      setDataPreview(null);
      fetch(`${API_BASE_URL}/preview/${selectedDataset.filename}`)
        .then(res => res.json())
        .then(data => setDataPreview(data))
        .catch(err => console.error("Failed to fetch data preview:", err));
    }
  }, [selectedDataset]);

  const handleDatasetSelect = (dataset) => {
    setSelectedDataset(dataset);
    setAnalysisResult(null);
    setFollowUpHistory([]);
    setPrompt('');
    setRevenueTarget('');
    setModelType('standard');
  };

  const handleAnalysis = async () => {
    if (!selectedDataset || !prompt.trim()) return;
    setIsLoading(true);
    setAnalysisResult(null);
    setFollowUpHistory([]);

    const formData = new FormData();
    formData.append('dataset_filename', selectedDataset.filename);
    formData.append('prompt', prompt);
    formData.append('model_type', modelType);
    formData.append('revenue_target', revenueTarget || '0');

    try {
      const response = await fetch(`${API_BASE_URL}/analyze`, { method: 'POST', body: formData });
      if (!response.ok) { const err = await response.json(); throw new Error(err.detail); }
      const data = await response.json();
      setAnalysisResult(data);
    } catch (error) {
      setAnalysisResult({ error: error.message });
    } finally {
      setIsLoading(false);
    }
  };

  const handleFollowUpSubmit = async (e) => {
    e.preventDefault();
    if (!followUpInput.trim()) return;
    const newHistory = [...followUpHistory, { sender: 'user', text: followUpInput }];
    setFollowUpHistory(newHistory);
    setIsFollowUpLoading(true);
    setFollowUpInput('');
    const formData = new FormData();
    formData.append('dataset_filename', selectedDataset.filename);
    formData.append('original_prompt', prompt);
    formData.append('follow_up_history', JSON.stringify(followUpHistory));
    formData.append('follow_up_prompt', followUpInput);
    try {
      const response = await fetch(`${API_BASE_URL}/follow-up`, { method: 'POST', body: formData });
      if (!response.ok) { const err = await response.json(); throw new Error(err.detail); }
      const data = await response.json();
      const agentResponse = { sender: 'agent', summary: data.summary, visualization: data.visualization };
      setFollowUpHistory([...newHistory, agentResponse]);
    } catch (error) {
       setFollowUpHistory([...newHistory, { sender: 'agent', summary: `Error: ${error.message}` }]);
    } finally {
      setIsFollowUpLoading(false);
    }
  };

  return (
    <Box sx={{ padding: { xs: 2, sm: 4 }, color: 'white' }}>
      <Typography variant="h4" component="h1" gutterBottom>Data Science Agent</Typography>
      <Paper sx={{ p: { xs: 2, sm: 3 }, backgroundColor: '#1E1E1E', color: 'white' }}>
        
        <Typography variant="h6" component="h2" gutterBottom>1. Select a Dataset</Typography>
        <Grid container spacing={2}>
          {datasets.map((ds) => (<Grid item key={ds.filename} xs={12} md={6}><Paper variant="outlined" onClick={() => handleDatasetSelect(ds)} sx={{ p: 2, cursor: 'pointer', height: '100%', borderColor: selectedDataset?.filename === ds.filename ? 'primary.main' : 'rgba(255,255,255,0.23)', transform: selectedDataset?.filename === ds.filename ? 'scale(1.03)' : 'scale(1)', transition: 'all 0.2s ease-in-out', backgroundColor: selectedDataset?.filename === ds.filename ? '#2a2a2a' : 'transparent', }}><Typography variant="subtitle1" fontWeight="bold">{ds.title}</Typography><Typography variant="body2" color="text.secondary">{ds.description}</Typography></Paper></Grid>))}
        </Grid>

        {selectedDataset && (
          <>
            <Paper sx={{ mt: 4, p: 2, backgroundColor: '#2a2a2a', border: '1px solid rgba(255,255,255,0.23)' }}>
              <Typography variant="subtitle1" fontWeight="bold">Dataset Details: {selectedDataset.title}</Typography>
              <Typography variant="body2" sx={{ whiteSpace: 'pre-wrap', mt: 1, color: 'text.secondary' }}>
                {selectedDataset.schemaDescription}
              </Typography>
              <DataPreview data={dataPreview} />
            </Paper>

            {selectedDataset.filename.includes('mmm_advanced') && (
                <Box sx={{mt: 4}}>
                    <Typography variant="h6" component="h2" gutterBottom>2. Choose Analysis Type</Typography>
                    <ToggleButtonGroup color="primary" value={modelType} exclusive onChange={(e, newType) => { if (newType) setModelType(newType); }} aria-label="Analysis Type">
                        <ToggleButton value="standard">Standard Report</ToggleButton>
                        <ToggleButton value="bayesian">Advanced Bayesian Model</ToggleButton>
                    </ToggleButtonGroup>
                </Box>
            )}

            <Box sx={{ mt: 4 }}>
              <Box sx={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
                <Typography variant="h6" component="h2" gutterBottom>{selectedDataset.filename.includes('mmm_advanced') ? '3. ' : '2. '}Ask a Question</Typography>
                <Button variant="text" size="small" onClick={() => setPrompt(selectedDataset.samplePrompt)}>Try a sample prompt</Button>
              </Box>

              {modelType === 'bayesian' && selectedDataset.filename.includes('mmm_advanced') && (
                  <TextField label="Next Quarter's Revenue Target ($)" type="number" variant="outlined" fullWidth margin="normal" value={revenueTarget} onChange={(e) => setRevenueTarget(e.target.value)} />
              )}

              <TextField label="What would you like to know about this data?" variant="outlined" fullWidth multiline rows={4} margin="normal" value={prompt} onChange={(e) => setPrompt(e.target.value)} disabled={isLoading} />
              <Button variant="contained" color="primary" onClick={handleAnalysis} disabled={!prompt.trim() || isLoading}>{isLoading ? 'Analyzing...' : 'Run Analysis'}</Button>
            </Box>
          </>
        )}

        <Box sx={{ marginTop: 4 }}>
          <Typography variant="h6" component="h3">Results</Typography>
          {isLoading && !isFollowUpLoading ? (<Box sx={{ display: 'flex', justifyContent: 'center', alignItems: 'center', height: '100px' }}><CircularProgress /></Box>) : (analysisResult && <AnalysisReport result={analysisResult} />)}
          
          {analysisResult && !analysisResult.error && (
            <Paper sx={{ p: 2, mt: 4, backgroundColor: '#2a2a2a', border: '1px solid rgba(255,255,255,0.23)' }}>
              <Typography variant="h6" gutterBottom><QuestionAnswerIcon sx={{verticalAlign: 'middle', mr: 1}}/>Follow-up Questions</Typography>
              <Box sx={{ mt: 2, maxHeight: '400px', overflowY: 'auto', p: 1 }}>
                {followUpHistory.map((msg, index) => (
                  <Box key={index} className={`message-bubble ${msg.sender === 'user' ? 'user' : 'agent'}`}>
                    {msg.sender === 'agent' ? (
                      <>
                        <ReactMarkdown remarkPlugins={[remarkGfm]}>{msg.summary}</ReactMarkdown>
                        {msg.visualization && <img src={msg.visualization} alt="Follow-up Plot" style={{maxWidth: '100%', borderRadius: '8px', marginTop: '1rem', padding: '10px' }} />}
                      </>
                    ) : (<Typography variant="body1">{msg.text}</Typography>)}
                  </Box>
                ))}
                {isFollowUpLoading && <Box className="message-bubble agent"><Typography className="typing-indicator">...</Typography></Box>}
                <div ref={followUpEndRef} />
              </Box>
              <Box component="form" onSubmit={handleFollowUpSubmit} className="message-form-container" sx={{mt: 2, p:0}}>
                <TextField fullWidth variant="outlined" placeholder="Ask a follow-up question..." value={followUpInput} onChange={(e) => setFollowUpInput(e.target.value)} autoComplete="off" />
                <Button type="submit" variant="contained">Send</Button>
              </Box>
            </Paper>
          )}
        </Box>
      </Paper>
    </Box>
  );
}

export default ForecastPage;