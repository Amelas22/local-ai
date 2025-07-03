#!/bin/bash
# Startup script for Clerk API with WebSocket support

# Default to uvicorn for WebSocket support
if [ "$USE_GUNICORN" = "true" ]; then
    echo "Starting with Gunicorn (WebSocket support limited)..."
    exec gunicorn -k uvicorn.workers.UvicornWorker main:app \
        --bind 0.0.0.0:8000 \
        --workers ${WORKERS:-1} \
        --worker-class uvicorn.workers.UvicornWorker \
        --access-logfile - \
        --error-logfile -
else
    echo "Starting with Uvicorn (Full WebSocket support)..."
    exec uvicorn main:app \
        --host 0.0.0.0 \
        --port 8000 \
        --workers ${WORKERS:-1} \
        --log-level ${LOG_LEVEL:-info} \
        --access-log
fi