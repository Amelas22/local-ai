import React from 'react';
import { render, screen, waitFor } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { QueryClient, QueryClientProvider } from '@tanstack/react-query';
import { describe, it, expect, vi, beforeEach, beforeAll, afterAll } from 'vitest';
import { LetterExportDialog } from '../LetterExportDialog';
import { goodFaithLetterAPI } from '../../../../services/api/goodFaithLetter';
import { GeneratedLetter } from '../../../../types/goodFaithLetter.types';

vi.mock('../../../../services/api/goodFaithLetter');

// Mock window functions
const mockCreateObjectURL = vi.fn();
const mockRevokeObjectURL = vi.fn();
const mockClick = vi.fn();
const mockConfirm = vi.fn();

// Store original window functions
const originalCreateObjectURL = window.URL.createObjectURL;
const originalRevokeObjectURL = window.URL.revokeObjectURL;
const originalCreateElement = document.createElement;
const originalConfirm = window.confirm;

beforeAll(() => {
  window.URL.createObjectURL = mockCreateObjectURL;
  window.URL.revokeObjectURL = mockRevokeObjectURL;
  window.confirm = mockConfirm;
  
  // Mock createElement to return a mock anchor element
  document.createElement = vi.fn((tagName) => {
    if (tagName === 'a') {
      return {
        href: '',
        download: '',
        click: mockClick,
        style: {},
        setAttribute: vi.fn()
      } as HTMLAnchorElement;
    }
    return originalCreateElement.call(document, tagName);
  });
});

afterAll(() => {
  window.URL.createObjectURL = originalCreateObjectURL;
  window.URL.revokeObjectURL = originalRevokeObjectURL;
  document.createElement = originalCreateElement;
  window.confirm = originalConfirm;
});

const mockLetter: GeneratedLetter = {
  id: 'letter-123',
  report_id: 'report-456',
  case_name: 'Smith v. Jones',
  jurisdiction: 'federal',
  content: 'Letter content...',
  status: 'finalized',
  version: 2,
  agent_execution_id: 'exec-789',
  created_at: '2024-10-04T10:00:00Z',
  edit_history: []
};

describe('LetterExportDialog', () => {
  let queryClient: QueryClient;
  const user = userEvent.setup();
  const mockOnClose = vi.fn();

  beforeEach(() => {
    queryClient = new QueryClient({
      defaultOptions: {
        queries: {
          retry: false,
        },
      },
    });
    vi.clearAllMocks();
    mockCreateObjectURL.mockReturnValue('blob:http://localhost/test-blob');
    mockConfirm.mockReturnValue(true);
  });

  const renderComponent = (letter: GeneratedLetter = mockLetter, open = true) => {
    return render(
      <QueryClientProvider client={queryClient}>
        <LetterExportDialog 
          open={open} 
          onClose={mockOnClose} 
          letter={letter} 
        />
      </QueryClientProvider>
    );
  };

  it('should render export dialog with format options', () => {
    renderComponent();

    expect(screen.getByText('Export Good Faith Letter')).toBeInTheDocument();
    expect(screen.getByText('PDF Document')).toBeInTheDocument();
    expect(screen.getByText('Word Document')).toBeInTheDocument();
    expect(screen.getByText('Best for printing and official records')).toBeInTheDocument();
    expect(screen.getByText('Editable format for further modifications')).toBeInTheDocument();
  });

  it('should show recommended badge for PDF format', () => {
    renderComponent();

    expect(screen.getByText('Recommended')).toBeInTheDocument();
  });

  it('should display letter details', () => {
    renderComponent();

    expect(screen.getByText(/Case: Smith v. Jones/)).toBeInTheDocument();
    expect(screen.getByText(/Jurisdiction: federal/)).toBeInTheDocument();
    expect(screen.getByText(/Version: 2/)).toBeInTheDocument();
    expect(screen.getByText(/Status: finalized/)).toBeInTheDocument();
  });

  it('should show warning for draft letters', () => {
    const draftLetter = { ...mockLetter, status: 'draft' as const };
    renderComponent(draftLetter);

    expect(screen.getByText(/This letter is still in draft status/)).toBeInTheDocument();
  });

  it('should select PDF format by default', () => {
    renderComponent();

    const pdfRadio = screen.getByRole('radio', { name: /pdf document/i });
    expect(pdfRadio).toBeChecked();
  });

  it('should allow changing export format', async () => {
    renderComponent();

    const wordOption = screen.getByText('Word Document');
    await user.click(wordOption);

    const wordRadio = screen.getByRole('radio', { name: /word document/i });
    expect(wordRadio).toBeChecked();
  });

  it('should export PDF successfully', async () => {
    const mockBlob = new Blob(['PDF content'], { type: 'application/pdf' });
    (goodFaithLetterAPI.exportLetter as ReturnType<typeof vi.fn>).mockResolvedValue(mockBlob);

    renderComponent();

    const exportButton = screen.getByRole('button', { name: /export/i });
    await user.click(exportButton);

    await waitFor(() => {
      expect(goodFaithLetterAPI.exportLetter).toHaveBeenCalledWith('letter-123', 'pdf');
      expect(mockCreateObjectURL).toHaveBeenCalledWith(mockBlob);
      expect(mockClick).toHaveBeenCalled();
      expect(mockRevokeObjectURL).toHaveBeenCalled();
    });

    expect(screen.getByText('Letter exported successfully!')).toBeInTheDocument();
  });

  it('should export Word document successfully', async () => {
    const mockBlob = new Blob(['Word content'], { type: 'application/vnd.openxmlformats-officedocument.wordprocessingml.document' });
    (goodFaithLetterAPI.exportLetter as ReturnType<typeof vi.fn>).mockResolvedValue(mockBlob);

    renderComponent();

    const wordOption = screen.getByText('Word Document');
    await user.click(wordOption);

    const exportButton = screen.getByRole('button', { name: /export/i });
    await user.click(exportButton);

    await waitFor(() => {
      expect(goodFaithLetterAPI.exportLetter).toHaveBeenCalledWith('letter-123', 'docx');
    });
  });

  it('should confirm before exporting draft letter', async () => {
    const draftLetter = { ...mockLetter, status: 'draft' as const };
    renderComponent(draftLetter);

    const exportButton = screen.getByRole('button', { name: /export/i });
    await user.click(exportButton);

    expect(mockConfirm).toHaveBeenCalledWith(
      'This letter is still in draft/review status. Are you sure you want to export it?'
    );
  });

  it('should not export if user cancels confirmation for draft letter', async () => {
    mockConfirm.mockReturnValue(false);
    const draftLetter = { ...mockLetter, status: 'draft' as const };
    renderComponent(draftLetter);

    const exportButton = screen.getByRole('button', { name: /export/i });
    await user.click(exportButton);

    expect(goodFaithLetterAPI.exportLetter).not.toHaveBeenCalled();
  });

  it('should handle export errors', async () => {
    (goodFaithLetterAPI.exportLetter as ReturnType<typeof vi.fn>).mockRejectedValue(
      new Error('Export failed')
    );

    renderComponent();

    const exportButton = screen.getByRole('button', { name: /export/i });
    await user.click(exportButton);

    await waitFor(() => {
      expect(screen.getByText('Failed to export letter. Please try again.')).toBeInTheDocument();
    });
  });

  it('should disable buttons during export', async () => {
    (goodFaithLetterAPI.exportLetter as ReturnType<typeof vi.fn>).mockImplementation(
      () => new Promise(resolve => setTimeout(resolve, 100))
    );

    renderComponent();

    const exportButton = screen.getByRole('button', { name: /export/i });
    const cancelButton = screen.getByRole('button', { name: /cancel/i });
    
    await user.click(exportButton);

    expect(exportButton).toBeDisabled();
    expect(cancelButton).toBeDisabled();
    expect(screen.getByText('Exporting...')).toBeInTheDocument();
  });

  it('should close dialog when cancel is clicked', async () => {
    renderComponent();

    const cancelButton = screen.getByRole('button', { name: /cancel/i });
    await user.click(cancelButton);

    expect(mockOnClose).toHaveBeenCalled();
  });

  it('should close dialog when X button is clicked', async () => {
    renderComponent();

    const closeButton = screen.getByRole('button', { name: '' });
    await user.click(closeButton);

    expect(mockOnClose).toHaveBeenCalled();
  });

  it('should generate proper filename', async () => {
    const mockBlob = new Blob(['PDF content'], { type: 'application/pdf' });
    (goodFaithLetterAPI.exportLetter as ReturnType<typeof vi.fn>).mockResolvedValue(mockBlob);

    renderComponent();

    const exportButton = screen.getByRole('button', { name: /export/i });
    await user.click(exportButton);

    await waitFor(() => {
      const createElementCall = (document.createElement as ReturnType<typeof vi.fn>).mock.calls.find(
        call => call[0] === 'a'
      );
      expect(createElementCall).toBeTruthy();
      
      const anchorElement = (document.createElement as ReturnType<typeof vi.fn>).mock.results.find(
        result => result.value && result.value.download !== undefined
      )?.value;
      
      expect(anchorElement.download).toMatch(/Good_Faith_Letter_Smith_v__Jones_\d{4}-\d{2}-\d{2}\.pdf/);
    });
  });

  it('should auto-close dialog after successful export', async () => {
    vi.useFakeTimers();
    const mockBlob = new Blob(['PDF content'], { type: 'application/pdf' });
    (goodFaithLetterAPI.exportLetter as ReturnType<typeof vi.fn>).mockResolvedValue(mockBlob);

    renderComponent();

    const exportButton = screen.getByRole('button', { name: /export/i });
    await user.click(exportButton);

    await waitFor(() => {
      expect(screen.getByText('Letter exported successfully!')).toBeInTheDocument();
    });

    vi.advanceTimersByTime(2000);

    await waitFor(() => {
      expect(mockOnClose).toHaveBeenCalled();
    });

    vi.useRealTimers();
  });
});