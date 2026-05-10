# ============================================================================
# KUBERA STOCK ANALYSIS CHATBOT - DOCKERFILE
# Multi-stage build using uv for all package management
# ============================================================================

# ============================================================================
# STAGE 1: BUILDER
# ============================================================================
FROM python:3.11-slim as builder

WORKDIR /app

# Install system dependencies
RUN apt-get update && apt-get install -y \
    gcc \
    g++ \
    make \
    libpq-dev \
    curl \
    && rm -rf /var/lib/apt/lists/*

# Install uv
RUN curl -LsSf https://astral.sh/uv/install.sh | sh
ENV PATH="/root/.local/bin:$PATH"

# Copy requirements
COPY requirements.txt .

# Install Python dependencies using uv
RUN uv pip install --system --no-cache -r requirements.txt

# ============================================================================
# STAGE 2: RUNTIME
# ============================================================================
FROM python:3.11-slim

ENV PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1 \
    TZ=Asia/Kolkata

WORKDIR /app

# Install runtime system dependencies
RUN apt-get update && apt-get install -y \
    libpq5 \
    curl \
    && rm -rf /var/lib/apt/lists/*

# Install uv and make it available system-wide
RUN curl -LsSf https://astral.sh/uv/install.sh | sh && \
    cp /root/.local/bin/uv /usr/local/bin/uv && \
    chmod +x /usr/local/bin/uv

# Create non-root user
RUN useradd -m -u 1000 kubera && \
    chown -R kubera:kubera /app

# Copy Python dependencies from builder
COPY --from=builder /usr/local/lib/python3.11/site-packages /usr/local/lib/python3.11/site-packages
COPY --from=builder /usr/local/bin /usr/local/bin

# Copy application code
COPY --chown=kubera:kubera . .

# Create necessary directories
RUN mkdir -p logs uploads && \
    chown -R kubera:kubera logs uploads

# Switch to non-root user
USER kubera

# Expose port
EXPOSE 8000

# start-period gives app 60s to fully initialize all 5 MCP servers before
# health checks begin — prevents false unhealthy restarts during startup
HEALTHCHECK --interval=30s --timeout=10s --start-period=60s --retries=3 \
    CMD curl -f http://localhost:8000/health || exit 1

# Run application
CMD ["uvicorn", "main:app", "--host", "0.0.0.0", "--port", "8000", "--workers", "1", "--ws", "websockets"]