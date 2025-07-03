import { ReactElement, useEffect, useState } from 'react';
import {
  Box,
  Card,
  CardContent,
  Typography,
  LinearProgress,
  List,
  ListItem,
  ListItemIcon,
  ListItemText,
  Collapse,
  IconButton,
  Chip,
  Alert,
  Stack
} from '@mui/material';
import {
  Description as DocumentIcon,
  CheckCircle as CheckIcon,
  Error as ErrorIcon,
  ExpandMore,
  ExpandLess,
  Analytics,
  Storage
} from '@mui/icons-material';
import { useWebSocket } from '../../hooks/useWebSocket';
import { useAppSelector } from '../../hooks/redux';
import { ProcessingDocument, ProcessingStage } from '../../types/discovery.types';

interface DiscoveryProgressProps {
  caseId: string;
}

export function DiscoveryProgress({ caseId }: DiscoveryProgressProps): ReactElement {
  const [expanded, setExpanded] = useState(true);
  const { on } = useWebSocket(caseId);
  const discoveryState = useAppSelector(state => state.discovery);
  
  // Listen for WebSocket events
  useEffect(() => {
    const unsubscribeStarted = on('discovery:started', (data) => {
      console.log('Discovery started:', data);
    });

    const unsubscribeCompleted = on('discovery:completed', (data) => {
      console.log('Discovery completed:', data);
    });

    const unsubscribeError = on('discovery:error', (data) => {
      console.error('Discovery error:', data);
    });

    return () => {
      unsubscribeStarted();
      unsubscribeCompleted();
      unsubscribeError();
    };
  }, [on]);

  // Calculate overall progress
  const calculateOverallProgress = () => {
    const docs = discoveryState.documents;
    if (docs.length === 0) return 0;
    
    const totalProgress = docs.reduce((sum, doc) => sum + doc.progress, 0);
    return Math.round(totalProgress / docs.length);
  };

  const getStageLabel = (stage: ProcessingStage): string => {
    const labels: Record<ProcessingStage, string> = {
      [ProcessingStage.INITIALIZING]: 'Initializing',
      [ProcessingStage.DISCOVERING_DOCUMENTS]: 'Discovering Documents',
      [ProcessingStage.CLASSIFYING_DOCUMENTS]: 'Classifying Documents',
      [ProcessingStage.CHUNKING_DOCUMENTS]: 'Chunking Documents',
      [ProcessingStage.GENERATING_EMBEDDINGS]: 'Generating Embeddings',
      [ProcessingStage.STORING_VECTORS]: 'Storing Vectors',
      [ProcessingStage.EXTRACTING_FACTS]: 'Extracting Facts',
      [ProcessingStage.COMPLETING]: 'Completing'
    };
    return labels[stage] || stage;
  };

  const getDocumentIcon = (doc: ProcessingDocument) => {
    if (doc.status === 'completed') return <CheckIcon color="success" />;
    if (doc.status === 'error') return <ErrorIcon color="error" />;
    return <DocumentIcon color="primary" />;
  };

  if (!discoveryState.isProcessing && discoveryState.documents.length === 0) {
    return <Box />;
  }

  const overallProgress = calculateOverallProgress();
  const stats = discoveryState.stats;

  return (
    <Card sx={{ mb: 2 }}>
      <CardContent>
        <Box display="flex" justifyContent="space-between" alignItems="center" mb={2}>
          <Typography variant="h6" component="h3">
            Discovery Processing
          </Typography>
          <IconButton size="small" onClick={() => setExpanded(!expanded)}>
            {expanded ? <ExpandLess /> : <ExpandMore />}
          </IconButton>
        </Box>

        {/* Overall Progress */}
        <Box mb={2}>
          <Box display="flex" justifyContent="space-between" mb={1}>
            <Typography variant="body2" color="text.secondary">
              Overall Progress
            </Typography>
            <Typography variant="body2" color="text.secondary">
              {overallProgress}%
            </Typography>
          </Box>
          <LinearProgress 
            variant="determinate" 
            value={overallProgress} 
            sx={{ height: 8, borderRadius: 1 }}
          />
        </Box>

        {/* Current Stage */}
        {discoveryState.currentStage && (
          <Box mb={2}>
            <Chip
              label={getStageLabel(discoveryState.currentStage)}
              color="primary"
              size="small"
              sx={{ mb: 1 }}
            />
          </Box>
        )}

        <Collapse in={expanded}>
          {/* Summary Stats */}
          {stats && (
            <Stack direction="row" spacing={2} mb={2}>
              <Chip
                icon={<DocumentIcon />}
                label={`${stats.documentsProcessed}/${stats.documentsFound} Documents`}
                size="small"
                variant="outlined"
              />
              <Chip
                icon={<Analytics />}
                label={`${stats.chunksCreated} Chunks`}
                size="small"
                variant="outlined"
              />
              <Chip
                icon={<Storage />}
                label={`${stats.vectorsStored} Vectors`}
                size="small"
                variant="outlined"
              />
            </Stack>
          )}

          {/* Document List */}
          <List dense>
            {discoveryState.documents.map((doc) => (
              <ListItem key={doc.id}>
                <ListItemIcon>{getDocumentIcon(doc)}</ListItemIcon>
                <ListItemText
                  primary={
                    <Box display="flex" justifyContent="space-between" alignItems="center">
                      <Typography variant="body2" noWrap sx={{ maxWidth: '60%' }}>
                        {doc.title}
                      </Typography>
                      <Typography variant="caption" color="text.secondary">
                        {doc.progress}%
                      </Typography>
                    </Box>
                  }
                  secondary={
                    <Box>
                      <LinearProgress
                        variant="determinate"
                        value={doc.progress}
                        sx={{ height: 4, mt: 0.5, mb: 0.5 }}
                      />
                      {doc.error && (
                        <Typography variant="caption" color="error">
                          {doc.error}
                        </Typography>
                      )}
                      {doc.batesRange && (
                        <Typography variant="caption" color="text.secondary">
                          Bates: {doc.batesRange.start} - {doc.batesRange.end}
                        </Typography>
                      )}
                    </Box>
                  }
                />
              </ListItem>
            ))}
          </List>

          {/* Error Alert */}
          {discoveryState.error && (
            <Alert severity="error" sx={{ mt: 2 }}>
              {discoveryState.error}
            </Alert>
          )}
        </Collapse>
      </CardContent>
    </Card>
  );
}