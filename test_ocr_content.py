#!/usr/bin/env python3
"""
Examine OCR'd PDF content to understand document structure
"""

import pdfplumber

pdf_path = "/tmp/tesdoc_Redacted_ocr.pdf"

print("Examining OCR'd PDF content...")
print("=" * 80)

with pdfplumber.open(pdf_path) as pdf:
    print(f"Total pages: {len(pdf.pages)}")
    
    # Look for document boundaries every few pages
    for i in range(0, len(pdf.pages), 5):
        page = pdf.pages[i]
        text = page.extract_text() or ""
        
        print(f"\n--- Page {i+1} ---")
        # Show first 300 characters
        preview = text[:300].strip()
        if preview:
            print(preview)
            if len(text) > 300:
                print("...")
        else:
            print("[No text content]")
        
        # Check for document markers
        print(f"\nDocument markers:")
        print(f"  - APPLICATION: {'APPLICATION' in text.upper()}")
        print(f"  - DRIVER: {'DRIVER' in text.upper()}")
        print(f"  - DEPOSITION: {'DEPOSITION' in text.upper()}")
        print(f"  - INVOICE: {'INVOICE' in text.upper()}")
        print(f"  - CONTRACT: {'CONTRACT' in text.upper()}")
        print(f"  - Page numbering: {any(p in text for p in ['Page 1', 'PAGE 1', '1 of'])}")
        
    # Check for major transitions
    print("\n\n=== Checking for document transitions ===")
    for i in range(1, min(20, len(pdf.pages))):
        curr_text = pdf.pages[i].extract_text() or ""
        prev_text = pdf.pages[i-1].extract_text() or ""
        
        # Look for significant changes
        if 'APPLICATION' in curr_text.upper() and 'APPLICATION' not in prev_text.upper():
            print(f"  - Page {i+1}: New APPLICATION detected")
        if 'DRIVER' in curr_text.upper() and 'DRIVER' not in prev_text.upper():
            print(f"  - Page {i+1}: New DRIVER document detected")
        if 'Page 1' in curr_text or 'PAGE 1' in curr_text:
            print(f"  - Page {i+1}: Page numbering reset detected")