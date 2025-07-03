import { useEffect, useCallback } from 'react';
import { useCaseContext } from '../context/CaseContext';
import { useWebSocket } from './useWebSocket';

export function useCaseSelection() {
  const { cases, activeCase, loading, error, selectCase, refreshCases } = useCaseContext();
  const { connected, subscribedCase } = useWebSocket(activeCase || undefined);

  // Handle case switching with WebSocket resubscription
  const switchCase = useCallback((caseName: string) => {
    if (caseName === activeCase) {
      console.log(`Already on case: ${caseName}`);
      return;
    }

    console.log(`Switching from ${activeCase} to ${caseName}`);
    selectCase(caseName);
  }, [activeCase, selectCase]);

  // Ensure WebSocket subscription matches active case
  useEffect(() => {
    if (connected && activeCase && subscribedCase !== activeCase) {
      console.log(`WebSocket case mismatch. Active: ${activeCase}, Subscribed: ${subscribedCase}`);
      // This will be handled by the useWebSocket hook with the caseId parameter
    }
  }, [connected, activeCase, subscribedCase]);

  // Get case info for active case
  const activeCaseInfo = cases.find(c => c.case_name === activeCase);

  return {
    // Case list
    cases,
    casesLoading: loading,
    casesError: error,
    refreshCases,
    
    // Active case
    activeCase,
    activeCaseInfo,
    switchCase,
    
    // WebSocket status for the case
    isConnected: connected,
    subscribedCase
  };
}