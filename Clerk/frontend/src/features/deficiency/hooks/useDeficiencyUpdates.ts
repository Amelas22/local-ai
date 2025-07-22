import { useEffect } from 'react';
import { useWebSocket } from '../../../hooks/useWebSocket';

export const useDeficiencyUpdates = (reportId: string, onUpdate: () => void) => {
  const { on } = useWebSocket();

  useEffect(() => {
    const handleItemUpdate = (data: { report_id: string; item_id: string; changes: Record<string, unknown> }) => {
      if (data.report_id === reportId) {
        onUpdate();
      }
    };

    const handleBulkUpdate = (data: { report_id: string; item_ids: string[]; changes: Record<string, unknown> }) => {
      if (data.report_id === reportId) {
        onUpdate();
      }
    };

    const handleReportSaved = (data: { report_id: string; saved_by: string; saved_at: string }) => {
      if (data.report_id === reportId) {
        onUpdate();
      }
    };

    const unsub1 = on('deficiency:item_updated', handleItemUpdate);
    const unsub2 = on('deficiency:bulk_update', handleBulkUpdate);
    const unsub3 = on('deficiency:report_saved', handleReportSaved);

    return () => {
      unsub1();
      unsub2();
      unsub3();
    };
  }, [reportId, onUpdate, on]);
};