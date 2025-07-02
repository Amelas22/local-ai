import React from 'react';
import {
  Box,
  Paper,
  Typography,
  Chip,
  Grid,
  Divider,
  Stack,
  Tooltip,
} from '@mui/material';
import BusinessIcon from '@mui/icons-material/Business';
import CalendarTodayIcon from '@mui/icons-material/CalendarToday';
import FolderIcon from '@mui/icons-material/Folder';
import SecurityIcon from '@mui/icons-material/Security';
import AssignmentIcon from '@mui/icons-material/Assignment';
import InfoOutlinedIcon from '@mui/icons-material/InfoOutlined';
import { format } from 'date-fns';

interface ProductionMetadataProps {
  productionBatch: string;
  producingParty: string;
  productionDate?: string;
  responsiveToRequests: string[];
  confidentialityDesignation?: string;
  caseId: string;
  folderId: string;
  className?: string;
}

const ProductionMetadata: React.FC<ProductionMetadataProps> = ({
  productionBatch,
  producingParty,
  productionDate,
  responsiveToRequests,
  confidentialityDesignation,
  caseId,
  folderId,
  className,
}) => {
  const getConfidentialityColor = () => {
    switch (confidentialityDesignation?.toLowerCase()) {
      case 'highly confidential':
      case 'attorneys eyes only':
        return 'error';
      case 'confidential':
        return 'warning';
      default:
        return 'default';
    }
  };

  const MetadataItem: React.FC<{
    icon: React.ReactNode;
    label: string;
    value: React.ReactNode;
    tooltip?: string;
  }> = ({ icon, label, value, tooltip }) => (
    <Box sx={{ display: 'flex', alignItems: 'flex-start', gap: 1.5 }}>
      <Box sx={{ color: 'text.secondary', mt: 0.5 }}>{icon}</Box>
      <Box sx={{ flex: 1 }}>
        <Box sx={{ display: 'flex', alignItems: 'center', gap: 0.5 }}>
          <Typography variant="caption" color="text.secondary">
            {label}
          </Typography>
          {tooltip && (
            <Tooltip title={tooltip} arrow>
              <InfoOutlinedIcon sx={{ fontSize: 14, color: 'text.disabled' }} />
            </Tooltip>
          )}
        </Box>
        <Typography variant="body2" fontWeight="medium">
          {value}
        </Typography>
      </Box>
    </Box>
  );

  return (
    <Paper className={className} elevation={1} sx={{ p: 3 }}>
      <Typography variant="h6" gutterBottom>
        Production Information
      </Typography>
      
      <Divider sx={{ mb: 2 }} />
      
      <Grid container spacing={3}>
        <Grid item xs={12} md={6}>
          <Stack spacing={2}>
            <MetadataItem
              icon={<FolderIcon fontSize="small" />}
              label="Production Batch"
              value={productionBatch}
              tooltip="Unique identifier for this production set"
            />
            
            <MetadataItem
              icon={<BusinessIcon fontSize="small" />}
              label="Producing Party"
              value={producingParty}
              tooltip="Party responsible for producing these documents"
            />
            
            {productionDate && (
              <MetadataItem
                icon={<CalendarTodayIcon fontSize="small" />}
                label="Production Date"
                value={format(new Date(productionDate), 'MMMM d, yyyy')}
              />
            )}
          </Stack>
        </Grid>
        
        <Grid item xs={12} md={6}>
          <Stack spacing={2}>
            {confidentialityDesignation && (
              <MetadataItem
                icon={<SecurityIcon fontSize="small" />}
                label="Confidentiality"
                value={
                  <Chip
                    label={confidentialityDesignation}
                    size="small"
                    color={getConfidentialityColor()}
                    variant={getConfidentialityColor() === 'default' ? 'outlined' : 'filled'}
                  />
                }
                tooltip="Confidentiality designation for these documents"
              />
            )}
            
            <Box>
              <Box sx={{ display: 'flex', alignItems: 'center', gap: 1.5, mb: 1 }}>
                <AssignmentIcon fontSize="small" sx={{ color: 'text.secondary' }} />
                <Typography variant="caption" color="text.secondary">
                  Responsive to Requests
                </Typography>
              </Box>
              {responsiveToRequests.length > 0 ? (
                <Box sx={{ display: 'flex', flexWrap: 'wrap', gap: 0.5, ml: 4 }}>
                  {responsiveToRequests.map((request, index) => (
                    <Chip
                      key={index}
                      label={request}
                      size="small"
                      variant="outlined"
                      sx={{
                        borderColor: 'primary.main',
                        color: 'primary.main',
                        '& .MuiChip-label': {
                          fontSize: '0.75rem',
                        },
                      }}
                    />
                  ))}
                </Box>
              ) : (
                <Typography variant="body2" color="text.secondary" sx={{ ml: 4 }}>
                  No specific requests indicated
                </Typography>
              )}
            </Box>
          </Stack>
        </Grid>
      </Grid>
      
      <Divider sx={{ my: 2 }} />
      
      <Box sx={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
        <Box>
          <Typography variant="caption" color="text.secondary">
            Case ID: <strong>{caseId}</strong>
          </Typography>
        </Box>
        <Box>
          <Typography variant="caption" color="text.secondary">
            Box Folder: <strong>{folderId}</strong>
          </Typography>
        </Box>
      </Box>
    </Paper>
  );
};

export default ProductionMetadata;