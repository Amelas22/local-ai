import React, { useState, useEffect } from 'react';
import {
  Box,
  Table,
  TableBody,
  TableCell,
  TableContainer,
  TableHead,
  TableRow,
  Paper,
  Chip,
  IconButton,
  TextField,
  InputAdornment,
  Typography,
  Tooltip,
  CircularProgress,
} from '@mui/material';
import SearchIcon from '@mui/icons-material/Search';
import RefreshIcon from '@mui/icons-material/Refresh';
import DownloadIcon from '@mui/icons-material/Download';
import VisibilityIcon from '@mui/icons-material/Visibility';
import { format } from 'date-fns';
import { useAppDispatch } from '@/hooks/redux';
import { addToast } from '@/store/slices/uiSlice';

interface ProductionRecord {
  id: string;
  caseId: string;
  caseName: string;
  productionBatch: string;
  producingParty: string;
  productionDate: string;
  processingDate: string;
  documentsCount: number;
  chunksCount: number;
  status: 'completed' | 'failed' | 'processing';
  responsiveToRequests: string[];
  confidentialityDesignation?: string;
  processingTime?: number;
}

const ProductionHistory: React.FC = () => {
  const dispatch = useAppDispatch();
  const [productions, setProductions] = useState<ProductionRecord[]>([]);
  const [loading, setLoading] = useState(true);
  const [searchTerm, setSearchTerm] = useState('');
  const [filteredProductions, setFilteredProductions] = useState<ProductionRecord[]>([]);

  const fetchProductionHistory = async () => {
    setLoading(true);
    try {
      // TODO: Replace with actual API endpoint when available
      const mockData: ProductionRecord[] = [
        {
          id: '1',
          caseId: 'case_001',
          caseName: 'Smith_v_Jones_2024',
          productionBatch: "Defendant's First Production",
          producingParty: 'ABC Transport Corp',
          productionDate: '2024-01-15T00:00:00Z',
          processingDate: '2024-01-16T10:30:00Z',
          documentsCount: 150,
          chunksCount: 4500,
          status: 'completed',
          responsiveToRequests: ['RFP 1-25', 'RFA 1-15'],
          confidentialityDesignation: 'Confidential',
          processingTime: 1845,
        },
        {
          id: '2',
          caseId: 'case_002',
          caseName: 'Johnson_v_ABC_Corp_2024',
          productionBatch: "Plaintiff's Second Production",
          producingParty: 'Johnson Legal Team',
          productionDate: '2024-01-10T00:00:00Z',
          processingDate: '2024-01-11T14:20:00Z',
          documentsCount: 75,
          chunksCount: 2100,
          status: 'completed',
          responsiveToRequests: ['RFP 26-50'],
          processingTime: 920,
        },
      ];
      
      setProductions(mockData);
      setFilteredProductions(mockData);
    } catch (error) {
      dispatch(addToast({
        message: 'Failed to fetch production history',
        severity: 'error',
      }));
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    fetchProductionHistory();
  }, []);

  useEffect(() => {
    const filtered = productions.filter((prod) =>
      prod.caseName.toLowerCase().includes(searchTerm.toLowerCase()) ||
      prod.productionBatch.toLowerCase().includes(searchTerm.toLowerCase()) ||
      prod.producingParty.toLowerCase().includes(searchTerm.toLowerCase())
    );
    setFilteredProductions(filtered);
  }, [searchTerm, productions]);

  const getStatusColor = (status: string) => {
    switch (status) {
      case 'completed':
        return 'success';
      case 'processing':
        return 'info';
      case 'failed':
        return 'error';
      default:
        return 'default';
    }
  };

  const formatProcessingTime = (seconds?: number) => {
    if (!seconds) return '-';
    const minutes = Math.floor(seconds / 60);
    const remainingSeconds = seconds % 60;
    return `${minutes}m ${remainingSeconds}s`;
  };

  if (loading) {
    return (
      <Box sx={{ display: 'flex', justifyContent: 'center', py: 4 }}>
        <CircularProgress />
      </Box>
    );
  }

  return (
    <Box>
      <Box sx={{ mb: 3, display: 'flex', alignItems: 'center', gap: 2 }}>
        <TextField
          placeholder="Search productions..."
          size="small"
          value={searchTerm}
          onChange={(e) => setSearchTerm(e.target.value)}
          sx={{ flexGrow: 1, maxWidth: 400 }}
          InputProps={{
            startAdornment: (
              <InputAdornment position="start">
                <SearchIcon />
              </InputAdornment>
            ),
          }}
        />
        <Tooltip title="Refresh">
          <IconButton onClick={fetchProductionHistory}>
            <RefreshIcon />
          </IconButton>
        </Tooltip>
      </Box>

      <TableContainer component={Paper}>
        <Table>
          <TableHead>
            <TableRow>
              <TableCell>Case</TableCell>
              <TableCell>Production Batch</TableCell>
              <TableCell>Producing Party</TableCell>
              <TableCell>Production Date</TableCell>
              <TableCell>Processing Date</TableCell>
              <TableCell align="center">Documents</TableCell>
              <TableCell align="center">Chunks</TableCell>
              <TableCell align="center">Time</TableCell>
              <TableCell align="center">Status</TableCell>
              <TableCell align="center">Actions</TableCell>
            </TableRow>
          </TableHead>
          <TableBody>
            {filteredProductions.length === 0 ? (
              <TableRow>
                <TableCell colSpan={10} align="center">
                  <Typography color="text.secondary" sx={{ py: 4 }}>
                    No production history found
                  </Typography>
                </TableCell>
              </TableRow>
            ) : (
              filteredProductions.map((prod) => (
                <TableRow key={prod.id} hover>
                  <TableCell>{prod.caseName}</TableCell>
                  <TableCell>{prod.productionBatch}</TableCell>
                  <TableCell>{prod.producingParty}</TableCell>
                  <TableCell>
                    {format(new Date(prod.productionDate), 'MMM d, yyyy')}
                  </TableCell>
                  <TableCell>
                    {format(new Date(prod.processingDate), 'MMM d, yyyy h:mm a')}
                  </TableCell>
                  <TableCell align="center">{prod.documentsCount}</TableCell>
                  <TableCell align="center">{prod.chunksCount}</TableCell>
                  <TableCell align="center">
                    {formatProcessingTime(prod.processingTime)}
                  </TableCell>
                  <TableCell align="center">
                    <Chip
                      label={prod.status}
                      size="small"
                      color={getStatusColor(prod.status)}
                    />
                  </TableCell>
                  <TableCell align="center">
                    <Box sx={{ display: 'flex', gap: 0.5, justifyContent: 'center' }}>
                      <Tooltip title="View Details">
                        <IconButton size="small">
                          <VisibilityIcon fontSize="small" />
                        </IconButton>
                      </Tooltip>
                      <Tooltip title="Download Report">
                        <IconButton size="small">
                          <DownloadIcon fontSize="small" />
                        </IconButton>
                      </Tooltip>
                    </Box>
                  </TableCell>
                </TableRow>
              ))
            )}
          </TableBody>
        </Table>
      </TableContainer>
    </Box>
  );
};

export default ProductionHistory;