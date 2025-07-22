import React from 'react';
import { render, screen, waitFor } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { QueryClient, QueryClientProvider } from '@tanstack/react-query';
import { describe, it, expect, vi, beforeEach } from 'vitest';
import { LetterVersionHistory } from '../LetterVersionHistory';
import { goodFaithLetterAPI } from '../../../../services/api/goodFaithLetter';
import { GeneratedLetter, LetterEdit } from '../../../../types/goodFaithLetter.types';

vi.mock('../../../../services/api/goodFaithLetter');

const mockVersions: LetterEdit[] = [
  {
    id: 'edit-1',
    letter_id: 'letter-123',
    version: 1,
    editor_id: 'user-1',
    editor_name: 'John Doe',
    section_edits: [
      { section: 'body', content: 'Initial draft' }
    ],
    edit_timestamp: '2024-10-01T10:00:00Z',
    edit_notes: 'Initial draft creation'
  },
  {
    id: 'edit-2',
    letter_id: 'letter-123',
    version: 2,
    editor_id: 'user-2',
    editor_name: 'Jane Smith',
    section_edits: [
      { section: 'body', content: 'Updated body content' },
      { section: 'deficiencies', content: 'Added deficiency details' }
    ],
    edit_timestamp: '2024-10-02T14:30:00Z',
    edit_notes: 'Added more details to deficiencies'
  },
  {
    id: 'edit-3',
    letter_id: 'letter-123',
    version: 3,
    editor_id: 'user-1',
    editor_name: 'John Doe',
    section_edits: [
      { section: 'conclusion', content: 'Updated conclusion' }
    ],
    edit_timestamp: '2024-10-03T09:15:00Z'
  }
];

const mockLetter: GeneratedLetter = {
  id: 'letter-123',
  report_id: 'report-456',
  case_name: 'Smith v. Jones',
  jurisdiction: 'federal',
  content: 'Current letter content...',
  status: 'draft',
  version: 3,
  agent_execution_id: 'exec-789',
  created_at: '2024-10-01T10:00:00Z',
  edit_history: mockVersions
};

describe('LetterVersionHistory', () => {
  let queryClient: QueryClient;
  const user = userEvent.setup();
  const mockOnVersionRestore = vi.fn();

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

  const renderComponent = (currentVersion = 3) => {
    return render(
      <QueryClientProvider client={queryClient}>
        <LetterVersionHistory 
          letterId="letter-123" 
          currentVersion={currentVersion}
          onVersionRestore={mockOnVersionRestore}
        />
      </QueryClientProvider>
    );
  };

  it('should display loading state initially', () => {
    (goodFaithLetterAPI.getLetterVersions as ReturnType<typeof vi.fn>).mockImplementation(() => 
      new Promise(() => {})
    );

    renderComponent();
    
    expect(screen.getByRole('progressbar')).toBeInTheDocument();
  });

  it('should display error when versions fail to load', async () => {
    (goodFaithLetterAPI.getLetterVersions as ReturnType<typeof vi.fn>).mockRejectedValue(
      new Error('Failed to load')
    );

    renderComponent();

    await waitFor(() => {
      expect(screen.getByText('Failed to load version history. Please try again later.')).toBeInTheDocument();
    });
  });

  it('should display version history timeline', async () => {
    (goodFaithLetterAPI.getLetterVersions as ReturnType<typeof vi.fn>).mockResolvedValue(mockVersions);
    (goodFaithLetterAPI.getLetter as ReturnType<typeof vi.fn>).mockResolvedValue(mockLetter);

    renderComponent();

    await waitFor(() => {
      expect(screen.getByText('Version History')).toBeInTheDocument();
      expect(screen.getByText('Version 1')).toBeInTheDocument();
      expect(screen.getByText('Version 2')).toBeInTheDocument();
      expect(screen.getByText('Version 3')).toBeInTheDocument();
    });
  });

  it('should show current version indicator', async () => {
    (goodFaithLetterAPI.getLetterVersions as ReturnType<typeof vi.fn>).mockResolvedValue(mockVersions);
    (goodFaithLetterAPI.getLetter as ReturnType<typeof vi.fn>).mockResolvedValue(mockLetter);

    renderComponent(3);

    await waitFor(() => {
      const currentChip = screen.getByText('Current');
      expect(currentChip).toBeInTheDocument();
    });
  });

  it('should display editor names and timestamps', async () => {
    (goodFaithLetterAPI.getLetterVersions as ReturnType<typeof vi.fn>).mockResolvedValue(mockVersions);
    (goodFaithLetterAPI.getLetter as ReturnType<typeof vi.fn>).mockResolvedValue(mockLetter);

    renderComponent();

    await waitFor(() => {
      expect(screen.getByText('John Doe')).toBeInTheDocument();
      expect(screen.getByText('Jane Smith')).toBeInTheDocument();
      expect(screen.getByText('Oct 1, 2024')).toBeInTheDocument();
      expect(screen.getByText('Oct 2, 2024')).toBeInTheDocument();
    });
  });

  it('should display edit notes when available', async () => {
    (goodFaithLetterAPI.getLetterVersions as ReturnType<typeof vi.fn>).mockResolvedValue(mockVersions);
    (goodFaithLetterAPI.getLetter as ReturnType<typeof vi.fn>).mockResolvedValue(mockLetter);

    renderComponent();

    await waitFor(() => {
      expect(screen.getByText('"Initial draft creation"')).toBeInTheDocument();
      expect(screen.getByText('"Added more details to deficiencies"')).toBeInTheDocument();
    });
  });

  it('should show section edit counts', async () => {
    (goodFaithLetterAPI.getLetterVersions as ReturnType<typeof vi.fn>).mockResolvedValue(mockVersions);
    (goodFaithLetterAPI.getLetter as ReturnType<typeof vi.fn>).mockResolvedValue(mockLetter);

    renderComponent();

    await waitFor(() => {
      expect(screen.getByText(/1 section edited/)).toBeInTheDocument();
      expect(screen.getByText(/2 sections edited/)).toBeInTheDocument();
    });
  });

  it('should allow selecting versions for comparison', async () => {
    (goodFaithLetterAPI.getLetterVersions as ReturnType<typeof vi.fn>).mockResolvedValue(mockVersions);
    (goodFaithLetterAPI.getLetter as ReturnType<typeof vi.fn>).mockResolvedValue(mockLetter);

    renderComponent();

    await waitFor(() => {
      expect(screen.getByText('Version 1')).toBeInTheDocument();
    });

    // Click on version 1
    const version1Card = screen.getByText('Version 1').closest('[role="button"]') || 
                        screen.getByText('Version 1').closest('div[class*="Card"]');
    await user.click(version1Card!);

    // Click on version 2
    const version2Card = screen.getByText('Version 2').closest('[role="button"]') || 
                        screen.getByText('Version 2').closest('div[class*="Card"]');
    await user.click(version2Card!);

    // Compare button should be enabled
    const compareButton = screen.getByRole('button', { name: /compare selected/i });
    expect(compareButton).not.toBeDisabled();
    expect(compareButton).toHaveTextContent('Compare Selected (2/2)');
  });

  it('should limit selection to 2 versions', async () => {
    (goodFaithLetterAPI.getLetterVersions as ReturnType<typeof vi.fn>).mockResolvedValue(mockVersions);
    (goodFaithLetterAPI.getLetter as ReturnType<typeof vi.fn>).mockResolvedValue(mockLetter);

    renderComponent();

    await waitFor(() => {
      expect(screen.getByText('Version 1')).toBeInTheDocument();
    });

    // Select all three versions
    for (let i = 1; i <= 3; i++) {
      const versionCard = screen.getByText(`Version ${i}`).closest('div[class*="Card"]');
      await user.click(versionCard!);
    }

    // Should only show 2 selected
    const compareButton = screen.getByRole('button', { name: /compare selected/i });
    expect(compareButton).toHaveTextContent('Compare Selected (2/2)');
  });

  it('should open comparison dialog when compare is clicked', async () => {
    (goodFaithLetterAPI.getLetterVersions as ReturnType<typeof vi.fn>).mockResolvedValue(mockVersions);
    (goodFaithLetterAPI.getLetter as ReturnType<typeof vi.fn>).mockResolvedValue(mockLetter);

    renderComponent();

    await waitFor(() => {
      expect(screen.getByText('Version 1')).toBeInTheDocument();
    });

    // Select two versions
    const version1Card = screen.getByText('Version 1').closest('div[class*="Card"]');
    const version2Card = screen.getByText('Version 2').closest('div[class*="Card"]');
    await user.click(version1Card!);
    await user.click(version2Card!);

    // Click compare
    const compareButton = screen.getByRole('button', { name: /compare selected/i });
    await user.click(compareButton);

    // Dialog should open
    expect(screen.getByText('Version Comparison: v1 vs v2')).toBeInTheDocument();
  });

  it('should show restore buttons for non-current versions', async () => {
    (goodFaithLetterAPI.getLetterVersions as ReturnType<typeof vi.fn>).mockResolvedValue(mockVersions);
    (goodFaithLetterAPI.getLetter as ReturnType<typeof vi.fn>).mockResolvedValue(mockLetter);

    renderComponent(3);

    await waitFor(() => {
      expect(screen.getByText('Version 1')).toBeInTheDocument();
    });

    // Should have restore buttons for versions 1 and 2, but not 3 (current)
    const restoreButtons = screen.getAllByRole('button', { name: /restore this version/i });
    expect(restoreButtons).toHaveLength(2);
  });

  it('should handle version restoration', async () => {
    const restoredLetter = { ...mockLetter, version: 4 };
    (goodFaithLetterAPI.getLetterVersions as ReturnType<typeof vi.fn>).mockResolvedValue(mockVersions);
    (goodFaithLetterAPI.getLetter as ReturnType<typeof vi.fn>).mockResolvedValue(mockLetter);
    (goodFaithLetterAPI.restoreVersion as ReturnType<typeof vi.fn>).mockResolvedValue(restoredLetter);

    renderComponent();

    await waitFor(() => {
      expect(screen.getByText('Version 1')).toBeInTheDocument();
    });

    // Click restore on version 1
    const restoreButtons = screen.getAllByRole('button', { name: /restore this version/i });
    await user.click(restoreButtons[0]);

    // Confirmation dialog should appear
    expect(screen.getByText('Restore Version 1?')).toBeInTheDocument();

    // Confirm restoration
    const confirmButton = screen.getByRole('button', { name: /^restore$/i });
    await user.click(confirmButton);

    await waitFor(() => {
      expect(goodFaithLetterAPI.restoreVersion).toHaveBeenCalledWith('letter-123', 1);
      expect(mockOnVersionRestore).toHaveBeenCalledWith(4);
    });
  });

  it('should disable restore for finalized letters', async () => {
    const finalizedLetter = { ...mockLetter, status: 'finalized' as const };
    (goodFaithLetterAPI.getLetterVersions as ReturnType<typeof vi.fn>).mockResolvedValue(mockVersions);
    (goodFaithLetterAPI.getLetter as ReturnType<typeof vi.fn>).mockResolvedValue(finalizedLetter);

    renderComponent();

    await waitFor(() => {
      expect(screen.getByText('This letter is finalized. Version restoration is disabled.')).toBeInTheDocument();
    });

    const restoreButtons = screen.queryAllByRole('button', { name: /restore this version/i });
    restoreButtons.forEach(button => {
      expect(button).toBeDisabled();
    });
  });

  it('should show info message when no versions exist', async () => {
    (goodFaithLetterAPI.getLetterVersions as ReturnType<typeof vi.fn>).mockResolvedValue([]);
    (goodFaithLetterAPI.getLetter as ReturnType<typeof vi.fn>).mockResolvedValue(mockLetter);

    renderComponent();

    await waitFor(() => {
      expect(screen.getByText('No version history available yet.')).toBeInTheDocument();
    });
  });
});