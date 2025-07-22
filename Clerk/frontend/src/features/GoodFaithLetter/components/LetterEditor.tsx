import React, { useState, useRef, useEffect } from 'react';
import {
  Box,
  Paper,
  Typography,
  TextField,
  Button,
  Stack,
  Divider,
  Alert,
  CircularProgress,
  IconButton,
  Tooltip,
  Card,
  CardContent,
  Chip
} from '@mui/material';
import {
  Edit as EditIcon,
  Save as SaveIcon,
  Cancel as CancelIcon,
  History as HistoryIcon,
  CheckCircle as CheckCircleIcon
} from '@mui/icons-material';
import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query';
import { goodFaithLetterAPI } from '../../../services/api/goodFaithLetter';
import { GeneratedLetter, LetterSection, SectionEdit } from '../../../types/goodFaithLetter.types';
import { useForm, Controller } from 'react-hook-form';
import DOMPurify from 'dompurify';

interface LetterEditorProps {
  letterId: string;
  onVersionChange?: (version: number) => void;
}

interface EditableSection extends LetterSection {
  isEditing: boolean;
  editedContent?: string;
}

interface EditFormData {
  section_edits: SectionEdit[];
  editor_notes: string;
}

const parseLetterIntoSections = (letter: GeneratedLetter): EditableSection[] => {
  const content = letter.content;
  const sections: EditableSection[] = [];
  
  const sectionPatterns = [
    { id: 'header', name: 'Header', regex: /^(.*?)(?=Re:|Dear\s)/s, editable: true },
    { id: 'subject', name: 'Subject Line', regex: /(Re:\s*.*?)(?=\n)/s, editable: true },
    { id: 'salutation', name: 'Salutation', regex: /(Dear\s+.*?:)/s, editable: true },
    { id: 'body', name: 'Body', regex: /Dear\s+.*?:\s*(.*?)(?=DEFICIENCIES|Sincerely|Very truly yours)/s, editable: true },
    { id: 'deficiencies', name: 'Deficiencies', regex: /DEFICIENCIES[:\s]*(.*?)(?=Sincerely|Very truly yours|$)/s, editable: true },
    { id: 'conclusion', name: 'Conclusion', regex: /((?:Sincerely|Very truly yours)[\s\S]*$)/s, editable: true }
  ];

  sectionPatterns.forEach((pattern) => {
    const match = content.match(pattern.regex);
    if (match) {
      sections.push({
        id: pattern.id,
        name: pattern.name,
        content: match[1] || match[0],
        editable: pattern.editable,
        isEditing: false
      });
    }
  });

  if (sections.length === 0) {
    sections.push({
      id: 'full',
      name: 'Letter Content',
      content: content,
      editable: true,
      isEditing: false
    });
  }

  return sections;
};

export const LetterEditor: React.FC<LetterEditorProps> = ({ letterId, onVersionChange }) => {
  const queryClient = useQueryClient();
  const [sections, setSections] = useState<EditableSection[]>([]);
  const [hasUnsavedChanges, setHasUnsavedChanges] = useState(false);
  const editingRefs = useRef<{ [key: string]: HTMLTextAreaElement | null }>({});

  const { control, handleSubmit, reset, formState: { isDirty } } = useForm<EditFormData>({
    defaultValues: {
      section_edits: [],
      editor_notes: ''
    }
  });

  const { data: letter, isLoading, error } = useQuery({
    queryKey: ['letter', letterId],
    queryFn: () => goodFaithLetterAPI.getLetter(letterId),
  });

  const customizeMutation = useMutation({
    mutationFn: (data: EditFormData) => 
      goodFaithLetterAPI.customizeLetter(letterId, data),
    onSuccess: (updatedLetter) => {
      queryClient.setQueryData(['letter', letterId], updatedLetter);
      setSections(parseLetterIntoSections(updatedLetter));
      setHasUnsavedChanges(false);
      reset();
      if (onVersionChange) {
        onVersionChange(updatedLetter.version);
      }
    },
  });

  useEffect(() => {
    if (letter) {
      setSections(parseLetterIntoSections(letter));
    }
  }, [letter]);

  useEffect(() => {
    setHasUnsavedChanges(isDirty);
  }, [isDirty]);

  const handleSectionEdit = (sectionId: string, isEditing: boolean) => {
    setSections(prev => prev.map(section => 
      section.id === sectionId 
        ? { ...section, isEditing, editedContent: isEditing ? section.content : undefined }
        : section
    ));
  };

  const handleSectionContentChange = (sectionId: string, content: string) => {
    setSections(prev => prev.map(section => 
      section.id === sectionId 
        ? { ...section, editedContent: content }
        : section
    ));
    setHasUnsavedChanges(true);
  };

  const handleSaveAll = handleSubmit((data) => {
    const editedSections = sections
      .filter(section => section.editedContent !== undefined && section.editedContent !== section.content)
      .map(section => ({
        section: section.id,
        content: section.editedContent!
      }));

    if (editedSections.length === 0) {
      return;
    }

    customizeMutation.mutate({
      section_edits: editedSections,
      editor_notes: data.editor_notes
    });
  });

  const handleCancelEdit = (sectionId: string) => {
    handleSectionEdit(sectionId, false);
  };

  const validateSection = (section: EditableSection): string | null => {
    if (!section.editedContent || section.editedContent.trim() === '') {
      return 'Section content cannot be empty';
    }
    if (section.id === 'subject' && !section.editedContent.includes('Re:')) {
      return 'Subject line must include "Re:"';
    }
    if (section.id === 'salutation' && !section.editedContent.includes(':')) {
      return 'Salutation must end with a colon';
    }
    return null;
  };

  if (isLoading) {
    return (
      <Box display="flex" justifyContent="center" alignItems="center" minHeight="400px">
        <CircularProgress />
      </Box>
    );
  }

  if (error || !letter) {
    return (
      <Box p={3}>
        <Alert severity="error">
          Failed to load letter for editing. Please try again later.
        </Alert>
      </Box>
    );
  }

  if (letter.status === 'finalized') {
    return (
      <Box p={3}>
        <Alert severity="info">
          This letter has been finalized and cannot be edited.
        </Alert>
      </Box>
    );
  }

  return (
    <Paper elevation={2} sx={{ p: 4, m: 2 }}>
      <Stack spacing={3}>
        <Box display="flex" justifyContent="space-between" alignItems="center">
          <Typography variant="h5" component="h1">
            Edit Good Faith Letter
          </Typography>
          <Stack direction="row" spacing={1} alignItems="center">
            {hasUnsavedChanges && (
              <Chip 
                size="small" 
                color="warning" 
                label="Unsaved changes" 
                icon={<EditIcon />}
              />
            )}
            <Chip 
              size="small" 
              label={`Version ${letter.version}`}
              icon={<HistoryIcon />}
            />
          </Stack>
        </Box>
        
        <Divider />

        {customizeMutation.isSuccess && (
          <Alert severity="success" icon={<CheckCircleIcon />}>
            Letter updated successfully! Version {letter.version} saved.
          </Alert>
        )}

        {customizeMutation.isError && (
          <Alert severity="error">
            Failed to save changes. Please try again.
          </Alert>
        )}

        <Stack spacing={3}>
          {sections.map((section) => {
            const validationError = section.isEditing ? validateSection(section) : null;
            
            return (
              <Card key={section.id} variant="outlined">
                <CardContent>
                  <Box display="flex" justifyContent="space-between" alignItems="center" mb={2}>
                    <Typography variant="subtitle1" fontWeight="bold">
                      {section.name}
                    </Typography>
                    {section.editable && !section.isEditing && (
                      <Tooltip title="Edit section">
                        <IconButton
                          size="small"
                          onClick={() => handleSectionEdit(section.id, true)}
                          disabled={customizeMutation.isPending}
                        >
                          <EditIcon />
                        </IconButton>
                      </Tooltip>
                    )}
                  </Box>

                  {section.isEditing ? (
                    <Stack spacing={2}>
                      <TextField
                        multiline
                        fullWidth
                        minRows={4}
                        maxRows={20}
                        value={section.editedContent || ''}
                        onChange={(e) => handleSectionContentChange(section.id, e.target.value)}
                        error={!!validationError}
                        helperText={validationError}
                        inputRef={(ref) => { editingRefs.current[section.id] = ref; }}
                        sx={{
                          '& .MuiInputBase-root': {
                            fontFamily: 'monospace',
                            fontSize: '14px'
                          }
                        }}
                      />
                      <Stack direction="row" spacing={1} justifyContent="flex-end">
                        <Button
                          size="small"
                          startIcon={<CancelIcon />}
                          onClick={() => handleCancelEdit(section.id)}
                        >
                          Cancel
                        </Button>
                      </Stack>
                    </Stack>
                  ) : (
                    <Box
                      sx={{
                        whiteSpace: 'pre-wrap',
                        fontFamily: 'Times New Roman, serif',
                        fontSize: '14px',
                        lineHeight: 1.6,
                        color: 'text.primary'
                      }}
                      dangerouslySetInnerHTML={{
                        __html: DOMPurify.sanitize(
                          (section.editedContent || section.content).replace(/\n/g, '<br />'),
                          { ADD_ATTR: ['target'] }
                        )
                      }}
                    />
                  )}
                </CardContent>
              </Card>
            );
          })}
        </Stack>

        <Divider />

        <Box>
          <Controller
            name="editor_notes"
            control={control}
            render={({ field }) => (
              <TextField
                {...field}
                fullWidth
                multiline
                rows={3}
                label="Editor Notes (Optional)"
                placeholder="Add any notes about your changes..."
                variant="outlined"
              />
            )}
          />
        </Box>

        <Stack direction="row" spacing={2} justifyContent="flex-end">
          <Button
            variant="contained"
            startIcon={<SaveIcon />}
            onClick={handleSaveAll}
            disabled={!hasUnsavedChanges || customizeMutation.isPending}
          >
            {customizeMutation.isPending ? 'Saving...' : 'Save All Changes'}
          </Button>
        </Stack>
      </Stack>
    </Paper>
  );
};