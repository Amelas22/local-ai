import React, { useState } from 'react';
import {
  Dialog,
  DialogTitle,
  DialogContent,
  DialogActions,
  TextField,
  Button,
  Alert,
  Box,
  Typography,
  CircularProgress,
} from '@mui/material';
import { useForm, Controller } from 'react-hook-form';
import { useCaseManagement } from '../../hooks/useCaseManagement';

interface AddCaseModalProps {
  open: boolean;
  onClose: () => void;
  onCaseCreated?: (caseData: any) => void;
}

interface CaseFormData {
  name: string;
  description?: string;
}

export const AddCaseModal: React.FC<AddCaseModalProps> = ({
  open,
  onClose,
  onCaseCreated,
}) => {
  const { createCase, isCreating, error: apiError } = useCaseManagement();
  const [submitError, setSubmitError] = useState<string | null>(null);

  const {
    control,
    handleSubmit,
    reset,
    formState: { errors, isSubmitting },
  } = useForm<CaseFormData>({
    defaultValues: {
      name: '',
      description: '',
    },
  });

  const handleClose = () => {
    reset();
    setSubmitError(null);
    onClose();
  };

  const onSubmit = async (data: CaseFormData) => {
    try {
      setSubmitError(null);
      
      // Create case with metadata if description provided
      const metadata = data.description ? { description: data.description } : undefined;
      const newCase = await createCase({
        name: data.name.trim(),
        metadata,
      });

      // Success - close modal and notify parent
      handleClose();
      if (onCaseCreated) {
        onCaseCreated(newCase);
      }
    } catch (error: any) {
      // Handle specific error cases
      if (error.response?.status === 400) {
        setSubmitError(error.response.data.detail || 'Invalid case name');
      } else if (error.response?.status === 409) {
        setSubmitError('A case with this name already exists');
      } else {
        setSubmitError(error.message || 'Failed to create case');
      }
    }
  };

  return (
    <Dialog
      open={open}
      onClose={handleClose}
      maxWidth="sm"
      fullWidth
      aria-labelledby="add-case-dialog-title"
    >
      <form onSubmit={handleSubmit(onSubmit)}>
        <DialogTitle id="add-case-dialog-title">
          Create New Case
        </DialogTitle>
        
        <DialogContent>
          <Box sx={{ pt: 2 }}>
            <Typography variant="body2" color="text.secondary" paragraph>
              Enter a name for your new case. Case names must be unique within your law firm
              and can be up to 50 characters long.
            </Typography>

            <Controller
              name="name"
              control={control}
              rules={{
                required: 'Case name is required',
                maxLength: {
                  value: 50,
                  message: 'Case name must be 50 characters or less',
                },
                pattern: {
                  value: /^[^/\\<>:|?*"]+$/,
                  message: 'Case name contains invalid characters',
                },
                validate: (value) => value.trim().length > 0 || 'Case name cannot be empty',
              }}
              render={({ field }) => (
                <TextField
                  {...field}
                  label="Case Name"
                  placeholder="e.g., Smith v Jones 2024"
                  fullWidth
                  margin="normal"
                  error={!!errors.name}
                  helperText={errors.name?.message || `${field.value.length}/50 characters`}
                  autoFocus
                  disabled={isCreating || isSubmitting}
                  inputProps={{
                    maxLength: 50,
                    'aria-describedby': 'case-name-helper',
                  }}
                />
              )}
            />

            <Controller
              name="description"
              control={control}
              rules={{
                maxLength: {
                  value: 500,
                  message: 'Description must be 500 characters or less',
                },
              }}
              render={({ field }) => (
                <TextField
                  {...field}
                  label="Description (Optional)"
                  placeholder="Brief description of the case"
                  fullWidth
                  margin="normal"
                  multiline
                  rows={3}
                  error={!!errors.description}
                  helperText={errors.description?.message}
                  disabled={isCreating || isSubmitting}
                  inputProps={{
                    maxLength: 500,
                  }}
                />
              )}
            />

            {(submitError || apiError) && (
              <Alert severity="error" sx={{ mt: 2 }}>
                {submitError || apiError}
              </Alert>
            )}
          </Box>
        </DialogContent>

        <DialogActions>
          <Button
            onClick={handleClose}
            disabled={isCreating || isSubmitting}
          >
            Cancel
          </Button>
          <Button
            type="submit"
            variant="contained"
            disabled={isCreating || isSubmitting}
            startIcon={isCreating || isSubmitting ? <CircularProgress size={20} /> : null}
          >
            {isCreating || isSubmitting ? 'Creating...' : 'Create Case'}
          </Button>
        </DialogActions>
      </form>
    </Dialog>
  );
};