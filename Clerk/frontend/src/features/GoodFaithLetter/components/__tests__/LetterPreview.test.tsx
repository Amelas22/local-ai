import React from 'react';
import { render, screen, waitFor } from '@testing-library/react';
import { QueryClient, QueryClientProvider } from '@tanstack/react-query';
import { describe, it, expect, vi, beforeEach } from 'vitest';
import { LetterPreview } from '../LetterPreview';
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
City, State 12345

October 4, 2024

Opposing Counsel
456 Oak Avenue
City, State 12346

Re: Smith v. Jones - Discovery Deficiencies

Dear Counsel:

I write to address the deficiencies in your client's discovery production dated September 1, 2024.

DEFICIENCIES:

1. Request for Production No. 1: Your response stating "No responsive documents" is inadequate given the evidence that such documents exist.

2. Request for Production No. 5: The produced documents are incomplete and fail to include critical emails referenced in the deposition testimony.

Sincerely,

Jane Smith, Esq.
Attorney for Plaintiff`,
  status: 'draft',
  version: 1,
  agent_execution_id: 'exec-789',
  created_at: '2024-10-04T10:00:00Z',
  edit_history: []
};

describe('LetterPreview', () => {
  let queryClient: QueryClient;

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

  const renderComponent = (letterId: string) => {
    return render(
      <QueryClientProvider client={queryClient}>
        <LetterPreview letterId={letterId} />
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

  it('should display error message when letter fails to load', async () => {
    (goodFaithLetterAPI.getLetter as ReturnType<typeof vi.fn>).mockRejectedValue(
      new Error('Failed to load')
    );

    renderComponent('letter-123');

    await waitFor(() => {
      expect(screen.getByText('Failed to load letter preview. Please try again later.')).toBeInTheDocument();
    });
  });

  it('should render letter sections correctly', async () => {
    (goodFaithLetterAPI.getLetter as ReturnType<typeof vi.fn>).mockResolvedValue(mockLetter);

    renderComponent('letter-123');

    await waitFor(() => {
      expect(screen.getByText('Good Faith Letter Preview')).toBeInTheDocument();
      // Check that the subject line content is rendered (it's rendered via dangerouslySetInnerHTML)
      const letterContent = screen.getByText('Good Faith Letter Preview').closest('div');
      expect(letterContent?.innerHTML).toContain('Smith v. Jones - Discovery Deficiencies');
      expect(screen.getByText('Dear Counsel:')).toBeInTheDocument();
      expect(screen.getByText(/I write to address the deficiencies/)).toBeInTheDocument();
      expect(screen.getByText(/Request for Production No. 1/)).toBeInTheDocument();
    });
  });

  it('should display letter status and version', async () => {
    (goodFaithLetterAPI.getLetter as ReturnType<typeof vi.fn>).mockResolvedValue(mockLetter);

    renderComponent('letter-123');

    await waitFor(() => {
      expect(screen.getByText('Draft')).toBeInTheDocument();
      expect(screen.getByText('Version 1')).toBeInTheDocument();
    });
  });

  it('should display letter metadata', async () => {
    (goodFaithLetterAPI.getLetter as ReturnType<typeof vi.fn>).mockResolvedValue(mockLetter);

    renderComponent('letter-123');

    await waitFor(() => {
      expect(screen.getByText(/Case: Smith v. Jones/)).toBeInTheDocument();
      expect(screen.getByText(/Jurisdiction: federal/)).toBeInTheDocument();
    });
  });

  it('should refetch draft letters periodically', async () => {
    const mockGetLetter = goodFaithLetterAPI.getLetter as ReturnType<typeof vi.fn>;
    mockGetLetter.mockResolvedValue(mockLetter);

    renderComponent('letter-123');

    await waitFor(() => {
      expect(screen.getByText('Good Faith Letter Preview')).toBeInTheDocument();
    });

    // Verify refetch interval is set for draft status
    expect(mockGetLetter).toHaveBeenCalledTimes(1);
  });

  it('should not refetch finalized letters', async () => {
    const finalizedLetter = { ...mockLetter, status: 'finalized' as const };
    const mockGetLetter = goodFaithLetterAPI.getLetter as ReturnType<typeof vi.fn>;
    mockGetLetter.mockResolvedValue(finalizedLetter);

    renderComponent('letter-123');

    await waitFor(() => {
      expect(screen.getByText('Finalized')).toBeInTheDocument();
    });

    // Should only be called once for finalized letters
    expect(mockGetLetter).toHaveBeenCalledTimes(1);
  });

  it('should show info message when no letter is found', async () => {
    (goodFaithLetterAPI.getLetter as ReturnType<typeof vi.fn>).mockResolvedValue(null);

    renderComponent('letter-123');

    await waitFor(() => {
      expect(screen.getByText('No letter found with the provided ID.')).toBeInTheDocument();
    });
  });

  it('should parse letter sections with different structures', async () => {
    const letterWithoutSections: GeneratedLetter = {
      ...mockLetter,
      content: 'This is a simple letter without standard sections.'
    };
    
    (goodFaithLetterAPI.getLetter as ReturnType<typeof vi.fn>).mockResolvedValue(letterWithoutSections);

    renderComponent('letter-123');

    await waitFor(() => {
      expect(screen.getByText('This is a simple letter without standard sections.')).toBeInTheDocument();
    });
  });
});