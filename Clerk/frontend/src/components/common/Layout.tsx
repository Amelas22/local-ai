import { Outlet } from 'react-router-dom';
import { Box, Container, Alert } from '@mui/material';
import Header from './Header';
import Sidebar from './Sidebar';
import { useAppSelector } from '@/hooks/redux';

const Layout = () => {
  const sidebarOpen = useAppSelector((state) => state.ui.sidebarOpen);
  const isMvpMode = import.meta.env.VITE_MVP_MODE === 'true';

  return (
    <Box sx={{ display: 'flex', minHeight: '100vh' }}>
      {/* MVP Mode Warning Banner */}
      {isMvpMode && (
        <Alert 
          severity="warning" 
          sx={{ 
            position: 'fixed', 
            top: 0, 
            left: 0, 
            right: 0, 
            zIndex: 2000,
            borderRadius: 0,
            justifyContent: 'center'
          }}
        >
          🚨 MVP Mode - No Authentication Active 🚨 This is for development only. DO NOT use in production!
        </Alert>
      )}
      
      <Header />
      <Sidebar />
      <Box
        component="main"
        sx={{
          flexGrow: 1,
          p: 3,
          mt: isMvpMode ? 12 : 8, // Account for header height + MVP banner
          ml: sidebarOpen ? '240px' : '64px',
          transition: 'margin-left 0.3s ease',
        }}
      >
        <Container maxWidth={false}>
          <Outlet />
        </Container>
      </Box>
    </Box>
  );
};

export default Layout;