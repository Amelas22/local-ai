import React from 'react';
import { render, screen, waitFor } from '@testing-library/react';
import { Provider } from 'react-redux';
import { configureStore } from '@reduxjs/toolkit';
import { DeficiencyReportView } from '../components/DeficiencyReportView';
import { baseApi } from '../../../store/api/baseApi';
import deficiencyUIReducer from '../stores/deficiencyUIStore';
import { DeficiencyReport } from '../types/DeficiencyReport.types';

const createMockStore = () => {
  return configureStore({
    reducer: {
      [baseApi.reducerPath]: baseApi.reducer,
      deficiencyUI: deficiencyUIReducer
    },
    middleware: (getDefaultMiddleware) =>
      getDefaultMiddleware().concat(baseApi.middleware)
  });
};

const mockReport: DeficiencyReport = {
  id: 'report-123',
  case_name: 'Test Case',
  production_id: 'prod-123',
  rtp_document_id: 'rtp-123',
  oc_response_document_id: 'oc-123',
  analysis_status: 'completed',
  total_requests: 10,
  summary_statistics: {
    fully_produced: 5,
    partially_produced: 2,
    not_produced: 2,
    no_responsive_docs: 1
  },
  deficiency_items: [
    {
      id: 'item-1',
      report_id: 'report-123',
      request_number: 'RFP No. 1',
      request_text: 'All documents related to contract',
      oc_response_text: 'No responsive documents',
      classification: 'no_responsive_docs',
      confidence_score: 0.95,
      evidence_chunks: []
    }
  ],
  created_at: '2024-01-01T00:00:00Z',
  updated_at: '2024-01-01T00:00:00Z'
};

describe('DeficiencyReportView', () => {
  let store: ReturnType<typeof createMockStore>;

  beforeEach(() => {
    store = createMockStore();
  });

  it('renders loading state initially', () => {
    render(
      <Provider store={store}>
        <DeficiencyReportView reportId="report-123" />
      </Provider>
    );

    expect(screen.getByRole('progressbar')).toBeInTheDocument();
  });

  it('renders report data when loaded', async () => {
    const mockUseQuery = jest.spyOn(baseApi, 'useGetDeficiencyReportQuery' as keyof typeof baseApi);
    (mockUseQuery as jest.Mock).mockReturnValue({
      data: mockReport,
      isLoading: false,
      error: null,
      refetch: jest.fn()
    });

    render(
      <Provider store={store}>
        <DeficiencyReportView reportId="report-123" />
      </Provider>
    );

    await waitFor(() => {
      expect(screen.getByText('Deficiency Analysis Report')).toBeInTheDocument();
      expect(screen.getByText('Case: Test Case')).toBeInTheDocument();
      expect(screen.getByText('10')).toBeInTheDocument();
    });
  });

  it('renders error state when loading fails', () => {
    const mockUseQuery = jest.spyOn(baseApi, 'useGetDeficiencyReportQuery' as keyof typeof baseApi);
    (mockUseQuery as jest.Mock).mockReturnValue({
      data: null,
      isLoading: false,
      error: { message: 'Failed to load' },
      refetch: jest.fn()
    });

    render(
      <Provider store={store}>
        <DeficiencyReportView reportId="report-123" />
      </Provider>
    );

    expect(screen.getByText('Failed to load deficiency report. Please try again later.')).toBeInTheDocument();
  });

  it('renders empty state when no items found', () => {
    const mockUseQuery = jest.spyOn(baseApi, 'useGetDeficiencyReportQuery' as keyof typeof baseApi);
    (mockUseQuery as jest.Mock).mockReturnValue({
      data: { ...mockReport, deficiency_items: [] },
      isLoading: false,
      error: null,
      refetch: jest.fn()
    });

    render(
      <Provider store={store}>
        <DeficiencyReportView reportId="report-123" />
      </Provider>
    );

    expect(screen.getByText('No deficiency items found in this report.')).toBeInTheDocument();
  });
});