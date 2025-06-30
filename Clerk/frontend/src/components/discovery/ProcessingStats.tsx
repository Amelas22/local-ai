import { Paper, Typography, Box, Divider } from '@mui/material';
import { ProcessingStats as ProcessingStatsType } from '@/store/slices/discoverySlice';

interface ProcessingStatsProps {
  stats: ProcessingStatsType;
}

const ProcessingStats = ({ stats }: ProcessingStatsProps) => {
  const statItems = [
    { label: 'Documents Found', value: stats.documentsFound, color: '#3182ce' },
    { label: 'Documents Processed', value: stats.documentsProcessed, color: '#38a169' },
    { label: 'Chunks Created', value: stats.chunksCreated, color: '#9c27b0' },
    { label: 'Vectors Stored', value: stats.vectorsStored, color: '#ff9800' },
    { label: 'Errors', value: stats.errors, color: '#f44336' },
  ];

  return (
    <Paper sx={{ p: 3, height: '100%' }}>
      <Typography variant="h6" gutterBottom>
        Processing Statistics
      </Typography>
      
      <Box sx={{ mt: 2 }}>
        {statItems.map((item, index) => (
          <Box key={item.label}>
            <Box
              sx={{
                display: 'flex',
                justifyContent: 'space-between',
                alignItems: 'center',
                py: 2,
              }}
            >
              <Typography variant="body1" color="text.secondary">
                {item.label}
              </Typography>
              <Typography
                variant="h5"
                fontWeight="medium"
                sx={{ color: item.color }}
              >
                {item.value.toLocaleString()}
              </Typography>
            </Box>
            {index < statItems.length - 1 && <Divider />}
          </Box>
        ))}
      </Box>
    </Paper>
  );
};

export default ProcessingStats;