# =============================================================================
# YouTube Shorts AI Agent — Multi-Stage Dockerfile
# =============================================================================
# Stage 1: Install Python dependencies into a virtual-env.
# Stage 2: Copy only the venv + application code (smaller final image).
# =============================================================================

# ---------------------------------------------------------------------------
# Stage 1 — Builder
# ---------------------------------------------------------------------------
FROM python:3.12-slim AS builder

# Prevent Python from writing .pyc files and enable unbuffered stdout/stderr
ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PIP_DISABLE_PIP_VERSION_CHECK=1 \
    PIP_DEFAULT_TIMEOUT=120 \
    PIP_RETRIES=5

WORKDIR /build

# Create a virtual-env so we can cleanly copy it to the runtime stage
RUN python -m venv /opt/venv
ENV PATH="/opt/venv/bin:$PATH"

# Install Python dependencies (layer cached unless requirements.txt changes)
COPY requirements.txt .
RUN --mount=type=cache,target=/root/.cache/pip \
    python -m pip install --upgrade pip setuptools wheel && \
    for attempt in 1 2 3; do \
        python -m pip install --prefer-binary -r requirements.txt && break; \
        if [ "$attempt" = "3" ]; then exit 1; fi; \
        sleep 5; \
    done

# ---------------------------------------------------------------------------
# Stage 2 — Runtime
# ---------------------------------------------------------------------------
FROM python:3.12-slim AS runtime

# Metadata
LABEL maintainer="Naveen Valasani" \
      description="Autonomous YouTube Shorts AI Agent" \
      version="1.0.0"

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PYTHONPATH="/home/appuser/app" \
    PATH="/opt/venv/bin:$PATH"

# Install only the runtime libraries (no compilers)
RUN apt-get update && \
    apt-get install -y --no-install-recommends curl ffmpeg && \
    rm -rf /var/lib/apt/lists/*

# Create a non-root user for security
RUN groupadd --gid 1000 appuser && \
    useradd --uid 1000 --gid appuser --shell /bin/bash --create-home appuser

WORKDIR /home/appuser/app

# Copy the pre-built virtual-env from the builder stage
COPY --from=builder /opt/venv /opt/venv

# Copy only files needed at runtime.
COPY --chown=appuser:appuser app ./app
COPY --chown=appuser:appuser alembic ./alembic
COPY --chown=appuser:appuser alembic.ini .

# Prepare writable, persistent media storage before switching to non-root.
RUN mkdir -p storage && \
    chown appuser:appuser storage && \
    chmod -R u+rwX app alembic alembic.ini
USER appuser

# Expose the API port
EXPOSE 8000

# Health-check (hits the FastAPI /health endpoint)
HEALTHCHECK --interval=30s --timeout=5s --start-period=10s --retries=3 \
    CMD curl -f http://localhost:8000/api/v1/health || exit 1

# Start the application via uvicorn
CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000", "--workers", "1"]
