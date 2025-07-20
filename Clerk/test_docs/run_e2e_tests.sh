#!/bin/bash
# E2E Test Runner Script for Deficiency Analyzer Agent
# This script should be run from inside the Clerk Docker container

set -e  # Exit on error

echo "=========================================="
echo "Deficiency Analyzer E2E Test Runner"
echo "=========================================="
echo ""

# Configuration
TEST_DIR="/app/src/ai_agents/bmad_framework/tests"
OUTPUT_DIR="/app/test_docs/output"
TIMESTAMP=$(date +%Y%m%d_%H%M%S)
LOG_FILE="$OUTPUT_DIR/e2e_test_log_$TIMESTAMP.txt"

# Ensure output directory exists
mkdir -p "$OUTPUT_DIR"

echo "Test Configuration:"
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
    else
        echo "✗ $test_name FAILED" | tee -a "$LOG_FILE"
        return 1
    fi
    echo "" | tee -a "$LOG_FILE"
}

# Start logging
echo "E2E Test Execution Log - $TIMESTAMP" > "$LOG_FILE"
echo "==========================================" >> "$LOG_FILE"
echo "" >> "$LOG_FILE"

# Run the main E2E test
echo "Starting E2E Integration Tests..." | tee -a "$LOG_FILE"
echo "" | tee -a "$LOG_FILE"

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

echo "Prerequisites check passed ✓" | tee -a "$LOG_FILE"
echo "" | tee -a "$LOG_FILE"

# Run the main E2E test
if run_test "Full E2E Deficiency Analyzer Test" "$TEST_DIR/test_e2e_deficiency_analyzer.py"; then
    E2E_STATUS="PASSED"
else
    E2E_STATUS="FAILED"
fi

# Run additional integration tests
echo "" | tee -a "$LOG_FILE"
echo "Running additional integration tests..." | tee -a "$LOG_FILE"
echo "" | tee -a "$LOG_FILE"

# Component integration tests
if [ -f "$TEST_DIR/test_integration_components.py" ]; then
    run_test "Component Integration Tests" "$TEST_DIR/test_integration_components.py"
fi

# API integration tests
if [ -f "$TEST_DIR/test_integration_api.py" ]; then
    run_test "API Integration Tests" "$TEST_DIR/test_integration_api.py"
fi

# Generate summary report
SUMMARY_FILE="$OUTPUT_DIR/test_summary_$TIMESTAMP.txt"
echo "========================================" > "$SUMMARY_FILE"
echo "E2E Test Execution Summary" >> "$SUMMARY_FILE"
echo "========================================" >> "$SUMMARY_FILE"
echo "" >> "$SUMMARY_FILE"
echo "Execution Time: $(date)" >> "$SUMMARY_FILE"
echo "Main E2E Test: $E2E_STATUS" >> "$SUMMARY_FILE"
echo "" >> "$SUMMARY_FILE"
echo "Output Files:" >> "$SUMMARY_FILE"
echo "  - Log: $LOG_FILE" >> "$SUMMARY_FILE"
echo "  - Test Results: $OUTPUT_DIR/e2e_test_results_*.json" >> "$SUMMARY_FILE"
echo "  - Test Summary: $OUTPUT_DIR/e2e_test_summary_*.txt" >> "$SUMMARY_FILE"
echo "" >> "$SUMMARY_FILE"

# Display summary
echo "" | tee -a "$LOG_FILE"
echo "========================================" | tee -a "$LOG_FILE"
echo "Test Execution Complete!" | tee -a "$LOG_FILE"
echo "========================================" | tee -a "$LOG_FILE"
echo "" | tee -a "$LOG_FILE"
echo "Summary saved to: $SUMMARY_FILE" | tee -a "$LOG_FILE"
echo "Full log saved to: $LOG_FILE" | tee -a "$LOG_FILE"
echo "" | tee -a "$LOG_FILE"

# Exit with appropriate status
if [ "$E2E_STATUS" = "PASSED" ]; then
    echo "All tests completed successfully! ✓" | tee -a "$LOG_FILE"
    exit 0
else
    echo "Some tests failed. Please check the logs." | tee -a "$LOG_FILE"
    exit 1
fi