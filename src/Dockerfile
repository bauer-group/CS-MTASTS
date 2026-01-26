# ═══════════════════════════════════════════════════════════════════════════════
# MTA-STS Server - Dockerfile
# ═══════════════════════════════════════════════════════════════════════════════
# Mail Transfer Agent Strict Transport Security Policy Server (RFC 8461)
#
# Features:
#   - Python 3 lightweight base image
#   - Tini init for proper signal handling
#   - Non-root user for security
#   - Health check endpoint
#   - Rate limiting support
#
# Build:  docker build -t mtasts-server .
# Run:    docker run -p 8080:8080 mtasts-server
# ═══════════════════════════════════════════════════════════════════════════════

FROM bauergroup/python3-light:latest

# ───────────────────────────────────────────────────────────────────────────────
# Metadata
# ───────────────────────────────────────────────────────────────────────────────

LABEL vendor="BAUER GROUP"
LABEL maintainer="Karl Bauer <karl.bauer@bauer-group.com>"

# Opencontainers Metadata
LABEL org.opencontainers.image.title="MTA-STS Server"
LABEL org.opencontainers.image.description="Mail Transfer Agent Strict Transport Security Policy Server (RFC 8461)"
LABEL org.opencontainers.image.version="0.2.0"
LABEL org.opencontainers.image.licenses="MIT"
LABEL org.opencontainers.image.vendor="BAUER GROUP"
LABEL org.opencontainers.image.authors="Karl Bauer <karl.bauer@bauer-group.com>"
LABEL org.opencontainers.image.source="https://github.com/bauer-group/CS-MTASTS"
LABEL org.opencontainers.image.url="https://github.com/bauer-group/CS-MTASTS"
LABEL org.opencontainers.image.documentation="https://github.com/bauer-group/CS-MTASTS#readme"

# ───────────────────────────────────────────────────────────────────────────────
# Environment Configuration
# ───────────────────────────────────────────────────────────────────────────────

# System Settings
ENV TIME_ZONE=Etc/UTC
ENV LANG=en_US.UTF-8

# Flask Application
ENV FLASK_APP=app

# Service Configuration
ENV SERVICE_HOSTNAME=mta-sts.example.com
ENV DYNAMIC_HOSTNAME=false
ENV GLOBAL_RATE_LIMIT=600/minute
ENV SERVER_PORT=8080

# MTA-STS Policy Settings
# Mode: enforce | testing | none
ENV STS_MODE=enforce
# Max age in seconds (86400 = 1 day)
ENV STS_MAX_AGE=86400
# Comma-separated list of MX records
ENV STS_MX_RECORDS="mx1.example.com, mx2.example.com"

# ───────────────────────────────────────────────────────────────────────────────
# Port Configuration
# ───────────────────────────────────────────────────────────────────────────────

EXPOSE 8080/tcp

# ───────────────────────────────────────────────────────────────────────────────
# Build Stage
# ───────────────────────────────────────────────────────────────────────────────

USER root
SHELL ["/bin/bash", "-c"]

# Remove demo main.py from base image
RUN rm -f /app/main.py

# Create non-root user for security
RUN useradd -m app

# Copy application files
ADD requirements.txt /app/requirements.txt
ADD gunicorn.conf.py /app/gunicorn.conf.py
ADD app.py /app/app.py
ADD templates/ /app/templates/
ADD static/ /app/static/

# Install Python dependencies
RUN /usr/local/bin/docker-setup-requirements.sh

# Set ownership and switch to non-root user
RUN chown -R app:app /app

# ───────────────────────────────────────────────────────────────────────────────
# Runtime Configuration
# ───────────────────────────────────────────────────────────────────────────────

USER app
WORKDIR /app

# Health check - verifies application is responding
HEALTHCHECK --interval=30s --timeout=3s --start-period=5s --retries=3 \
    CMD curl -sf http://localhost:${SERVER_PORT}/health || exit 1

# Start application with tini init system for proper signal handling
CMD ["/usr/bin/tini", "--", "/app/app.sh"]
