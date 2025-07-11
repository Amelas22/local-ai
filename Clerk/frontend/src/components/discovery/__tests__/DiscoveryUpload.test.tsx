import React from 'react';
import { render, screen, fireEvent, waitFor } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { Provider } from 'react-redux';
import { configureStore } from '@reduxjs/toolkit';
import { DiscoveryUpload } from '../DiscoveryUpload';
import { discoveryService } from '../../../services/discoveryService';
import uiSlice from '../../../store/slices/uiSlice';

// Mock dependencies
jest.mock('../../../services/discoveryService');
jest.mock('../../../hooks/useCaseManagement', () => ({
  useCaseManagement: () => ({
    selectedCase: {
      id: 'test-case-123',
      name: 'Test v Case 2024',
    },
  }),
}));

// Mock react-dropzone
jest.mock('react-dropzone', () => ({
  useDropzone: ({ onDrop, accept, multiple }: any) => {
    const inputProps = {
      type: 'file',
      accept: Object.keys(accept).join(','),
      multiple,
      onChange: (e: any) => {
        if (e.target.files) {
          onDrop(Array.from(e.target.files));
        }
      },
    };
    
    return {
      getRootProps: () => ({
        'data-testid': multiple ? 'discovery-dropzone' : 'rfp-dropzone',
      }),
      getInputProps: () => inputProps,
      isDragActive: false,
    };
  },
}));

const mockStore = configureStore({
  reducer: {
    ui: uiSlice,
  },
});

const renderComponent = (onUploadComplete = jest.fn()) => {
  return render(
    <Provider store={mockStore}>
      <DiscoveryUpload onUploadComplete={onUploadComplete} />
    </Provider>
  );
};

describe('DiscoveryUpload', () => {
  beforeEach(() => {
    jest.clearAllMocks();
  });

  it('renders upload zones correctly', () => {
    renderComponent();
    
    expect(screen.getByText('Discovery Documents')).toBeInTheDocument();
    expect(screen.getByText('Request for Production (Optional)')).toBeInTheDocument();
    expect(screen.getByText('Start Discovery Processing')).toBeInTheDocument();
  });

  it('validates PDF files only', async () => {
    renderComponent();
    
    const file = new File(['content'], 'test.txt', { type: 'text/plain' });
    const input = screen.getByTestId('discovery-dropzone').querySelector('input[type="file"]');
    
    fireEvent.change(input!, { target: { files: [file] } });
    
    await waitFor(() => {
      expect(screen.getByText('Only PDF files are allowed')).toBeInTheDocument();
    });
  });

  it('validates file size limit', async () => {
    renderComponent();
    
    // Create a file larger than 100MB
    const largeContent = new Array(101 * 1024 * 1024).join('a');
    const file = new File([largeContent], 'large.pdf', { type: 'application/pdf' });
    const input = screen.getByTestId('discovery-dropzone').querySelector('input[type="file"]');
    
    fireEvent.change(input!, { target: { files: [file] } });
    
    await waitFor(() => {
      expect(screen.getByText('File size must be less than 100MB')).toBeInTheDocument();
    });
  });

  it('accepts valid PDF files', async () => {
    renderComponent();
    
    const file = new File(['pdf content'], 'test.pdf', { type: 'application/pdf' });
    const input = screen.getByTestId('discovery-dropzone').querySelector('input[type="file"]');
    
    fireEvent.change(input!, { target: { files: [file] } });
    
    await waitFor(() => {
      expect(screen.getByText('test.pdf')).toBeInTheDocument();
      expect(screen.queryByText('Only PDF files are allowed')).not.toBeInTheDocument();
    });
  });

  it('allows removing files', async () => {
    renderComponent();
    
    const file = new File(['pdf content'], 'test.pdf', { type: 'application/pdf' });
    const input = screen.getByTestId('discovery-dropzone').querySelector('input[type="file"]');
    
    fireEvent.change(input!, { target: { files: [file] } });
    
    await waitFor(() => {
      expect(screen.getByText('test.pdf')).toBeInTheDocument();
    });
    
    const deleteButton = screen.getByRole('button', { name: /delete/i });
    fireEvent.click(deleteButton);
    
    expect(screen.queryByText('test.pdf')).not.toBeInTheDocument();
  });

  it('handles successful upload', async () => {
    const onUploadComplete = jest.fn();
    const mockResponse = { processing_id: 'proc-123', status: 'started' };
    
    (discoveryService.processDiscovery as jest.Mock).mockResolvedValue(mockResponse);
    
    renderComponent(onUploadComplete);
    
    // Add a file
    const file = new File(['pdf content'], 'test.pdf', { type: 'application/pdf' });
    const input = screen.getByTestId('discovery-dropzone').querySelector('input[type="file"]');
    fireEvent.change(input!, { target: { files: [file] } });
    
    // Click upload button
    const uploadButton = screen.getByText('Start Discovery Processing');
    fireEvent.click(uploadButton);
    
    await waitFor(() => {
      expect(discoveryService.processDiscovery).toHaveBeenCalled();
      expect(onUploadComplete).toHaveBeenCalledWith('proc-123');
    });
  });

  it('handles upload errors', async () => {
    const error = new Error('Upload failed');
    (discoveryService.processDiscovery as jest.Mock).mockRejectedValue(error);
    
    renderComponent();
    
    // Add a file
    const file = new File(['pdf content'], 'test.pdf', { type: 'application/pdf' });
    const input = screen.getByTestId('discovery-dropzone').querySelector('input[type="file"]');
    fireEvent.change(input!, { target: { files: [file] } });
    
    // Click upload button
    const uploadButton = screen.getByText('Start Discovery Processing');
    fireEvent.click(uploadButton);
    
    await waitFor(() => {
      expect(screen.getByText('0.00 MB')).toBeInTheDocument(); // File still shown but with error
    });
  });

  it('shows warning when no case is selected', () => {
    // Mock no case selected
    jest.resetModules();
    jest.doMock('../../../hooks/useCaseManagement', () => ({
      useCaseManagement: () => ({
        selectedCase: null,
      }),
    }));
    
    renderComponent();
    
    expect(screen.getByText('Please select a case before uploading documents')).toBeInTheDocument();
  });

  it('disables upload button when no files or folder selected', () => {
    renderComponent();
    
    const uploadButton = screen.getByText('Start Discovery Processing');
    expect(uploadButton).toBeDisabled();
  });

  it('enables upload button when files are added', async () => {
    renderComponent();
    
    const file = new File(['pdf content'], 'test.pdf', { type: 'application/pdf' });
    const input = screen.getByTestId('discovery-dropzone').querySelector('input[type="file"]');
    
    fireEvent.change(input!, { target: { files: [file] } });
    
    await waitFor(() => {
      const uploadButton = screen.getByText('Start Discovery Processing');
      expect(uploadButton).not.toBeDisabled();
    });
  });
});