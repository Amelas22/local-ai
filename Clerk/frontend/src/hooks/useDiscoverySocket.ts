import { useEffect, useCallback, useRef } from 'react';
import { useAppDispatch } from './redux';
import { useWebSocket } from './useWebSocket';
import { 
  setProcessingStatus,
  addDocument,
  updateDocument,
  setProcessingSummary,
  setProcessingError,
  addExtractedFact,
  updateExtractedFact,
  removeExtractedFact,
} from '../store/slices/discoverySlice';
import { showNotification } from '../store/slices/uiSlice';
import { 
  DiscoveryWebSocketEvents,
  ProcessingStage,
  ExtractedFactWithSource 
} from '../types/discovery.types';

interface UseDiscoverySocketOptions {
  processingId?: string;
  caseId?: string;
  onFactExtracted?: (fact: ExtractedFactWithSource) => void;
  onProcessingComplete?: () => void;
  onError?: (error: string) => void;
}

export const useDiscoverySocket = (options: UseDiscoverySocketOptions = {}) => {
  const { processingId, caseId, onFactExtracted, onProcessingComplete, onError } = options;
  const dispatch = useAppDispatch();
  const { socket, isConnected } = useWebSocket();
  const subscribedRef = useRef(false);
  const reconnectTimeoutRef = useRef<NodeJS.Timeout>();

  const handleDiscoveryStarted = useCallback((data: DiscoveryWebSocketEvents['discovery:started']) => {
    if (processingId && data.processingId !== processingId) return;
    
    dispatch(setProcessingStatus({
      processingId: data.processingId,
      status: 'processing',
      stage: ProcessingStage.DISCOVERING_DOCUMENTS,
    }));
  }, [dispatch, processingId]);

  const handleDocumentFound = useCallback((data: DiscoveryWebSocketEvents['discovery:document_found']) => {
    dispatch(addDocument({
      id: data.documentId,
      title: data.title,
      type: data.type,
      batesRange: data.batesRange,
      pageCount: data.pageCount,
      confidence: data.confidence,
      status: 'pending',
      progress: 0,
    }));
  }, [dispatch]);

  const handleChunking = useCallback((data: DiscoveryWebSocketEvents['discovery:chunking']) => {
    dispatch(updateDocument({
      id: data.documentId,
      status: 'processing',
      progress: data.progress,
      chunks: data.chunksCreated,
    }));
  }, [dispatch]);

  const handleEmbedding = useCallback((data: DiscoveryWebSocketEvents['discovery:embedding']) => {
    dispatch(updateDocument({
      id: data.documentId,
      progress: data.progress,
    }));
  }, [dispatch]);

  const handleStored = useCallback((data: DiscoveryWebSocketEvents['discovery:stored']) => {
    dispatch(updateDocument({
      id: data.documentId,
      status: 'completed',
      progress: 100,
      vectors: data.vectorsStored,
    }));
  }, [dispatch]);

  const handleFactExtracted = useCallback((data: DiscoveryWebSocketEvents['discovery:fact_extracted']) => {
    const fact: ExtractedFactWithSource = {
      id: data.factId,
      content: data.content,
      category: data.category,
      confidence: data.confidence,
      source: {
        doc_id: data.documentId,
        doc_title: '',
        page: 0,
        bbox: [],
        text_snippet: '',
      },
      is_edited: false,
      edit_history: [],
      review_status: 'pending',
      created_at: new Date().toISOString(),
      updated_at: new Date().toISOString(),
    };

    dispatch(addExtractedFact(fact));
    onFactExtracted?.(fact);
  }, [dispatch, onFactExtracted]);

  const handleCompleted = useCallback((data: DiscoveryWebSocketEvents['discovery:completed']) => {
    if (processingId && data.processingId !== processingId) return;
    
    dispatch(setProcessingSummary(data.summary));
    dispatch(setProcessingStatus({
      processingId: data.processingId,
      status: 'completed',
      stage: ProcessingStage.COMPLETING,
    }));
    
    dispatch(showNotification({
      message: 'Discovery processing completed successfully',
      severity: 'success',
    }));
    
    onProcessingComplete?.();
  }, [dispatch, processingId, onProcessingComplete]);

  const handleError = useCallback((data: DiscoveryWebSocketEvents['discovery:error']) => {
    if (processingId && data.processingId !== processingId) return;
    
    dispatch(setProcessingError({
      error: data.error,
      documentId: data.documentId,
    }));
    
    if (data.documentId) {
      dispatch(updateDocument({
        id: data.documentId,
        status: 'error',
        error: data.error,
      }));
    }
    
    dispatch(showNotification({
      message: `Discovery error: ${data.error}`,
      severity: 'error',
    }));
    
    onError?.(data.error);
  }, [dispatch, processingId, onError]);

  const handleFactUpdated = useCallback((data: { fact_id: string; content: string; updated_by: string }) => {
    dispatch(updateExtractedFact({
      id: data.fact_id,
      content: data.content,
      is_edited: true,
    }));
  }, [dispatch]);

  const handleFactDeleted = useCallback((data: { fact_id: string; deleted_by: string }) => {
    dispatch(removeExtractedFact(data.fact_id));
  }, [dispatch]);

  const subscribeToDiscoveryEvents = useCallback(() => {
    if (!socket || !isConnected || subscribedRef.current) return;

    socket.on('discovery:started', handleDiscoveryStarted);
    socket.on('discovery:document_found', handleDocumentFound);
    socket.on('discovery:chunking', handleChunking);
    socket.on('discovery:embedding', handleEmbedding);
    socket.on('discovery:stored', handleStored);
    socket.on('discovery:fact_extracted', handleFactExtracted);
    socket.on('discovery:completed', handleCompleted);
    socket.on('discovery:error', handleError);
    socket.on('fact:updated', handleFactUpdated);
    socket.on('fact:deleted', handleFactDeleted);

    if (caseId) {
      socket.emit('subscribe_case', { case_id: caseId });
    }

    subscribedRef.current = true;
  }, [
    socket,
    isConnected,
    caseId,
    handleDiscoveryStarted,
    handleDocumentFound,
    handleChunking,
    handleEmbedding,
    handleStored,
    handleFactExtracted,
    handleCompleted,
    handleError,
    handleFactUpdated,
    handleFactDeleted,
  ]);

  const unsubscribeFromDiscoveryEvents = useCallback(() => {
    if (!socket || !subscribedRef.current) return;

    socket.off('discovery:started');
    socket.off('discovery:document_found');
    socket.off('discovery:chunking');
    socket.off('discovery:embedding');
    socket.off('discovery:stored');
    socket.off('discovery:fact_extracted');
    socket.off('discovery:completed');
    socket.off('discovery:error');
    socket.off('fact:updated');
    socket.off('fact:deleted');

    if (caseId) {
      socket.emit('unsubscribe_case', { case_id: caseId });
    }

    subscribedRef.current = false;
  }, [socket, caseId]);

  const updateFact = useCallback(async (factId: string, content: string, reason?: string) => {
    if (!socket || !isConnected || !caseId) {
      throw new Error('Socket not connected or case not selected');
    }

    return new Promise((resolve, reject) => {
      socket.emit('fact:update', {
        case_id: caseId,
        fact_id: factId,
        content,
        reason,
      }, (response: any) => {
        if (response.error) {
          reject(new Error(response.error));
        } else {
          resolve(response);
        }
      });
    });
  }, [socket, isConnected, caseId]);

  const deleteFact = useCallback(async (factId: string) => {
    if (!socket || !isConnected || !caseId) {
      throw new Error('Socket not connected or case not selected');
    }

    return new Promise((resolve, reject) => {
      socket.emit('fact:delete', {
        case_id: caseId,
        fact_id: factId,
      }, (response: any) => {
        if (response.error) {
          reject(new Error(response.error));
        } else {
          resolve(response);
        }
      });
    });
  }, [socket, isConnected, caseId]);

  useEffect(() => {
    subscribeToDiscoveryEvents();

    return () => {
      unsubscribeFromDiscoveryEvents();
      if (reconnectTimeoutRef.current) {
        clearTimeout(reconnectTimeoutRef.current);
      }
    };
  }, [subscribeToDiscoveryEvents, unsubscribeFromDiscoveryEvents]);

  useEffect(() => {
    if (!isConnected && subscribedRef.current) {
      subscribedRef.current = false;
      reconnectTimeoutRef.current = setTimeout(() => {
        subscribeToDiscoveryEvents();
      }, 1000);
    }
  }, [isConnected, subscribeToDiscoveryEvents]);

  return {
    isConnected,
    updateFact,
    deleteFact,
    subscribeToDiscoveryEvents,
    unsubscribeFromDiscoveryEvents,
  };
};