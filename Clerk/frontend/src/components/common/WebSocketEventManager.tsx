import { useEffect, ReactElement } from 'react';
import { useWebSocketContext } from '../../context/WebSocketContext';
import { handleDiscoveryEvents } from '../../services/websocket/handlers/discoveryHandlers';

export function WebSocketEventManager(): ReactElement | null {
  const { socket, state } = useWebSocketContext();

  useEffect(() => {
    if (socket && state.connected) {
      // Register discovery event handlers
      handleDiscoveryEvents(socket);
      
      console.log('WebSocket event handlers registered');
    }
  }, [socket, state.connected]);

  // This component doesn't render anything
  return null;
}