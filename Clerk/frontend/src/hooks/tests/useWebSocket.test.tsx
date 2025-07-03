import { renderHook, act, waitFor } from '@testing-library/react';
import { ReactNode } from 'react';
import { WebSocketProvider } from '../../context/WebSocketContext';
import { useWebSocket } from '../useWebSocket';
import { io, Socket } from 'socket.io-client';
import '@testing-library/jest-dom';

// Mock socket.io-client
jest.mock('socket.io-client');

const mockSocket = {
  connected: false,
  on: jest.fn(),
  off: jest.fn(),
  emit: jest.fn(),
  connect: jest.fn(),
  disconnect: jest.fn()
} as unknown as Socket;

const wrapper = ({ children }: { children: ReactNode }) => (
  <WebSocketProvider>{children}</WebSocketProvider>
);

describe('useWebSocket Hook', () => {
  beforeEach(() => {
    jest.clearAllMocks();
    (io as jest.Mock).mockReturnValue(mockSocket);
  });

  it('should establish connection successfully', async () => {
    // Setup mock to simulate successful connection
    (mockSocket.on as jest.Mock).mockImplementation((event, callback) => {
      if (event === 'connect') {
        // Simulate connection after a short delay
        setTimeout(() => {
          mockSocket.connected = true;
          callback();
        }, 100);
      }
    });

    const { result } = renderHook(() => useWebSocket('test-case'), { wrapper });
    
    // Initially should be connecting
    expect(result.current.connecting).toBe(true);
    expect(result.current.connected).toBe(false);
    
    // Wait for connection
    await waitFor(() => {
      expect(result.current.connected).toBe(true);
      expect(result.current.connecting).toBe(false);
    });
    
    expect(result.current.subscribedCase).toBe('test-case');
  });

  it('should handle connection errors gracefully', async () => {
    const errorMessage = 'Connection failed';
    
    // Setup mock to simulate connection error
    (mockSocket.on as jest.Mock).mockImplementation((event, callback) => {
      if (event === 'connect_error') {
        callback(new Error(errorMessage));
      }
    });

    const { result } = renderHook(() => useWebSocket(), { wrapper });
    
    await waitFor(() => {
      expect(result.current.error).toBeTruthy();
      expect(result.current.connected).toBe(false);
    });
  });

  it('should cleanup on unmount', () => {
    const { unmount } = renderHook(() => useWebSocket(), { wrapper });
    
    unmount();
    
    expect(mockSocket.disconnect).toHaveBeenCalled();
  });

  it('should handle event subscriptions', () => {
    mockSocket.connected = true;
    
    const { result } = renderHook(() => useWebSocket(), { wrapper });
    const mockHandler = jest.fn();
    
    // Subscribe to an event
    act(() => {
      const unsubscribe = result.current.on('discovery:started', mockHandler);
      
      // Should register the handler
      expect(mockSocket.on).toHaveBeenCalledWith('discovery:started', expect.any(Function));
      
      // Unsubscribe
      unsubscribe();
      
      // Should remove the handler
      expect(mockSocket.off).toHaveBeenCalledWith('discovery:started', expect.any(Function));
    });
  });

  it('should emit events when connected', () => {
    mockSocket.connected = true;
    
    const { result } = renderHook(() => useWebSocket(), { wrapper });
    
    act(() => {
      result.current.emit('ping', undefined);
    });
    
    expect(mockSocket.emit).toHaveBeenCalledWith('ping', undefined);
  });

  it('should not emit events when disconnected', () => {
    mockSocket.connected = false;
    
    const { result } = renderHook(() => useWebSocket(), { wrapper });
    
    act(() => {
      result.current.emit('ping', undefined);
    });
    
    expect(mockSocket.emit).not.toHaveBeenCalled();
  });

  it('should handle case switching', async () => {
    mockSocket.connected = true;
    
    const { result, rerender } = renderHook(
      ({ caseId }) => useWebSocket(caseId),
      { 
        wrapper,
        initialProps: { caseId: 'case1' }
      }
    );
    
    // Should subscribe to initial case
    await waitFor(() => {
      expect(result.current.subscribedCase).toBe('case1');
    });
    
    // Switch to different case
    rerender({ caseId: 'case2' });
    
    await waitFor(() => {
      expect(result.current.subscribedCase).toBe('case2');
    });
  });
});