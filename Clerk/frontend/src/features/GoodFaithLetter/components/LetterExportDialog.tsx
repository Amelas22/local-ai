import React, { useState } from 'react';
import {
  Dialog,
  DialogTitle,
  DialogContent,
  DialogActions,
  Button,
  Box,
  Typography,
  RadioGroup,
  Radio,
  Alert,
  CircularProgress,
  Stack,
  Paper,
  IconButton,
  List,
  ListItem,
  ListItemIcon,
  ListItemText,
  ListItemSecondaryAction
} from '@mui/material';
import {
  Close as CloseIcon,
  PictureAsPdf as PdfIcon,
  Description as WordIcon,
  Download as DownloadIcon,
  CheckCircle as CheckCircleIcon,
  Error as ErrorIcon
} from '@mui/icons-material';
import { useMutation } from '@tanstack/react-query';
import { goodFaithLetterAPI } from '../../../services/api/goodFaithLetter';
import { ExportFormat, GeneratedLetter } from '../../../types/goodFaithLetter.types';

interface LetterExportDialogProps {
  open: boolean;
  onClose: () => void;
  letter: GeneratedLetter;
}

interface ExportOption {
  format: ExportFormat['format'];
  label: string;
  icon: React.ReactNode;
  description: string;
  recommended?: boolean;
}

const exportOptions: ExportOption[] = [
  {
    format: 'pdf',
    label: 'PDF Document',
    icon: <PdfIcon color="error" />,
    description: 'Best for printing and official records',
    recommended: true
  },
  {
    format: 'docx',
    label: 'Word Document',
    icon: <WordIcon color="primary" />,
    description: 'Editable format for further modifications'
  }
];

const generateFileName = (letter: GeneratedLetter, format: string): string => {
  const date = new Date().toISOString().split('T')[0];
  const caseName = letter.case_name.replace(/[^a-zA-Z0-9]/g, '_');
  return `Good_Faith_Letter_${caseName}_${date}.${format}`;
};

export const LetterExportDialog: React.FC<LetterExportDialogProps> = ({ 
  open, 
  onClose, 
  letter 
}) => {
  const [selectedFormat, setSelectedFormat] = useState<ExportFormat['format']>('pdf');
  const [exportStatus, setExportStatus] = useState<'idle' | 'success' | 'error'>('idle');

  const exportMutation = useMutation({
    mutationFn: async (format: ExportFormat['format']) => {
      const blob = await goodFaithLetterAPI.exportLetter(letter.id, format);
      return { blob, format };
    },
    onSuccess: ({ blob, format }) => {
      // Create download link
      const url = window.URL.createObjectURL(blob);
      const link = document.createElement('a');
      link.href = url;
      link.download = generateFileName(letter, format);
      document.body.appendChild(link);
      link.click();
      document.body.removeChild(link);
      window.URL.revokeObjectURL(url);
      
      setExportStatus('success');
      setTimeout(() => {
        setExportStatus('idle');
        onClose();
      }, 2000);
    },
    onError: () => {
      setExportStatus('error');
      setTimeout(() => {
        setExportStatus('idle');
      }, 3000);
    }
  });

  const handleExport = () => {
    if (letter.status !== 'finalized' && letter.status !== 'approved') {
      const confirmExport = window.confirm(
        'This letter is still in draft/review status. Are you sure you want to export it?'
      );
      if (!confirmExport) return;
    }
    
    exportMutation.mutate(selectedFormat);
  };

  const handleClose = () => {
    if (!exportMutation.isPending) {
      onClose();
      setExportStatus('idle');
    }
  };

  return (
    <Dialog 
      open={open} 
      onClose={handleClose}
      maxWidth="sm"
      fullWidth
      PaperProps={{
        sx: { borderRadius: 2 }
      }}
    >
      <DialogTitle>
        <Box display="flex" justifyContent="space-between" alignItems="center">
          <Typography variant="h6">Export Good Faith Letter</Typography>
          <IconButton
            edge="end"
            color="inherit"
            onClick={handleClose}
            disabled={exportMutation.isPending}
            size="small"
          >
            <CloseIcon />
          </IconButton>
        </Box>
      </DialogTitle>

      <DialogContent dividers>
        <Stack spacing={3}>
          {letter.status === 'draft' && (
            <Alert severity="warning" icon={<ErrorIcon />}>
              This letter is still in draft status. Consider finalizing it before sending to opposing counsel.
            </Alert>
          )}

          {exportStatus === 'success' && (
            <Alert severity="success" icon={<CheckCircleIcon />}>
              Letter exported successfully!
            </Alert>
          )}

          {exportStatus === 'error' && (
            <Alert severity="error" icon={<ErrorIcon />}>
              Failed to export letter. Please try again.
            </Alert>
          )}

          <Box>
            <Typography variant="subtitle1" gutterBottom fontWeight="medium">
              Select Export Format
            </Typography>
            <RadioGroup
              value={selectedFormat}
              onChange={(e) => setSelectedFormat(e.target.value as ExportFormat['format'])}
            >
              <List>
                {exportOptions.map((option) => (
                  <ListItem
                    key={option.format}
                    component={Paper}
                    variant="outlined"
                    sx={{
                      mb: 1.5,
                      cursor: 'pointer',
                      border: selectedFormat === option.format ? 2 : 1,
                      borderColor: selectedFormat === option.format ? 'primary.main' : 'divider',
                      transition: 'all 0.2s',
                      '&:hover': {
                        borderColor: 'primary.light',
                        bgcolor: 'action.hover'
                      }
                    }}
                    onClick={() => setSelectedFormat(option.format)}
                  >
                    <ListItemIcon>{option.icon}</ListItemIcon>
                    <ListItemText
                      primary={
                        <Box display="flex" alignItems="center" gap={1}>
                          <Typography variant="body1">{option.label}</Typography>
                          {option.recommended && (
                            <Typography
                              variant="caption"
                              sx={{
                                px: 1,
                                py: 0.25,
                                bgcolor: 'success.light',
                                color: 'success.dark',
                                borderRadius: 1,
                                fontWeight: 'medium'
                              }}
                            >
                              Recommended
                            </Typography>
                          )}
                        </Box>
                      }
                      secondary={option.description}
                    />
                    <ListItemSecondaryAction>
                      <Radio
                        value={option.format}
                        checked={selectedFormat === option.format}
                        onClick={(e) => e.stopPropagation()}
                      />
                    </ListItemSecondaryAction>
                  </ListItem>
                ))}
              </List>
            </RadioGroup>
          </Box>

          <Paper variant="outlined" sx={{ p: 2, bgcolor: 'grey.50' }}>
            <Typography variant="body2" color="text.secondary">
              <strong>Letter Details:</strong>
              <br />
              Case: {letter.case_name}
              <br />
              Jurisdiction: {letter.jurisdiction}
              <br />
              Version: {letter.version}
              <br />
              Status: {letter.status}
            </Typography>
          </Paper>
        </Stack>
      </DialogContent>

      <DialogActions sx={{ px: 3, py: 2 }}>
        <Button 
          onClick={handleClose}
          disabled={exportMutation.isPending}
        >
          Cancel
        </Button>
        <Button
          variant="contained"
          onClick={handleExport}
          disabled={exportMutation.isPending || exportStatus === 'success'}
          startIcon={
            exportMutation.isPending ? (
              <CircularProgress size={20} color="inherit" />
            ) : (
              <DownloadIcon />
            )
          }
        >
          {exportMutation.isPending ? 'Exporting...' : 'Export'}
        </Button>
      </DialogActions>
    </Dialog>
  );
};