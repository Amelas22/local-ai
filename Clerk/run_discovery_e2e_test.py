#!/usr/bin/env python3
"""
Run the discovery processing end-to-end test

This script helps run the e2e test with proper environment setup and debugging output.
"""

import os
import sys
import subprocess
from pathlib import Path

# Add the project root to Python path
project_root = Path(__file__).parent
sys.path.insert(0, str(project_root))

def setup_test_environment():
    """Set up required environment variables for testing"""
    test_env = {
        # MVP Mode for testing
        "MVP_MODE": "true",
        
        # Test database settings (using mock)
        "SUPABASE_URL": "http://localhost:8000",
        "SUPABASE_ANON_KEY": "test-anon-key",
        "SUPABASE_SERVICE_ROLE_KEY": "test-service-key",
        
        # Qdrant settings (using mock)
        "QDRANT_HOST": "localhost",
        "QDRANT_PORT": "6333",
        "QDRANT_API_KEY": "test-api-key",
        "QDRANT_HTTPS": "false",
        
        # OpenAI settings (using mock)
        "OPENAI_API_KEY": "test-openai-key",
        "CONTEXT_LLM_MODEL": "gpt-3.5-turbo",
        
        # Discovery settings
        "DISCOVERY_BOUNDARY_MODEL": "gpt-4",
        "DISCOVERY_WINDOW_SIZE": "5",
        "DISCOVERY_WINDOW_OVERLAP": "1",
        "DISCOVERY_CONFIDENCE_THRESHOLD": "0.7",
        "DISCOVERY_CLASSIFICATION_MODEL": "gpt-4",
        
        # General settings
        "ENABLE_CASE_ISOLATION": "true",
        "MAX_CASE_NAME_LENGTH": "50",
        "CHUNK_SIZE": "1400",
        "CHUNK_OVERLAP": "200",
        
        # Logging
        "PYTHONUNBUFFERED": "1",
        "LOG_LEVEL": "DEBUG"
    }
    
    # Update environment
    os.environ.update(test_env)
    
    return test_env

def run_test():
    """Run the discovery e2e test with pytest"""
    print("Setting up test environment...")
    env = setup_test_environment()
    
    print("\nEnvironment variables set:")
    for key, value in env.items():
        if "KEY" in key or "PASSWORD" in key:
            print(f"  {key}: ***")
        else:
            print(f"  {key}: {value}")
    
    print("\nRunning discovery processing end-to-end test...")
    print("-" * 80)
    
    # Run pytest with verbose output and specific test
    cmd = [
        "python", "-m", "pytest",
        "src/api/tests/test_discovery_processing_e2e.py",
        "-v",
        "-s",  # Show print statements
        "--tb=short",  # Shorter traceback
        "-k", "test_complete_discovery_processing_flow"  # Run specific test first
    ]
    
    try:
        result = subprocess.run(cmd, check=True)
        print("\n" + "=" * 80)
        print("✅ All tests passed!")
        return 0
    except subprocess.CalledProcessError as e:
        print("\n" + "=" * 80)
        print(f"❌ Tests failed with exit code: {e.returncode}")
        return e.returncode

def run_single_test(test_name):
    """Run a specific test by name"""
    print(f"Running single test: {test_name}")
    
    cmd = [
        "python", "-m", "pytest",
        "src/api/tests/test_discovery_processing_e2e.py",
        "-v",
        "-s",
        "--tb=short",
        "-k", test_name
    ]
    
    return subprocess.run(cmd).returncode

if __name__ == "__main__":
    if len(sys.argv) > 1:
        # Run specific test if provided
        test_name = sys.argv[1]
        exit_code = run_single_test(test_name)
    else:
        # Run all e2e tests
        exit_code = run_test()
    
    sys.exit(exit_code)