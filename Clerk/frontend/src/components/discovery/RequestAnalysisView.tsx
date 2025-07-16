import React, { useState } from 'react';
import {
  Box,
  Typography,
  TextField,
  Chip,
  Stack,
  Divider,
  IconButton,
  Collapse,
  List,
  ListItem,
  ListItemText,
  Paper,
  Alert,
} from '@mui/material';
import {
  ExpandMore as ExpandMoreIcon,
  ExpandLess as ExpandLessIcon,
  Search as SearchIcon,
  Description as DocumentIcon,
} from '@mui/icons-material';
import { 
  RequestAnalysis, 
  EvidenceItem,
  ProductionStatus 
} from '../../types/discovery.types';

interface RequestAnalysisViewProps {
  analysis: RequestAnalysis;
  editable?: boolean;
  onUpdate?: (updated: RequestAnalysis) => void;
}

const RequestAnalysisView: React.FC<RequestAnalysisViewProps> = ({
  analysis,
  editable = false,
  onUpdate,
}) => {
  const [editedAnalysis, setEditedAnalysis] = useState(analysis);
  const [showSearchQueries, setShowSearchQueries] = useState(false);

  const handleFieldChange = (field: keyof RequestAnalysis, value: any) => {
    const updated = { ...editedAnalysis, [field]: value };
    setEditedAnalysis(updated);
    if (onUpdate) {
      onUpdate(updated);
    }
  };

  const renderEvidence = (evidence: EvidenceItem[]) => {
    if (evidence.length === 0) {
      return (
        <Alert severity="info" sx={{ mt: 2 }}>
          No supporting documents found in the production.
        </Alert>
      );
    }

    return (
      <Box sx={{ mt: 2 }}>
        <Typography variant="subtitle2" gutterBottom>
          Evidence Found ({evidence.length} document{evidence.length !== 1 ? 's' : ''}):
        </Typography>
        {evidence.map((item, idx) => (
          <Paper
            key={idx}
            elevation={1}
            sx={{ 
              p: 2, 
              mb: 2,
              backgroundColor: 'background.default',
              border: '1px solid',
              borderColor: 'divider',
            }}
          >
            <Box display="flex" alignItems="flex-start" gap={1}>
              <DocumentIcon color="action" fontSize="small" />
              <Box flex={1}>
                <Typography variant="body2" fontWeight="bold">
                  {item.document_title}
                </Typography>
                {item.bates_range && (
                  <Typography variant="caption" color="text.secondary">
                    Bates: {item.bates_range}
                  </Typography>
                )}
                <Box
                  sx={{
                    mt: 1,
                    p: 1,
                    backgroundColor: '#e8f5e9',
                    borderRadius: 1,
                    borderLeft: '4px solid #4caf50',
                  }}
                >
                  <Typography variant="body2" sx={{ fontStyle: 'italic' }}>
                    "{item.quoted_text}"
                  </Typography>
                </Box>
                <Box display="flex" justifyContent="space-between" mt={1}>
                  {item.page_numbers && item.page_numbers.length > 0 && (
                    <Typography variant="caption" color="text.secondary">
                      Pages: {item.page_numbers.join(', ')}
                    </Typography>
                  )}
                  <Chip
                    label={`${item.confidence_score}% confidence`}
                    size="small"
                    variant="outlined"
                    color={item.confidence_score >= 80 ? 'success' : 'warning'}
                  />
                </Box>
              </Box>
            </Box>
          </Paper>
        ))}
      </Box>
    );
  };

  const renderDeficiencies = (deficiencies: string[]) => {
    if (deficiencies.length === 0 && analysis.status === ProductionStatus.NOT_PRODUCED) {
      return (
        <Alert severity="error" sx={{ mt: 2 }}>
          No responsive documents were produced for this request.
        </Alert>
      );
    }

    if (deficiencies.length === 0) {
      return null;
    }

    return (
      <Box sx={{ mt: 2 }}>
        <Typography variant="subtitle2" gutterBottom color="error">
          Deficiencies Identified:
        </Typography>
        <List dense>
          {deficiencies.map((deficiency, idx) => (
            <ListItem key={idx} sx={{ pl: 2 }}>
              <ListItemText
                primary={deficiency}
                primaryTypographyProps={{
                  variant: 'body2',
                  color: 'error.dark',
                }}
              />
            </ListItem>
          ))}
        </List>
      </Box>
    );
  };

  return (
    <Box>
      <Stack spacing={3}>
        {/* Request Text */}
        <Box>
          <Typography variant="subtitle2" gutterBottom color="primary">
            Request {analysis.request_number}:
          </Typography>
          {editable ? (
            <TextField
              fullWidth
              multiline
              rows={2}
              value={editedAnalysis.request_text}
              onChange={(e) => handleFieldChange('request_text', e.target.value)}
              variant="outlined"
              size="small"
            />
          ) : (
            <Typography variant="body1" sx={{ pl: 2 }}>
              {analysis.request_text}
            </Typography>
          )}
        </Box>

        {/* Defense Response */}
        {analysis.response_text && (
          <Box>
            <Typography variant="subtitle2" gutterBottom color="text.secondary">
              Defense Response:
            </Typography>
            {editable ? (
              <TextField
                fullWidth
                multiline
                rows={2}
                value={editedAnalysis.response_text || ''}
                onChange={(e) => handleFieldChange('response_text', e.target.value)}
                variant="outlined"
                size="small"
              />
            ) : (
              <Typography variant="body2" sx={{ pl: 2, fontStyle: 'italic' }}>
                "{analysis.response_text}"
              </Typography>
            )}
          </Box>
        )}

        <Divider />

        {/* Analysis Summary */}
        <Box>
          <Typography variant="subtitle2" gutterBottom>
            Analysis Summary:
          </Typography>
          <Box display="flex" gap={2} alignItems="center" flexWrap="wrap">
            <Chip
              label={`Status: ${analysis.status.replace('_', ' ').toUpperCase()}`}
              color={
                analysis.status === ProductionStatus.FULLY_PRODUCED ? 'success' :
                analysis.status === ProductionStatus.PARTIALLY_PRODUCED ? 'warning' : 'error'
              }
            />
            <Chip
              label={`Confidence: ${analysis.confidence}%`}
              variant="outlined"
              color={analysis.confidence >= 80 ? 'success' : 'warning'}
            />
            <Chip
              label={`${analysis.evidence.length} supporting document${analysis.evidence.length !== 1 ? 's' : ''}`}
              variant="outlined"
              icon={<DocumentIcon />}
            />
          </Box>
        </Box>

        {/* Search Queries Used */}
        <Box>
          <Box display="flex" alignItems="center">
            <Typography variant="subtitle2" sx={{ flexGrow: 1 }}>
              Search Queries Used ({analysis.search_queries_used.length})
            </Typography>
            <IconButton
              size="small"
              onClick={() => setShowSearchQueries(!showSearchQueries)}
            >
              {showSearchQueries ? <ExpandLessIcon /> : <ExpandMoreIcon />}
            </IconButton>
          </Box>
          <Collapse in={showSearchQueries}>
            <Box sx={{ pl: 2, pt: 1 }}>
              {analysis.search_queries_used.map((query, idx) => (
                <Chip
                  key={idx}
                  label={query}
                  size="small"
                  icon={<SearchIcon />}
                  sx={{ mr: 1, mb: 1 }}
                  variant="outlined"
                />
              ))}
            </Box>
          </Collapse>
        </Box>

        {/* Evidence */}
        {renderEvidence(analysis.evidence)}

        {/* Deficiencies */}
        {renderDeficiencies(analysis.deficiencies)}

        {/* Additional Notes for Partial Production */}
        {analysis.status === ProductionStatus.PARTIALLY_PRODUCED && (
          <Alert severity="warning" sx={{ mt: 2 }}>
            This request was only partially satisfied. Some responsive documents may be missing or incomplete.
            Review the evidence and deficiencies to determine what additional documents should be requested.
          </Alert>
        )}
      </Stack>
    </Box>
  );
};

export default RequestAnalysisView;