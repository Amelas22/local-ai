import { useEffect, useCallback, useRef } from 'react';
import { useAppDispatch } from './redux';
import { useWebSocket } from './useWebSocket';
import { 
  processingStarted,
  addDocument,
  updateDocument,
  setProcessingSummary,
  setProcessingError,
  addExtractedFact,
  updateExtractedFact,
  removeExtractedFact,
  setCurrentStage,
} from '../store/slices/discoverySlice';
import { showNotification } from '../store/slices/uiSlice';
import { 
  ProcessingStage,
  ExtractedFactWithSource 
} from '../types/discovery.types';

interface UseEnhancedDiscoverySocketOptions {
  processingId?: string;
  caseId?: string;
  onFactExtracted?: (fact: ExtractedFactWithSource) => void;
  onProcessingComplete?: () => void;
  onError?: (error: string) => void;
}

interface DocumentProcessingStatus {
  [documentId: string]: {
    stage: ProcessingStage;
    progress: number;
  };
}

export const useEnhancedDiscoverySocket = (options: UseEnhancedDiscoverySocketOptions = {}) => {
  const { processingId, caseId, onFactExtracted, onProcessingComplete, onError } = options;
  const dispatch = useAppDispatch();
  const { socket, isConnected } = useWebSocket();
  const subscribedRef = useRef(false);
  const documentStatusRef = useRef<DocumentProcessingStatus>({});
  const subscriptionTimeoutRef = useRef<NodeJS.Timeout | null>(null);
  const lastSubscribedCaseRef = useRef<string | null>(null);
  const lastProcessingIdRef = useRef<string | null>(null);
  
  // Store event handlers in refs to prevent recreating them
  const eventHandlersRef = useRef<any>({});

  // Enhanced event handlers
  const handleDiscoveryStarted = useCallback((data: any) => {
    console.log('🚀 [Discovery] Started event received:', data);
    if (processingId && data.processing_id !== processingId) return;
    
    dispatch(processingStarted({
      processingId: data.processing_id,
      totalFiles: data.total_files || 0,
      caseId: data.case_name || caseId || '',
    }));
    
    // Clear document status tracking
    documentStatusRef.current = {};
  }, [dispatch, processingId, caseId]);

  const handleDocumentFound = useCallback((data: any) => {
    console.log('📄 [Discovery] Document Found event received:', data);
    console.log('  - Looking for processing_id:', processingId);
    console.log('  - Event processing_id:', data.processing_id);
    console.log('  - Document ID:', data.document_id);
    console.log('  - Title:', data.title);
    console.log('  - Type:', data.type);
    console.log('  - Page count:', data.page_count);
    console.log('  - Confidence:', data.confidence);
    
    // Check if this event is for our processing session
    if (processingId && data.processing_id !== processingId) {
      console.log('  - Ignoring event for different processing_id');
      return;
    }
    
    dispatch(addDocument({
      id: data.document_id,
      title: data.title,
      type: data.type,
      batesRange: data.bates_range,
      pageCount: data.page_count || 0,
      confidence: data.confidence,
      status: 'pending',
      progress: 0,
    }));
    
    // Initialize document status
    documentStatusRef.current[data.document_id] = {
      stage: ProcessingStage.DISCOVERING_DOCUMENTS,
      progress: 0,
    };
  }, [dispatch, processingId]);

  const handleDocumentProcessing = useCallback((data: any) => {
    const { document_id, stage, status } = data;
    
    // Map backend stage names to frontend ProcessingStage enum
    const stageMap: { [key: string]: ProcessingStage } = {
      'chunking': ProcessingStage.CHUNKING_DOCUMENTS,
      'embedding': ProcessingStage.GENERATING_EMBEDDINGS,
      'storing': ProcessingStage.STORING_VECTORS,
      'extracting_facts': ProcessingStage.EXTRACTING_FACTS,
    };
    
    const mappedStage = stageMap[stage] || ProcessingStage.DISCOVERING_DOCUMENTS;
    
    // Update document status
    documentStatusRef.current[document_id] = {
      stage: mappedStage,
      progress: data.progress || 0,
    };
    
    // Update document in store
    dispatch(updateDocument({
      id: document_id,
      status: status === 'started' ? 'processing' : status,
      progress: data.progress || 0,
    }));
    
    // Update global stage based on most advanced document
    const stages = Object.values(documentStatusRef.current).map(s => s.stage);
    const mostAdvancedStage = stages.reduce((prev, curr) => {
      const stageOrder = [
        ProcessingStage.DISCOVERING_DOCUMENTS,
        ProcessingStage.CLASSIFYING_DOCUMENTS,
        ProcessingStage.CHUNKING_DOCUMENTS,
        ProcessingStage.GENERATING_EMBEDDINGS,
        ProcessingStage.STORING_VECTORS,
        ProcessingStage.EXTRACTING_FACTS,
      ];
      const prevIndex = stageOrder.indexOf(prev);
      const currIndex = stageOrder.indexOf(curr);
      return currIndex > prevIndex ? curr : prev;
    }, ProcessingStage.DISCOVERING_DOCUMENTS);
    
    dispatch(setCurrentStage(mostAdvancedStage));
  }, [dispatch]);

  const handleChunking = useCallback((data: any) => {
    // Check if this event is for our processing session
    if (processingId && data.processing_id !== processingId) {
      return;
    }
    
    dispatch(updateDocument({
      id: data.document_id,
      status: 'processing',
      progress: 50, // Chunking is roughly 50% through document processing
      chunks: data.chunks_created,
    }));
    
    handleDocumentProcessing({
      document_id: data.document_id,
      stage: 'chunking',
      status: data.status,
      progress: 50,
    });
  }, [dispatch, handleDocumentProcessing, processingId]);

  const handleEmbedding = useCallback((data: any) => {
    const progress = 60 + (data.progress || 0) * 0.2; // 60-80% for embeddings
    
    dispatch(updateDocument({
      id: data.document_id,
      progress,
    }));
    
    handleDocumentProcessing({
      document_id: data.document_id,
      stage: 'embedding',
      status: 'processing',
      progress,
    });
  }, [dispatch, handleDocumentProcessing]);

  const handleFactExtracted = useCallback((data: any) => {
    const fact: ExtractedFactWithSource = {
      id: data.fact.fact_id || `fact_${Date.now()}_${Math.random()}`,
      content: data.fact.text || data.fact.content,
      category: data.fact.category,
      confidence: data.fact.confidence,
      source: {
        doc_id: data.document_id,
        doc_title: data.fact.source_metadata?.document_title || '',
        page: data.fact.source_metadata?.page || 0,
        bbox: data.fact.source_metadata?.bbox || [],
        text_snippet: data.fact.source_metadata?.text_snippet || '',
      },
      entities: data.fact.entities || [],
      keywords: data.fact.keywords || [],
      dates: data.fact.dates || [],
      is_edited: false,
      edit_history: [],
      review_status: 'pending',
      created_at: new Date().toISOString(),
      updated_at: new Date().toISOString(),
    };

    dispatch(addExtractedFact(fact));
    onFactExtracted?.(fact);
    
    // Update document processing stage
    handleDocumentProcessing({
      document_id: data.document_id,
      stage: 'extracting_facts',
      status: 'processing',
      progress: 90,
    });
  }, [dispatch, onFactExtracted, handleDocumentProcessing]);

  const handleDocumentCompleted = useCallback((data: any) => {
    dispatch(updateDocument({
      id: data.document_id,
      status: 'completed',
      progress: 100,
      vectors: data.vectors_stored,
    }));
    
    // Remove from tracking
    delete documentStatusRef.current[data.document_id];
  }, [dispatch]);

  const handleCompleted = useCallback((data: any) => {
    console.log('✅ [Discovery] Completed event received:', data);
    if (processingId && data.processing_id !== processingId) return;
    
    const summary = {
      totalDocuments: data.total_documents_found || 0,
      processedDocuments: data.documents_processed || 0,
      totalChunks: data.chunks_created || 0,
      totalVectors: data.vectors_stored || 0,
      totalErrors: data.errors?.length || 0,
      averageConfidence: data.average_confidence || 0,
      totalFacts: data.facts_extracted || 0,
      processingTime: data.processing_time || 0,
    };
    
    console.log('📊 [Discovery] Summary:', summary);
    
    dispatch(setProcessingSummary(summary));
    dispatch(setCurrentStage(ProcessingStage.COMPLETING));
    
    dispatch(showNotification({
      message: `Discovery processing completed. Found ${summary.totalDocuments} documents, extracted ${summary.totalFacts} facts.`,
      severity: 'success',
    }));
    
    onProcessingComplete?.();
    
    // Clear all document tracking
    documentStatusRef.current = {};
  }, [dispatch, processingId, onProcessingComplete]);

  const handleError = useCallback((data: any) => {
    if (processingId && data.processing_id !== processingId) return;
    
    dispatch(setProcessingError({
      error: data.error,
      documentId: data.document_id,
    }));
    
    if (data.document_id) {
      dispatch(updateDocument({
        id: data.document_id,
        status: 'error',
        error: data.error,
      }));
      
      // Remove from tracking
      delete documentStatusRef.current[data.document_id];
    }
    
    dispatch(showNotification({
      message: `Discovery error: ${data.error}`,
      severity: 'error',
    }));
    
    onError?.(data.error);
  }, [dispatch, processingId, onError]);

  const handleFactUpdated = useCallback((data: any) => {
    dispatch(updateExtractedFact({
      id: data.fact_id,
      content: data.content,
      is_edited: true,
    }));
  }, [dispatch]);

  const handleFactDeleted = useCallback((data: any) => {
    dispatch(removeExtractedFact(data.fact_id));
  }, [dispatch]);

  const subscribeToDiscoveryEvents = useCallback(() => {
    if (!socket || !isConnected) return;
    
    // Check if we're already subscribed with the same case/processing ID
    if (subscribedRef.current && 
        lastSubscribedCaseRef.current === caseId && 
        lastProcessingIdRef.current === processingId) {
      console.log('🔌 [Discovery] Already subscribed with same parameters, skipping');
      return;
    }

    // Clear any pending subscription attempts
    if (subscriptionTimeoutRef.current) {
      clearTimeout(subscriptionTimeoutRef.current);
    }

    // Debounce subscription to prevent rapid fire
    subscriptionTimeoutRef.current = setTimeout(() => {
      console.log('🔌 [Discovery] Subscribing to WebSocket events...');
      console.log('  - Socket connected:', isConnected);
      console.log('  - Case ID:', caseId);
      console.log('  - Processing ID:', processingId);
      console.log('  - Previously subscribed:', subscribedRef.current);

      // Unsubscribe from previous case if different
      if (subscribedRef.current && lastSubscribedCaseRef.current && lastSubscribedCaseRef.current !== caseId) {
        console.log('📡 [Discovery] Unsubscribing from previous case:', lastSubscribedCaseRef.current);
        socket.emit('unsubscribe_case', { case_id: lastSubscribedCaseRef.current });
      }

      // Store handler references to ensure we can properly unsubscribe
      eventHandlersRef.current = {
        handleDiscoveryStarted,
        handleDocumentFound,
        handleDocumentProcessing,
        handleChunking,
        handleEmbedding,
        handleFactExtracted,
        handleDocumentCompleted,
        handleCompleted,
        handleError,
        handleFactUpdated,
        handleFactDeleted
      };
      
      // Discovery processing events
      socket.on('discovery:started', eventHandlersRef.current.handleDiscoveryStarted);
      socket.on('discovery:document_found', eventHandlersRef.current.handleDocumentFound);
      socket.on('discovery:document_processing', eventHandlersRef.current.handleDocumentProcessing);
      socket.on('discovery:chunking', eventHandlersRef.current.handleChunking);
      socket.on('discovery:embedding', eventHandlersRef.current.handleEmbedding);
      socket.on('discovery:fact_extracted', eventHandlersRef.current.handleFactExtracted);
      socket.on('discovery:document_completed', eventHandlersRef.current.handleDocumentCompleted);
      socket.on('discovery:completed', eventHandlersRef.current.handleCompleted);
      socket.on('discovery:error', eventHandlersRef.current.handleError);
      
      // Fact management events
      socket.on('fact:updated', eventHandlersRef.current.handleFactUpdated);
      socket.on('fact:deleted', eventHandlersRef.current.handleFactDeleted);

      if (caseId) {
        console.log('📡 [Discovery] Subscribing to case:', caseId);
        socket.emit('subscribe_case', { case_id: caseId });
      }

      subscribedRef.current = true;
      lastSubscribedCaseRef.current = caseId || null;
      lastProcessingIdRef.current = processingId || null;
      console.log('✅ [Discovery] WebSocket event subscription complete');
    }, 100); // Small delay to prevent rapid subscription
  }, [socket, isConnected, caseId, processingId]); // Reduced dependencies to prevent circular updates

  const unsubscribeFromDiscoveryEvents = useCallback(() => {
    if (!socket || !subscribedRef.current) return;
    
    console.log('🔌 [Discovery] Unsubscribing from WebSocket events...');

    // Remove all event listeners using the stored handler references
    if (eventHandlersRef.current) {
      socket.off('discovery:started', eventHandlersRef.current.handleDiscoveryStarted);
      socket.off('discovery:document_found', eventHandlersRef.current.handleDocumentFound);
      socket.off('discovery:document_processing', eventHandlersRef.current.handleDocumentProcessing);
      socket.off('discovery:chunking', eventHandlersRef.current.handleChunking);
      socket.off('discovery:embedding', eventHandlersRef.current.handleEmbedding);
      socket.off('discovery:fact_extracted', eventHandlersRef.current.handleFactExtracted);
      socket.off('discovery:document_completed', eventHandlersRef.current.handleDocumentCompleted);
      socket.off('discovery:completed', eventHandlersRef.current.handleCompleted);
      socket.off('discovery:error', eventHandlersRef.current.handleError);
      socket.off('fact:updated', eventHandlersRef.current.handleFactUpdated);
      socket.off('fact:deleted', eventHandlersRef.current.handleFactDeleted);
    }

    if (lastSubscribedCaseRef.current) {
      console.log('📡 [Discovery] Unsubscribing from case:', lastSubscribedCaseRef.current);
      socket.emit('unsubscribe_case', { case_id: lastSubscribedCaseRef.current });
    }

    subscribedRef.current = false;
    documentStatusRef.current = {};
    eventHandlersRef.current = {};
  }, [socket]);

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

  // Add debug logging for all events
  useEffect(() => {
    if (!socket) return;
    
    // Log ALL incoming events for debugging
    const logAllEvents = (eventName: string, ...args: any[]) => {
      console.log(`🔵 [WebSocket] Event received: ${eventName}`, {
        timestamp: new Date().toISOString(),
        args: args,
        currentProcessingId: processingId,
        isSubscribed: subscribedRef.current
      });
    };
    
    socket.onAny(logAllEvents);
    
    return () => {
      socket.offAny(logAllEvents);
    };
  }, [socket, processingId]);

  // Main subscription effect with better dependency management
  useEffect(() => {
    console.log('🔄 [Discovery] Effect triggered:', {
      socket: !!socket,
      isConnected,
      caseId,
      processingId,
      subscribedRef: subscribedRef.current,
      lastCaseId: lastSubscribedCaseRef.current,
      lastProcessingId: lastProcessingIdRef.current
    });

    subscribeToDiscoveryEvents();

    return () => {
      console.log('🔄 [Discovery] Effect cleanup');
      // Clear timeout on cleanup
      if (subscriptionTimeoutRef.current) {
        clearTimeout(subscriptionTimeoutRef.current);
      }
      unsubscribeFromDiscoveryEvents();
    };
  }, [socket, isConnected, caseId, processingId]); // Simplified dependencies

  return {
    isConnected,
    updateFact,
    deleteFact,
    subscribeToDiscoveryEvents,
    unsubscribeFromDiscoveryEvents,
  };
};