"""
Unit tests for temporary file management.
"""

import pytest
import asyncio
import os
from pathlib import Path
from datetime import datetime, timedelta
from unittest.mock import Mock, patch, AsyncMock

from src.utils.temp_file_manager import (
    TempFileManager,
    get_temp_file_manager,
    startup_cleanup,
    shutdown_cleanup,
    CLEANUP_AGE_HOURS,
)


class TestTempFileManager:
    """Test the TempFileManager class."""

    @pytest.fixture
    def temp_manager(self):
        """Create a temp file manager for testing."""
        return TempFileManager()

    @pytest.mark.asyncio
    async def test_save_temp_file(self, temp_manager):
        """Test saving a temporary file."""
        content = b"Test PDF content"
        filename = "test_document.pdf"
        processing_id = "test-proc-123"

        file_id, file_path = await temp_manager.save_temp_file(
            content=content,
            filename=filename,
            processing_id=processing_id,
            file_type="rtp",
        )

        assert file_id is not None
        assert file_path is not None
        assert os.path.exists(file_path)

        # Verify content
        with open(file_path, "rb") as f:
            saved_content = f.read()
        assert saved_content == content

        # Verify registry entry
        assert file_id in temp_manager._file_registry
        file_info = temp_manager._file_registry[file_id]
        assert file_info["filename"] == filename
        assert file_info["processing_id"] == processing_id
        assert file_info["file_type"] == "rtp"
        assert file_info["size_bytes"] == len(content)

        # Cleanup
        await temp_manager.cleanup_temp_files(processing_id=processing_id)

    def test_get_temp_file_path(self, temp_manager):
        """Test retrieving temp file path."""
        # Add a mock entry to registry
        file_id = "test-file-123"
        file_path = str(temp_manager.temp_dir / "test_file.pdf")

        # Create the actual file
        with open(file_path, "wb") as f:
            f.write(b"test content")

        temp_manager._file_registry[file_id] = {
            "path": file_path,
            "filename": "test_file.pdf",
            "processing_id": "test-proc",
            "file_type": "document",
            "created_at": datetime.utcnow().isoformat(),
            "size_bytes": 12,
        }

        # Test retrieval
        retrieved_path = temp_manager.get_temp_file_path(file_id)
        assert retrieved_path == file_path

        # Test non-existent ID
        assert temp_manager.get_temp_file_path("non-existent") is None

        # Cleanup
        os.unlink(file_path)

    def test_get_temp_file_path_missing_file(self, temp_manager):
        """Test retrieving path when file is missing."""
        file_id = "test-file-456"
        file_path = "/path/that/does/not/exist.pdf"

        temp_manager._file_registry[file_id] = {
            "path": file_path,
            "filename": "missing.pdf",
            "processing_id": "test-proc",
            "file_type": "document",
            "created_at": datetime.utcnow().isoformat(),
            "size_bytes": 0,
        }

        # Should return None and remove from registry
        result = temp_manager.get_temp_file_path(file_id)
        assert result is None
        assert file_id not in temp_manager._file_registry

    @pytest.mark.asyncio
    async def test_cleanup_by_processing_id(self, temp_manager):
        """Test cleanup of files by processing ID."""
        processing_id = "test-proc-cleanup"
        other_proc_id = "other-proc"

        # Create files for target processing ID
        file1_id, file1_path = await temp_manager.save_temp_file(
            b"content1", "file1.pdf", processing_id, "rtp"
        )
        file2_id, file2_path = await temp_manager.save_temp_file(
            b"content2", "file2.pdf", processing_id, "oc_response"
        )

        # Create file for different processing ID
        file3_id, file3_path = await temp_manager.save_temp_file(
            b"content3", "file3.pdf", other_proc_id, "document"
        )

        # Cleanup only target processing ID
        cleaned = await temp_manager.cleanup_temp_files(processing_id=processing_id)

        assert cleaned == 2
        assert not os.path.exists(file1_path)
        assert not os.path.exists(file2_path)
        assert os.path.exists(file3_path)  # Should still exist

        assert file1_id not in temp_manager._file_registry
        assert file2_id not in temp_manager._file_registry
        assert file3_id in temp_manager._file_registry

        # Cleanup remaining
        await temp_manager.cleanup_temp_files(processing_id=other_proc_id)

    @pytest.mark.asyncio
    async def test_cleanup_orphaned_files(self, temp_manager):
        """Test cleanup of orphaned files."""
        # Create an old orphaned file
        old_file = temp_manager.temp_dir / "old_orphan.pdf"
        with open(old_file, "wb") as f:
            f.write(b"old content")

        # Modify its timestamp to be old
        old_time = datetime.utcnow() - timedelta(hours=CLEANUP_AGE_HOURS + 1)
        os.utime(old_file, (old_time.timestamp(), old_time.timestamp()))

        # Create a recent orphaned file
        new_file = temp_manager.temp_dir / "new_orphan.pdf"
        with open(new_file, "wb") as f:
            f.write(b"new content")

        # Run orphaned file cleanup
        cleaned = await temp_manager._cleanup_orphaned_files(force=False)

        assert cleaned >= 1
        assert not old_file.exists()
        assert new_file.exists()  # Should still exist (too recent)

        # Force cleanup
        cleaned = await temp_manager._cleanup_orphaned_files(force=True)
        assert not new_file.exists()

    @pytest.mark.asyncio
    async def test_temp_file_context(self, temp_manager):
        """Test temp file context manager."""
        processing_id = "test-proc-context"
        file_paths = []

        async with temp_manager.temp_file_context(processing_id) as tfm:
            # Save files within context
            file1_id, file1_path = await tfm.save_temp_file(
                b"content1", "file1.pdf", processing_id, "rtp"
            )
            file2_id, file2_path = await tfm.save_temp_file(
                b"content2", "file2.pdf", processing_id, "oc_response"
            )

            file_paths = [file1_path, file2_path]

            # Files should exist within context
            assert all(os.path.exists(p) for p in file_paths)

        # Files should be cleaned up after context
        assert not any(os.path.exists(p) for p in file_paths)

    @pytest.mark.asyncio
    async def test_background_cleanup_task(self, temp_manager):
        """Test background cleanup task."""
        # Start background cleanup
        await temp_manager.start_background_cleanup()
        assert temp_manager._cleanup_task is not None
        assert not temp_manager._cleanup_task.done()

        # Stop background cleanup
        await temp_manager.stop_background_cleanup()
        assert temp_manager._cleanup_task.done()

    @pytest.mark.asyncio
    async def test_concurrent_file_operations(self, temp_manager):
        """Test concurrent file save operations."""
        processing_id = "test-proc-concurrent"

        async def save_file(index):
            return await temp_manager.save_temp_file(
                f"content{index}".encode(),
                f"file{index}.pdf",
                processing_id,
                "document",
            )

        # Save multiple files concurrently
        tasks = [save_file(i) for i in range(5)]
        results = await asyncio.gather(*tasks)

        assert len(results) == 5
        assert len(temp_manager._file_registry) >= 5

        # All files should exist
        for file_id, file_path in results:
            assert os.path.exists(file_path)

        # Cleanup
        await temp_manager.cleanup_temp_files(processing_id=processing_id)


class TestGlobalFunctions:
    """Test global temp file manager functions."""

    def test_get_temp_file_manager_singleton(self):
        """Test that get_temp_file_manager returns singleton."""
        manager1 = get_temp_file_manager()
        manager2 = get_temp_file_manager()

        assert manager1 is manager2

    @pytest.mark.asyncio
    async def test_startup_cleanup(self):
        """Test startup cleanup function."""
        with patch("src.utils.temp_file_manager.get_temp_file_manager") as mock_get:
            mock_manager = Mock()
            mock_manager._cleanup_orphaned_files = AsyncMock(return_value=3)
            mock_manager.start_background_cleanup = AsyncMock()
            mock_get.return_value = mock_manager

            await startup_cleanup()

            mock_manager._cleanup_orphaned_files.assert_called_once_with(force=False)
            mock_manager.start_background_cleanup.assert_called_once()

    @pytest.mark.asyncio
    async def test_shutdown_cleanup(self):
        """Test shutdown cleanup function."""
        with patch("src.utils.temp_file_manager.get_temp_file_manager") as mock_get:
            mock_manager = Mock()
            mock_manager.stop_background_cleanup = AsyncMock()
            mock_get.return_value = mock_manager

            await shutdown_cleanup()

            mock_manager.stop_background_cleanup.assert_called_once()


class TestErrorHandling:
    """Test error handling in temp file manager."""

    @pytest.mark.asyncio
    async def test_save_file_error(self, temp_manager):
        """Test error handling during file save."""
        # Make temp_dir read-only to trigger error
        with patch.object(Path, "open", side_effect=PermissionError("No write access")):
            with pytest.raises(PermissionError):
                await temp_manager.save_temp_file(
                    b"content", "test.pdf", "test-proc", "document"
                )

    @pytest.mark.asyncio
    async def test_cleanup_error_handling(self, temp_manager):
        """Test error handling during cleanup."""
        # Add a file to registry that can't be deleted
        file_id = "test-file-error"
        file_path = str(temp_manager.temp_dir / "undeletable.pdf")

        # Create file
        with open(file_path, "wb") as f:
            f.write(b"content")

        temp_manager._file_registry[file_id] = {
            "path": file_path,
            "processing_id": "test-proc",
            "filename": "undeletable.pdf",
            "file_type": "document",
            "created_at": datetime.utcnow().isoformat(),
            "size_bytes": 7,
        }

        # Mock unlink to raise error
        with patch("os.unlink", side_effect=PermissionError("Can't delete")):
            # Should handle error gracefully
            cleaned = await temp_manager.cleanup_temp_files(processing_id="test-proc")

            # File should still be in registry due to error
            assert file_id in temp_manager._file_registry

        # Actual cleanup
        os.unlink(file_path)


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
