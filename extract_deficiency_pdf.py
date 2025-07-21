#!/usr/bin/env python3
"""Extract text from deficiency letter PDF"""

import pdfplumber
import sys

pdf_path = sys.argv[1] if len(sys.argv) > 1 else "examples/LT DAT re discovery (10 day)-109533.pdf"

with pdfplumber.open(pdf_path) as pdf:
    for i, page in enumerate(pdf.pages[:5]):  # First 5 pages
        print(f"\n=== PAGE {i+1} ===\n")
        text = page.extract_text()
        if text:
            print(text)
        else:
            print("No text extracted from this page")