import React from 'react';
import { Box, Typography, Grid, Chip, Button, Menu, MenuItem } from '@mui/material';
import { Download as DownloadIcon, Print as PrintIcon } from '@mui/icons-material';
import { DeficiencyReport } from '../types/DeficiencyReport.types';

interface DeficiencyReportHeaderProps {
  report: DeficiencyReport;
}

export const DeficiencyReportHeader: React.FC<DeficiencyReportHeaderProps> = ({ report }) => {
  const [anchorEl, setAnchorEl] = React.useState<null | HTMLElement>(null);

  const handleExportClick = (event: React.MouseEvent<HTMLButtonElement>) => {
    setAnchorEl(event.currentTarget);
  };

  const handleExportClose = () => {
    setAnchorEl(null);
  };

  const handleExport = async (format: 'pdf' | 'excel') => {
    try {
      const { deficiencyAPI } = await import('../services/deficiencyAPI');
      const blob = await deficiencyAPI.exportReport(report.id, format);
      
      const url = window.URL.createObjectURL(blob);
      const a = document.createElement('a');
      a.href = url;
      a.download = `deficiency-report-${report.case_name}-${new Date().toISOString().split('T')[0]}.${format === 'pdf' ? 'pdf' : 'xlsx'}`;
      document.body.appendChild(a);
      a.click();
      window.URL.revokeObjectURL(url);
      document.body.removeChild(a);
    } catch (error) {
      console.error('Export failed:', error);
    }
    handleExportClose();
  };

  const handlePrint = () => {
    window.print();
  };

  const getStatusColor = (status: DeficiencyReport['analysis_status']) => {
    switch (status) {
      case 'completed': return 'success';
      case 'processing': return 'warning';
      case 'failed': return 'error';
      default: return 'default';
    }
  };

  return (
    <Box p={3} borderBottom={1} borderColor="divider">
      <Box display="flex" justifyContent="space-between" alignItems="flex-start" mb={2}>
        <Box>
          <Typography variant="h5" gutterBottom>
            Deficiency Analysis Report
          </Typography>
          <Typography variant="body2" color="textSecondary">
            Case: {report.case_name}
          </Typography>
        </Box>
        
        <Box>
          <Button
            startIcon={<PrintIcon />}
            onClick={handlePrint}
            sx={{ mr: 1 }}
          >
            Print
          </Button>
          <Button
            startIcon={<DownloadIcon />}
            onClick={handleExportClick}
            variant="contained"
          >
            Export
          </Button>
          <Menu
            anchorEl={anchorEl}
            open={Boolean(anchorEl)}
            onClose={handleExportClose}
          >
            <MenuItem onClick={() => handleExport('pdf')}>Export as PDF</MenuItem>
            <MenuItem onClick={() => handleExport('excel')}>Export as Excel</MenuItem>
          </Menu>
        </Box>
      </Box>

      <Box mb={2}>
        <Chip
          label={report.analysis_status}
          color={getStatusColor(report.analysis_status)}
          size="small"
        />
      </Box>

      <Grid container spacing={3}>
        <Grid item xs={12} sm={6} md={3}>
          <Box>
            <Typography variant="body2" color="textSecondary">
              Total Requests
            </Typography>
            <Typography variant="h6">
              {report.total_requests}
            </Typography>
          </Box>
        </Grid>
        
        <Grid item xs={12} sm={6} md={3}>
          <Box>
            <Typography variant="body2" color="textSecondary">
              Fully Produced
            </Typography>
            <Typography variant="h6" color="success.main">
              {report.summary_statistics.fully_produced}
            </Typography>
          </Box>
        </Grid>
        
        <Grid item xs={12} sm={6} md={3}>
          <Box>
            <Typography variant="body2" color="textSecondary">
              Partially Produced
            </Typography>
            <Typography variant="h6" color="warning.main">
              {report.summary_statistics.partially_produced}
            </Typography>
          </Box>
        </Grid>
        
        <Grid item xs={12} sm={6} md={3}>
          <Box>
            <Typography variant="body2" color="textSecondary">
              Not Produced
            </Typography>
            <Typography variant="h6" color="error.main">
              {report.summary_statistics.not_produced}
            </Typography>
          </Box>
        </Grid>
      </Grid>
    </Box>
  );
};