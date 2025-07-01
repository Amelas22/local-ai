import { createSlice, PayloadAction } from '@reduxjs/toolkit';

interface WebSocketState {
  connected: boolean;
  connecting: boolean;
  error: string | null;
  reconnectAttempts: number;
  lastConnected: string | null;
  activeEvents: string[];
}

const initialState: WebSocketState = {
  connected: false,
  connecting: false,
  error: null,
  reconnectAttempts: 0,
  lastConnected: null,
  activeEvents: []
};

const websocketSlice = createSlice({
  name: 'websocket',
  initialState,
  reducers: {
    connectionInitiated: (state) => {
      state.connecting = true;
      state.error = null;
    },
    connectionEstablished: (state) => {
      state.connected = true;
      state.connecting = false;
      state.error = null;
      state.reconnectAttempts = 0;
      state.lastConnected = new Date().toISOString();
    },
    connectionLost: (state) => {
      state.connected = false;
      state.connecting = false;
      state.activeEvents = [];
    },
    connectionError: (state, action: PayloadAction<string>) => {
      state.error = action.payload;
      state.connecting = false;
      state.connected = false;
    },
    reconnectAttempt: (state) => {
      state.reconnectAttempts += 1;
      state.connecting = true;
    },
    eventReceived: (state, action: PayloadAction<string>) => {
      if (!state.activeEvents.includes(action.payload)) {
        state.activeEvents.push(action.payload);
      }
    },
    clearActiveEvents: (state) => {
      state.activeEvents = [];
    }
  }
});

export const {
  connectionInitiated,
  connectionEstablished,
  connectionLost,
  connectionError,
  reconnectAttempt,
  eventReceived,
  clearActiveEvents
} = websocketSlice.actions;

export default websocketSlice.reducer;