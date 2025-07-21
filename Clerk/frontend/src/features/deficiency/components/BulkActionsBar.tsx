import React, { useState } from 'react';
import {
  Box,
  Paper,
  Typography,
  Button,
  Select,
  MenuItem,
  FormControl,
  InputLabel,
  TextField,
  Dialog,
  DialogTitle,
  DialogContent,
  DialogActions,
  LinearProgress
} from '@mui/material';
import { Edit as EditIcon } from '@mui/icons-material';
import { DeficiencyItem, DeficiencyItemUpdate } from '../types/DeficiencyReport.types';
import { useDeficiencyUIStore } from '../stores/deficiencyUIStore';
import { deficiencyAPI } from '../services/deficiencyAPI';

interface BulkActionsBarProps {
  selectedCount: number;
  reportId: string;
  onComplete: () => void;
}

export const BulkActionsBar: React.FC<BulkActionsBarProps> = ({
  selectedCount,
  reportId,
  onComplete
}) => {
  const { selectedItems, clearSelection } = useDeficiencyUIStore();
  const [dialogOpen, setDialogOpen] = useState(false);
  const [bulkClassification, setBulkClassification] = useState<DeficiencyItem['classification'] | ''>('');
  const [bulkNotes, setBulkNotes] = useState('');
  const [isProcessing, setIsProcessing] = useState(false);
  const [progress, setProgress] = useState(0);

  const handleBulkUpdate = () => {
    setDialogOpen(true);
  };

  const handleConfirmUpdate = async () => {
    setIsProcessing(true);
    setProgress(0);
    
    const updates: Partial<DeficiencyItemUpdate> = {};
    if (bulkClassification) updates.classification = bulkClassification;
    if (bulkNotes) updates.notes = bulkNotes;

    try {
      await deficiencyAPI.bulkUpdateDeficiencyItems(reportId, {
        item_ids: Array.from(selectedItems),
        updates
      });
      
      setProgress(100);
      clearSelection();
      setDialogOpen(false);
      setBulkClassification('');
      setBulkNotes('');
      onComplete();
    } catch (error) {
      console.error('Failed to update items:', error);
    } finally {
      setIsProcessing(false);
    }
  };

  const handleCancel = () => {
    setDialogOpen(false);
    setBulkClassification('');
    setBulkNotes('');
  };

  return (
    <>
      <Paper elevation={0} sx={{ p: 2, borderBottom: 1, borderColor: 'divider' }}>
        <Box display="flex" alignItems="center" justifyContent="space-between">
          <Typography variant="body1">
            {selectedCount} item{selectedCount > 1 ? 's' : ''} selected
          </Typography>
          
          <Box display="flex" gap={1}>
            <Button
              variant="outlined"
              startIcon={<EditIcon />}
              onClick={handleBulkUpdate}
            >
              Bulk Edit
            </Button>
            
            <Button
              variant="text"
              onClick={clearSelection}
            >
              Clear Selection
            </Button>
          </Box>
        </Box>
        
        {isProcessing && (
          <Box mt={2}>
            <LinearProgress variant="determinate" value={progress} />
          </Box>
        )}
      </Paper>

      <Dialog open={dialogOpen} onClose={handleCancel} maxWidth="sm" fullWidth>
        <DialogTitle>Bulk Update {selectedCount} Items</DialogTitle>
        <DialogContent>
          <Box py={2}>
            <FormControl fullWidth sx={{ mb: 2 }}>
              <InputLabel>Classification</InputLabel>
              <Select
                value={bulkClassification}
                onChange={(e) => setBulkClassification(e.target.value as DeficiencyItem['classification'])}
                label="Classification"
              >
                <MenuItem value="">No Change</MenuItem>
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
              label="Append to Notes"
              value={bulkNotes}
              onChange={(e) => setBulkNotes(e.target.value)}
              placeholder="Text will be appended to existing notes..."
              helperText="This text will be added to the end of existing notes for each selected item"
            />
          </Box>
        </DialogContent>
        <DialogActions>
          <Button onClick={handleCancel} disabled={isProcessing}>
            Cancel
          </Button>
          <Button
            onClick={handleConfirmUpdate}
            variant="contained"
            disabled={isProcessing || (!bulkClassification && !bulkNotes)}
          >
            Update {selectedCount} Items
          </Button>
        </DialogActions>
      </Dialog>
    </>
  );
};