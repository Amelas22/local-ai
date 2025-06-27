# Enhanced Logging for Motion Drafting Process

## Overview

Added comprehensive logging throughout the motion drafting pipeline to help identify where timeout errors (like the WORKER TIMEOUT you experienced) are occurring. The enhanced logging provides detailed timing information, progress tracking, and timeout monitoring.

## Changes Made

### 1. Main API Endpoint (main.py)

Enhanced the `/draft-motion` endpoint with:

- **Request logging**: Parameters, outline structure, database info
- **Timing tracking**: Start/end times for each major step
- **Progress indicators**: Clear markers for each phase
- **Error context**: Detailed error information with request context
- **Box upload tracking**: Specific timing for file upload operations

Key log messages to watch for:
- `Starting motion draft for database: {database_name}`
- `Calling motion_drafter.draft_motion()`
- `Motion drafting completed`
- `Starting DOCX export...`
- `Starting Box upload`

### 2. Motion Drafter Core (motion_drafter.py)

Added detailed logging with `[MOTION_DRAFTER]` prefix for:

- **Phase tracking**: Each major phase (context retrieval, section drafting, review)
- **Section progress**: Individual section drafting with timing
- **AI agent calls**: Timing for each AI agent interaction
- **Database operations**: Search queries and results
- **Quality metrics**: Confidence scores, word counts, etc.

### 3. Timeout Monitoring System

Created new utility (`timeout_monitor.py`) with:

#### TimeoutMonitor Class
- Tracks operation duration
- Issues warnings at configurable thresholds (60s warning, 120s critical)
- Logs progress steps with timestamps
- Provides detailed summaries on completion or failure

#### ProgressTracker Class
- Tracks progress through multi-step processes
- Estimates remaining time based on average step duration
- Provides percentage completion updates

### 4. Enhanced Error Handling

Improved error logging with:
- **Exception context**: Full stack traces with `exc_info=True`
- **State information**: What was completed before the error
- **Timing data**: How long the process ran before failing
- **Progress summaries**: Where in the process the error occurred

## Log Messages to Monitor

### Normal Operation Flow

1. **API Start**: `Starting motion draft for database: {database_name}`
2. **Context Retrieval**: `[CONTEXT_RETRIEVAL] Starting context retrieval`
3. **Section Drafting**: `[MOTION_DRAFTER] === Drafting section {i+1}`
4. **Review Process**: `[REVIEW] Starting comprehensive review`
5. **Completion**: `[MOTION_DRAFTER] === MOTION DRAFTING COMPLETED ====`

### Timeout Warnings

1. **Warning (60s)**: `[TIMEOUT_MONITOR] Motion Drafting has been running for 60.0s`
2. **Critical (120s)**: `[TIMEOUT_MONITOR] Motion Drafting has been running for 120.0s`

### Progress Tracking

- **Section Progress**: `[PROGRESS] Motion Drafting - Step {x}/{total} (X.X%)`
- **Time Estimates**: `Elapsed: {time}, Estimated remaining: {time}`

### Error Indicators

- **Database Issues**: `[CONTEXT_RETRIEVAL] Error searching for '{query}'`
- **AI Agent Failures**: `[SECTION_DRAFTING] Error in CoT drafting`
- **Timeout Summary**: `[MOTION_DRAFTER] Timeout monitor summary: {...}`

## Identifying Timeout Causes

### If timeout occurs during:

1. **Context Retrieval** (`[CONTEXT_RETRIEVAL]` messages):
   - Database connection issues
   - Large number of search queries
   - Slow embedding generation

2. **Section Drafting** (`[SECTION_DRAFTING]` messages):
   - AI agent response delays
   - Complex sections requiring multiple expansions
   - Large content generation

3. **Review Process** (`[REVIEW]` messages):
   - Document quality issues requiring fixes
   - Citation verification delays
   - Consistency checking on large documents

4. **Box Upload** (`Starting Box upload` messages):
   - Network connectivity issues
   - Large file upload delays
   - Box API rate limiting

## Configuration

### Timeout Thresholds
- **Warning**: 60 seconds (configurable in TimeoutMonitor)
- **Critical**: 120 seconds (configurable in TimeoutMonitor)
- **Worker Timeout**: Typically 20-30 seconds (gunicorn configuration)

### Log Levels
- **INFO**: Normal progress and timing information
- **WARNING**: Timeout warnings and non-critical issues
- **ERROR**: Failures and exceptions
- **CRITICAL**: Severe timeout warnings
- **DEBUG**: Detailed operation information (query text, etc.)

## Recommended Monitoring

1. **Set up log aggregation** to collect these detailed logs
2. **Create alerts** for timeout warning messages
3. **Monitor section completion rates** to identify bottlenecks
4. **Track average operation times** to establish baselines
5. **Set up dashboards** for real-time process monitoring

## Next Steps

With this enhanced logging in place, you should be able to:

1. **Identify the exact step** where timeouts occur
2. **Measure timing** for each component of the process
3. **Detect patterns** in timeout occurrences
4. **Optimize specific bottlenecks** based on data
5. **Set appropriate timeout values** based on actual performance

The next time you see a worker timeout, check the logs for the most recent `[MOTION_DRAFTER]` or `[TIMEOUT_MONITOR]` message to see exactly where the process was when it timed out.