import React, { useMemo } from 'react';
import {
  Box,
  Paper,
  Typography,
  CircularProgress,
  LinearProgress,
  Chip,
  Alert,
  Grid,
  Stack,
  Divider,
} from '@mui/material';
import {
  CheckCircle as CheckCircleIcon,
  Error as ErrorIcon,
  Timer as TimerIcon,
  Description as DocumentIcon,
} from '@mui/icons-material';
import { FactCard } from './FactCard';
import { ProcessingDocument, ExtractedFactWithSource, ProcessingStage } from '../../types/discovery.types';

interface DocumentProcessingTabProps {
  document: ProcessingDocument;
  facts: ExtractedFactWithSource[];
  currentStage: ProcessingStage | null;
  onFactSelect: (fact: ExtractedFactWithSource) => void;
  onFactUpdate: (fact: ExtractedFactWithSource, newContent: string, reason?: string) => void;
  onFactDelete: (fact: ExtractedFactWithSource) => void;
  viewMode: 'grid' | 'list';
  selectedFact: ExtractedFactWithSource | null;
}

export const DocumentProcessingTab: React.FC<DocumentProcessingTabProps> = ({
  document,
  facts,
  currentStage,
  onFactSelect,
  onFactUpdate,
  onFactDelete,
  viewMode,
  selectedFact,
}) => {
  const documentFacts = useMemo(() => 
    facts.filter(f => f.source.doc_id === document.id),
    [facts, document.id]
  );

  const getProcessingStageInfo = () => {
    if (document.status === 'completed') {
      return {
        label: 'Completed',
        color: 'success' as const,
        icon: <CheckCircleIcon />,
        progress: 100,
      };
    }
    
    if (document.status === 'error') {
      return {
        label: 'Error',
        color: 'error' as const,
        icon: <ErrorIcon />,
        progress: 0,
      };
    }
    
    // Document is processing
    const stages = [
      ProcessingStage.DISCOVERING_DOCUMENTS,
      ProcessingStage.CLASSIFYING_DOCUMENTS,
      ProcessingStage.CHUNKING_DOCUMENTS,
      ProcessingStage.GENERATING_EMBEDDINGS,
      ProcessingStage.STORING_VECTORS,
      ProcessingStage.EXTRACTING_FACTS,
    ];
    
    const currentIndex = stages.indexOf(currentStage || ProcessingStage.DISCOVERING_DOCUMENTS);
    const progress = ((currentIndex + 1) / stages.length) * 100;
    
    return {
      label: currentStage?.replace(/_/g, ' ').toLowerCase() || 'Processing',
      color: 'primary' as const,
      icon: <TimerIcon />,
      progress,
    };
  };

  const stageInfo = getProcessingStageInfo();

  return (
    <Box sx={{ height: '100%', display: 'flex', flexDirection: 'column' }}>
      {/* Document Header */}
      <Paper sx={{ p: 2, mb: 2 }}>
        <Stack direction="row" alignItems="center" spacing={2}>
          <DocumentIcon color="action" />
          <Box sx={{ flexGrow: 1 }}>
            <Typography variant="h6">{document.title}</Typography>
            <Stack direction="row" spacing={1} alignItems="center">
              <Chip
                label={document.type.replace(/_/g, ' ')}
                size="small"
                color="primary"
              />
              {document.batesRange && (
                <Chip
                  label={`Bates: ${document.batesRange}`}
                  size="small"
                  variant="outlined"
                />
              )}
              <Chip
                label={`Pages: ${document.pageCount || 'Unknown'}`}
                size="small"
                variant="outlined"
              />
              <Chip
                icon={stageInfo.icon}
                label={stageInfo.label}
                color={stageInfo.color}
                size="small"
              />
            </Stack>
          </Box>
          <Box sx={{ minWidth: 120 }}>
            <Typography variant="caption" color="text.secondary" gutterBottom>
              Confidence
            </Typography>
            <LinearProgress
              variant="determinate"
              value={document.confidence * 100}
              sx={{ height: 8, borderRadius: 4 }}
              color={document.confidence > 0.8 ? 'success' : document.confidence > 0.6 ? 'warning' : 'error'}
            />
            <Typography variant="caption" color="text.secondary">
              {Math.round(document.confidence * 100)}%
            </Typography>
          </Box>
        </Stack>
      </Paper>

      {/* Processing Progress */}
      {document.status === 'processing' && (
        <Paper sx={{ p: 2, mb: 2 }}>
          <Typography variant="subtitle2" gutterBottom>
            Processing Progress
          </Typography>
          <LinearProgress
            variant="determinate"
            value={stageInfo.progress}
            sx={{ height: 10, borderRadius: 5, mb: 1 }}
          />
          <Typography variant="caption" color="text.secondary">
            {stageInfo.label} - {Math.round(stageInfo.progress)}% complete
          </Typography>
        </Paper>
      )}

      {/* Error Display */}
      {document.status === 'error' && document.error && (
        <Alert severity="error" sx={{ mb: 2 }}>
          {document.error}
        </Alert>
      )}

      {/* Facts Section */}
      <Box sx={{ flexGrow: 1, overflow: 'auto' }}>
        {document.status === 'processing' && currentStage !== ProcessingStage.EXTRACTING_FACTS ? (
          <Box sx={{ display: 'flex', flexDirection: 'column', alignItems: 'center', p: 4 }}>
            <CircularProgress size={48} />
            <Typography variant="body2" color="text.secondary" sx={{ mt: 2 }}>
              Processing document... Facts will appear here once extraction begins.
            </Typography>
          </Box>
        ) : documentFacts.length === 0 ? (
          <Alert severity="info">
            No facts have been extracted from this document yet.
          </Alert>
        ) : (
          <>
            <Box sx={{ p: 2, bgcolor: 'grey.50' }}>
              <Typography variant="subtitle2" gutterBottom>
                Extracted Facts ({documentFacts.length})
              </Typography>
              <Divider />
            </Box>
            <Grid container spacing={2} sx={{ p: 2 }}>
              {documentFacts.map((fact) => (
                <Grid
                  item
                  xs={12}
                  sm={viewMode === 'grid' ? 6 : 12}
                  lg={viewMode === 'grid' ? 4 : 12}
                  key={fact.id}
                >
                  <FactCard
                    fact={fact}
                    viewMode={viewMode}
                    onSelect={onFactSelect}
                    onUpdate={onFactUpdate}
                    onDelete={onFactDelete}
                    isSelected={selectedFact?.id === fact.id}
                  />
                </Grid>
              ))}
            </Grid>
          </>
        )}
      </Box>

      {/* Real-time Fact Stream */}
      {document.status === 'processing' && currentStage === ProcessingStage.EXTRACTING_FACTS && (
        <Paper sx={{ p: 2, mt: 2, bgcolor: 'primary.50' }}>
          <Stack direction="row" spacing={1} alignItems="center">
            <CircularProgress size={20} />
            <Typography variant="body2">
              Extracting facts from this document...
            </Typography>
          </Stack>
        </Paper>
      )}
    </Box>
  );
};