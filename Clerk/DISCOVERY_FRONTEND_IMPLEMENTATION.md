# Discovery Processing Frontend Implementation

## Overview
This document summarizes the frontend implementation for the enhanced discovery processing feature that displays document processing progress in real-time with a tab-based interface.

## Key Components Created

### 1. DocumentProcessingTab Component
**File**: `/frontend/src/components/discovery/DocumentProcessingTab.tsx`

This component displays the processing status and extracted facts for a single document within a tab.

**Features**:
- Shows document metadata (title, type, Bates range, pages)
- Real-time processing progress with stage indicators
- Displays extracted facts as they arrive via WebSocket
- Integrates with existing FactCard component for fact display
- Shows appropriate loading states during processing
- Error handling and display

### 2. EnhancedFactReviewPanel Component
**File**: `/frontend/src/components/discovery/EnhancedFactReviewPanel.tsx`

An enhanced version of the fact review panel that integrates document processing visualization.

**Features**:
- Tab-based interface with "All Documents" tab and individual document tabs
- Real-time status badges on tabs (processing, completed, error)
- Fact count badges per document
- Overall processing progress display
- Filtering and search capabilities
- Side-by-side PDF viewer integration
- Grid/List view toggle for facts

### 3. EnhancedDiscoveryProcessing Page
**File**: `/frontend/src/pages/EnhancedDiscoveryProcessing.tsx`

Updated page component that combines processing visualization with fact review.

**Features**:
- Simplified 2-step workflow (Upload → Processing & Review)
- Shows processing visualization and fact review simultaneously
- Real-time statistics display
- Option to hide/show processing visualization
- Seamless transition from processing to review

### 4. Enhanced WebSocket Hook
**File**: `/frontend/src/hooks/useEnhancedDiscoverySocket.ts`

Improved WebSocket event handling for per-document processing status.

**Features**:
- Tracks processing stage per document
- Maps backend events to frontend state updates
- Handles document-level progress tracking
- Maintains global processing stage based on all documents
- Enhanced error handling per document

## Integration Points

### Existing Components Used
1. **FactCard** - For displaying individual facts with edit/delete capabilities
2. **PDFViewer** - For showing source documents with fact highlighting
3. **ProcessingVisualization** - For overall processing progress display
4. **DiscoveryUpload** - For file upload interface

### Redux State Management
The implementation leverages the existing `discoverySlice` which already supports:
- Per-document status tracking
- Fact management (add, update, delete)
- Processing statistics
- WebSocket event handling

### WebSocket Events
The frontend now properly handles these discovery events:
- `discovery:started` - Initialize processing
- `discovery:document_found` - Add document to tabs
- `discovery:document_processing` - Update document status
- `discovery:chunking` - Show chunking progress
- `discovery:embedding` - Show embedding progress
- `discovery:fact_extracted` - Add facts in real-time
- `discovery:document_completed` - Mark document as complete
- `discovery:completed` - Finalize processing
- `discovery:error` - Handle errors per document

## User Experience Flow

1. **Upload Phase**
   - User selects PDF files for discovery processing
   - Can specify producing party and production batch

2. **Processing Phase**
   - Documents appear as tabs as they're discovered
   - Each tab shows real-time processing progress
   - Facts appear within each document's tab as extracted
   - Overall progress shown at the top

3. **Review Phase**
   - All facts available for review and editing
   - Can filter by document, category, confidence
   - Click facts to view source in PDF viewer
   - Bulk operations available

## Key Features Implemented

1. **Real-time Updates**
   - Documents appear as discovered
   - Processing progress per document
   - Facts stream in as extracted
   - Status badges update automatically

2. **Tab Management**
   - Dynamic tab creation for each document
   - Badge indicators for status and fact count
   - Smooth transitions between tabs
   - Persistent state during processing

3. **Fact Management**
   - Edit facts inline with reason tracking
   - Delete facts with confirmation
   - Review status management
   - Source document linking

4. **Error Handling**
   - Per-document error display
   - Graceful failure handling
   - Continue processing other documents on error

## Backend Integration Requirements

For this frontend to work properly, the backend must emit WebSocket events in this format:

```javascript
// Document found
{
  processing_id: string,
  document_id: string,
  title: string,
  type: string,
  pages: string, // "1-10"
  bates_range: string,
  confidence: number
}

// Fact extracted
{
  processing_id: string,
  document_id: string,
  fact: {
    fact_id: string,
    text: string,
    category: string,
    confidence: number,
    entities: string[],
    dates: string[],
    source_metadata: {...}
  }
}

// Processing complete
{
  processing_id: string,
  total_documents_found: number,
  documents_processed: number,
  facts_extracted: number,
  errors: []
}
```

## Testing Recommendations

1. **Unit Tests**
   - Test DocumentProcessingTab with various processing states
   - Test fact filtering and search in EnhancedFactReviewPanel
   - Test WebSocket event handlers

2. **Integration Tests**
   - Test full workflow from upload to fact review
   - Test error scenarios (document processing failure)
   - Test concurrent document processing

3. **E2E Tests**
   - Upload multi-document PDF
   - Verify tabs appear for each document
   - Verify facts appear in real-time
   - Test fact editing and deletion

## Performance Considerations

1. **Lazy Loading**
   - Only render visible tab content
   - Virtualize fact lists for large datasets

2. **Debouncing**
   - Debounce search input
   - Batch WebSocket updates

3. **Memory Management**
   - Clear completed document data after review
   - Limit fact history storage

## Future Enhancements

1. **Export Functionality**
   - Export facts by document
   - Generate fact summaries

2. **Advanced Filtering**
   - Date range filters
   - Multi-select categories
   - Saved filter presets

3. **Collaboration**
   - Real-time multi-user fact review
   - Comment threads on facts
   - Assignment workflow

## Usage

To use the enhanced discovery processing:

1. Import the enhanced page component:
```typescript
import EnhancedDiscoveryProcessing from './pages/EnhancedDiscoveryProcessing';
```

2. Update your routes to use the new component:
```typescript
<Route path="/discovery" element={<EnhancedDiscoveryProcessing />} />
```

3. Ensure WebSocket connection is established before processing

The implementation is now ready for testing with the updated backend that properly splits documents and emits granular processing events.