import React from 'react';
import ReactDOM from 'react-dom/client';

// Simple test component
const TestApp = () => {
  return (
    <div style={{ padding: '20px' }}>
      <h1>Test App Working!</h1>
      <p>If you see this, React is working.</p>
    </div>
  );
};

ReactDOM.createRoot(document.getElementById('root')!).render(
  <React.StrictMode>
    <TestApp />
  </React.StrictMode>
);