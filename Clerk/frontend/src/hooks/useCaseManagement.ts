import { useState, useCallback } from 'react';
import axios from 'axios';
import { useCaseSelection } from './useCaseSelection';

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
      const response = await axios.post<Case>(
        `${API_BASE_URL}/api/cases`,
        caseData,
        {
          headers: {
            'Content-Type': 'application/json',
            // Include auth headers if available
            ...(localStorage.getItem('access_token') && {
              Authorization: `Bearer ${localStorage.getItem('access_token')}`,
            }),
          },
        }
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
      const response = await axios.put<Case>(
        `${API_BASE_URL}/api/cases/${caseId}`,
        { status },
        {
          headers: {
            'Content-Type': 'application/json',
            'X-Case-ID': caseId,
            ...(localStorage.getItem('access_token') && {
              Authorization: `Bearer ${localStorage.getItem('access_token')}`,
            }),
          },
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
      await axios.post(
        `${API_BASE_URL}/api/cases/${caseId}/permissions`,
        permissionData,
        {
          headers: {
            'Content-Type': 'application/json',
            'X-Case-ID': caseId,
            ...(localStorage.getItem('access_token') && {
              Authorization: `Bearer ${localStorage.getItem('access_token')}`,
            }),
          },
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

      const response = await axios.get<{ cases: Case[] }>(
        `${API_BASE_URL}/api/cases?${params.toString()}`,
        {
          headers: {
            ...(localStorage.getItem('access_token') && {
              Authorization: `Bearer ${localStorage.getItem('access_token')}`,
            }),
          },
        }
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