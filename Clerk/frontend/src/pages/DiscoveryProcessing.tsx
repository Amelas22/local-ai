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
} from '@mui/material';
import { useNavigate } from 'react-router-dom';
import { DiscoveryUpload } from '../components/discovery/DiscoveryUpload';
import { FactReviewPanel } from '../components/discovery/FactReviewPanel';
import ProcessingVisualization from '../components/discovery/ProcessingVisualization';
import { useCaseManagement } from '../hooks/useCaseManagement';
import { useDiscoverySocket } from '../hooks/useDiscoverySocket';
import { useAppSelector } from '../hooks/redux';

const steps = [
  'Upload Documents',
  'Processing',
  'Review Facts',
];

const DiscoveryProcessing: React.FC = () => {
  const [activeStep, setActiveStep] = useState(0);
  const [processingId, setProcessingId] = useState<string | null>(null);
  const navigate = useNavigate();
  
  const { selectedCase } = useCaseManagement();
  const { isProcessing, currentStage, extractedFacts } = useAppSelector(state => state.discovery);
  
  const { isConnected } = useDiscoverySocket({
    processingId: processingId || undefined,
    caseId: selectedCase?.case_name,
    onProcessingComplete: () => {
      setActiveStep(2);
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
  };

  const handleReset = () => {
    setActiveStep(0);
    setProcessingId(null);
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
            <ProcessingVisualization />
            {!isProcessing && extractedFacts.length > 0 && (
              <Box sx={{ mt: 2, textAlign: 'center' }}>
                <Button
                  variant="contained"
                  onClick={() => setActiveStep(2)}
                  size="large"
                >
                  Review {extractedFacts.length} Extracted Facts
                </Button>
              </Box>
            )}
          </Box>
        );
      
      case 2:
        return (
          <Box sx={{ mt: 4 }}>
            <FactReviewPanel />
            <Box sx={{ mt: 2, textAlign: 'right' }}>
              <Button
                variant="outlined"
                onClick={handleReset}
              >
                Process More Documents
              </Button>
            </Box>
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

        {isProcessing && currentStage && (
          <Alert severity="info" sx={{ mb: 2 }}>
            Processing Stage: {currentStage.replace(/_/g, ' ').toLowerCase()}
          </Alert>
        )}
      </Paper>

      {renderStepContent()}
    </Container>
  );
};

export default DiscoveryProcessing;