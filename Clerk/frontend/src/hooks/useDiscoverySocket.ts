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

  // Store handlers in refs to prevent recreating them
  const handlersRef = useRef<Record<string, (...args: any[]) => void>>({});

  const handleDiscoveryStarted = useCallback((data: DiscoveryWebSocketEvents['discovery:started']) => {
    if (processingId && data.processingId !== processingId) return;
    
    dispatch(setProcessingStatus({
      processingId: data.processingId,
      status: 'processing',
      stage: ProcessingStage.DISCOVERING_DOCUMENTS,
    }));
  }, [dispatch, processingId]);

  const handleDocumentFound = useCallback((data: any) => {
    dispatch(addDocument({
      id: data.document_id,
      title: data.title,
      type: data.type,
      batesRange: data.bates_range,
      pageCount: parseInt(data.pages?.split('-')[1] || '0') - parseInt(data.pages?.split('-')[0] || '0') + 1,
      confidence: data.confidence,
      status: 'pending',
      progress: 0,
    }));
  }, [dispatch]);

  const handleChunking = useCallback((data: any) => {
    dispatch(updateDocument({
      id: data.document_id,
      status: 'processing',
      progress: data.progress || 0,
      chunks: data.chunks_created,
    }));
  }, [dispatch]);

  const handleEmbedding = useCallback((data: any) => {
    dispatch(updateDocument({
      id: data.document_id,
      progress: data.progress || 50,
    }));
  }, [dispatch]);

  const handleStored = useCallback((data: any) => {
    dispatch(updateDocument({
      id: data.document_id,
      status: 'completed',
      progress: 100,
      vectors: data.vectors_stored,
    }));
  }, [dispatch]);

  const handleFactExtracted = useCallback((data: any) => {
    const fact: ExtractedFactWithSource = {
      id: data.fact?.fact_id || data.fact_id,
      content: data.fact?.text || data.content,
      category: data.fact?.category || data.category,
      confidence: data.fact?.confidence || data.confidence,
      source: {
        doc_id: data.document_id,
        doc_title: '',
        page: 0,
        bbox: [],
        text_snippet: '',
      },
      entities: data.fact?.entities || [],
      keywords: data.fact?.dates || [],
      is_edited: false,
      edit_history: [],
      review_status: 'pending',
      created_at: new Date().toISOString(),
      updated_at: new Date().toISOString(),
    };

    dispatch(addExtractedFact(fact));
    onFactExtracted?.(fact);
  }, [dispatch, onFactExtracted]);

  const handleDocumentCompleted = useCallback((data: any) => {
    dispatch(updateDocument({
      id: data.document_id,
      status: 'completed',
      progress: 100,
    }));
  }, [dispatch]);

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

    console.log('[useDiscoverySocket] Subscribing to discovery events');

    // Use the handlers from the ref to avoid stale closures
    socket.on('discovery:started', (data) => {
      console.log('[useDiscoverySocket] Received discovery:started', data);
      handlersRef.current.handleDiscoveryStarted(data);
    });
    socket.on('discovery:document_found', (data) => {
      console.log('[useDiscoverySocket] Received discovery:document_found', data);
      handlersRef.current.handleDocumentFound(data);
    });
    socket.on('discovery:chunking', (data) => {
      console.log('[useDiscoverySocket] Received discovery:chunking', data);
      handlersRef.current.handleChunking(data);
    });
    socket.on('discovery:embedding', (data) => {
      console.log('[useDiscoverySocket] Received discovery:embedding', data);
      handlersRef.current.handleEmbedding(data);
    });
    socket.on('discovery:stored', (data) => {
      console.log('[useDiscoverySocket] Received discovery:stored', data);
      handlersRef.current.handleStored(data);
    });
    socket.on('discovery:fact_extracted', (data) => {
      console.log('[useDiscoverySocket] Received discovery:fact_extracted', data);
      handlersRef.current.handleFactExtracted(data);
    });
    socket.on('discovery:document_completed', (data) => {
      console.log('[useDiscoverySocket] Received discovery:document_completed', data);
      handlersRef.current.handleDocumentCompleted(data);
    });
    socket.on('discovery:completed', (data) => {
      console.log('[useDiscoverySocket] Received discovery:completed', data);
      handlersRef.current.handleCompleted(data);
    });
    socket.on('discovery:error', (data) => {
      console.log('[useDiscoverySocket] Received discovery:error', data);
      handlersRef.current.handleError(data);
    });
    socket.on('fact:updated', (data) => {
      console.log('[useDiscoverySocket] Received fact:updated', data);
      handlersRef.current.handleFactUpdated(data);
    });
    socket.on('fact:deleted', (data) => {
      console.log('[useDiscoverySocket] Received fact:deleted', data);
      handlersRef.current.handleFactDeleted(data);
    });

    // Note: Case subscription is now handled by CaseContext to prevent duplicates
    // Removed: socket.emit('subscribe_case', { case_id: caseId });

    subscribedRef.current = true;
  }, [socket, isConnected]); // Removed handler dependencies to prevent recreating

  const unsubscribeFromDiscoveryEvents = useCallback(() => {
    if (!socket || !subscribedRef.current) return;

    console.log('[useDiscoverySocket] Unsubscribing from discovery events');

    socket.off('discovery:started');
    socket.off('discovery:document_found');
    socket.off('discovery:chunking');
    socket.off('discovery:embedding');
    socket.off('discovery:stored');
    socket.off('discovery:fact_extracted');
    socket.off('discovery:document_completed');
    socket.off('discovery:completed');
    socket.off('discovery:error');
    socket.off('fact:updated');
    socket.off('fact:deleted');

    // Note: Case unsubscription is now handled by CaseContext
    // Removed: socket.emit('unsubscribe_case', { case_id: caseId });

    subscribedRef.current = false;
  }, [socket]); // Removed caseId dependency

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

  // Update handler refs when they change
  useEffect(() => {
    handlersRef.current = {
      handleDiscoveryStarted,
      handleDocumentFound,
      handleChunking,
      handleEmbedding,
      handleStored,
      handleFactExtracted,
      handleDocumentCompleted,
      handleCompleted,
      handleError,
      handleFactUpdated,
      handleFactDeleted,
    };
  });

  useEffect(() => {
    // Only subscribe/unsubscribe when socket connection changes
    if (isConnected && socket) {
      subscribeToDiscoveryEvents();
    }

    return () => {
      unsubscribeFromDiscoveryEvents();
      if (reconnectTimeoutRef.current) {
        clearTimeout(reconnectTimeoutRef.current);
      }
    };
  }, [isConnected, socket]); // Only depend on connection state, not the functions

  // Handle reconnection - no longer needed as WebSocketContext handles this
  // The subscription will be re-established when isConnected becomes true

  return {
    isConnected,
    updateFact,
    deleteFact,
    subscribeToDiscoveryEvents,
    unsubscribeFromDiscoveryEvents,
  };
};