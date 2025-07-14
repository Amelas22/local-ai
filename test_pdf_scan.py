#!/usr/bin/env python3
"""
Check if PDF is scanned/image-based
"""

import pdfplumber

pdf_path = "/tmp/tesdoc_Redacted.pdf"

print("Checking PDF type...")
print("=" * 80)

with pdfplumber.open(pdf_path) as pdf:
    print(f"Total pages: {len(pdf.pages)}")
    
    # Check multiple pages for text
    pages_with_text = 0
    pages_with_images = 0
    
    for i, page in enumerate(pdf.pages):
        text = page.extract_text() or ""
        if text.strip():
            pages_with_text += 1
            
        # Check for images
        if hasattr(page, 'images') and page.images:
            pages_with_images += 1
    
    print(f"\nPages with extractable text: {pages_with_text}")
    print(f"Pages with images: {pages_with_images}")
    
    if pages_with_text == 0 and pages_with_images > 0:
        print("\n⚠️  This appears to be a scanned PDF without OCR!")
        print("Text extraction won't work without OCR processing.")
    elif pages_with_text == 0:
        print("\n⚠️  No text found in any pages!")
        print("The PDF might be corrupted or use an unsupported format.")
    
    # Try different extraction methods on page 10
    print("\n\nTrying page 10 with different methods:")
    if len(pdf.pages) > 9:
        page = pdf.pages[9]
        
        # Method 1: Standard text extraction
        text = page.extract_text() or ""
        print(f"Standard extraction: {len(text)} chars")
        
        # Method 2: Extract words
        if hasattr(page, 'extract_words'):
            words = page.extract_words()
            print(f"Word extraction: {len(words)} words")
            if words:
                print(f"First few words: {[w['text'] for w in words[:5]]}")
        
        # Method 3: Check for chars
        if hasattr(page, 'chars'):
            chars = page.chars
            print(f"Character extraction: {len(chars)} chars")
            if chars:
                sample_text = ''.join([c['text'] for c in chars[:50]])
                print(f"First 50 chars: {sample_text}")