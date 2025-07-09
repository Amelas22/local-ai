import React, { useMemo } from 'react';
import {
  FormControl,
  InputLabel,
  Select,
  MenuItem,
  SelectChangeEvent,
  Chip,
  Box,
  Typography,
  Divider,
  ListSubheader,
  CircularProgress,
} from '@mui/material';
import {
  FolderOpen as FolderIcon,
  Archive as ArchiveIcon,
  Lock as LockIcon,
  Public as PublicIcon,
} from '@mui/icons-material';

interface Case {
  id: string;
  name: string;
  collection_name: string;
  status: 'active' | 'archived' | 'closed';
  is_shared?: boolean;
  law_firm_name?: string;
  vector_count?: number;
}

interface CaseSelectorProps {
  value: string;
  onChange: (caseId: string) => void;
  cases: Case[];
  loading?: boolean;
  error?: string;
  disabled?: boolean;
  showArchived?: boolean;
  showShared?: boolean;
  fullWidth?: boolean;
  label?: string;
}

export const CaseSelector: React.FC<CaseSelectorProps> = ({
  value,
  onChange,
  cases,
  loading = false,
  error,
  disabled = false,
  showArchived = false,
  showShared = true,
  fullWidth = true,
  label = 'Select Case',
}) => {
  // Group cases by type
  const groupedCases = useMemo(() => {
    const active: Case[] = [];
    const archived: Case[] = [];
    const shared: Case[] = [];

    cases.forEach((caseItem) => {
      if (caseItem.is_shared && showShared) {
        shared.push(caseItem);
      } else if (caseItem.status === 'archived' && showArchived) {
        archived.push(caseItem);
      } else if (caseItem.status === 'active') {
        active.push(caseItem);
      }
    });

    return { active, archived, shared };
  }, [cases, showArchived, showShared]);

  const handleChange = (event: SelectChangeEvent) => {
    onChange(event.target.value);
  };

  const renderCaseOption = (caseItem: Case) => {
    const Icon = caseItem.is_shared
      ? PublicIcon
      : caseItem.status === 'archived'
      ? ArchiveIcon
      : caseItem.status === 'closed'
      ? LockIcon
      : FolderIcon;

    return (
      <MenuItem key={caseItem.collection_name} value={caseItem.collection_name}>
        <Box display="flex" alignItems="center" width="100%">
          <Icon
            fontSize="small"
            sx={{
              mr: 1,
              color: caseItem.is_shared
                ? 'info.main'
                : caseItem.status === 'archived'
                ? 'text.disabled'
                : 'primary.main',
            }}
          />
          <Box flex={1}>
            <Typography variant="body2">{caseItem.name}</Typography>
            {caseItem.law_firm_name && (
              <Typography variant="caption" color="text.secondary">
                {caseItem.law_firm_name}
              </Typography>
            )}
          </Box>
          {caseItem.vector_count !== undefined && (
            <Chip
              label={`${caseItem.vector_count.toLocaleString()} docs`}
              size="small"
              variant="outlined"
              sx={{ ml: 1 }}
            />
          )}
        </Box>
      </MenuItem>
    );
  };

  return (
    <FormControl fullWidth={fullWidth} disabled={disabled || loading} error={!!error}>
      <InputLabel id="case-selector-label">{label}</InputLabel>
      <Select
        labelId="case-selector-label"
        id="case-selector"
        value={value}
        label={label}
        onChange={handleChange}
        startAdornment={
          loading ? (
            <CircularProgress size={20} sx={{ mr: 1 }} />
          ) : null
        }
      >
        {/* Active Cases */}
        {groupedCases.active.length > 0 && [
          <ListSubheader key="active-header">Active Cases</ListSubheader>,
          ...groupedCases.active.map(renderCaseOption),
        ]}

        {/* Archived Cases */}
        {groupedCases.archived.length > 0 && [
          groupedCases.active.length > 0 && <Divider key="archived-divider" />,
          <ListSubheader key="archived-header">Archived Cases</ListSubheader>,
          ...groupedCases.archived.map(renderCaseOption),
        ]}

        {/* Shared Resources */}
        {groupedCases.shared.length > 0 && [
          (groupedCases.active.length > 0 || groupedCases.archived.length > 0) && (
            <Divider key="shared-divider" />
          ),
          <ListSubheader key="shared-header">Shared Resources</ListSubheader>,
          ...groupedCases.shared.map(renderCaseOption),
        ]}

        {/* Empty State */}
        {cases.length === 0 && !loading && (
          <MenuItem disabled>
            <Typography variant="body2" color="text.secondary">
              {error || 'No cases available'}
            </Typography>
          </MenuItem>
        )}
      </Select>
      
      {error && (
        <Typography variant="caption" color="error" sx={{ mt: 0.5 }}>
          {error}
        </Typography>
      )}
    </FormControl>
  );
};