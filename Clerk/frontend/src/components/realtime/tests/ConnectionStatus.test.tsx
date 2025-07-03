import { render, screen } from '@testing-library/react';
import { ConnectionStatus } from '../ConnectionStatus';
import { WebSocketContext } from '../../../context/WebSocketContext';
import '@testing-library/jest-dom';
import { ReactNode } from 'react';

// Mock WebSocket context
const mockContextValue = {
  socket: null,
  state: {
    connected: false,
    connecting: false,
    error: null,
    reconnectAttempts: 0,
    subscribedCase: null
  },
  connect: jest.fn(),
  disconnect: jest.fn(),
  emit: jest.fn(),
  subscribeToCase: jest.fn(),
  unsubscribeFromCase: jest.fn()
};

const wrapper = ({ children, contextValue = mockContextValue }: { 
  children: ReactNode;
  contextValue?: any;
}) => (
  <WebSocketContext.Provider value={contextValue}>
    {children}
  </WebSocketContext.Provider>
);

describe('ConnectionStatus Component', () => {
  it('should show disconnected state', () => {
    render(<ConnectionStatus />, { wrapper });
    
    expect(screen.getByText('Disconnected')).toBeInTheDocument();
  });

  it('should show connecting state', () => {
    const connectingContext = {
      ...mockContextValue,
      state: {
        ...mockContextValue.state,
        connecting: true
      }
    };
    
    render(<ConnectionStatus />, { 
      wrapper: (props) => wrapper({ ...props, contextValue: connectingContext })
    });
    
    expect(screen.getByText('Connecting...')).toBeInTheDocument();
  });

  it('should show connected state without case', () => {
    const connectedContext = {
      ...mockContextValue,
      state: {
        ...mockContextValue.state,
        connected: true
      }
    };
    
    render(<ConnectionStatus />, { 
      wrapper: (props) => wrapper({ ...props, contextValue: connectedContext })
    });
    
    expect(screen.getByText('Connected')).toBeInTheDocument();
  });

  it('should show connected state with case', () => {
    const connectedWithCaseContext = {
      ...mockContextValue,
      state: {
        ...mockContextValue.state,
        connected: true,
        subscribedCase: 'Smith_v_Jones_2024'
      }
    };
    
    render(<ConnectionStatus />, { 
      wrapper: (props) => wrapper({ ...props, contextValue: connectedWithCaseContext })
    });
    
    expect(screen.getByText('Connected: Smith_v_Jones_2024')).toBeInTheDocument();
  });

  it('should show error state', () => {
    const errorContext = {
      ...mockContextValue,
      state: {
        ...mockContextValue.state,
        error: 'Connection timeout'
      }
    };
    
    render(<ConnectionStatus />, { 
      wrapper: (props) => wrapper({ ...props, contextValue: errorContext })
    });
    
    expect(screen.getByText('Disconnected')).toBeInTheDocument();
  });

  it('should show reconnecting state', () => {
    const reconnectingContext = {
      ...mockContextValue,
      state: {
        ...mockContextValue.state,
        error: 'Connection lost',
        reconnectAttempts: 3
      }
    };
    
    render(<ConnectionStatus />, { 
      wrapper: (props) => wrapper({ ...props, contextValue: reconnectingContext })
    });
    
    expect(screen.getByText('Reconnecting (3/5)')).toBeInTheDocument();
  });
});