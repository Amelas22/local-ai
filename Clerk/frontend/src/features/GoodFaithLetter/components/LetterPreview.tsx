import React from 'react';
import {
  Box,
  Paper,
  Typography,
  CircularProgress,
  Alert,
  Divider,
  Stack,
  Chip
} from '@mui/material';
import { useQuery } from '@tanstack/react-query';
import { goodFaithLetterAPI } from '../../../services/api/goodFaithLetter';
import { GeneratedLetter, LetterSection } from '../../../types/goodFaithLetter.types';
import DOMPurify from 'dompurify';

interface LetterPreviewProps {
  letterId: string;
}

const parseLetterSections = (letter: GeneratedLetter): LetterSection[] => {
  const content = letter.content;
  const sections: LetterSection[] = [];
  
  // Parse the letter content into sections based on common legal letter structure
  const sectionPatterns = [
    { id: 'header', name: 'Header', regex: /^(.*?)(?=Re:|Dear\s)/s, editable: false },
    { id: 'subject', name: 'Subject Line', regex: /Re:\s*(.*?)(?=\n)/s, editable: true },
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
        editable: pattern.editable
      });
    }
  });

  // If no sections matched, treat entire content as body
  if (sections.length === 0) {
    sections.push({
      id: 'full',
      name: 'Letter Content',
      content: content,
      editable: true
    });
  }

  return sections;
};

const StatusChip: React.FC<{ status: GeneratedLetter['status'] }> = ({ status }) => {
  const statusConfig = {
    draft: { color: 'default' as const, label: 'Draft' },
    review: { color: 'warning' as const, label: 'Under Review' },
    approved: { color: 'success' as const, label: 'Approved' },
    finalized: { color: 'info' as const, label: 'Finalized' }
  };

  const config = statusConfig[status];
  return <Chip size="small" color={config.color} label={config.label} />;
};

export const LetterPreview: React.FC<LetterPreviewProps> = ({ letterId }) => {
  const { data: letter, isLoading, error } = useQuery({
    queryKey: ['letter', letterId],
    queryFn: () => goodFaithLetterAPI.getLetter(letterId),
    refetchInterval: (data) => data && 'status' in data && data.status === 'draft' ? 5000 : false,
  });

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
          Failed to load letter preview. Please try again later.
        </Alert>
      </Box>
    );
  }

  if (!letter) {
    return (
      <Box p={3}>
        <Alert severity="info">
          No letter found with the provided ID.
        </Alert>
      </Box>
    );
  }

  const sections = parseLetterSections(letter);

  return (
    <Paper 
      elevation={2} 
      sx={{ 
        p: 4, 
        m: 2,
        backgroundColor: '#ffffff',
        '@media print': {
          boxShadow: 'none',
          m: 0,
          p: '1in'
        }
      }}
    >
      <Stack spacing={2} mb={3}>
        <Box display="flex" justifyContent="space-between" alignItems="center">
          <Typography variant="h5" component="h1">
            Good Faith Letter Preview
          </Typography>
          <Stack direction="row" spacing={1} alignItems="center">
            <StatusChip status={letter.status} />
            <Typography variant="caption" color="text.secondary">
              Version {letter.version}
            </Typography>
          </Stack>
        </Box>
        <Divider />
      </Stack>

      <Box
        sx={{
          fontFamily: 'Times New Roman, serif',
          fontSize: '12pt',
          lineHeight: 1.6,
          color: '#000000',
          '& p': {
            marginBottom: '1em'
          }
        }}
      >
        {sections.map((section, index) => (
          <Box key={section.id} mb={3}>
            {section.name !== 'Letter Content' && (
              <Typography
                variant="overline"
                sx={{
                  display: 'block',
                  color: 'text.secondary',
                  fontSize: '0.75rem',
                  mb: 1,
                  '@media print': {
                    display: 'none'
                  }
                }}
              >
                {section.name}
              </Typography>
            )}
            <Box
              dangerouslySetInnerHTML={{ 
                __html: DOMPurify.sanitize(
                  section.content.replace(/\n/g, '<br />'),
                  { ADD_ATTR: ['target'] }
                )
              }}
              sx={{
                '& strong': {
                  fontWeight: 'bold'
                },
                '& em': {
                  fontStyle: 'italic'
                },
                '& u': {
                  textDecoration: 'underline'
                }
              }}
            />
            {index < sections.length - 1 && section.name !== 'Header' && (
              <Box my={2} />
            )}
          </Box>
        ))}
      </Box>

      <Box
        sx={{
          mt: 4,
          pt: 2,
          borderTop: 1,
          borderColor: 'divider',
          '@media print': {
            display: 'none'
          }
        }}
      >
        <Typography variant="caption" color="text.secondary">
          Generated on {new Date(letter.created_at).toLocaleString()} | 
          Case: {letter.case_name} | 
          Jurisdiction: {letter.jurisdiction}
          {letter.updated_at && ` | Last updated: ${new Date(letter.updated_at).toLocaleString()}`}
        </Typography>
      </Box>
    </Paper>
  );
};