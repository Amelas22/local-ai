import React, { useState, useEffect, useMemo } from 'react';
import {
  Box,
  Paper,
  Typography,
  Tabs,
  Tab,
  Grid,
  TextField,
  FormControl,
  InputLabel,
  Select,
  MenuItem,
  Chip,
  Button,
  Badge,
  CircularProgress,
  Alert,
  ToggleButton,
  ToggleButtonGroup,
  InputAdornment,
  IconButton,
} from '@mui/material';
import {
  Search as SearchIcon,
  CheckCircle as CheckCircleIcon,
  Cancel as CancelIcon,
  ViewModule as ViewModuleIcon,
  ViewList as ViewListIcon,
  PictureAsPdf as PdfIcon,
  Clear as ClearIcon,
} from '@mui/icons-material';
import { FactCard } from './FactCard';
import { PDFViewer } from './PDFViewer';
import { useDiscoverySocket } from '../../hooks/useDiscoverySocket';
import { useAppSelector, useAppDispatch } from '../../hooks/redux';
import { useCaseManagement } from '../../hooks/useCaseManagement';
import { discoveryService } from '../../services/discoveryService';
import { showNotification } from '../../store/slices/uiSlice';
import { setExtractedFacts, updateExtractedFact } from '../../store/slices/discoverySlice';
import { 
  ExtractedFactWithSource, 
  FactSearchRequest,
  DiscoveryDocument 
} from '../../types/discovery.types';

export const FactReviewPanel: React.FC = () => {
  const [selectedTab, setSelectedTab] = useState(0);
  const [viewMode, setViewMode] = useState<'grid' | 'list'>('grid');
  const [searchQuery, setSearchQuery] = useState('');
  const [categoryFilter, setCategoryFilter] = useState<string>('all');
  const [confidenceFilter, setConfidenceFilter] = useState<number>(0);
  const [reviewFilter, setReviewFilter] = useState<string>('all');
  const [selectedFact, setSelectedFact] = useState<ExtractedFactWithSource | null>(null);
  const [selectedDocument, setSelectedDocument] = useState<DiscoveryDocument | null>(null);
  const [isLoading, setIsLoading] = useState(false);
  
  const dispatch = useAppDispatch();
  const { selectedCase } = useCaseManagement();
  const { extractedFacts, processingDocuments } = useAppSelector(state => state.discovery);
  const { updateFact, deleteFact, isConnected } = useDiscoverySocket({
    caseId: selectedCase?.case_name,
  });

  const categories = useMemo(() => {
    const cats = new Set(extractedFacts.map(f => f.category));
    return ['all', ...Array.from(cats)];
  }, [extractedFacts]);

  const documentTabs = useMemo(() => {
    const uniqueDocs = new Map<string, DiscoveryDocument>();
    
    processingDocuments.forEach(doc => {
      if (doc.status === 'completed') {
        uniqueDocs.set(doc.id, {
          id: doc.id,
          title: doc.title,
          type: doc.type,
          bates_range: doc.batesRange,
          page_count: doc.pageCount,
          confidence: doc.confidence,
        });
      }
    });
    
    return Array.from(uniqueDocs.values());
  }, [processingDocuments]);

  const filteredFacts = useMemo(() => {
    let facts = extractedFacts;

    if (selectedTab > 0 && documentTabs[selectedTab - 1]) {
      const docId = documentTabs[selectedTab - 1].id;
      facts = facts.filter(f => f.source.doc_id === docId);
    }

    if (searchQuery) {
      const query = searchQuery.toLowerCase();
      facts = facts.filter(f => 
        f.content.toLowerCase().includes(query) ||
        f.entities?.some(e => e.toLowerCase().includes(query)) ||
        f.keywords?.some(k => k.toLowerCase().includes(query))
      );
    }

    if (categoryFilter !== 'all') {
      facts = facts.filter(f => f.category === categoryFilter);
    }

    if (confidenceFilter > 0) {
      facts = facts.filter(f => f.confidence >= confidenceFilter);
    }

    if (reviewFilter !== 'all') {
      facts = facts.filter(f => f.review_status === reviewFilter);
    }

    return facts;
  }, [extractedFacts, selectedTab, documentTabs, searchQuery, categoryFilter, confidenceFilter, reviewFilter]);

  const getReviewStats = () => {
    const total = filteredFacts.length;
    const reviewed = filteredFacts.filter(f => f.review_status === 'reviewed').length;
    const rejected = filteredFacts.filter(f => f.review_status === 'rejected').length;
    const pending = total - reviewed - rejected;
    
    return { total, reviewed, rejected, pending };
  };

  const stats = getReviewStats();

  const loadFacts = async () => {
    if (!selectedCase) return;
    
    setIsLoading(true);
    try {
      const searchRequest: FactSearchRequest = {
        case_name: selectedCase.case_name,
        limit: 1000,
      };
      
      const response = await discoveryService.searchFacts(searchRequest);
      dispatch(setExtractedFacts(response.facts));
    } catch (error: any) {
      dispatch(showNotification({
        message: 'Failed to load facts',
        severity: 'error',
      }));
    } finally {
      setIsLoading(false);
    }
  };

  useEffect(() => {
    loadFacts();
  }, [selectedCase]);

  const handleTabChange = (_: React.SyntheticEvent, newValue: number) => {
    setSelectedTab(newValue);
  };

  const handleFactSelect = (fact: ExtractedFactWithSource) => {
    setSelectedFact(fact);
    
    const doc = documentTabs.find(d => d.id === fact.source.doc_id);
    if (doc) {
      setSelectedDocument(doc);
    }
  };

  const handleFactUpdate = async (fact: ExtractedFactWithSource, newContent: string, reason?: string) => {
    try {
      await updateFact(fact.id, newContent, reason);
      dispatch(updateExtractedFact({
        id: fact.id,
        content: newContent,
        is_edited: true,
      }));
      dispatch(showNotification({
        message: 'Fact updated successfully',
        severity: 'success',
      }));
    } catch (error: any) {
      dispatch(showNotification({
        message: error.message || 'Failed to update fact',
        severity: 'error',
      }));
    }
  };

  const handleFactDelete = async (fact: ExtractedFactWithSource) => {
    try {
      await deleteFact(fact.id);
      dispatch(showNotification({
        message: 'Fact deleted successfully',
        severity: 'success',
      }));
    } catch (error: any) {
      dispatch(showNotification({
        message: error.message || 'Failed to delete fact',
        severity: 'error',
      }));
    }
  };

  const handleBulkReview = async () => {
    const pendingFacts = filteredFacts.filter(f => f.review_status === 'pending');
    if (pendingFacts.length === 0) return;

    try {
      const result = await discoveryService.markFactsReviewed(pendingFacts.map(f => f.id));
      dispatch(showNotification({
        message: `Marked ${result.updated} facts as reviewed`,
        severity: 'success',
      }));
      loadFacts();
    } catch (error: any) {
      dispatch(showNotification({
        message: 'Failed to mark facts as reviewed',
        severity: 'error',
      }));
    }
  };

  if (!isConnected) {
    return (
      <Alert severity="warning">
        Connecting to server... Please wait.
      </Alert>
    );
  }

  return (
    <Grid container spacing={2} sx={{ height: 'calc(100vh - 200px)' }}>
      <Grid item xs={12} md={selectedFact ? 6 : 12}>
        <Paper sx={{ p: 2, height: '100%', display: 'flex', flexDirection: 'column' }}>
          <Box sx={{ mb: 2 }}>
            <Typography variant="h5" gutterBottom>
              Fact Review
            </Typography>
            
            <Box sx={{ display: 'flex', gap: 1, mb: 2 }}>
              <Chip
                label={`Total: ${stats.total}`}
                size="small"
              />
              <Chip
                icon={<CheckCircleIcon />}
                label={`Reviewed: ${stats.reviewed}`}
                color="success"
                size="small"
              />
              <Chip
                icon={<CancelIcon />}
                label={`Rejected: ${stats.rejected}`}
                color="error"
                size="small"
              />
              <Chip
                label={`Pending: ${stats.pending}`}
                color="warning"
                size="small"
              />
            </Box>

            <Grid container spacing={2} alignItems="center">
              <Grid item xs={12} md={4}>
                <TextField
                  fullWidth
                  size="small"
                  placeholder="Search facts..."
                  value={searchQuery}
                  onChange={(e) => setSearchQuery(e.target.value)}
                  InputProps={{
                    startAdornment: (
                      <InputAdornment position="start">
                        <SearchIcon />
                      </InputAdornment>
                    ),
                    endAdornment: searchQuery && (
                      <InputAdornment position="end">
                        <IconButton size="small" onClick={() => setSearchQuery('')}>
                          <ClearIcon />
                        </IconButton>
                      </InputAdornment>
                    ),
                  }}
                />
              </Grid>
              
              <Grid item xs={6} md={2}>
                <FormControl fullWidth size="small">
                  <InputLabel>Category</InputLabel>
                  <Select
                    value={categoryFilter}
                    onChange={(e) => setCategoryFilter(e.target.value)}
                    label="Category"
                  >
                    {categories.map(cat => (
                      <MenuItem key={cat} value={cat}>
                        {cat === 'all' ? 'All Categories' : cat}
                      </MenuItem>
                    ))}
                  </Select>
                </FormControl>
              </Grid>
              
              <Grid item xs={6} md={2}>
                <FormControl fullWidth size="small">
                  <InputLabel>Status</InputLabel>
                  <Select
                    value={reviewFilter}
                    onChange={(e) => setReviewFilter(e.target.value)}
                    label="Status"
                  >
                    <MenuItem value="all">All</MenuItem>
                    <MenuItem value="pending">Pending</MenuItem>
                    <MenuItem value="reviewed">Reviewed</MenuItem>
                    <MenuItem value="rejected">Rejected</MenuItem>
                  </Select>
                </FormControl>
              </Grid>
              
              <Grid item xs={6} md={2}>
                <FormControl fullWidth size="small">
                  <InputLabel>Min Confidence</InputLabel>
                  <Select
                    value={confidenceFilter}
                    onChange={(e) => setConfidenceFilter(Number(e.target.value))}
                    label="Min Confidence"
                  >
                    <MenuItem value={0}>Any</MenuItem>
                    <MenuItem value={0.5}>50%+</MenuItem>
                    <MenuItem value={0.7}>70%+</MenuItem>
                    <MenuItem value={0.9}>90%+</MenuItem>
                  </Select>
                </FormControl>
              </Grid>
              
              <Grid item xs={6} md={2}>
                <Box sx={{ display: 'flex', gap: 1 }}>
                  <ToggleButtonGroup
                    value={viewMode}
                    exclusive
                    onChange={(_, mode) => mode && setViewMode(mode)}
                    size="small"
                  >
                    <ToggleButton value="grid">
                      <ViewModuleIcon />
                    </ToggleButton>
                    <ToggleButton value="list">
                      <ViewListIcon />
                    </ToggleButton>
                  </ToggleButtonGroup>
                  
                  <Button
                    variant="outlined"
                    size="small"
                    onClick={handleBulkReview}
                    disabled={stats.pending === 0}
                  >
                    Review All
                  </Button>
                </Box>
              </Grid>
            </Grid>
          </Box>

          <Tabs
            value={selectedTab}
            onChange={handleTabChange}
            variant="scrollable"
            scrollButtons="auto"
            sx={{ borderBottom: 1, borderColor: 'divider' }}
          >
            <Tab 
              label={
                <Badge badgeContent={extractedFacts.length} color="primary">
                  All Documents
                </Badge>
              } 
            />
            {documentTabs.map((doc) => (
              <Tab
                key={doc.id}
                icon={<PdfIcon />}
                label={
                  <Badge 
                    badgeContent={extractedFacts.filter(f => f.source.doc_id === doc.id).length} 
                    color="secondary"
                  >
                    {doc.title}
                  </Badge>
                }
              />
            ))}
          </Tabs>

          <Box sx={{ flexGrow: 1, overflow: 'auto', mt: 2 }}>
            {isLoading ? (
              <Box sx={{ display: 'flex', justifyContent: 'center', p: 4 }}>
                <CircularProgress />
              </Box>
            ) : filteredFacts.length === 0 ? (
              <Alert severity="info">
                No facts found matching your filters.
              </Alert>
            ) : (
              <Grid container spacing={2}>
                {filteredFacts.map((fact) => (
                  <Grid 
                    item 
                    xs={12} 
                    sm={viewMode === 'grid' ? 6 : 12} 
                    lg={viewMode === 'grid' ? 4 : 12}
                    key={fact.id}
                  >
                    <FactCard
                      fact={fact}
                      viewMode={viewMode}
                      onSelect={handleFactSelect}
                      onUpdate={handleFactUpdate}
                      onDelete={handleFactDelete}
                      isSelected={selectedFact?.id === fact.id}
                    />
                  </Grid>
                ))}
              </Grid>
            )}
          </Box>
        </Paper>
      </Grid>

      {selectedFact && selectedDocument && (
        <Grid item xs={12} md={6}>
          <Paper sx={{ p: 2, height: '100%' }}>
            <Typography variant="h6" gutterBottom>
              Source Document
            </Typography>
            <PDFViewer
              document={selectedDocument}
              highlightedFact={selectedFact}
              onFactClick={handleFactSelect}
            />
          </Paper>
        </Grid>
      )}
    </Grid>
  );
};