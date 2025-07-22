import React from 'react';
import { render, screen, waitFor } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { QueryClient, QueryClientProvider } from '@tanstack/react-query';
import { describe, it, expect, vi, beforeEach } from 'vitest';
import { LetterEditor } from '../LetterEditor';
import { goodFaithLetterAPI } from '../../../../services/api/goodFaithLetter';
import { GeneratedLetter } from '../../../../types/goodFaithLetter.types';

vi.mock('../../../../services/api/goodFaithLetter');

const mockLetter: GeneratedLetter = {
  id: 'letter-123',
  report_id: 'report-456',
  case_name: 'Smith v. Jones',
  jurisdiction: 'federal',
  content: `Law Firm Name
123 Main Street

Re: Smith v. Jones

Dear Counsel:

I write regarding discovery deficiencies.

DEFICIENCIES:
1. Request No. 1 - Incomplete

Sincerely,
Jane Smith, Esq.`,
  status: 'draft',
  version: 1,
  agent_execution_id: 'exec-789',
  created_at: '2024-10-04T10:00:00Z',
  edit_history: []
};

describe('LetterEditor', () => {
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

  const renderComponent = (letterId: string, onVersionChange?: ReturnType<typeof vi.fn>) => {
    return render(
      <QueryClientProvider client={queryClient}>
        <LetterEditor letterId={letterId} onVersionChange={onVersionChange} />
      </QueryClientProvider>
    );
  };

  it('should display loading state initially', () => {
    (goodFaithLetterAPI.getLetter as ReturnType<typeof vi.fn>).mockImplementation(() => 
      new Promise(() => {})
    );

    renderComponent('letter-123');
    
    expect(screen.getByRole('progressbar')).toBeInTheDocument();
  });

  it('should display error when letter fails to load', async () => {
    (goodFaithLetterAPI.getLetter as ReturnType<typeof vi.fn>).mockRejectedValue(
      new Error('Failed to load')
    );

    renderComponent('letter-123');

    await waitFor(() => {
      expect(screen.getByText('Failed to load letter for editing. Please try again later.')).toBeInTheDocument();
    });
  });

  it('should render letter sections with edit buttons', async () => {
    (goodFaithLetterAPI.getLetter as ReturnType<typeof vi.fn>).mockResolvedValue(mockLetter);

    renderComponent('letter-123');

    await waitFor(() => {
      expect(screen.getByText('Edit Good Faith Letter')).toBeInTheDocument();
      expect(screen.getByText('Header')).toBeInTheDocument();
      expect(screen.getByText('Subject Line')).toBeInTheDocument();
      expect(screen.getByText('Salutation')).toBeInTheDocument();
      expect(screen.getByText('Body')).toBeInTheDocument();
      expect(screen.getByText('Deficiencies')).toBeInTheDocument();
      expect(screen.getByText('Conclusion')).toBeInTheDocument();
    });

    // Check for edit buttons
    const editButtons = screen.getAllByRole('button', { name: /edit section/i });
    expect(editButtons.length).toBeGreaterThan(0);
  });

  it('should not allow editing finalized letters', async () => {
    const finalizedLetter = { ...mockLetter, status: 'finalized' as const };
    (goodFaithLetterAPI.getLetter as ReturnType<typeof vi.fn>).mockResolvedValue(finalizedLetter);

    renderComponent('letter-123');

    await waitFor(() => {
      expect(screen.getByText('This letter has been finalized and cannot be edited.')).toBeInTheDocument();
    });
  });

  it('should enable editing mode when edit button is clicked', async () => {
    (goodFaithLetterAPI.getLetter as ReturnType<typeof vi.fn>).mockResolvedValue(mockLetter);

    renderComponent('letter-123');

    await waitFor(() => {
      expect(screen.getByText('Subject Line')).toBeInTheDocument();
    });

    const editButtons = screen.getAllByRole('button', { name: /edit section/i });
    await user.click(editButtons[0]);

    // Should show textarea for editing
    expect(screen.getByRole('textbox', { name: '' })).toBeInTheDocument();
    expect(screen.getByText('Cancel')).toBeInTheDocument();
  });

  it('should validate empty section content', async () => {
    (goodFaithLetterAPI.getLetter as ReturnType<typeof vi.fn>).mockResolvedValue(mockLetter);

    renderComponent('letter-123');

    await waitFor(() => {
      expect(screen.getByText('Body')).toBeInTheDocument();
    });

    const editButtons = screen.getAllByRole('button', { name: /edit section/i });
    const bodyEditIndex = 3; // Body section is typically the 4th section
    await user.click(editButtons[bodyEditIndex]);

    const textarea = screen.getByRole('textbox');
    await user.clear(textarea);

    await waitFor(() => {
      expect(screen.getByText('Section content cannot be empty')).toBeInTheDocument();
    });
  });

  it('should validate subject line format', async () => {
    (goodFaithLetterAPI.getLetter as ReturnType<typeof vi.fn>).mockResolvedValue(mockLetter);

    renderComponent('letter-123');

    await waitFor(() => {
      expect(screen.getByText('Subject Line')).toBeInTheDocument();
    });

    const editButtons = screen.getAllByRole('button', { name: /edit section/i });
    await user.click(editButtons[1]); // Subject line section

    const textarea = screen.getByRole('textbox');
    await user.clear(textarea);
    await user.type(textarea, 'Invalid subject without Re:');

    await waitFor(() => {
      expect(screen.getByText('Subject line must include "Re:"')).toBeInTheDocument();
    });
  });

  it('should show unsaved changes indicator', async () => {
    (goodFaithLetterAPI.getLetter as ReturnType<typeof vi.fn>).mockResolvedValue(mockLetter);

    renderComponent('letter-123');

    await waitFor(() => {
      expect(screen.getByText('Body')).toBeInTheDocument();
    });

    const editButtons = screen.getAllByRole('button', { name: /edit section/i });
    await user.click(editButtons[3]); // Body section

    const textarea = screen.getByRole('textbox');
    await user.type(textarea, ' Additional text');

    await waitFor(() => {
      expect(screen.getByText('Unsaved changes')).toBeInTheDocument();
    });
  });

  it('should save changes successfully', async () => {
    (goodFaithLetterAPI.getLetter as ReturnType<typeof vi.fn>).mockResolvedValue(mockLetter);
    const updatedLetter = { ...mockLetter, version: 2 };
    (goodFaithLetterAPI.customizeLetter as ReturnType<typeof vi.fn>).mockResolvedValue(updatedLetter);

    const onVersionChange = vi.fn();
    renderComponent('letter-123', onVersionChange);

    await waitFor(() => {
      expect(screen.getByText('Body')).toBeInTheDocument();
    });

    const editButtons = screen.getAllByRole('button', { name: /edit section/i });
    await user.click(editButtons[3]); // Body section

    const textarea = screen.getByRole('textbox');
    await user.type(textarea, ' Additional text');

    const saveButton = screen.getByRole('button', { name: /save all changes/i });
    await user.click(saveButton);

    await waitFor(() => {
      expect(goodFaithLetterAPI.customizeLetter).toHaveBeenCalledWith(
        'letter-123',
        expect.objectContaining({
          section_edits: expect.arrayContaining([
            expect.objectContaining({
              section: 'body',
              content: expect.stringContaining('Additional text')
            })
          ])
        })
      );
      expect(onVersionChange).toHaveBeenCalledWith(2);
      expect(screen.getByText(/Letter updated successfully/)).toBeInTheDocument();
    });
  });

  it('should handle save errors gracefully', async () => {
    (goodFaithLetterAPI.getLetter as ReturnType<typeof vi.fn>).mockResolvedValue(mockLetter);
    (goodFaithLetterAPI.customizeLetter as ReturnType<typeof vi.fn>).mockRejectedValue(
      new Error('Save failed')
    );

    renderComponent('letter-123');

    await waitFor(() => {
      expect(screen.getByText('Body')).toBeInTheDocument();
    });

    const editButtons = screen.getAllByRole('button', { name: /edit section/i });
    await user.click(editButtons[3]); // Body section

    const textarea = screen.getByRole('textbox');
    await user.type(textarea, ' Additional text');

    const saveButton = screen.getByRole('button', { name: /save all changes/i });
    await user.click(saveButton);

    await waitFor(() => {
      expect(screen.getByText('Failed to save changes. Please try again.')).toBeInTheDocument();
    });
  });

  it('should cancel editing when cancel button is clicked', async () => {
    (goodFaithLetterAPI.getLetter as ReturnType<typeof vi.fn>).mockResolvedValue(mockLetter);

    renderComponent('letter-123');

    await waitFor(() => {
      expect(screen.getByText('Body')).toBeInTheDocument();
    });

    const editButtons = screen.getAllByRole('button', { name: /edit section/i });
    await user.click(editButtons[3]); // Body section

    const textarea = screen.getByRole('textbox');
    await user.type(textarea, ' Additional text');

    const cancelButton = screen.getByRole('button', { name: /cancel/i });
    await user.click(cancelButton);

    // Should no longer show textarea
    expect(screen.queryByRole('textbox')).not.toBeInTheDocument();
    // Should show original content
    expect(screen.getByText(/I write regarding discovery deficiencies/)).toBeInTheDocument();
  });

  it('should allow adding editor notes', async () => {
    (goodFaithLetterAPI.getLetter as ReturnType<typeof vi.fn>).mockResolvedValue(mockLetter);
    (goodFaithLetterAPI.customizeLetter as ReturnType<typeof vi.fn>).mockResolvedValue({ ...mockLetter, version: 2 });

    renderComponent('letter-123');

    await waitFor(() => {
      expect(screen.getByText('Edit Good Faith Letter')).toBeInTheDocument();
    });

    const notesField = screen.getByLabelText(/editor notes/i);
    await user.type(notesField, 'Made tone more formal');

    const editButtons = screen.getAllByRole('button', { name: /edit section/i });
    await user.click(editButtons[3]); // Body section
    const textarea = screen.getByRole('textbox', { name: '' });
    await user.type(textarea, ' Updated');

    const saveButton = screen.getByRole('button', { name: /save all changes/i });
    await user.click(saveButton);

    await waitFor(() => {
      expect(goodFaithLetterAPI.customizeLetter).toHaveBeenCalledWith(
        'letter-123',
        expect.objectContaining({
          editor_notes: 'Made tone more formal'
        })
      );
    });
  });
});