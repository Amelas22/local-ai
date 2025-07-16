import React, { useState, useEffect, useRef } from 'react';
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
  Tabs,
  Tab,
} from '@mui/material';
import { useNavigate } from 'react-router-dom';
import { DiscoveryUpload } from '../components/discovery/DiscoveryUpload';
import { FactReviewPanel } from '../components/discovery/FactReviewPanel';
import { DeficiencyReportViewer } from '../components/discovery/DeficiencyReportViewer';
import ProcessingVisualization from '../components/discovery/ProcessingVisualization';
import { useCaseManagement } from '../hooks/useCaseManagement';
import { useDiscoverySocket } from '../hooks/useDiscoverySocket';
import { useAppSelector, useAppDispatch } from '../hooks/redux';
import { startDeficiencyAnalysis, fetchDeficiencyReport } from '../store/slices/deficiencySlice';
import { DeficiencyAnalysisRequest } from '../types/discovery.types';

const steps = [
  'Upload Documents',
  'Processing',
  'Review Facts',
];

const DiscoveryProcessing: React.FC = () => {
  const [activeStep, setActiveStep] = useState(0);
  const [processingId, setProcessingId] = useState<string | null>(null);
  const [productionBatch, setProductionBatch] = useState<string | null>(null);
  const [uploadedFiles, setUploadedFiles] = useState<{
    rfpFileId?: string;
    defenseResponseFileId?: string;
  }>({});
  const [activeTab, setActiveTab] = useState(0);
  const navigate = useNavigate();
  const dispatch = useAppDispatch();
  const hasTriggeredAnalysis = useRef(false);
  
  const { selectedCase } = useCaseManagement();
  const { isProcessing, currentStage, extractedFacts } = useAppSelector(state => state.discovery);
  const { currentReport, analysisInProgress, loading: deficiencyLoading } = useAppSelector(state => state.deficiency);
  
  const triggerDeficiencyAnalysis = async () => {
    if (!selectedCase || !productionBatch || !processingId || hasTriggeredAnalysis.current) return;
    
    hasTriggeredAnalysis.current = true;
    
    const request: DeficiencyAnalysisRequest = {
      rfp_document_id: uploadedFiles.rfpFileId || '',
      defense_response_id: uploadedFiles.defenseResponseFileId,
      production_batch: productionBatch,
      processing_id: processingId,
    };
    
    try {
      const result = await dispatch(startDeficiencyAnalysis(request)).unwrap();
      // Store the analysis ID for later retrieval
      if (result.analysis_id) {
        localStorage.setItem(`deficiency_analysis_${selectedCase.case_name}_${productionBatch}`, result.analysis_id);
      }
    } catch (error) {
      console.error('Failed to start deficiency analysis:', error);
    }
  };
  
  const handleFilesUploaded = (files: { rfpFileId?: string; defenseResponseFileId?: string; productionBatch: string }) => {
    setUploadedFiles({ rfpFileId: files.rfpFileId, defenseResponseFileId: files.defenseResponseFileId });
    setProductionBatch(files.productionBatch);
  };
  
  const { isConnected } = useDiscoverySocket({
    processingId: processingId || undefined,
    caseId: selectedCase?.case_name,
    onProcessingComplete: () => {
      setActiveStep(2);
      triggerDeficiencyAnalysis();
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
  
  useEffect(() => {
    // Fetch deficiency report when analysis completes
    if (!analysisInProgress && currentReport === null && activeTab === 1) {
      // Check if there's a recent analysis we should fetch
      const storedAnalysisId = localStorage.getItem(`deficiency_analysis_${selectedCase?.case_name}_${productionBatch}`);
      if (storedAnalysisId) {
        dispatch(fetchDeficiencyReport(storedAnalysisId));
      }
    }
  }, [analysisInProgress, currentReport, activeTab, selectedCase, productionBatch, dispatch]);

  const handleUploadComplete = (newProcessingId: string, uploadInfo?: any) => {
    setProcessingId(newProcessingId);
    if (uploadInfo) {
      handleFilesUploaded(uploadInfo);
    }
    setActiveStep(1);
  };

  const handleReset = () => {
    setActiveStep(0);
    setProcessingId(null);
    setProductionBatch(null);
    setUploadedFiles({});
    setActiveTab(0);
    hasTriggeredAnalysis.current = false;
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
            <Tabs value={activeTab} onChange={(_, newValue) => setActiveTab(newValue)} sx={{ mb: 3 }}>
              <Tab label="Facts Review" />
              <Tab label="Deficiency Report" disabled={!currentReport && !analysisInProgress} />
            </Tabs>
            
            {activeTab === 0 ? (
              <>
                <FactReviewPanel />
                {analysisInProgress && (
                  <Alert severity="info" sx={{ mt: 2 }}>
                    Deficiency analysis is running in the background. The report will be available soon.
                  </Alert>
                )}
              </>
            ) : (
              <>
                {deficiencyLoading ? (
                  <Box sx={{ textAlign: 'center', py: 4 }}>
                    <Typography>Loading deficiency report...</Typography>
                  </Box>
                ) : currentReport ? (
                  <DeficiencyReportViewer report={currentReport} />
                ) : (
                  <Alert severity="info">
                    No deficiency report available yet. The analysis may still be in progress.
                  </Alert>
                )}
              </>
            )}
            
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