#!/usr/bin/env python3
"""Extract text from deficiency letter PDF for analysis."""

import os
import sys
import subprocess

# Install required packages if not available
try:
    import pdfplumber
except ImportError:
    print("Installing pdfplumber...")
    subprocess.check_call([sys.executable, "-m", "pip", "install", "pdfplumber"])
    import pdfplumber

def extract_pdf_text(pdf_path):
    """Extract text from PDF file."""
    try:
        with pdfplumber.open(pdf_path) as pdf:
            full_text = []
            for i, page in enumerate(pdf.pages):
                print(f"=== PAGE {i+1} ===")
                text = page.extract_text()
                if text:
                    print(text)
                    full_text.append(text)
                print()
            return "\n\n".join(full_text)
    except Exception as e:
        print(f"Error extracting PDF: {e}")
        return None

if __name__ == "__main__":
    pdf_path = "/mnt/d/jrl/GitHub Repos/local-ai/examples/LT DAT re discovery (10 day)-109533.pdf"
    extract_pdf_text(pdf_path)