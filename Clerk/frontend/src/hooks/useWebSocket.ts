import { useEffect, useCallback } from 'react';
import { useAppSelector } from './redux';
import { socketClient } from '../services/websocket/socketClient';
import { WebSocketEventName, WebSocketEvents } from '../types/websocket.types';

export const useWebSocket = () => {
  const { connected, connecting, error } = useAppSelector(state => state.websocket);

  // Connect to WebSocket
  const connect = useCallback((url?: string) => {
    socketClient.connect(url);
  }, []);

  // Disconnect from WebSocket
  const disconnect = useCallback(() => {
    socketClient.disconnect();
  }, []);

  // Emit an event
  const emit = useCallback(<T extends WebSocketEventName>(
    event: T,
    data: WebSocketEvents[T]
  ) => {
    socketClient.emit(event, data);
  }, []);

  // Subscribe to an event
  const on = useCallback(<T extends WebSocketEventName>(
    event: T,
    handler: (data: WebSocketEvents[T]) => void
  ) => {
    socketClient.on(event, handler);
    
    // Return cleanup function
    return () => {
      socketClient.off(event, handler);
    };
  }, []);

  // Connect on mount if not already connected
  useEffect(() => {
    if (!connected && !connecting) {
      connect();
    }

    // Cleanup on unmount
    return () => {
      // Don't disconnect on unmount to maintain connection across routes
      // disconnect();
    };
  }, []);

  return {
    connected,
    connecting,
    error,
    connect,
    disconnect,
    emit,
    on,
    isConnected: socketClient.isConnected(),
  };
};