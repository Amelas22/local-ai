import { createSlice, PayloadAction } from '@reduxjs/toolkit';
import { useSelector, useDispatch } from 'react-redux';
import type { RootState } from '../../../store/store';

interface DeficiencyUISliceState {
  selectedItems: string[];
  editingItemId: string | null;
  isAllSelected: boolean;
  expandedItems: string[];
}

const initialState: DeficiencyUISliceState = {
  selectedItems: [],
  editingItemId: null,
  isAllSelected: false,
  expandedItems: []
};

const deficiencyUISlice = createSlice({
  name: 'deficiencyUI',
  initialState,
  reducers: {
    setSelectedItems: (state, action: PayloadAction<string[]>) => {
      state.selectedItems = action.payload;
    },
    toggleItemSelection: (state, action: PayloadAction<string>) => {
      const itemId = action.payload;
      const index = state.selectedItems.indexOf(itemId);
      if (index > -1) {
        state.selectedItems.splice(index, 1);
      } else {
        state.selectedItems.push(itemId);
      }
      state.isAllSelected = false;
    },
    toggleAllSelection: (state, action: PayloadAction<string[]>) => {
      if (state.isAllSelected) {
        state.selectedItems = [];
        state.isAllSelected = false;
      } else {
        state.selectedItems = action.payload;
        state.isAllSelected = true;
      }
    },
    setEditingItemId: (state, action: PayloadAction<string | null>) => {
      state.editingItemId = action.payload;
    },
    toggleItemExpansion: (state, action: PayloadAction<string>) => {
      const itemId = action.payload;
      const index = state.expandedItems.indexOf(itemId);
      if (index > -1) {
        state.expandedItems.splice(index, 1);
      } else {
        state.expandedItems.push(itemId);
      }
    },
    clearSelection: (state) => {
      state.selectedItems = [];
      state.isAllSelected = false;
    }
  }
});

export const {
  setSelectedItems,
  toggleItemSelection,
  toggleAllSelection,
  setEditingItemId,
  toggleItemExpansion,
  clearSelection
} = deficiencyUISlice.actions;

export default deficiencyUISlice.reducer;

export const useDeficiencyUIStore = () => {
  const dispatch = useDispatch();
  const state = useSelector((state: RootState) => state.deficiencyUI);
  
  return {
    selectedItems: new Set(state.selectedItems),
    editingItemId: state.editingItemId,
    isAllSelected: state.isAllSelected,
    expandedItems: new Set(state.expandedItems),
    setSelectedItems: (items: Set<string>) => dispatch(setSelectedItems(Array.from(items))),
    toggleItemSelection: (itemId: string) => dispatch(toggleItemSelection(itemId)),
    toggleAllSelection: (allItemIds: string[]) => dispatch(toggleAllSelection(allItemIds)),
    setEditingItemId: (itemId: string | null) => dispatch(setEditingItemId(itemId)),
    toggleItemExpansion: (itemId: string) => dispatch(toggleItemExpansion(itemId)),
    clearSelection: () => dispatch(clearSelection())
  };
};