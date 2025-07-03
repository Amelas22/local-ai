import { ReactElement } from 'react';
import { Box, Chip, Tooltip, CircularProgress } from '@mui/material';
import { FiberManualRecord as DotIcon } from '@mui/icons-material';
import { useWebSocketContext } from '../../context/WebSocketContext';

export function ConnectionStatus(): ReactElement {
  const { state } = useWebSocketContext();
  const { connected, connecting, error, reconnectAttempts, subscribedCase } = state;

  // Determine status and styling
  const getStatusInfo = () => {
    if (connecting) {
      return {
        label: 'Connecting...',
        color: 'warning' as const,
        icon: <CircularProgress size={16} color="inherit" />,
        tooltip: 'Establishing WebSocket connection'
      };
    }
    
    if (connected) {
      return {
        label: subscribedCase ? `Connected: ${subscribedCase}` : 'Connected',
        color: 'success' as const,
        icon: <DotIcon fontSize="small" />,
        tooltip: subscribedCase 
          ? `Connected to case: ${subscribedCase}` 
          : 'WebSocket connected, no case selected'
      };
    }
    
    if (error) {
      return {
        label: reconnectAttempts > 0 ? `Reconnecting (${reconnectAttempts}/5)` : 'Disconnected',
        color: 'error' as const,
        icon: <DotIcon fontSize="small" />,
        tooltip: error
      };
    }
    
    return {
      label: 'Disconnected',
      color: 'default' as const,
      icon: <DotIcon fontSize="small" />,
      tooltip: 'WebSocket not connected'
    };
  };

  const statusInfo = getStatusInfo();

  return (
    <Box sx={{ display: 'flex', alignItems: 'center', gap: 1 }}>
      <Tooltip title={statusInfo.tooltip} arrow>
        <Chip
          label={statusInfo.label}
          color={statusInfo.color}
          size="small"
          icon={statusInfo.icon}
          sx={{
            '& .MuiChip-icon': {
              marginLeft: '8px',
              marginRight: '-4px'
            }
          }}
        />
      </Tooltip>
    </Box>
  );
}