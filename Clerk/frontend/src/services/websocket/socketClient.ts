import { io, Socket } from 'socket.io-client';
import { store } from '../../store/store';
import { 
  connectionEstablished, 
  connectionLost, 
  connectionError 
} from '../../store/slices/websocketSlice';
import { handleDiscoveryEvents } from './handlers/discoveryHandlers';
import { WebSocketEvents } from '../../types/websocket.types';

class SocketClient {
  private socket: Socket | null = null;
  private reconnectAttempts = 0;
  private maxReconnectAttempts = 5;
  private reconnectDelay = 1000; // Start with 1 second
  private eventHandlers: Map<string, Function[]> = new Map();
  private reconnectTimer: NodeJS.Timeout | null = null;

  constructor() {
    // Bind methods to preserve context
    this.connect = this.connect.bind(this);
    this.disconnect = this.disconnect.bind(this);
    this.emit = this.emit.bind(this);
    this.on = this.on.bind(this);
    this.off = this.off.bind(this);
  }

  connect(url?: string): void {
    if (this.socket?.connected) {
      console.log('WebSocket already connected');
      return;
    }

    // Use environment variable or default
    let wsUrl = url || import.meta.env.VITE_WS_URL || '';
    
    // If no URL is provided, use the current host
    if (!wsUrl) {
      // Use the same protocol and host as the current page
      const protocol = window.location.protocol === 'https:' ? 'wss:' : 'ws:';
      wsUrl = `${protocol}//${window.location.host}`;
    }
    
    // Handle relative WebSocket URLs
    if (wsUrl.startsWith('/')) {
      // Construct full WebSocket URL from current location
      const protocol = window.location.protocol === 'https:' ? 'wss:' : 'ws:';
      wsUrl = `${protocol}//${window.location.host}${wsUrl}`;
    }
    
    console.log('Connecting to WebSocket:', wsUrl);
    console.log('WebSocket path:', '/ws/socket.io/');
    console.log('Current location:', window.location.href);

    this.socket = io(wsUrl, {
      path: '/ws/socket.io/',
      transports: ['websocket', 'polling'], // Allow fallback to polling
      reconnection: false, // We'll handle reconnection manually
      auth: {
        token: store.getState().auth.token || 'dev-token'
      },
      // Add timeout
      timeout: 5000,
      // Force new connection
      forceNew: true
    });

    this.setupEventListeners();
  }

  private setupEventListeners(): void {
    if (!this.socket) return;

    // Connection events
    this.socket.on('connect', () => {
      console.log('WebSocket connected');
      this.reconnectAttempts = 0;
      this.reconnectDelay = 1000;
      store.dispatch(connectionEstablished());
    });

    this.socket.on('disconnect', (reason) => {
      console.log('WebSocket disconnected:', reason);
      store.dispatch(connectionLost());
      
      // Attempt to reconnect
      if (reason !== 'io client disconnect') {
        this.attemptReconnect();
      }
    });

    this.socket.on('connect_error', (error) => {
      console.error('WebSocket connection error:', error.message);
      console.error('Full error:', error);
      store.dispatch(connectionError(error.message));
    });

    // Add event listener for the 'connected' event sent by the server
    this.socket.on('connected', (data) => {
      console.log('Received connected event from server:', data);
    });

    // Listen for any errors
    this.socket.on('error', (error) => {
      console.error('Socket error event:', error);
    });

    // Test broadcast handler
    this.socket.on('test_broadcast', (data) => {
      console.log('Received test broadcast:', data);
    });

    // Register discovery event handlers
    handleDiscoveryEvents(this.socket);

    // Handle any custom event handlers that were registered
    this.eventHandlers.forEach((handlers, event) => {
      handlers.forEach(handler => {
        this.socket?.on(event, handler as any);
      });
    });
  }

  private attemptReconnect(): void {
    if (this.reconnectAttempts >= this.maxReconnectAttempts) {
      console.error('Max reconnection attempts reached');
      store.dispatch(connectionError('Max reconnection attempts reached'));
      return;
    }

    // Clear any existing reconnect timer
    if (this.reconnectTimer) {
      clearTimeout(this.reconnectTimer);
    }

    this.reconnectAttempts++;
    const currentDelay = this.calculateReconnectDelay();
    
    console.log(`Attempting to reconnect (${this.reconnectAttempts}/${this.maxReconnectAttempts}) in ${currentDelay}ms...`);
    
    store.dispatch(connectionError(`Reconnecting... (attempt ${this.reconnectAttempts}/${this.maxReconnectAttempts})`));

    this.reconnectTimer = setTimeout(() => {
      this.connect();
    }, currentDelay);
  }

  private calculateReconnectDelay(): number {
    // Exponential backoff with jitter
    const baseDelay = this.reconnectDelay * Math.pow(2, this.reconnectAttempts - 1);
    const jitter = Math.random() * 1000; // Add up to 1 second of jitter
    return Math.min(baseDelay + jitter, 30000); // Max 30 seconds
  }

  disconnect(): void {
    // Clear any pending reconnect timer
    if (this.reconnectTimer) {
      clearTimeout(this.reconnectTimer);
      this.reconnectTimer = null;
    }
    
    if (this.socket) {
      this.socket.disconnect();
      this.socket = null;
    }
    
    // Reset reconnect attempts
    this.reconnectAttempts = 0;
    this.reconnectDelay = 1000;
  }

  emit<T extends keyof WebSocketEvents>(event: T, data: WebSocketEvents[T]): void {
    if (!this.socket?.connected) {
      console.warn('Cannot emit event: WebSocket not connected');
      return;
    }

    this.socket.emit(event as string, data);
  }

  on<T extends keyof WebSocketEvents>(
    event: T, 
    handler: (data: WebSocketEvents[T]) => void
  ): void {
    // Store the handler for reconnection
    if (!this.eventHandlers.has(event as string)) {
      this.eventHandlers.set(event as string, []);
    }
    this.eventHandlers.get(event as string)!.push(handler as Function);

    // Add to current socket if connected
    this.socket?.on(event as string, handler as any);
  }

  off<T extends keyof WebSocketEvents>(
    event: T, 
    handler: (data: WebSocketEvents[T]) => void
  ): void {
    // Remove from stored handlers
    const handlers = this.eventHandlers.get(event as string);
    if (handlers) {
      const index = handlers.indexOf(handler as Function);
      if (index > -1) {
        handlers.splice(index, 1);
      }
    }

    // Remove from current socket
    this.socket?.off(event as string, handler as any);
  }

  isConnected(): boolean {
    return this.socket?.connected || false;
  }

  getSocket(): Socket | null {
    return this.socket;
  }
}

// Export singleton instance
export const socketClient = new SocketClient();