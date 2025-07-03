import { createContext, useContext, useState, useEffect, ReactElement, ReactNode } from 'react';
import { useWebSocketContext } from './WebSocketContext';

// Case information interface
export interface CaseInfo {
  case_name: string;
  display_name: string;
  document_count: number;
  last_activity: string;
}

// Case context value interface
interface CaseContextValue {
  cases: CaseInfo[];
  activeCase: string | null;
  loading: boolean;
  error: string | null;
  selectCase: (caseName: string) => void;
  refreshCases: () => Promise<void>;
}

// Create context with undefined default
const CaseContext = createContext<CaseContextValue | undefined>(undefined);

// Provider props
interface CaseProviderProps {
  children: ReactNode;
}

export function CaseProvider({ children }: CaseProviderProps): ReactElement {
  const [cases, setCases] = useState<CaseInfo[]>([]);
  const [activeCase, setActiveCase] = useState<string | null>(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  
  const { subscribeToCase, unsubscribeFromCase } = useWebSocketContext();

  // Fetch available cases from the API
  const refreshCases = async () => {
    setLoading(true);
    setError(null);
    
    try {
      const response = await fetch('/api/cases');
      if (!response.ok) {
        throw new Error('Failed to fetch cases');
      }
      
      const data = await response.json();
      
      // Ensure data.cases is an array before mapping
      const cases = data.cases || [];
      if (!Array.isArray(cases)) {
        console.error('Invalid cases data received:', data);
        throw new Error('Invalid cases data format');
      }
      
      // Transform API response to CaseInfo format
      const caseList: CaseInfo[] = cases
        .map((caseData: any) => {
          // Handle both string case names and case objects
          let caseName: string;
          let documentCount = 0;
          
          if (typeof caseData === 'string') {
            caseName = caseData;
          } else if (caseData && typeof caseData === 'object') {
            // Handle case object from Qdrant
            caseName = caseData.collection_name || caseData.original_name || '';
            documentCount = caseData.points_count || caseData.vector_count || 0;
          } else {
            console.warn('Unexpected case data format:', caseData);
            return null;
          }
          
          // Ensure we have a valid case name
          if (!caseName) return null;
          
          return {
            case_name: caseName,
            display_name: caseName.replace(/_/g, ' '),
            document_count: documentCount,
            last_activity: new Date().toISOString()
          };
        })
        .filter((item): item is CaseInfo => item !== null); // Type-safe filter
      
      setCases(caseList);
      
      // Select first case if none selected
      if (!activeCase && caseList.length > 0) {
        selectCase(caseList[0].case_name);
      }
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Failed to load cases');
      console.error('Error fetching cases:', err);
    } finally {
      setLoading(false);
    }
  };

  // Select a case and update WebSocket subscription
  const selectCase = (caseName: string) => {
    if (caseName === activeCase) return;
    
    // Just set the active case - the useEffect will handle subscription
    setActiveCase(caseName);
    
    // Store in localStorage for persistence
    localStorage.setItem('activeCase', caseName);
    
    console.log(`Selected case: ${caseName}`);
  };

  // Load cases on mount
  useEffect(() => {
    refreshCases();
    
    // Restore active case from localStorage
    const storedCase = localStorage.getItem('activeCase');
    if (storedCase) {
      setActiveCase(storedCase);
    }
  }, []);

  // Handle case subscription changes
  useEffect(() => {
    if (!activeCase) return;
    
    // Subscribe to the new case
    subscribeToCase(activeCase);
    
    // Cleanup: unsubscribe when case changes or component unmounts
    return () => {
      unsubscribeFromCase();
    };
  }, [activeCase, subscribeToCase, unsubscribeFromCase]);

  const contextValue: CaseContextValue = {
    cases,
    activeCase,
    loading,
    error,
    selectCase,
    refreshCases
  };

  return (
    <CaseContext.Provider value={contextValue}>
      {children}
    </CaseContext.Provider>
  );
}

// Custom hook to use Case context
export function useCaseContext(): CaseContextValue {
  const context = useContext(CaseContext);
  if (!context) {
    throw new Error('useCaseContext must be used within a CaseProvider');
  }
  return context;
}