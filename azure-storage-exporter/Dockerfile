FROM python:3.11-slim

LABEL maintainer="DevOps Team"
LABEL description="Azure Storage Account Prometheus Exporter"
LABEL org.opencontainers.image.description="Multi-platform support: linux/amd64, linux/arm64"

# Set working directory
WORKDIR /app

# Install system dependencies
RUN apt-get update && \
    apt-get install -y --no-install-recommends \
    ca-certificates \
    curl \
    && rm -rf /var/lib/apt/lists/*

# Copy requirements first for better layer caching
COPY requirements.txt .

# Install Python dependencies
RUN pip install --no-cache-dir -r requirements.txt

# Copy application code
COPY azure_storage_exporter.py .

# Create non-root user for security
RUN useradd -r -u 1000 -m exporter && \
    chown -R exporter:exporter /app

USER exporter

# Expose metrics port
EXPOSE 9358

# Health check
HEALTHCHECK --interval=30s --timeout=10s --start-period=5s --retries=3 \
    CMD curl -f http://localhost:9358/metrics || exit 1

# Run the exporter
ENTRYPOINT ["python3", "-u", "azure_storage_exporter.py"]



