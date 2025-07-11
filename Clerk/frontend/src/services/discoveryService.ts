import { apiClient } from './utils/apiClient';
import { 
  DiscoveryProcessingResponse,
  ExtractedFactWithSource,
  FactUpdateRequest,
  FactSearchRequest,
  FactSearchResponse,
  FactBulkOperation
} from '../types/discovery.types';

class DiscoveryService {
  private readonly baseUrl = '/api/discovery';

  async processDiscovery(formData: FormData): Promise<DiscoveryProcessingResponse> {
    const response = await apiClient.post(`${this.baseUrl}/process`, formData, {
      headers: {
        'Content-Type': 'multipart/form-data',
      },
    });
    return response.data;
  }

  async getProcessingStatus(processingId: string): Promise<DiscoveryProcessingResponse> {
    const response = await apiClient.get(`${this.baseUrl}/status/${processingId}`);
    return response.data;
  }

  async searchFacts(request: FactSearchRequest): Promise<FactSearchResponse> {
    const response = await apiClient.post(`${this.baseUrl}/facts/search`, request);
    return response.data;
  }

  async getFact(factId: string): Promise<ExtractedFactWithSource> {
    const response = await apiClient.get(`${this.baseUrl}/facts/${factId}`);
    return response.data;
  }

  async updateFact(factId: string, request: FactUpdateRequest): Promise<ExtractedFactWithSource> {
    const response = await apiClient.put(`${this.baseUrl}/facts/${factId}`, request);
    return response.data;
  }

  async deleteFact(factId: string): Promise<void> {
    await apiClient.delete(`${this.baseUrl}/facts/${factId}`);
  }

  async bulkUpdateFacts(operation: FactBulkOperation): Promise<{ updated: number }> {
    const response = await apiClient.post(`${this.baseUrl}/facts/bulk`, operation);
    return response.data;
  }

  async markFactsReviewed(factIds: string[]): Promise<{ updated: number }> {
    return this.bulkUpdateFacts({
      operation: 'mark_reviewed',
      fact_ids: factIds,
    });
  }

  async bulkDeleteFacts(factIds: string[]): Promise<{ deleted: number }> {
    const response = await apiClient.post(`${this.baseUrl}/facts/bulk`, {
      operation: 'delete',
      fact_ids: factIds,
    });
    return response.data;
  }

  async getDocumentPdf(documentId: string): Promise<Blob> {
    const response = await apiClient.get(`${this.baseUrl}/documents/${documentId}/pdf`, {
      responseType: 'blob',
    });
    return response.data;
  }

  async getBoxFolders(parentId: string = '0'): Promise<any[]> {
    const response = await apiClient.get(`${this.baseUrl}/box/folders`, {
      params: { parent_id: parentId },
    });
    return response.data;
  }

  async getBoxFiles(folderId: string): Promise<any[]> {
    const response = await apiClient.get(`${this.baseUrl}/box/files`, {
      params: { folder_id: folderId },
    });
    return response.data;
  }
}

export const discoveryService = new DiscoveryService();