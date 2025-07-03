import { ReactElement, useState, useEffect } from 'react';
import { Box, Button, Card, CardContent, Typography, List, ListItem, Chip, Stack } from '@mui/material';
import { useWebSocket } from '../hooks/useWebSocket';
import { ConnectionStatus } from '../components/realtime/ConnectionStatus';

interface LogEntry {
  timestamp: Date;
  message: string;
  type: 'info' | 'success' | 'error';
}

export default function WebSocketTest(): ReactElement {
  const [logs, setLogs] = useState<LogEntry[]>([]);
  const { connected, connecting, error, on, emit, subscribeToCase, socket } = useWebSocket();

  const addLog = (message: string, type: LogEntry['type'] = 'info') => {
    setLogs(prev => [...prev, { timestamp: new Date(), message, type }]);
  };

  useEffect(() => {
    if (connected) {
      addLog('WebSocket connected!', 'success');
    } else if (connecting) {
      addLog('Connecting to WebSocket...', 'info');
    } else if (error) {
      addLog(`Connection error: ${error}`, 'error');
    }
  }, [connected, connecting, error]);

  useEffect(() => {
    // Listen for server events
    const unsubConnected = on('connected', (data) => {
      addLog(`Server acknowledged connection: ${JSON.stringify(data)}`, 'success');
    });

    const unsubPong = on('pong', () => {
      addLog('Received pong from server', 'success');
    });

    const unsubSubscribed = on('subscribed', (data) => {
      addLog(`Subscribed to case: ${JSON.stringify(data)}`, 'success');
    });

    return () => {
      unsubConnected();
      unsubPong();
      unsubSubscribed();
    };
  }, [on]);

  const testPing = () => {
    if (!connected) {
      addLog('Not connected!', 'error');
      return;
    }
    addLog('Sending ping...', 'info');
    emit('ping', undefined);
  };

  const testCaseSubscription = () => {
    if (!connected) {
      addLog('Not connected!', 'error');
      return;
    }
    const caseId = `test_case_${Date.now()}`;
    addLog(`Subscribing to case: ${caseId}`, 'info');
    subscribeToCase(caseId);
  };

  const getLogColor = (type: LogEntry['type']) => {
    switch (type) {
      case 'success': return 'success.main';
      case 'error': return 'error.main';
      default: return 'info.main';
    }
  };

  return (
    <Box sx={{ p: 3 }}>
      <Typography variant="h4" gutterBottom>
        WebSocket Connection Test
      </Typography>

      <Stack direction="row" spacing={2} mb={3}>
        <ConnectionStatus />
        <Chip 
          label={`Socket ID: ${socket?.id || 'N/A'}`} 
          variant="outlined" 
        />
      </Stack>

      <Stack direction="row" spacing={2} mb={3}>
        <Button 
          variant="contained" 
          onClick={testPing} 
          disabled={!connected}
        >
          Test Ping
        </Button>
        <Button 
          variant="contained" 
          onClick={testCaseSubscription}
          disabled={!connected}
        >
          Test Case Subscription
        </Button>
      </Stack>

      <Card>
        <CardContent>
          <Typography variant="h6" gutterBottom>
            Connection Log
          </Typography>
          <List sx={{ maxHeight: 400, overflow: 'auto', bgcolor: 'grey.100' }}>
            {logs.map((log, index) => (
              <ListItem key={index} sx={{ py: 0.5 }}>
                <Typography
                  variant="body2"
                  sx={{ 
                    fontFamily: 'monospace',
                    color: getLogColor(log.type)
                  }}
                >
                  {log.timestamp.toLocaleTimeString()} - {log.message}
                </Typography>
              </ListItem>
            ))}
          </List>
        </CardContent>
      </Card>
    </Box>
  );
}