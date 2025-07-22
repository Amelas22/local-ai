# Testing Strategy

## Integration with Existing Tests
- **Existing Test Framework:** pytest with asyncio support
- **Test Organization:** Co-located tests in tests/ subdirectories
- **Coverage Requirements:** Maintain >80% coverage for new code

## New Testing Requirements

**Unit Tests for New Components:**
- **Framework:** pytest
- **Location:** src/*/tests/ following vertical slice pattern
- **Coverage Target:** 85% for critical paths
- **Integration with Existing:** Use existing fixtures and mocks

**Integration Tests:**
- **Scope:** End-to-end deficiency analysis workflow
- **Existing System Verification:** Ensure discovery pipeline unaffected
- **New Feature Testing:** Complete deficiency analysis with mock data

**Regression Testing:**
- **Existing Feature Verification:** Run full discovery test suite
- **Automated Regression Suite:** Add deficiency tests to CI/CD
- **Manual Testing Requirements:** Legal team UAT for report accuracy

## Test Implementation Examples

**Integration Test Pattern:**
```python
import pytest
from httpx import AsyncClient
from src.main import app

class TestDeficiencyIntegration:
    """Integration tests for deficiency analysis workflow."""
    
    @pytest.mark.asyncio
    async def test_complete_deficiency_workflow(self, async_client: AsyncClient):
        """Test full workflow from discovery to letter generation."""
        # Step 1: Process discovery with deficiency analysis
        response = await async_client.post(
            "/api/discovery/process-with-deficiency",
            json={
                "folder_id": "test_folder",
                "case_name": "test_case",
                "rtp_file": "base64_test_rtp",
                "oc_response_file": "base64_test_response",
                "enable_deficiency_analysis": True
            }
        )
        assert response.status_code == 200
        production_id = response.json()["production_id"]
        
        # Step 2: Wait for analysis completion (mocked)
        # Step 3: Retrieve deficiency report
        # Step 4: Generate Good Faith letter
        # Assert all steps succeed
```

**Mock Strategy:**
```python
@pytest.fixture
def mock_vector_store():
    """Mock Qdrant vector store for testing."""
    with patch("src.vector_storage.qdrant_store.QdrantVectorStore") as mock:
        mock.hybrid_search.return_value = [
            # Mock search results
        ]
        yield mock
```

## Frontend Testing Strategy

### Testing Framework
The frontend uses **Vitest** as the primary testing framework (migrated from Jest in July 2025).

**Why Vitest:**
- Native ESM support - no more `import.meta.env` compatibility issues
- Seamless integration with Vite build tool
- Faster test execution using Vite's transformation pipeline
- Jest-compatible API for easy migration
- Built-in TypeScript support without additional configuration

### Test Configuration
```typescript
// vitest.config.ts
import { defineConfig } from 'vitest/config';
import react from '@vitejs/plugin-react';
import path from 'path';

export default defineConfig({
  plugins: [react()],
  test: {
    globals: true,
    environment: 'jsdom',
    setupFiles: './src/test-setup.ts',
    css: false,
    isolate: true,
    pool: 'forks',
    env: {
      VITE_API_URL: 'http://localhost:8010',
      VITE_WS_URL: 'ws://localhost:8010',
      VITE_MVP_MODE: 'false',
      VITE_AUTH_ENABLED: 'true'
    },
    coverage: {
      reporter: ['text', 'json', 'html'],
      exclude: [
        'node_modules/',
        'src/test-setup.ts',
        '**/*.d.ts',
        '**/*.config.*',
        '**/mockData/**',
        '**/__mocks__/**'
      ]
    }
  },
  resolve: {
    alias: {
      '@': path.resolve(__dirname, './src'),
      '@components': path.resolve(__dirname, './src/components'),
      '@services': path.resolve(__dirname, './src/services'),
      // ... other aliases
    },
  },
});
```

### Frontend Test Organization
- **Unit Tests:** Co-located in `__tests__/` directories next to components
- **Integration Tests:** `src/__tests__/integration/` for workflow testing
- **Test Utilities:** `src/test-utils/` for shared testing helpers
- **Coverage Target:** 80% for components, 90% for critical business logic

### Component Testing Pattern
```typescript
// src/components/__tests__/ComponentName.test.tsx
import { describe, it, expect, vi, beforeEach } from 'vitest';
import { render, screen, waitFor } from '@testing-library/react';
import { QueryClient, QueryClientProvider } from '@tanstack/react-query';
import { ComponentName } from '../ComponentName';

// Mock dependencies
vi.mock('@/services/api/apiService');

describe('ComponentName', () => {
  let queryClient: QueryClient;

  beforeEach(() => {
    queryClient = new QueryClient({
      defaultOptions: {
        queries: { retry: false },
      },
    });
    vi.clearAllMocks();
  });

  it('should render correctly', async () => {
    render(
      <QueryClientProvider client={queryClient}>
        <ComponentName />
      </QueryClientProvider>
    );

    expect(screen.getByText('Expected Text')).toBeInTheDocument();
  });
});
```

### Mock Strategies
```typescript
// Mocking API calls
vi.mocked(apiService.getData).mockResolvedValue({ data: 'test' });

// Mocking hooks
vi.mock('@/hooks/useAuth', () => ({
  useAuth: () => ({
    user: { id: 'test-user', name: 'Test User' },
    isAuthenticated: true,
  }),
}));

// Mocking WebSocket
vi.mock('socket.io-client', () => ({
  io: () => ({
    on: vi.fn(),
    emit: vi.fn(),
    disconnect: vi.fn(),
  }),
}));
```

### Running Tests
```bash
# Run all tests
npm test

# Run tests in watch mode
npm run test:watch

# Run with coverage
npm run test:coverage

# Run with UI
npm run test:ui

# Run specific test file
npx vitest run path/to/test.tsx
```
