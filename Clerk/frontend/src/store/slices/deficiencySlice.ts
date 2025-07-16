import { createSlice, PayloadAction, createAsyncThunk } from '@reduxjs/toolkit';
import { 
  DeficiencyReport, 
  DeficiencyAnalysisRequest
} from '../../types/discovery.types';
import { discoveryService } from '../../services/discoveryService';

interface DeficiencyState {
  currentReport: DeficiencyReport | null;
  analysisInProgress: boolean;
  analysisId: string | null;
  error: string | null;
  loading: boolean;
  reports: Record<string, DeficiencyReport>; // Cache of reports by ID
}

const initialState: DeficiencyState = {
  currentReport: null,
  analysisInProgress: false,
  analysisId: null,
  error: null,
  loading: false,
  reports: {},
};

// Async thunks
export const startDeficiencyAnalysis = createAsyncThunk(
  'deficiency/startAnalysis',
  async (request: DeficiencyAnalysisRequest) => {
    const response = await discoveryService.startDeficiencyAnalysis(request);
    return response;
  }
);

export const fetchDeficiencyReport = createAsyncThunk(
  'deficiency/fetchReport',
  async (reportId: string) => {
    const response = await discoveryService.getDeficiencyReport(reportId);
    return response;
  }
);

const deficiencySlice = createSlice({
  name: 'deficiency',
  initialState,
  reducers: {
    setAnalysisInProgress: (state, action: PayloadAction<boolean>) => {
      state.analysisInProgress = action.payload;
    },
    setCurrentReport: (state, action: PayloadAction<DeficiencyReport | null>) => {
      state.currentReport = action.payload;
      if (action.payload) {
        state.reports[action.payload.id] = action.payload;
      }
    },
    updateReport: (state, action: PayloadAction<DeficiencyReport>) => {
      const report = action.payload;
      state.reports[report.id] = report;
      if (state.currentReport?.id === report.id) {
        state.currentReport = report;
      }
    },
    clearError: (state) => {
      state.error = null;
    },
    handleWebSocketEvent: (state, action: PayloadAction<any>) => {
      const event = action.payload;
      
      switch (event.type) {
        case 'deficiency_analysis_started':
          state.analysisInProgress = true;
          state.analysisId = event.analysisId;
          break;
          
        case 'deficiency_analysis_progress':
          // Update progress if needed
          break;
          
        case 'deficiency_analysis_completed':
          state.analysisInProgress = false;
          // Optionally fetch the complete report
          break;
          
        case 'deficiency_analysis_error':
          state.analysisInProgress = false;
          state.error = event.error;
          break;
      }
    },
  },
  extraReducers: (builder) => {
    builder
      // Start analysis
      .addCase(startDeficiencyAnalysis.pending, (state) => {
        state.loading = true;
        state.error = null;
      })
      .addCase(startDeficiencyAnalysis.fulfilled, (state, action) => {
        state.loading = false;
        state.analysisInProgress = true;
        state.analysisId = action.payload.analysis_id;
      })
      .addCase(startDeficiencyAnalysis.rejected, (state, action) => {
        state.loading = false;
        state.error = action.error.message || 'Failed to start deficiency analysis';
      })
      
      // Fetch report
      .addCase(fetchDeficiencyReport.pending, (state) => {
        state.loading = true;
        state.error = null;
      })
      .addCase(fetchDeficiencyReport.fulfilled, (state, action) => {
        state.loading = false;
        state.currentReport = action.payload;
        state.reports[action.payload.id] = action.payload;
      })
      .addCase(fetchDeficiencyReport.rejected, (state, action) => {
        state.loading = false;
        state.error = action.error.message || 'Failed to fetch deficiency report';
      });
  },
});

export const {
  setAnalysisInProgress,
  setCurrentReport,
  updateReport,
  clearError,
  handleWebSocketEvent,
} = deficiencySlice.actions;

export default deficiencySlice.reducer;