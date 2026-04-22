# NeuralBook Platform - Docker Image
# Multi-stage build for minimal production image

FROM python:3.13-slim as builder

# Install build dependencies
RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential \
    libssl-dev \
    libffi-dev \
    && rm -rf /var/lib/apt/lists/*

# Create virtual environment
RUN python -m venv /opt/venv
ENV PATH="/opt/venv/bin:$PATH"

# Copy and install requirements
COPY requirements.txt .
RUN pip install --no-cache-dir --upgrade pip && \
    pip install --no-cache-dir -r requirements.txt

# Production stage
FROM python:3.13-slim

# Install runtime dependencies only
RUN apt-get update && apt-get install -y --no-install-recommends \
    curl \
    ca-certificates \
    && rm -rf /var/lib/apt/lists/*

# Copy virtual environment from builder
COPY --from=builder /opt/venv /opt/venv

# Set environment
ENV PATH="/opt/venv/bin:$PATH" \
    PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1 \
    NEURALBOOK_STORE_PATH=/data/store.json \
    NEURALBOOK_PORT=8000 \
    NEURALBOOK_HOST=0.0.0.0

# Create app directory
WORKDIR /app

# Copy application
COPY . .

# Install package in development mode
RUN pip install --no-cache-dir -e .

# Create data directory
RUN mkdir -p /data && chmod 777 /data

# Health check
HEALTHCHECK --interval=30s --timeout=3s --start-period=5s --retries=3 \
    CMD python -c "import requests; requests.get('http://localhost:${NEURALBOOK_PORT}/health')" || exit 1

# Expose port
EXPOSE 8000

# Run API server by default
CMD ["python", "examples/02_api_server.py", "--host", "0.0.0.0", "--port", "8000"]
