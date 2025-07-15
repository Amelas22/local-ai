"""
WebSocket server implementation using Socket.IO for real-time updates
"""

import logging
import os
from typing import Dict, Any, Optional
import socketio
from datetime import datetime

# Configure logging
logger = logging.getLogger(__name__)

# Create Socket.IO server instance
sio = socketio.AsyncServer(
    async_mode="asgi",
    cors_allowed_origins="*",  # Configure this properly in production
    logger=True,
    engineio_logger=False,
    # Ensure compatibility with Socket.IO v4 clients
    async_handlers=True,
    # Allow all transports
    transports=["polling", "websocket"],
    # Additional CORS configuration for development
    cors_credentials=True,
    # Accept any origin in development
    allow_upgrades=True,
    http_compression=True,
)

# Socket.IO ASGI app
socket_app = socketio.ASGIApp(sio, socketio_path="/ws/socket.io", other_asgi_app=None)

# Store active connections and their metadata
active_connections: Dict[str, Dict[str, Any]] = {}


@sio.event
async def connect(sid, environ, auth):
    """Handle client connection"""
    logger.info(f"Client connected: {sid}")
    logger.info(f"Connection auth: {auth}")
    logger.info(f"Connection headers: {environ.get('HTTP_ORIGIN', 'No origin')}")

    # MVP Mode: Skip auth validation
    if os.getenv("MVP_MODE", "false").lower() == "true":
        logger.warning(f"MVP Mode: Bypassing WebSocket auth for {sid}")
        # Use mock user data
        from src.middleware.mock_user_middleware import MockUserMiddleware

        mock_user = MockUserMiddleware.get_mock_user()
        active_connections[sid] = {
            "connected_at": datetime.utcnow(),
            "auth": {
                "user_id": mock_user.id,
                "email": mock_user.email,
                "authenticated": True,
            },
            "case_id": None,
        }
        # Save session for MVP mode
        await sio.save_session(sid, {"user_id": mock_user.id, "authenticated": True})
    else:
        # Normal auth flow
        # TODO: Validate auth token here in production
        active_connections[sid] = {
            "connected_at": datetime.utcnow(),
            "auth": auth,
            "case_id": None,
        }

    # Send connection confirmation
    try:
        await sio.emit(
            "connected",
            {"message": "Successfully connected to Clerk WebSocket", "sid": sid},
            room=sid,
        )
        logger.info(f"Sent connected event to {sid}")
    except Exception as e:
        logger.error(f"Error sending connected event: {e}")

    return True


@sio.event
async def disconnect(sid):
    """Handle client disconnection"""
    logger.info(f"Client disconnected: {sid}")

    # Clean up connection data
    if sid in active_connections:
        del active_connections[sid]


@sio.event
async def ping(sid):
    """Handle ping event for connection health check"""
    await sio.emit("pong", room=sid)


@sio.event
async def subscribe_case(sid, data):
    """Subscribe to updates for a specific case"""
    case_id = data.get("case_id")
    if case_id and sid in active_connections:
        # Leave previous room if any
        if active_connections[sid]["case_id"]:
            prev_case = active_connections[sid]["case_id"]
            sio.leave_room(sid, f"case_{prev_case}")
            logger.info(f"Client {sid} left room case_{prev_case}")
        
        # Join new case room
        active_connections[sid]["case_id"] = case_id
        room_name = f"case_{case_id}"
        sio.enter_room(sid, room_name)
        logger.info(f"Client {sid} joined room {room_name}")
        
        await sio.emit("subscribed", {"case_id": case_id}, room=sid)


@sio.event
async def unsubscribe_case(sid, data):
    """Unsubscribe from case updates"""
    if sid in active_connections and active_connections[sid]["case_id"]:
        case_id = active_connections[sid]["case_id"]
        sio.leave_room(sid, f"case_{case_id}")
        active_connections[sid]["case_id"] = None
        logger.info(f"Client {sid} unsubscribed from case {case_id}")
        await sio.emit("unsubscribed", {"case_id": case_id}, room=sid)


# Discovery processing event emitters
async def emit_discovery_started(processing_id: str, case_id: str, total_files: int):
    """Emit when discovery processing starts"""
    event_data = {
        "processing_id": processing_id,
        "case_id": case_id,
        "total_files": total_files,
    }
    room = f"case_{case_id}"
    logger.info(f"About to emit discovery:started to room '{room}' with data: {event_data}")
    
    # Debug: Log emission details
    logger.debug(f"Emitting to room: {room}")
    
    await sio.emit("discovery:started", event_data, room=room)
    logger.info(f"Emitted discovery:started for processing {processing_id} to room {room}")


async def emit_document_found(
    processing_id: str,
    case_id: str,
    document_id: str,
    title: str,
    doc_type: str,
    page_count: int,
    bates_range: Optional[Dict[str, str]] = None,
    confidence: float = 1.0,
):
    """Emit when a new document is discovered"""
    event_data = {
        "processing_id": processing_id,
        "document_id": document_id,
        "title": title,
        "type": doc_type,
        "page_count": page_count,
        "bates_range": bates_range,
        "confidence": confidence,
    }
    room = f"case_{case_id}"
    logger.debug(f"Emitting discovery:document_found to room {room} with data: {event_data}")
    await sio.emit("discovery:document_found", event_data, room=room)
    logger.debug(f"Emitted discovery:document_found for document {document_id} to room {room}")


async def emit_chunking_progress(
    processing_id: str, case_id: str, document_id: str, progress: float, chunks_created: int
):
    """Emit document chunking progress"""
    event_data = {
        "processing_id": processing_id,
        "document_id": document_id,
        "progress": progress,
        "chunks_created": chunks_created,
    }
    room = f"case_{case_id}"
    logger.debug(f"Emitting discovery:chunking to room {room} with data: {event_data}")
    await sio.emit("discovery:chunking", event_data, room=room)


async def emit_embedding_progress(
    processing_id: str, case_id: str, document_id: str, chunk_id: str, progress: float
):
    """Emit embedding generation progress"""
    event_data = {
        "processing_id": processing_id,
        "document_id": document_id,
        "chunk_id": chunk_id,
        "progress": progress,
    }
    room = f"case_{case_id}"
    logger.debug(f"Emitting discovery:embedding to room {room} with data: {event_data}")
    await sio.emit("discovery:embedding", event_data, room=room)


async def emit_document_stored(
    processing_id: str, case_id: str, document_id: str, vectors_stored: int
):
    """Emit when document vectors are stored"""
    event_data = {
        "processing_id": processing_id,
        "document_id": document_id,
        "vectors_stored": vectors_stored,
    }
    room = f"case_{case_id}"
    logger.debug(f"Emitting discovery:stored to room {room} with data: {event_data}")
    await sio.emit("discovery:stored", event_data, room=room)


async def emit_processing_completed(processing_id: str, case_id: str, summary: Dict[str, Any]):
    """Emit when processing is completed"""
    event_data = {"processing_id": processing_id, "summary": summary}
    room = f"case_{case_id}"
    logger.debug(f"Emitting discovery:completed to room {room} with data: {event_data}")
    await sio.emit("discovery:completed", event_data, room=room)
    logger.info(f"Emitted discovery:completed for processing {processing_id} to room {room}")


async def emit_processing_error(
    processing_id: str, case_id: str, error: str, stage: str, document_id: Optional[str] = None
):
    """Emit when an error occurs during processing"""
    event_data = {
        "processing_id": processing_id,
        "error": error,
        "stage": stage,
        "document_id": document_id,
    }
    room = f"case_{case_id}"
    logger.debug(f"Emitting discovery:error to room {room} with data: {event_data}")
    await sio.emit("discovery:error", event_data, room=room)
    logger.error(f"Emitted discovery:error for processing {processing_id} to room {room}: {error}")


# Motion drafting event emitters (for future use)
async def emit_motion_started(motion_id: str, case_id: str, motion_type: str):
    """Emit when motion drafting starts"""
    event_data = {"motion_id": motion_id, "case_id": case_id, "type": motion_type}
    logger.debug(f"Emitting motion:started with data: {event_data}")
    await sio.emit("motion:started", event_data)


async def emit_motion_section_completed(motion_id: str, section: str, content: str):
    """Emit when a motion section is completed"""
    event_data = {"motion_id": motion_id, "section": section, "content": content}
    logger.debug(f"Emitting motion:section_completed with data: {event_data}")
    await sio.emit("motion:section_completed", event_data)


async def emit_motion_completed(motion_id: str, download_url: str):
    """Emit when motion drafting is completed"""
    event_data = {"motion_id": motion_id, "download_url": download_url}
    logger.debug(f"Emitting motion:completed with data: {event_data}")
    await sio.emit("motion:completed", event_data)


# Case management event emitters
async def emit_case_event(event_type: str, case_id: str, data: dict):
    """
    Emit case-related events.

    Args:
        event_type: Type of event (e.g., 'collection_created', 'collection_error')
        case_id: ID of the case
        data: Event data payload
    """
    event_data = {
        "case_id": case_id,
        "event_type": event_type,
        "timestamp": datetime.utcnow().isoformat(),
        **data,
    }
    
    logger.debug(f"Emitting case:{event_type} with data: {event_data}")
    await sio.emit(f"case:{event_type}", event_data)
    logger.info(f"Emitted case event: case:{event_type} for case {case_id}")


# Utility functions
def get_active_connections():
    """Get information about active connections"""
    return {
        "total": len(active_connections),
        "connections": [
            {
                "sid": sid,
                "connected_at": info["connected_at"].isoformat(),
                "case_id": info.get("case_id"),
            }
            for sid, info in active_connections.items()
        ],
    }


# Export the socket app and event emitters
__all__ = [
    "socket_app",
    "sio",
    "emit_discovery_started",
    "emit_document_found",
    "emit_chunking_progress",
    "emit_embedding_progress",
    "emit_document_stored",
    "emit_processing_completed",
    "emit_processing_error",
    "emit_motion_started",
    "emit_motion_section_completed",
    "emit_motion_completed",
    "emit_case_event",
    "get_active_connections",
]
