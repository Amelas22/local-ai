"""
PDF validation utilities for discovery processing.

This module provides validation for PDF files including
type checking, size limits, and content validation.
"""

import os
from typing import Tuple, Optional
from pathlib import Path

from ..utils.logger import setup_logger

logger = setup_logger(__name__)

# Configuration
DEFAULT_MAX_FILE_SIZE_MB = 50
MAX_FILE_SIZE_MB = int(
    os.getenv("DISCOVERY_MAX_FILE_SIZE_MB", DEFAULT_MAX_FILE_SIZE_MB)
)
MAX_FILE_SIZE_BYTES = MAX_FILE_SIZE_MB * 1024 * 1024

# PDF magic numbers (file signatures)
PDF_MAGIC_NUMBERS = [
    b"%PDF-1.",  # Standard PDF header
    b"%PDF-2.",  # PDF 2.0
]


class PDFValidationError(Exception):
    """Custom exception for PDF validation errors."""

    pass


def validate_pdf_content(
    content: bytes, filename: Optional[str] = None
) -> Tuple[bool, str]:
    """
    Validate PDF file content.

    Args:
        content: File content as bytes
        filename: Optional filename for better error messages

    Returns:
        Tuple of (is_valid, message)
    """
    file_desc = filename or "file"

    # Check if content is empty
    if not content:
        return False, f"The {file_desc} is empty"

    # Check file size
    size_mb = len(content) / (1024 * 1024)
    if len(content) > MAX_FILE_SIZE_BYTES:
        return (
            False,
            f"The {file_desc} exceeds size limit ({size_mb:.1f}MB > {MAX_FILE_SIZE_MB}MB)",
        )

    # Check PDF magic number
    if not any(content.startswith(magic) for magic in PDF_MAGIC_NUMBERS):
        return False, f"The {file_desc} is not a valid PDF (invalid file signature)"

    # Basic structure check - look for EOF marker
    if not content.rstrip().endswith(b"%%EOF"):
        logger.warning(f"PDF {file_desc} missing EOF marker - may be truncated")
        # Don't fail on missing EOF as some PDFs may still be readable

    # Check for encrypted PDFs (basic check)
    if b"/Encrypt" in content:
        return False, f"The {file_desc} appears to be encrypted"

    logger.debug(f"PDF validation passed for {file_desc} ({size_mb:.1f}MB)")
    return True, f"Valid PDF ({size_mb:.1f}MB)"


def validate_pdf_file(file_path: str) -> Tuple[bool, str]:
    """
    Validate a PDF file from disk.

    Args:
        file_path: Path to the PDF file

    Returns:
        Tuple of (is_valid, message)
    """
    path = Path(file_path)

    # Check if file exists
    if not path.exists():
        return False, f"File not found: {file_path}"

    # Check if it's a file
    if not path.is_file():
        return False, f"Not a file: {file_path}"

    # Read and validate content
    try:
        with open(file_path, "rb") as f:
            content = f.read()
        return validate_pdf_content(content, path.name)
    except Exception as e:
        return False, f"Error reading file: {str(e)}"


def validate_base64_pdf(
    base64_data: str, filename: Optional[str] = None
) -> Tuple[bool, str]:
    """
    Validate a base64-encoded PDF.

    Args:
        base64_data: Base64-encoded PDF data
        filename: Optional filename for better error messages

    Returns:
        Tuple of (is_valid, message)
    """
    import base64

    file_desc = filename or "base64 data"

    # Check if empty
    if not base64_data:
        return False, f"The {file_desc} is empty"

    # Try to decode base64
    try:
        content = base64.b64decode(base64_data, validate=True)
    except Exception as e:
        return False, f"Invalid base64 encoding in {file_desc}: {str(e)}"

    # Validate the decoded content
    return validate_pdf_content(content, filename)


def get_pdf_info(content: bytes) -> dict:
    """
    Extract basic information from PDF content.

    Args:
        content: PDF file content as bytes

    Returns:
        Dictionary with PDF information
    """
    info = {
        "size_bytes": len(content),
        "size_mb": len(content) / (1024 * 1024),
        "has_eof": content.rstrip().endswith(b"%%EOF"),
        "is_encrypted": b"/Encrypt" in content,
        "pdf_version": None,
    }

    # Try to extract PDF version
    if content.startswith(b"%PDF-"):
        try:
            version_end = content.index(b"\n", 0, 20)
            version = content[5:version_end].decode("ascii").strip()
            info["pdf_version"] = version
        except:
            pass

    return info
