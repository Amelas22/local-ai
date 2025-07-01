import { configureStore } from '@reduxjs/toolkit';
import { setupListeners } from '@reduxjs/toolkit/query';
import { baseApi } from './api/baseApi';
import discoveryReducer from './slices/discoverySlice';
import uiReducer from './slices/uiSlice';
import authReducer from './slices/authSlice';
import websocketReducer from './slices/websocketSlice';

export const store = configureStore({
  reducer: {
    [baseApi.reducerPath]: baseApi.reducer,
    discovery: discoveryReducer,
    ui: uiReducer,
    auth: authReducer,
    websocket: websocketReducer,
  },
  middleware: (getDefaultMiddleware) =>
    getDefaultMiddleware({
      serializableCheck: {
        // Ignore these action types
        ignoredActions: ['discovery/setProcessingStartTime'],
        // Ignore these field paths in all actions
        ignoredActionPaths: ['payload.timestamp', 'meta.arg.originalArgs.date'],
        // Ignore these paths in the state
        ignoredPaths: ['discovery.processingStartTime'],
      },
    }).concat(baseApi.middleware),
});

// Enable refetch on focus/reconnect
setupListeners(store.dispatch);

export type RootState = ReturnType<typeof store.getState>;
export type AppDispatch = typeof store.dispatch;