#!/usr/bin/env python3
"""
Test runner for discovery processing feature tests
"""
import subprocess
import sys
import os

def run_tests():
    """Run all discovery-related tests"""
    print("🧪 Running Discovery Processing Tests...")
    print("=" * 80)
    
    # Test categories
    test_suites = [
        {
            "name": "Discovery Endpoint Unit Tests",
            "path": "src/api/tests/test_discovery_endpoints.py",
            "markers": ""
        },
        {
            "name": "Discovery Splitter Unit Tests", 
            "path": "src/document_processing/tests/test_discovery_splitter.py",
            "markers": ""
        },
        {
            "name": "Discovery Integration Tests",
            "path": "tests/integration/test_discovery_integration.py",
            "markers": "-m integration"
        }
    ]
    
    all_passed = True
    results = []
    
    for suite in test_suites:
        print(f"\n📋 Running: {suite['name']}")
        print("-" * 40)
        
        cmd = [
            "python", "-m", "pytest",
            suite['path'],
            "-v",
            "--tb=short",
            "--no-header"
        ]
        
        if suite['markers']:
            cmd.append(suite['markers'])
        
        try:
            result = subprocess.run(
                cmd,
                capture_output=True,
                text=True,
                cwd="/app"  # Run from container root
            )
            
            if result.returncode == 0:
                print(f"✅ {suite['name']}: PASSED")
                # Show test summary
                output_lines = result.stdout.split('\n')
                for line in output_lines:
                    if "passed" in line and "warning" in line:
                        print(f"   {line.strip()}")
            else:
                print(f"❌ {suite['name']}: FAILED")
                all_passed = False
                # Show failures
                print("\nFailure details:")
                print(result.stdout)
                if result.stderr:
                    print("Errors:")
                    print(result.stderr)
            
            results.append({
                "suite": suite['name'],
                "passed": result.returncode == 0,
                "output": result.stdout
            })
            
        except Exception as e:
            print(f"❌ {suite['name']}: ERROR - {str(e)}")
            all_passed = False
            results.append({
                "suite": suite['name'],
                "passed": False,
                "output": str(e)
            })
    
    # Summary
    print("\n" + "=" * 80)
    print("📊 TEST SUMMARY")
    print("=" * 80)
    
    for result in results:
        status = "✅ PASSED" if result['passed'] else "❌ FAILED"
        print(f"{result['suite']}: {status}")
    
    if all_passed:
        print("\n🎉 All tests passed!")
        return 0
    else:
        print("\n❌ Some tests failed. Please review the output above.")
        return 1

def run_specific_test(test_name):
    """Run a specific test file or test case"""
    print(f"🧪 Running specific test: {test_name}")
    
    cmd = [
        "python", "-m", "pytest",
        test_name,
        "-v",
        "-s",  # Don't capture output
        "--tb=short"
    ]
    
    result = subprocess.run(cmd, cwd="/app")
    return result.returncode

if __name__ == "__main__":
    if len(sys.argv) > 1:
        # Run specific test
        exit_code = run_specific_test(sys.argv[1])
    else:
        # Run all discovery tests
        exit_code = run_tests()
    
    sys.exit(exit_code)