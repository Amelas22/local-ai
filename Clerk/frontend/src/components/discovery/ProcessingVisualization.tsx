import { Box, Typography, Grid, Paper, LinearProgress, Chip } from '@mui/material';
import { useAppSelector } from '@/hooks/redux';
import DocumentStream from './DocumentStream';
import ProcessingStats from './ProcessingStats';
import ChunkingAnimation from './ChunkingAnimation';
import { ProcessingStage } from '@/types/discovery.types';

const ProcessingVisualization = () => {
  const { 
    isProcessing, 
    currentStage, 
    stats, 
    processingStartTime,
    currentChunkingDocument
  } = useAppSelector(
    (state) => state.discovery
  );

  if (!isProcessing && !processingStartTime) {
    return (
      <Box sx={{ textAlign: 'center', py: 4 }}>
        <Typography color="text.secondary">
          No active processing. Start a new discovery processing job to see visualizations.
        </Typography>
      </Box>
    );
  }

  const getStageProgress = () => {
    const stages = [
      'initializing',
      'discovering_documents',
      'classifying_documents',
      'chunking_documents',
      'generating_embeddings',
      'storing_vectors',
      'extracting_facts',
      'completing',
    ];
    
    const currentIndex = stages.indexOf(currentStage || '');
    return ((currentIndex + 1) / stages.length) * 100;
  };

  return (
    <Box>
      <Grid container spacing={3}>
        <Grid item xs={12}>
          <Paper sx={{ p: 3 }}>
            <Box sx={{ mb: 2, display: 'flex', alignItems: 'center', gap: 2 }}>
              <Typography variant="h6">Processing Progress</Typography>
              {currentStage && (
                <Chip
                  label={currentStage.replace(/_/g, ' ').toUpperCase()}
                  color="primary"
                  size="small"
                />
              )}
            </Box>
            <LinearProgress
              variant="determinate"
              value={getStageProgress()}
              sx={{ height: 8, borderRadius: 4 }}
            />
          </Paper>
        </Grid>

        <Grid item xs={12} md={4}>
          <ProcessingStats stats={stats} />
        </Grid>

        <Grid item xs={12} md={8}>
          <Paper sx={{ p: 3, height: '600px', overflow: 'hidden' }}>
            <Typography variant="h6" gutterBottom>
              Document Discovery Stream
            </Typography>
            <DocumentStream />
          </Paper>
        </Grid>

        {/* Show chunking animation when in chunking stage */}
        {currentStage === ProcessingStage.CHUNKING_DOCUMENTS && currentChunkingDocument && (
          <Grid item xs={12}>
            <ChunkingAnimation
              isActive={true}
              progress={currentChunkingDocument.progress || 0}
              chunksCreated={currentChunkingDocument.chunks || 0}
              documentTitle={currentChunkingDocument.title}
            />
          </Grid>
        )}
      </Grid>
    </Box>
  );
};

export default ProcessingVisualization;