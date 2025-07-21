import React, { useEffect } from 'react';
import { Box, Paper, CircularProgress, Alert } from '@mui/material';
import { DeficiencyReportHeader } from './DeficiencyReportHeader';
import { DeficiencyItemList } from './DeficiencyItemList';
import { BulkActionsBar } from './BulkActionsBar';
import { useDeficiencyReport } from '../hooks/useDeficiencyReport';
import { useDeficiencyUpdates } from '../hooks/useDeficiencyUpdates';
import { useDeficiencyUIStore } from '../stores/deficiencyUIStore';
import '../styles/print.css';

interface DeficiencyReportViewProps {
  reportId: string;
}

export const DeficiencyReportView: React.FC<DeficiencyReportViewProps> = ({ reportId }) => {
  const { data: report, isLoading, error, refetch } = useDeficiencyReport(reportId);
  const { selectedItems, clearSelection } = useDeficiencyUIStore();
  
  useDeficiencyUpdates(reportId, refetch);

  useEffect(() => {
    return () => {
      clearSelection();
    };
  }, [clearSelection]);

  if (isLoading) {
    return (
      <Box display="flex" justifyContent="center" alignItems="center" minHeight="400px">
        <CircularProgress />
      </Box>
    );
  }

  if (error) {
    return (
      <Box p={3}>
        <Alert severity="error">
          Failed to load deficiency report. Please try again later.
        </Alert>
      </Box>
    );
  }

  if (!report || report.deficiency_items.length === 0) {
    return (
      <Box p={3}>
        <Alert severity="info">
          No deficiency items found in this report.
        </Alert>
      </Box>
    );
  }

  return (
    <Paper elevation={0}>
      <DeficiencyReportHeader report={report} />
      
      {selectedItems.size > 0 && (
        <BulkActionsBar
          selectedCount={selectedItems.size}
          reportId={reportId}
          onComplete={refetch}
        />
      )}
      
      <DeficiencyItemList
        items={report.deficiency_items}
        reportId={reportId}
        onItemUpdate={refetch}
      />
    </Paper>
  );
};