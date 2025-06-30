import { createSlice, PayloadAction } from '@reduxjs/toolkit';
import type { DocumentType, ProcessingStage } from '@/types/discovery.types';

interface DiscoveryDocument {
  id: string;
  title: string;
  type: DocumentType;
  batesRange?: {
    start: string;
    end: string;
  };
  confidence: number;
  status: 'processing' | 'completed' | 'error';
  error?: string;
}

export interface ProcessingStats {
  documentsFound: number;
  documentsProcessed: number;
  chunksCreated: number;
  vectorsStored: number;
  errors: number;
}

interface DiscoveryState {
  isProcessing: boolean;
  currentStage: ProcessingStage | null;
  processingStartTime: Date | null;
  processingEndTime: Date | null;
  documents: DiscoveryDocument[];
  stats: ProcessingStats;
  currentProcessingId: string | null;
  error: string | null;
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
  },
  currentProcessingId: null,
  error: null,
};

const discoverySlice = createSlice({
  name: 'discovery',
  initialState,
  reducers: {
    startProcessing: (state, action: PayloadAction<string>) => {
      state.isProcessing = true;
      state.currentProcessingId = action.payload;
      state.processingStartTime = new Date();
      state.processingEndTime = null;
      state.documents = [];
      state.stats = initialState.stats;
      state.error = null;
    },
    setCurrentStage: (state, action: PayloadAction<ProcessingStage>) => {
      state.currentStage = action.payload;
    },
    addDocument: (state, action: PayloadAction<DiscoveryDocument>) => {
      state.documents.push(action.payload);
      state.stats.documentsFound += 1;
    },
    updateDocument: (state, action: PayloadAction<{ id: string; updates: Partial<DiscoveryDocument> }>) => {
      const index = state.documents.findIndex(doc => doc.id === action.payload.id);
      if (index !== -1) {
        state.documents[index] = { ...state.documents[index], ...action.payload.updates };
        if (action.payload.updates.status === 'completed') {
          state.stats.documentsProcessed += 1;
        } else if (action.payload.updates.status === 'error') {
          state.stats.errors += 1;
        }
      }
    },
    updateStats: (state, action: PayloadAction<Partial<ProcessingStats>>) => {
      state.stats = { ...state.stats, ...action.payload };
    },
    completeProcessing: (state) => {
      state.isProcessing = false;
      state.currentStage = null;
      state.processingEndTime = new Date();
    },
    setError: (state, action: PayloadAction<string>) => {
      state.error = action.payload;
      state.isProcessing = false;
    },
    resetProcessing: (state) => {
      return initialState;
    },
  },
});

export const {
  startProcessing,
  setCurrentStage,
  addDocument,
  updateDocument,
  updateStats,
  completeProcessing,
  setError,
  resetProcessing,
} = discoverySlice.actions;

export default discoverySlice.reducer;