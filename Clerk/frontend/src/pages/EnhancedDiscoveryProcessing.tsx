import React, { useState, useEffect } from 'react';
import {
  Box,
  Paper,
  Typography,
  Stepper,
  Step,
  StepLabel,
  Container,
  Alert,
  Button,
  Fade,
} from '@mui/material';
import { useNavigate } from 'react-router-dom';
import { DiscoveryUpload } from '../components/discovery/DiscoveryUpload';
import { EnhancedFactReviewPanel } from '../components/discovery/EnhancedFactReviewPanel';
import ProcessingVisualization from '../components/discovery/ProcessingVisualization';
import { useCaseManagement } from '../hooks/useCaseManagement';
import { useEnhancedDiscoverySocket } from '../hooks/useEnhancedDiscoverySocket';
import { useAppSelector } from '../hooks/redux';

const steps = [
  'Upload Documents',
  'Processing & Review',
];

const EnhancedDiscoveryProcessing: React.FC = () => {
  const [activeStep, setActiveStep] = useState(0);
  const [processingId, setProcessingId] = useState<string | null>(null);
  const [showVisualization, setShowVisualization] = useState(true);
  const navigate = useNavigate();
  
  const { selectedCase } = useCaseManagement();
  const { 
    isProcessing, 
    extractedFacts,
    stats 
  } = useAppSelector(state => state.discovery);
  
  const { isConnected } = useEnhancedDiscoverySocket({
    processingId: processingId || undefined,
    caseId: selectedCase?.case_name,
    onProcessingComplete: () => {
      // Don't automatically switch steps, let user continue viewing
      setShowVisualization(false);
    },
    onError: (error) => {
      console.error('Processing error:', error);
    },
  });

  useEffect(() => {
    if (!selectedCase) {
      navigate('/cases');
    }
  }, [selectedCase, navigate]);

  const handleUploadComplete = (newProcessingId: string) => {
    setProcessingId(newProcessingId);
    setActiveStep(1);
    setShowVisualization(true);
  };

  const handleReset = () => {
    setActiveStep(0);
    setProcessingId(null);
    setShowVisualization(true);
  };

  const renderStepContent = () => {
    switch (activeStep) {
      case 0:
        return (
          <Box sx={{ mt: 4 }}>
            <DiscoveryUpload onUploadComplete={handleUploadComplete} />
          </Box>
        );
      
      case 1:
        return (
          <Box sx={{ mt: 4 }}>
            {/* Show both visualization and fact review simultaneously */}
            {isProcessing && showVisualization && (
              <Fade in={isProcessing}>
                <Box sx={{ mb: 4 }}>
                  <ProcessingVisualization />
                  <Box sx={{ mt: 2, textAlign: 'center' }}>
                    <Button
                      variant="outlined"
                      onClick={() => setShowVisualization(false)}
                      size="small"
                    >
                      Hide Visualization
                    </Button>
                  </Box>
                </Box>
              </Fade>
            )}
            
            {/* Always show the enhanced fact review panel during processing */}
            <EnhancedFactReviewPanel />
            
            {/* Show option to process more documents when complete */}
            {!isProcessing && extractedFacts.length > 0 && (
              <Box sx={{ mt: 2, textAlign: 'right' }}>
                <Button
                  variant="outlined"
                  onClick={handleReset}
                >
                  Process More Documents
                </Button>
              </Box>
            )}
          </Box>
        );
      
      default:
        return null;
    }
  };

  if (!selectedCase) {
    return (
      <Container maxWidth="lg" sx={{ mt: 4 }}>
        <Alert severity="warning">
          Please select a case before processing discovery documents.
        </Alert>
      </Container>
    );
  }

  if (!isConnected) {
    return (
      <Container maxWidth="lg" sx={{ mt: 4 }}>
        <Alert severity="info">
          Connecting to server... Please wait.
        </Alert>
      </Container>
    );
  }

  return (
    <Container maxWidth="xl" sx={{ py: 4 }}>
      <Paper sx={{ p: 3, mb: 3 }}>
        <Typography variant="h4" gutterBottom>
          Discovery Document Processing
        </Typography>
        
        <Typography variant="body1" color="text.secondary" paragraph>
          Case: <strong>{selectedCase.display_name || selectedCase.case_name}</strong>
        </Typography>

        <Stepper activeStep={activeStep} sx={{ mb: 4 }}>
          {steps.map((label) => (
            <Step key={label}>
              <StepLabel>{label}</StepLabel>
            </Step>
          ))}
        </Stepper>

        {/* Processing Summary */}
        {activeStep === 1 && (
          <Box sx={{ display: 'flex', gap: 2, flexWrap: 'wrap' }}>
            <Typography variant="body2" color="text.secondary">
              Documents Found: <strong>{stats.documentsFound}</strong>
            </Typography>
            <Typography variant="body2" color="text.secondary">
              Documents Processed: <strong>{stats.documentsProcessed}</strong>
            </Typography>
            <Typography variant="body2" color="text.secondary">
              Facts Extracted: <strong>{extractedFacts.length}</strong>
            </Typography>
            {stats.errors > 0 && (
              <Typography variant="body2" color="error">
                Errors: <strong>{stats.errors}</strong>
              </Typography>
            )}
          </Box>
        )}
      </Paper>

      {renderStepContent()}
    </Container>
  );
};

export default EnhancedDiscoveryProcessing;