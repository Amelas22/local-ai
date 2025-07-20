"""
Temporary file management for discovery processing.

This module handles temporary storage of RTP and OC response documents
during discovery processing, with automatic cleanup mechanisms.
"""

import os
import uuid
import tempfile
import asyncio
from pathlib import Path
from datetime import datetime, timedelta
from typing import Optional, Dict, Any, Tuple
from contextlib import asynccontextmanager

from ..utils.logger import setup_logger

logger = setup_logger(__name__)

# Configuration
TEMP_DIR_NAME = "clerk_discovery_temp"
CLEANUP_AGE_HOURS = 24  # Clean up files older than 24 hours
CLEANUP_INTERVAL_SECONDS = 3600  # Run cleanup every hour


class TempFileManager:
    """
    Manages temporary file storage for discovery processing.

    Features:
    - Thread-safe temporary file creation
    - Automatic cleanup of orphaned files
    - Crash recovery with startup cleanup
    - UUID-based file referencing
    """

    def __init__(self):
        """Initialize the temporary file manager."""
        self.temp_dir = self._ensure_temp_dir()
        self._file_registry: Dict[str, Dict[str, Any]] = {}
        self._cleanup_task: Optional[asyncio.Task] = None

    def _ensure_temp_dir(self) -> Path:
        """
        Ensure the temporary directory exists.

        Returns:
            Path to the temporary directory
        """
        temp_base = Path(tempfile.gettempdir())
        temp_dir = temp_base / TEMP_DIR_NAME
        temp_dir.mkdir(exist_ok=True)
        logger.info(f"Temporary directory ensured at: {temp_dir}")
        return temp_dir

    async def save_temp_file(
        self,
        content: bytes,
        filename: str,
        processing_id: str,
        file_type: str = "document",
    ) -> Tuple[str, str]:
        """
        Save content to a temporary file with UUID reference.

        Args:
            content: File content as bytes
            filename: Original filename for reference
            processing_id: Discovery processing ID
            file_type: Type of file (rtp, oc_response, etc.)

        Returns:
            Tuple of (file_id, file_path)
        """
        file_id = str(uuid.uuid4())
        safe_filename = f"{file_type}_{file_id}_{filename.replace(' ', '_')}"
        file_path = self.temp_dir / safe_filename

        try:
            # Write file
            with open(file_path, "wb") as f:
                f.write(content)

            # Register file
            self._file_registry[file_id] = {
                "path": str(file_path),
                "filename": filename,
                "processing_id": processing_id,
                "file_type": file_type,
                "created_at": datetime.utcnow().isoformat(),
                "size_bytes": len(content),
            }

            logger.info(
                f"Saved temp file: {file_id} -> {file_path} "
                f"({len(content)} bytes) for processing {processing_id}"
            )

            return file_id, str(file_path)

        except Exception as e:
            logger.error(f"Failed to save temp file: {e}")
            raise

    def get_temp_file_path(self, file_id: str) -> Optional[str]:
        """
        Get the path for a temporary file by ID.

        Args:
            file_id: UUID of the temporary file

        Returns:
            File path or None if not found
        """
        file_info = self._file_registry.get(file_id)
        if file_info:
            path = file_info["path"]
            if os.path.exists(path):
                return path
            else:
                logger.warning(
                    f"Temp file {file_id} registered but not found at {path}"
                )
                del self._file_registry[file_id]
        return None

    async def cleanup_temp_files(
        self, processing_id: Optional[str] = None, force: bool = False
    ) -> int:
        """
        Clean up temporary files.

        Args:
            processing_id: If specified, only clean files for this processing ID
            force: If True, remove all files regardless of age

        Returns:
            Number of files cleaned up
        """
        cleaned = 0

        # Clean from registry
        files_to_remove = []
        for file_id, file_info in self._file_registry.items():
            if processing_id and file_info["processing_id"] != processing_id:
                continue

            file_path = file_info["path"]
            try:
                if os.path.exists(file_path):
                    os.unlink(file_path)
                    logger.debug(f"Removed temp file: {file_path}")
                files_to_remove.append(file_id)
                cleaned += 1
            except Exception as e:
                logger.error(f"Failed to remove temp file {file_path}: {e}")

        # Remove from registry
        for file_id in files_to_remove:
            del self._file_registry[file_id]

        # Clean orphaned files from disk
        if force or not processing_id:
            cleaned += await self._cleanup_orphaned_files(force)

        logger.info(f"Cleaned up {cleaned} temporary files")
        return cleaned

    async def _cleanup_orphaned_files(self, force: bool = False) -> int:
        """
        Clean up orphaned files from the temp directory.

        Args:
            force: If True, remove all files regardless of age

        Returns:
            Number of files cleaned
        """
        cleaned = 0
        cutoff_time = datetime.utcnow() - timedelta(hours=CLEANUP_AGE_HOURS)

        try:
            for file_path in self.temp_dir.iterdir():
                if file_path.is_file():
                    # Check file age
                    file_stat = file_path.stat()
                    file_mtime = datetime.fromtimestamp(file_stat.st_mtime)

                    if force or file_mtime < cutoff_time:
                        try:
                            file_path.unlink()
                            cleaned += 1
                            logger.debug(f"Removed orphaned file: {file_path}")
                        except Exception as e:
                            logger.error(
                                f"Failed to remove orphaned file {file_path}: {e}"
                            )

        except Exception as e:
            logger.error(f"Error during orphaned file cleanup: {e}")

        return cleaned

    async def start_background_cleanup(self):
        """Start the background cleanup task."""
        if self._cleanup_task and not self._cleanup_task.done():
            logger.warning("Background cleanup already running")
            return

        self._cleanup_task = asyncio.create_task(self._background_cleanup_loop())
        logger.info("Started background cleanup task")

    async def stop_background_cleanup(self):
        """Stop the background cleanup task."""
        if self._cleanup_task and not self._cleanup_task.done():
            self._cleanup_task.cancel()
            try:
                await self._cleanup_task
            except asyncio.CancelledError:
                pass
            logger.info("Stopped background cleanup task")

    async def _background_cleanup_loop(self):
        """Background task that periodically cleans up old files."""
        while True:
            try:
                await asyncio.sleep(CLEANUP_INTERVAL_SECONDS)
                await self.cleanup_temp_files(force=False)
            except asyncio.CancelledError:
                break
            except Exception as e:
                logger.error(f"Error in background cleanup: {e}")

    @asynccontextmanager
    async def temp_file_context(self, processing_id: str):
        """
        Context manager for temporary files that ensures cleanup.

        Usage:
            async with manager.temp_file_context(processing_id) as ctx:
                file_id, path = await manager.save_temp_file(...)
                # Process files
            # Files are automatically cleaned up
        """
        try:
            yield self
        finally:
            # Cleanup files for this processing ID
            await self.cleanup_temp_files(processing_id=processing_id)


# Global instance
_temp_file_manager: Optional[TempFileManager] = None


def get_temp_file_manager() -> TempFileManager:
    """Get or create the global temp file manager instance."""
    global _temp_file_manager
    if _temp_file_manager is None:
        _temp_file_manager = TempFileManager()
    return _temp_file_manager


async def startup_cleanup():
    """
    Perform startup cleanup of orphaned temporary files.
    Should be called when the application starts.
    """
    manager = get_temp_file_manager()
    cleaned = await manager._cleanup_orphaned_files(force=False)
    logger.info(f"Startup cleanup removed {cleaned} orphaned temp files")

    # Start background cleanup
    await manager.start_background_cleanup()


async def shutdown_cleanup():
    """
    Perform shutdown cleanup.
    Should be called when the application shuts down.
    """
    manager = get_temp_file_manager()
    await manager.stop_background_cleanup()
    # Don't force cleanup on shutdown - let files be cleaned on next startup
    logger.info("Shutdown cleanup completed")
