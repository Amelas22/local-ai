import React from 'react';
import { render, screen, fireEvent, waitFor } from '@testing-library/react';
import { FactCard } from '../FactCard';
import { ExtractedFactWithSource } from '../../../types/discovery.types';
import { format } from 'date-fns';

const mockFact: ExtractedFactWithSource = {
  id: 'fact-123',
  content: 'The accident occurred on January 15, 2024',
  category: 'incident',
  confidence: 0.95,
  source: {
    doc_id: 'doc-456',
    doc_title: 'Police Report.pdf',
    page: 3,
    bbox: [100, 200, 300, 400],
    text_snippet: '...the accident occurred on January 15, 2024 at approximately...',
  },
  is_edited: false,
  edit_history: [],
  review_status: 'pending',
  created_at: '2024-01-20T10:00:00Z',
  updated_at: '2024-01-20T10:00:00Z',
  entities: ['January 15, 2024'],
  keywords: ['accident', 'occurred'],
};

const defaultProps = {
  fact: mockFact,
  viewMode: 'grid' as const,
  onSelect: jest.fn(),
  onUpdate: jest.fn(),
  onDelete: jest.fn(),
  isSelected: false,
};

describe('FactCard', () => {
  beforeEach(() => {
    jest.clearAllMocks();
  });

  describe('Grid View', () => {
    it('renders fact content correctly', () => {
      render(<FactCard {...defaultProps} />);
      
      expect(screen.getByText(mockFact.content)).toBeInTheDocument();
      expect(screen.getByText(mockFact.category)).toBeInTheDocument();
      expect(screen.getByText('95%')).toBeInTheDocument();
      expect(screen.getByText('pending')).toBeInTheDocument();
    });

    it('displays source information', () => {
      render(<FactCard {...defaultProps} />);
      
      expect(screen.getByText('Police Report.pdf')).toBeInTheDocument();
      expect(screen.getByText('• Page 3')).toBeInTheDocument();
    });

    it('shows entities as chips', () => {
      render(<FactCard {...defaultProps} />);
      
      expect(screen.getByText('January 15, 2024')).toBeInTheDocument();
    });

    it('handles fact selection on content click', () => {
      render(<FactCard {...defaultProps} />);
      
      fireEvent.click(screen.getByText(mockFact.content));
      
      expect(defaultProps.onSelect).toHaveBeenCalledWith(mockFact);
    });

    it('shows selected state', () => {
      const { container } = render(<FactCard {...defaultProps} isSelected={true} />);
      
      const card = container.querySelector('.MuiCard-root');
      expect(card).toHaveStyle('border-top: 4px');
    });
  });

  describe('List View', () => {
    it('renders in list format', () => {
      render(<FactCard {...defaultProps} viewMode="list" />);
      
      expect(screen.getByText(mockFact.content)).toBeInTheDocument();
      expect(screen.getByText('Police Report.pdf')).toBeInTheDocument();
    });

    it('shows selected state in list view', () => {
      const { container } = render(<FactCard {...defaultProps} viewMode="list" isSelected={true} />);
      
      const card = container.querySelector('.MuiCard-root');
      expect(card).toHaveStyle('border-left: 4px');
    });
  });

  describe('Edit Functionality', () => {
    it('enters edit mode when edit button clicked', () => {
      render(<FactCard {...defaultProps} />);
      
      const editButton = screen.getAllByRole('button')[0]; // First button is edit
      fireEvent.click(editButton);
      
      expect(screen.getByRole('textbox')).toBeInTheDocument();
      expect(screen.getByPlaceholderText('Reason for edit (optional)')).toBeInTheDocument();
    });

    it('saves edited content', async () => {
      render(<FactCard {...defaultProps} />);
      
      // Enter edit mode
      const editButton = screen.getAllByRole('button')[0];
      fireEvent.click(editButton);
      
      // Change content
      const textbox = screen.getByRole('textbox');
      fireEvent.change(textbox, { target: { value: 'Updated content' } });
      
      // Add reason
      const reasonInput = screen.getByPlaceholderText('Reason for edit (optional)');
      fireEvent.change(reasonInput, { target: { value: 'Correcting date' } });
      
      // Save
      const saveButton = screen.getAllByRole('button')[0]; // Save button
      fireEvent.click(saveButton);
      
      expect(defaultProps.onUpdate).toHaveBeenCalledWith(
        mockFact,
        'Updated content',
        'Correcting date'
      );
    });

    it('cancels edit without saving', () => {
      render(<FactCard {...defaultProps} />);
      
      // Enter edit mode
      const editButton = screen.getAllByRole('button')[0];
      fireEvent.click(editButton);
      
      // Change content
      const textbox = screen.getByRole('textbox');
      fireEvent.change(textbox, { target: { value: 'Changed content' } });
      
      // Cancel
      const cancelButton = screen.getAllByRole('button')[1]; // Cancel button
      fireEvent.click(cancelButton);
      
      expect(defaultProps.onUpdate).not.toHaveBeenCalled();
      expect(screen.getByText(mockFact.content)).toBeInTheDocument();
    });
  });

  describe('Delete Functionality', () => {
    it('shows delete confirmation dialog', async () => {
      render(<FactCard {...defaultProps} />);
      
      // Open menu
      const menuButton = screen.getAllByRole('button')[1]; // More options button
      fireEvent.click(menuButton);
      
      // Click delete
      await waitFor(() => {
        const deleteOption = screen.getByText('Delete');
        fireEvent.click(deleteOption);
      });
      
      expect(screen.getByText('Confirm Delete')).toBeInTheDocument();
      expect(screen.getByText('Are you sure you want to delete this fact? This action cannot be undone.')).toBeInTheDocument();
    });

    it('confirms deletion', async () => {
      render(<FactCard {...defaultProps} />);
      
      // Open menu and click delete
      const menuButton = screen.getAllByRole('button')[1];
      fireEvent.click(menuButton);
      
      await waitFor(() => {
        fireEvent.click(screen.getByText('Delete'));
      });
      
      // Confirm deletion
      const confirmButton = screen.getByRole('button', { name: 'Delete' });
      fireEvent.click(confirmButton);
      
      expect(defaultProps.onDelete).toHaveBeenCalledWith(mockFact);
    });
  });

  describe('Edit History', () => {
    it('shows edit history dialog', async () => {
      const factWithHistory = {
        ...mockFact,
        edit_history: [
          {
            timestamp: '2024-01-21T10:00:00Z',
            user_id: 'user-123',
            old_content: 'Original content',
            new_content: 'Updated content',
            reason: 'Fixing typo',
          },
        ],
      };
      
      render(<FactCard {...defaultProps} fact={factWithHistory} />);
      
      // Open menu
      const menuButton = screen.getAllByRole('button')[1];
      fireEvent.click(menuButton);
      
      // Click view history
      await waitFor(() => {
        const historyOption = screen.getByText('View History');
        fireEvent.click(historyOption);
      });
      
      expect(screen.getByText('Edit History')).toBeInTheDocument();
      expect(screen.getByText('Updated content')).toBeInTheDocument();
      expect(screen.getByText('Reason: Fixing typo')).toBeInTheDocument();
    });
  });

  describe('Confidence Indicators', () => {
    it('shows high confidence in green', () => {
      render(<FactCard {...defaultProps} />);
      
      const confidenceChip = screen.getByText('95%').closest('.MuiChip-root');
      expect(confidenceChip).toHaveClass('MuiChip-colorSuccess');
    });

    it('shows medium confidence in blue', () => {
      const mediumConfidenceFact = { ...mockFact, confidence: 0.75 };
      render(<FactCard {...defaultProps} fact={mediumConfidenceFact} />);
      
      const confidenceChip = screen.getByText('75%').closest('.MuiChip-root');
      expect(confidenceChip).toHaveClass('MuiChip-colorInfo');
    });

    it('shows low confidence in orange', () => {
      const lowConfidenceFact = { ...mockFact, confidence: 0.55 };
      render(<FactCard {...defaultProps} fact={lowConfidenceFact} />);
      
      const confidenceChip = screen.getByText('55%').closest('.MuiChip-root');
      expect(confidenceChip).toHaveClass('MuiChip-colorWarning');
    });
  });

  describe('Review Status', () => {
    it('shows pending status in warning color', () => {
      render(<FactCard {...defaultProps} />);
      
      const statusChip = screen.getByText('pending').closest('.MuiChip-root');
      expect(statusChip).toHaveClass('MuiChip-colorWarning');
    });

    it('shows reviewed status in success color', () => {
      const reviewedFact = { ...mockFact, review_status: 'reviewed' as const };
      render(<FactCard {...defaultProps} fact={reviewedFact} />);
      
      const statusChip = screen.getByText('reviewed').closest('.MuiChip-root');
      expect(statusChip).toHaveClass('MuiChip-colorSuccess');
    });

    it('shows rejected status in error color', () => {
      const rejectedFact = { ...mockFact, review_status: 'rejected' as const };
      render(<FactCard {...defaultProps} fact={rejectedFact} />);
      
      const statusChip = screen.getByText('rejected').closest('.MuiChip-root');
      expect(statusChip).toHaveClass('MuiChip-colorError');
    });
  });

  describe('Edited Indicator', () => {
    it('shows edited chip when fact is edited', () => {
      const editedFact = { ...mockFact, is_edited: true };
      render(<FactCard {...defaultProps} fact={editedFact} />);
      
      expect(screen.getByText('Edited')).toBeInTheDocument();
    });

    it('does not show edited chip for unedited facts', () => {
      render(<FactCard {...defaultProps} />);
      
      expect(screen.queryByText('Edited')).not.toBeInTheDocument();
    });
  });
});