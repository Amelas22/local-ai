import React from 'react';
import { render, screen, waitFor } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { describe, it, expect, vi, beforeEach } from 'vitest';
import { EmailPreparation } from '../EmailPreparation';
import { GeneratedLetter } from '../../../../types/goodFaithLetter.types';

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

describe('EmailPreparation', () => {
  const user = userEvent.setup();
  const mockOnSendEmail = vi.fn();
  const mockOnSaveDraft = vi.fn();

  beforeEach(() => {
    vi.clearAllMocks();
  });

  const renderComponent = (letter = mockLetter) => {
    return render(
      <EmailPreparation 
        letter={letter}
        onSendEmail={mockOnSendEmail}
        onSaveDraft={mockOnSaveDraft}
      />
    );
  };

  it('should render email preparation form', () => {
    renderComponent();

    expect(screen.getByText('Email Preparation')).toBeInTheDocument();
    expect(screen.getByLabelText('To')).toBeInTheDocument();
    expect(screen.getByLabelText('CC (Optional)')).toBeInTheDocument();
    expect(screen.getByLabelText('BCC (Optional)')).toBeInTheDocument();
    expect(screen.getByLabelText('Subject')).toBeInTheDocument();
    expect(screen.getByLabelText('Message')).toBeInTheDocument();
  });

  it('should pre-fill subject line with case name', () => {
    renderComponent();

    const subjectField = screen.getByLabelText('Subject') as HTMLInputElement;
    expect(subjectField.value).toContain('Smith v. Jones');
    expect(subjectField.value).toContain('Good Faith Letter Regarding Discovery Deficiencies');
  });

  it('should pre-fill message with template', () => {
    renderComponent();

    const messageField = screen.getByLabelText('Message') as HTMLTextAreaElement;
    expect(messageField.value).toContain('Dear Counsel');
    expect(messageField.value).toContain('Smith v. Jones');
    expect(messageField.value).toContain('discovery deficiencies');
  });

  it('should show warning for draft letters', () => {
    const draftLetter = { ...mockLetter, status: 'draft' as const };
    renderComponent(draftLetter);

    expect(screen.getByText(/This letter is still in draft status/)).toBeInTheDocument();
  });

  it('should validate email addresses', async () => {
    renderComponent();

    const toField = screen.getByLabelText('To');
    await user.type(toField, 'invalid-email{enter}');

    // The chip should show as error
    const chip = screen.getByText('invalid-email');
    expect(chip.closest('.MuiChip-root')).toHaveClass('MuiChip-colorError');
  });

  it('should add multiple recipients', async () => {
    renderComponent();

    const toField = screen.getByLabelText('To');
    await user.type(toField, 'john@example.com{enter}');
    await user.type(toField, 'jane@example.com{enter}');

    expect(screen.getByText('john@example.com')).toBeInTheDocument();
    expect(screen.getByText('jane@example.com')).toBeInTheDocument();
  });

  it('should show letter attachment by default', () => {
    renderComponent();

    expect(screen.getByText('Good_Faith_Letter.pdf')).toBeInTheDocument();
    expect(screen.getByText('245 KB')).toBeInTheDocument();
  });

  it('should add evidence attachment when checkbox is checked', async () => {
    renderComponent();

    const includeEvidenceCheckbox = screen.getByLabelText('Include supporting evidence documents');
    await user.click(includeEvidenceCheckbox);

    await waitFor(() => {
      expect(screen.getByText('Evidence_Supporting_Deficiencies.pdf')).toBeInTheDocument();
      expect(screen.getByText('12.3 MB')).toBeInTheDocument();
    });
  });

  it('should calculate total attachment size', async () => {
    renderComponent();

    // Initially just the letter
    expect(screen.getByText(/Total attachment size:.*0\.2.*MB/)).toBeInTheDocument();

    // Add evidence
    const includeEvidenceCheckbox = screen.getByLabelText('Include supporting evidence documents');
    await user.click(includeEvidenceCheckbox);

    await waitFor(() => {
      expect(screen.getByText(/Total attachment size:.*12\.5.*MB/)).toBeInTheDocument();
    });
  });

  it('should disable send button when form is invalid', async () => {
    renderComponent();

    const sendButton = screen.getByRole('button', { name: /send email/i });
    
    // Initially disabled because no recipients
    expect(sendButton).toBeDisabled();

    // Add recipient
    const toField = screen.getByLabelText('To');
    await user.type(toField, 'valid@example.com{enter}');

    await waitFor(() => {
      expect(sendButton).not.toBeDisabled();
    });
  });

  it('should save draft when save button is clicked', async () => {
    renderComponent();

    const toField = screen.getByLabelText('To');
    await user.type(toField, 'john@example.com{enter}');

    const saveDraftButton = screen.getByRole('button', { name: /save draft/i });
    await user.click(saveDraftButton);

    await waitFor(() => {
      expect(mockOnSaveDraft).toHaveBeenCalledWith(
        expect.objectContaining({
          recipients: ['john@example.com'],
          subject: expect.stringContaining('Smith v. Jones')
        })
      );
    });

    // Should show success message
    expect(screen.getByText('Draft saved')).toBeInTheDocument();
  });

  it('should show confirmation dialog for non-finalized letters', async () => {
    const draftLetter = { ...mockLetter, status: 'draft' as const };
    renderComponent(draftLetter);

    const toField = screen.getByLabelText('To');
    await user.type(toField, 'john@example.com{enter}');

    const sendButton = screen.getByRole('button', { name: /send email/i });
    await user.click(sendButton);

    // Confirmation dialog should appear
    expect(screen.getByText('Send Good Faith Letter?')).toBeInTheDocument();
    expect(screen.getByText(/This letter is in draft status/)).toBeInTheDocument();
  });

  it('should send email directly for finalized letters', async () => {
    renderComponent();

    const toField = screen.getByLabelText('To');
    await user.type(toField, 'john@example.com{enter}');

    const sendButton = screen.getByRole('button', { name: /send email/i });
    await user.click(sendButton);

    // Should call onSendEmail directly without confirmation
    await waitFor(() => {
      expect(mockOnSendEmail).toHaveBeenCalledWith(
        expect.objectContaining({
          recipients: ['john@example.com']
        })
      );
    });
  });

  it('should handle CC and BCC recipients', async () => {
    renderComponent();

    const toField = screen.getByLabelText('To');
    const ccField = screen.getByLabelText('CC (Optional)');
    const bccField = screen.getByLabelText('BCC (Optional)');

    await user.type(toField, 'to@example.com{enter}');
    await user.type(ccField, 'cc@example.com{enter}');
    await user.type(bccField, 'bcc@example.com{enter}');

    const sendButton = screen.getByRole('button', { name: /send email/i });
    await user.click(sendButton);

    await waitFor(() => {
      expect(mockOnSendEmail).toHaveBeenCalledWith(
        expect.objectContaining({
          recipients: ['to@example.com'],
          ccRecipients: ['cc@example.com'],
          bccRecipients: ['bcc@example.com']
        })
      );
    });
  });

  it('should allow custom subject and message', async () => {
    renderComponent();

    const toField = screen.getByLabelText('To');
    const subjectField = screen.getByLabelText('Subject');
    const messageField = screen.getByLabelText('Message');

    await user.type(toField, 'to@example.com{enter}');
    await user.clear(subjectField);
    await user.type(subjectField, 'Custom Subject');
    await user.clear(messageField);
    await user.type(messageField, 'Custom message body');

    const sendButton = screen.getByRole('button', { name: /send email/i });
    await user.click(sendButton);

    await waitFor(() => {
      expect(mockOnSendEmail).toHaveBeenCalledWith(
        expect.objectContaining({
          subject: 'Custom Subject',
          customMessage: 'Custom message body'
        })
      );
    });
  });

  it('should require at least one recipient', async () => {
    renderComponent();

    const sendButton = screen.getByRole('button', { name: /send email/i });
    expect(sendButton).toBeDisabled();

    const toField = screen.getByLabelText('To');
    await user.type(toField, 'valid@example.com{enter}');

    await waitFor(() => {
      expect(sendButton).not.toBeDisabled();
    });
  });

  it('should confirm send from dialog', async () => {
    const draftLetter = { ...mockLetter, status: 'draft' as const };
    renderComponent(draftLetter);

    const toField = screen.getByLabelText('To');
    await user.type(toField, 'john@example.com{enter}');

    const sendButton = screen.getByRole('button', { name: /send email/i });
    await user.click(sendButton);

    // Click confirm in dialog
    const confirmButton = screen.getByRole('button', { name: /confirm send/i });
    await user.click(confirmButton);

    await waitFor(() => {
      expect(mockOnSendEmail).toHaveBeenCalled();
    });
  });
});