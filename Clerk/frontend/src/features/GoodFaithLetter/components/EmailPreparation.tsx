import React, { useState } from 'react';
import {
  Box,
  Paper,
  Typography,
  TextField,
  Button,
  Stack,
  Chip,
  Alert,
  Dialog,
  DialogTitle,
  DialogContent,
  DialogActions,
  List,
  ListItem,
  ListItemIcon,
  ListItemText,
  ListItemSecondaryAction,
  IconButton,
  Autocomplete,
  FormControlLabel,
  Checkbox,
  Divider,
  Card,
  CardContent
} from '@mui/material';
import {
  Send as SendIcon,
  AttachFile as AttachFileIcon,
  Save as SaveIcon,
  Delete as DeleteIcon,
  PictureAsPdf as PdfIcon,
  Description as DocumentIcon,
  Email as EmailIcon,
  Warning as WarningIcon,
  CheckCircle as CheckCircleIcon
} from '@mui/icons-material';
import { useForm, Controller } from 'react-hook-form';
import { GeneratedLetter } from '../../../types/goodFaithLetter.types';

interface EmailPreparationProps {
  letter: GeneratedLetter;
  onSendEmail?: (emailData: EmailFormData) => void;
  onSaveDraft?: (emailData: EmailFormData) => void;
}

interface EmailFormData {
  recipients: string[];
  ccRecipients: string[];
  bccRecipients: string[];
  subject: string;
  customMessage: string;
  includeEvidence: boolean;
  attachments: AttachmentInfo[];
}

interface AttachmentInfo {
  id: string;
  name: string;
  type: 'letter' | 'evidence' | 'other';
  size?: string;
}

const defaultAttachments: AttachmentInfo[] = [
  {
    id: 'letter-pdf',
    name: 'Good_Faith_Letter.pdf',
    type: 'letter',
    size: '245 KB'
  }
];

const validateEmail = (email: string): boolean => {
  const emailRegex = /^[^\s@]+@[^\s@]+\.[^\s@]+$/;
  return emailRegex.test(email);
};

const validateEmails = (emails: string[]): string | true => {
  if (emails.length === 0) return 'At least one recipient is required';
  const invalidEmails = emails.filter(email => !validateEmail(email));
  if (invalidEmails.length > 0) {
    return `Invalid email format: ${invalidEmails.join(', ')}`;
  }
  return true;
};

export const EmailPreparation: React.FC<EmailPreparationProps> = ({
  letter,
  onSendEmail,
  onSaveDraft
}) => {
  const [sendConfirmOpen, setSendConfirmOpen] = useState(false);
  const [savedDraft, setSavedDraft] = useState(false);

  const { control, handleSubmit, formState: { errors, isValid }, watch, setValue } = useForm<EmailFormData>({
    defaultValues: {
      recipients: [],
      ccRecipients: [],
      bccRecipients: [],
      subject: `Re: ${letter.case_name} - Good Faith Letter Regarding Discovery Deficiencies`,
      customMessage: `Dear Counsel,

Please find attached our Good Faith Letter regarding discovery deficiencies in the matter of ${letter.case_name}.

We look forward to your prompt response and resolution of these matters.

Best regards,`,
      includeEvidence: false,
      attachments: [...defaultAttachments]
    },
    mode: 'onChange'
  });

  const watchIncludeEvidence = watch('includeEvidence');
  const watchAttachments = watch('attachments');

  React.useEffect(() => {
    if (watchIncludeEvidence) {
      const evidenceAttachment: AttachmentInfo = {
        id: 'evidence-bundle',
        name: 'Evidence_Supporting_Deficiencies.pdf',
        type: 'evidence',
        size: '12.3 MB'
      };
      
      if (!watchAttachments.find(att => att.id === 'evidence-bundle')) {
        setValue('attachments', [...watchAttachments, evidenceAttachment]);
      }
    } else {
      setValue('attachments', watchAttachments.filter(att => att.type !== 'evidence'));
    }
  }, [watchIncludeEvidence, watchAttachments, setValue]);

  const handleSendClick = () => {
    if (letter.status !== 'finalized' && letter.status !== 'approved') {
      setSendConfirmOpen(true);
    } else {
      handleSubmit(onSendConfirm)();
    }
  };

  const onSendConfirm = (data: EmailFormData) => {
    setSendConfirmOpen(false);
    if (onSendEmail) {
      onSendEmail(data);
    }
  };

  const handleSaveDraftClick = handleSubmit((data) => {
    if (onSaveDraft) {
      onSaveDraft(data);
      setSavedDraft(true);
      setTimeout(() => setSavedDraft(false), 3000);
    }
  });

  const getAttachmentIcon = (type: AttachmentInfo['type']) => {
    switch (type) {
      case 'letter':
        return <PdfIcon color="error" />;
      case 'evidence':
        return <DocumentIcon color="primary" />;
      default:
        return <AttachFileIcon />;
    }
  };

  return (
    <Paper elevation={2} sx={{ p: 4 }}>
      <Stack spacing={3}>
        <Box display="flex" justifyContent="space-between" alignItems="center">
          <Typography variant="h6" display="flex" alignItems="center" gap={1}>
            <EmailIcon />
            Email Preparation
          </Typography>
          {savedDraft && (
            <Chip
              icon={<CheckCircleIcon />}
              label="Draft saved"
              color="success"
              size="small"
            />
          )}
        </Box>

        <Divider />

        {letter.status === 'draft' && (
          <Alert severity="warning" icon={<WarningIcon />}>
            This letter is still in draft status. Consider finalizing it before sending.
          </Alert>
        )}

        <form onSubmit={handleSendClick}>
          <Stack spacing={3}>
            {/* Recipients */}
            <Controller
              name="recipients"
              control={control}
              rules={{ validate: validateEmails }}
              render={({ field }) => (
                <Autocomplete
                  {...field}
                  multiple
                  freeSolo
                  options={[]}
                  renderTags={(value, getTagProps) =>
                    value.map((option, index) => (
                      <Chip
                        variant="outlined"
                        label={option}
                        {...getTagProps({ index })}
                        color={validateEmail(option) ? 'default' : 'error'}
                      />
                    ))
                  }
                  renderInput={(params) => (
                    <TextField
                      {...params}
                      label="To"
                      placeholder="Enter email addresses"
                      error={!!errors.recipients}
                      helperText={errors.recipients?.message || 'Press Enter after each email address'}
                      required
                    />
                  )}
                  onChange={(_, value) => field.onChange(value)}
                />
              )}
            />

            {/* CC Recipients */}
            <Controller
              name="ccRecipients"
              control={control}
              render={({ field }) => (
                <Autocomplete
                  {...field}
                  multiple
                  freeSolo
                  options={[]}
                  renderTags={(value, getTagProps) =>
                    value.map((option, index) => (
                      <Chip
                        variant="outlined"
                        label={option}
                        {...getTagProps({ index })}
                        size="small"
                      />
                    ))
                  }
                  renderInput={(params) => (
                    <TextField
                      {...params}
                      label="CC (Optional)"
                      placeholder="Enter CC email addresses"
                      size="small"
                    />
                  )}
                  onChange={(_, value) => field.onChange(value)}
                />
              )}
            />

            {/* BCC Recipients */}
            <Controller
              name="bccRecipients"
              control={control}
              render={({ field }) => (
                <Autocomplete
                  {...field}
                  multiple
                  freeSolo
                  options={[]}
                  renderTags={(value, getTagProps) =>
                    value.map((option, index) => (
                      <Chip
                        variant="outlined"
                        label={option}
                        {...getTagProps({ index })}
                        size="small"
                      />
                    ))
                  }
                  renderInput={(params) => (
                    <TextField
                      {...params}
                      label="BCC (Optional)"
                      placeholder="Enter BCC email addresses"
                      size="small"
                    />
                  )}
                  onChange={(_, value) => field.onChange(value)}
                />
              )}
            />

            {/* Subject Line */}
            <Controller
              name="subject"
              control={control}
              rules={{ required: 'Subject is required' }}
              render={({ field }) => (
                <TextField
                  {...field}
                  fullWidth
                  label="Subject"
                  error={!!errors.subject}
                  helperText={errors.subject?.message}
                  required
                />
              )}
            />

            {/* Custom Message */}
            <Controller
              name="customMessage"
              control={control}
              render={({ field }) => (
                <TextField
                  {...field}
                  fullWidth
                  multiline
                  rows={6}
                  label="Message"
                  helperText="This message will appear in the email body before the letter attachment"
                />
              )}
            />

            {/* Attachments Section */}
            <Card variant="outlined">
              <CardContent>
                <Typography variant="subtitle1" gutterBottom>
                  Attachments
                </Typography>
                
                <Stack spacing={2}>
                  <Controller
                    name="includeEvidence"
                    control={control}
                    render={({ field }) => (
                      <FormControlLabel
                        control={<Checkbox {...field} checked={field.value} />}
                        label="Include supporting evidence documents"
                      />
                    )}
                  />

                  <List dense>
                    {watchAttachments.map((attachment) => (
                      <ListItem key={attachment.id}>
                        <ListItemIcon>
                          {getAttachmentIcon(attachment.type)}
                        </ListItemIcon>
                        <ListItemText
                          primary={attachment.name}
                          secondary={attachment.size}
                        />
                        {attachment.type === 'other' && (
                          <ListItemSecondaryAction>
                            <IconButton edge="end" size="small">
                              <DeleteIcon />
                            </IconButton>
                          </ListItemSecondaryAction>
                        )}
                      </ListItem>
                    ))}
                  </List>

                  <Box>
                    <Typography variant="caption" color="text.secondary">
                      Total attachment size: {
                        watchAttachments.reduce((total, att) => {
                          const size = parseFloat(att.size?.replace(/[^\d.]/g, '') || '0');
                          return total + size;
                        }, 0).toFixed(1)
                      } MB
                    </Typography>
                  </Box>
                </Stack>
              </CardContent>
            </Card>

            {/* Action Buttons */}
            <Stack direction="row" spacing={2} justifyContent="flex-end">
              <Button
                variant="outlined"
                startIcon={<SaveIcon />}
                onClick={handleSaveDraftClick}
              >
                Save Draft
              </Button>
              <Button
                variant="contained"
                startIcon={<SendIcon />}
                type="submit"
                disabled={!isValid}
              >
                Send Email
              </Button>
            </Stack>
          </Stack>
        </form>
      </Stack>

      {/* Send Confirmation Dialog */}
      <Dialog open={sendConfirmOpen} onClose={() => setSendConfirmOpen(false)}>
        <DialogTitle>Send Good Faith Letter?</DialogTitle>
        <DialogContent>
          <Stack spacing={2}>
            <Alert severity="warning">
              This letter is in {letter.status} status. Sending it will create an official record.
            </Alert>
            <Typography variant="body2">
              Recipients: {watch('recipients').join(', ')}
            </Typography>
            <Typography variant="body2">
              Attachments: {watchAttachments.length} file(s)
            </Typography>
          </Stack>
        </DialogContent>
        <DialogActions>
          <Button onClick={() => setSendConfirmOpen(false)}>Cancel</Button>
          <Button
            variant="contained"
            onClick={handleSubmit(onSendConfirm)}
            startIcon={<SendIcon />}
          >
            Confirm Send
          </Button>
        </DialogActions>
      </Dialog>
    </Paper>
  );
};