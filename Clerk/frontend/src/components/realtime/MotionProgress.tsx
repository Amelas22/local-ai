import { ReactElement, useEffect, useState } from 'react';
import {
  Box,
  Card,
  CardContent,
  Typography,
  LinearProgress,
  Stepper,
  Step,
  StepLabel,
  StepContent,
  Alert,
  Chip,
  Button,
  Stack
} from '@mui/material';
import {
  Gavel as MotionIcon,
  CheckCircle as CheckIcon,
  Error as ErrorIcon,
  Download as DownloadIcon,
  Timer as TimerIcon
} from '@mui/icons-material';
import { useWebSocket } from '../../hooks/useWebSocket';

interface MotionProgressProps {
  caseId: string;
  motionId?: string;
}

interface MotionState {
  motionId: string | null;
  motionType: string | null;
  currentStep: number;
  progress: number;
  completedSections: string[];
  downloadUrl: string | null;
  error: string | null;
  startTime: Date | null;
  endTime: Date | null;
}

const MOTION_STEPS = [
  'Analyzing Motion Requirements',
  'Generating Outline',
  'Drafting Introduction',
  'Drafting Arguments',
  'Adding Citations',
  'Finalizing Motion'
];

export function MotionProgress({ caseId, motionId }: MotionProgressProps): ReactElement {
  const [motionState, setMotionState] = useState<MotionState>({
    motionId: null,
    motionType: null,
    currentStep: -1,
    progress: 0,
    completedSections: [],
    downloadUrl: null,
    error: null,
    startTime: null,
    endTime: null
  });

  const { on } = useWebSocket(caseId);

  useEffect(() => {
    // Listen for motion events
    const unsubscribeStarted = on('motion:started', (data) => {
      if (!motionId || data.motionId === motionId) {
        setMotionState(prev => ({
          ...prev,
          motionId: data.motionId,
          motionType: data.type,
          currentStep: 0,
          startTime: new Date(),
          error: null
        }));
      }
    });

    const unsubscribeOutlineStarted = on('motion:outline_started', (data) => {
      if (!motionId || data.motionId === motionId) {
        setMotionState(prev => ({
          ...prev,
          currentStep: 1,
          progress: 10
        }));
      }
    });

    const unsubscribeOutlineCompleted = on('motion:outline_completed', (data) => {
      if (!motionId || data.motionId === motionId) {
        setMotionState(prev => ({
          ...prev,
          currentStep: 2,
          progress: 20
        }));
      }
    });

    const unsubscribeSectionCompleted = on('motion:section_completed', (data) => {
      if (!motionId || data.motionId === motionId) {
        setMotionState(prev => ({
          ...prev,
          completedSections: [...prev.completedSections, data.section],
          progress: Math.min(prev.progress + 15, 90)
        }));
      }
    });

    const unsubscribeCompleted = on('motion:completed', (data) => {
      if (!motionId || data.motionId === motionId) {
        setMotionState(prev => ({
          ...prev,
          currentStep: MOTION_STEPS.length,
          progress: 100,
          downloadUrl: data.downloadUrl,
          endTime: new Date()
        }));
      }
    });

    const unsubscribeError = on('motion:error', (data) => {
      if (!motionId || data.motionId === motionId) {
        setMotionState(prev => ({
          ...prev,
          error: data.error
        }));
      }
    });

    return () => {
      unsubscribeStarted();
      unsubscribeOutlineStarted();
      unsubscribeOutlineCompleted();
      unsubscribeSectionCompleted();
      unsubscribeCompleted();
      unsubscribeError();
    };
  }, [on, motionId]);

  // Calculate elapsed time
  const getElapsedTime = () => {
    if (!motionState.startTime) return '';
    const end = motionState.endTime || new Date();
    const elapsed = Math.floor((end.getTime() - motionState.startTime.getTime()) / 1000);
    const minutes = Math.floor(elapsed / 60);
    const seconds = elapsed % 60;
    return `${minutes}:${seconds.toString().padStart(2, '0')}`;
  };

  if (motionState.currentStep === -1) {
    return <Box />;
  }

  const isComplete = motionState.progress === 100;
  const hasError = Boolean(motionState.error);

  return (
    <Card sx={{ mb: 2 }}>
      <CardContent>
        <Box display="flex" justifyContent="space-between" alignItems="center" mb={2}>
          <Box display="flex" alignItems="center" gap={1}>
            <MotionIcon color="primary" />
            <Typography variant="h6" component="h3">
              Motion Drafting
            </Typography>
            {motionState.motionType && (
              <Chip label={motionState.motionType} size="small" color="primary" variant="outlined" />
            )}
          </Box>
          {motionState.startTime && (
            <Chip
              icon={<TimerIcon />}
              label={getElapsedTime()}
              size="small"
              variant="outlined"
            />
          )}
        </Box>

        {/* Progress Bar */}
        <Box mb={3}>
          <Box display="flex" justifyContent="space-between" mb={1}>
            <Typography variant="body2" color="text.secondary">
              Progress
            </Typography>
            <Typography variant="body2" color="text.secondary">
              {motionState.progress}%
            </Typography>
          </Box>
          <LinearProgress
            variant="determinate"
            value={motionState.progress}
            sx={{ height: 8, borderRadius: 1 }}
            color={hasError ? 'error' : isComplete ? 'success' : 'primary'}
          />
        </Box>

        {/* Stepper */}
        <Stepper activeStep={motionState.currentStep} orientation="vertical">
          {MOTION_STEPS.map((step, index) => (
            <Step key={step} completed={index < motionState.currentStep}>
              <StepLabel
                error={hasError && index === motionState.currentStep}
                StepIconComponent={() => {
                  if (index < motionState.currentStep) return <CheckIcon color="success" />;
                  if (hasError && index === motionState.currentStep) return <ErrorIcon color="error" />;
                  return <Box>{index + 1}</Box>;
                }}
              >
                {step}
              </StepLabel>
              <StepContent>
                {index === motionState.currentStep && !hasError && (
                  <Typography variant="body2" color="text.secondary">
                    Processing...
                  </Typography>
                )}
              </StepContent>
            </Step>
          ))}
        </Stepper>

        {/* Completed Sections */}
        {motionState.completedSections.length > 0 && (
          <Box mt={2}>
            <Typography variant="subtitle2" gutterBottom>
              Completed Sections:
            </Typography>
            <Stack direction="row" spacing={1} flexWrap="wrap">
              {motionState.completedSections.map((section, index) => (
                <Chip
                  key={index}
                  label={section}
                  size="small"
                  color="success"
                  variant="outlined"
                />
              ))}
            </Stack>
          </Box>
        )}

        {/* Error Alert */}
        {hasError && (
          <Alert severity="error" sx={{ mt: 2 }}>
            {motionState.error}
          </Alert>
        )}

        {/* Download Button */}
        {isComplete && motionState.downloadUrl && (
          <Box mt={2}>
            <Button
              variant="contained"
              color="success"
              startIcon={<DownloadIcon />}
              href={motionState.downloadUrl}
              target="_blank"
              fullWidth
            >
              Download Motion
            </Button>
          </Box>
        )}
      </CardContent>
    </Card>
  );
}