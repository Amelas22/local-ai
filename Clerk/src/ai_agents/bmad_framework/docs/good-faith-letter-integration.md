# Good Faith Letter Integration with Deficiency Analysis Pipeline

## Overview

The Good Faith Letter generation integrates seamlessly with the deficiency analysis pipeline, providing an end-to-end workflow from discovery document analysis to formal correspondence.

## Integration Architecture

```
Discovery Documents → Deficiency Analysis → Good Faith Letter → Export/Send
                           ↓                        ↓
                    DeficiencyReport         GeneratedLetter
                           ↓                        ↓
                    DeficiencyItems          Letter Versions
```

## Complete Pipeline Integration

### 1. Automatic Trigger Pattern

When deficiency analysis completes, automatically trigger letter generation:

```python
# In deficiency_endpoints.py
@router.post("/analyze")
async def analyze_deficiencies(
    request: DeficiencyAnalysisRequest,
    background_tasks: BackgroundTasks,
    case_context = Depends(require_case_context("write"))
):
    # ... perform analysis ...
    
    # If analysis completes successfully
    if result.status == "completed":
        # Trigger Good Faith letter generation
        background_tasks.add_task(
            generate_good_faith_letter_task,
            report_id=result.id,
            case_name=case_context.case_name,
            auto_generate=request.auto_generate_letter
        )
    
    return result

async def generate_good_faith_letter_task(
    report_id: str,
    case_name: str,
    auto_generate: bool = False
):
    """Background task to generate Good Faith letter."""
    if not auto_generate:
        # Just emit notification
        await emit_event(
            'deficiency:letter_ready',
            {
                'report_id': report_id,
                'case_name': case_name,
                'message': 'Deficiency analysis complete. Ready to generate Good Faith letter.'
            }
        )
        return
    
    # Auto-generate letter
    try:
        service = GoodFaithLetterAgentService()
        letter = await service.generate_letter(
            parameters={
                'report_id': report_id,
                'jurisdiction': 'federal',  # Or determine from case
                'include_evidence': True
            },
            security_context=create_system_context(case_name)
        )
        
        await emit_event(
            'letter:auto_generated',
            {
                'letter_id': str(letter.id),
                'report_id': report_id,
                'status': 'draft'
            }
        )
    except Exception as e:
        logger.error(f"Auto-generation failed: {e}")
```

### 2. Manual Trigger Pattern

UI-driven letter generation after reviewing deficiency report:

```javascript
// React component example
function DeficiencyReportView({ reportId }) {
  const [report, setReport] = useState(null);
  const [generating, setGenerating] = useState(false);
  const { generateLetter } = useGoodFaithLetter();
  
  const handleGenerateLetter = async () => {
    setGenerating(true);
    
    try {
      const letter = await generateLetter(reportId, {
        jurisdiction: 'federal',
        include_evidence: true,
        attorney_info: getDefaultAttorneyInfo()
      });
      
      // Navigate to letter editor
      navigate(`/letters/${letter.letter_id}/edit`);
      
    } catch (error) {
      showError('Failed to generate letter');
    } finally {
      setGenerating(false);
    }
  };
  
  return (
    <div>
      <DeficiencyReportDetails report={report} />
      
      <Button
        onClick={handleGenerateLetter}
        disabled={generating || report?.status !== 'completed'}
      >
        Generate Good Faith Letter
      </Button>
    </div>
  );
}
```

### 3. Batch Processing Pattern

Generate letters for multiple deficiency reports:

```python
from typing import List
import asyncio

async def batch_generate_letters(
    report_ids: List[str],
    jurisdiction: str,
    attorney_info: dict,
    security_context: AgentSecurityContext
) -> List[GeneratedLetter]:
    """
    Generate Good Faith letters for multiple reports.
    
    Respects rate limits and handles failures gracefully.
    """
    results = []
    failed = []
    
    # Process in batches to respect rate limits
    batch_size = 5  # 10 per minute limit
    
    for i in range(0, len(report_ids), batch_size):
        batch = report_ids[i:i + batch_size]
        
        # Generate letters concurrently within batch
        tasks = [
            generate_single_letter(
                report_id, 
                jurisdiction, 
                attorney_info,
                security_context
            )
            for report_id in batch
        ]
        
        batch_results = await asyncio.gather(*tasks, return_exceptions=True)
        
        # Process results
        for report_id, result in zip(batch, batch_results):
            if isinstance(result, Exception):
                logger.error(f"Failed to generate letter for {report_id}: {result}")
                failed.append(report_id)
            else:
                results.append(result)
        
        # Rate limit delay between batches
        if i + batch_size < len(report_ids):
            await asyncio.sleep(60)  # 1 minute between batches
    
    # Emit summary event
    await emit_event(
        'letters:batch_complete',
        {
            'total': len(report_ids),
            'succeeded': len(results),
            'failed': len(failed),
            'failed_reports': failed
        }
    )
    
    return results
```

## Data Flow Mapping

### From DeficiencyReport to Letter Variables

```python
# Template variable mapping
def map_deficiency_to_letter_variables(
    report: DeficiencyReport,
    items: List[DeficiencyItem],
    case_info: dict
) -> dict:
    """Map deficiency data to letter template variables."""
    
    return {
        # Case information
        "CASE_NAME": report.case_name,
        "CASE_NUMBER": case_info.get("case_number", ""),
        
        # Discovery information  
        "PRODUCTION_DATE": report.created_at.strftime("%B %d, %Y"),
        "TOTAL_REQUESTS": report.total_requests,
        "DEFICIENCY_COUNT": calculate_deficiency_count(report),
        
        # Deficiency items formatted for template
        "DEFICIENCY_ITEMS": [
            {
                "REQUEST_NUMBER": item.request_number,
                "REQUEST_TEXT": item.request_text,
                "OC_RESPONSE": item.oc_response_text,
                "CLASSIFICATION": format_classification(item.classification),
                "EVIDENCE": format_evidence_chunks(item.evidence_chunks)
            }
            for item in items
            if item.classification != "fully_produced"
        ],
        
        # Summary statistics
        "SUMMARY_STATS": {
            "fully_produced": report.summary_statistics.get("fully_produced", 0),
            "partially_produced": report.summary_statistics.get("partially_produced", 0),
            "not_produced": report.summary_statistics.get("not_produced", 0),
            "no_responsive_docs": report.summary_statistics.get("no_responsive_docs", 0)
        }
    }
```

## UI Integration Components

### Letter Generation Button

```typescript
// LetterGenerationButton.tsx
export function LetterGenerationButton({ 
  reportId,
  onLetterGenerated 
}: LetterGenerationButtonProps) {
  const [modalOpen, setModalOpen] = useState(false);
  const [attorneyInfo, setAttorneyInfo] = useState(getStoredAttorneyInfo());
  
  return (
    <>
      <Button onClick={() => setModalOpen(true)}>
        Generate Good Faith Letter
      </Button>
      
      <Modal open={modalOpen} onClose={() => setModalOpen(false)}>
        <LetterGenerationForm
          reportId={reportId}
          attorneyInfo={attorneyInfo}
          onSubmit={async (params) => {
            const letter = await generateLetter(reportId, params);
            onLetterGenerated(letter);
            setModalOpen(false);
          }}
        />
      </Modal>
    </>
  );
}
```

### Letter Editor Integration

```typescript
// LetterEditor.tsx
export function LetterEditor({ letterId }: { letterId: string }) {
  const [letter, setLetter] = useState<Letter | null>(null);
  const [editing, setEditing] = useState(false);
  const { socket } = useWebSocket();
  
  useEffect(() => {
    // Subscribe to letter updates
    socket.on(`letter:${letterId}:updated`, (data) => {
      setLetter(data.letter);
    });
    
    return () => {
      socket.off(`letter:${letterId}:updated`);
    };
  }, [letterId]);
  
  const handleSave = async (edits: SectionEdit[]) => {
    const updated = await customizeLetter(letterId, edits);
    setLetter(updated);
    setEditing(false);
  };
  
  return (
    <div className="letter-editor">
      <LetterPreview 
        content={letter?.content}
        editable={editing && letter?.status === 'draft'}
        onEdit={handleSave}
      />
      
      <LetterActions
        letter={letter}
        onEdit={() => setEditing(true)}
        onFinalize={handleFinalize}
        onExport={handleExport}
      />
    </div>
  );
}
```

## Workflow State Management

### Redux/State Example

```typescript
// letterSlice.ts
interface LetterState {
  letters: Record<string, GeneratedLetter>;
  generating: Record<string, boolean>;
  errors: Record<string, string>;
}

const letterSlice = createSlice({
  name: 'letters',
  initialState: {
    letters: {},
    generating: {},
    errors: {}
  },
  reducers: {
    generationStarted(state, action) {
      state.generating[action.payload.reportId] = true;
    },
    generationCompleted(state, action) {
      const { reportId, letter } = action.payload;
      state.letters[letter.id] = letter;
      state.generating[reportId] = false;
    },
    generationFailed(state, action) {
      const { reportId, error } = action.payload;
      state.errors[reportId] = error;
      state.generating[reportId] = false;
    },
    letterUpdated(state, action) {
      const { letterId, updates } = action.payload;
      state.letters[letterId] = {
        ...state.letters[letterId],
        ...updates
      };
    }
  }
});
```

## Error Recovery Patterns

### Retry with Fallback

```python
async def generate_letter_with_retry(
    report_id: str,
    max_retries: int = 3
) -> GeneratedLetter:
    """Generate letter with automatic retry and fallback."""
    
    last_error = None
    
    for attempt in range(max_retries):
        try:
            # Try primary method
            return await generate_via_agent(report_id)
            
        except AgentExecutionError as e:
            last_error = e
            logger.warning(f"Agent execution failed (attempt {attempt + 1}): {e}")
            
            if attempt < max_retries - 1:
                # Exponential backoff
                await asyncio.sleep(2 ** attempt)
            else:
                # Final attempt - try fallback method
                logger.info("Falling back to direct template generation")
                return await generate_via_template_direct(report_id)
    
    raise last_error
```

## Performance Optimization

### Caching Strategy

```python
from functools import lru_cache
from datetime import timedelta

class LetterGenerationCache:
    """Cache for expensive operations in letter generation."""
    
    @lru_cache(maxsize=100)
    def get_attorney_info(self, user_id: str) -> dict:
        """Cache attorney information."""
        return fetch_attorney_info(user_id)
    
    @lru_cache(maxsize=50)
    def get_jurisdiction_requirements(self, jurisdiction: str) -> dict:
        """Cache jurisdiction requirements."""
        with open(f"data/jurisdiction-requirements.json") as f:
            data = json.load(f)
        return data.get(jurisdiction, data.get("states", {}).get(jurisdiction))
    
    def cache_generated_letter(
        self, 
        letter: GeneratedLetter,
        ttl: timedelta = timedelta(hours=24)
    ):
        """Cache generated letters for quick retrieval."""
        cache_key = f"letter:{letter.id}"
        cache.set(cache_key, letter, ttl)
```

## Monitoring and Analytics

### Track Letter Generation Metrics

```python
from prometheus_client import Counter, Histogram, Gauge

# Metrics
letter_generations = Counter(
    'good_faith_letters_generated_total',
    'Total Good Faith letters generated',
    ['jurisdiction', 'status']
)

letter_generation_duration = Histogram(
    'good_faith_letter_generation_seconds',
    'Time to generate Good Faith letter'
)

active_draft_letters = Gauge(
    'good_faith_letters_draft_active',
    'Number of letters in draft status'
)

# Track metrics
@letter_generation_duration.time()
async def generate_letter_tracked(report_id: str, **kwargs):
    """Generate letter with metrics tracking."""
    try:
        letter = await generate_letter(report_id, **kwargs)
        letter_generations.labels(
            jurisdiction=letter.jurisdiction,
            status='success'
        ).inc()
        
        if letter.status == LetterStatus.DRAFT:
            active_draft_letters.inc()
            
        return letter
        
    except Exception as e:
        letter_generations.labels(
            jurisdiction=kwargs.get('jurisdiction', 'unknown'),
            status='failed'
        ).inc()
        raise
```

## Testing Integration

### End-to-End Test Example

```python
@pytest.mark.integration
async def test_deficiency_to_letter_pipeline():
    """Test complete pipeline from deficiency analysis to letter export."""
    
    # Step 1: Create deficiency report
    report = await create_test_deficiency_report()
    
    # Step 2: Generate letter
    letter_service = GoodFaithLetterAgentService()
    letter = await letter_service.generate_letter(
        parameters={
            'report_id': str(report.id),
            'jurisdiction': 'federal'
        },
        security_context=test_security_context
    )
    
    assert letter.status == LetterStatus.DRAFT
    assert letter.report_id == report.id
    
    # Step 3: Customize letter
    customization_service = LetterCustomizationService()
    updated = await customization_service.apply_edits(
        letter_id=letter.id,
        section_edits=[
            {'section': 'test', 'content': 'Updated content'}
        ],
        editor_id='test-user'
    )
    
    assert updated.version == 2
    
    # Step 4: Finalize and export
    finalized = await letter_service.finalize_letter(
        letter_id=letter.id,
        approved_by='test-approver',
        security_context=test_security_context
    )
    
    export_data = await letter_service.export_letter(
        letter_id=letter.id,
        format='pdf',
        security_context=test_security_context
    )
    
    assert export_data['format'] == 'pdf'
    assert len(export_data['content']) > 0
```