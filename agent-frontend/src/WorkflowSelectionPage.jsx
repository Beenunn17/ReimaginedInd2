import React from 'react';
import { Box, Button, Typography, Grid, Paper } from '@mui/material';

function WorkflowSelectionPage({ onSelectFlow }) {
    const workflows = [
        {
            key: 'strategy',
            title: 'Full Strategy & Creative',
            description: 'Work with a Brand Strategist to analyze your brand, define creative approaches, and then generate assets with a Creative Director.'
        },
        {
            key: 'creative',
            title: 'Creative Director Only',
            description: 'You provide a creative brief directly to the Creative Director agent to generate a series of visual assets.'
        },
        {
            key: 'manual',
            title: 'Manual Mode',
            description: 'The original tool. Manually control all prompt parameters to generate images for quick, specific tasks.'
        }
    ];

    return (
        <Box sx={{ textAlign: 'center' }}>
            <Typography variant="h3" component="h1" gutterBottom>
                Welcome to the Generative Marketing Suite
            </Typography>
            <Typography variant="h6" color="text.secondary" sx={{ mb: 6 }}>
                Choose a workflow to get started.
            </Typography>
            <Grid container spacing={4} justifyContent="center">
                {workflows.map((flow) => (
                    <Grid item xs={12} md={4} key={flow.key}>
                        <Paper sx={{ p: 4, height: '100%', display: 'flex', flexDirection: 'column', justifyContent: 'space-between' }}>
                            <Box>
                                <Typography variant="h5" component="h2" gutterBottom>{flow.title}</Typography>
                                <Typography variant="body1" color="text.secondary">{flow.description}</Typography>
                            </Box>
                            <Button
                                variant="contained"
                                onClick={() => onSelectFlow(flow.key)}
                                sx={{ mt: 3 }}
                            >
                                Start Here
                            </Button>
                        </Paper>
                    </Grid>
                ))}
            </Grid>
        </Box>
    );
}

export default WorkflowSelectionPage;