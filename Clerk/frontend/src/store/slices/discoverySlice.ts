import { createSlice, PayloadAction } from '@reduxjs/toolkit';
import { 
  ProcessingStage, 
  ProcessingDocument, 
  ProcessingSummary
} from '../../types/discovery.types';

export interface ProcessingStats {
  documentsFound: number;
  documentsProcessed: number;
  chunksCreated: number;
  vectorsStored: number;
  errors: number;
  averageConfidence: number;
}

interface DiscoveryState {
  isProcessing: boolean;
  currentStage: ProcessingStage | null;
  processingStartTime: string | null;
  processingEndTime: string | null;
  documents: ProcessingDocument[];
  stats: ProcessingStats;
  currentProcessingId: string | null;
  error: string | null;
  totalFiles: number;
  caseId: string | null;
  currentChunkingDocument: ProcessingDocument | null;
}

const initialState: DiscoveryState = {
  isProcessing: false,
  currentStage: null,
  processingStartTime: null,
  processingEndTime: null,
  documents: [],
  stats: {
    documentsFound: 0,
    documentsProcessed: 0,
    chunksCreated: 0,
    vectorsStored: 0,
    errors: 0,
    averageConfidence: 0,
  },
  currentProcessingId: null,
  error: null,
  totalFiles: 0,
  caseId: null,
  currentChunkingDocument: null,
};

const discoverySlice = createSlice({
  name: 'discovery',
  initialState,
  reducers: {
    // Manual start processing (for form submission)
    startProcessing: (state, action: PayloadAction<string>) => {
      state.isProcessing = true;
      state.currentProcessingId = action.payload;
      state.processingStartTime = new Date().toISOString();
      state.processingEndTime = null;
      state.documents = [];
      state.stats = initialState.stats;
      state.error = null;
      state.currentStage = ProcessingStage.INITIALIZING;
    },
    
    // WebSocket event handlers
    processingStarted: (state, action: PayloadAction<{
      processingId: string;
      totalFiles: number;
      caseId: string;
    }>) => {
      state.isProcessing = true;
      state.currentProcessingId = action.payload.processingId;
      state.totalFiles = action.payload.totalFiles;
      state.caseId = action.payload.caseId;
      state.processingStartTime = new Date().toISOString();
      state.currentStage = ProcessingStage.DISCOVERING_DOCUMENTS;
    },
    
    documentFound: (state, action: PayloadAction<ProcessingDocument>) => {
      state.documents.push(action.payload);
      state.stats.documentsFound += 1;
      
      // Update average confidence
      const totalConfidence = state.documents.reduce((sum, doc) => sum + doc.confidence, 0);
      state.stats.averageConfidence = totalConfidence / state.documents.length;
    },
    
    documentChunking: (state, action: PayloadAction<{
      documentId: string;
      progress: number;
      chunksCreated: number;
    }>) => {
      const doc = state.documents.find(d => d.id === action.payload.documentId);
      if (doc) {
        doc.chunks = action.payload.chunksCreated;
        doc.progress = action.payload.progress;
        state.stats.chunksCreated += action.payload.chunksCreated;
        // Set current chunking document
        state.currentChunkingDocument = doc;
      }
      state.currentStage = ProcessingStage.CHUNKING_DOCUMENTS;
    },
    
    documentEmbedding: (state, _action: PayloadAction<{
      documentId: string;
      chunkId: string;
      progress: number;
    }>) => {
      state.currentStage = ProcessingStage.GENERATING_EMBEDDINGS;
      state.currentChunkingDocument = null; // Clear chunking document when moving to next stage
    },
    
    documentStored: (state, action: PayloadAction<{
      documentId: string;
      vectorsStored: number;
    }>) => {
      const doc = state.documents.find(d => d.id === action.payload.documentId);
      if (doc) {
        doc.vectors = action.payload.vectorsStored;
        state.stats.vectorsStored += action.payload.vectorsStored;
      }
      state.currentStage = ProcessingStage.STORING_VECTORS;
    },
    
    updateDocumentProgress: (state, action: PayloadAction<{
      documentId: string;
      progress: number;
      status: 'pending' | 'processing' | 'completed' | 'error';
      error?: string;
    }>) => {
      const doc = state.documents.find(d => d.id === action.payload.documentId);
      if (doc) {
        doc.progress = action.payload.progress;
        doc.status = action.payload.status;
        if (action.payload.error) {
          doc.error = action.payload.error;
        }
        
        if (action.payload.status === 'completed') {
          state.stats.documentsProcessed += 1;
        } else if (action.payload.status === 'error') {
          state.stats.errors += 1;
        }
      }
    },
    
    processingCompleted: (state, action: PayloadAction<{
      processingId: string;
      summary: ProcessingSummary;
    }>) => {
      state.isProcessing = false;
      state.currentStage = ProcessingStage.COMPLETING;
      state.processingEndTime = new Date().toISOString();
      state.currentChunkingDocument = null;
      
      // Update stats from summary
      state.stats = {
        documentsFound: action.payload.summary.totalDocuments,
        documentsProcessed: action.payload.summary.processedDocuments,
        chunksCreated: action.payload.summary.totalChunks,
        vectorsStored: action.payload.summary.totalVectors,
        errors: action.payload.summary.totalErrors,
        averageConfidence: action.payload.summary.averageConfidence,
      };
    },
    
    processingError: (state, action: PayloadAction<{
      processingId: string;
      documentId?: string;
      error: string;
      stage: ProcessingStage;
    }>) => {
      state.error = action.payload.error;
      state.stats.errors += 1;
      
      if (action.payload.documentId) {
        const doc = state.documents.find(d => d.id === action.payload.documentId);
        if (doc) {
          doc.status = 'error';
          doc.error = action.payload.error;
        }
      }
    },
    
    setCurrentStage: (state, action: PayloadAction<ProcessingStage>) => {
      state.currentStage = action.payload;
    },
    
    setError: (state, action: PayloadAction<string>) => {
      state.error = action.payload;
      state.isProcessing = false;
    },
    
    resetProcessing: () => {
      return initialState;
    },
  },
});

export const {
  startProcessing,
  processingStarted,
  documentFound,
  documentChunking,
  documentEmbedding,
  documentStored,
  updateDocumentProgress,
  processingCompleted,
  processingError,
  setCurrentStage,
  setError,
  resetProcessing,
} = discoverySlice.actions;

export default discoverySlice.reducer;