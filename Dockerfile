# NeuralBook Platform API - Production Docker Image
# Multi-stage build for minimal image

FROM python:3.13-slim AS builder

RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential libssl-dev libffi-dev \
    && rm -rf /var/lib/apt/lists/*

RUN python -m venv /opt/venv
ENV PATH="/opt/venv/bin:$PATH"

COPY . .
RUN pip install --no-cache-dir --upgrade pip && \
    pip install --no-cache-dir ".[server]"

# ── Production stage ──────────────────────────────────────────────────────
FROM python:3.13-slim

RUN apt-get update && apt-get install -y --no-install-recommends \
    curl ca-certificates \
    && rm -rf /var/lib/apt/lists/*

COPY --from=builder /opt/venv /opt/venv

ENV PATH="/opt/venv/bin:$PATH" \
    PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1 \
    NBOOK_DATA=/data \
    NBOOK_HOST=0.0.0.0

WORKDIR /app
COPY . .

RUN mkdir -p /data && chmod 777 /data

# Non-root user
RUN useradd --create-home nbook && chown -R nbook:nbook /data
USER nbook

HEALTHCHECK --interval=30s --timeout=3s --start-period=10s --retries=3 \
    CMD curl -f http://localhost:${PORT:-8000}/health || exit 1

EXPOSE 8000

CMD ["neuralbook-api"]
