import { useState } from 'react';
import { Box, Typography, Paper, Tabs, Tab } from '@mui/material';
import DiscoveryForm from '@/components/discovery/DiscoveryForm';
import ProcessingVisualization from '@/components/discovery/ProcessingVisualization';
import { useAppSelector } from '@/hooks/redux';

interface TabPanelProps {
  children?: React.ReactNode;
  index: number;
  value: number;
}

function TabPanel(props: TabPanelProps) {
  const { children, value, index, ...other } = props;

  return (
    <div
      role="tabpanel"
      hidden={value !== index}
      id={`discovery-tabpanel-${index}`}
      aria-labelledby={`discovery-tab-${index}`}
      {...other}
    >
      {value === index && <Box sx={{ py: 3 }}>{children}</Box>}
    </div>
  );
}

const DiscoveryPage = () => {
  const [activeTab, setActiveTab] = useState(0);
  const isProcessing = useAppSelector((state) => state.discovery.isProcessing);

  const handleTabChange = (_event: React.SyntheticEvent, newValue: number) => {
    setActiveTab(newValue);
  };

  return (
    <Box>
      <Typography variant="h4" component="h1" gutterBottom>
        Discovery Processing
      </Typography>
      
      <Paper sx={{ width: '100%' }}>
        <Tabs
          value={activeTab}
          onChange={handleTabChange}
          aria-label="discovery processing tabs"
        >
          <Tab label="New Processing" />
          <Tab label="Processing Status" disabled={!isProcessing} />
          <Tab label="History" />
        </Tabs>
        
        <TabPanel value={activeTab} index={0}>
          <DiscoveryForm />
        </TabPanel>
        
        <TabPanel value={activeTab} index={1}>
          <ProcessingVisualization />
        </TabPanel>
        
        <TabPanel value={activeTab} index={2}>
          <Typography>Processing history will be displayed here...</Typography>
        </TabPanel>
      </Paper>
    </Box>
  );
};

export default DiscoveryPage;