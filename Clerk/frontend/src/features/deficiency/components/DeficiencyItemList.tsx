import React from 'react';
import { Box, Checkbox, FormControlLabel, Typography } from '@mui/material';
import { DeficiencyItem } from './DeficiencyItem';
import { DeficiencyItem as DeficiencyItemType } from '../types/DeficiencyReport.types';
import { useDeficiencyUIStore } from '../stores/deficiencyUIStore';

interface DeficiencyItemListProps {
  items: DeficiencyItemType[];
  reportId: string;
  onItemUpdate: () => void;
}

export const DeficiencyItemList: React.FC<DeficiencyItemListProps> = ({
  items,
  reportId,
  onItemUpdate
}) => {
  const { isAllSelected, toggleAllSelection, selectedItems } = useDeficiencyUIStore();

  const handleSelectAll = () => {
    const allItemIds = items.map(item => item.id);
    toggleAllSelection(allItemIds);
  };

  return (
    <Box>
      <Box px={3} py={2} borderBottom={1} borderColor="divider">
        <FormControlLabel
          control={
            <Checkbox
              checked={isAllSelected}
              onChange={handleSelectAll}
              indeterminate={!isAllSelected && items.some(item => 
                selectedItems.has(item.id)
              )}
            />
          }
          label={
            <Typography variant="body2">
              Select All ({items.length} items)
            </Typography>
          }
        />
      </Box>

      <Box>
        {items.map((item) => (
          <DeficiencyItem
            key={item.id}
            item={item}
            reportId={reportId}
            onUpdate={onItemUpdate}
          />
        ))}
      </Box>
    </Box>
  );
};