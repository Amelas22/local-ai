import { useState } from 'react';
import { useForm, Controller } from 'react-hook-form';
import {
  Box,
  TextField,
  Button,
  Grid,
  FormControl,
  InputLabel,
  Select,
  MenuItem,
  Autocomplete,
  Chip,
  FormControlLabel,
  Switch,
  Paper,
  Typography,
} from '@mui/material';
import { DatePicker } from '@mui/x-date-pickers/DatePicker';
import SendIcon from '@mui/icons-material/Send';
import { useAppDispatch } from '@/hooks/redux';
import { addToast } from '@/store/slices/uiSlice';
import { startProcessing } from '@/store/slices/discoverySlice';
import { useWebSocket } from '@/hooks/useWebSocket';
import type { DiscoveryProcessingRequest } from '@/types/discovery.types';
import { apiClient } from '@/services/utils/apiClient';

const mockCases = [
  'Smith_v_Jones_2024',
  'Johnson_v_ABC_Corp_2024',
  'Davis_v_XYZ_Transport_2024',
];

const confidentialityOptions = [
  'Not Confidential',
  'Confidential',
  'Highly Confidential',
  'Attorneys Eyes Only',
];

const responsiveRequests = [
  'RFP 1-25',
  'RFA 1-15',
  'Interrogatory 1-20',
  'RFP 26-50',
];

const DiscoveryForm = () => {
  const dispatch = useAppDispatch();
  const { connected } = useWebSocket();
  const [isSubmitting, setIsSubmitting] = useState(false);
  
  const { control, handleSubmit, formState: { errors } } = useForm<DiscoveryProcessingRequest>({
    defaultValues: {
      folder_id: '',
      case_name: '',
      production_batch: '',
      producing_party: '',
      production_date: new Date().toISOString(),
      responsive_to_requests: [],
      confidentiality_designation: 'Not Confidential',
      override_fact_extraction: true,
    },
  });

  const onSubmit = async (data: DiscoveryProcessingRequest) => {
    setIsSubmitting(true);
    try {
      // Check WebSocket connection
      if (!connected) {
        dispatch(addToast({
          message: 'WebSocket not connected. Please refresh the page.',
          severity: 'warning',
        }));
      }
      
      // Call the API endpoint with retry logic
      // When running in production, always use the real endpoint
      const endpoint = '/discovery/process';
      
      const response = await apiClient.post(endpoint, data, {
        retries: 3,
        retryDelay: 2000,
        retryCondition: (error) => {
          // Retry on network errors, 5xx errors, or specific 4xx errors
          return !error.response || 
                 (error.response.status >= 500) ||
                 (error.response.status === 408) || // Request timeout
                 (error.response.status === 429);   // Too many requests
        }
      });
      
      // The processing ID will be used to track this specific job
      const processingId = response.data.processing_id;
      
      // Update local state to show processing has started
      dispatch(startProcessing(processingId));
      
      dispatch(addToast({
        message: 'Discovery processing started successfully',
        severity: 'success',
      }));
    } catch (error: any) {
      console.error('Error starting discovery processing:', error);
      dispatch(addToast({
        message: error.response?.data?.detail || 'Failed to start discovery processing',
        severity: 'error',
      }));
    } finally {
      setIsSubmitting(false);
    }
  };

  return (
    <Paper sx={{ p: 3 }}>
      <Typography variant="h6" gutterBottom>
        New Discovery Production
      </Typography>
      
      <form onSubmit={handleSubmit(onSubmit)}>
        <Grid container spacing={3}>
          <Grid item xs={12} md={6}>
            <Controller
              name="folder_id"
              control={control}
              rules={{ required: 'Folder ID is required' }}
              render={({ field }) => (
                <TextField
                  {...field}
                  label="Box Folder ID"
                  fullWidth
                  error={!!errors.folder_id}
                  helperText={errors.folder_id?.message}
                  placeholder="123456789"
                />
              )}
            />
          </Grid>
          
          <Grid item xs={12} md={6}>
            <Controller
              name="case_name"
              control={control}
              rules={{ required: 'Case name is required' }}
              render={({ field }) => (
                <Autocomplete
                  {...field}
                  options={mockCases}
                  freeSolo
                  onChange={(_, value) => field.onChange(value)}
                  renderInput={(params) => (
                    <TextField
                      {...params}
                      label="Case Name"
                      error={!!errors.case_name}
                      helperText={errors.case_name?.message}
                    />
                  )}
                />
              )}
            />
          </Grid>
          
          <Grid item xs={12} md={6}>
            <Controller
              name="production_batch"
              control={control}
              rules={{ required: 'Production batch is required' }}
              render={({ field }) => (
                <TextField
                  {...field}
                  label="Production Batch"
                  fullWidth
                  error={!!errors.production_batch}
                  helperText={errors.production_batch?.message}
                  placeholder="Defendant's First Production"
                />
              )}
            />
          </Grid>
          
          <Grid item xs={12} md={6}>
            <Controller
              name="producing_party"
              control={control}
              rules={{ required: 'Producing party is required' }}
              render={({ field }) => (
                <TextField
                  {...field}
                  label="Producing Party"
                  fullWidth
                  error={!!errors.producing_party}
                  helperText={errors.producing_party?.message}
                  placeholder="ABC Transport Corp"
                />
              )}
            />
          </Grid>
          
          <Grid item xs={12} md={6}>
            <Controller
              name="production_date"
              control={control}
              render={({ field }) => (
                <DatePicker
                  label="Production Date"
                  value={field.value ? new Date(field.value) : null}
                  onChange={(date) => field.onChange(date?.toISOString())}
                  slotProps={{
                    textField: {
                      fullWidth: true,
                    },
                  }}
                />
              )}
            />
          </Grid>
          
          <Grid item xs={12} md={6}>
            <Controller
              name="confidentiality_designation"
              control={control}
              render={({ field }) => (
                <FormControl fullWidth>
                  <InputLabel>Confidentiality Designation</InputLabel>
                  <Select {...field} label="Confidentiality Designation">
                    {confidentialityOptions.map((option) => (
                      <MenuItem key={option} value={option}>
                        {option}
                      </MenuItem>
                    ))}
                  </Select>
                </FormControl>
              )}
            />
          </Grid>
          
          <Grid item xs={12}>
            <Controller
              name="responsive_to_requests"
              control={control}
              render={({ field }) => (
                <Autocomplete
                  {...field}
                  multiple
                  options={responsiveRequests}
                  freeSolo
                  onChange={(_, value) => field.onChange(value)}
                  renderTags={(value, getTagProps) =>
                    value.map((option, index) => (
                      <Chip
                        variant="outlined"
                        label={option}
                        {...getTagProps({ index })}
                      />
                    ))
                  }
                  renderInput={(params) => (
                    <TextField
                      {...params}
                      label="Responsive to Requests"
                      placeholder="Add request numbers..."
                    />
                  )}
                />
              )}
            />
          </Grid>
          
          <Grid item xs={12}>
            <Controller
              name="override_fact_extraction"
              control={control}
              render={({ field }) => (
                <FormControlLabel
                  control={
                    <Switch
                      {...field}
                      checked={field.value}
                      color="primary"
                    />
                  }
                  label="Force fact extraction for all documents"
                />
              )}
            />
          </Grid>
          
          <Grid item xs={12}>
            <Box sx={{ display: 'flex', gap: 2, justifyContent: 'flex-end' }}>
              <Button variant="outlined" disabled={isSubmitting}>
                Cancel
              </Button>
              <Button
                type="submit"
                variant="contained"
                startIcon={<SendIcon />}
                disabled={isSubmitting}
              >
                {isSubmitting ? 'Processing...' : 'Start Processing'}
              </Button>
            </Box>
          </Grid>
        </Grid>
      </form>
    </Paper>
  );
};

export default DiscoveryForm;