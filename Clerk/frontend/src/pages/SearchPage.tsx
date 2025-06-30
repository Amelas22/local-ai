import { Typography, Box, Paper } from '@mui/material';

const SearchPage = () => {
  return (
    <Box>
      <Typography variant="h4" component="h1" gutterBottom>
        Search Documents
      </Typography>
      
      <Paper sx={{ p: 3 }}>
        <Typography color="text.secondary">
          Search interface coming soon...
        </Typography>
      </Paper>
    </Box>
  );
};

export default SearchPage;