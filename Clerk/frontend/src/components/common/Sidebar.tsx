import { ReactElement, useState } from 'react';
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
  Button,
  Stack,
} from '@mui/material';
import DashboardIcon from '@mui/icons-material/Dashboard';
import FolderIcon from '@mui/icons-material/Folder';
import GavelIcon from '@mui/icons-material/Gavel';
import SearchIcon from '@mui/icons-material/Search';
import SettingsIcon from '@mui/icons-material/Settings';
import AddIcon from '@mui/icons-material/Add';
import { useAppSelector } from '@/hooks/redux';
import { useCaseSelection } from '@/hooks/useCaseSelection';
import { ConnectionStatus } from '../realtime/ConnectionStatus';
import { AddCaseModal } from '../cases/AddCaseModal';
import { CaseSelector } from '../cases/CaseSelector';

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
  const [addCaseModalOpen, setAddCaseModalOpen] = useState(false);
  const { 
    cases, 
    activeCase, 
    switchCase, 
    casesLoading, 
    casesError,
    refreshCases
  } = useCaseSelection();

  const drawerWidth = sidebarOpen ? 240 : 64;

  const handleCaseCreated = async (newCase: any) => {
    // Refresh cases list and switch to the new case
    await refreshCases();
    switchCase(newCase.collection_name);
  };

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
            <Stack spacing={1}>
              {/* Add Case Button */}
              <Button
                variant="outlined"
                startIcon={<AddIcon />}
                onClick={() => setAddCaseModalOpen(true)}
                fullWidth
                size="small"
                sx={{ mb: 1 }}
              >
                Add Case
              </Button>

              {/* Case Selector */}
              <CaseSelector
                value={activeCase || ''}
                onChange={switchCase}
                cases={cases.map((c) => ({
                  id: c.case_name,
                  name: c.display_name,
                  collection_name: c.case_name,
                  status: 'active' as const,
                  vector_count: c.document_count,
                }))}
                loading={casesLoading}
                error={casesError || undefined}
                label="Active Case"
              />
            </Stack>
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

      {/* Add Case Modal */}
      <AddCaseModal
        open={addCaseModalOpen}
        onClose={() => setAddCaseModalOpen(false)}
        onCaseCreated={handleCaseCreated}
      />
    </Drawer>
  );
};

export default Sidebar;