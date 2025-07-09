"""
WebSocket server implementation using Socket.IO for real-time updates
"""
import logging
from typing import Dict, Any, Optional
import socketio
from fastapi import HTTPException
import asyncio
from datetime import datetime

# Configure logging
logger = logging.getLogger(__name__)

# Create Socket.IO server instance
sio = socketio.AsyncServer(
    async_mode='asgi',
    cors_allowed_origins='*',  # Configure this properly in production
    logger=True,
    engineio_logger=False,
    # Ensure compatibility with Socket.IO v4 clients
    async_handlers=True,
    # Allow all transports
    transports=['polling', 'websocket'],
    # Additional CORS configuration for development
    cors_credentials=True,
    # Accept any origin in development
    allow_upgrades=True,
    http_compression=True
)

# Socket.IO ASGI app
socket_app = socketio.ASGIApp(
    sio,
    socketio_path='/ws/socket.io',
    other_asgi_app=None
)

# Store active connections and their metadata
active_connections: Dict[str, Dict[str, Any]] = {}

@sio.event
async def connect(sid, environ, auth):
    """Handle client connection"""
    logger.info(f"Client connected: {sid}")
    logger.info(f"Connection auth: {auth}")
    logger.info(f"Connection headers: {environ.get('HTTP_ORIGIN', 'No origin')}")
    
    # Store connection metadata
    active_connections[sid] = {
        'connected_at': datetime.utcnow(),
        'auth': auth,
        'case_id': None
    }
    
    # Send connection confirmation
    try:
        await sio.emit('connected', {'message': 'Successfully connected to Clerk WebSocket', 'sid': sid}, room=sid)
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
    await sio.emit('pong', room=sid)

@sio.event
async def subscribe_case(sid, data):
    """Subscribe to updates for a specific case"""
    case_id = data.get('case_id')
    if case_id and sid in active_connections:
        active_connections[sid]['case_id'] = case_id
        logger.info(f"Client {sid} subscribed to case {case_id}")
        await sio.emit('subscribed', {'case_id': case_id}, room=sid)

# Discovery processing event emitters
async def emit_discovery_started(processing_id: str, case_id: str, total_files: int):
    """Emit when discovery processing starts"""
    event_data = {
        'processingId': processing_id,
        'caseId': case_id,
        'totalFiles': total_files
    }
    await sio.emit('discovery:started', event_data)
    logger.info(f"Emitted discovery:started for processing {processing_id}")

async def emit_document_found(
    processing_id: str,
    document_id: str,
    title: str,
    doc_type: str,
    page_count: int,
    bates_range: Optional[Dict[str, str]] = None,
    confidence: float = 1.0
):
    """Emit when a new document is discovered"""
    event_data = {
        'processingId': processing_id,
        'documentId': document_id,
        'title': title,
        'type': doc_type,
        'pageCount': page_count,
        'batesRange': bates_range,
        'confidence': confidence
    }
    await sio.emit('discovery:document_found', event_data)
    logger.debug(f"Emitted discovery:document_found for document {document_id}")

async def emit_chunking_progress(
    processing_id: str,
    document_id: str,
    progress: float,
    chunks_created: int
):
    """Emit document chunking progress"""
    event_data = {
        'processingId': processing_id,
        'documentId': document_id,
        'progress': progress,
        'chunksCreated': chunks_created
    }
    await sio.emit('discovery:chunking', event_data)

async def emit_embedding_progress(
    processing_id: str,
    document_id: str,
    chunk_id: str,
    progress: float
):
    """Emit embedding generation progress"""
    event_data = {
        'processingId': processing_id,
        'documentId': document_id,
        'chunkId': chunk_id,
        'progress': progress
    }
    await sio.emit('discovery:embedding', event_data)

async def emit_document_stored(
    processing_id: str,
    document_id: str,
    vectors_stored: int
):
    """Emit when document vectors are stored"""
    event_data = {
        'processingId': processing_id,
        'documentId': document_id,
        'vectorsStored': vectors_stored
    }
    await sio.emit('discovery:stored', event_data)

async def emit_processing_completed(
    processing_id: str,
    summary: Dict[str, Any]
):
    """Emit when processing is completed"""
    event_data = {
        'processingId': processing_id,
        'summary': summary
    }
    await sio.emit('discovery:completed', event_data)
    logger.info(f"Emitted discovery:completed for processing {processing_id}")

async def emit_processing_error(
    processing_id: str,
    error: str,
    stage: str,
    document_id: Optional[str] = None
):
    """Emit when an error occurs during processing"""
    event_data = {
        'processingId': processing_id,
        'error': error,
        'stage': stage,
        'documentId': document_id
    }
    await sio.emit('discovery:error', event_data)
    logger.error(f"Emitted discovery:error for processing {processing_id}: {error}")

# Motion drafting event emitters (for future use)
async def emit_motion_started(motion_id: str, case_id: str, motion_type: str):
    """Emit when motion drafting starts"""
    event_data = {
        'motionId': motion_id,
        'caseId': case_id,
        'type': motion_type
    }
    await sio.emit('motion:started', event_data)

async def emit_motion_section_completed(motion_id: str, section: str, content: str):
    """Emit when a motion section is completed"""
    event_data = {
        'motionId': motion_id,
        'section': section,
        'content': content
    }
    await sio.emit('motion:section_completed', event_data)

async def emit_motion_completed(motion_id: str, download_url: str):
    """Emit when motion drafting is completed"""
    event_data = {
        'motionId': motion_id,
        'downloadUrl': download_url
    }
    await sio.emit('motion:completed', event_data)

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
        'caseId': case_id,
        'eventType': event_type,
        'timestamp': datetime.utcnow().isoformat(),
        **data
    }
    
    await sio.emit(f'case:{event_type}', event_data)
    logger.info(f"Emitted case event: case:{event_type} for case {case_id}")

# Utility functions
def get_active_connections():
    """Get information about active connections"""
    return {
        'total': len(active_connections),
        'connections': [
            {
                'sid': sid,
                'connected_at': info['connected_at'].isoformat(),
                'case_id': info.get('case_id')
            }
            for sid, info in active_connections.items()
        ]
    }

# Export the socket app and event emitters
__all__ = [
    'socket_app',
    'sio',
    'emit_discovery_started',
    'emit_document_found',
    'emit_chunking_progress',
    'emit_embedding_progress',
    'emit_document_stored',
    'emit_processing_completed',
    'emit_processing_error',
    'emit_motion_started',
    'emit_motion_section_completed',
    'emit_motion_completed',
    'emit_case_event',
    'get_active_connections'
]