import { baseApi } from '../../../store/api/baseApi';
import { DeficiencyReport } from '../types/DeficiencyReport.types';

const deficiencyApi = baseApi.injectEndpoints({
  endpoints: (builder) => ({
    getDeficiencyReport: builder.query<DeficiencyReport, string>({
      query: (reportId) => `/api/deficiency/reports/${reportId}`,
      providesTags: (_result, _error, reportId) => [
        { type: 'DeficiencyReport', id: reportId }
      ]
    })
  })
});

export const useDeficiencyReport = (reportId: string) => {
  const { data, isLoading, error, refetch } = deficiencyApi.useGetDeficiencyReportQuery(reportId);
  
  return {
    data,
    isLoading,
    error,
    refetch
  };
};