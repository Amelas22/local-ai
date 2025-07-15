import { createContext, useContext, useState, useEffect, useRef, ReactElement, ReactNode } from 'react';
import { io, Socket } from 'socket.io-client';

// WebSocket connection state interface
interface WebSocketState {
  connected: boolean;
  connecting: boolean;
  error: string | null;
  reconnectAttempts: number;
  subscribedCase: string | null;
}

// WebSocket context value interface
interface WebSocketContextValue {
  socket: Socket | null;
  state: WebSocketState;
  connect: (caseId?: string) => void;
  disconnect: () => void;
  emit: (event: string, data: any) => void;
  subscribeToCase: (caseId: string) => void;
  unsubscribeFromCase: () => void;
}

// Create context with undefined default
export const WebSocketContext = createContext<WebSocketContextValue | undefined>(undefined);

// Provider props
interface WebSocketProviderProps {
  children: ReactNode;
  wsUrl?: string;
}

export function WebSocketProvider({ children, wsUrl }: WebSocketProviderProps): ReactElement {
  const [state, setState] = useState<WebSocketState>({
    connected: false,
    connecting: false,
    error: null,
    reconnectAttempts: 0,
    subscribedCase: null
  });

  const socketRef = useRef<Socket | null>(null);
  const reconnectTimerRef = useRef<NodeJS.Timeout | null>(null);
  const maxReconnectAttempts = 5;
  const baseReconnectDelay = 1000;

  const connect = (caseId?: string) => {
    // Prevent multiple connection attempts
    if (socketRef.current?.connected || state.connecting) {
      console.log('WebSocket already connected or connecting');
      return;
    }

    setState(prev => ({ ...prev, connecting: true, error: null }));

    // Simple URL construction following KISS principle
    // Use relative URL when VITE_WS_URL is empty to work with the dev proxy
    const baseUrl = wsUrl || import.meta.env.VITE_WS_URL || '';
    const url = baseUrl || window.location.origin;
    
    console.log('Connecting to WebSocket:', url);
    console.log('WebSocket path:', '/ws/socket.io/');

    // Create socket instance with proper configuration
    const socket = io(url, {
      path: '/ws/socket.io/',
      transports: ['websocket', 'polling'],
      timeout: 20000,
      forceNew: true,
      reconnection: false // We'll handle reconnection manually
    });

    socketRef.current = socket;

    // Connection event handlers
    socket.on('connect', () => {
      console.log('WebSocket connected');
      setState(prev => ({ 
        ...prev, 
        connected: true, 
        connecting: false, 
        error: null,
        reconnectAttempts: 0 
      }));
      
      // Subscribe to case if provided
      if (caseId) {
        subscribeToCase(caseId);
      }
    });

    socket.on('connect_error', (error) => {
      console.error('WebSocket connection error:', error.message);
      setState(prev => ({ 
        ...prev, 
        connected: false, 
        connecting: false, 
        error: error.message,
        reconnectAttempts: prev.reconnectAttempts + 1 
      }));
      
      // Attempt reconnection with exponential backoff
      attemptReconnect();
    });

    socket.on('disconnect', (reason) => {
      console.log('WebSocket disconnected:', reason);
      setState(prev => ({ 
        ...prev, 
        connected: false, 
        subscribedCase: null 
      }));
      
      // Auto-reconnect unless manually disconnected
      if (reason !== 'io client disconnect') {
        attemptReconnect();
      }
    });

    // Server confirmation event
    socket.on('connected', (data) => {
      console.log('Received connected event from server:', data);
    });
  };

  const disconnect = () => {
    // Clear any pending reconnect timer
    if (reconnectTimerRef.current) {
      clearTimeout(reconnectTimerRef.current);
      reconnectTimerRef.current = null;
    }
    
    if (socketRef.current) {
      socketRef.current.disconnect();
      socketRef.current = null;
    }
    
    setState({
      connected: false,
      connecting: false,
      error: null,
      reconnectAttempts: 0,
      subscribedCase: null
    });
  };

  const attemptReconnect = () => {
    // Use setState callback to ensure we have fresh state
    setState(prev => {
      if (prev.reconnectAttempts >= maxReconnectAttempts) {
        console.error('Max reconnection attempts reached');
        return { ...prev, error: 'Max reconnection attempts reached' };
      }

      // Clear any existing reconnect timer
      if (reconnectTimerRef.current) {
        clearTimeout(reconnectTimerRef.current);
      }

      // Calculate delay with exponential backoff and jitter
      const baseDelay = baseReconnectDelay * Math.pow(2, prev.reconnectAttempts);
      const jitter = Math.random() * 1000;
      const delay = Math.min(baseDelay + jitter, 30000);
      
      console.log(`Attempting to reconnect in ${delay}ms (attempt ${prev.reconnectAttempts + 1}/${maxReconnectAttempts})...`);
      
      reconnectTimerRef.current = setTimeout(() => {
        connect(prev.subscribedCase || undefined);
      }, delay);

      return prev; // Return unchanged state since we're just scheduling
    });
  };

  const emit = (event: string, data: any) => {
    if (!socketRef.current?.connected) {
      console.warn('Cannot emit event: WebSocket not connected');
      return;
    }
    socketRef.current.emit(event, data);
  };

  const subscribeToCase = (caseId: string) => {
    if (!socketRef.current?.connected) {
      console.warn('Cannot subscribe to case: WebSocket not connected');
      return;
    }
    
    // Don't re-subscribe if already subscribed to this case
    if (state.subscribedCase === caseId) {
      console.log(`Already subscribed to case: ${caseId}`);
      return;
    }
    
    console.log(`Subscribing to case: ${caseId} (previous: ${state.subscribedCase || 'none'})`);
    
    // Unsubscribe from previous case if any
    if (state.subscribedCase) {
      console.log(`Unsubscribing from previous case: ${state.subscribedCase}`);
      emit('unsubscribe_case', { case_id: state.subscribedCase });
    }
    
    emit('subscribe_case', { case_id: caseId });
    setState(prev => ({ ...prev, subscribedCase: caseId }));
    console.log(`Successfully subscribed to case: ${caseId}`);
  };

  const unsubscribeFromCase = () => {
    if (state.subscribedCase) {
      emit('unsubscribe_case', { case_id: state.subscribedCase });
      setState(prev => ({ ...prev, subscribedCase: null }));
      console.log('Unsubscribed from case');
    }
  };

  // Connect on mount
  useEffect(() => {
    connect();
    
    // Cleanup on unmount
    return () => {
      disconnect();
    };
  }, []); // Empty dependency array - only run on mount/unmount

  // Note: Re-subscription on reconnection is handled by CaseContext
  // which watches for connection state changes

  const contextValue: WebSocketContextValue = {
    socket: socketRef.current,
    state,
    connect,
    disconnect,
    emit,
    subscribeToCase,
    unsubscribeFromCase
  };

  return (
    <WebSocketContext.Provider value={contextValue}>
      {children}
    </WebSocketContext.Provider>
  );
}

// Custom hook to use WebSocket context
export function useWebSocketContext(): WebSocketContextValue {
  const context = useContext(WebSocketContext);
  if (!context) {
    throw new Error('useWebSocketContext must be used within a WebSocketProvider');
  }
  return context;
}