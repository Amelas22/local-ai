#!/usr/bin/env python3
"""
Diagnostic script to check the exact issue with arguments_by_category
"""

import requests
import json

print("🔍 Diagnosing Legal Motion API Issue")
print("=" * 40)

# Test motion
motion = {
    "motion_text": "Defendant moves to dismiss for lack of jurisdiction.",
    "case_context": "Diagnostic test"
}

# Make request
response = requests.post(
    "http://localhost:8000/api/v1/analyze-motion",
    json=motion,
    timeout=30
)

print(f"Status Code: {response.status_code}")

if response.status_code == 200:
    result = response.json()
    
    # Check all_arguments
    all_args = result.get('all_arguments', [])
    print(f"\n✓ Total arguments in all_arguments: {len(all_args)}")
    
    if all_args:
        first_arg = all_args[0]
        print(f"✓ First argument has {len(first_arg)} fields")
        print(f"  Fields: {list(first_arg.keys())[:5]}...")
    
    # Check arguments_by_category
    args_by_cat = result.get('arguments_by_category', {})
    print(f"\n✓ Categories found: {list(args_by_cat.keys())}")
    
    # Diagnose the issue
    issue_found = False
    for cat, args in args_by_cat.items():
        if args:
            first_cat_arg = args[0]
            required_fields = ['argument_id', 'argument_summary', 'category', 
                             'location_in_motion', 'strength_assessment']
            missing = [f for f in required_fields if f not in first_cat_arg]
            
            if missing:
                print(f"\n❌ ISSUE FOUND in '{cat}':")
                print(f"   Argument has only {len(first_cat_arg)} fields: {list(first_cat_arg.keys())}")
                print(f"   Missing required fields: {missing}")
                issue_found = True
            else:
                print(f"\n✅ '{cat}' arguments have all required fields")
    
    if not issue_found:
        print("\n✅ NO ISSUES FOUND - All arguments have required fields!")
        
    # Check argument_groups format
    groups = result.get('argument_groups', [])
    if groups and groups[0].get('arguments'):
        first_arg_in_group = groups[0]['arguments'][0]
        if isinstance(first_arg_in_group, str):
            print("\n✅ Argument groups correctly use IDs")
        else:
            print("\n❌ Argument groups incorrectly contain objects")
            
else:
    print(f"\n❌ Request failed: {response.status_code}")
    error = response.text[:500]
    
    # Look for specific validation errors
    if "Field required" in error:
        print("\nValidation errors found:")
        # Extract field names from error
        import re
        fields = re.findall(r'arguments_by_category\.[^.]+\.\d+\.(\w+)\s+Field required', error)
        unique_fields = list(set(fields))
        print(f"Missing fields: {unique_fields[:10]}")
        
print("\n" + "=" * 40)
print("This diagnostic shows exactly what fields are missing.")