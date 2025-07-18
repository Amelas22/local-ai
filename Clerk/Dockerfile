# Stage 1: Build dependencies in a clean virtual environment
FROM python:3.11-slim as builder

ENV PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1 \
    PIP_NO_CACHE_DIR=1 \
    PIP_DISABLE_PIP_VERSION_CHECK=1

RUN apt-get update && apt-get install -y \
    build-essential \
    curl \
    # PyMuPDF dependencies
    libmupdf-dev \
    mupdf-tools \
    # Additional dependencies that might be needed
    libfreetype6-dev \
    libharfbuzz-dev \
    libjpeg-dev \
    libopenjp2-7-dev \
    && rm -rf /var/lib/apt/lists/*

# Create and activate virtual environment
ENV VIRTUAL_ENV=/opt/venv
RUN python3 -m venv $VIRTUAL_ENV
ENV PATH="$VIRTUAL_ENV/bin:$PATH"

# Install Python dependencies with retry logic and timeout configurations
WORKDIR /app
COPY requirements.txt .

# Configure pip for better network handling
ENV PIP_DEFAULT_TIMEOUT=120 \
    PIP_RETRIES=5 \
    PIP_TIMEOUT=120

# Install with retry logic
RUN pip install --upgrade pip && \
    pip install --no-cache-dir --timeout 120 --retries 5 -r requirements.txt || \
    (sleep 5 && pip install --no-cache-dir --timeout 120 --retries 5 -r requirements.txt) || \
    (sleep 10 && pip install --no-cache-dir --timeout 120 --retries 5 -r requirements.txt)

# Download spaCy language model
RUN python -m spacy download en_core_web_sm

# Stage 2: Final production container
FROM python:3.11-slim as production

ENV PATH="/opt/venv/bin:$PATH"

# Copy the virtual environment from builder
COPY --from=builder /opt/venv /opt/venv

# Create non-root user
RUN groupadd -r appuser && useradd --no-log-init -r -g appuser appuser

# Set working directory and copy app files
WORKDIR /app
COPY . /app/

RUN mkdir -p /app/logs /app/reports && \
    chown -R appuser:appuser /app && \
    chmod -R 755 /app && \
    chmod 777 /app/logs /app/reports

# Install curl for health checks and PyMuPDF runtime dependencies
RUN apt-get update && apt-get install -y --no-install-recommends \
    curl netcat-openbsd \
    # PyMuPDF runtime dependencies
    libmupdf-dev \
    mupdf-tools \
    && rm -rf /var/lib/apt/lists/*

HEALTHCHECK --interval=30s --timeout=10s --start-period=40s --retries=3 \
    CMD curl -f http://localhost:8000/health || exit 1

USER appuser

EXPOSE 8000

# Run wait_for_services.py, init_db.py, then start the app
CMD sh -c "python wait_for_services.py && python init_db.py || true && uvicorn main:app --host 0.0.0.0 --port 8000 --workers 1"