import React, { useEffect, useState } from 'react';
import { Box, Typography, LinearProgress, Fade, Paper } from '@mui/material';
import { keyframes } from '@mui/system';
import ContentCutIcon from '@mui/icons-material/ContentCut';
import TextSnippetIcon from '@mui/icons-material/TextSnippet';

interface ChunkingAnimationProps {
  isActive: boolean;
  progress: number;
  chunksCreated: number;
  documentTitle?: string;
}

// Keyframe animations
const slideDown = keyframes`
  0% {
    transform: translateY(-20px);
    opacity: 0;
  }
  100% {
    transform: translateY(0);
    opacity: 1;
  }
`;

const pulse = keyframes`
  0% {
    transform: scale(1);
  }
  50% {
    transform: scale(1.05);
  }
  100% {
    transform: scale(1);
  }
`;

const ChunkingAnimation: React.FC<ChunkingAnimationProps> = ({
  isActive,
  progress,
  chunksCreated,
  documentTitle,
}) => {
  const [visibleChunks, setVisibleChunks] = useState<number[]>([]);
  const [lastChunkCount, setLastChunkCount] = useState(0);

  useEffect(() => {
    if (chunksCreated > lastChunkCount) {
      // Add new chunks with animation
      const newChunks: number[] = [];
      for (let i = lastChunkCount; i < chunksCreated && i < lastChunkCount + 3; i++) {
        newChunks.push(i);
      }
      
      setVisibleChunks((prev) => [...prev.slice(-6), ...newChunks]);
      setLastChunkCount(chunksCreated);
    }
  }, [chunksCreated, lastChunkCount]);

  if (!isActive && chunksCreated === 0) {
    return null;
  }

  return (
    <Paper
      elevation={1}
      sx={{
        p: 2,
        background: 'linear-gradient(135deg, #f5f5f5 0%, #ffffff 100%)',
        position: 'relative',
        overflow: 'hidden',
      }}
    >
      <Box sx={{ mb: 2 }}>
        <Box sx={{ display: 'flex', alignItems: 'center', gap: 1, mb: 1 }}>
          <ContentCutIcon 
            sx={{ 
              color: 'primary.main',
              animation: isActive ? `${pulse} 2s ease-in-out infinite` : 'none',
            }} 
          />
          <Typography variant="subtitle2" fontWeight="medium">
            Document Chunking
          </Typography>
        </Box>
        
        {documentTitle && (
          <Typography variant="caption" color="text.secondary" noWrap>
            {documentTitle}
          </Typography>
        )}
      </Box>

      <Box sx={{ mb: 2 }}>
        <Box sx={{ display: 'flex', justifyContent: 'space-between', mb: 0.5 }}>
          <Typography variant="caption" color="text.secondary">
            Progress
          </Typography>
          <Typography variant="caption" color="primary.main" fontWeight="medium">
            {Math.round(progress)}%
          </Typography>
        </Box>
        <LinearProgress
          variant="determinate"
          value={progress}
          sx={{
            height: 6,
            borderRadius: 3,
            backgroundColor: 'grey.200',
            '& .MuiLinearProgress-bar': {
              borderRadius: 3,
              background: 'linear-gradient(90deg, #1976d2 0%, #42a5f5 100%)',
            },
          }}
        />
      </Box>

      <Box sx={{ mb: 1 }}>
        <Typography variant="caption" color="text.secondary">
          Chunks Created: <strong>{chunksCreated}</strong>
        </Typography>
      </Box>

      <Box
        sx={{
          display: 'flex',
          flexWrap: 'wrap',
          gap: 0.5,
          minHeight: 40,
          position: 'relative',
        }}
      >
        {visibleChunks.map((chunkIndex, idx) => (
          <Fade
            key={`chunk-${chunkIndex}`}
            in={true}
            timeout={300}
            style={{ transitionDelay: `${idx * 50}ms` }}
          >
            <Box
              sx={{
                display: 'flex',
                alignItems: 'center',
                gap: 0.5,
                px: 1,
                py: 0.5,
                borderRadius: 1,
                backgroundColor: 'primary.main',
                color: 'primary.contrastText',
                fontSize: '0.7rem',
                animation: `${slideDown} 0.3s ease-out`,
                '&:hover': {
                  transform: 'scale(1.05)',
                  transition: 'transform 0.2s',
                },
              }}
            >
              <TextSnippetIcon sx={{ fontSize: 14 }} />
              <Typography variant="caption" sx={{ fontSize: '0.7rem' }}>
                #{chunkIndex + 1}
              </Typography>
            </Box>
          </Fade>
        ))}
        
        {isActive && chunksCreated > 0 && (
          <Box
            sx={{
              display: 'flex',
              alignItems: 'center',
              px: 1,
              py: 0.5,
              animation: `${pulse} 1s ease-in-out infinite`,
            }}
          >
            <Typography variant="caption" color="text.secondary">
              ...
            </Typography>
          </Box>
        )}
      </Box>

      {/* Background decoration */}
      <Box
        sx={{
          position: 'absolute',
          top: -50,
          right: -50,
          width: 150,
          height: 150,
          borderRadius: '50%',
          background: 'linear-gradient(135deg, rgba(25, 118, 210, 0.05) 0%, rgba(66, 165, 245, 0.05) 100%)',
          pointerEvents: 'none',
        }}
      />
    </Paper>
  );
};

export default ChunkingAnimation;