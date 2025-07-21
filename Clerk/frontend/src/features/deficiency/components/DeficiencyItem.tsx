import React, { useState } from 'react';
import {
  Box,
  Card,
  CardContent,
  Checkbox,
  Typography,
  Chip,
  LinearProgress,
  IconButton,
  Collapse,
  Button,
  Stack
} from '@mui/material';
import {
  Edit as EditIcon,
  Save as SaveIcon,
  Cancel as CancelIcon,
  ExpandMore as ExpandMoreIcon,
  ExpandLess as ExpandLessIcon
} from '@mui/icons-material';
import { DeficiencyItem as DeficiencyItemType } from '../types/DeficiencyReport.types';
import { EditableField } from './EditableField';
import { EvidenceChunk } from './EvidenceChunk';
import { useDeficiencyUIStore } from '../stores/deficiencyUIStore';
import { deficiencyAPI } from '../services/deficiencyAPI';

interface DeficiencyItemProps {
  item: DeficiencyItemType;
  reportId: string;
  onUpdate: () => void;
}

const DeficiencyItemComponent: React.FC<DeficiencyItemProps> = ({ item, reportId, onUpdate }) => {
  const { 
    selectedItems, 
    toggleItemSelection, 
    editingItemId, 
    setEditingItemId,
    expandedItems,
    toggleItemExpansion
  } = useDeficiencyUIStore();
  
  const [editedItem, setEditedItem] = useState(item);
  const [isSaving, setIsSaving] = useState(false);
  
  const isSelected = selectedItems.has(item.id);
  const isEditing = editingItemId === item.id;
  const isExpanded = expandedItems.has(item.id);

  const handleKeyDown = (e: React.KeyboardEvent) => {
    if (isEditing) {
      if (e.key === 'Enter' && e.ctrlKey) {
        e.preventDefault();
        handleSave();
      } else if (e.key === 'Escape') {
        e.preventDefault();
        handleCancel();
      }
    }
  };

  const handleEdit = () => {
    setEditingItemId(item.id);
    setEditedItem(item);
  };

  const handleCancel = () => {
    setEditingItemId(null);
    setEditedItem(item);
  };

  const handleSave = async () => {
    setIsSaving(true);
    try {
      await deficiencyAPI.updateDeficiencyItem(reportId, item.id, {
        classification: editedItem.classification,
        notes: editedItem.notes
      });
      setEditingItemId(null);
      onUpdate();
    } catch (error) {
      console.error('Failed to save changes:', error);
      setEditedItem(item);
    } finally {
      setIsSaving(false);
    }
  };

  const getClassificationColor = (classification: DeficiencyItemType['classification']) => {
    switch (classification) {
      case 'fully_produced': return 'success';
      case 'partially_produced': return 'warning';
      case 'not_produced': return 'error';
      case 'no_responsive_docs': return 'default';
    }
  };

  const getClassificationLabel = (classification: DeficiencyItemType['classification']) => {
    return classification.split('_').map(word => 
      word.charAt(0).toUpperCase() + word.slice(1)
    ).join(' ');
  };

  return (
    <Card variant="outlined" sx={{ mb: 2, mx: 2 }} onKeyDown={handleKeyDown}>
      <CardContent>
        <Box display="flex" alignItems="flex-start" gap={2}>
          <Checkbox
            checked={isSelected}
            onChange={() => toggleItemSelection(item.id)}
            inputProps={{ 'aria-label': `Select ${item.request_number}` }}
          />
          
          <Box flex={1}>
            <Box display="flex" justifyContent="space-between" alignItems="flex-start" mb={2}>
              <Box>
                <Typography variant="h6" gutterBottom>
                  {item.request_number}
                </Typography>
                
                <Stack direction="row" spacing={1} alignItems="center" mb={1}>
                  <Chip
                    label={getClassificationLabel(isEditing ? editedItem.classification : item.classification)}
                    color={getClassificationColor(isEditing ? editedItem.classification : item.classification)}
                    size="small"
                  />
                  
                  <Box display="flex" alignItems="center" gap={1}>
                    <Typography variant="caption" color="textSecondary">
                      Confidence:
                    </Typography>
                    <Box width={100}>
                      <LinearProgress
                        variant="determinate"
                        value={item.confidence_score * 100}
                        sx={{ height: 6, borderRadius: 3 }}
                      />
                    </Box>
                    <Typography variant="caption">
                      {Math.round(item.confidence_score * 100)}%
                    </Typography>
                  </Box>
                </Stack>
              </Box>
              
              <Box>
                {!isEditing ? (
                  <IconButton size="small" onClick={handleEdit} aria-label={`Edit ${item.request_number}`}>
                    <EditIcon />
                  </IconButton>
                ) : (
                  <>
                    <IconButton size="small" onClick={handleSave} disabled={isSaving} aria-label="Save changes">
                      <SaveIcon />
                    </IconButton>
                    <IconButton size="small" onClick={handleCancel} disabled={isSaving} aria-label="Cancel editing">
                      <CancelIcon />
                    </IconButton>
                  </>
                )}
              </Box>
            </Box>

            <Box mb={2}>
              <Typography variant="subtitle2" gutterBottom>
                Request:
              </Typography>
              <Typography variant="body2" paragraph>
                {item.request_text}
              </Typography>
            </Box>

            <Box mb={2}>
              <Typography variant="subtitle2" gutterBottom>
                OC Response:
              </Typography>
              <Typography variant="body2" paragraph>
                {item.oc_response_text}
              </Typography>
            </Box>

            {isEditing && (
              <EditableField
                item={editedItem}
                onChange={setEditedItem}
              />
            )}

            {item.notes && !isEditing && (
              <Box mb={2}>
                <Typography variant="subtitle2" gutterBottom>
                  Notes:
                </Typography>
                <Typography variant="body2">
                  {item.notes}
                </Typography>
              </Box>
            )}

            {item.evidence_chunks.length > 0 && (
              <Box>
                <Button
                  startIcon={isExpanded ? <ExpandLessIcon /> : <ExpandMoreIcon />}
                  onClick={() => toggleItemExpansion(item.id)}
                  size="small"
                >
                  Evidence ({item.evidence_chunks.length} chunks)
                </Button>
                
                <Collapse in={isExpanded}>
                  <Box mt={2}>
                    {item.evidence_chunks.map((chunk, index) => (
                      <EvidenceChunk key={index} chunk={chunk} />
                    ))}
                  </Box>
                </Collapse>
              </Box>
            )}
          </Box>
        </Box>
      </CardContent>
    </Card>
  );
};

export const DeficiencyItem = React.memo(DeficiencyItemComponent);