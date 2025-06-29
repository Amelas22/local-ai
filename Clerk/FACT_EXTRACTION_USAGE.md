# Fact Extraction Integration - Usage Guide

## Overview
The Clerk Legal AI System now includes integrated fact extraction that automatically processes documents to extract facts, parse depositions, index exhibits, and generate timelines while maintaining strict case isolation.

## Quick Start

### 1. First-Time Setup
Initialize the shared knowledge databases (Florida statutes and FMCSR):
```bash
python cli_injector.py --init-shared-knowledge
```
This only needs to be run once and will create shared collections accessible by all cases.

### 2. Process Documents with Full Fact Extraction
```bash
# Process a single case folder with fact extraction
python cli_injector.py --folder-id 123456789

# Process and generate a timeline
python cli_injector.py --folder-id 123456789 --generate-timeline

# Process multiple cases from a root folder
python cli_injector.py --root 987654321 --max-folders 5
```

### 3. Process Without Fact Extraction (Faster)
```bash
# Skip fact extraction for faster processing
python cli_injector.py --folder-id 123456789 --skip-facts
```

## What Gets Extracted

### 1. Facts
- **What**: Key factual statements from documents
- **Categories**: Procedural, substantive, evidentiary, medical, damages, timeline, party, expert, regulatory
- **Storage**: `{case_name}_facts` collection
- **Example**: "On January 15, 2024, the defendant's vehicle collided with plaintiff's car"

### 2. Deposition Citations
- **What**: Testimony with page:line references
- **Formats**: "Smith Dep. 45:12-23", "Deposition of John Smith, p. 45"
- **Storage**: `{case_name}_depositions` collection
- **Example**: "I saw him looking at his phone (Smith Dep. 45:12)"

### 3. Exhibits
- **What**: References to exhibits in documents
- **Formats**: "Exhibit A", "Ex. 12", "Plaintiff's Exhibit 3"
- **Storage**: `{case_name}_exhibits` collection
- **Types**: Photos, emails, contracts, medical records, reports

### 4. Timeline
- **What**: Chronological sequence of events
- **Generated**: After document processing if `--generate-timeline` is used
- **Output**: Markdown file in `timelines/` directory
- **Features**: Key dates, event sequence, date ranges

## Database Structure

### Case-Specific Collections (Isolated)
```
Smith_v_Jones_2024/
├── smith_v_jones_2024_facts         # Extracted facts
├── smith_v_jones_2024_depositions   # Deposition testimony
├── smith_v_jones_2024_exhibits      # Exhibit index
└── smith_v_jones_2024_timeline      # Chronological events
```

### Shared Knowledge (All Cases)
```
Shared/
├── florida_statutes      # Florida state law
└── fmcsr_regulations     # Federal motor carrier regulations
```

## Command Line Options

### Basic Options
- `--folder-id`: Process a single Box folder as a case
- `--root`: Process multiple case folders from a root folder
- `--max-documents`: Limit number of documents to process
- `--max-folders`: Limit number of folders (with --root)

### Fact Extraction Options
- `--skip-facts`: Disable fact extraction (faster processing)
- `--generate-timeline`: Create timeline after processing
- `--init-shared-knowledge`: Initialize shared legal databases

### Other Options
- `--dry-run`: Preview what would be processed
- `--no-context`: Skip context generation
- `--skip-cost-tracking`: Disable API cost tracking
- `--save-cost-report`: Save cost report after processing
- `--log-level`: Set logging level (DEBUG, INFO, WARNING, ERROR)

## Examples

### Example 1: Process New Case with Timeline
```bash
python cli_injector.py --folder-id 234567890 --generate-timeline --save-cost-report
```
This will:
- Process all PDFs in the folder
- Extract facts, depositions, and exhibits
- Generate a timeline in `timelines/Case_Name_timeline.md`
- Save an API cost report

### Example 2: Process Multiple Cases
```bash
python cli_injector.py --root 345678901 --max-folders 10 --max-documents 50
```
This will:
- Process up to 10 case folders
- Process up to 50 documents per case
- Extract facts from all documents

### Example 3: Quick Processing Without Facts
```bash
python cli_injector.py --folder-id 456789012 --skip-facts --no-context
```
This will:
- Process documents for vector search only
- Skip fact extraction and context generation
- Much faster processing

## Integration with Motion Drafter

The extracted facts are automatically available to the motion drafter:

```python
# During motion drafting, the system can:
1. Search case facts: "Find evidence of negligence"
2. Retrieve deposition testimony: "Get testimony about distracted driving"
3. Reference exhibits: "Find photos of vehicle damage"
4. Use timeline: "Create chronological narrative of events"
```

## Performance Considerations

### Processing Times (Approximate)
- Document chunking: 5-10 seconds per document
- Fact extraction: 10-20 seconds per document
- Deposition parsing: 5-10 seconds per deposition
- Exhibit indexing: 3-5 seconds per document
- Timeline generation: 10-30 seconds per case

### Optimization Tips
1. Use `--skip-facts` for initial bulk imports
2. Process depositions separately with fact extraction enabled
3. Use `--max-documents` for testing
4. Enable `--no-context` to skip context generation

## Troubleshooting

### Common Issues

1. **"Collection already exists" error**
   - This is normal - collections are created once per case
   - The system will use existing collections

2. **Slow processing**
   - Use `--skip-facts` for faster processing
   - Check your OpenAI API rate limits
   - Process in smaller batches with `--max-documents`

3. **Memory issues**
   - Process fewer documents at once
   - Restart between large batches
   - Monitor system memory usage

4. **Timeline not generating**
   - Ensure documents contain dates
   - Check that facts were extracted successfully
   - Verify case name matches across documents

### Verification

Run the test script to verify integration:
```bash
python test_fact_extraction_integration.py
```

## Security & Case Isolation

- **Guaranteed**: Each case's data is completely isolated
- **Validated**: Case names are sanitized to prevent injection
- **Auditable**: All access attempts are logged
- **Shared Access**: Only regulatory databases are shared

## Next Steps

1. **Process Your Cases**: Start with a small test folder
2. **Review Extracted Facts**: Check the quality of extraction
3. **Generate Timelines**: Use for case chronologies
4. **Integrate with Motions**: Use facts in motion drafting

## API Usage in Code

```python
from src.ai_agents.fact_extractor import FactExtractor
from src.document_processing.deposition_parser import DepositionParser
from src.utils.timeline_generator import TimelineGenerator

# Search facts for a case
fact_extractor = FactExtractor("Smith_v_Jones_2024")
facts = await fact_extractor.search_facts("negligence", limit=10)

# Search deposition testimony
depo_parser = DepositionParser("Smith_v_Jones_2024")
testimony = await depo_parser.search_testimony("speed", deponent_filter="John Smith")

# Generate timeline
timeline_gen = TimelineGenerator("Smith_v_Jones_2024")
timeline = await timeline_gen.generate_timeline()
narrative = timeline_gen.generate_narrative_timeline(timeline)
```

The fact extraction system is now fully integrated and ready to enhance your legal motion drafting with structured, searchable evidence!