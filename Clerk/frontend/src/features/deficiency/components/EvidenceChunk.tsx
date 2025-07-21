import React from 'react';
import { Box, Paper, Typography, Chip } from '@mui/material';
import { EvidenceChunk as EvidenceChunkType } from '../types/DeficiencyReport.types';

interface EvidenceChunkProps {
  chunk: EvidenceChunkType;
}

export const EvidenceChunk: React.FC<EvidenceChunkProps> = ({ chunk }) => {
  return (
    <Paper variant="outlined" sx={{ p: 2, mb: 1 }}>
      <Box display="flex" justifyContent="space-between" alignItems="flex-start" mb={1}>
        <Box display="flex" gap={1}>
          {chunk.page_number && (
            <Chip label={`Page ${chunk.page_number}`} size="small" variant="outlined" />
          )}
          {chunk.bates_number && (
            <Chip label={chunk.bates_number} size="small" variant="outlined" />
          )}
        </Box>
        
        <Chip
          label={`${Math.round(chunk.relevance_score * 100)}% relevant`}
          size="small"
          color={chunk.relevance_score > 0.8 ? 'success' : 'default'}
        />
      </Box>
      
      <Typography variant="body2" sx={{ whiteSpace: 'pre-wrap' }}>
        {chunk.chunk_text}
      </Typography>
    </Paper>
  );
};