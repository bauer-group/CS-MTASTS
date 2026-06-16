# ═══════════════════════════════════════════════════════════════════════════════
# MTA-STS Server - Dockerfile
# ═══════════════════════════════════════════════════════════════════════════════
# Mail Transfer Agent Strict Transport Security Policy Server (RFC 8461)
#
# Multi-stage build on python:3.14-alpine with an integrated test gate:
#   - Stage 1 (builder): installs Python dependencies into an isolated prefix
#   - Stage 2 (test):    runs pytest — the build FAILS if any test fails
#   - Stage 3 (prod):    minimal runtime, non-root user, tini init, healthcheck
#
# The prod stage copies a marker out of the test stage (COPY --from=test ...),
# which makes a green test run a hard prerequisite for producing the runtime
# image. The tests cannot be skipped.
#
#   docker build -t mtasts-server ./src        # full pipeline (test gates prod)
#   docker build --target test ./src           # run the test stage only
#   docker run -p 8080:8080 mtasts-server
# ═══════════════════════════════════════════════════════════════════════════════


# ── Stage 1: Builder — install Python dependencies into /install ───────────────
FROM python:3.14-alpine AS builder

# build-base + libffi-dev cover source builds for any dependency that lacks a
# prebuilt cp314 musl wheel. Builder-only — these never reach the runtime image.
RUN apk add --no-cache build-base libffi-dev

WORKDIR /build
COPY requirements.txt .
RUN pip install --no-cache-dir --prefix=/install -r requirements.txt


# ── Stage 2: Test — pytest as a hard build gate ────────────────────────────────
FROM python:3.14-alpine AS test

WORKDIR /app

COPY requirements.txt requirements-test.txt ./
RUN pip install --no-cache-dir -r requirements-test.txt

COPY app.py gunicorn.conf.py pytest.ini ./
COPY templates/ ./templates/
COPY static/ ./static/
COPY tests/ ./tests/

# app.py validates its configuration at import time and calls sys.exit(1) on
# missing/invalid env. Provide throwaway TEST values so the suite can import the
# app — these are build-only and never ship in the prod image.
ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    SERVICE_HOSTNAME=mta-sts.test.example.com \
    STS_MODE=enforce \
    STS_MAX_AGE=86400 \
    STS_MX_RECORDS="mx1.test.example.com, mx2.test.example.com"

RUN pytest tests/ -v --tb=short


# ── Stage 3: Production — minimal runtime image ────────────────────────────────
FROM python:3.14-alpine AS prod

# ── Metadata ───────────────────────────────────────────────────────────────────
LABEL vendor="BAUER GROUP"
LABEL maintainer="Karl Bauer <karl.bauer@bauer-group.com>"

# Opencontainers Metadata
LABEL org.opencontainers.image.title="MTA-STS Server"
LABEL org.opencontainers.image.description="Mail Transfer Agent Strict Transport Security Policy Server (RFC 8461)"
LABEL org.opencontainers.image.licenses="MIT"
LABEL org.opencontainers.image.vendor="BAUER GROUP"
LABEL org.opencontainers.image.authors="Karl Bauer <karl.bauer@bauer-group.com>"
LABEL org.opencontainers.image.source="https://github.com/bauer-group/CS-MTASTS"
LABEL org.opencontainers.image.url="https://github.com/bauer-group/CS-MTASTS"
LABEL org.opencontainers.image.documentation="https://github.com/bauer-group/CS-MTASTS#readme"
LABEL org.opencontainers.image.base.name="docker.io/library/python:3.14-alpine"
LABEL org.opencontainers.image.version="0.4.4"

LABEL com.bauer-group.image.component="application"
LABEL com.bauer-group.image.stack="mta-sts"

# Runtime dependencies only: tini (clean PID 1 signal handling), tzdata, CA certs,
# and curl for the container healthcheck.
RUN apk add --no-cache tini tzdata ca-certificates curl \
    && rm -rf /var/cache/apk/* \
    && addgroup -g 1001 -S app \
    && adduser -S -D -u 1001 -G app -h /app app

# Python packages from the builder stage
COPY --from=builder /install /usr/local

# Make the test stage a hard build dependency: if the test stage failed, this
# COPY cannot resolve and the prod build aborts. Tests cannot be bypassed.
COPY --from=test /app/pytest.ini /tmp/_test_passed
RUN rm /tmp/_test_passed

# ── Environment Configuration (runtime defaults; override at deploy time) ───────
ENV TIME_ZONE=Etc/UTC \
    LANG=en_US.UTF-8 \
    PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1 \
    FLASK_APP=app \
    SERVICE_HOSTNAME=mta-sts.example.com \
    DYNAMIC_HOSTNAME=false \
    GLOBAL_RATE_LIMIT=600/minute \
    SERVER_PORT=8080 \
    STS_MODE=enforce \
    STS_MAX_AGE=86400 \
    STS_MX_RECORDS="mx1.example.com, mx2.example.com"

WORKDIR /app

# Application files (owned by the non-root runtime user)
COPY --chown=app:app app.py gunicorn.conf.py ./
COPY --chown=app:app templates/ ./templates/
COPY --chown=app:app static/ ./static/

EXPOSE 8080/tcp

USER app

# Health check — verifies the application is responding on the configured port.
# Use 127.0.0.1 (not localhost) so the probe targets gunicorn's IPv4 bind
# (0.0.0.0) directly and never stalls on an IPv6 ::1 attempt first.
HEALTHCHECK --interval=30s --timeout=3s --start-period=5s --retries=3 \
    CMD curl -sf "http://127.0.0.1:${SERVER_PORT}/health" || exit 1

# tini as PID 1 → forwards SIGTERM/SIGINT cleanly to the gunicorn master
ENTRYPOINT ["/sbin/tini", "--", "gunicorn", "-c", "gunicorn.conf.py", "app:app"]
