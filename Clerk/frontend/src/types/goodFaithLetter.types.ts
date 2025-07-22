export interface SectionEdit {
  section: string;
  content: string;
}

export interface LetterEdit {
  id: string;
  letter_id: string;
  version: number;
  editor_id: string;
  editor_name: string;
  section_edits: SectionEdit[];
  edit_timestamp: string;
  edit_notes?: string;
}

export interface GeneratedLetter {
  id: string;
  report_id: string;
  case_name: string;
  jurisdiction: string;
  content: string;
  status: 'draft' | 'review' | 'approved' | 'finalized';
  version: number;
  agent_execution_id: string;
  created_at: string;
  updated_at?: string;
  approved_by?: string;
  approved_at?: string;
  edit_history: LetterEdit[];
}

export interface LetterSection {
  id: string;
  name: string;
  title?: string;
  content: string;
  editable: boolean;
}

export interface LetterPreviewData {
  letter: GeneratedLetter;
  sections: LetterSection[];
}

export interface ExportFormat {
  format: 'pdf' | 'docx' | 'html';
  label: string;
  icon?: string;
}

export interface EmailPreparation {
  recipients: string[];
  subject: string;
  attachments: string[];
  isDraft: boolean;
}

// WebSocket event payloads
export interface LetterUpdateEvent {
  letter_id: string;
  version?: number;
  updated_by?: string;
}

export interface LetterFinalizedEvent {
  letter_id: string;
  finalized_by: string;
  finalized_at: string;
}

export interface LetterEmailSentEvent {
  letter_id: string;
  recipients: string[];
  sent_at?: string;
}