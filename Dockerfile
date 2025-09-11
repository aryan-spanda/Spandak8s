# Multi-stage build for minimal production image
FROM python:3.11-slim as builder

# Install build dependencies
RUN apt-get update && apt-get install -y \
    build-essential \
    curl \
    git \
    && rm -rf /var/lib/apt/lists/*

# Create virtual environment
RUN python -m venv /opt/venv
ENV PATH="/opt/venv/bin:$PATH"

# Copy requirements and install Python dependencies
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy application source
COPY . /app
WORKDIR /app

# Install the application
RUN pip install --no-cache-dir .

# Production stage
FROM python:3.11-slim

# Install runtime dependencies
RUN apt-get update && apt-get install -y \
    curl \
    git \
    ca-certificates \
    && rm -rf /var/lib/apt/lists/*

# Install kubectl
ARG KUBECTL_VERSION=v1.28.3
RUN curl -LO "https://dl.k8s.io/release/${KUBECTL_VERSION}/bin/linux/amd64/kubectl" \
    && install -o root -g root -m 0755 kubectl /usr/local/bin/kubectl \
    && rm kubectl

# Install helm
ARG HELM_VERSION=v3.13.2
RUN curl -fsSL https://get.helm.sh/helm-${HELM_VERSION}-linux-amd64.tar.gz | tar -xz \
    && mv linux-amd64/helm /usr/local/bin/helm \
    && rm -rf linux-amd64

# Copy virtual environment from builder
COPY --from=builder /opt/venv /opt/venv
ENV PATH="/opt/venv/bin:$PATH"

# Create application directory structure
RUN mkdir -p /opt/spandak8s/config /opt/spandak8s/charts

# Copy charts if available
COPY config/module-definitions.yaml /opt/spandak8s/config/

# Create non-root user
RUN groupadd -r spanda && useradd -r -g spanda spanda
RUN chown -R spanda:spanda /opt/spandak8s

# Set working directory
WORKDIR /home/spanda

# Switch to non-root user
USER spanda

# Set environment variables
ENV PYTHONPATH="/opt/venv/lib/python3.11/site-packages"
ENV SPANDAK8S_CONFIG_DIR="/opt/spandak8s/config"
ENV SPANDAK8S_CHARTS_DIR="/opt/spandak8s/charts"

# Health check
HEALTHCHECK --interval=30s --timeout=10s --start-period=5s --retries=3 \
    CMD spandak8s --version || exit 1

# Default command
ENTRYPOINT ["spandak8s"]
CMD ["--help"]

# Labels for metadata
LABEL org.opencontainers.image.title="Spandak8s CLI"
LABEL org.opencontainers.image.description="CLI for the Spanda AI Platform"
LABEL org.opencontainers.image.version="0.1.0"
LABEL org.opencontainers.image.vendor="Spanda AI"
LABEL org.opencontainers.image.licenses="MIT"
LABEL org.opencontainers.image.source="https://github.com/spandaai/spandak8s"
LABEL org.opencontainers.image.documentation="https://docs.spanda.ai/cli"
