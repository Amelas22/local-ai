export interface EvidenceChunk {
  document_id: string;
  chunk_text: string;
  relevance_score: number;
  page_number?: number;
  bates_number?: string;
}

export interface DeficiencyItem {
  id: string;
  report_id: string;
  request_number: string;
  request_text: string;
  oc_response_text: string;
  classification: 'fully_produced' | 'partially_produced' | 'not_produced' | 'no_responsive_docs';
  confidence_score: number;
  evidence_chunks: EvidenceChunk[];
  notes?: string;
  updated_by?: string;
  updated_at?: string;
}

export interface SummaryStatistics {
  fully_produced: number;
  partially_produced: number;
  not_produced: number;
  no_responsive_docs: number;
}

export interface DeficiencyReport {
  id: string;
  case_name: string;
  production_id: string;
  rtp_document_id: string;
  oc_response_document_id: string;
  analysis_status: 'pending' | 'processing' | 'completed' | 'failed';
  total_requests: number;
  summary_statistics: SummaryStatistics;
  deficiency_items: DeficiencyItem[];
  created_at: string;
  updated_at: string;
}

export interface DeficiencyItemUpdate {
  classification?: DeficiencyItem['classification'];
  notes?: string;
}

export interface BulkUpdateRequest {
  item_ids: string[];
  updates: DeficiencyItemUpdate;
}

export interface DeficiencyUIState {
  selectedItems: Set<string>;
  editingItemId: string | null;
  isAllSelected: boolean;
  expandedItems: Set<string>;
  setSelectedItems: (items: Set<string>) => void;
  toggleItemSelection: (itemId: string) => void;
  toggleAllSelection: (totalItems: number) => void;
  setEditingItemId: (itemId: string | null) => void;
  toggleItemExpansion: (itemId: string) => void;
  clearSelection: () => void;
}