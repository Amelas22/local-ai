#!/usr/bin/env python3
"""
Verify that all test files are properly structured and can be imported
"""
import os
import ast
import sys

def verify_test_file(filepath):
    """Verify a test file has proper structure"""
    print(f"\n📄 Checking: {filepath}")
    
    try:
        with open(filepath, 'r') as f:
            content = f.read()
        
        # Parse the AST
        tree = ast.parse(content)
        
        # Find test classes and functions
        test_classes = []
        test_functions = []
        
        for node in ast.walk(tree):
            if isinstance(node, ast.ClassDef) and node.name.startswith('Test'):
                test_classes.append(node.name)
                # Find test methods in class
                for item in node.body:
                    if isinstance(item, ast.FunctionDef) and item.name.startswith('test_'):
                        test_functions.append(f"{node.name}.{item.name}")
            elif isinstance(node, ast.FunctionDef) and node.name.startswith('test_'):
                test_functions.append(node.name)
        
        print(f"  ✅ Valid Python syntax")
        print(f"  📦 Test classes found: {len(test_classes)}")
        for cls in test_classes:
            print(f"     - {cls}")
        print(f"  🧪 Test functions found: {len(test_functions)}")
        for func in test_functions[:5]:  # Show first 5
            print(f"     - {func}")
        if len(test_functions) > 5:
            print(f"     ... and {len(test_functions) - 5} more")
        
        return True
        
    except SyntaxError as e:
        print(f"  ❌ Syntax error: {e}")
        return False
    except Exception as e:
        print(f"  ❌ Error: {e}")
        return False

def main():
    """Check all discovery test files"""
    print("🔍 Verifying Discovery Test Structure")
    print("=" * 60)
    
    test_files = [
        "/mnt/c/Users/jlemr/Test2/local-ai-package/Clerk/src/api/tests/test_discovery_endpoints.py",
        "/mnt/c/Users/jlemr/Test2/local-ai-package/Clerk/src/document_processing/tests/test_discovery_splitter.py",
        "/mnt/c/Users/jlemr/Test2/local-ai-package/Clerk/tests/integration/test_discovery_integration.py"
    ]
    
    all_valid = True
    
    for test_file in test_files:
        if os.path.exists(test_file):
            if not verify_test_file(test_file):
                all_valid = False
        else:
            print(f"\n❌ File not found: {test_file}")
            all_valid = False
    
    print("\n" + "=" * 60)
    if all_valid:
        print("✅ All test files are properly structured!")
        print("\n📝 Next steps:")
        print("1. Run the tests inside Docker container:")
        print("   ./run_discovery_tests_docker.sh")
        print("\n2. Or manually inside the container:")
        print("   docker-compose -p localai exec clerk bash")
        print("   python -m pytest src/api/tests/test_discovery_endpoints.py -v")
    else:
        print("❌ Some test files have issues. Please fix them before running tests.")
    
    return 0 if all_valid else 1

if __name__ == "__main__":
    sys.exit(main())