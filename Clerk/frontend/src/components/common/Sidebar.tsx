import { ReactElement } from 'react';
import { useNavigate, useLocation } from 'react-router-dom';
import {
  Drawer,
  List,
  ListItem,
  ListItemButton,
  ListItemIcon,
  ListItemText,
  Toolbar,
  Divider,
  Box,
  Select,
  MenuItem,
  FormControl,
  InputLabel,
  Typography,
  CircularProgress,
  Alert,
} from '@mui/material';
import DashboardIcon from '@mui/icons-material/Dashboard';
import FolderIcon from '@mui/icons-material/Folder';
import GavelIcon from '@mui/icons-material/Gavel';
import SearchIcon from '@mui/icons-material/Search';
import SettingsIcon from '@mui/icons-material/Settings';
import BusinessCenterIcon from '@mui/icons-material/BusinessCenter';
import { useAppSelector } from '@/hooks/redux';
import { useCaseSelection } from '@/hooks/useCaseSelection';
import { ConnectionStatus } from '../realtime/ConnectionStatus';

const menuItems = [
  { text: 'Dashboard', icon: <DashboardIcon />, path: '/dashboard' },
  { text: 'Discovery Processing', icon: <FolderIcon />, path: '/discovery' },
  { text: 'Motion Drafting', icon: <GavelIcon />, path: '/motion-drafting' },
  { text: 'Search', icon: <SearchIcon />, path: '/search' },
];

const Sidebar = (): ReactElement => {
  const navigate = useNavigate();
  const location = useLocation();
  const sidebarOpen = useAppSelector((state) => state.ui.sidebarOpen);
  const { 
    cases, 
    activeCase, 
    switchCase, 
    casesLoading, 
    casesError
  } = useCaseSelection();

  const drawerWidth = sidebarOpen ? 240 : 64;

  return (
    <Drawer
      variant="permanent"
      sx={{
        width: drawerWidth,
        flexShrink: 0,
        '& .MuiDrawer-paper': {
          width: drawerWidth,
          boxSizing: 'border-box',
          transition: 'width 0.3s ease',
          overflowX: 'hidden',
        },
      }}
    >
      <Toolbar />
      <Box sx={{ overflow: 'auto' }}>
        {/* Connection Status */}
        <Box sx={{ p: 2, display: 'flex', justifyContent: 'center' }}>
          <ConnectionStatus />
        </Box>
        
        {/* Case Selection */}
        {sidebarOpen && (
          <Box sx={{ px: 2, pb: 2 }}>
            <FormControl fullWidth size="small" disabled={casesLoading}>
              <InputLabel id="case-select-label">
                <Box display="flex" alignItems="center" gap={1}>
                  <BusinessCenterIcon fontSize="small" />
                  <span>Active Case</span>
                </Box>
              </InputLabel>
              <Select
                labelId="case-select-label"
                value={activeCase || ''}
                onChange={(e) => switchCase(e.target.value)}
                label="Active Case"
              >
                {casesLoading && (
                  <MenuItem disabled>
                    <CircularProgress size={20} />
                    <Typography sx={{ ml: 1 }}>Loading cases...</Typography>
                  </MenuItem>
                )}
                {!casesLoading && cases.length === 0 && (
                  <MenuItem disabled>
                    <Typography>No cases available</Typography>
                  </MenuItem>
                )}
                {cases.map((caseInfo) => (
                  <MenuItem key={caseInfo.case_name} value={caseInfo.case_name}>
                    <Box>
                      <Typography variant="body2">
                        {caseInfo.display_name}
                      </Typography>
                      <Typography variant="caption" color="text.secondary">
                        {caseInfo.document_count} documents
                      </Typography>
                    </Box>
                  </MenuItem>
                ))}
              </Select>
            </FormControl>
            
            {casesError && (
              <Alert severity="error" sx={{ mt: 1 }}>
                {casesError}
              </Alert>
            )}
          </Box>
        )}
        
        <Divider />
        
        <List>
          {menuItems.map((item) => (
            <ListItem key={item.text} disablePadding sx={{ display: 'block' }}>
              <ListItemButton
                selected={location.pathname === item.path}
                onClick={() => navigate(item.path)}
                sx={{
                  minHeight: 48,
                  justifyContent: sidebarOpen ? 'initial' : 'center',
                  px: 2.5,
                }}
              >
                <ListItemIcon
                  sx={{
                    minWidth: 0,
                    mr: sidebarOpen ? 3 : 'auto',
                    justifyContent: 'center',
                  }}
                >
                  {item.icon}
                </ListItemIcon>
                <ListItemText
                  primary={item.text}
                  sx={{ opacity: sidebarOpen ? 1 : 0 }}
                />
              </ListItemButton>
            </ListItem>
          ))}
        </List>
        <Divider />
        <List>
          <ListItem disablePadding sx={{ display: 'block' }}>
            <ListItemButton
              sx={{
                minHeight: 48,
                justifyContent: sidebarOpen ? 'initial' : 'center',
                px: 2.5,
              }}
            >
              <ListItemIcon
                sx={{
                  minWidth: 0,
                  mr: sidebarOpen ? 3 : 'auto',
                  justifyContent: 'center',
                }}
              >
                <SettingsIcon />
              </ListItemIcon>
              <ListItemText
                primary="Settings"
                sx={{ opacity: sidebarOpen ? 1 : 0 }}
              />
            </ListItemButton>
          </ListItem>
        </List>
      </Box>
    </Drawer>
  );
};

export default Sidebar;