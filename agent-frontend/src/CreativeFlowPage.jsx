import React, { useState } from 'react';
import {
    Box, Button, Typography, Paper, Grid, CircularProgress,
    Card, CardMedia, Alert, CardContent, Divider
} from '@mui/material';

const API_BASE_URL = import.meta.env.VITE_API_BASE_URL || 'http://127.0.0.1:8000';

function CreativeFlowPage({ brandContext, selectedApproach, onBackToStrategy }) {
    const [isLoadingAssets, setIsLoadingAssets] = useState(false);
    const [generatedAssets, setGeneratedAssets] = useState([]);
    const [assetError, setAssetError] = useState(null);
    
    const [isLoadingCopy, setIsLoadingCopy] = useState(false);
    const [generatedCopy, setGeneratedCopy] = useState([]);
    const [copyError, setCopyError] = useState(null);

    const handleGenerateAssets = async () => {
        setIsLoadingAssets(true);
        setGeneratedAssets([]);
        setAssetError(null);
        setGeneratedCopy([]);
        
        try {
            const payload = { ...brandContext, selectedStrategy: selectedApproach };
            const response = await fetch(`${API_BASE_URL}/generate-assets-from-brief`, {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify(payload)
            });
            if (!response.ok) {
                const err = await response.json();
                throw new Error(err.detail || "Failed to generate assets.");
            }
            const data = await response.json();
            setGeneratedAssets(data.image_urls || []);
        } catch (err) {
            setAssetError(err.message);
        } finally {
            setIsLoadingAssets(false);
        }
    };

    const handleGenerateCopy = async () => {
        setIsLoadingCopy(true);
        setGeneratedCopy([]);
        setCopyError(null);

        try {
            const payload = { ...brandContext, selectedStrategy: selectedApproach };
            const response = await fetch(`${API_BASE_URL}/generate-social-copy`, {
                 method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify(payload)
            });
             if (!response.ok) {
                const err = await response.json();
                throw new Error(err.detail || "Failed to generate copy.");
            }
            const data = await response.json();
            setGeneratedCopy(data.posts || []);
        } catch(err) {
            setCopyError(err.message);
        } finally {
            setIsLoadingCopy(false);
        }
    };

    if (!selectedApproach) {
        return <Alert severity="warning">No creative direction selected. Please go back.</Alert>;
    }

    return (
        <Box>
            <Typography variant="h4" component="h1" gutterBottom>Phase 2: Creative Direction</Typography>
            <Paper sx={{ p: 4 }}>
                <Typography variant="h6">Selected Strategic Direction:</Typography>
                <Card variant="outlined" sx={{ mt: 1, mb: 3, p: 2, bgcolor: 'rgba(255, 255, 255, 0.05)' }}>
                    <Typography variant="h5" gutterBottom>{selectedApproach.Title}</Typography>
                    <Typography color="text.secondary">{selectedApproach['Core Idea']}</Typography>
                </Card>

                <Button variant="contained" size="large" onClick={handleGenerateAssets} disabled={isLoadingAssets} fullWidth sx={{ py: 2 }}>
                    {isLoadingAssets ? <CircularProgress size={24} /> : `1. Generate Creative Assets for "${selectedApproach.Title}"`}
                </Button>

                {assetError && <Alert severity="error" sx={{ mt: 2 }}>{assetError}</Alert>}

                {generatedAssets.length > 0 && (
                     <Box sx={{ mt: 4 }}>
                        <Typography variant="h5" gutterBottom>Generated Assets:</Typography>
                        <Grid container spacing={2}>
                            {generatedAssets.map((url, index) => (
                                <Grid item xs={6} md={3} key={index}>
                                    <Card><CardMedia component="img" image={url} alt={`Generated asset ${index + 1}`} /></Card>
                                </Grid>
                            ))}
                        </Grid>

                        <Divider sx={{ my: 4 }} />
                        <Typography variant="h5" gutterBottom>Social Media Copy</Typography>
                        <Button variant="contained" color="secondary" onClick={handleGenerateCopy} disabled={isLoadingCopy}>
                            {isLoadingCopy ? <CircularProgress size={24} color="inherit" /> : `2. Generate Social Post Copy`}
                        </Button>

                        {copyError && <Alert severity="error" sx={{ mt: 2 }}>{copyError}</Alert>}
                        
                        {generatedCopy.length > 0 && (
                            <Grid container spacing={2} sx={{mt: 2}}>
                                {generatedCopy.map((post, index) => (
                                    <Grid item xs={12} md={4} key={index}>
                                        <Paper variant="outlined" sx={{p: 2, height: '100%'}}>
                                            <Typography variant="subtitle1" fontWeight="bold">{post.Hook}</Typography>
                                            <Typography variant="body2" sx={{my: 1}}>{post.Body}</Typography>
                                            <Typography variant="body2" fontWeight="bold">{post.CTA}</Typography>
                                            
                                            {/* --- THIS IS THE FIX --- */}
                                            {/* It checks if Hashtags exists and is an array before trying to join it */}
                                            {post.Hashtags && Array.isArray(post.Hashtags) && (
                                                <Typography variant="caption" color="text.secondary" sx={{mt: 2, display: 'block'}}>
                                                    {post.Hashtags.join(' ')}
                                                </Typography>
                                            )}
                                        </Paper>
                                    </Grid>
                                ))}
                            </Grid>
                        )}
                    </Box>
                )}
            </Paper>
            <Button sx={{ mt: 2 }} onClick={onBackToStrategy}>&larr; Back to Strategy</Button>
        </Box>
    );
}

export default CreativeFlowPage;