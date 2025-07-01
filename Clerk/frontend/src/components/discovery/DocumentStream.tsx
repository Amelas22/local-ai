import { Box, Card, CardContent, Typography, Chip, LinearProgress } from '@mui/material';
import { useAppSelector } from '@/hooks/redux';
import { DocumentType } from '@/types/discovery.types';

const getDocumentTypeColor = (type: DocumentType): string => {
  const colorMap: Partial<Record<DocumentType, string>> = {
    [DocumentType.MOTION]: '#1976d2',
    [DocumentType.DEPOSITION]: '#9c27b0',
    [DocumentType.INTERROGATORY]: '#ff9800',
    [DocumentType.REQUEST_FOR_PRODUCTION]: '#ff5722',
    [DocumentType.CORRESPONDENCE]: '#4caf50',
    [DocumentType.EXPERT_REPORT]: '#f44336',
    [DocumentType.POLICE_REPORT]: '#e91e63',
    [DocumentType.CONTRACT]: '#3f51b5',
    [DocumentType.UNKNOWN]: '#757575',
  };
  
  return colorMap[type] || '#757575';
};

const DocumentStream = () => {
  const documents = useAppSelector((state) => state.discovery.documents);

  return (
    <Box
      sx={{
        height: 'calc(100% - 40px)',
        overflowY: 'auto',
        display: 'flex',
        flexDirection: 'column',
        gap: 2,
      }}
    >
      {documents.length === 0 ? (
        <Typography color="text.secondary" align="center" sx={{ mt: 4 }}>
          Waiting for documents to be discovered...
        </Typography>
      ) : (
        documents.map((doc) => (
          <Card
            key={doc.id}
            sx={{
              animation: 'slideIn 0.5s ease-out',
              '@keyframes slideIn': {
                from: {
                  opacity: 0,
                  transform: 'translateX(-20px)',
                },
                to: {
                  opacity: 1,
                  transform: 'translateX(0)',
                },
              },
            }}
          >
            <CardContent>
              <Box sx={{ display: 'flex', justifyContent: 'space-between', mb: 1 }}>
                <Typography variant="subtitle1" fontWeight="medium">
                  {doc.title}
                </Typography>
                <Chip
                  label={doc.type.replace(/_/g, ' ')}
                  size="small"
                  sx={{
                    backgroundColor: getDocumentTypeColor(doc.type),
                    color: 'white',
                  }}
                />
              </Box>
              
              {doc.batesRange && (
                <Typography variant="body2" color="text.secondary" gutterBottom>
                  Bates: {doc.batesRange.start} - {doc.batesRange.end}
                </Typography>
              )}
              
              <Box sx={{ display: 'flex', alignItems: 'center', gap: 1, mt: 1 }}>
                <Typography variant="caption" color="text.secondary">
                  Confidence: {(doc.confidence * 100).toFixed(0)}%
                </Typography>
                {doc.status === 'processing' && (
                  <LinearProgress
                    variant="indeterminate"
                    sx={{ flexGrow: 1, height: 2 }}
                  />
                )}
                {doc.status === 'completed' && (
                  <Chip label="✓ Processed" size="small" color="success" />
                )}
                {doc.status === 'error' && (
                  <Chip label="Error" size="small" color="error" />
                )}
              </Box>
            </CardContent>
          </Card>
        ))
      )}
    </Box>
  );
};

export default DocumentStream;