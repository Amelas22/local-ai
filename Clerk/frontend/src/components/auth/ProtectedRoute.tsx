import { useEffect, useState } from 'react';
import { Navigate, useLocation } from 'react-router-dom';
import { Box, CircularProgress } from '@mui/material';
import { useAppSelector } from '@/hooks/redux';
import { tokenService } from '@/services/token.service';
import { authService } from '@/services/auth.service';
import { store } from '@/store/store';
import { loginSuccess } from '@/store/slices/authSlice';

interface ProtectedRouteProps {
  children: React.ReactNode;
  requiredRole?: string;
}

const ProtectedRoute = ({ children, requiredRole }: ProtectedRouteProps) => {
  const location = useLocation();
  const { isAuthenticated, user } = useAppSelector((state) => state.auth);
  const [isChecking, setIsChecking] = useState(true);

  useEffect(() => {
    const checkAuth = async () => {
      try {
        // Check if we have tokens but no Redux state (page refresh)
        if (!isAuthenticated && tokenService.hasTokens()) {
          // Check if access token is expired
          if (tokenService.isAccessTokenExpired()) {
            // Try to refresh the token
            try {
              const tokens = await authService.refreshAccessToken();
              const user = await authService.getCurrentUser();
              
              store.dispatch(loginSuccess({
                user,
                token: tokens.access_token,
                refreshToken: tokens.refresh_token
              }));
            } catch (error) {
              // Refresh failed, clear tokens
              tokenService.clearTokens();
            }
          } else {
            // Token is valid, restore user session
            try {
              const user = await authService.getCurrentUser();
              const accessToken = tokenService.getAccessToken();
              const refreshToken = tokenService.getRefreshToken();
              
              if (user && accessToken && refreshToken) {
                store.dispatch(loginSuccess({
                  user,
                  token: accessToken,
                  refreshToken
                }));
              }
            } catch (error) {
              // Failed to get user, clear tokens
              tokenService.clearTokens();
            }
          }
        }
      } catch (error) {
        console.error('Auth check failed:', error);
      } finally {
        setIsChecking(false);
      }
    };

    checkAuth();
  }, []);

  if (isChecking) {
    return (
      <Box
        display="flex"
        justifyContent="center"
        alignItems="center"
        minHeight="100vh"
      >
        <CircularProgress />
      </Box>
    );
  }

  if (!isAuthenticated) {
    // Redirect to login page but save the attempted location
    return <Navigate to="/login" state={{ from: location }} replace />;
  }

  // Check role-based access
  if (requiredRole && user && !user.is_admin && user.law_firm_id !== requiredRole) {
    return <Navigate to="/unauthorized" replace />;
  }

  return <>{children}</>;
};

export default ProtectedRoute;