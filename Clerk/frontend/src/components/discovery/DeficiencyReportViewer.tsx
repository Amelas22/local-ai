import React, { useState, useEffect } from 'react';
import {
  Box,
  Paper,
  Typography,
  LinearProgress,
  Button,
  Accordion,
  AccordionSummary,
  AccordionDetails,
  Chip,
  IconButton,
  Alert,
  CircularProgress,
} from '@mui/material';
import {
  ExpandMore as ExpandMoreIcon,
  Download as DownloadIcon,
  Edit as EditIcon,
  Save as SaveIcon,
  Cancel as CancelIcon,
} from '@mui/icons-material';
import { 
  DeficiencyReport, 
  RequestAnalysis,
  ProductionStatus
} from '../../types/discovery.types';
import { useAppDispatch } from '../../hooks/redux';
import { showNotification } from '../../store/slices/uiSlice';
import RequestAnalysisView from './RequestAnalysisView';

interface DeficiencyReportViewerProps {
  report: DeficiencyReport;
  onUpdate?: (updatedReport: DeficiencyReport) => void;
  loading?: boolean;
}

export const DeficiencyReportViewer: React.FC<DeficiencyReportViewerProps> = ({
  report,
  onUpdate,
  loading = false,
}) => {
  const [editMode, setEditMode] = useState(false);
  const [editedReport, setEditedReport] = useState(report);
  const [downloadLoading, setDownloadLoading] = useState(false);
  const dispatch = useAppDispatch();

  useEffect(() => {
    setEditedReport(report);
  }, [report]);

  const getStatusColor = (status: string): 'success' | 'warning' | 'error' => {
    switch (status) {
      case ProductionStatus.FULLY_PRODUCED:
        return 'success';
      case ProductionStatus.PARTIALLY_PRODUCED:
        return 'warning';
      case ProductionStatus.NOT_PRODUCED:
        return 'error';
      default:
        return 'warning';
    }
  };

  const getStatusIcon = (status: string): string => {
    switch (status) {
      case ProductionStatus.FULLY_PRODUCED:
        return '✅';
      case ProductionStatus.PARTIALLY_PRODUCED:
        return '⚠️';
      case ProductionStatus.NOT_PRODUCED:
        return '❌';
      default:
        return '❓';
    }
  };

  const handleDownload = async () => {
    setDownloadLoading(true);
    try {
      const response = await fetch(`/api/discovery/reports/${report.id}/download`, {
        headers: {
          'X-Case-ID': report.case_name,
        },
      });
      
      if (!response.ok) {
        throw new Error('Failed to download report');
      }
      
      const blob = await response.blob();
      const url = window.URL.createObjectURL(blob);
      const a = document.createElement('a');
      a.href = url;
      a.download = `deficiency_report_${report.production_batch}_${new Date().toISOString().split('T')[0]}.pdf`;
      a.click();
      window.URL.revokeObjectURL(url);
      
      dispatch(showNotification({
        message: 'Report downloaded successfully',
        severity: 'success',
      }));
    } catch (error) {
      console.error('Failed to download report:', error);
      dispatch(showNotification({
        message: 'Failed to download report',
        severity: 'error',
      }));
    } finally {
      setDownloadLoading(false);
    }
  };

  const handleSave = () => {
    if (onUpdate) {
      onUpdate(editedReport);
    }
    setEditMode(false);
    dispatch(showNotification({
      message: 'Report updates saved',
      severity: 'success',
    }));
  };

  const handleCancel = () => {
    setEditedReport(report);
    setEditMode(false);
  };

  const handleAnalysisUpdate = (index: number, updatedAnalysis: RequestAnalysis) => {
    const newAnalyses = [...editedReport.analyses];
    newAnalyses[index] = updatedAnalysis;
    setEditedReport({
      ...editedReport,
      analyses: newAnalyses,
    });
  };

  const calculateDeficiencyStats = () => {
    const total = report.analyses.length;
    const fullyProduced = report.analyses.filter(a => a.status === ProductionStatus.FULLY_PRODUCED).length;
    const partiallyProduced = report.analyses.filter(a => a.status === ProductionStatus.PARTIALLY_PRODUCED).length;
    const notProduced = report.analyses.filter(a => a.status === ProductionStatus.NOT_PRODUCED).length;
    
    return { total, fullyProduced, partiallyProduced, notProduced };
  };

  const stats = calculateDeficiencyStats();

  if (loading) {
    return (
      <Box display="flex" justifyContent="center" alignItems="center" minHeight={400}>
        <CircularProgress />
      </Box>
    );
  }

  return (
    <Box>
      <Paper sx={{ p: 3, mb: 3 }}>
        <Box display="flex" justifyContent="space-between" alignItems="center" mb={2}>
          <Box>
            <Typography variant="h5" gutterBottom>
              Discovery Deficiency Analysis
            </Typography>
            <Typography variant="subtitle1" color="text.secondary">
              Production Batch: {report.production_batch}
            </Typography>
            <Typography variant="caption" color="text.secondary">
              Generated: {new Date(report.generated_at).toLocaleString()}
            </Typography>
          </Box>
          <Box>
            {!editMode ? (
              <IconButton onClick={() => setEditMode(true)} title="Edit Report">
                <EditIcon />
              </IconButton>
            ) : (
              <>
                <IconButton onClick={handleSave} color="primary" title="Save Changes">
                  <SaveIcon />
                </IconButton>
                <IconButton onClick={handleCancel} color="secondary" title="Cancel">
                  <CancelIcon />
                </IconButton>
              </>
            )}
            <Button
              variant="contained"
              startIcon={downloadLoading ? <CircularProgress size={20} /> : <DownloadIcon />}
              onClick={handleDownload}
              disabled={downloadLoading}
              sx={{ ml: 1 }}
            >
              Download Report
            </Button>
          </Box>
        </Box>
        
        <Box sx={{ mt: 3 }}>
          <Typography variant="body2" gutterBottom>
            Overall Completeness
          </Typography>
          <LinearProgress
            variant="determinate"
            value={report.overall_completeness}
            sx={{ height: 10, borderRadius: 5, mb: 1 }}
            color={report.overall_completeness >= 80 ? 'success' : report.overall_completeness >= 50 ? 'warning' : 'error'}
          />
          <Typography variant="body2" sx={{ mb: 3 }}>
            {report.overall_completeness.toFixed(1)}% Complete
          </Typography>

          <Box display="flex" gap={2} flexWrap="wrap">
            <Chip
              label={`Total Requests: ${stats.total}`}
              variant="outlined"
            />
            <Chip
              label={`Fully Produced: ${stats.fullyProduced}`}
              color="success"
              variant="outlined"
              icon={<Typography fontSize="small">✅</Typography>}
            />
            <Chip
              label={`Partially Produced: ${stats.partiallyProduced}`}
              color="warning"
              variant="outlined"
              icon={<Typography fontSize="small">⚠️</Typography>}
            />
            <Chip
              label={`Not Produced: ${stats.notProduced}`}
              color="error"
              variant="outlined"
              icon={<Typography fontSize="small">❌</Typography>}
            />
          </Box>
        </Box>

        {stats.notProduced > 0 && (
          <Alert severity="warning" sx={{ mt: 2 }}>
            {stats.notProduced} request{stats.notProduced > 1 ? 's' : ''} {stats.notProduced > 1 ? 'were' : 'was'} not produced. 
            Consider sending a good faith letter outlining these deficiencies.
          </Alert>
        )}
      </Paper>

      {(editMode ? editedReport.analyses : report.analyses).map((analysis, index) => (
        <Accordion 
          key={analysis.request_number} 
          defaultExpanded={analysis.status !== ProductionStatus.FULLY_PRODUCED}
        >
          <AccordionSummary expandIcon={<ExpandMoreIcon />}>
            <Box display="flex" alignItems="center" width="100%" gap={2}>
              <Typography variant="h6" sx={{ flexGrow: 0 }}>
                {getStatusIcon(analysis.status)} Request {analysis.request_number}
              </Typography>
              <Box sx={{ flexGrow: 1 }} />
              <Chip
                label={analysis.status.replace('_', ' ').toUpperCase()}
                color={getStatusColor(analysis.status)}
                size="small"
              />
              <Typography variant="caption" color="text.secondary">
                Confidence: {analysis.confidence}%
              </Typography>
            </Box>
          </AccordionSummary>
          <AccordionDetails>
            <RequestAnalysisView
              analysis={analysis}
              editable={editMode}
              onUpdate={(updated) => handleAnalysisUpdate(index, updated)}
            />
          </AccordionDetails>
        </Accordion>
      ))}

      {report.analyses.length === 0 && (
        <Paper sx={{ p: 4, textAlign: 'center' }}>
          <Typography color="text.secondary">
            No requests found in the RFP document.
          </Typography>
        </Paper>
      )}
    </Box>
  );
};

export default DeficiencyReportViewer;