# Coding Standards and Conventions

## Existing Standards Compliance
- **Code Style:** PEP8 with type hints, formatted with ruff
- **Linting Rules:** ruff check . (configured in project)
- **Testing Patterns:** pytest with co-located tests in tests/ subdirectories
- **Documentation Style:** Google-style docstrings for all functions

## Critical Integration Rules
- **Existing API Compatibility:** Never modify existing discovery endpoints - only extend
- **Database Integration:** Always use case_name for filtering - no cross-case queries
- **Error Handling:** Use existing exception patterns with detailed logging
- **Logging Consistency:** Use logger = logging.getLogger("clerk_api") pattern

## Code Examples Following Standards

**Python Code Pattern:**
```python
from typing import List, Optional
from pydantic import BaseModel
from src.utils.logger import get_logger

logger = get_logger("clerk_api")

class DeficiencyAnalyzer:
    """
    AI agent for analyzing RTP requests against discovery productions.
    
    Attributes:
        case_name (str): Case identifier for isolation.
        confidence_threshold (float): Minimum confidence for classifications.
    """
    
    async def analyze_rtp_item(
        self, 
        request: RTPRequest, 
        case_name: str
    ) -> DeficiencyClassification:
        """
        Analyze a single RTP request against production documents.
        
        Args:
            request (RTPRequest): The RTP request to analyze.
            case_name (str): Case name for document isolation.
            
        Returns:
            DeficiencyClassification: Analysis result with evidence.
            
        Raises:
            AnalysisTimeoutError: If analysis exceeds time limit.
        """
        # Implementation follows KISS principle
        pass
```

**React/TypeScript Pattern:**
```typescript
import { useState, useEffect } from 'react';
import { useWebSocket } from '@/hooks/useWebSocket';
import { DeficiencyReport } from '@/types/deficiency.types';

export const DeficiencyReportView: React.FC<{ reportId: string }> = ({ reportId }) => {
  const [report, setReport] = useState<DeficiencyReport | null>(null);
  const { emit, on } = useWebSocket();
  
  useEffect(() => {
    // Follow existing WebSocket patterns
    const handleUpdate = (data: DeficiencyReport) => {
      setReport(data);
    };
    
    on('deficiency:report_updated', handleUpdate);
    return () => off('deficiency:report_updated', handleUpdate);
  }, [reportId]);
  
  // Component implementation
};
```

**Testing Pattern:**
```python
import pytest
from unittest.mock import Mock, patch
from src.ai_agents.deficiency_analyzer import DeficiencyAnalyzer

class TestDeficiencyAnalyzer:
    """Test suite for DeficiencyAnalyzer following existing patterns."""
    
    @pytest.fixture
    def analyzer(self):
        """Create analyzer instance for testing."""
        return DeficiencyAnalyzer(
            case_name="test_case",
            confidence_threshold=0.7
        )
    
    async def test_analyze_rtp_item_success(self, analyzer):
        """Test successful RTP item analysis."""
        # Arrange
        request = RTPRequest(
            number="RFP No. 1",
            text="All medical records"
        )
        
        # Act
        result = await analyzer.analyze_rtp_item(request, "test_case")
        
        # Assert
        assert result.classification in ["fully_produced", "partially_produced", "not_produced", "no_responsive_docs"]
        assert 0 <= result.confidence_score <= 1
```
