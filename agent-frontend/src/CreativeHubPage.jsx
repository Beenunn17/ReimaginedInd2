import React, { useState } from 'react';
import { Box, Button } from '@mui/material';

import WorkflowSelectionPage from './WorkflowSelectionPage';
import StrategistFlowPage from './StrategistFlowPage';
import CreativeFlowPage from './CreativeFlowPage';
import ManualModePage from './ManualModePage';

function CreativeHubPage() {
    const [currentFlow, setCurrentFlow] = useState('selection');
    const [brandContext, setBrandContext] = useState(null); // To hold name, urls, brief
    const [selectedStrategy, setSelectedStrategy] = useState(null);

    const handleStrategySelected = (strategy, context) => {
        setSelectedStrategy(strategy);
        setBrandContext(context);
        setCurrentFlow('creative');
    };

    const handleBackToStrategy = () => {
        setSelectedStrategy(null);
        setCurrentFlow('strategy');
    };
    
    const renderContent = () => {
        switch (currentFlow) {
            case 'strategy':
                return <StrategistFlowPage onStrategySelected={handleStrategySelected} />;
            case 'creative':
                return <CreativeFlowPage brandContext={brandContext} selectedApproach={selectedStrategy} onBackToStrategy={handleBackToStrategy} />;
            case 'manual':
                return <ManualModePage />;
            case 'selection':
            default:
                return <WorkflowSelectionPage onSelectFlow={setCurrentFlow} />;
        }
    };

    return (
        <Box sx={{ p: { xs: 2, sm: 3, md: 4 } }}>
            {currentFlow !== 'selection' && (
                <Button sx={{ mb: 3 }} onClick={() => { setCurrentFlow('selection'); setSelectedStrategy(null); }}>
                    &larr; Back to Main Menu
                </Button>
            )}
            {renderContent()}
        </Box>
    );
}

export default CreativeHubPage;