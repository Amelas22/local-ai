import { apiClient } from '../utils/apiClient';
import { GeneratedLetter, LetterEdit, ExportFormat } from '../../types/goodFaithLetter.types';

export interface GenerateLetterParams {
  report_id: string;
  jurisdiction: 'federal' | 'state';
  include_evidence: boolean;
  attorney_info?: {
    name: string;
    firm: string;
    bar_number?: string;
    email?: string;
    phone?: string;
  };
}

export interface CustomizeLetterParams {
  section_edits: Array<{
    section: string;
    content: string;
  }>;
  editor_notes?: string;
}

export const goodFaithLetterAPI = {
  generateLetter: async (params: GenerateLetterParams): Promise<GeneratedLetter> => {
    const response = await apiClient.post('/api/agents/good-faith-letter/generate-letter', params);
    return response.data;
  },

  getLetter: async (letterId: string): Promise<GeneratedLetter> => {
    const response = await apiClient.get(`/api/agents/good-faith-letter/preview/${letterId}`);
    return response.data;
  },

  customizeLetter: async (letterId: string, params: CustomizeLetterParams): Promise<GeneratedLetter> => {
    const response = await apiClient.put(`/api/agents/good-faith-letter/customize/${letterId}`, params);
    return response.data;
  },

  finalizeLetter: async (letterId: string): Promise<GeneratedLetter> => {
    const response = await apiClient.post(`/api/agents/good-faith-letter/finalize/${letterId}`);
    return response.data;
  },

  exportLetter: async (letterId: string, format: ExportFormat['format']): Promise<Blob> => {
    const response = await apiClient.get(`/api/agents/good-faith-letter/export/${letterId}/${format}`, {
      responseType: 'blob'
    });
    return response.data;
  },

  getLetterVersions: async (letterId: string): Promise<LetterEdit[]> => {
    const response = await apiClient.get(`/api/agents/good-faith-letter/versions/${letterId}`);
    return response.data;
  },

  restoreVersion: async (letterId: string, version: number): Promise<GeneratedLetter> => {
    const response = await apiClient.post(`/api/agents/good-faith-letter/restore/${letterId}/${version}`);
    return response.data;
  }
};