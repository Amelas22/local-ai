import React from 'react';
import { render, screen, waitFor, within } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { QueryClient, QueryClientProvider } from '@tanstack/react-query';
import { MemoryRouter, Route, Routes } from 'react-router-dom';
import { describe, it, expect, vi, beforeEach } from 'vitest';
import { GoodFaithLetterPage } from '../GoodFaithLetterPage';
import { goodFaithLetterAPI } from '../../../services/api/goodFaithLetter';
import { GeneratedLetter, LetterEdit } from '../../../types/goodFaithLetter.types';

// Mock dependencies
vi.mock('../../../services/api/goodFaithLetter');
vi.mock('../../../hooks/useWebSocket', () => ({
  useWebSocket: () => ({
    on: vi.fn(),
    off: vi.fn(),
    emit: vi.fn()
  })
}));

const mockLetter: GeneratedLetter = {
  id: 'letter-123',
  report_id: 'report-456',
  case_name: 'Smith v. Jones',
  jurisdiction: 'federal',
  content: 'Letter content...',
  status: 'draft',
  version: 2,
  agent_execution_id: 'exec-789',
  created_at: '2024-10-04T10:00:00Z',
  edit_history: []
};

const mockVersions: LetterEdit[] = [
  {
    id: 'edit-1',
    letter_id: 'letter-123',
    version: 1,
    editor_id: 'user-1',
    editor_name: 'John Doe',
    section_edits: [{ section: 'body', content: 'Initial draft' }],
    edit_timestamp: '2024-10-01T10:00:00Z'
  },
  {
    id: 'edit-2',
    letter_id: 'letter-123',
    version: 2,
    editor_id: 'user-2',
    editor_name: 'Jane Smith',
    section_edits: [{ section: 'body', content: 'Updated content' }],
    edit_timestamp: '2024-10-02T14:30:00Z'
  }
];

describe('GoodFaithLetterPage Integration Tests', () => {
  let queryClient: QueryClient;
  const user = userEvent.setup();

  beforeEach(() => {
    queryClient = new QueryClient({
      defaultOptions: {
        queries: {
          retry: false,
        },
      },
    });
    vi.clearAllMocks();
  });

  const renderPage = (letterId = 'letter-123') => {
    return render(
      <QueryClientProvider client={queryClient}>
        <MemoryRouter initialEntries={[`/letter/${letterId}`]}>
          <Routes>
            <Route path="/letter/:letterId" element={<GoodFaithLetterPage />} />
          </Routes>
        </MemoryRouter>
      </QueryClientProvider>
    );
  };

  it('should render all tabs and components', async () => {
    (goodFaithLetterAPI.getLetter as ReturnType<typeof vi.fn>).mockResolvedValue(mockLetter);
    (goodFaithLetterAPI.getLetterVersions as ReturnType<typeof vi.fn>).mockResolvedValue(mockVersions);

    renderPage();

    await waitFor(() => {
      expect(screen.getByText('Good Faith Letter')).toBeInTheDocument();
    });

    // Check all tabs are present
    expect(screen.getByRole('tab', { name: /preview/i })).toBeInTheDocument();
    expect(screen.getByRole('tab', { name: /edit/i })).toBeInTheDocument();
    expect(screen.getByRole('tab', { name: /version history/i })).toBeInTheDocument();
    expect(screen.getByRole('tab', { name: /email/i })).toBeInTheDocument();

    // Preview tab should be active by default
    expect(screen.getByRole('tab', { name: /preview/i })).toHaveAttribute('aria-selected', 'true');
  });

  it('should disable edit tab for finalized letters', async () => {
    const finalizedLetter = { ...mockLetter, status: 'finalized' as const };
    (goodFaithLetterAPI.getLetter as ReturnType<typeof vi.fn>).mockResolvedValue(finalizedLetter);

    renderPage();

    await waitFor(() => {
      const editTab = screen.getByRole('tab', { name: /edit/i });
      expect(editTab).toBeDisabled();
    });
  });

  it('should navigate between tabs', async () => {
    (goodFaithLetterAPI.getLetter as ReturnType<typeof vi.fn>).mockResolvedValue(mockLetter);
    (goodFaithLetterAPI.getLetterVersions as ReturnType<typeof vi.fn>).mockResolvedValue(mockVersions);

    renderPage();

    await waitFor(() => {
      expect(screen.getByText('Good Faith Letter Preview')).toBeInTheDocument();
    });

    // Click on Edit tab
    const editTab = screen.getByRole('tab', { name: /edit/i });
    await user.click(editTab);

    await waitFor(() => {
      expect(screen.getByText('Edit Good Faith Letter')).toBeInTheDocument();
    });

    // Click on Version History tab
    const historyTab = screen.getByRole('tab', { name: /version history/i });
    await user.click(historyTab);

    await waitFor(() => {
      expect(screen.getByText('Version History')).toBeInTheDocument();
    });

    // Click on Email tab
    const emailTab = screen.getByRole('tab', { name: /email/i });
    await user.click(emailTab);

    await waitFor(() => {
      expect(screen.getByText('Email Preparation')).toBeInTheDocument();
    });
  });

  it('should open export dialog when export button is clicked', async () => {
    (goodFaithLetterAPI.getLetter as ReturnType<typeof vi.fn>).mockResolvedValue(mockLetter);

    renderPage();

    await waitFor(() => {
      expect(screen.getByText('Good Faith Letter')).toBeInTheDocument();
    });

    const exportButton = screen.getByRole('button', { name: /export/i });
    await user.click(exportButton);

    expect(screen.getByText('Export Good Faith Letter')).toBeInTheDocument();
  });

  it('should handle letter editing workflow', async () => {
    (goodFaithLetterAPI.getLetter as ReturnType<typeof vi.fn>).mockResolvedValue(mockLetter);
    const updatedLetter = { ...mockLetter, version: 3 };
    (goodFaithLetterAPI.customizeLetter as ReturnType<typeof vi.fn>).mockResolvedValue(updatedLetter);

    renderPage();

    await waitFor(() => {
      expect(screen.getByText('Good Faith Letter')).toBeInTheDocument();
    });

    // Navigate to edit tab
    const editTab = screen.getByRole('tab', { name: /edit/i });
    await user.click(editTab);

    await waitFor(() => {
      expect(screen.getByText('Edit Good Faith Letter')).toBeInTheDocument();
    });

    // Find and click an edit button (assuming there's at least one section)
    const editButtons = screen.getAllByRole('button', { name: /edit section/i });
    await user.click(editButtons[0]);

    // Type in the textarea
    const textarea = screen.getByRole('textbox');
    await user.type(textarea, ' Updated text');

    // Save changes
    const saveButton = screen.getByRole('button', { name: /save all changes/i });
    await user.click(saveButton);

    await waitFor(() => {
      expect(goodFaithLetterAPI.customizeLetter).toHaveBeenCalled();
    });
  });

  it('should handle version restoration workflow', async () => {
    (goodFaithLetterAPI.getLetter as ReturnType<typeof vi.fn>).mockResolvedValue(mockLetter);
    (goodFaithLetterAPI.getLetterVersions as ReturnType<typeof vi.fn>).mockResolvedValue(mockVersions);
    const restoredLetter = { ...mockLetter, version: 3 };
    (goodFaithLetterAPI.restoreVersion as ReturnType<typeof vi.fn>).mockResolvedValue(restoredLetter);

    renderPage();

    await waitFor(() => {
      expect(screen.getByText('Good Faith Letter')).toBeInTheDocument();
    });

    // Navigate to version history tab
    const historyTab = screen.getByRole('tab', { name: /version history/i });
    await user.click(historyTab);

    await waitFor(() => {
      expect(screen.getByText('Version History')).toBeInTheDocument();
    });

    // Click restore on version 1
    const restoreButtons = screen.getAllByRole('button', { name: /restore this version/i });
    await user.click(restoreButtons[0]);

    // Confirm restoration
    const confirmButton = screen.getByRole('button', { name: /^restore$/i });
    await user.click(confirmButton);

    await waitFor(() => {
      expect(goodFaithLetterAPI.restoreVersion).toHaveBeenCalledWith('letter-123', 1);
    });
  });

  it('should handle email preparation workflow', async () => {
    (goodFaithLetterAPI.getLetter as ReturnType<typeof vi.fn>).mockResolvedValue(mockLetter);

    renderPage();

    await waitFor(() => {
      expect(screen.getByText('Good Faith Letter')).toBeInTheDocument();
    });

    // Navigate to email tab
    const emailTab = screen.getByRole('tab', { name: /email/i });
    await user.click(emailTab);

    await waitFor(() => {
      expect(screen.getByText('Email Preparation')).toBeInTheDocument();
    });

    // Fill in recipient
    const toField = screen.getByLabelText('To');
    await user.type(toField, 'opposing@counsel.com{enter}');

    // Include evidence
    const includeEvidenceCheckbox = screen.getByLabelText('Include supporting evidence documents');
    await user.click(includeEvidenceCheckbox);

    // Send email
    const sendButton = screen.getByRole('button', { name: /send email/i });
    await user.click(sendButton);

    // Should show confirmation dialog for draft letter
    expect(screen.getByText('Send Good Faith Letter?')).toBeInTheDocument();
  });

  it('should refresh letter data when refresh button is clicked', async () => {
    (goodFaithLetterAPI.getLetter as ReturnType<typeof vi.fn>).mockResolvedValue(mockLetter);

    renderPage();

    await waitFor(() => {
      expect(screen.getByText('Good Faith Letter')).toBeInTheDocument();
    });

    const refreshButton = screen.getByRole('button', { name: /refresh/i });
    await user.click(refreshButton);

    expect(goodFaithLetterAPI.getLetter).toHaveBeenCalledTimes(2);
  });

  it('should show error state and retry option', async () => {
    (goodFaithLetterAPI.getLetter as ReturnType<typeof vi.fn>).mockRejectedValueOnce(new Error('Network error'));

    renderPage();

    await waitFor(() => {
      expect(screen.getByText(/Failed to load letter/)).toBeInTheDocument();
    });

    const retryButton = screen.getByRole('button', { name: /retry/i });
    
    // Mock successful response for retry
    (goodFaithLetterAPI.getLetter as ReturnType<typeof vi.fn>).mockResolvedValueOnce(mockLetter);
    
    await user.click(retryButton);

    await waitFor(() => {
      expect(screen.getByText('Good Faith Letter Preview')).toBeInTheDocument();
    });
  });

  it('should handle breadcrumb navigation', async () => {
    (goodFaithLetterAPI.getLetter as ReturnType<typeof vi.fn>).mockResolvedValue(mockLetter);

    renderPage();

    await waitFor(() => {
      expect(screen.getByText('Good Faith Letter')).toBeInTheDocument();
    });

    // Check breadcrumbs
    const breadcrumbs = screen.getByRole('navigation', { name: /breadcrumb/i });
    expect(within(breadcrumbs).getByText('Deficiency Analysis')).toBeInTheDocument();
    expect(within(breadcrumbs).getByText('Deficiency Report')).toBeInTheDocument();
  });

  it('should handle export workflow', async () => {
    const mockBlob = new Blob(['PDF content'], { type: 'application/pdf' });
    (goodFaithLetterAPI.getLetter as ReturnType<typeof vi.fn>).mockResolvedValue(mockLetter);
    (goodFaithLetterAPI.exportLetter as ReturnType<typeof vi.fn>).mockResolvedValue(mockBlob);

    // Mock window functions
    const mockCreateObjectURL = vi.fn().mockReturnValue('blob:url');
    const mockRevokeObjectURL = vi.fn();
    const mockClick = vi.fn();
    
    window.URL.createObjectURL = mockCreateObjectURL;
    window.URL.revokeObjectURL = mockRevokeObjectURL;
    
    const originalCreateElement = document.createElement;
    document.createElement = vi.fn((tagName) => {
      if (tagName === 'a') {
        return { 
          click: mockClick, 
          style: {},
          href: '',
          download: ''
        } as HTMLAnchorElement;
      }
      return originalCreateElement.call(document, tagName);
    });

    renderPage();

    await waitFor(() => {
      expect(screen.getByText('Good Faith Letter')).toBeInTheDocument();
    });

    // Open export dialog
    const exportButton = screen.getByRole('button', { name: /export/i });
    await user.click(exportButton);

    // Export as PDF
    const exportDialogButton = screen.getAllByRole('button', { name: /export/i })[1];
    await user.click(exportDialogButton);

    await waitFor(() => {
      expect(goodFaithLetterAPI.exportLetter).toHaveBeenCalledWith('letter-123', 'pdf');
      expect(mockClick).toHaveBeenCalled();
    });

    // Cleanup
    document.createElement = originalCreateElement;
  });
});