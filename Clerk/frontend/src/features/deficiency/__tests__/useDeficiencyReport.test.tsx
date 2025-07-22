import React from 'react';
import { renderHook } from '@testing-library/react';
import { Provider } from 'react-redux';
import { configureStore } from '@reduxjs/toolkit';
import { useDeficiencyReport } from '../hooks/useDeficiencyReport';
import { baseApi } from '../../../store/api/baseApi';

const createMockStore = () => {
  return configureStore({
    reducer: {
      [baseApi.reducerPath]: baseApi.reducer
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
  deficiency_items: [],
  created_at: '2024-01-01T00:00:00Z',
  updated_at: '2024-01-01T00:00:00Z'
};

describe('useDeficiencyReport', () => {
  let store: ReturnType<typeof createMockStore>;

  beforeEach(() => {
    store = createMockStore();
  });

  it('returns loading state initially', () => {
    const wrapper = ({ children }: { children: React.ReactNode }) => (
      <Provider store={store}>{children}</Provider>
    );

    const { result } = renderHook(() => useDeficiencyReport('report-123'), { wrapper });

    expect(result.current.isLoading).toBe(true);
    expect(result.current.data).toBeUndefined();
    expect(result.current.error).toBeUndefined();
  });

  it('returns report data when loaded', async () => {
    const mockUseQuery = jest.spyOn(baseApi, 'useGetDeficiencyReportQuery' as keyof typeof baseApi);
    (mockUseQuery as jest.Mock).mockReturnValue({
      data: mockReport,
      isLoading: false,
      error: null,
      refetch: jest.fn()
    });

    const wrapper = ({ children }: { children: React.ReactNode }) => (
      <Provider store={store}>{children}</Provider>
    );

    const { result } = renderHook(() => useDeficiencyReport('report-123'), { wrapper });

    expect(result.current.isLoading).toBe(false);
    expect(result.current.data).toEqual(mockReport);
    expect(result.current.error).toBeNull();
  });

  it('returns error when request fails', () => {
    const mockError = { message: 'Failed to fetch' };
    const mockUseQuery = jest.spyOn(baseApi, 'useGetDeficiencyReportQuery' as keyof typeof baseApi);
    (mockUseQuery as jest.Mock).mockReturnValue({
      data: undefined,
      isLoading: false,
      error: mockError,
      refetch: jest.fn()
    });

    const wrapper = ({ children }: { children: React.ReactNode }) => (
      <Provider store={store}>{children}</Provider>
    );

    const { result } = renderHook(() => useDeficiencyReport('report-123'), { wrapper });

    expect(result.current.isLoading).toBe(false);
    expect(result.current.data).toBeUndefined();
    expect(result.current.error).toEqual(mockError);
  });
});