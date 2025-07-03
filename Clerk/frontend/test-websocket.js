// Test WebSocket connection to Docker backend
import { io } from 'socket.io-client';

const wsUrl = 'http://localhost:8000';  // Direct to Clerk backend
const socket = io(wsUrl, {
  path: '/ws/socket.io/',
  transports: ['websocket', 'polling'],
  timeout: 5000,
  reconnection: false
});

console.log(`Attempting to connect to ${wsUrl}/ws/socket.io/`);

socket.on('connect', () => {
  console.log('✅ Connected successfully!');
  console.log('Socket ID:', socket.id);
  
  // Test ping
  socket.emit('ping');
  
  // Subscribe to a test case
  socket.emit('subscribe_case', { case_id: 'test_case' });
  
  // Disconnect after 2 seconds
  setTimeout(() => {
    socket.disconnect();
    process.exit(0);
  }, 2000);
});

socket.on('connect_error', (error) => {
  console.error('❌ Connection error:', error.message);
  console.error('Error type:', error.type);
  process.exit(1);
});

socket.on('connected', (data) => {
  console.log('📨 Received connected event:', data);
});

socket.on('pong', () => {
  console.log('🏓 Received pong');
});

socket.on('subscribed', (data) => {
  console.log('📋 Subscribed to case:', data);
});

socket.on('error', (error) => {
  console.error('❌ Socket error:', error);
});

// Timeout after 10 seconds
setTimeout(() => {
  console.error('❌ Connection timeout');
  process.exit(1);
}, 10000);