#!/bin/bash
# BMad Framework E2E Test Runner Script for Deficiency Analyzer Agent
# This script runs the FIXED e2e test that properly uses the BMad framework

set -e  # Exit on error

echo "=========================================="
echo "BMad Deficiency Analyzer E2E Test Runner"
echo "=========================================="
echo ""
echo "This test validates the BMad framework implementation"
echo "and ensures all commands are properly mapped to tasks."
echo ""

# Configuration
TEST_DIR="/app/src/ai_agents/bmad_framework/tests"
OUTPUT_DIR="/app/test_docs/output"
TIMESTAMP=$(date +%Y%m%d_%H%M%S)
LOG_FILE="$OUTPUT_DIR/bmad_e2e_test_log_$TIMESTAMP.txt"

# Ensure output directory exists
mkdir -p "$OUTPUT_DIR"

echo "Test Configuration:"
echo "  - Framework: BMad Agent Framework"
echo "  - RTP Document: /app/test_docs/RTP.pdf"
echo "  - Case Name: story1_4_test_database_bb623c92"
echo "  - Output Directory: $OUTPUT_DIR"
echo "  - Log File: $LOG_FILE"
echo ""

# Function to run a test and capture output
run_test() {
    local test_name=$1
    local test_file=$2
    
    echo "Running test: $test_name"
    echo "----------------------------------------"
    
    if python -m pytest "$test_file" -v -s --tb=short 2>&1 | tee -a "$LOG_FILE"; then
        echo "✓ $test_name PASSED" | tee -a "$LOG_FILE"
        return 0
    else
        echo "✗ $test_name FAILED" | tee -a "$LOG_FILE"
        return 1
    fi
    echo "" | tee -a "$LOG_FILE"
}

# Start logging
echo "BMad E2E Test Execution Log - $TIMESTAMP" > "$LOG_FILE"
echo "==========================================" >> "$LOG_FILE"
echo "" >> "$LOG_FILE"

# Check prerequisites
echo "Checking prerequisites..." | tee -a "$LOG_FILE"

# Check if RTP.pdf exists
if [ ! -f "/app/test_docs/RTP.pdf" ]; then
    echo "ERROR: RTP.pdf not found in /app/test_docs/" | tee -a "$LOG_FILE"
    exit 1
fi

# Check if Python environment is set up
if ! python -c "import pytest" 2>/dev/null; then
    echo "ERROR: pytest not installed" | tee -a "$LOG_FILE"
    exit 1
fi

# Check if BMad framework is available
if ! python -c "from src.ai_agents.bmad_framework import AgentLoader, AgentExecutor" 2>/dev/null; then
    echo "ERROR: BMad framework not properly installed" | tee -a "$LOG_FILE"
    exit 1
fi

echo "Prerequisites check passed ✓" | tee -a "$LOG_FILE"
echo "" | tee -a "$LOG_FILE"

# Run the FIXED BMad E2E test
echo "Starting BMad Framework E2E Test..." | tee -a "$LOG_FILE"
echo "" | tee -a "$LOG_FILE"

if run_test "BMad Framework Deficiency Analyzer Test" "$TEST_DIR/test_e2e_deficiency_analyzer_fixed.py"; then
    BMAD_STATUS="PASSED"
else
    BMAD_STATUS="FAILED"
fi

# Also run the original test for comparison (optional)
echo "" | tee -a "$LOG_FILE"
echo "Running original test for comparison..." | tee -a "$LOG_FILE"
echo "" | tee -a "$LOG_FILE"

if run_test "Original E2E Test (Comparison)" "$TEST_DIR/test_e2e_deficiency_analyzer.py"; then
    ORIGINAL_STATUS="PASSED"
else
    ORIGINAL_STATUS="FAILED"
fi

# Generate comparison report
COMPARISON_FILE="$OUTPUT_DIR/bmad_test_comparison_$TIMESTAMP.txt"
echo "========================================" > "$COMPARISON_FILE"
echo "BMad Framework Test Comparison Report" >> "$COMPARISON_FILE"
echo "========================================" >> "$COMPARISON_FILE"
echo "" >> "$COMPARISON_FILE"
echo "Execution Time: $(date)" >> "$COMPARISON_FILE"
echo "" >> "$COMPARISON_FILE"
echo "Test Results:" >> "$COMPARISON_FILE"
echo "  - BMad Framework Test: $BMAD_STATUS" >> "$COMPARISON_FILE"
echo "  - Original Test: $ORIGINAL_STATUS" >> "$COMPARISON_FILE"
echo "" >> "$COMPARISON_FILE"
echo "Key Differences:" >> "$COMPARISON_FILE"
echo "  - BMad test uses proper command-to-task mapping" >> "$COMPARISON_FILE"
echo "  - BMad test integrates with actual Clerk services" >> "$COMPARISON_FILE"
echo "  - BMad test validates framework usage" >> "$COMPARISON_FILE"
echo "" >> "$COMPARISON_FILE"

# Display summary
echo "" | tee -a "$LOG_FILE"
echo "========================================" | tee -a "$LOG_FILE"
echo "BMad Test Execution Complete!" | tee -a "$LOG_FILE"
echo "========================================" | tee -a "$LOG_FILE"
echo "" | tee -a "$LOG_FILE"
echo "Summary:" | tee -a "$LOG_FILE"
echo "  - BMad Framework Test: $BMAD_STATUS" | tee -a "$LOG_FILE"
echo "  - Original Test: $ORIGINAL_STATUS" | tee -a "$LOG_FILE"
echo "" | tee -a "$LOG_FILE"
echo "Output Files:" | tee -a "$LOG_FILE"
echo "  - Log: $LOG_FILE" | tee -a "$LOG_FILE"
echo "  - BMad Results: $OUTPUT_DIR/bmad_e2e_test_results_*.json" | tee -a "$LOG_FILE"
echo "  - BMad Summary: $OUTPUT_DIR/bmad_e2e_test_summary_*.txt" | tee -a "$LOG_FILE"
echo "  - Comparison: $COMPARISON_FILE" | tee -a "$LOG_FILE"
echo "" | tee -a "$LOG_FILE"

# Exit with appropriate status based on BMad test
if [ "$BMAD_STATUS" = "PASSED" ]; then
    echo "BMad framework test passed! ✓" | tee -a "$LOG_FILE"
    echo "The deficiency analyzer agent is properly integrated with BMad." | tee -a "$LOG_FILE"
    exit 0
else
    echo "BMad framework test failed." | tee -a "$LOG_FILE"
    echo "Please check the logs for details." | tee -a "$LOG_FILE"
    exit 1
fi