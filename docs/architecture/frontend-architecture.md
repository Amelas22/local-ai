# Frontend Architecture

## Overview

The Clerk Legal AI System frontend is built with React and TypeScript, following modern web development practices. The architecture emphasizes component reusability, type safety, and real-time updates through WebSocket connections.

## Technology Stack

### Core Technologies
- **React 18+**: Component-based UI framework
- **TypeScript**: Type-safe JavaScript
- **Vite**: Build tool and dev server
- **React Router v6**: Client-side routing
- **Socket.io Client**: Real-time WebSocket communication

### State Management
- **React Context API**: Global state for auth and case context
- **React Query (TanStack Query)**: Server state management
- **Zustand**: Client state for complex UI state

### UI Framework
- **Material-UI (MUI) v5**: Component library
- **Emotion**: CSS-in-JS styling
- **React Hook Form**: Form management
- **Zod**: Schema validation

## Architecture Principles

### Design Principles
- **Component-First**: Build reusable, composable components
- **Type Safety**: Full TypeScript coverage
- **Accessibility**: WCAG 2.1 AA compliance
- **Performance**: Code splitting and lazy loading
- **Responsive**: Mobile-first design approach

### Code Organization
```
src/
├── components/          # Reusable UI components
├── features/           # Feature-specific components
├── hooks/             # Custom React hooks
├── services/          # API and external services
├── contexts/          # React contexts
├── utils/             # Utility functions
├── types/             # TypeScript type definitions
└── styles/            # Global styles and themes
```

## Component Architecture

### Component Hierarchy
```
App
├── AuthProvider
│   └── RouterProvider
│       ├── Layout
│       │   ├── Header
│       │   ├── Sidebar
│       │   └── MainContent
│       └── Routes
│           ├── CaseList
│           ├── CaseDetail
│           ├── DiscoveryProcessing
│           ├── DeficiencyAnalysis
│           └── MotionDrafting
```

### Component Categories

#### Layout Components
```typescript
// Layout/MainLayout.tsx
interface MainLayoutProps {
  children: React.ReactNode;
  showSidebar?: boolean;
}

export const MainLayout: React.FC<MainLayoutProps> = ({ 
  children, 
  showSidebar = true 
}) => {
  return (
    <Box sx={{ display: 'flex' }}>
      {showSidebar && <Sidebar />}
      <Box component="main" sx={{ flexGrow: 1 }}>
        <Header />
        <Container maxWidth="xl">
          {children}
        </Container>
      </Box>
    </Box>
  );
};
```

#### Feature Components
```typescript
// features/Discovery/DiscoveryUpload.tsx
export const DiscoveryUpload: React.FC = () => {
  const { caseId } = useCaseContext();
  const [files, setFiles] = useState<File[]>([]);
  const uploadMutation = useDiscoveryUpload();

  const handleUpload = async () => {
    await uploadMutation.mutateAsync({
      caseId,
      files,
      metadata: {
        productionBatch: 'PROD_001',
        producingParty: 'Opposing Counsel'
      }
    });
  };

  return (
    <UploadZone
      onFilesAdded={setFiles}
      acceptedTypes={['.pdf']}
      maxFiles={100}
    />
  );
};
```

#### Shared Components
```typescript
// components/DocumentViewer/DocumentViewer.tsx
interface DocumentViewerProps {
  documentId: string;
  highlights?: TextHighlight[];
  onPageChange?: (page: number) => void;
}

export const DocumentViewer: React.FC<DocumentViewerProps> = ({
  documentId,
  highlights = [],
  onPageChange
}) => {
  // PDF viewing logic with highlights
};
```

## State Management

### Global State Context
```typescript
// contexts/CaseContext.tsx
interface CaseContextValue {
  currentCase: Case | null;
  permissions: Permission[];
  switchCase: (caseId: string) => Promise<void>;
}

export const CaseContext = createContext<CaseContextValue | null>(null);

export const CaseProvider: React.FC<{ children: ReactNode }> = ({ 
  children 
}) => {
  const [currentCase, setCurrentCase] = useState<Case | null>(null);
  
  // Case management logic
  
  return (
    <CaseContext.Provider value={{ currentCase, permissions, switchCase }}>
      {children}
    </CaseContext.Provider>
  );
};
```

### Server State with React Query
```typescript
// hooks/useDiscoveryProduction.ts
export const useDiscoveryProduction = (productionId: string) => {
  return useQuery({
    queryKey: ['discovery', 'production', productionId],
    queryFn: () => api.discovery.getProduction(productionId),
    refetchInterval: (data) => 
      data?.status === 'processing' ? 5000 : false,
    staleTime: 5 * 60 * 1000, // 5 minutes
  });
};
```

### Local UI State with Zustand
```typescript
// stores/uiStore.ts
interface UIStore {
  sidebarOpen: boolean;
  selectedDocuments: string[];
  toggleSidebar: () => void;
  selectDocument: (id: string) => void;
}

export const useUIStore = create<UIStore>((set) => ({
  sidebarOpen: true,
  selectedDocuments: [],
  toggleSidebar: () => set((state) => ({ 
    sidebarOpen: !state.sidebarOpen 
  })),
  selectDocument: (id) => set((state) => ({
    selectedDocuments: [...state.selectedDocuments, id]
  }))
}));
```

## Routing Architecture

### Route Configuration
```typescript
// routes/index.tsx
export const routes: RouteObject[] = [
  {
    path: '/',
    element: <MainLayout />,
    children: [
      {
        index: true,
        element: <Navigate to="/cases" replace />
      },
      {
        path: 'cases',
        children: [
          {
            index: true,
            element: <CaseList />
          },
          {
            path: ':caseId',
            element: <CaseDetail />,
            children: [
              {
                path: 'discovery',
                element: <DiscoveryDashboard />
              },
              {
                path: 'deficiency/:reportId',
                element: <DeficiencyReport />
              },
              {
                path: 'motions',
                element: <MotionsList />
              }
            ]
          }
        ]
      }
    ]
  },
  {
    path: '/auth',
    element: <AuthLayout />,
    children: [
      {
        path: 'login',
        element: <Login />
      }
    ]
  }
];
```

### Protected Routes
```typescript
// components/ProtectedRoute.tsx
export const ProtectedRoute: React.FC<{ children: ReactNode }> = ({ 
  children 
}) => {
  const { user, loading } = useAuth();
  
  if (loading) return <LoadingScreen />;
  if (!user) return <Navigate to="/auth/login" />;
  
  return <>{children}</>;
};
```

## API Integration

### API Client Setup
```typescript
// services/api/client.ts
class APIClient {
  private baseURL: string;
  private token: string | null = null;

  constructor() {
    this.baseURL = import.meta.env.VITE_API_URL;
  }

  setAuthToken(token: string) {
    this.token = token;
  }

  async request<T>(
    endpoint: string,
    options: RequestInit = {}
  ): Promise<T> {
    const headers = {
      'Content-Type': 'application/json',
      ...(this.token && { Authorization: `Bearer ${this.token}` }),
      ...(options.headers || {})
    };

    const response = await fetch(`${this.baseURL}${endpoint}`, {
      ...options,
      headers
    });

    if (!response.ok) {
      throw new APIError(response.status, await response.json());
    }

    return response.json();
  }
}

export const api = new APIClient();
```

### API Service Layer
```typescript
// services/api/discovery.ts
export const discoveryAPI = {
  async processProduction(data: ProcessProductionRequest) {
    const formData = new FormData();
    data.files.forEach(file => formData.append('discovery_files', file));
    formData.append('metadata', JSON.stringify(data.metadata));
    
    return api.request<ProcessProductionResponse>(
      '/api/v1/discovery/process',
      {
        method: 'POST',
        body: formData,
        headers: {
          'X-Case-ID': data.caseId
        }
      }
    );
  },

  async getProduction(productionId: string) {
    return api.request<DiscoveryProduction>(
      `/api/v1/discovery/productions/${productionId}`
    );
  }
};
```

## Real-time Updates

### WebSocket Connection
```typescript
// services/websocket/client.ts
class WebSocketClient {
  private socket: Socket | null = null;
  private listeners: Map<string, Set<Function>> = new Map();

  connect(token: string) {
    this.socket = io(import.meta.env.VITE_WS_URL, {
      auth: { token }
    });

    this.socket.on('connect', () => {
      console.log('WebSocket connected');
    });

    this.setupEventHandlers();
  }

  subscribe(caseId: string) {
    this.socket?.emit('subscribe', { case_id: caseId });
  }

  on(event: string, handler: Function) {
    if (!this.listeners.has(event)) {
      this.listeners.set(event, new Set());
    }
    this.listeners.get(event)!.add(handler);
  }

  private setupEventHandlers() {
    const events = [
      'discovery:progress',
      'discovery:completed',
      'deficiency:analysis_progress',
      'motion:draft_progress'
    ];

    events.forEach(event => {
      this.socket?.on(event, (data) => {
        this.listeners.get(event)?.forEach(handler => handler(data));
      });
    });
  }
}

export const wsClient = new WebSocketClient();
```

### WebSocket Hooks
```typescript
// hooks/useWebSocket.ts
export const useDiscoveryProgress = (productionId: string) => {
  const [progress, setProgress] = useState<ProgressData | null>(null);

  useEffect(() => {
    const handler = (data: ProgressData) => {
      if (data.productionId === productionId) {
        setProgress(data);
      }
    };

    wsClient.on('discovery:progress', handler);

    return () => {
      wsClient.off('discovery:progress', handler);
    };
  }, [productionId]);

  return progress;
};
```

## Form Management

### Form Architecture
```typescript
// features/Motions/MotionOutlineForm.tsx
const motionOutlineSchema = z.object({
  motionType: z.enum(['summary_judgment', 'motion_to_compel']),
  party: z.enum(['plaintiff', 'defendant']),
  claims: z.array(z.string()).min(1),
  keyFacts: z.array(z.string()).min(1)
});

type MotionOutlineForm = z.infer<typeof motionOutlineSchema>;

export const MotionOutlineForm: React.FC = () => {
  const { caseId } = useCaseContext();
  const createOutline = useCreateMotionOutline();
  
  const {
    control,
    handleSubmit,
    formState: { errors }
  } = useForm<MotionOutlineForm>({
    resolver: zodResolver(motionOutlineSchema)
  });

  const onSubmit = async (data: MotionOutlineForm) => {
    await createOutline.mutateAsync({
      caseId,
      ...data
    });
  };

  return (
    <form onSubmit={handleSubmit(onSubmit)}>
      {/* Form fields */}
    </form>
  );
};
```

## Performance Optimization

### Code Splitting
```typescript
// Lazy load feature modules
const DiscoveryModule = lazy(() => 
  import('./features/Discovery')
);

const DeficiencyModule = lazy(() => 
  import('./features/Deficiency')
);

// Route configuration with lazy loading
{
  path: 'discovery',
  element: (
    <Suspense fallback={<LoadingScreen />}>
      <DiscoveryModule />
    </Suspense>
  )
}
```

### Memoization
```typescript
// components/DocumentList.tsx
export const DocumentList = memo<DocumentListProps>(({ 
  documents, 
  onSelect 
}) => {
  const sortedDocs = useMemo(() => 
    documents.sort((a, b) => 
      b.createdAt.getTime() - a.createdAt.getTime()
    ),
    [documents]
  );

  return (
    <List>
      {sortedDocs.map(doc => (
        <DocumentItem 
          key={doc.id} 
          document={doc} 
          onSelect={onSelect}
        />
      ))}
    </List>
  );
});
```

### Virtual Scrolling
```typescript
// components/LargeDocumentList.tsx
import { FixedSizeList } from 'react-window';

export const LargeDocumentList: React.FC<{ documents: Document[] }> = ({ 
  documents 
}) => {
  const Row = ({ index, style }: { index: number; style: any }) => (
    <div style={style}>
      <DocumentItem document={documents[index]} />
    </div>
  );

  return (
    <FixedSizeList
      height={600}
      itemCount={documents.length}
      itemSize={80}
      width="100%"
    >
      {Row}
    </FixedSizeList>
  );
};
```

## Testing Strategy

The frontend uses **Vitest** as the testing framework, which provides:
- Native ESM support for Vite-based projects
- Faster test execution using Vite's transformation pipeline
- Jest-compatible API for easy migration
- Built-in TypeScript support

### Component Testing
```typescript
// __tests__/DiscoveryUpload.test.tsx
import { describe, it, expect, vi } from 'vitest';

describe('DiscoveryUpload', () => {
  it('should upload files when submit is clicked', async () => {
    const mockUpload = vi.fn();
    vi.mocked(useDiscoveryUpload).mockReturnValue({
      mutateAsync: mockUpload
    });

    const { getByRole } = render(
      <CaseProvider value={mockCaseContext}>
        <DiscoveryUpload />
      </CaseProvider>
    );

    const file = new File(['test'], 'test.pdf', { type: 'application/pdf' });
    const input = getByRole('button', { name: /upload/i });
    
    fireEvent.change(input, { target: { files: [file] } });
    fireEvent.click(getByRole('button', { name: /submit/i }));

    await waitFor(() => {
      expect(mockUpload).toHaveBeenCalledWith({
        caseId: 'test-case-id',
        files: [file],
        metadata: expect.any(Object)
      });
    });
  });
});
```

### Integration Testing
```typescript
// __tests__/integration/discovery-flow.test.tsx
describe('Discovery Processing Flow', () => {
  it('should show progress updates via WebSocket', async () => {
    const { getByText, findByText } = render(<App />);
    
    // Navigate to discovery
    fireEvent.click(getByText('Discovery'));
    
    // Upload file
    // ... upload logic
    
    // Simulate WebSocket progress
    act(() => {
      mockSocket.emit('discovery:progress', {
        productionId: 'test-id',
        percentage: 50,
        message: 'Processing documents...'
      });
    });

    expect(await findByText('50%')).toBeInTheDocument();
  });
});
```

## Error Handling

### Global Error Boundary
```typescript
// components/ErrorBoundary.tsx
export class ErrorBoundary extends Component<
  { children: ReactNode },
  { hasError: boolean; error: Error | null }
> {
  state = { hasError: false, error: null };

  static getDerivedStateFromError(error: Error) {
    return { hasError: true, error };
  }

  componentDidCatch(error: Error, errorInfo: ErrorInfo) {
    console.error('Error caught by boundary:', error, errorInfo);
    // Send to error reporting service
  }

  render() {
    if (this.state.hasError) {
      return <ErrorFallback error={this.state.error} />;
    }

    return this.props.children;
  }
}
```

### API Error Handling
```typescript
// hooks/useAPIError.ts
export const useAPIError = () => {
  const { enqueueSnackbar } = useSnackbar();

  const handleError = useCallback((error: unknown) => {
    if (error instanceof APIError) {
      enqueueSnackbar(error.message, { variant: 'error' });
      
      if (error.status === 401) {
        // Handle unauthorized
        window.location.href = '/auth/login';
      }
    } else {
      enqueueSnackbar('An unexpected error occurred', { 
        variant: 'error' 
      });
    }
  }, [enqueueSnackbar]);

  return { handleError };
};
```

## Styling Architecture

### Theme Configuration
```typescript
// styles/theme.ts
export const theme = createTheme({
  palette: {
    primary: {
      main: '#1976d2',
      light: '#42a5f5',
      dark: '#1565c0'
    },
    secondary: {
      main: '#dc004e'
    },
    background: {
      default: '#f5f5f5',
      paper: '#ffffff'
    }
  },
  typography: {
    fontFamily: '"Inter", "Roboto", "Helvetica", "Arial", sans-serif',
    h1: {
      fontSize: '2.5rem',
      fontWeight: 600
    }
  },
  components: {
    MuiButton: {
      styleOverrides: {
        root: {
          textTransform: 'none',
          borderRadius: 8
        }
      }
    }
  }
});
```

### Responsive Design
```typescript
// hooks/useResponsive.ts
export const useResponsive = () => {
  const theme = useTheme();
  
  const isMobile = useMediaQuery(theme.breakpoints.down('sm'));
  const isTablet = useMediaQuery(theme.breakpoints.down('md'));
  const isDesktop = useMediaQuery(theme.breakpoints.up('lg'));

  return { isMobile, isTablet, isDesktop };
};
```

## Build & Deployment

### Build Configuration
```typescript
// vite.config.ts
export default defineConfig({
  plugins: [react()],
  build: {
    rollupOptions: {
      output: {
        manualChunks: {
          'react-vendor': ['react', 'react-dom', 'react-router-dom'],
          'mui-vendor': ['@mui/material', '@emotion/react'],
          'utils': ['lodash', 'date-fns', 'zod']
        }
      }
    },
    chunkSizeWarningLimit: 1000
  },
  optimizeDeps: {
    include: ['@mui/material', '@emotion/react']
  }
});
```

### Environment Configuration
```typescript
// config/env.ts
export const config = {
  API_URL: import.meta.env.VITE_API_URL,
  WS_URL: import.meta.env.VITE_WS_URL,
  SENTRY_DSN: import.meta.env.VITE_SENTRY_DSN,
  ENABLE_ANALYTICS: import.meta.env.VITE_ENABLE_ANALYTICS === 'true'
};
```

## Security Considerations

### Authentication
- JWT tokens stored in httpOnly cookies
- Automatic token refresh before expiration
- Logout clears all auth state

### Data Protection
- Sanitize all user inputs
- Escape HTML in rendered content
- Validate file types and sizes
- Implement CSP headers

### API Security
- HTTPS only in production
- CORS properly configured
- Rate limiting awareness
- Request signing for sensitive operations