import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';
import { useEffect, useRef } from 'react';
import { useWebSocket } from './useWebSocket';
import { goodFaithLetterAPI, GenerateLetterParams, CustomizeLetterParams } from '../services/api/goodFaithLetter';
import { ExportFormat, LetterUpdateEvent } from '../types/goodFaithLetter.types';

export const useGoodFaithLetter = (letterId?: string) => {
  const queryClient = useQueryClient();
  const { on } = useWebSocket();
  const unsubscribeRefs = useRef<(() => void)[]>([]);

  // Query for fetching a specific letter
  const letterQuery = useQuery({
    queryKey: ['letter', letterId],
    queryFn: () => goodFaithLetterAPI.getLetter(letterId!),
    enabled: !!letterId,
    refetchInterval: (data) => {
      // Refetch draft letters periodically to get updates
      if (data && 'status' in data && (data.status === 'draft' || data.status === 'review')) {
        return 10000; // 10 seconds
      }
      return false;
    }
  });

  // Query for fetching letter versions
  const versionsQuery = useQuery({
    queryKey: ['letter-versions', letterId],
    queryFn: () => goodFaithLetterAPI.getLetterVersions(letterId!),
    enabled: !!letterId
  });

  // Mutation for generating a new letter
  const generateMutation = useMutation({
    mutationFn: (params: GenerateLetterParams) => goodFaithLetterAPI.generateLetter(params),
    onSuccess: (data) => {
      queryClient.setQueryData(['letter', data.id], data);
      queryClient.invalidateQueries({ queryKey: ['letters'] });
    }
  });

  // Mutation for customizing a letter
  const customizeMutation = useMutation({
    mutationFn: ({ letterId, params }: { letterId: string; params: CustomizeLetterParams }) => 
      goodFaithLetterAPI.customizeLetter(letterId, params),
    onSuccess: (data, variables) => {
      queryClient.setQueryData(['letter', variables.letterId], data);
      queryClient.invalidateQueries({ queryKey: ['letter-versions', variables.letterId] });
    }
  });

  // Mutation for finalizing a letter
  const finalizeMutation = useMutation({
    mutationFn: (letterId: string) => goodFaithLetterAPI.finalizeLetter(letterId),
    onSuccess: (data, letterId) => {
      queryClient.setQueryData(['letter', letterId], data);
      queryClient.invalidateQueries({ queryKey: ['letters'] });
    }
  });

  // Mutation for exporting a letter
  const exportMutation = useMutation({
    mutationFn: ({ letterId, format }: { letterId: string; format: ExportFormat['format'] }) => 
      goodFaithLetterAPI.exportLetter(letterId, format),
    onSuccess: (blob, variables) => {
      // Create download link
      const url = window.URL.createObjectURL(blob);
      const link = document.createElement('a');
      link.href = url;
      
      // Generate filename
      const date = new Date().toISOString().split('T')[0];
      const extension = variables.format;
      link.download = `Good_Faith_Letter_${date}.${extension}`;
      
      document.body.appendChild(link);
      link.click();
      document.body.removeChild(link);
      window.URL.revokeObjectURL(url);
    }
  });

  // Mutation for restoring a version
  const restoreVersionMutation = useMutation({
    mutationFn: ({ letterId, version }: { letterId: string; version: number }) => 
      goodFaithLetterAPI.restoreVersion(letterId, version),
    onSuccess: (data, variables) => {
      queryClient.setQueryData(['letter', variables.letterId], data);
      queryClient.invalidateQueries({ queryKey: ['letter-versions', variables.letterId] });
    }
  });

  // WebSocket listeners for real-time updates
  useEffect(() => {
    if (!letterId) return;

    const handleLetterUpdate = (data: LetterUpdateEvent) => {
      if (data.letter_id === letterId) {
        queryClient.invalidateQueries({ queryKey: ['letter', letterId] });
        queryClient.invalidateQueries({ queryKey: ['letter-versions', letterId] });
      }
    };

    const events = [
      'letter:draft_created',
      'letter:customization_applied',
      'letter:finalized',
      'letter:version_restored'
    ] as const;

    // Clear previous subscriptions
    unsubscribeRefs.current.forEach(unsub => unsub());
    unsubscribeRefs.current = [];

    // Subscribe to events and store unsubscribe functions
    events.forEach(event => {
      const unsubscribe = on(event, handleLetterUpdate);
      unsubscribeRefs.current.push(unsubscribe);
    });

    return () => {
      unsubscribeRefs.current.forEach(unsub => unsub());
      unsubscribeRefs.current = [];
    };
  }, [letterId, on, queryClient]);

  return {
    // Queries
    letter: letterQuery.data,
    isLoadingLetter: letterQuery.isLoading,
    letterError: letterQuery.error,
    refetchLetter: letterQuery.refetch,

    versions: versionsQuery.data,
    isLoadingVersions: versionsQuery.isLoading,
    versionsError: versionsQuery.error,

    // Mutations
    generateLetter: generateMutation.mutate,
    isGenerating: generateMutation.isPending,
    generateError: generateMutation.error,

    customizeLetter: customizeMutation.mutate,
    isCustomizing: customizeMutation.isPending,
    customizeError: customizeMutation.error,

    finalizeLetter: finalizeMutation.mutate,
    isFinalizing: finalizeMutation.isPending,
    finalizeError: finalizeMutation.error,

    exportLetter: exportMutation.mutate,
    isExporting: exportMutation.isPending,
    exportError: exportMutation.error,

    restoreVersion: restoreVersionMutation.mutate,
    isRestoringVersion: restoreVersionMutation.isPending,
    restoreError: restoreVersionMutation.error
  };
};