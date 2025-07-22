import React, { useState } from 'react';
import {
  Box,
  Paper,
  Typography,
  IconButton,
  Chip,
  Button,
  Dialog,
  DialogTitle,
  DialogContent,
  DialogActions,
  Alert,
  CircularProgress,
  Divider,
  Stack,
  Tooltip,
  Card,
  CardContent
} from '@mui/material';
import {
  Timeline,
  TimelineItem,
  TimelineSeparator,
  TimelineConnector,
  TimelineContent,
  TimelineDot,
  TimelineOppositeContent
} from '@mui/lab';
import {
  Restore as RestoreIcon,
  Compare as CompareIcon,
  Person as PersonIcon,
  Edit as EditIcon,
  Check as CheckIcon,
  History as HistoryIcon
} from '@mui/icons-material';
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';
import { goodFaithLetterAPI } from '../../../services/api/goodFaithLetter';
import { LetterEdit } from '../../../types/goodFaithLetter.types';
import { format, formatDistanceToNow } from 'date-fns';

interface LetterVersionHistoryProps {
  letterId: string;
  currentVersion: number;
  onVersionRestore?: (version: number) => void;
}

interface VersionComparisonDialogProps {
  open: boolean;
  onClose: () => void;
  version1: LetterEdit | null;
  version2: LetterEdit | null;
}

const VersionComparisonDialog: React.FC<VersionComparisonDialogProps> = ({
  open,
  onClose,
  version1,
  version2
}) => {
  if (!version1 || !version2) return null;

  const renderSectionChanges = () => {
    const allSections = new Set([
      ...version1.section_edits.map(e => e.section),
      ...version2.section_edits.map(e => e.section)
    ]);

    return Array.from(allSections).map(section => {
      const v1Edit = version1.section_edits.find(e => e.section === section);
      const v2Edit = version2.section_edits.find(e => e.section === section);

      if (!v1Edit && !v2Edit) return null;

      return (
        <Card key={section} variant="outlined" sx={{ mb: 2 }}>
          <CardContent>
            <Typography variant="subtitle2" gutterBottom>
              {section.charAt(0).toUpperCase() + section.slice(1)} Section
            </Typography>
            <Stack direction="row" spacing={2} divider={<Divider orientation="vertical" flexItem />}>
              <Box flex={1}>
                <Typography variant="caption" color="text.secondary">
                  Version {version1.version}
                </Typography>
                <Typography variant="body2" sx={{ mt: 1, whiteSpace: 'pre-wrap' }}>
                  {v1Edit?.content || '(No changes in this version)'}
                </Typography>
              </Box>
              <Box flex={1}>
                <Typography variant="caption" color="text.secondary">
                  Version {version2.version}
                </Typography>
                <Typography variant="body2" sx={{ mt: 1, whiteSpace: 'pre-wrap' }}>
                  {v2Edit?.content || '(No changes in this version)'}
                </Typography>
              </Box>
            </Stack>
          </CardContent>
        </Card>
      );
    }).filter(Boolean);
  };

  return (
    <Dialog open={open} onClose={onClose} maxWidth="lg" fullWidth>
      <DialogTitle>
        Version Comparison: v{version1.version} vs v{version2.version}
      </DialogTitle>
      <DialogContent dividers>
        <Stack spacing={2}>
          <Alert severity="info">
            Showing section-by-section changes between versions
          </Alert>
          {renderSectionChanges()}
        </Stack>
      </DialogContent>
      <DialogActions>
        <Button onClick={onClose}>Close</Button>
      </DialogActions>
    </Dialog>
  );
};

export const LetterVersionHistory: React.FC<LetterVersionHistoryProps> = ({
  letterId,
  currentVersion,
  onVersionRestore
}) => {
  const queryClient = useQueryClient();
  const [selectedVersions, setSelectedVersions] = useState<number[]>([]);
  const [compareDialogOpen, setCompareDialogOpen] = useState(false);
  const [restoreDialogOpen, setRestoreDialogOpen] = useState(false);
  const [versionToRestore, setVersionToRestore] = useState<number | null>(null);

  const { data: versions, isLoading, error } = useQuery({
    queryKey: ['letter-versions', letterId],
    queryFn: () => goodFaithLetterAPI.getLetterVersions(letterId),
  });

  const { data: letter } = useQuery({
    queryKey: ['letter', letterId],
    queryFn: () => goodFaithLetterAPI.getLetter(letterId),
  });

  const restoreMutation = useMutation({
    mutationFn: (version: number) => goodFaithLetterAPI.restoreVersion(letterId, version),
    onSuccess: (restoredLetter) => {
      queryClient.setQueryData(['letter', letterId], restoredLetter);
      queryClient.invalidateQueries({ queryKey: ['letter-versions', letterId] });
      setRestoreDialogOpen(false);
      setVersionToRestore(null);
      if (onVersionRestore) {
        onVersionRestore(restoredLetter.version);
      }
    },
  });

  const handleVersionSelect = (version: number) => {
    if (selectedVersions.includes(version)) {
      setSelectedVersions(prev => prev.filter(v => v !== version));
    } else if (selectedVersions.length < 2) {
      setSelectedVersions(prev => [...prev, version]);
    } else {
      setSelectedVersions([selectedVersions[1], version]);
    }
  };

  const handleCompare = () => {
    if (selectedVersions.length === 2) {
      setCompareDialogOpen(true);
    }
  };

  const handleRestoreClick = (version: number) => {
    setVersionToRestore(version);
    setRestoreDialogOpen(true);
  };

  const handleRestoreConfirm = () => {
    if (versionToRestore) {
      restoreMutation.mutate(versionToRestore);
    }
  };

  const getVersionStatus = (version: LetterEdit): string => {
    if (version.version === currentVersion) return 'current';
    if (version.version === 1) return 'initial';
    return 'past';
  };

  if (isLoading) {
    return (
      <Box display="flex" justifyContent="center" alignItems="center" minHeight="300px">
        <CircularProgress />
      </Box>
    );
  }

  if (error || !versions) {
    return (
      <Alert severity="error">
        Failed to load version history. Please try again later.
      </Alert>
    );
  }

  if (versions.length === 0) {
    return (
      <Alert severity="info">
        No version history available yet.
      </Alert>
    );
  }

  const selectedVersionObjects = versions.filter(v => selectedVersions.includes(v.version));

  return (
    <Paper elevation={2} sx={{ p: 3 }}>
      <Stack spacing={3}>
        <Box display="flex" justifyContent="space-between" alignItems="center">
          <Typography variant="h6" display="flex" alignItems="center" gap={1}>
            <HistoryIcon />
            Version History
          </Typography>
          <Button
            variant="outlined"
            startIcon={<CompareIcon />}
            onClick={handleCompare}
            disabled={selectedVersions.length !== 2}
          >
            Compare Selected ({selectedVersions.length}/2)
          </Button>
        </Box>

        <Divider />

        <Timeline position="alternate">
          {versions.map((version, index) => {
            const status = getVersionStatus(version);
            const isSelected = selectedVersions.includes(version.version);
            
            return (
              <TimelineItem key={version.id}>
                <TimelineOppositeContent color="text.secondary">
                  <Typography variant="caption">
                    {format(new Date(version.edit_timestamp), 'MMM d, yyyy')}
                  </Typography>
                  <br />
                  <Typography variant="caption">
                    {format(new Date(version.edit_timestamp), 'h:mm a')}
                  </Typography>
                </TimelineOppositeContent>
                
                <TimelineSeparator>
                  <TimelineDot
                    color={status === 'current' ? 'primary' : 'grey'}
                    variant={status === 'current' ? 'filled' : 'outlined'}
                  >
                    {status === 'current' ? <CheckIcon /> : <EditIcon />}
                  </TimelineDot>
                  {index < versions.length - 1 && <TimelineConnector />}
                </TimelineSeparator>
                
                <TimelineContent>
                  <Card
                    variant={isSelected ? 'elevation' : 'outlined'}
                    sx={{
                      bgcolor: isSelected ? 'action.selected' : 'background.paper',
                      cursor: 'pointer',
                      transition: 'all 0.2s',
                      '&:hover': {
                        bgcolor: 'action.hover'
                      }
                    }}
                    onClick={() => handleVersionSelect(version.version)}
                  >
                    <CardContent>
                      <Box display="flex" justifyContent="space-between" alignItems="start">
                        <Box>
                          <Typography variant="subtitle1" fontWeight="medium">
                            Version {version.version}
                            {status === 'current' && (
                              <Chip
                                size="small"
                                label="Current"
                                color="primary"
                                sx={{ ml: 1 }}
                              />
                            )}
                          </Typography>
                          
                          <Typography variant="body2" color="text.secondary" sx={{ mt: 0.5 }}>
                            <PersonIcon sx={{ fontSize: 16, verticalAlign: 'middle', mr: 0.5 }} />
                            {version.editor_name}
                          </Typography>
                          
                          {version.edit_notes && (
                            <Typography variant="body2" sx={{ mt: 1, fontStyle: 'italic' }}>
                              "{version.edit_notes}"
                            </Typography>
                          )}
                          
                          <Typography variant="caption" color="text.secondary" sx={{ mt: 1, display: 'block' }}>
                            {version.section_edits.length} section{version.section_edits.length !== 1 ? 's' : ''} edited
                            {' • '}
                            {formatDistanceToNow(new Date(version.edit_timestamp), { addSuffix: true })}
                          </Typography>
                        </Box>
                        
                        {status !== 'current' && (
                          <Tooltip title="Restore this version">
                            <IconButton
                              size="small"
                              onClick={(e) => {
                                e.stopPropagation();
                                handleRestoreClick(version.version);
                              }}
                              disabled={letter?.status === 'finalized'}
                            >
                              <RestoreIcon />
                            </IconButton>
                          </Tooltip>
                        )}
                      </Box>
                    </CardContent>
                  </Card>
                </TimelineContent>
              </TimelineItem>
            );
          })}
        </Timeline>

        {letter?.status === 'finalized' && (
          <Alert severity="info">
            This letter is finalized. Version restoration is disabled.
          </Alert>
        )}
      </Stack>

      <VersionComparisonDialog
        open={compareDialogOpen}
        onClose={() => setCompareDialogOpen(false)}
        version1={selectedVersionObjects[0] || null}
        version2={selectedVersionObjects[1] || null}
      />

      <Dialog open={restoreDialogOpen} onClose={() => setRestoreDialogOpen(false)}>
        <DialogTitle>Restore Version {versionToRestore}?</DialogTitle>
        <DialogContent>
          <Alert severity="warning">
            This will create a new version based on version {versionToRestore}. 
            The current version will remain in the history.
          </Alert>
        </DialogContent>
        <DialogActions>
          <Button onClick={() => setRestoreDialogOpen(false)}>Cancel</Button>
          <Button
            variant="contained"
            onClick={handleRestoreConfirm}
            disabled={restoreMutation.isPending}
            startIcon={restoreMutation.isPending ? <CircularProgress size={20} /> : <RestoreIcon />}
          >
            {restoreMutation.isPending ? 'Restoring...' : 'Restore'}
          </Button>
        </DialogActions>
      </Dialog>
    </Paper>
  );
};