"""WebSocket module for real-time updates"""

from .socket_server import (
    socket_app as socket_app,
    sio as sio,
    emit_discovery_started as emit_discovery_started,
    emit_document_found as emit_document_found,
    emit_chunking_progress as emit_chunking_progress,
    emit_embedding_progress as emit_embedding_progress,
    emit_document_stored as emit_document_stored,
    emit_processing_completed as emit_processing_completed,
    emit_processing_error as emit_processing_error,
    emit_motion_started as emit_motion_started,
    get_active_connections as get_active_connections,
)
