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
    console.log('  - Document ID:', data.document_id);
    console.log('  - Title:', data.title);
    console.log('  - Type:', data.type);
    console.log('  - Pages:', data.pages);
    console.log('  - Confidence:', data.confidence);
    
    dispatch(addDocument({
      id: data.document_id,
      title: data.title,
      type: data.type,
      batesRange: data.bates_range,
      pageCount: parseInt(data.pages?.split('-')[1] || '0'),
      confidence: data.confidence,
      status: 'pending',
      progress: 0,
    }));
    
    // Initialize document status
    documentStatusRef.current[data.document_id] = {
      stage: ProcessingStage.DISCOVERING_DOCUMENTS,
      progress: 0,
    };
  }, [dispatch]);

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
    dispatch(updateDocument({
      id: data.document_id,
      status: 'processing',
      progress: 50, // Chunking is roughly 50% through document processing
      chunks: data.total_chunks,
    }));
    
    handleDocumentProcessing({
      document_id: data.document_id,
      stage: 'chunking',
      status: data.status,
      progress: 50,
    });
  }, [dispatch, handleDocumentProcessing]);

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
    if (!socket || !isConnected || subscribedRef.current) return;

    console.log('🔌 [Discovery] Subscribing to WebSocket events...');
    console.log('  - Socket connected:', isConnected);
    console.log('  - Case ID:', caseId);
    console.log('  - Processing ID:', processingId);

    // Discovery processing events
    socket.on('discovery:started', handleDiscoveryStarted);
    socket.on('discovery:document_found', handleDocumentFound);
    socket.on('discovery:document_processing', handleDocumentProcessing);
    socket.on('discovery:chunking', handleChunking);
    socket.on('discovery:embedding', handleEmbedding);
    socket.on('discovery:fact_extracted', handleFactExtracted);
    socket.on('discovery:document_completed', handleDocumentCompleted);
    socket.on('discovery:completed', handleCompleted);
    socket.on('discovery:error', handleError);
    
    // Fact management events
    socket.on('fact:updated', handleFactUpdated);
    socket.on('fact:deleted', handleFactDeleted);

    if (caseId) {
      console.log('📡 [Discovery] Subscribing to case:', caseId);
      socket.emit('subscribe_case', { case_id: caseId });
    }

    subscribedRef.current = true;
    console.log('✅ [Discovery] WebSocket event subscription complete');
  }, [
    socket,
    isConnected,
    caseId,
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
    handleFactDeleted,
  ]);

  const unsubscribeFromDiscoveryEvents = useCallback(() => {
    if (!socket || !subscribedRef.current) return;

    socket.off('discovery:started');
    socket.off('discovery:document_found');
    socket.off('discovery:document_processing');
    socket.off('discovery:chunking');
    socket.off('discovery:embedding');
    socket.off('discovery:fact_extracted');
    socket.off('discovery:document_completed');
    socket.off('discovery:completed');
    socket.off('discovery:error');
    socket.off('fact:updated');
    socket.off('fact:deleted');

    if (caseId) {
      socket.emit('unsubscribe_case', { case_id: caseId });
    }

    subscribedRef.current = false;
    documentStatusRef.current = {};
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
    };
  }, [subscribeToDiscoveryEvents, unsubscribeFromDiscoveryEvents]);

  return {
    isConnected,
    updateFact,
    deleteFact,
    subscribeToDiscoveryEvents,
    unsubscribeFromDiscoveryEvents,
  };
};