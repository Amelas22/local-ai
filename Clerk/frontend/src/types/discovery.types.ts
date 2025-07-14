export enum DocumentType {
  // Legal Filings
  MOTION = 'motion',
  COMPLAINT = 'complaint',
  ANSWER = 'answer',
  MEMORANDUM = 'memorandum',
  BRIEF = 'brief',
  ORDER = 'order',
  
  // Discovery Documents
  DEPOSITION = 'deposition',
  INTERROGATORY = 'interrogatory',
  REQUEST_FOR_ADMISSION = 'request_for_admission',
  REQUEST_FOR_PRODUCTION = 'request_for_production',
  
  // Evidence Documents
  POLICE_REPORT = 'police_report',
  EXPERT_REPORT = 'expert_report',
  PHOTOS = 'photos',
  VIDEOS = 'videos',
  
  // Business/Financial
  INVOICE = 'invoice',
  CONTRACT = 'contract',
  FINANCIAL_RECORDS = 'financial_records',
  EMPLOYMENT_RECORDS = 'employment_records',
  INSURANCE = 'insurance',
  
  // Other Evidence
  CORRESPONDENCE = 'correspondence',
  INCIDENT_REPORT = 'incident_report',
  WITNESS_STATEMENT = 'witness_statement',
  AFFIDAVIT = 'affidavit',
  
  // Unknown
  UNKNOWN = 'unknown',
}

export enum ProcessingStage {
  INITIALIZING = 'initializing',
  DISCOVERING_DOCUMENTS = 'discovering_documents',
  CLASSIFYING_DOCUMENTS = 'classifying_documents',
  CHUNKING_DOCUMENTS = 'chunking_documents',
  GENERATING_EMBEDDINGS = 'generating_embeddings',
  STORING_VECTORS = 'storing_vectors',
  EXTRACTING_FACTS = 'extracting_facts',
  COMPLETING = 'completing',
}

export interface DiscoveryProcessingRequest {
  folder_id: string;
  case_name: string;
  matter_id?: string;
  case_id?: string;
  production_batch: string;
  producing_party: string;
  production_date?: string;
  responsive_to_requests: string[];
  confidentiality_designation?: string;
  override_fact_extraction: boolean;
}

export interface BatesRange {
  start: string;
  end: string;
}

export interface ProcessingDocument {
  id: string;
  title: string;
  type: DocumentType;
  batesRange?: BatesRange;
  pageCount: number;
  confidence: number;
  status: 'pending' | 'processing' | 'completed' | 'error';
  progress: number;
  chunks?: number;
  vectors?: number;
  error?: string;
}

export interface ProcessingSummary {
  totalDocuments: number;
  processedDocuments: number;
  totalChunks: number;
  totalVectors: number;
  totalErrors: number;
  processingTime: number;
  averageConfidence: number;
  totalFacts: number;
}

// WebSocket event types
export interface DiscoveryWebSocketEvents {
  'discovery:started': {
    caseId: string;
    totalFiles: number;
    processingId: string;
  };
  'discovery:document_found': {
    documentId: string;
    title: string;
    type: DocumentType;
    pageCount: number;
    batesRange?: BatesRange;
    confidence: number;
  };
  'discovery:chunking': {
    documentId: string;
    progress: number;
    chunksCreated: number;
  };
  'discovery:embedding': {
    documentId: string;
    chunkId: string;
    progress: number;
  };
  'discovery:stored': {
    documentId: string;
    vectorsStored: number;
  };
  'discovery:completed': {
    processingId: string;
    summary: ProcessingSummary;
  };
  'discovery:error': {
    processingId: string;
    documentId?: string;
    error: string;
    stage: ProcessingStage;
  };
  'discovery:fact_extracted': {
    factId: string;
    documentId: string;
    content: string;
    category: string;
    confidence: number;
  };
}

export interface DiscoveryProcessingResponse {
  processing_id: string;
  status: 'started' | 'processing' | 'completed' | 'error';
  message?: string;
}

export interface FactSource {
  doc_id: string;
  doc_title: string;
  page: number;
  bbox: number[];
  text_snippet: string;
}

export interface ExtractedFactWithSource {
  id: string;
  content: string;
  category: string;
  confidence: number;
  source: FactSource;
  is_edited: boolean;
  edit_history: FactEditHistory[];
  review_status: 'pending' | 'reviewed' | 'rejected';
  created_at: string;
  updated_at: string;
  entities?: string[];
  keywords?: string[];
  dates?: string[];
}

export interface FactEditHistory {
  timestamp: string;
  user_id: string;
  old_content: string;
  new_content: string;
  reason?: string;
}

export interface FactUpdateRequest {
  content: string;
  category?: string;
  reason?: string;
}

export interface FactSearchRequest {
  case_name: string;
  query?: string;
  category?: string;
  confidence_min?: number;
  confidence_max?: number;
  document_ids?: string[];
  review_status?: 'pending' | 'reviewed' | 'rejected';
  is_edited?: boolean;
  limit?: number;
  offset?: number;
}

export interface FactSearchResponse {
  facts: ExtractedFactWithSource[];
  total: number;
  limit: number;
  offset: number;
}

export interface FactBulkOperation {
  operation: 'mark_reviewed' | 'delete' | 'change_category';
  fact_ids: string[];
  category?: string;
}

export interface DiscoveryDocument {
  id: string;
  title: string;
  type: DocumentType;
  bates_range?: BatesRange;
  page_count: number;
  confidence: number;
  file_path?: string;
  box_file_id?: string;
}