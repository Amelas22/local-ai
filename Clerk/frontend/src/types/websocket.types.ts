import { DiscoveryWebSocketEvents } from './discovery.types';

// Combine all WebSocket event types
export interface WebSocketEvents extends DiscoveryWebSocketEvents {
  // Connection events
  'connect': void;
  'disconnect': string;
  'connect_error': Error;
  'connected': {
    message: string;
    sid: string;
  };
  
  // General events
  'ping': void;
  'pong': void;
  'test_broadcast': {
    message: string;
    timestamp: string;
  };
  
  // Case subscription events
  'subscribe_case': {
    case_id: string;
  };
  'unsubscribe_case': {
    case_id: string;
  };
  'subscribed': {
    case_id: string;
  };
  
  // Motion drafting events
  'motion:started': {
    motionId: string;
    caseId: string;
    type: string;
  };
  'motion:outline_started': {
    motionId: string;
    caseId: string;
    motionType: string;
  };
  'motion:outline_completed': {
    motionId: string;
    outline: any;
  };
  'motion:draft_started': {
    motionId: string;
    progress: number;
  };
  'motion:draft_completed': {
    motionId: string;
    downloadUrl: string;
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
  
  // Search events
  'search:started': {
    queryId: string;
    query: string;
    caseId: string;
  };
  'search:results': {
    queryId: string;
    results: any[];
    totalResults: number;
  };
  'search:error': {
    queryId: string;
    error: string;
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