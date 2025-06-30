import { Routes, Route, Navigate } from 'react-router-dom';
import { Box } from '@mui/material';
import Layout from '@components/common/Layout';
import ProtectedRoute from '@components/auth/ProtectedRoute';
import DiscoveryPage from './pages/DiscoveryPage';
import DashboardPage from './pages/DashboardPage';
import MotionDraftingPage from './pages/MotionDraftingPage';
import SearchPage from './pages/SearchPage';
import LoginPage from './pages/LoginPage';
import SignUpPage from './pages/SignUpPage';

const isAuthEnabled = import.meta.env.VITE_AUTH_ENABLED === 'true';

function App() {
  // Development mode - no authentication
  if (!isAuthEnabled) {
    return (
      <Box sx={{ display: 'flex', minHeight: '100vh' }}>
        <Routes>
          <Route path="/" element={<Layout />}>
            <Route index element={<Navigate to="/dashboard" replace />} />
            <Route path="dashboard" element={<DashboardPage />} />
            <Route path="discovery" element={<DiscoveryPage />} />
            <Route path="motion-drafting" element={<MotionDraftingPage />} />
            <Route path="search" element={<SearchPage />} />
          </Route>
          {/* In dev mode, redirect login/signup to dashboard */}
          <Route path="/login" element={<Navigate to="/dashboard" replace />} />
          <Route path="/signup" element={<Navigate to="/dashboard" replace />} />
          <Route path="*" element={<Navigate to="/dashboard" replace />} />
        </Routes>
      </Box>
    );
  }

  // Production mode - with authentication
  return (
    <Box sx={{ display: 'flex', minHeight: '100vh' }}>
      <Routes>
        {/* Public routes */}
        <Route path="/login" element={<LoginPage />} />
        <Route path="/signup" element={<SignUpPage />} />
        
        {/* Protected routes */}
        <Route
          path="/"
          element={
            <ProtectedRoute>
              <Layout />
            </ProtectedRoute>
          }
        >
          <Route index element={<Navigate to="/dashboard" replace />} />
          <Route path="dashboard" element={<DashboardPage />} />
          <Route path="discovery" element={<DiscoveryPage />} />
          <Route path="motion-drafting" element={<MotionDraftingPage />} />
          <Route path="search" element={<SearchPage />} />
        </Route>
        
        {/* Catch all - redirect to login */}
        <Route path="*" element={<Navigate to="/login" replace />} />
      </Routes>
    </Box>
  );
}

export default App;