import { DiscoveryWebSocketEvents } from './discovery.types';

// Combine all WebSocket event types
export interface WebSocketEvents extends DiscoveryWebSocketEvents {
  // Connection events
  'connect': void;
  'disconnect': string;
  'connect_error': Error;
  
  // General events
  'ping': void;
  'pong': void;
  
  // Future motion drafting events
  'motion:started': {
    motionId: string;
    caseId: string;
    type: string;
  };
  'motion:section_completed': {
    motionId: string;
    section: string;
    content: string;
  };
  'motion:completed': {
    motionId: string;
    downloadUrl: string;
  };
  'motion:error': {
    motionId: string;
    error: string;
  };
  
  // Future search events
  'search:results': {
    queryId: string;
    results: any[];
    totalResults: number;
  };
}

// Type for event names
export type WebSocketEventName = keyof WebSocketEvents;

// Type for event data
export type WebSocketEventData<T extends WebSocketEventName> = WebSocketEvents[T];

// Connection status
export enum ConnectionStatus {
  DISCONNECTED = 'disconnected',
  CONNECTING = 'connecting',
  CONNECTED = 'connected',
  RECONNECTING = 'reconnecting',
  ERROR = 'error'
}