import React, { useState } from 'react';
import {
    Box, Button, Typography, Paper, Grid, TextField, CircularProgress,
    Card, CardContent, Alert, CardActions
} from '@mui/material';

const API_BASE_URL = import.meta.env.VITE_API_BASE_URL || 'http://127.0.0.1:8000';

function StrategistFlowPage({ onStrategySelected }) {
    const [brandName, setBrandName] = useState('Allbirds');
    const [websiteUrl, setWebsiteUrl] = useState('https://www.allbirds.com');
    const [adLibraryUrl, setAdLibraryUrl] = useState('https://www.facebook.com/ads/library/?active_status=all&ad_type=all&country=US&q=Allbirds&search_type=keyword_unordered&media_type=all');
    const [userBrief, setUserBrief] = useState('We are launching a new line of running shoes and want to emphasize their sustainable materials and superior comfort.');

    const [isLoading, setIsLoading] = useState(false);
    const [analysisResult, setAnalysisResult] = useState(null);
    const [error, setError] = useState(null);
    const [rawResponseForDebug, setRawResponseForDebug] = useState(null);

    const handleAnalyze = async () => {
        setIsLoading(true);
        setAnalysisResult(null);
        setError(null);
        setRawResponseForDebug(null);

        const formData = new FormData();
        formData.append('brandName', brandName);
        formData.append('websiteUrl', websiteUrl);
        formData.append('adLibraryUrl', adLibraryUrl);
        formData.append('userBrief', userBrief);

        try {
            const response = await fetch(`${API_BASE_URL}/analyze-brand`, {
                method: 'POST',
                body: formData,
            });
            const data = await response.json();

            if (!response.ok) {
                throw new Error(data.detail || 'An error occurred on the backend.');
            }
            
            try {
                const parsedLlmResponse = JSON.parse(data.llm_response);
                setAnalysisResult({
                    approaches: parsedLlmResponse.approaches || [],
                });
            } catch (e) {
                setRawResponseForDebug(data.llm_response);
                throw new Error("Failed to parse the JSON response from the LLM. See raw output for details.");
            }

        } catch (err) {
            setError(err.message);
        } finally {
            setIsLoading(false);
        }
    };

    const handleSelectApproach = (approach) => {
        const context = { brandName, websiteUrl, adLibraryUrl, userBrief };
        onStrategySelected(approach, context);
    };

    return (
        <Box>
            <Typography variant="h4" component="h1" gutterBottom>Phase 1: Brand Strategy</Typography>
            <Paper sx={{ p: 4 }}>
                <Typography variant="h6" component="h2">Let's build a creative strategy.</Typography>
                <Typography color="text.secondary" sx={{ mb: 3 }}>Provide your brand info and a brief. The strategist agent will analyze it and propose three creative approaches.</Typography>
                <Grid container spacing={2}>
                    <Grid item xs={12}><TextField fullWidth label="Brand Name" value={brandName} onChange={(e) => setBrandName(e.target.value)} /></Grid>
                    <Grid item xs={12}><TextField fullWidth label="Official Website URL" value={websiteUrl} onChange={(e) => setWebsiteUrl(e.target.value)} /></Grid>
                    <Grid item xs={12}><TextField fullWidth label="Meta Ad Library URL (Optional)" value={adLibraryUrl} onChange={(e) => setAdLibraryUrl(e.target.value)} /></Grid>
                    <Grid item xs={12}><TextField fullWidth multiline rows={3} label="What is the ask? (Your Creative Brief)" value={userBrief} onChange={(e) => setUserBrief(e.target.value)} /></Grid>
                    <Grid item xs={12}><Button variant="contained" onClick={handleAnalyze} disabled={isLoading || !brandName || !websiteUrl || !userBrief} sx={{ py: 1.5, px: 4, width: '100%' }}>{isLoading ? <CircularProgress size={24} /> : 'Generate Strategic Approaches'}</Button></Grid>
                </Grid>

                {error && <Alert severity="error" sx={{ mt: 2, mb: 2 }}>{error}</Alert>}
                
                {analysisResult && analysisResult.approaches && analysisResult.approaches.length > 0 && (
                    <Box sx={{ mt: 4 }}>
                        <Typography variant="h5" gutterBottom>Here are three proposed creative approaches:</Typography>
                        <Grid container spacing={3} sx={{ mb: 3 }}>
                            {analysisResult.approaches.map((item, index) => (
                                <Grid item xs={12} md={4} key={index}>
                                    <Card sx={{height: '100%', display: 'flex', flexDirection: 'column', justifyContent: 'space-between'}}>
                                        <CardContent>
                                            {/* --- THIS IS THE FIX: Using Capitalized Keys --- */}
                                            <Typography variant="h6">{item.Title}</Typography>
                                            <Typography variant="subtitle1" color="text.secondary" sx={{my: 1}}>{item['Core Idea']}</Typography>
                                            <Typography variant="body2">{item.Description}</Typography>
                                        </CardContent>
                                        <CardActions>
                                            <Button size="small" variant="contained" onClick={() => handleSelectApproach(item)}>
                                                Select This Direction
                                            </Button>
                                        </CardActions>
                                    </Card>
                                </Grid>
                            ))}
                        </Grid>
                    </Box>
                )}
            </Paper>
        </Box>
    );
}

export default StrategistFlowPage;