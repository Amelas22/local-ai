import React from 'react';
import { Box, Typography, Chip, Tooltip } from '@mui/material';
import DescriptionIcon from '@mui/icons-material/Description';
import { BatesRange } from '@/types/discovery.types';

interface BatesNumberDisplayProps {
  batesRange?: BatesRange;
  size?: 'small' | 'medium' | 'large';
  showIcon?: boolean;
  className?: string;
}

const BatesNumberDisplay: React.FC<BatesNumberDisplayProps> = ({
  batesRange,
  size = 'medium',
  showIcon = true,
  className,
}) => {
  if (!batesRange || !batesRange.start || !batesRange.end) {
    return null;
  }

  const getFontSize = () => {
    switch (size) {
      case 'small':
        return '0.75rem';
      case 'large':
        return '1rem';
      default:
        return '0.875rem';
    }
  };

  const getIconSize = () => {
    switch (size) {
      case 'small':
        return 16;
      case 'large':
        return 24;
      default:
        return 20;
    }
  };

  const formatBatesNumber = (bates: string) => {
    // Add spacing for readability if it's a long alphanumeric string
    if (bates.length > 10) {
      return bates.replace(/(.{3})(.{6})/, '$1 $2 ');
    }
    return bates;
  };

  const getBatesRangeText = () => {
    if (batesRange.start === batesRange.end) {
      return formatBatesNumber(batesRange.start);
    }
    return `${formatBatesNumber(batesRange.start)} - ${formatBatesNumber(batesRange.end)}`;
  };

  const getPageCount = () => {
    // Try to extract numeric parts from Bates numbers to estimate page count
    const startMatch = batesRange.start.match(/\d+$/);
    const endMatch = batesRange.end.match(/\d+$/);
    
    if (startMatch && endMatch) {
      const startNum = parseInt(startMatch[0], 10);
      const endNum = parseInt(endMatch[0], 10);
      const count = endNum - startNum + 1;
      return count > 0 ? count : null;
    }
    return null;
  };

  const pageCount = getPageCount();

  return (
    <Box 
      className={className}
      sx={{ 
        display: 'inline-flex', 
        alignItems: 'center',
        gap: 1,
      }}
    >
      {showIcon && (
        <DescriptionIcon 
          sx={{ 
            fontSize: getIconSize(),
            color: 'text.secondary' 
          }} 
        />
      )}
      
      <Tooltip 
        title={
          <Box>
            <Typography variant="body2">Bates Number Range</Typography>
            <Typography variant="caption" color="text.secondary">
              {batesRange.start === batesRange.end 
                ? `Single page: ${batesRange.start}`
                : `From: ${batesRange.start}`
              }
            </Typography>
            {batesRange.start !== batesRange.end && (
              <Typography variant="caption" color="text.secondary" display="block">
                To: {batesRange.end}
              </Typography>
            )}
            {pageCount && (
              <Typography variant="caption" color="primary" display="block" sx={{ mt: 0.5 }}>
                Estimated {pageCount} page{pageCount !== 1 ? 's' : ''}
              </Typography>
            )}
          </Box>
        }
        arrow
      >
        <Box sx={{ display: 'flex', alignItems: 'center', gap: 0.5 }}>
          <Typography 
            variant="body2" 
            sx={{ 
              fontSize: getFontSize(),
              fontFamily: 'monospace',
              fontWeight: 500,
              color: 'primary.main',
            }}
          >
            {getBatesRangeText()}
          </Typography>
          
          {pageCount && pageCount > 1 && (
            <Chip
              label={`${pageCount}p`}
              size="small"
              variant="outlined"
              sx={{
                height: size === 'small' ? 18 : 20,
                fontSize: size === 'small' ? '0.65rem' : '0.7rem',
                '& .MuiChip-label': {
                  px: 0.75,
                },
              }}
            />
          )}
        </Box>
      </Tooltip>
    </Box>
  );
};

export default BatesNumberDisplay;