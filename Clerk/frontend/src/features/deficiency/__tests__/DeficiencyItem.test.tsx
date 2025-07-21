import React from 'react';
import { render, screen, fireEvent, waitFor } from '@testing-library/react';
import { Provider } from 'react-redux';
import { configureStore } from '@reduxjs/toolkit';
import { DeficiencyItem } from '../components/DeficiencyItem';
import { deficiencyAPI } from '../services/deficiencyAPI';
import deficiencyUIReducer from '../stores/deficiencyUIStore';
import { DeficiencyItem as DeficiencyItemType } from '../types/DeficiencyReport.types';

jest.mock('../services/deficiencyAPI');

const createMockStore = () => {
  return configureStore({
    reducer: {
      deficiencyUI: deficiencyUIReducer
    }
  });
};

const mockItem: DeficiencyItemType = {
  id: 'item-1',
  report_id: 'report-123',
  request_number: 'RFP No. 1',
  request_text: 'All documents related to contract',
  oc_response_text: 'No responsive documents',
  classification: 'not_produced',
  confidence_score: 0.85,
  evidence_chunks: [
    {
      document_id: 'doc-1',
      chunk_text: 'Sample evidence text',
      relevance_score: 0.9,
      page_number: 5,
      bates_number: 'BATES001'
    }
  ],
  notes: 'Initial notes'
};

describe('DeficiencyItem', () => {
  let store: ReturnType<typeof createMockStore>;
  const mockOnUpdate = jest.fn();

  beforeEach(() => {
    store = createMockStore();
    jest.clearAllMocks();
  });

  it('renders item data correctly', () => {
    render(
      <Provider store={store}>
        <DeficiencyItem item={mockItem} reportId="report-123" onUpdate={mockOnUpdate} />
      </Provider>
    );

    expect(screen.getByText('RFP No. 1')).toBeInTheDocument();
    expect(screen.getByText('All documents related to contract')).toBeInTheDocument();
    expect(screen.getByText('No responsive documents')).toBeInTheDocument();
    expect(screen.getByText('Not Produced')).toBeInTheDocument();
    expect(screen.getByText('85%')).toBeInTheDocument();
  });

  it('enters edit mode when edit button is clicked', () => {
    render(
      <Provider store={store}>
        <DeficiencyItem item={mockItem} reportId="report-123" onUpdate={mockOnUpdate} />
      </Provider>
    );

    const editButton = screen.getByLabelText('Edit RFP No. 1');
    fireEvent.click(editButton);

    expect(screen.getByLabelText('Classification')).toBeInTheDocument();
    expect(screen.getByLabelText('Notes')).toBeInTheDocument();
    expect(screen.getByLabelText('Save changes')).toBeInTheDocument();
    expect(screen.getByLabelText('Cancel editing')).toBeInTheDocument();
  });

  it('saves changes when save button is clicked', async () => {
    (deficiencyAPI.updateDeficiencyItem as jest.Mock).mockResolvedValueOnce(mockItem);

    render(
      <Provider store={store}>
        <DeficiencyItem item={mockItem} reportId="report-123" onUpdate={mockOnUpdate} />
      </Provider>
    );

    const editButton = screen.getByLabelText('Edit RFP No. 1');
    fireEvent.click(editButton);

    const notesField = screen.getByLabelText('Notes');
    fireEvent.change(notesField, { target: { value: 'Updated notes' } });

    const saveButton = screen.getByLabelText('Save changes');
    fireEvent.click(saveButton);

    await waitFor(() => {
      expect(deficiencyAPI.updateDeficiencyItem).toHaveBeenCalledWith(
        'report-123',
        'item-1',
        {
          classification: 'not_produced',
          notes: 'Updated notes'
        }
      );
      expect(mockOnUpdate).toHaveBeenCalled();
    });
  });

  it('cancels editing when cancel button is clicked', () => {
    render(
      <Provider store={store}>
        <DeficiencyItem item={mockItem} reportId="report-123" onUpdate={mockOnUpdate} />
      </Provider>
    );

    const editButton = screen.getByLabelText('Edit RFP No. 1');
    fireEvent.click(editButton);

    const notesField = screen.getByLabelText('Notes');
    fireEvent.change(notesField, { target: { value: 'Changed notes' } });

    const cancelButton = screen.getByLabelText('Cancel editing');
    fireEvent.click(cancelButton);

    expect(screen.queryByLabelText('Notes')).not.toBeInTheDocument();
    expect(screen.getByText('Initial notes')).toBeInTheDocument();
  });

  it('expands and collapses evidence section', () => {
    render(
      <Provider store={store}>
        <DeficiencyItem item={mockItem} reportId="report-123" onUpdate={mockOnUpdate} />
      </Provider>
    );

    const evidenceButton = screen.getByText('Evidence (1 chunks)');
    expect(screen.queryByText('Sample evidence text')).not.toBeInTheDocument();

    fireEvent.click(evidenceButton);
    expect(screen.getByText('Sample evidence text')).toBeInTheDocument();
    expect(screen.getByText('Page 5')).toBeInTheDocument();
    expect(screen.getByText('BATES001')).toBeInTheDocument();

    fireEvent.click(evidenceButton);
    expect(screen.queryByText('Sample evidence text')).not.toBeInTheDocument();
  });

  it('handles keyboard shortcuts in edit mode', () => {
    render(
      <Provider store={store}>
        <DeficiencyItem item={mockItem} reportId="report-123" onUpdate={mockOnUpdate} />
      </Provider>
    );

    const editButton = screen.getByLabelText('Edit RFP No. 1');
    fireEvent.click(editButton);

    const card = screen.getByRole('article').parentElement;
    fireEvent.keyDown(card!, { key: 'Escape' });

    expect(screen.queryByLabelText('Notes')).not.toBeInTheDocument();
  });

  it('toggles item selection', () => {
    render(
      <Provider store={store}>
        <DeficiencyItem item={mockItem} reportId="report-123" onUpdate={mockOnUpdate} />
      </Provider>
    );

    const checkbox = screen.getByLabelText('Select RFP No. 1');
    expect(checkbox).not.toBeChecked();

    fireEvent.click(checkbox);
    expect(checkbox).toBeChecked();

    fireEvent.click(checkbox);
    expect(checkbox).not.toBeChecked();
  });
});