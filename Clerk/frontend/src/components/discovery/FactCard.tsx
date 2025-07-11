import React, { useState } from 'react';
import {
  Card,
  CardContent,
  CardActions,
  Typography,
  Box,
  Chip,
  IconButton,
  Button,
  TextField,
  Dialog,
  DialogTitle,
  DialogContent,
  DialogActions,
  Tooltip,
  LinearProgress,
  Menu,
  MenuItem,
  Divider,
  Stack,
} from '@mui/material';
import {
  Edit as EditIcon,
  Delete as DeleteIcon,
  Check as CheckIcon,
  Close as CloseIcon,
  MoreVert as MoreVertIcon,
  Description as DocumentIcon,
  History as HistoryIcon,
  Person as PersonIcon,
  Category as CategoryIcon,
  LocalOffer as TagIcon,
} from '@mui/icons-material';
import { format } from 'date-fns';
import { ExtractedFactWithSource } from '../../types/discovery.types';

interface FactCardProps {
  fact: ExtractedFactWithSource;
  viewMode: 'grid' | 'list';
  onSelect: (fact: ExtractedFactWithSource) => void;
  onUpdate: (fact: ExtractedFactWithSource, newContent: string, reason?: string) => void;
  onDelete: (fact: ExtractedFactWithSource) => void;
  isSelected?: boolean;
}

export const FactCard: React.FC<FactCardProps> = ({
  fact,
  viewMode,
  onSelect,
  onUpdate,
  onDelete,
  isSelected = false,
}) => {
  const [isEditing, setIsEditing] = useState(false);
  const [editContent, setEditContent] = useState(fact.content);
  const [editReason, setEditReason] = useState('');
  const [anchorEl, setAnchorEl] = useState<null | HTMLElement>(null);
  const [showHistory, setShowHistory] = useState(false);
  const [showDeleteConfirm, setShowDeleteConfirm] = useState(false);

  const handleEdit = () => {
    setIsEditing(true);
    setEditContent(fact.content);
    setEditReason('');
    setAnchorEl(null);
  };

  const handleSave = () => {
    if (editContent.trim() && editContent !== fact.content) {
      onUpdate(fact, editContent.trim(), editReason);
    }
    setIsEditing(false);
  };

  const handleCancel = () => {
    setIsEditing(false);
    setEditContent(fact.content);
    setEditReason('');
  };

  const handleDelete = () => {
    setShowDeleteConfirm(true);
    setAnchorEl(null);
  };

  const confirmDelete = () => {
    onDelete(fact);
    setShowDeleteConfirm(false);
  };

  const getStatusColor = () => {
    switch (fact.review_status) {
      case 'reviewed':
        return 'success';
      case 'rejected':
        return 'error';
      default:
        return 'warning';
    }
  };

  const getConfidenceColor = () => {
    if (fact.confidence >= 0.9) return 'success';
    if (fact.confidence >= 0.7) return 'info';
    if (fact.confidence >= 0.5) return 'warning';
    return 'error';
  };

  const renderContent = () => {
    if (isEditing) {
      return (
        <Box>
          <TextField
            fullWidth
            multiline
            rows={3}
            value={editContent}
            onChange={(e) => setEditContent(e.target.value)}
            variant="outlined"
            size="small"
            sx={{ mb: 1 }}
            autoFocus
          />
          <TextField
            fullWidth
            value={editReason}
            onChange={(e) => setEditReason(e.target.value)}
            placeholder="Reason for edit (optional)"
            variant="outlined"
            size="small"
          />
        </Box>
      );
    }

    return (
      <Typography
        variant="body2"
        sx={{
          cursor: 'pointer',
          '&:hover': { backgroundColor: 'action.hover' },
          p: 1,
          borderRadius: 1,
        }}
        onClick={() => onSelect(fact)}
      >
        {fact.content}
      </Typography>
    );
  };

  const renderMetadata = () => (
    <Stack direction="row" spacing={1} sx={{ mt: 1 }} flexWrap="wrap">
      <Chip
        icon={<CategoryIcon />}
        label={fact.category}
        size="small"
        variant="outlined"
      />
      <Chip
        label={`${Math.round(fact.confidence * 100)}%`}
        size="small"
        color={getConfidenceColor()}
      />
      <Chip
        label={fact.review_status}
        size="small"
        color={getStatusColor()}
      />
      {fact.is_edited && (
        <Chip
          icon={<EditIcon />}
          label="Edited"
          size="small"
          color="secondary"
        />
      )}
    </Stack>
  );

  const renderListView = () => (
    <Card 
      sx={{ 
        mb: 1,
        borderLeft: isSelected ? 4 : 0,
        borderColor: 'primary.main',
        backgroundColor: isSelected ? 'action.selected' : 'background.paper',
      }}
    >
      <CardContent sx={{ pb: 1 }}>
        <Box sx={{ display: 'flex', alignItems: 'flex-start', gap: 2 }}>
          <Box sx={{ flexGrow: 1 }}>
            {renderContent()}
            {renderMetadata()}
          </Box>
          
          <Box sx={{ display: 'flex', flexDirection: 'column', alignItems: 'flex-end' }}>
            <Typography variant="caption" color="text.secondary">
              {fact.source.doc_title}
            </Typography>
            <Typography variant="caption" color="text.secondary">
              Page {fact.source.page}
            </Typography>
            
            <Box sx={{ mt: 1 }}>
              {isEditing ? (
                <>
                  <IconButton size="small" onClick={handleSave} color="primary">
                    <CheckIcon />
                  </IconButton>
                  <IconButton size="small" onClick={handleCancel}>
                    <CloseIcon />
                  </IconButton>
                </>
              ) : (
                <>
                  <IconButton size="small" onClick={handleEdit}>
                    <EditIcon />
                  </IconButton>
                  <IconButton 
                    size="small" 
                    onClick={(e) => setAnchorEl(e.currentTarget)}
                  >
                    <MoreVertIcon />
                  </IconButton>
                </>
              )}
            </Box>
          </Box>
        </Box>
      </CardContent>
    </Card>
  );

  const renderGridView = () => (
    <Card 
      sx={{ 
        height: '100%',
        display: 'flex',
        flexDirection: 'column',
        borderTop: isSelected ? 4 : 0,
        borderColor: 'primary.main',
        backgroundColor: isSelected ? 'action.selected' : 'background.paper',
      }}
    >
      <CardContent sx={{ flexGrow: 1 }}>
        <LinearProgress
          variant="determinate"
          value={fact.confidence * 100}
          color={getConfidenceColor()}
          sx={{ mb: 1, height: 4, borderRadius: 2 }}
        />
        
        {renderContent()}
        
        <Divider sx={{ my: 1 }} />
        
        <Box sx={{ display: 'flex', alignItems: 'center', gap: 1, mb: 1 }}>
          <DocumentIcon fontSize="small" color="action" />
          <Typography variant="caption" color="text.secondary" noWrap>
            {fact.source.doc_title}
          </Typography>
          <Typography variant="caption" color="text.secondary">
            • Page {fact.source.page}
          </Typography>
        </Box>

        {fact.entities && fact.entities.length > 0 && (
          <Box sx={{ mb: 1 }}>
            <Stack direction="row" spacing={0.5} flexWrap="wrap">
              {fact.entities.slice(0, 3).map((entity, index) => (
                <Chip
                  key={index}
                  icon={<TagIcon />}
                  label={entity}
                  size="small"
                  variant="outlined"
                  sx={{ mt: 0.5 }}
                />
              ))}
              {fact.entities.length > 3 && (
                <Chip
                  label={`+${fact.entities.length - 3}`}
                  size="small"
                  variant="outlined"
                  sx={{ mt: 0.5 }}
                />
              )}
            </Stack>
          </Box>
        )}

        {renderMetadata()}
      </CardContent>
      
      <CardActions sx={{ justifyContent: 'space-between', px: 2 }}>
        <Typography variant="caption" color="text.secondary">
          {format(new Date(fact.updated_at), 'MMM d, h:mm a')}
        </Typography>
        
        {isEditing ? (
          <Box>
            <IconButton size="small" onClick={handleSave} color="primary">
              <CheckIcon />
            </IconButton>
            <IconButton size="small" onClick={handleCancel}>
              <CloseIcon />
            </IconButton>
          </Box>
        ) : (
          <Box>
            <Tooltip title="Edit">
              <IconButton size="small" onClick={handleEdit}>
                <EditIcon />
              </IconButton>
            </Tooltip>
            <Tooltip title="More options">
              <IconButton 
                size="small" 
                onClick={(e) => setAnchorEl(e.currentTarget)}
              >
                <MoreVertIcon />
              </IconButton>
            </Tooltip>
          </Box>
        )}
      </CardActions>
    </Card>
  );

  return (
    <>
      {viewMode === 'list' ? renderListView() : renderGridView()}
      
      <Menu
        anchorEl={anchorEl}
        open={Boolean(anchorEl)}
        onClose={() => setAnchorEl(null)}
      >
        <MenuItem onClick={() => { setShowHistory(true); setAnchorEl(null); }}>
          <HistoryIcon fontSize="small" sx={{ mr: 1 }} />
          View History
        </MenuItem>
        <MenuItem onClick={handleDelete}>
          <DeleteIcon fontSize="small" sx={{ mr: 1 }} />
          Delete
        </MenuItem>
      </Menu>

      <Dialog open={showHistory} onClose={() => setShowHistory(false)} maxWidth="sm" fullWidth>
        <DialogTitle>Edit History</DialogTitle>
        <DialogContent>
          {fact.edit_history.length === 0 ? (
            <Typography color="text.secondary">No edit history</Typography>
          ) : (
            <Stack spacing={2}>
              {fact.edit_history.map((edit, index) => (
                <Box key={index}>
                  <Box sx={{ display: 'flex', alignItems: 'center', gap: 1, mb: 1 }}>
                    <PersonIcon fontSize="small" color="action" />
                    <Typography variant="caption" color="text.secondary">
                      {edit.user_id} • {format(new Date(edit.timestamp), 'MMM d, yyyy h:mm a')}
                    </Typography>
                  </Box>
                  <Typography variant="body2" sx={{ pl: 3 }}>
                    {edit.new_content}
                  </Typography>
                  {edit.reason && (
                    <Typography variant="caption" color="text.secondary" sx={{ pl: 3 }}>
                      Reason: {edit.reason}
                    </Typography>
                  )}
                  {index < fact.edit_history.length - 1 && <Divider sx={{ mt: 2 }} />}
                </Box>
              ))}
            </Stack>
          )}
        </DialogContent>
        <DialogActions>
          <Button onClick={() => setShowHistory(false)}>Close</Button>
        </DialogActions>
      </Dialog>

      <Dialog open={showDeleteConfirm} onClose={() => setShowDeleteConfirm(false)}>
        <DialogTitle>Confirm Delete</DialogTitle>
        <DialogContent>
          <Typography>
            Are you sure you want to delete this fact? This action cannot be undone.
          </Typography>
        </DialogContent>
        <DialogActions>
          <Button onClick={() => setShowDeleteConfirm(false)}>Cancel</Button>
          <Button onClick={confirmDelete} color="error" variant="contained">
            Delete
          </Button>
        </DialogActions>
      </Dialog>
    </>
  );
};