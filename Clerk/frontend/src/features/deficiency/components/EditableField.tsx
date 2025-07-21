import React from 'react';
import { Box, FormControl, InputLabel, Select, MenuItem, TextField } from '@mui/material';
import { DeficiencyItem } from '../types/DeficiencyReport.types';

interface EditableFieldProps {
  item: DeficiencyItem;
  onChange: (updatedItem: DeficiencyItem) => void;
}

export const EditableField: React.FC<EditableFieldProps> = ({ item, onChange }) => {
  const handleClassificationChange = (classification: DeficiencyItem['classification']) => {
    onChange({ ...item, classification });
  };

  const handleNotesChange = (notes: string) => {
    onChange({ ...item, notes });
  };

  const handleKeyDown = (e: React.KeyboardEvent) => {
    if (e.key === 'Escape') {
      e.preventDefault();
      e.stopPropagation();
    }
  };

  return (
    <Box mb={2}>
      <FormControl fullWidth size="small" sx={{ mb: 2 }}>
        <InputLabel>Classification</InputLabel>
        <Select
          value={item.classification}
          onChange={(e) => handleClassificationChange(e.target.value as DeficiencyItem['classification'])}
          label="Classification"
          onKeyDown={handleKeyDown}
        >
          <MenuItem value="fully_produced">Fully Produced</MenuItem>
          <MenuItem value="partially_produced">Partially Produced</MenuItem>
          <MenuItem value="not_produced">Not Produced</MenuItem>
          <MenuItem value="no_responsive_docs">No Responsive Documents</MenuItem>
        </Select>
      </FormControl>

      <TextField
        fullWidth
        multiline
        rows={3}
        label="Notes"
        value={item.notes || ''}
        onChange={(e) => handleNotesChange(e.target.value)}
        placeholder="Add any additional context or notes..."
        onKeyDown={handleKeyDown}
      />
    </Box>
  );
};