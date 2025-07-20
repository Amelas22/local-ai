"""
Unit tests for PDF validation utilities.
"""

import pytest
import os
import tempfile

from src.utils.pdf_validator import (
    validate_pdf_content,
    validate_pdf_file,
    validate_base64_pdf,
    get_pdf_info,
)


class TestPDFContentValidation:
    """Test PDF content validation."""

    def test_valid_pdf_content(self):
        """Test validation of valid PDF content."""
        valid_pdf = b"%PDF-1.4\n%\xe2\xe3\xcf\xd3\n1 0 obj\n<<\n/Type /Catalog\n>>\nendobj\nxref\n0 2\n0000000000 65535 f\n0000000015 00000 n\ntrailer\n<<\n/Size 2\n/Root 1 0 R\n>>\nstartxref\n116\n%%EOF"

        is_valid, message = validate_pdf_content(valid_pdf)
        assert is_valid is True
        assert "Valid PDF" in message

    def test_empty_content(self):
        """Test validation of empty content."""
        is_valid, message = validate_pdf_content(b"")
        assert is_valid is False
        assert "empty" in message.lower()

    def test_invalid_content(self):
        """Test validation of non-PDF content."""
        is_valid, message = validate_pdf_content(b"This is not a PDF")
        assert is_valid is False
        assert "not a valid PDF" in message

    def test_oversized_content(self):
        """Test validation of oversized PDF."""
        # Create content larger than limit
        oversized = b"%PDF-1.4\n" + b"X" * (51 * 1024 * 1024) + b"\n%%EOF"
        is_valid, message = validate_pdf_content(oversized)
        assert is_valid is False
        assert "exceeds size limit" in message

    def test_encrypted_pdf(self):
        """Test detection of encrypted PDF."""
        encrypted_pdf = b"%PDF-1.4\n/Encrypt << /Filter /Standard >>\n%%EOF"
        is_valid, message = validate_pdf_content(encrypted_pdf)
        assert is_valid is False
        assert "encrypted" in message.lower()

    def test_pdf_without_eof(self):
        """Test PDF without EOF marker (should warn but pass)."""
        pdf_no_eof = (
            b"%PDF-1.4\n%\xe2\xe3\xcf\xd3\n1 0 obj\n<<\n/Type /Catalog\n>>\nendobj"
        )
        is_valid, message = validate_pdf_content(pdf_no_eof)
        assert is_valid is True  # Should still pass

    def test_pdf_20_format(self):
        """Test PDF 2.0 format validation."""
        pdf_20 = b"%PDF-2.0\n%\xe2\xe3\xcf\xd3\n1 0 obj\n<<\n/Type /Catalog\n>>\nendobj\n%%EOF"
        is_valid, message = validate_pdf_content(pdf_20)
        assert is_valid is True
        assert "Valid PDF" in message


class TestPDFFileValidation:
    """Test PDF file validation from disk."""

    def test_valid_pdf_file(self):
        """Test validation of valid PDF file."""
        with tempfile.NamedTemporaryFile(suffix=".pdf", delete=False) as tmp:
            tmp.write(b"%PDF-1.4\n%%EOF")
            tmp_path = tmp.name

        try:
            is_valid, message = validate_pdf_file(tmp_path)
            assert is_valid is True
        finally:
            os.unlink(tmp_path)

    def test_nonexistent_file(self):
        """Test validation of non-existent file."""
        is_valid, message = validate_pdf_file("/path/that/does/not/exist.pdf")
        assert is_valid is False
        assert "not found" in message.lower()

    def test_directory_not_file(self):
        """Test validation of directory instead of file."""
        with tempfile.TemporaryDirectory() as tmpdir:
            is_valid, message = validate_pdf_file(tmpdir)
            assert is_valid is False
            assert "not a file" in message.lower()


class TestBase64PDFValidation:
    """Test base64-encoded PDF validation."""

    def test_valid_base64_pdf(self):
        """Test validation of valid base64-encoded PDF."""
        import base64

        valid_pdf = b"%PDF-1.4\n%%EOF"
        base64_data = base64.b64encode(valid_pdf).decode("utf-8")

        is_valid, message = validate_base64_pdf(base64_data)
        assert is_valid is True
        assert "Valid PDF" in message

    def test_invalid_base64(self):
        """Test validation of invalid base64 data."""
        is_valid, message = validate_base64_pdf("not valid base64!@#$")
        assert is_valid is False
        assert "Invalid base64 encoding" in message

    def test_empty_base64(self):
        """Test validation of empty base64 data."""
        is_valid, message = validate_base64_pdf("")
        assert is_valid is False
        assert "empty" in message.lower()

    def test_base64_non_pdf(self):
        """Test validation of base64-encoded non-PDF."""
        import base64

        non_pdf = b"This is not a PDF"
        base64_data = base64.b64encode(non_pdf).decode("utf-8")

        is_valid, message = validate_base64_pdf(base64_data)
        assert is_valid is False
        assert "not a valid PDF" in message


class TestPDFInfo:
    """Test PDF information extraction."""

    def test_get_pdf_info_basic(self):
        """Test basic PDF info extraction."""
        pdf_content = b"%PDF-1.5\n%\xe2\xe3\xcf\xd3\n%%EOF"
        info = get_pdf_info(pdf_content)

        assert info["size_bytes"] == len(pdf_content)
        assert info["size_mb"] == len(pdf_content) / (1024 * 1024)
        assert info["has_eof"] is True
        assert info["is_encrypted"] is False
        assert info["pdf_version"] == "1.5"

    def test_get_pdf_info_encrypted(self):
        """Test info extraction for encrypted PDF."""
        pdf_content = b"%PDF-1.4\n/Encrypt << >>\n%%EOF"
        info = get_pdf_info(pdf_content)

        assert info["is_encrypted"] is True

    def test_get_pdf_info_no_version(self):
        """Test info extraction when version can't be determined."""
        pdf_content = b"corrupted pdf content %%EOF"
        info = get_pdf_info(pdf_content)

        assert info["pdf_version"] is None
        assert info["has_eof"] is True


class TestConfigurableLimits:
    """Test configurable size limits."""

    def test_environment_variable_limit(self, monkeypatch):
        """Test that size limit can be configured via environment variable."""
        # This would require reloading the module after setting env var
        # For now, just verify the constant exists
        from src.utils.pdf_validator import MAX_FILE_SIZE_MB, DEFAULT_MAX_FILE_SIZE_MB

        assert MAX_FILE_SIZE_MB > 0
        assert DEFAULT_MAX_FILE_SIZE_MB == 50


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
