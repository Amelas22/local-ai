name: "React 19 Frontend with Working WebSocket Integration"
description: |

## Purpose
Complete revamp of the Clerk Legal AI frontend to use React 19 best practices with a fully functional WebSocket connection for real-time discovery processing, document management, and motion drafting.

## Core Principles
1. **React 19 Modern Patterns**: Leverage React 19 compiler optimizations and new APIs
2. **WebSocket Reliability**: Fix current timeout issues with proper connection management
3. **Case Isolation**: Maintain existing case-based security model
4. **Type Safety**: Strict TypeScript implementation following CLAUDE.md
5. **Performance**: Optimize for real-time updates and large document processing

---

## Goal
Transform the existing React 18 frontend into a modern React 19 application with reliable WebSocket connections that enable real-time discovery processing, document uploads via Box folder-id, and motion drafting. Replace Gunicorn backend with async-capable server for proper WebSocket support.

## Why
- **User Experience**: Real-time updates during document processing prevent user confusion about processing status
- **Technical Debt**: Current WebSocket implementation times out and fails consistently
- **Modern Standards**: React 19 provides better performance and developer experience
- **Scalability**: Support multiple law firms with proper case isolation
- **Integration**: Seamless connection between frontend UI and existing backend functionality

## What
A complete frontend implementation that provides:
- Working WebSocket connection for real-time discovery processing updates
- Case selection sidebar with proper isolation
- Document processing with live progress indicators
- Motion outline and draft generation with real-time status
- Responsive UI with proper loading states and error handling
- Modern React 19 patterns with TypeScript strict mode

### Success Criteria
- [ ] WebSocket connection establishes and maintains connection without timeouts
- [ ] Real-time discovery processing updates display correctly
- [ ] Case switching works with proper document isolation
- [ ] Document upload via Box folder-id functions with progress tracking
- [ ] Motion drafting shows live progress and results
- [ ] All tests pass with minimum 80% coverage
- [ ] No TypeScript errors in strict mode
- [ ] Backend runs with Uvicorn instead of Gunicorn for WebSocket support

## All Needed Context

### Documentation & References
```yaml
# MUST READ - Include these in your context window
- url: https://react.dev/reference/react/useEffect
  why: Modern useEffect patterns for WebSocket connection management
  
- url: https://socket.io/how-to/use-with-react
  why: Official Socket.IO React integration patterns
  
- url: https://vite.dev/config/server-options
  why: Proxy configuration for WebSocket development
  
- file: /mnt/c/Webapps/local-ai/Clerk/src/websocket/socket_server.py
  why: Current backend WebSocket implementation and event structure
  
- file: /mnt/c/Webapps/local-ai/Clerk/frontend/src/services/websocket/socketClient.ts
  why: Current frontend WebSocket client with identified issues
  
- file: /mnt/c/Webapps/local-ai/CLAUDE.md
  why: Project rules, type safety requirements, and testing standards
  
- file: /mnt/c/Webapps/local-ai/examples/CLAUDE-react.md
  why: React 19 patterns and requirements for this project
  
- file: /mnt/c/Webapps/local-ai/docker-compose.yml
  why: Current tech stack and service configuration
  
- docfile: Context7 React Documentation
  why: React 19 useEffect and custom hook patterns
  
- docfile: Context7 Socket.IO Documentation  
  why: FastAPI + Socket.IO integration best practices
```

### Current Codebase Structure
```bash
Clerk/
├── main.py                         # FastAPI entry point (needs Uvicorn instead of Gunicorn)
├── src/
│   ├── websocket/
│   │   └── socket_server.py        # Current WebSocket server (path mismatch issue)
│   ├── ai_agents/                  # Motion drafting agents
│   ├── document_processing/        # Box integration and PDF processing
│   └── vector_storage/             # Qdrant case isolation
├── frontend/
│   ├── src/
│   │   ├── services/websocket/
│   │   │   └── socketClient.ts     # BROKEN: Complex URL logic, memory leaks
│   │   ├── hooks/
│   │   │   └── useWebSocket.ts     # BROKEN: Manual reconnection, poor cleanup
│   │   ├── components/
│   │   │   ├── discovery/          # Discovery processing components
│   │   │   └── common/             # Sidebar, Layout components
│   │   └── pages/                  # Main application pages
│   ├── vite.config.ts              # NEEDS: WebSocket proxy configuration
│   └── package.json                # React 18 (needs upgrade to React 19)
```

### Desired Codebase Structure with New Files
```bash
Clerk/
├── main.py                         # ✅ Keep: Use Uvicorn startup
├── src/websocket/
│   └── socket_server.py           # 🔧 Fix: Path configuration
├── frontend/
│   ├── src/
│   │   ├── hooks/
│   │   │   ├── useWebSocket.ts     # 🔧 Rewrite: React 19 patterns, proper cleanup
│   │   │   ├── useDiscovery.ts     # ➕ New: Discovery processing hook
│   │   │   └── useCaseSelection.ts # ➕ New: Case isolation management
│   │   ├── services/
│   │   │   ├── websocket/
│   │   │   │   ├── socketClient.ts  # 🔧 Rewrite: Simplified, reliable connection
│   │   │   │   ├── eventHandlers.ts # ➕ New: Centralized event handling
│   │   │   │   └── types.ts        # ➕ New: WebSocket event type definitions
│   │   │   └── api/
│   │   │       └── caseApi.ts      # ➕ New: Case management API calls
│   │   ├── components/
│   │   │   ├── realtime/
│   │   │   │   ├── ConnectionStatus.tsx    # ➕ New: WebSocket status indicator
│   │   │   │   ├── DiscoveryProgress.tsx   # 🔧 Fix: Real-time progress display
│   │   │   │   └── MotionProgress.tsx      # ➕ New: Motion drafting progress
│   │   │   ├── case/
│   │   │   │   ├── CaseSelector.tsx        # ➕ New: Case selection component
│   │   │   │   └── CaseProvider.tsx        # ➕ New: Case context provider
│   │   │   └── layout/
│   │   │       └── Sidebar.tsx             # 🔧 Fix: Case isolation integration
│   │   ├── context/
│   │   │   ├── WebSocketContext.tsx        # ➕ New: WebSocket context provider
│   │   │   └── CaseContext.tsx             # ➕ New: Case management context
│   │   └── types/
│   │       ├── websocket.types.ts          # 🔧 Enhance: Complete event typing
│   │       └── case.types.ts               # ➕ New: Case-related types
│   ├── vite.config.ts                      # 🔧 Fix: Add WebSocket proxy
│   └── package.json                        # 🔧 Update: React 19 dependencies
```

### Known Gotchas & Critical Issues
```typescript
// CRITICAL: Backend WebSocket path mismatch
// Current: backend serves on '/socket.io' but mounts at '/ws'
// Fix: Change socket_server.py socketio_path to '/ws/socket.io'

// CRITICAL: Vite proxy must include ws: true for WebSocket support
// Pattern: proxy: { '/ws': { target: 'http://localhost:8000', ws: true } }

// CRITICAL: Frontend URL construction is overly complex and error-prone
// Current: Complex environment-based URL building causes connection failures
// Fix: Simplified URL strategy with proper development/production handling

// CRITICAL: useEffect cleanup is missing in current WebSocket hook
// Pattern: Always return cleanup function to prevent memory leaks

// CRITICAL: React 19 requires ReactElement instead of JSX.Element
// Pattern: import { ReactElement } from 'react'; function Comp(): ReactElement

// GOTCHA: Socket.IO is NOT raw WebSocket - requires socket.io-client
// Pattern: import { io } from 'socket.io-client'

// GOTCHA: Case isolation requires case_name in every WebSocket subscription
// Pattern: socket.emit('subscribe_case', { case_name: activeCaseName })
```

## Implementation Blueprint

### Data Models and Types
```typescript
// WebSocket Event Types
interface DiscoveryEvent {
  type: 'discovery:started' | 'discovery:document_found' | 'discovery:chunking' 
       | 'discovery:embedding' | 'discovery:stored' | 'discovery:completed' | 'discovery:error';
  case_name: string;
  data: {
    folder_id?: string;
    document_name?: string;
    progress?: number;
    chunk_count?: number;
    error_message?: string;
  };
}

interface MotionEvent {
  type: 'motion:outline_started' | 'motion:outline_completed' | 'motion:draft_started' | 'motion:draft_completed';
  case_name: string;
  data: {
    motion_type?: string;
    outline?: any;
    draft?: any;
    progress?: number;
  };
}

// Case Management Types
interface CaseInfo {
  case_name: string;
  display_name: string;
  document_count: number;
  last_activity: string;
}

// WebSocket Connection State
interface WebSocketState {
  connected: boolean;
  connecting: boolean;
  error: string | null;
  reconnectAttempts: number;
  subscribed_case: string | null;
}
```

### Task List - Implementation Order

```yaml
Task 1 - Fix Backend WebSocket Path Configuration:
MODIFY src/websocket/socket_server.py:
  - FIND: socketio_path='/socket.io'
  - REPLACE WITH: socketio_path='/ws/socket.io'
  - PRESERVE: All existing event handlers and connection logic
  - ENSURE: FastAPI mount remains at app.mount("/ws", socket_app)

Task 2 - Update Backend to Use Uvicorn Instead of Gunicorn:
MODIFY main.py:
  - FIND: Any gunicorn references or WSGI setup
  - REPLACE WITH: Uvicorn ASGI server configuration
  - ENSURE: WebSocket support is maintained
  - PATTERN: if __name__ == "__main__": uvicorn.run(app, host="0.0.0.0", port=8000)

Task 3 - Upgrade Frontend to React 19:
MODIFY package.json:
  - UPDATE: "react": "^19.0.0", "react-dom": "^19.0.0"
  - UPDATE: "@types/react": "^19.0.0", "@types/react-dom": "^19.0.0"
  - ADD: "@vitejs/plugin-react": "^4.0.0" (React 19 support)
  - KEEP: Existing Socket.IO, MUI, and other dependencies

Task 4 - Fix Vite Configuration for WebSocket Proxy:
MODIFY vite.config.ts:
  - ADD: Proper WebSocket proxy configuration
  - PATTERN: proxy: { '/ws': { target: 'http://localhost:8000', ws: true, rewrite: (path) => path } }
  - ENSURE: Development server supports WebSocket upgrades

Task 5 - Create WebSocket Context Provider:
CREATE src/context/WebSocketContext.tsx:
  - IMPLEMENT: React Context for WebSocket connection state
  - PATTERN: Use React 19 useEffect patterns from examples
  - INCLUDE: Connection status, error handling, case subscription
  - ENSURE: Proper cleanup and reconnection logic

Task 6 - Rewrite WebSocket Hook with React 19 Patterns:
REWRITE src/hooks/useWebSocket.ts:
  - IMPLEMENT: Simplified, reliable connection management
  - PATTERN: Custom hook with useEffect cleanup as shown in React docs
  - REMOVE: Complex URL construction logic
  - ADD: Exponential backoff reconnection
  - ENSURE: Memory leak prevention with proper cleanup

Task 7 - Create Case Management System:
CREATE src/context/CaseContext.tsx:
  - IMPLEMENT: Case selection and isolation context
  - PATTERN: Similar to WebSocketContext but for case state
  - INCLUDE: Active case tracking, case list management
  - ENSURE: Integration with WebSocket case subscription

CREATE src/hooks/useCaseSelection.ts:
  - IMPLEMENT: Case switching with WebSocket resubscription
  - PATTERN: useEffect dependency on case change
  - ENSURE: Proper cleanup of previous case subscription

Task 8 - Fix Discovery Processing Components:
MODIFY src/components/discovery/:
  - UPDATE: All components to use ReactElement return type
  - CONNECT: To WebSocket context for real-time updates
  - PATTERN: useContext(WebSocketContext) for event listening
  - ENSURE: Proper TypeScript strict mode compliance

Task 9 - Create Real-time Status Components:
CREATE src/components/realtime/ConnectionStatus.tsx:
  - IMPLEMENT: WebSocket connection status indicator
  - PATTERN: Traffic light system (green/yellow/red)
  - CONNECT: To WebSocketContext for connection state

CREATE src/components/realtime/DiscoveryProgress.tsx:
  - IMPLEMENT: Real-time discovery processing progress
  - PATTERN: Progress bar with step indicators
  - LISTEN: For discovery:* events from WebSocket

CREATE src/components/realtime/MotionProgress.tsx:
  - IMPLEMENT: Motion drafting progress indicator
  - PATTERN: Similar to DiscoveryProgress but for motion events
  - LISTEN: For motion:* events from WebSocket

Task 10 - Integrate Case Selection in Sidebar:
MODIFY src/components/common/Sidebar.tsx:
  - ADD: Case selector dropdown/list
  - CONNECT: To CaseContext for case switching
  - ENSURE: Visual indication of active case
  - PATTERN: MUI Select component with case list

Task 11 - Create Comprehensive Test Suite:
CREATE tests/ structure:
  - ADD: WebSocket hook tests with mock Socket.IO
  - ADD: Component tests with React Testing Library
  - ADD: Integration tests for case switching
  - PATTERN: Follow existing test patterns in codebase
  - ENSURE: 80% minimum coverage as per CLAUDE.md

Task 12 - Update Environment Configuration:
CREATE .env.example:
  - ADD: VITE_WS_URL configuration examples
  - ADD: Development vs production WebSocket URLs
  - DOCUMENT: All required environment variables

MODIFY src/services/websocket/socketClient.ts:
  - SIMPLIFY: URL construction logic
  - USE: Environment variables properly
  - PATTERN: const wsUrl = import.meta.env.VITE_WS_URL || 'ws://localhost:8000'
```

### Critical WebSocket Implementation Pattern
```typescript
// Custom Hook Pattern (React 19 Best Practice)
export function useWebSocket(caseId?: string): WebSocketState {
  const [state, setState] = useState<WebSocketState>({
    connected: false,
    connecting: false,
    error: null,
    reconnectAttempts: 0,
    subscribed_case: null
  });

  const socketRef = useRef<Socket | null>(null);

  useEffect(() => {
    // CRITICAL: Simple URL construction
    const wsUrl = import.meta.env.VITE_WS_URL || 'http://localhost:8000';
    
    setState(prev => ({ ...prev, connecting: true }));
    
    // PATTERN: Socket.IO client with proper configuration
    const socket = io(wsUrl, {
      path: '/ws/socket.io',  // CRITICAL: Match backend path
      transports: ['websocket', 'polling'],  // Fallback support
      timeout: 20000,
      forceNew: true
    });

    socketRef.current = socket;

    // Connection event handlers
    socket.on('connect', () => {
      setState(prev => ({ 
        ...prev, 
        connected: true, 
        connecting: false, 
        error: null,
        reconnectAttempts: 0 
      }));
      
      // CRITICAL: Subscribe to case if provided
      if (caseId) {
        socket.emit('subscribe_case', { case_name: caseId });
        setState(prev => ({ ...prev, subscribed_case: caseId }));
      }
    });

    socket.on('connect_error', (error) => {
      setState(prev => ({ 
        ...prev, 
        connected: false, 
        connecting: false, 
        error: error.message,
        reconnectAttempts: prev.reconnectAttempts + 1 
      }));
    });

    socket.on('disconnect', () => {
      setState(prev => ({ 
        ...prev, 
        connected: false, 
        subscribed_case: null 
      }));
    });

    // CRITICAL: Cleanup function to prevent memory leaks
    return () => {
      if (socketRef.current) {
        socketRef.current.disconnect();
        socketRef.current = null;
      }
    };
  }, [caseId]); // Re-connect when case changes

  return state;
}
```

### Integration Points
```yaml
BACKEND:
  - file: src/websocket/socket_server.py
  - change: socketio_path='/ws/socket.io' 
  - verify: WebSocket handshake succeeds

FRONTEND_CONFIG:
  - file: vite.config.ts
  - add: WebSocket proxy with ws: true
  - verify: Development proxy works

ENVIRONMENT:
  - add: VITE_WS_URL for different environments
  - pattern: VITE_WS_URL=http://localhost:8000
  - verify: Connection URLs resolve correctly

DOCKER:
  - ensure: Caddy proxy supports WebSocket upgrades
  - verify: Production WebSocket routing works
```

## Validation Loop

### Level 1: Syntax & Style
```bash
# Fix TypeScript and linting issues FIRST
npm run type-check                   # Must pass strict TypeScript
npm run lint                        # Must pass with zero warnings
npm run format                      # Auto-format code

# Backend validation
cd Clerk && python -m ruff check src/ --fix
cd Clerk && python -m mypy src/
```

### Level 2: WebSocket Connection Tests
```typescript
// CREATE tests/hooks/useWebSocket.test.tsx
describe('useWebSocket Hook', () => {
  it('should establish connection successfully', async () => {
    const { result } = renderHook(() => useWebSocket('test-case'));
    
    await waitFor(() => {
      expect(result.current.connected).toBe(true);
    });
    
    expect(result.current.subscribed_case).toBe('test-case');
  });

  it('should handle connection errors gracefully', async () => {
    // Mock server unavailable
    const { result } = renderHook(() => useWebSocket());
    
    await waitFor(() => {
      expect(result.current.error).toBeTruthy();
    });
  });

  it('should cleanup on unmount', () => {
    const { unmount } = renderHook(() => useWebSocket());
    const spy = jest.spyOn(socketMock, 'disconnect');
    
    unmount();
    
    expect(spy).toHaveBeenCalled();
  });
});
```

```bash
# Run tests and iterate until passing
npm test -- --coverage --watchAll=false
# Target: 80% minimum coverage, all tests passing
```

### Level 3: Integration Testing
```bash
# Start backend with WebSocket support
cd Clerk && python main.py

# Start frontend development server
cd Clerk/frontend && npm run dev

# Manual WebSocket test
# Open browser to http://localhost:5173
# Open Developer Tools > Network > WS tab
# Verify WebSocket connection established to ws://localhost:8000/ws/socket.io/
# Select a case from sidebar
# Verify 'subscribe_case' event sent
# Trigger discovery processing
# Verify real-time events received

# Test case switching
# Switch cases in sidebar
# Verify new 'subscribe_case' event
# Verify UI updates for new case
```

### Level 4: Production Verification
```bash
# Build production frontend
npm run build

# Test with Docker stack
docker-compose up -d

# Verify WebSocket through Caddy proxy
# Check https://your-domain/ws/socket.io/ connection
# Verify SSL WebSocket (wss://) works properly
```

## Final Validation Checklist
- [ ] WebSocket connection establishes within 5 seconds: `Check browser dev tools WS tab`
- [ ] Real-time discovery updates display: `Trigger discovery and watch progress`
- [ ] Case switching preserves WebSocket connection: `Switch cases multiple times`
- [ ] No memory leaks after component unmounts: `React DevTools Profiler`
- [ ] All TypeScript strict mode compliant: `npm run type-check`
- [ ] Test coverage above 80%: `npm test -- --coverage`
- [ ] Production WebSocket works through proxy: `Test on Docker stack`
- [ ] Error states handled gracefully: `Disconnect server mid-processing`
- [ ] Reconnection works automatically: `Network interruption test`

---

## Anti-Patterns to Avoid
- ❌ Don't use complex URL construction - keep it simple
- ❌ Don't skip useEffect cleanup - prevents memory leaks
- ❌ Don't use JSX.Element - React 19 requires ReactElement
- ❌ Don't ignore WebSocket connection state - always show status
- ❌ Don't hardcode WebSocket URLs - use environment variables
- ❌ Don't use raw WebSocket - Socket.IO provides reliability features
- ❌ Don't forget case isolation - every WebSocket event needs case context
- ❌ Don't use Gunicorn for WebSocket - requires async server like Uvicorn

## Implementation Success Score: 9/10
This PRP provides comprehensive context including:
✅ Complete analysis of current broken implementation
✅ Specific file references and patterns to follow
✅ React 19 documentation and examples
✅ Socket.IO integration best practices
✅ Detailed step-by-step implementation tasks
✅ Executable validation loops with specific commands
✅ Known gotchas and critical configuration fixes
✅ Complete type definitions and patterns
✅ Memory leak prevention and cleanup patterns
✅ Production deployment considerations

The AI agent has all necessary context to implement this feature successfully in one pass through iterative validation and refinement.