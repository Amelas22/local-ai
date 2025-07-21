import { apiClient } from '../../../services/utils/apiClient';
import { DeficiencyReport, DeficiencyItem, DeficiencyItemUpdate, BulkUpdateRequest } from '../types/DeficiencyReport.types';

export const deficiencyAPI = {
  async getDeficiencyReport(reportId: string): Promise<DeficiencyReport> {
    const response = await apiClient.get(`/api/deficiency/reports/${reportId}`);
    return response.data;
  },

  async updateDeficiencyItem(
    reportId: string,
    itemId: string,
    updates: DeficiencyItemUpdate
  ): Promise<DeficiencyItem> {
    const response = await apiClient.patch(
      `/api/deficiency/reports/${reportId}/items/${itemId}`,
      updates
    );
    return response.data;
  },

  async bulkUpdateDeficiencyItems(
    reportId: string,
    request: BulkUpdateRequest
  ): Promise<{ updated_count: number }> {
    const response = await apiClient.post(
      `/api/deficiency/reports/${reportId}/bulk-update`,
      request
    );
    return response.data;
  },

  async exportReport(reportId: string, format: 'pdf' | 'excel'): Promise<Blob> {
    const response = await apiClient.get(
      `/api/deficiency/reports/${reportId}/export`,
      {
        params: { format },
        responseType: 'blob'
      }
    );
    return response.data;
  }
};