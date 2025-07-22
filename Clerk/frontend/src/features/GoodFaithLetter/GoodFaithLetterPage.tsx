import React, { useState, useEffect } from 'react';
import {
  Box,
  Container,
  Paper,
  Tabs,
  Tab,
  Typography,
  CircularProgress,
  Alert,
  Breadcrumbs,
  Link,
  Button,
  Stack,
  IconButton,
  Tooltip
} from '@mui/material';
import {
  Preview as PreviewIcon,
  Edit as EditIcon,
  Download as DownloadIcon,
  History as HistoryIcon,
  Email as EmailIcon,
  ArrowBack as ArrowBackIcon,
  Refresh as RefreshIcon
} from '@mui/icons-material';
import { useParams, useNavigate, Link as RouterLink } from 'react-router-dom';
import { useQuery, useQueryClient } from '@tanstack/react-query';
import { useWebSocket } from '../../hooks/useWebSocket';
import { goodFaithLetterAPI } from '../../services/api/goodFaithLetter';
import { LetterPreview } from './components/LetterPreview';
import { LetterEditor } from './components/LetterEditor';
import { LetterExportDialog } from './components/LetterExportDialog';
import { LetterVersionHistory } from './components/LetterVersionHistory';
import { EmailPreparation } from './components/EmailPreparation';
import { 
  LetterUpdateEvent, 
  LetterFinalizedEvent
} from '../../types/goodFaithLetter.types';

interface TabPanelProps {
  children?: React.ReactNode;
  index: number;
  value: number;
}

const TabPanel: React.FC<TabPanelProps> = ({ children, value, index, ...other }) => {
  return (
    <div
      role="tabpanel"
      hidden={value !== index}
      id={`letter-tabpanel-${index}`}
      aria-labelledby={`letter-tab-${index}`}
      {...other}
    >
      {value === index && <Box sx={{ py: 3 }}>{children}</Box>}
    </div>
  );
};

const a11yProps = (index: number) => {
  return {
    id: `letter-tab-${index}`,
    'aria-controls': `letter-tabpanel-${index}`,
  };
};

export const GoodFaithLetterPage: React.FC = () => {
  const { letterId } = useParams<{ letterId: string }>();
  const navigate = useNavigate();
  const queryClient = useQueryClient();
  const { on, emit } = useWebSocket();
  
  const [activeTab, setActiveTab] = useState(0);
  const [exportDialogOpen, setExportDialogOpen] = useState(false);
  const [currentVersion, setCurrentVersion] = useState<number>(1);

  const { 
    data: letter, 
    isLoading, 
    error, 
    refetch 
  } = useQuery({
    queryKey: ['letter', letterId],
    queryFn: () => goodFaithLetterAPI.getLetter(letterId!),
    enabled: !!letterId,
    refetchInterval: (data) => {
      // Refetch more frequently for draft letters
      if (data && 'status' in data && (data.status === 'draft' || data.status === 'review')) {
        return 10000; // 10 seconds
      }
      return false;
    }
  });

  // WebSocket event handlers
  useEffect(() => {
    if (!letterId) return;

    const handleLetterUpdate = (data: LetterUpdateEvent) => {
      if (data.letter_id === letterId) {
        queryClient.invalidateQueries({ queryKey: ['letter', letterId] });
      }
    };

    const handleLetterFinalized = (data: LetterFinalizedEvent) => {
      if (data.letter_id === letterId) {
        queryClient.invalidateQueries({ queryKey: ['letter', letterId] });
        // Move to preview tab when finalized
        setActiveTab(0);
      }
    };

    const unsubscribe1 = on('letter:customization_applied', handleLetterUpdate);
    const unsubscribe2 = on('letter:finalized', handleLetterFinalized);
    const unsubscribe3 = on('letter:version_restored', handleLetterUpdate);

    return () => {
      unsubscribe1();
      unsubscribe2();
      unsubscribe3();
    };
  }, [letterId, on, queryClient]);

  useEffect(() => {
    if (letter) {
      setCurrentVersion(letter.version);
    }
  }, [letter]);

  const handleTabChange = (_event: React.SyntheticEvent, newValue: number) => {
    setActiveTab(newValue);
  };

  const handleVersionChange = (newVersion: number) => {
    setCurrentVersion(newVersion);
    refetch();
  };

  const handleExportClick = () => {
    setExportDialogOpen(true);
  };

  const handleSendEmail = (emailData: { recipients: string[] }) => {
    // In a real implementation, this would call an API to send the email
    // TODO: Implement actual email sending logic
    emit('letter:email_sent', { 
      letter_id: letterId!, 
      recipients: emailData.recipients 
    });
  };

  const handleSaveDraft = (_emailData: { recipients: string[] }) => {
    // In a real implementation, this would save the email draft
    // TODO: Implement email draft saving logic
    // For now, we'll just store it locally or show a success message
  };

  if (!letterId) {
    return (
      <Container>
        <Alert severity="error">No letter ID provided</Alert>
      </Container>
    );
  }

  if (isLoading) {
    return (
      <Box display="flex" justifyContent="center" alignItems="center" minHeight="60vh">
        <CircularProgress size={60} />
      </Box>
    );
  }

  if (error || !letter) {
    return (
      <Container>
        <Alert severity="error" action={
          <Button color="inherit" size="small" onClick={() => refetch()}>
            Retry
          </Button>
        }>
          Failed to load letter. Please try again.
        </Alert>
      </Container>
    );
  }

  const canEdit = letter.status === 'draft' || letter.status === 'review';

  return (
    <Container maxWidth="lg" sx={{ py: 3 }}>
      <Stack spacing={3}>
        {/* Header */}
        <Box>
          <Breadcrumbs aria-label="breadcrumb" sx={{ mb: 2 }}>
            <Link component={RouterLink} to="/deficiency" color="inherit">
              Deficiency Analysis
            </Link>
            <Link component={RouterLink} to={`/deficiency/report/${letter.report_id}`} color="inherit">
              Deficiency Report
            </Link>
            <Typography color="text.primary">Good Faith Letter</Typography>
          </Breadcrumbs>

          <Box display="flex" justifyContent="space-between" alignItems="center">
            <Stack direction="row" spacing={2} alignItems="center">
              <IconButton onClick={() => navigate(-1)}>
                <ArrowBackIcon />
              </IconButton>
              <Typography variant="h4">
                Good Faith Letter
              </Typography>
            </Stack>

            <Stack direction="row" spacing={1}>
              <Tooltip title="Refresh">
                <IconButton onClick={() => refetch()}>
                  <RefreshIcon />
                </IconButton>
              </Tooltip>
              <Button
                variant="outlined"
                startIcon={<DownloadIcon />}
                onClick={handleExportClick}
              >
                Export
              </Button>
            </Stack>
          </Box>
        </Box>

        {/* Tabs */}
        <Paper elevation={1}>
          <Tabs
            value={activeTab}
            onChange={handleTabChange}
            variant="scrollable"
            scrollButtons="auto"
            sx={{ borderBottom: 1, borderColor: 'divider' }}
          >
            <Tab 
              label="Preview" 
              icon={<PreviewIcon />} 
              iconPosition="start"
              {...a11yProps(0)} 
            />
            <Tab 
              label="Edit" 
              icon={<EditIcon />} 
              iconPosition="start"
              {...a11yProps(1)}
              disabled={!canEdit}
            />
            <Tab 
              label="Version History" 
              icon={<HistoryIcon />} 
              iconPosition="start"
              {...a11yProps(2)} 
            />
            <Tab 
              label="Email" 
              icon={<EmailIcon />} 
              iconPosition="start"
              {...a11yProps(3)} 
            />
          </Tabs>

          {/* Tab Panels */}
          <Box sx={{ minHeight: '60vh' }}>
            <TabPanel value={activeTab} index={0}>
              <LetterPreview letterId={letterId} />
            </TabPanel>

            <TabPanel value={activeTab} index={1}>
              {canEdit ? (
                <LetterEditor 
                  letterId={letterId} 
                  onVersionChange={handleVersionChange}
                />
              ) : (
                <Alert severity="info">
                  This letter cannot be edited in its current status ({letter.status}).
                </Alert>
              )}
            </TabPanel>

            <TabPanel value={activeTab} index={2}>
              <LetterVersionHistory 
                letterId={letterId}
                currentVersion={currentVersion}
                onVersionRestore={handleVersionChange}
              />
            </TabPanel>

            <TabPanel value={activeTab} index={3}>
              <EmailPreparation 
                letter={letter}
                onSendEmail={handleSendEmail}
                onSaveDraft={handleSaveDraft}
              />
            </TabPanel>
          </Box>
        </Paper>
      </Stack>

      {/* Export Dialog */}
      <LetterExportDialog
        open={exportDialogOpen}
        onClose={() => setExportDialogOpen(false)}
        letter={letter}
      />
    </Container>
  );
};