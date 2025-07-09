import { useState, useCallback } from 'react';
import { useCaseSelection } from './useCaseSelection';
import { apiClient } from '@/services/utils/apiClient';

interface CreateCaseRequest {
  name: string;
  metadata?: Record<string, any>;
}

interface Case {
  id: string;
  name: string;
  law_firm_id: string;
  collection_name: string;
  status: 'active' | 'archived' | 'closed';
  created_by: string;
  created_at: string;
  updated_at: string;
  metadata: Record<string, any>;
}

interface CasePermissionRequest {
  user_id: string;
  permission_level: 'read' | 'write' | 'admin';
  expires_at?: string;
}

export const useCaseManagement = () => {
  const { refreshCases } = useCaseSelection();
  const [isCreating, setIsCreating] = useState(false);
  const [isUpdating, setIsUpdating] = useState(false);
  const [error, setError] = useState<string | null>(null);

  // Use empty base URL to use relative paths (which will be handled by the server/proxy)
  const API_BASE_URL = '';

  // Create a new case
  const createCase = useCallback(async (caseData: CreateCaseRequest): Promise<Case> => {
    setIsCreating(true);
    setError(null);

    try {
      const response = await apiClient.post<Case>(
        `${API_BASE_URL}/api/cases`,
        caseData
      );

      // Refresh the case list after successful creation
      await refreshCases();

      return response.data;
    } catch (err: any) {
      const errorMessage = err.response?.data?.detail || err.message || 'Failed to create case';
      setError(errorMessage);
      throw err;
    } finally {
      setIsCreating(false);
    }
  }, [API_BASE_URL, refreshCases]);

  // Update case status
  const updateCaseStatus = useCallback(async (
    caseId: string,
    status: 'active' | 'archived' | 'closed'
  ): Promise<Case> => {
    setIsUpdating(true);
    setError(null);

    try {
      const response = await apiClient.put<Case>(
        `${API_BASE_URL}/api/cases/${caseId}`,
        { status },
        {
          headers: {
            'X-Case-ID': caseId
          }
        }
      );

      // Refresh the case list after successful update
      await refreshCases();

      return response.data;
    } catch (err: any) {
      const errorMessage = err.response?.data?.detail || err.message || 'Failed to update case';
      setError(errorMessage);
      throw err;
    } finally {
      setIsUpdating(false);
    }
  }, [API_BASE_URL, refreshCases]);

  // Grant case permission
  const grantCasePermission = useCallback(async (
    caseId: string,
    permissionData: CasePermissionRequest
  ): Promise<void> => {
    setIsUpdating(true);
    setError(null);

    try {
      await apiClient.post(
        `${API_BASE_URL}/api/cases/${caseId}/permissions`,
        permissionData,
        {
          headers: {
            'X-Case-ID': caseId
          }
        }
      );
    } catch (err: any) {
      const errorMessage = err.response?.data?.detail || err.message || 'Failed to grant permission';
      setError(errorMessage);
      throw err;
    } finally {
      setIsUpdating(false);
    }
  }, [API_BASE_URL]);

  // Get user cases
  const getUserCases = useCallback(async (
    lawFirmId?: string,
    includeArchived: boolean = false
  ): Promise<Case[]> => {
    try {
      const params = new URLSearchParams();
      if (lawFirmId) params.append('law_firm_id', lawFirmId);
      if (includeArchived) params.append('include_archived', 'true');

      const response = await apiClient.get<{ cases: Case[] }>(
        `${API_BASE_URL}/api/cases?${params.toString()}`
      );

      return response.data.cases || [];
    } catch (err: any) {
      const errorMessage = err.response?.data?.detail || err.message || 'Failed to fetch cases';
      setError(errorMessage);
      throw err;
    }
  }, [API_BASE_URL]);

  return {
    createCase,
    updateCaseStatus,
    grantCasePermission,
    getUserCases,
    isCreating,
    isUpdating,
    error,
  };
};