import { useCallback, useEffect, useRef } from 'react';
import { useWebSocketContext } from '../context/WebSocketContext';
import { WebSocketEventName, WebSocketEvents } from '../types/websocket.types';

export function useWebSocket(caseId?: string) {
  const { socket, state, connect, disconnect, emit, subscribeToCase, unsubscribeFromCase } = useWebSocketContext();
  const handlersRef = useRef<Map<string, Function[]>>(new Map());

  // Subscribe to an event with proper cleanup
  const on = useCallback(<T extends WebSocketEventName>(
    event: T,
    handler: (data: WebSocketEvents[T]) => void
  ) => {
    if (!socket) {
      console.warn('Cannot subscribe to event: WebSocket not connected');
      return () => {};
    }

    // Store handler for cleanup
    const eventName = event as string;
    if (!handlersRef.current.has(eventName)) {
      handlersRef.current.set(eventName, []);
    }
    handlersRef.current.get(eventName)!.push(handler);

    // Add listener to socket
    socket.on(eventName, handler as any);

    // Return cleanup function
    return () => {
      if (socket) {
        socket.off(eventName, handler as any);
      }
      
      // Remove from stored handlers
      const handlers = handlersRef.current.get(eventName);
      if (handlers) {
        const index = handlers.indexOf(handler);
        if (index > -1) {
          handlers.splice(index, 1);
        }
      }
    };
  }, [socket]);

  // Typed emit function
  const typedEmit = useCallback(<T extends WebSocketEventName>(
    event: T,
    data: WebSocketEvents[T]
  ) => {
    emit(event as string, data);
  }, [emit]);

  // Handle case subscription
  useEffect(() => {
    if (caseId && state.connected && state.subscribedCase !== caseId) {
      subscribeToCase(caseId);
    }

    return () => {
      if (caseId && state.subscribedCase === caseId) {
        unsubscribeFromCase();
      }
    };
  }, [caseId, state.connected, state.subscribedCase, subscribeToCase, unsubscribeFromCase]);

  // Cleanup all handlers on unmount
  useEffect(() => {
    return () => {
      // Remove all event listeners
      handlersRef.current.forEach((handlers, event) => {
        handlers.forEach(handler => {
          if (socket) {
            socket.off(event, handler as any);
          }
        });
      });
      handlersRef.current.clear();
    };
  }, [socket]);

  return {
    connected: state.connected,
    connecting: state.connecting,
    error: state.error,
    subscribedCase: state.subscribedCase,
    socket,
    connect,
    disconnect,
    emit: typedEmit,
    on,
    subscribeToCase,
    unsubscribeFromCase
  };
}