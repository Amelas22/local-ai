# UI Components Library

## Overview

This document catalogs the reusable UI components in the Clerk Legal AI System. Components are built with React, TypeScript, and Material-UI, following consistent patterns for accessibility, theming, and composition.

## Component Categories

### Core Components

#### Button
Primary interactive element with multiple variants.

```typescript
interface ButtonProps {
  variant?: 'contained' | 'outlined' | 'text';
  color?: 'primary' | 'secondary' | 'error' | 'warning' | 'success';
  size?: 'small' | 'medium' | 'large';
  startIcon?: ReactNode;
  endIcon?: ReactNode;
  loading?: boolean;
  fullWidth?: boolean;
  disabled?: boolean;
  onClick?: () => void;
  children: ReactNode;
}

// Usage
<Button 
  variant="contained" 
  color="primary"
  loading={isSubmitting}
  startIcon={<SaveIcon />}
>
  Save Document
</Button>
```

#### Card
Container component for grouped content.

```typescript
interface CardProps {
  elevation?: number;
  variant?: 'elevation' | 'outlined';
  interactive?: boolean;
  selected?: boolean;
  onClick?: () => void;
  children: ReactNode;
}

// Usage
<Card interactive selected={isSelected} onClick={handleSelect}>
  <CardHeader title="Discovery Production" />
  <CardContent>
    <Typography>150 documents processed</Typography>
  </CardContent>
</Card>
```

#### TextField
Enhanced input component with validation support.

```typescript
interface TextFieldProps {
  label: string;
  value: string;
  onChange: (value: string) => void;
  error?: boolean;
  helperText?: string;
  multiline?: boolean;
  rows?: number;
  required?: boolean;
  disabled?: boolean;
  placeholder?: string;
  type?: 'text' | 'email' | 'password' | 'number';
  InputProps?: InputProps;
}

// Usage
<TextField
  label="Case Name"
  value={caseName}
  onChange={setCaseName}
  required
  error={!!errors.caseName}
  helperText={errors.caseName?.message}
/>
```

### Layout Components

#### PageContainer
Standard page layout wrapper.

```typescript
interface PageContainerProps {
  title?: string;
  subtitle?: string;
  actions?: ReactNode;
  breadcrumbs?: BreadcrumbItem[];
  loading?: boolean;
  error?: Error | null;
  children: ReactNode;
}

// Usage
<PageContainer
  title="Discovery Analysis"
  subtitle="Review and process discovery documents"
  actions={<Button>New Production</Button>}
  breadcrumbs={[
    { label: 'Cases', href: '/cases' },
    { label: 'Smith v Jones', href: '/cases/123' },
    { label: 'Discovery' }
  ]}
>
  {/* Page content */}
</PageContainer>
```

#### DataGrid
Advanced table component with sorting, filtering, and pagination.

```typescript
interface DataGridProps<T> {
  columns: Column<T>[];
  rows: T[];
  loading?: boolean;
  pagination?: PaginationConfig;
  onRowClick?: (row: T) => void;
  selectable?: boolean;
  onSelectionChange?: (selected: T[]) => void;
  actions?: (row: T) => ReactNode;
}

// Usage
<DataGrid
  columns={[
    { field: 'fileName', headerName: 'File Name', width: 300 },
    { field: 'pageCount', headerName: 'Pages', width: 100 },
    { field: 'status', headerName: 'Status', renderCell: StatusChip }
  ]}
  rows={documents}
  pagination={{ page: 0, pageSize: 25 }}
  onRowClick={handleDocumentClick}
/>
```

#### TabPanel
Tabbed interface for organizing related content.

```typescript
interface TabPanelProps {
  tabs: TabConfig[];
  value: string;
  onChange: (value: string) => void;
  lazy?: boolean;
}

// Usage
<TabPanel
  tabs={[
    { value: 'documents', label: 'Documents', content: <DocumentList /> },
    { value: 'facts', label: 'Extracted Facts', content: <FactsList /> },
    { value: 'timeline', label: 'Timeline', content: <Timeline /> }
  ]}
  value={activeTab}
  onChange={setActiveTab}
  lazy
/>
```

### Form Components

#### FormField
Wrapper for form fields with consistent spacing and labels.

```typescript
interface FormFieldProps {
  label: string;
  required?: boolean;
  error?: FieldError;
  tooltip?: string;
  children: ReactNode;
}

// Usage
<FormField 
  label="Motion Type" 
  required 
  error={errors.motionType}
  tooltip="Select the type of motion to draft"
>
  <Select value={motionType} onChange={setMotionType}>
    <MenuItem value="summary_judgment">Summary Judgment</MenuItem>
    <MenuItem value="motion_to_compel">Motion to Compel</MenuItem>
  </Select>
</FormField>
```

#### FileUpload
Drag-and-drop file upload component.

```typescript
interface FileUploadProps {
  accept?: string[];
  multiple?: boolean;
  maxSize?: number;
  maxFiles?: number;
  onFilesAdded: (files: File[]) => void;
  onFileRemoved?: (file: File) => void;
  files?: File[];
  disabled?: boolean;
}

// Usage
<FileUpload
  accept={['.pdf', '.doc', '.docx']}
  multiple
  maxFiles={50}
  maxSize={10 * 1024 * 1024} // 10MB
  onFilesAdded={handleFilesAdded}
  files={selectedFiles}
/>
```

#### DatePicker
Date selection component with calendar interface.

```typescript
interface DatePickerProps {
  label: string;
  value: Date | null;
  onChange: (date: Date | null) => void;
  minDate?: Date;
  maxDate?: Date;
  disabled?: boolean;
  error?: boolean;
  helperText?: string;
}

// Usage
<DatePicker
  label="Production Date"
  value={productionDate}
  onChange={setProductionDate}
  maxDate={new Date()}
/>
```

### Display Components

#### StatusChip
Colored chip for displaying status information.

```typescript
interface StatusChipProps {
  status: 'pending' | 'processing' | 'completed' | 'failed';
  size?: 'small' | 'medium';
  showIcon?: boolean;
}

// Usage
<StatusChip status="completed" showIcon />
```

#### ProgressBar
Linear or circular progress indicator.

```typescript
interface ProgressBarProps {
  value: number;
  variant?: 'linear' | 'circular';
  color?: 'primary' | 'secondary';
  showLabel?: boolean;
  size?: 'small' | 'medium' | 'large';
}

// Usage
<ProgressBar 
  value={processingProgress} 
  variant="linear"
  showLabel
/>
```

#### EmptyState
Placeholder for empty content areas.

```typescript
interface EmptyStateProps {
  icon?: ReactNode;
  title: string;
  description?: string;
  action?: ReactNode;
}

// Usage
<EmptyState
  icon={<FolderOpenIcon />}
  title="No documents found"
  description="Upload documents to get started"
  action={<Button>Upload Documents</Button>}
/>
```

### Document Components

#### DocumentViewer
PDF viewer with annotation support.

```typescript
interface DocumentViewerProps {
  documentId: string;
  highlights?: Highlight[];
  annotations?: Annotation[];
  onPageChange?: (page: number) => void;
  onTextSelect?: (selection: TextSelection) => void;
  toolbar?: boolean;
  zoom?: number;
}

// Usage
<DocumentViewer
  documentId={currentDocument.id}
  highlights={searchHighlights}
  annotations={userAnnotations}
  onTextSelect={handleTextSelection}
  toolbar
/>
```

#### DocumentCard
Preview card for documents.

```typescript
interface DocumentCardProps {
  document: Document;
  selected?: boolean;
  onSelect?: () => void;
  onView?: () => void;
  onDownload?: () => void;
  showActions?: boolean;
}

// Usage
<DocumentCard
  document={document}
  selected={isSelected}
  onSelect={handleSelect}
  onView={handleView}
  showActions
/>
```

### Legal-Specific Components

#### CaseSelector
Dropdown for switching between cases.

```typescript
interface CaseSelectorProps {
  currentCase: Case | null;
  cases: Case[];
  onCaseChange: (caseId: string) => void;
  allowCreate?: boolean;
}

// Usage
<CaseSelector
  currentCase={currentCase}
  cases={userCases}
  onCaseChange={handleCaseSwitch}
  allowCreate
/>
```

#### DeficiencyItem
Display component for deficiency analysis results.

```typescript
interface DeficiencyItemProps {
  item: DeficiencyItem;
  onEdit?: (item: DeficiencyItem) => void;
  onViewEvidence?: (evidence: Evidence[]) => void;
  editable?: boolean;
}

// Usage
<DeficiencyItem
  item={deficiencyItem}
  onEdit={handleEdit}
  onViewEvidence={handleViewEvidence}
  editable={canEdit}
/>
```

#### MotionSection
Editable section of a legal motion.

```typescript
interface MotionSectionProps {
  section: MotionSection;
  onChange?: (content: string) => void;
  editable?: boolean;
  showCitations?: boolean;
}

// Usage
<MotionSection
  section={introductionSection}
  onChange={handleSectionChange}
  editable
  showCitations
/>
```

### Feedback Components

#### ConfirmDialog
Confirmation modal for destructive actions.

```typescript
interface ConfirmDialogProps {
  open: boolean;
  onClose: () => void;
  onConfirm: () => void;
  title: string;
  message: string;
  confirmText?: string;
  cancelText?: string;
  severity?: 'info' | 'warning' | 'error';
}

// Usage
<ConfirmDialog
  open={showDeleteConfirm}
  onClose={() => setShowDeleteConfirm(false)}
  onConfirm={handleDelete}
  title="Delete Document?"
  message="This action cannot be undone."
  severity="warning"
/>
```

#### Snackbar
Temporary notification messages.

```typescript
interface SnackbarProps {
  open: boolean;
  onClose: () => void;
  message: string;
  severity?: 'success' | 'error' | 'warning' | 'info';
  duration?: number;
  action?: ReactNode;
}

// Usage
<Snackbar
  open={showSuccess}
  onClose={() => setShowSuccess(false)}
  message="Document uploaded successfully"
  severity="success"
  duration={5000}
/>
```

#### LoadingOverlay
Full-screen or container loading indicator.

```typescript
interface LoadingOverlayProps {
  loading: boolean;
  message?: string;
  fullScreen?: boolean;
  backdrop?: boolean;
}

// Usage
<LoadingOverlay
  loading={isProcessing}
  message="Processing discovery documents..."
  backdrop
/>
```

### Navigation Components

#### Breadcrumbs
Hierarchical navigation trail.

```typescript
interface BreadcrumbsProps {
  items: BreadcrumbItem[];
  separator?: ReactNode;
  maxItems?: number;
}

// Usage
<Breadcrumbs
  items={[
    { label: 'Home', href: '/' },
    { label: 'Cases', href: '/cases' },
    { label: 'Smith v Jones', href: '/cases/123' },
    { label: 'Discovery' }
  ]}
/>
```

#### SideNav
Vertical navigation menu.

```typescript
interface SideNavProps {
  items: NavItem[];
  activeItem?: string;
  onItemClick?: (item: NavItem) => void;
  collapsed?: boolean;
}

// Usage
<SideNav
  items={[
    { id: 'dashboard', label: 'Dashboard', icon: <DashboardIcon /> },
    { id: 'cases', label: 'Cases', icon: <FolderIcon /> },
    { id: 'discovery', label: 'Discovery', icon: <SearchIcon /> }
  ]}
  activeItem={currentRoute}
  onItemClick={handleNavigation}
/>
```

## Component Patterns

### Composition Pattern
```typescript
// Composable card components
<Card>
  <Card.Header 
    title="Discovery Production"
    action={<IconButton><MoreVertIcon /></IconButton>}
  />
  <Card.Content>
    <Typography>Content here</Typography>
  </Card.Content>
  <Card.Actions>
    <Button>View Details</Button>
  </Card.Actions>
</Card>
```

### Compound Components
```typescript
// Form with compound field components
<Form onSubmit={handleSubmit}>
  <Form.Section title="Case Information">
    <Form.Field name="caseName" label="Case Name" required>
      <TextField />
    </Form.Field>
    <Form.Field name="caseNumber" label="Case Number">
      <TextField />
    </Form.Field>
  </Form.Section>
  <Form.Actions>
    <Button type="submit">Save</Button>
  </Form.Actions>
</Form>
```

### Render Props Pattern
```typescript
// Flexible data display
<DataProvider
  endpoint="/api/documents"
  params={{ caseId }}
>
  {({ data, loading, error }) => (
    loading ? <Skeleton /> :
    error ? <ErrorMessage error={error} /> :
    <DocumentGrid documents={data} />
  )}
</DataProvider>
```

## Accessibility Guidelines

### ARIA Labels
```typescript
<IconButton 
  aria-label="Delete document"
  onClick={handleDelete}
>
  <DeleteIcon />
</IconButton>
```

### Keyboard Navigation
```typescript
<MenuItem 
  onKeyDown={(e) => {
    if (e.key === 'Enter' || e.key === ' ') {
      handleSelect();
    }
  }}
  tabIndex={0}
>
  Option
</MenuItem>
```

### Screen Reader Support
```typescript
<div role="status" aria-live="polite" aria-atomic="true">
  {loading && <span className="sr-only">Loading documents...</span>}
</div>
```

## Theme Integration

### Using Theme Variables
```typescript
const StyledCard = styled(Card)(({ theme }) => ({
  borderRadius: theme.shape.borderRadius * 2,
  padding: theme.spacing(3),
  transition: theme.transitions.create(['box-shadow', 'transform'], {
    duration: theme.transitions.duration.short,
  }),
  '&:hover': {
    boxShadow: theme.shadows[8],
    transform: 'translateY(-2px)',
  }
}));
```

### Responsive Components
```typescript
const ResponsiveGrid = styled(Grid)(({ theme }) => ({
  [theme.breakpoints.down('sm')]: {
    flexDirection: 'column',
  },
  [theme.breakpoints.up('md')]: {
    flexDirection: 'row',
    gap: theme.spacing(3),
  }
}));
```

## Performance Considerations

### Memoization
```typescript
export const ExpensiveComponent = memo(({ data }: Props) => {
  const processedData = useMemo(() => 
    processData(data), 
    [data]
  );
  
  return <DataDisplay data={processedData} />;
});
```

### Lazy Loading
```typescript
const HeavyComponent = lazy(() => 
  import('./HeavyComponent')
);

<Suspense fallback={<Skeleton />}>
  <HeavyComponent />
</Suspense>
```

### Virtual Rendering
```typescript
<VirtualList
  height={600}
  itemCount={items.length}
  itemSize={80}
  renderItem={({ index, style }) => (
    <div style={style}>
      <ListItem item={items[index]} />
    </div>
  )}
/>
```

## Testing Components

### Component Testing
```typescript
describe('Button', () => {
  it('should render with correct text', () => {
    render(<Button>Click me</Button>);
    expect(screen.getByText('Click me')).toBeInTheDocument();
  });

  it('should call onClick when clicked', () => {
    const handleClick = jest.fn();
    render(<Button onClick={handleClick}>Click</Button>);
    fireEvent.click(screen.getByRole('button'));
    expect(handleClick).toHaveBeenCalledTimes(1);
  });
});
```

### Accessibility Testing
```typescript
it('should be accessible', async () => {
  const { container } = render(<DocumentCard document={mockDocument} />);
  const results = await axe(container);
  expect(results).toHaveNoViolations();
});
```

## Component Documentation

Each component should include:
- TypeScript interface definitions
- Usage examples
- Props documentation
- Accessibility considerations
- Performance notes
- Testing guidelines