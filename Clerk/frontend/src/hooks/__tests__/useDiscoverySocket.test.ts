import { renderHook, act } from '@testing-library/react';
import { Provider } from 'react-redux';
import { configureStore } from '@reduxjs/toolkit';
import React from 'react';
import { useDiscoverySocket } from '../useDiscoverySocket';
import discoverySlice from '../../store/slices/discoverySlice';
import uiSlice from '../../store/slices/uiSlice';
import { Socket } from 'socket.io-client';

// Mock socket.io
const mockSocket = {
  on: jest.fn(),
  off: jest.fn(),
  emit: jest.fn(),
  connected: true,
} as unknown as Socket;

// Mock useWebSocket hook
jest.mock('../useWebSocket', () => ({
  useWebSocket: () => ({
    socket: mockSocket,
    isConnected: true,
  }),
}));

const createMockStore = () =>
  configureStore({
    reducer: {
      discovery: discoverySlice.reducer,
      ui: uiSlice.reducer,
    },
  });

const wrapper: React.FC<{ children: React.ReactNode }> = ({ children }) => (
  <Provider store={createMockStore()}>{children}</Provider>
);

describe('useDiscoverySocket', () => {
  beforeEach(() => {
    jest.clearAllMocks();
  });

  it('subscribes to discovery events on mount', () => {
    const { result } = renderHook(
      () => useDiscoverySocket({ processingId: 'test-123', caseId: 'case-456' }),
      { wrapper }
    );

    expect(mockSocket.on).toHaveBeenCalledWith('discovery:started', expect.any(Function));
    expect(mockSocket.on).toHaveBeenCalledWith('discovery:document_found', expect.any(Function));
    expect(mockSocket.on).toHaveBeenCalledWith('discovery:chunking', expect.any(Function));
    expect(mockSocket.on).toHaveBeenCalledWith('discovery:embedding', expect.any(Function));
    expect(mockSocket.on).toHaveBeenCalledWith('discovery:stored', expect.any(Function));
    expect(mockSocket.on).toHaveBeenCalledWith('discovery:fact_extracted', expect.any(Function));
    expect(mockSocket.on).toHaveBeenCalledWith('discovery:completed', expect.any(Function));
    expect(mockSocket.on).toHaveBeenCalledWith('discovery:error', expect.any(Function));
    expect(mockSocket.on).toHaveBeenCalledWith('fact:updated', expect.any(Function));
    expect(mockSocket.on).toHaveBeenCalledWith('fact:deleted', expect.any(Function));
  });

  it('subscribes to case room when caseId provided', () => {
    renderHook(
      () => useDiscoverySocket({ caseId: 'case-456' }),
      { wrapper }
    );

    expect(mockSocket.emit).toHaveBeenCalledWith('subscribe_case', { case_id: 'case-456' });
  });

  it('unsubscribes from events on unmount', () => {
    const { unmount } = renderHook(
      () => useDiscoverySocket({ processingId: 'test-123', caseId: 'case-456' }),
      { wrapper }
    );

    unmount();

    expect(mockSocket.off).toHaveBeenCalledWith('discovery:started');
    expect(mockSocket.off).toHaveBeenCalledWith('discovery:document_found');
    expect(mockSocket.off).toHaveBeenCalledWith('discovery:chunking');
    expect(mockSocket.off).toHaveBeenCalledWith('discovery:embedding');
    expect(mockSocket.off).toHaveBeenCalledWith('discovery:stored');
    expect(mockSocket.off).toHaveBeenCalledWith('discovery:fact_extracted');
    expect(mockSocket.off).toHaveBeenCalledWith('discovery:completed');
    expect(mockSocket.off).toHaveBeenCalledWith('discovery:error');
    expect(mockSocket.off).toHaveBeenCalledWith('fact:updated');
    expect(mockSocket.off).toHaveBeenCalledWith('fact:deleted');
    expect(mockSocket.emit).toHaveBeenCalledWith('unsubscribe_case', { case_id: 'case-456' });
  });

  it('handles discovery:started event', () => {
    const store = createMockStore();
    const { result } = renderHook(
      () => useDiscoverySocket({ processingId: 'test-123' }),
      { 
        wrapper: ({ children }: { children: React.ReactNode }) => <Provider store={store}>{children}</Provider>,
      }
    );

    // Get the handler that was registered
    const handler = (mockSocket.on as jest.Mock).mock.calls.find(
      call => call[0] === 'discovery:started'
    )[1];

    // Simulate event
    act(() => {
      handler({
        processingId: 'test-123',
        caseId: 'case-456',
        totalFiles: 5,
      });
    });

    const state = store.getState().discovery;
    expect(state.currentProcessingId).toBe('test-123');
  });

  it('handles discovery:fact_extracted event and calls callback', () => {
    const onFactExtracted = jest.fn();
    const store = createMockStore();
    
    renderHook(
      () => useDiscoverySocket({ onFactExtracted }),
      { 
        wrapper: ({ children }: { children: React.ReactNode }) => <Provider store={store}>{children}</Provider>,
      }
    );

    const handler = (mockSocket.on as jest.Mock).mock.calls.find(
      call => call[0] === 'discovery:fact_extracted'
    )[1];

    act(() => {
      handler({
        factId: 'fact-123',
        documentId: 'doc-456',
        content: 'Test fact content',
        category: 'test',
        confidence: 0.95,
      });
    });

    expect(onFactExtracted).toHaveBeenCalledWith(
      expect.objectContaining({
        id: 'fact-123',
        content: 'Test fact content',
        category: 'test',
        confidence: 0.95,
      })
    );
  });

  it('handles discovery:completed event and calls callback', () => {
    const onProcessingComplete = jest.fn();
    const store = createMockStore();
    
    renderHook(
      () => useDiscoverySocket({ processingId: 'test-123', onProcessingComplete }),
      { 
        wrapper: ({ children }: { children: React.ReactNode }) => <Provider store={store}>{children}</Provider>,
      }
    );

    const handler = (mockSocket.on as jest.Mock).mock.calls.find(
      call => call[0] === 'discovery:completed'
    )[1];

    act(() => {
      handler({
        processingId: 'test-123',
        summary: {
          totalDocuments: 10,
          processedDocuments: 10,
          totalChunks: 50,
          totalVectors: 50,
          totalErrors: 0,
          averageConfidence: 0.85,
          processingTime: 120,
        },
      });
    });

    expect(onProcessingComplete).toHaveBeenCalled();
  });

  it('handles discovery:error event and calls callback', () => {
    const onError = jest.fn();
    const store = createMockStore();
    
    renderHook(
      () => useDiscoverySocket({ processingId: 'test-123', onError }),
      { 
        wrapper: ({ children }: { children: React.ReactNode }) => <Provider store={store}>{children}</Provider>,
      }
    );

    const handler = (mockSocket.on as jest.Mock).mock.calls.find(
      call => call[0] === 'discovery:error'
    )[1];

    act(() => {
      handler({
        processingId: 'test-123',
        error: 'Processing failed',
        stage: 'processing',
      });
    });

    expect(onError).toHaveBeenCalledWith('Processing failed');
  });

  describe('Fact operations', () => {
    it('updates fact via socket', async () => {
      mockSocket.emit = jest.fn((event, data, callback) => {
        callback({ success: true });
      }) as any;

      const { result } = renderHook(
        () => useDiscoverySocket({ caseId: 'case-456' }),
        { wrapper }
      );

      await act(async () => {
        await result.current.updateFact('fact-123', 'Updated content', 'Fixing typo');
      });

      expect(mockSocket.emit).toHaveBeenCalledWith(
        'fact:update',
        {
          case_id: 'case-456',
          fact_id: 'fact-123',
          content: 'Updated content',
          reason: 'Fixing typo',
        },
        expect.any(Function)
      );
    });

    it('deletes fact via socket', async () => {
      mockSocket.emit = jest.fn((event, data, callback) => {
        callback({ success: true });
      }) as any;

      const { result } = renderHook(
        () => useDiscoverySocket({ caseId: 'case-456' }),
        { wrapper }
      );

      await act(async () => {
        await result.current.deleteFact('fact-123');
      });

      expect(mockSocket.emit).toHaveBeenCalledWith(
        'fact:delete',
        {
          case_id: 'case-456',
          fact_id: 'fact-123',
        },
        expect.any(Function)
      );
    });

    it('throws error when socket not connected', async () => {
      jest.resetModules();
      jest.doMock('../useWebSocket', () => ({
        useWebSocket: () => ({
          socket: mockSocket,
          isConnected: false,
        }),
      }));

      const { useDiscoverySocket: useDiscoverySocketDisconnected } = require('../useDiscoverySocket');
      
      const { result } = renderHook(
        () => useDiscoverySocketDisconnected({ caseId: 'case-456' }),
        { wrapper }
      );

      await expect(
        result.current.updateFact('fact-123', 'Updated content')
      ).rejects.toThrow('Socket not connected or case not selected');
    });
  });

  it('handles reconnection after disconnect', () => {
    const store = createMockStore();
    let isConnected = true;
    
    jest.resetModules();
    jest.doMock('../useWebSocket', () => ({
      useWebSocket: () => ({
        socket: mockSocket,
        isConnected,
      }),
    }));

    const { useDiscoverySocket: useDiscoverySocketReconnect } = require('../useDiscoverySocket');
    
    const { rerender } = renderHook(
      () => useDiscoverySocketReconnect({ caseId: 'case-456' }),
      { 
        wrapper: ({ children }: { children: React.ReactNode }) => <Provider store={store}>{children}</Provider>,
      }
    );

    // Simulate disconnect
    isConnected = false;
    rerender();

    // Clear previous calls
    jest.clearAllMocks();

    // Simulate reconnect after timeout
    jest.useFakeTimers();
    isConnected = true;
    
    act(() => {
      jest.advanceTimersByTime(1100);
      rerender();
    });

    // Should resubscribe to events
    expect(mockSocket.on).toHaveBeenCalledWith('discovery:started', expect.any(Function));
    
    jest.useRealTimers();
  });
});