#!/usr/bin/env python3
"""
Examine PDF content to understand why boundaries aren't being detected
"""

import pdfplumber

pdf_path = "/tmp/tesdoc_Redacted.pdf"

print("Examining PDF content...")
print("=" * 80)

with pdfplumber.open(pdf_path) as pdf:
    print(f"Total pages: {len(pdf.pages)}")
    print("\nFirst 5 pages preview:\n")
    
    for i in range(min(5, len(pdf.pages))):
        page = pdf.pages[i]
        text = page.extract_text() or ""
        
        print(f"\n--- Page {i+1} ---")
        # Show first 500 characters
        preview = text[:500].strip()
        if preview:
            print(preview)
            if len(text) > 500:
                print("...")
        else:
            print("[No text content]")
        
        # Check for potential document markers
        print(f"\nPage characteristics:")
        print(f"  - Text length: {len(text)} chars")
        print(f"  - Has 'DEPOSITION': {'DEPOSITION' in text.upper()}")
        print(f"  - Has 'EXHIBIT': {'EXHIBIT' in text.upper()}")
        print(f"  - Has 'Page 1': {'PAGE 1' in text.upper() or 'Page 1' in text}")
        print(f"  - Has email headers: {'From:' in text or 'Subject:' in text}")
        print(f"  - Has form markers: {'FORM' in text.upper()}")