import React, { useState, useCallback } from 'react';
import { useDropzone } from 'react-dropzone';
import {
  Box,
  Paper,
  Typography,
  Grid,
  Button,
  IconButton,
  List,
  ListItem,
  ListItemText,
  ListItemSecondaryAction,
  Chip,
  Alert,
  CircularProgress,
  Divider,
} from '@mui/material';
import {
  CloudUpload as CloudUploadIcon,
  Description as DescriptionIcon,
  Delete as DeleteIcon,
  FolderOpen as FolderOpenIcon,
  CheckCircle as CheckCircleIcon,
  Error as ErrorIcon,
} from '@mui/icons-material';
import { useCaseManagement } from '../../hooks/useCaseManagement';
import { discoveryService } from '../../services/discoveryService';
import { useAppDispatch } from '../../hooks/redux';
import { showNotification } from '../../store/slices/uiSlice';

interface UploadedFile {
  file: File;
  status: 'pending' | 'uploading' | 'success' | 'error';
  error?: string | null;
}

interface DiscoveryUploadProps {
  onUploadComplete: (processingId: string) => void;
}

export const DiscoveryUpload: React.FC<DiscoveryUploadProps> = ({ onUploadComplete }) => {
  const [discoveryFiles, setDiscoveryFiles] = useState<UploadedFile[]>([]);
  const [rfpFile, setRfpFile] = useState<UploadedFile | null>(null);
  const [isUploading, setIsUploading] = useState(false);
  const [boxFolderId, setBoxFolderId] = useState<string | null>(null);
  
  const { selectedCase } = useCaseManagement();
  const dispatch = useAppDispatch();

  const validateFile = (file: File): string | null => {
    if (file.type !== 'application/pdf') {
      return 'Only PDF files are allowed';
    }
    if (file.size > 100 * 1024 * 1024) {
      return 'File size must be less than 100MB';
    }
    return null;
  };

  const onDiscoveryDrop = useCallback((acceptedFiles: File[]) => {
    const newFiles: UploadedFile[] = acceptedFiles.map(file => {
      const error = validateFile(file);
      return {
        file,
        status: error ? 'error' : 'pending',
        error,
      };
    });
    setDiscoveryFiles(prev => [...prev, ...newFiles]);
  }, []);

  const onRfpDrop = useCallback((acceptedFiles: File[]) => {
    if (acceptedFiles.length > 0) {
      const file = acceptedFiles[0];
      const error = validateFile(file);
      setRfpFile({
        file,
        status: error ? 'error' : 'pending',
        error,
      });
    }
  }, []);

  const discoveryDropzone = useDropzone({
    onDrop: onDiscoveryDrop,
    accept: {
      'application/pdf': ['.pdf'],
    },
    multiple: true,
  });

  const rfpDropzone = useDropzone({
    onDrop: onRfpDrop,
    accept: {
      'application/pdf': ['.pdf'],
    },
    multiple: false,
  });

  const removeDiscoveryFile = (index: number) => {
    setDiscoveryFiles(prev => prev.filter((_, i) => i !== index));
  };

  const removeRfpFile = () => {
    setRfpFile(null);
  };

  const handleBoxSelect = async () => {
    try {
      if (!window.Box) {
        await loadBoxSDK();
      }
      
      const boxPicker = new window.Box.ContentPicker();
      boxPicker.addListener('select', (files: any[]) => {
        if (files.length > 0) {
          setBoxFolderId(files[0].id);
          dispatch(showNotification({
            message: `Selected Box folder: ${files[0].name}`,
            severity: 'success',
          }));
        }
      });
      
      boxPicker.show('0', {
        container: '.box-picker-container',
        logoUrl: '/box-logo.png',
        size: 'large',
        isTouch: false,
        filter: ['.pdf'],
        canSetShareAccess: false,
        canUpload: false,
        canCreateNewFolder: false,
      });
    } catch (error) {
      dispatch(showNotification({
        message: 'Failed to load Box picker',
        severity: 'error',
      }));
    }
  };

  const loadBoxSDK = (): Promise<void> => {
    return new Promise((resolve, reject) => {
      if (window.Box) {
        resolve();
        return;
      }
      
      const script = document.createElement('script');
      script.src = 'https://cdn01.boxcdn.net/platform/elements/17.1.0/en-US/picker.js';
      script.onload = () => resolve();
      script.onerror = () => reject(new Error('Failed to load Box SDK'));
      document.head.appendChild(script);
    });
  };

  const handleUpload = async () => {
    if (!selectedCase) {
      dispatch(showNotification({
        message: 'Please select a case first',
        severity: 'error',
      }));
      return;
    }

    const validDiscoveryFiles = discoveryFiles.filter(f => f.status !== 'error');
    if (validDiscoveryFiles.length === 0 && !boxFolderId) {
      dispatch(showNotification({
        message: 'Please add discovery documents or select a Box folder',
        severity: 'error',
      }));
      return;
    }

    setIsUploading(true);

    try {
      const formData = new FormData();
      formData.append('case_id', selectedCase.case_name);
      formData.append('case_name', selectedCase.case_name);

      validDiscoveryFiles.forEach((uploadedFile, index) => {
        formData.append('discovery_files', uploadedFile.file);
        setDiscoveryFiles(prev => 
          prev.map((f, i) => i === index ? { ...f, status: 'uploading' } : f)
        );
      });

      if (rfpFile && rfpFile.status !== 'error') {
        formData.append('rfp_file', rfpFile.file);
        setRfpFile(prev => prev ? { ...prev, status: 'uploading' } : null);
      }

      if (boxFolderId) {
        formData.append('box_folder_id', boxFolderId);
      }

      const response = await discoveryService.processDiscovery(formData);
      
      setDiscoveryFiles(prev => 
        prev.map(f => ({ ...f, status: 'success' }))
      );
      if (rfpFile) {
        setRfpFile(prev => prev ? { ...prev, status: 'success' } : null);
      }

      dispatch(showNotification({
        message: 'Discovery processing started successfully',
        severity: 'success',
      }));

      onUploadComplete(response.processing_id);
    } catch (error: any) {
      dispatch(showNotification({
        message: error.message || 'Failed to start discovery processing',
        severity: 'error',
      }));
      
      setDiscoveryFiles(prev => 
        prev.map(f => ({ ...f, status: 'error', error: 'Upload failed' }))
      );
      if (rfpFile) {
        setRfpFile(prev => prev ? { ...prev, status: 'error', error: 'Upload failed' } : null);
      }
    } finally {
      setIsUploading(false);
    }
  };

  const renderFileList = (files: UploadedFile[], onRemove: (index: number) => void) => (
    <List dense>
      {files.map((uploadedFile, index) => (
        <ListItem key={index}>
          <DescriptionIcon sx={{ mr: 2, color: 'text.secondary' }} />
          <ListItemText
            primary={uploadedFile.file.name}
            secondary={
              uploadedFile.error ? (
                <Typography variant="caption" color="error">
                  {uploadedFile.error}
                </Typography>
              ) : (
                `${(uploadedFile.file.size / 1024 / 1024).toFixed(2)} MB`
              )
            }
          />
          <ListItemSecondaryAction>
            {uploadedFile.status === 'uploading' && <CircularProgress size={20} />}
            {uploadedFile.status === 'success' && <CheckCircleIcon color="success" />}
            {uploadedFile.status === 'error' && <ErrorIcon color="error" />}
            {uploadedFile.status === 'pending' && (
              <IconButton edge="end" onClick={() => onRemove(index)} size="small">
                <DeleteIcon />
              </IconButton>
            )}
          </ListItemSecondaryAction>
        </ListItem>
      ))}
    </List>
  );

  return (
    <Box>
      <Grid container spacing={3}>
        <Grid item xs={12} md={6}>
          <Paper sx={{ p: 3 }}>
            <Typography variant="h6" gutterBottom>
              Discovery Documents
            </Typography>
            <Typography variant="body2" color="text.secondary" paragraph>
              Upload concatenated discovery response PDFs for processing
            </Typography>
            
            <Box
              {...discoveryDropzone.getRootProps()}
              sx={{
                border: '2px dashed',
                borderColor: discoveryDropzone.isDragActive ? 'primary.main' : 'divider',
                borderRadius: 2,
                p: 3,
                textAlign: 'center',
                cursor: 'pointer',
                backgroundColor: discoveryDropzone.isDragActive ? 'action.hover' : 'background.paper',
                transition: 'all 0.2s ease',
                '&:hover': {
                  backgroundColor: 'action.hover',
                },
              }}
            >
              <input {...discoveryDropzone.getInputProps()} />
              <CloudUploadIcon sx={{ fontSize: 48, color: 'text.secondary', mb: 2 }} />
              <Typography variant="body1" gutterBottom>
                {discoveryDropzone.isDragActive
                  ? 'Drop PDFs here...'
                  : 'Drag & drop PDFs here, or click to select'}
              </Typography>
              <Typography variant="caption" color="text.secondary">
                Multiple files allowed • PDF only • Max 100MB per file
              </Typography>
            </Box>

            {discoveryFiles.length > 0 && (
              <Box sx={{ mt: 2 }}>
                {renderFileList(discoveryFiles, removeDiscoveryFile)}
              </Box>
            )}

            <Divider sx={{ my: 2 }} />

            <Button
              variant="outlined"
              startIcon={<FolderOpenIcon />}
              onClick={handleBoxSelect}
              fullWidth
              sx={{ mb: 1 }}
            >
              Select from Box Folder
            </Button>
            {boxFolderId && (
              <Chip
                label={`Box Folder Selected: ${boxFolderId}`}
                color="primary"
                variant="outlined"
                size="small"
                onDelete={() => setBoxFolderId(null)}
              />
            )}
            <div className="box-picker-container" />
          </Paper>
        </Grid>

        <Grid item xs={12} md={6}>
          <Paper sx={{ p: 3 }}>
            <Typography variant="h6" gutterBottom>
              Request for Production (Optional)
            </Typography>
            <Typography variant="body2" color="text.secondary" paragraph>
              Upload the RFP document to match responses
            </Typography>
            
            <Box
              {...rfpDropzone.getRootProps()}
              sx={{
                border: '2px dashed',
                borderColor: rfpDropzone.isDragActive ? 'primary.main' : 'divider',
                borderRadius: 2,
                p: 3,
                textAlign: 'center',
                cursor: 'pointer',
                backgroundColor: rfpDropzone.isDragActive ? 'action.hover' : 'background.paper',
                transition: 'all 0.2s ease',
                '&:hover': {
                  backgroundColor: 'action.hover',
                },
              }}
            >
              <input {...rfpDropzone.getInputProps()} />
              <DescriptionIcon sx={{ fontSize: 48, color: 'text.secondary', mb: 2 }} />
              <Typography variant="body1" gutterBottom>
                {rfpDropzone.isDragActive
                  ? 'Drop RFP here...'
                  : 'Drag & drop RFP PDF here, or click to select'}
              </Typography>
              <Typography variant="caption" color="text.secondary">
                Single file only • PDF format
              </Typography>
            </Box>

            {rfpFile && (
              <Box sx={{ mt: 2 }}>
                <List dense>
                  <ListItem>
                    <DescriptionIcon sx={{ mr: 2, color: 'text.secondary' }} />
                    <ListItemText
                      primary={rfpFile.file.name}
                      secondary={
                        rfpFile.error ? (
                          <Typography variant="caption" color="error">
                            {rfpFile.error}
                          </Typography>
                        ) : (
                          `${(rfpFile.file.size / 1024 / 1024).toFixed(2)} MB`
                        )
                      }
                    />
                    <ListItemSecondaryAction>
                      {rfpFile.status === 'uploading' && <CircularProgress size={20} />}
                      {rfpFile.status === 'success' && <CheckCircleIcon color="success" />}
                      {rfpFile.status === 'error' && <ErrorIcon color="error" />}
                      {rfpFile.status === 'pending' && (
                        <IconButton edge="end" onClick={removeRfpFile} size="small">
                          <DeleteIcon />
                        </IconButton>
                      )}
                    </ListItemSecondaryAction>
                  </ListItem>
                </List>
              </Box>
            )}
          </Paper>
        </Grid>

        <Grid item xs={12}>
          {!selectedCase && (
            <Alert severity="warning" sx={{ mb: 2 }}>
              Please select a case before uploading documents
            </Alert>
          )}
          
          <Button
            variant="contained"
            size="large"
            onClick={handleUpload}
            disabled={isUploading || !selectedCase || (discoveryFiles.length === 0 && !boxFolderId)}
            startIcon={isUploading ? <CircularProgress size={20} /> : <CloudUploadIcon />}
            fullWidth
          >
            {isUploading ? 'Processing...' : 'Start Discovery Processing'}
          </Button>
        </Grid>
      </Grid>
    </Box>
  );
};

declare global {
  interface Window {
    Box: any;
  }
}