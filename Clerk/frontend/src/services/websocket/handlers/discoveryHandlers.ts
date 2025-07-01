import { Socket } from 'socket.io-client';
import { store } from '../../../store/store';
import { 
  processingStarted,
  documentFound,
  documentChunking,
  documentEmbedding,
  documentStored,
  processingCompleted,
  processingError,
  updateDocumentProgress
} from '../../../store/slices/discoverySlice';
import { eventReceived } from '../../../store/slices/websocketSlice';
import { DiscoveryWebSocketEvents } from '../../../types/discovery.types';

export function handleDiscoveryEvents(socket: Socket): void {
  // Processing started
  socket.on('discovery:started', (data: DiscoveryWebSocketEvents['discovery:started']) => {
    console.log('Discovery processing started:', data);
    store.dispatch(eventReceived('discovery:started'));
    store.dispatch(processingStarted({
      processingId: data.processingId,
      totalFiles: data.totalFiles,
      caseId: data.caseId
    }));
  });

  // Document found
  socket.on('discovery:document_found', (data: DiscoveryWebSocketEvents['discovery:document_found']) => {
    console.log('Document found:', data);
    store.dispatch(eventReceived('discovery:document_found'));
    store.dispatch(documentFound({
      id: data.documentId,
      title: data.title,
      type: data.type,
      pageCount: data.pageCount,
      batesRange: data.batesRange,
      confidence: data.confidence,
      status: 'pending',
      progress: 0
    }));
  });

  // Document chunking progress
  socket.on('discovery:chunking', (data: DiscoveryWebSocketEvents['discovery:chunking']) => {
    store.dispatch(eventReceived('discovery:chunking'));
    store.dispatch(documentChunking({
      documentId: data.documentId,
      progress: data.progress,
      chunksCreated: data.chunksCreated
    }));
    
    // Update document progress
    store.dispatch(updateDocumentProgress({
      documentId: data.documentId,
      progress: data.progress,
      status: 'processing'
    }));
  });

  // Document embedding progress
  socket.on('discovery:embedding', (data: DiscoveryWebSocketEvents['discovery:embedding']) => {
    store.dispatch(eventReceived('discovery:embedding'));
    store.dispatch(documentEmbedding({
      documentId: data.documentId,
      chunkId: data.chunkId,
      progress: data.progress
    }));
  });

  // Document stored
  socket.on('discovery:stored', (data: DiscoveryWebSocketEvents['discovery:stored']) => {
    store.dispatch(eventReceived('discovery:stored'));
    store.dispatch(documentStored({
      documentId: data.documentId,
      vectorsStored: data.vectorsStored
    }));
    
    // Mark document as completed
    store.dispatch(updateDocumentProgress({
      documentId: data.documentId,
      progress: 100,
      status: 'completed'
    }));
  });

  // Processing completed
  socket.on('discovery:completed', (data: DiscoveryWebSocketEvents['discovery:completed']) => {
    console.log('Discovery processing completed:', data);
    store.dispatch(eventReceived('discovery:completed'));
    store.dispatch(processingCompleted({
      processingId: data.processingId,
      summary: data.summary
    }));
  });

  // Processing error
  socket.on('discovery:error', (data: DiscoveryWebSocketEvents['discovery:error']) => {
    console.error('Discovery processing error:', data);
    store.dispatch(eventReceived('discovery:error'));
    store.dispatch(processingError({
      processingId: data.processingId,
      documentId: data.documentId,
      error: data.error,
      stage: data.stage
    }));
    
    // If document specific error, update its status
    if (data.documentId) {
      store.dispatch(updateDocumentProgress({
        documentId: data.documentId,
        progress: 0,
        status: 'error',
        error: data.error
      }));
    }
  });
}