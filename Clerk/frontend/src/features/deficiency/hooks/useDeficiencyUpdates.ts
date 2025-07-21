import { useEffect } from 'react';
import { useWebSocket } from '../../../hooks/useWebSocket';

interface DeficiencyUpdateEvent {
  type: 'deficiency:item_updated' | 'deficiency:bulk_update' | 'deficiency:report_saved';
  data: {
    report_id: string;
    [key: string]: unknown;
  };
}

export const useDeficiencyUpdates = (reportId: string, onUpdate: () => void) => {
  const { on, off } = useWebSocket();

  useEffect(() => {
    const handleItemUpdate = (event: DeficiencyUpdateEvent) => {
      if (event.data.report_id === reportId) {
        onUpdate();
      }
    };

    const handleBulkUpdate = (event: DeficiencyUpdateEvent) => {
      if (event.data.report_id === reportId) {
        onUpdate();
      }
    };

    const handleReportSaved = (event: DeficiencyUpdateEvent) => {
      if (event.data.report_id === reportId) {
        onUpdate();
      }
    };

    on('deficiency:item_updated', handleItemUpdate);
    on('deficiency:bulk_update', handleBulkUpdate);
    on('deficiency:report_saved', handleReportSaved);

    return () => {
      off('deficiency:item_updated', handleItemUpdate);
      off('deficiency:bulk_update', handleBulkUpdate);
      off('deficiency:report_saved', handleReportSaved);
    };
  }, [reportId, onUpdate, on, off]);
};