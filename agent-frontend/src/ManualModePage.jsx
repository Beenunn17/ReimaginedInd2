import React, { useState } from 'react';
import {
    Box, Button, Typography, Paper, Grid, TextField, CircularProgress,
    ToggleButtonGroup, ToggleButton, Card, CardMedia, FormControl,
    InputLabel, Select, MenuItem, IconButton
} from '@mui/material';
import AddPhotoAlternateIcon from '@mui/icons-material/AddPhotoAlternate';
import ClearIcon from '@mui/icons-material/Clear';

// DEFINE THE API BASE URL AT THE TOP
const API_BASE_URL = import.meta.env.VITE_API_BASE_URL || 'http://127.0.0.1:8000';

// Helper component for dropdowns
const PromptSelect = ({ label, value, onChange, options }) => (
    <FormControl fullWidth margin="normal">
        <InputLabel>{label}</InputLabel>
        <Select value={value} label={label} onChange={onChange}>
            {options.map((option) => (
                <MenuItem key={option} value={option}>{option}</MenuItem>
            ))}
        </Select>
    </FormControl>
);

// Helper function to resize images
const resizeImage = (file, callback) => {
    const MAX_WIDTH = 1024;
    const MAX_HEIGHT = 1024;
    const reader = new FileReader();
    reader.onload = (event) => {
        const img = new Image();
        img.onload = () => {
            let width = img.width;
            let height = img.height;

            if (width > height) {
                if (width > MAX_WIDTH) {
                    height *= MAX_WIDTH / width;
                    width = MAX_WIDTH;
                }
            } else {
                if (height > MAX_HEIGHT) {
                    width *= MAX_HEIGHT / height;
                    height = MAX_HEIGHT;
                }
            }

            const canvas = document.createElement('canvas');
            canvas.width = width;
            canvas.height = height;
            const ctx = canvas.getContext('2d');
            ctx.drawImage(img, 0, 0, width, height);
            
            callback(canvas.toDataURL('image/jpeg', 0.9));
        };
        img.src = event.target.result;
    };
    reader.readAsDataURL(file);
};


// Reusable Image Upload Component
const ImageUpload = ({ title, image, setImage }) => {
    const handleFileChange = (event) => {
        const file = event.target.files[0];
        if (file) {
            resizeImage(file, (resizedDataUrl) => {
                setImage(resizedDataUrl);
            });
        }
    };

    return (
        <Box sx={{ mt: 2 }}>
            <Typography variant="subtitle1" gutterBottom>{title}</Typography>
            <Paper
                variant="outlined"
                sx={{
                    p: 2,
                    border: '2px dashed',
                    borderColor: 'grey.700',
                    height: 180,
                    display: 'flex',
                    alignItems: 'center',
                    justifyContent: 'center',
                    flexDirection: 'column',
                    position: 'relative',
                    backgroundImage: image ? `url(${image})` : 'none',
                    backgroundSize: 'contain',
                    backgroundPosition: 'center',
                    backgroundRepeat: 'no-repeat'
                }}
            >
                {!image && (
                    <IconButton component="label">
                        <AddPhotoAlternateIcon sx={{ fontSize: 40 }} />
                        <input type="file" hidden accept="image/*" onChange={handleFileChange} />
                    </IconButton>
                )}
                {image && (
                    <IconButton
                        onClick={() => setImage(null)}
                        sx={{ position: 'absolute', top: 8, right: 8, backgroundColor: 'rgba(0,0,0,0.5)' }}
                    >
                        <ClearIcon />
                    </IconButton>
                )}
            </Paper>
        </Box>
    );
};


function CreativePage() {
    const [promptOptions, setPromptOptions] = useState({
        imageType: 'Product Photo',
        style: 'Photorealistic',
        camera: '85mm',
        lighting: 'Studio Lighting',
        composition: 'Centered',
        modifiers: 'Ultra detailed',
        negativePrompt: 'Low quality, blurry, watermark'
    });
    const [customSubject, setCustomSubject] = useState('A luxury, sustainable coffee brand with notes of chocolate and citrus.');
    const [sceneDescription, setSceneDescription] = useState('A minimalist cafe with clean, bright lighting.');
    const [platform, setPlatform] = useState('meta');
    const [isLoading, setIsLoading] = useState(false);
    const [imageUrls, setImageUrls] = useState([]);
    const [subjectImage, setSubjectImage] = useState(null);
    const [sceneImage, setSceneImage] = useState(null);

    const handleOptionChange = (key) => (event) => {
        setPromptOptions(prev => ({ ...prev, [key]: event.target.value }));
    };

    const handleGenerate = async () => {
        setIsLoading(true);
        setImageUrls([]);
        const formData = new FormData();
        
        for (const [key, value] of Object.entries(promptOptions)) {
            formData.append(key, value);
        }
        formData.append('customSubject', customSubject);
        formData.append('sceneDescription', sceneDescription);
        formData.append('platform', platform);
        
        if (subjectImage) formData.append('subjectImage', subjectImage);
        if (sceneImage) formData.append('sceneImage', sceneImage);

        try {
            // UPDATED THE FETCH URL to use the environment variable and correct endpoint
            const response = await fetch(`${API_BASE_URL}/generate-creative`, {
                method: 'POST',
                body: formData,
            });
            if (!response.ok) {
                const err = await response.json();
                throw new Error(err.detail || 'Failed to generate creative.');
            }
            const data = await response.json();
            setImageUrls(data.image_urls);
        } catch (error) {
            alert(error.message);
        } finally {
            setIsLoading(false);
        }
    };

    return (
        <Box sx={{ padding: { xs: 2, sm: 4 } }}>
            <Typography variant="h4" component="h1" gutterBottom>Creative Generation Agent</Typography>
            <Paper sx={{ p: { xs: 2, sm: 3 } }}>
                <Grid container spacing={4}>
                    <Grid item xs={12} md={5} lg={4}>
                        <Typography variant="h6" component="h2" gutterBottom>1. Build Your Prompt</Typography>
                        
                        <ImageUpload title="Subject Image (Optional)" image={subjectImage} setImage={setSubjectImage} />
                        <TextField label="Subject Description" fullWidth multiline rows={2} margin="normal" value={customSubject} onChange={(e) => setCustomSubject(e.target.value)} />

                        <ImageUpload title="Scene Image (Optional)" image={sceneImage} setImage={setSceneImage} />
                        <TextField label="Scene Description" fullWidth multiline rows={2} margin="normal" value={sceneDescription} onChange={(e) => setSceneDescription(e.target.value)} />

                        <Grid container spacing={2}>
                            <Grid item xs={6}><PromptSelect label="Image Type" value={promptOptions.imageType} onChange={handleOptionChange('imageType')} options={['Product Photo', 'Portrait', 'Landscape', 'Still Life', 'Editorial / Fashion']} /></Grid>
                            <Grid item xs={6}><PromptSelect label="Style" value={promptOptions.style} onChange={handleOptionChange('style')} options={['Photorealistic', '3D Render', 'Film Photography', 'Minimalist', 'Cyberpunk']} /></Grid>
                            <Grid item xs={6}><PromptSelect label="Camera Details" value={promptOptions.camera} onChange={handleOptionChange('camera')} options={['85mm', '35mm', 'Close-up', 'Wide angle', 'Macro']} /></Grid>
                            <Grid item xs={6}><PromptSelect label="Lighting" value={promptOptions.lighting} onChange={handleOptionChange('lighting')} options={['Studio Lighting', 'Natural sunlight', 'Golden hour', 'Moody / Low-key', 'Backlit']} /></Grid>
                            <Grid item xs={6}><PromptSelect label="Composition" value={promptOptions.composition} onChange={handleOptionChange('composition')} options={['Centered', 'Rule of thirds', 'Symmetrical', 'Flat lay']} /></Grid>
                            <Grid item xs={6}><PromptSelect label="Modifiers" value={promptOptions.modifiers} onChange={handleOptionChange('modifiers')} options={['Ultra detailed', 'Cinematic', 'Sharp focus', 'Soft focus', 'Vintage']} /></Grid>
                        </Grid>

                        <TextField label="Negative Prompt" fullWidth margin="normal" value={promptOptions.negativePrompt} onChange={handleOptionChange('negativePrompt')} />

                        <Typography variant="subtitle2" sx={{ mt: 2, mb: 1 }}>Platform</Typography>
                        <ToggleButtonGroup value={platform} exclusive fullWidth onChange={(e, newPlatform) => { if (newPlatform) setPlatform(newPlatform); }}>
                            <ToggleButton value="meta">Meta (1:1)</ToggleButton>
                            <ToggleButton value="tiktok">TikTok (9:16)</ToggleButton>
                        </ToggleButtonGroup>
                        <Button variant="contained" fullWidth sx={{ mt: 3, py: 1.5 }} onClick={handleGenerate} disabled={isLoading}>
                            {isLoading ? 'Generating...' : 'Generate Creative'}
                        </Button>
                    </Grid>
                    <Grid item xs={12} md={7} lg={8}>
                        <Typography variant="h6" component="h2" gutterBottom>2. Generated Asset</Typography>
                        <Paper variant="outlined" sx={{ display: 'flex', alignItems: 'center', justifyContent: 'center', height: {xs: 'auto', md: 'calc(100% - 48px)'}, backgroundColor: 'background.default', p: 2 }}>
                            {isLoading && <CircularProgress />}
                            {!isLoading && imageUrls.length > 0 && (
                                <Grid container spacing={2}>
                                    {imageUrls.map((url, index) => (
                                        <Grid item xs={6} key={index}>
                                            <Card sx={{ width: '100%', height: '100%', bgcolor: 'transparent' }} elevation={0}>
                                                <CardMedia component="img" image={url} alt={`Generated Creative ${index + 1}`} sx={{ objectFit: 'contain', width: '100%', height: '100%' }} />
                                            </Card>
                                        </Grid>
                                    ))}
                                </Grid>
                            )}
                        </Paper>
                    </Grid>
                </Grid>
            </Paper>
        </Box>
    );
}

export default CreativePage;