import React, { useState, useEffect, useCallback } from 'react';
import { Worker, Viewer } from '@react-pdf-viewer/core';
import { defaultLayoutPlugin } from '@react-pdf-viewer/default-layout';
import { highlightPlugin, HighlightArea } from '@react-pdf-viewer/highlight';
import { pageNavigationPlugin } from '@react-pdf-viewer/page-navigation';
import '@react-pdf-viewer/core/lib/styles/index.css';
import '@react-pdf-viewer/default-layout/lib/styles/index.css';
import '@react-pdf-viewer/highlight/lib/styles/index.css';
import {
  Box,
  CircularProgress,
  Alert,
  Paper,
  Typography,
  IconButton,
  Tooltip,
  Chip,
  Stack,
} from '@mui/material';
import {
  ZoomIn as ZoomInIcon,
  ZoomOut as ZoomOutIcon,
  FitScreen as FitScreenIcon,
  NavigateBefore as PrevIcon,
  NavigateNext as NextIcon,
} from '@mui/icons-material';
import { discoveryService } from '../../services/discoveryService';
import { ExtractedFactWithSource, DiscoveryDocument } from '../../types/discovery.types';

interface PDFViewerProps {
  document: DiscoveryDocument;
  highlightedFact?: ExtractedFactWithSource;
  onFactClick?: (fact: ExtractedFactWithSource) => void;
  relatedFacts?: ExtractedFactWithSource[];
}

interface FactHighlight {
  factId: string;
  areas: HighlightArea[];
  color: string;
  fact: ExtractedFactWithSource;
}

export const PDFViewer: React.FC<PDFViewerProps> = ({
  document,
  highlightedFact,
  onFactClick,
  relatedFacts = [],
}) => {
  const [pdfUrl, setPdfUrl] = useState<string | null>(null);
  const [isLoading, setIsLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [currentPage, setCurrentPage] = useState(0);
  const [totalPages, setTotalPages] = useState(0);
  const [scale, setScale] = useState(1.0);
  const [highlights, setHighlights] = useState<FactHighlight[]>([]);

  const defaultLayoutPluginInstance = defaultLayoutPlugin({
    sidebarTabs: () => [],
  });

  const pageNavigationPluginInstance = pageNavigationPlugin();
  const { jumpToPage } = pageNavigationPluginInstance;

  const renderHighlight = useCallback((highlight: FactHighlight) => (
    <Box
      sx={{
        backgroundColor: highlight.color,
        opacity: 0.4,
        cursor: 'pointer',
        '&:hover': {
          opacity: 0.6,
        },
      }}
      onClick={() => onFactClick?.(highlight.fact)}
    >
      <Tooltip title={highlight.fact.content}>
        <span />
      </Tooltip>
    </Box>
  ), [onFactClick]);

  const highlightPluginInstance = highlightPlugin({
    renderHighlights: (props) => (
      <>
        {highlights
          .filter(h => h.areas.some(a => a.pageIndex === props.pageIndex))
          .map(highlight => {
            const areas = highlight.areas.filter(a => a.pageIndex === props.pageIndex);
            return areas.map((area, idx) => (
              <div
                key={`${highlight.factId}-${idx}`}
                style={{
                  position: 'absolute',
                  left: `${area.left}%`,
                  top: `${area.top}%`,
                  width: `${area.width}%`,
                  height: `${area.height}%`,
                }}
              >
                {renderHighlight(highlight)}
              </div>
            ));
          })}
      </>
    ),
  });

  useEffect(() => {
    const loadPdf = async () => {
      setIsLoading(true);
      setError(null);
      
      try {
        if (document.file_path) {
          setPdfUrl(document.file_path);
        } else if (document.box_file_id) {
          const blob = await discoveryService.getDocumentPdf(document.id);
          const url = URL.createObjectURL(blob);
          setPdfUrl(url);
        } else {
          throw new Error('No PDF source available');
        }
      } catch (err: any) {
        setError(err.message || 'Failed to load PDF');
      } finally {
        setIsLoading(false);
      }
    };

    loadPdf();

    return () => {
      if (pdfUrl && pdfUrl.startsWith('blob:')) {
        URL.revokeObjectURL(pdfUrl);
      }
    };
  }, [document]);

  useEffect(() => {
    const newHighlights: FactHighlight[] = [];

    if (highlightedFact && highlightedFact.source.doc_id === document.id) {
      const bbox = highlightedFact.source.bbox;
      if (bbox && bbox.length === 4) {
        newHighlights.push({
          factId: highlightedFact.id,
          areas: [{
            pageIndex: highlightedFact.source.page - 1,
            left: bbox[0],
            top: bbox[1],
            width: bbox[2] - bbox[0],
            height: bbox[3] - bbox[1],
          }],
          color: '#FFD700',
          fact: highlightedFact,
        });
      }
    }

    relatedFacts
      .filter(fact => fact.source.doc_id === document.id)
      .forEach(fact => {
        const bbox = fact.source.bbox;
        if (bbox && bbox.length === 4) {
          newHighlights.push({
            factId: fact.id,
            areas: [{
              pageIndex: fact.source.page - 1,
              left: bbox[0],
              top: bbox[1],
              width: bbox[2] - bbox[0],
              height: bbox[3] - bbox[1],
            }],
            color: fact.id === highlightedFact?.id ? '#FFD700' : '#87CEEB',
            fact: fact,
          });
        }
      });

    setHighlights(newHighlights);

    if (highlightedFact && highlightedFact.source.doc_id === document.id) {
      setTimeout(() => {
        jumpToPage(highlightedFact.source.page - 1);
      }, 500);
    }
  }, [highlightedFact, relatedFacts, document, jumpToPage]);

  const handleDocumentLoad = (e: any) => {
    setTotalPages(e.doc.numPages);
  };

  const handlePageChange = (e: any) => {
    setCurrentPage(e.currentPage);
  };

  const handleZoomIn = () => {
    setScale(prev => Math.min(prev + 0.25, 3));
  };

  const handleZoomOut = () => {
    setScale(prev => Math.max(prev - 0.25, 0.5));
  };

  const handleFitScreen = () => {
    setScale(1.0);
  };

  const navigateToPrevPage = () => {
    if (currentPage > 0) {
      jumpToPage(currentPage - 1);
    }
  };

  const navigateToNextPage = () => {
    if (currentPage < totalPages - 1) {
      jumpToPage(currentPage + 1);
    }
  };

  if (isLoading) {
    return (
      <Box sx={{ display: 'flex', justifyContent: 'center', p: 4 }}>
        <CircularProgress />
      </Box>
    );
  }

  if (error) {
    return (
      <Alert severity="error" sx={{ m: 2 }}>
        {error}
      </Alert>
    );
  }

  if (!pdfUrl) {
    return (
      <Alert severity="info" sx={{ m: 2 }}>
        No PDF available for this document
      </Alert>
    );
  }

  return (
    <Box sx={{ height: '100%', display: 'flex', flexDirection: 'column' }}>
      <Paper sx={{ p: 1, display: 'flex', alignItems: 'center', gap: 2 }}>
        <Stack direction="row" spacing={1} sx={{ flexGrow: 1 }}>
          <Chip
            label={document.title}
            size="small"
            icon={<span>📄</span>}
          />
          {document.bates_range && (
            <Chip
              label={`Bates: ${document.bates_range.start} - ${document.bates_range.end}`}
              size="small"
              variant="outlined"
            />
          )}
          <Chip
            label={`Page ${currentPage + 1} of ${totalPages}`}
            size="small"
            color="primary"
          />
          {highlights.length > 0 && (
            <Chip
              label={`${highlights.length} highlights`}
              size="small"
              color="secondary"
            />
          )}
        </Stack>

        <Box sx={{ display: 'flex', gap: 1 }}>
          <Tooltip title="Previous page">
            <IconButton
              size="small"
              onClick={navigateToPrevPage}
              disabled={currentPage === 0}
            >
              <PrevIcon />
            </IconButton>
          </Tooltip>
          
          <Tooltip title="Next page">
            <IconButton
              size="small"
              onClick={navigateToNextPage}
              disabled={currentPage === totalPages - 1}
            >
              <NextIcon />
            </IconButton>
          </Tooltip>

          <Box sx={{ width: 1, bgcolor: 'divider' }} />

          <Tooltip title="Zoom out">
            <IconButton size="small" onClick={handleZoomOut}>
              <ZoomOutIcon />
            </IconButton>
          </Tooltip>
          
          <Typography variant="body2" sx={{ display: 'flex', alignItems: 'center', px: 1 }}>
            {Math.round(scale * 100)}%
          </Typography>
          
          <Tooltip title="Zoom in">
            <IconButton size="small" onClick={handleZoomIn}>
              <ZoomInIcon />
            </IconButton>
          </Tooltip>
          
          <Tooltip title="Fit to screen">
            <IconButton size="small" onClick={handleFitScreen}>
              <FitScreenIcon />
            </IconButton>
          </Tooltip>
        </Box>
      </Paper>

      <Box sx={{ flexGrow: 1, overflow: 'auto', bgcolor: 'grey.100' }}>
        <Worker workerUrl="/pdf.worker.min.js">
          <Viewer
            fileUrl={pdfUrl}
            plugins={[
              defaultLayoutPluginInstance,
              highlightPluginInstance,
              pageNavigationPluginInstance,
            ]}
            defaultScale={scale}
            onDocumentLoad={handleDocumentLoad}
            onPageChange={handlePageChange}
          />
        </Worker>
      </Box>

      {highlightedFact && (
        <Paper sx={{ p: 2, mt: 1 }}>
          <Typography variant="subtitle2" gutterBottom>
            Selected Fact
          </Typography>
          <Typography variant="body2">
            {highlightedFact.content}
          </Typography>
          <Stack direction="row" spacing={1} sx={{ mt: 1 }}>
            <Chip
              label={highlightedFact.category}
              size="small"
              variant="outlined"
            />
            <Chip
              label={`${Math.round(highlightedFact.confidence * 100)}% confidence`}
              size="small"
              color="primary"
            />
          </Stack>
        </Paper>
      )}
    </Box>
  );
};