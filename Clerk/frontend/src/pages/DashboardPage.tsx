import { Typography, Grid, Paper, Box } from '@mui/material';
import { styled } from '@mui/material/styles';

const StatCard = styled(Paper)(({ theme }) => ({
  padding: theme.spacing(3),
  textAlign: 'center',
  color: theme.palette.text.secondary,
  height: '100%',
}));

const DashboardPage = () => {
  return (
    <Box>
      <Typography variant="h4" component="h1" gutterBottom>
        Dashboard
      </Typography>
      
      <Grid container spacing={3}>
        <Grid item xs={12} sm={6} md={3}>
          <StatCard>
            <Typography variant="h6" gutterBottom>
              Active Cases
            </Typography>
            <Typography variant="h3" color="primary">
              12
            </Typography>
          </StatCard>
        </Grid>
        
        <Grid item xs={12} sm={6} md={3}>
          <StatCard>
            <Typography variant="h6" gutterBottom>
              Documents Processed
            </Typography>
            <Typography variant="h3" color="primary">
              1,234
            </Typography>
          </StatCard>
        </Grid>
        
        <Grid item xs={12} sm={6} md={3}>
          <StatCard>
            <Typography variant="h6" gutterBottom>
              Motions Drafted
            </Typography>
            <Typography variant="h3" color="primary">
              23
            </Typography>
          </StatCard>
        </Grid>
        
        <Grid item xs={12} sm={6} md={3}>
          <StatCard>
            <Typography variant="h6" gutterBottom>
              Processing Time Saved
            </Typography>
            <Typography variant="h3" color="primary">
              156h
            </Typography>
          </StatCard>
        </Grid>
      </Grid>
      
      <Box mt={4}>
        <Typography variant="h5" gutterBottom>
          Recent Activity
        </Typography>
        <Paper sx={{ p: 2 }}>
          <Typography color="text.secondary">
            Recent processing activity will appear here...
          </Typography>
        </Paper>
      </Box>
    </Box>
  );
};

export default DashboardPage;