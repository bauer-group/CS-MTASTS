"""Gunicorn configuration for the MTA-STS Server.

Single source of truth for the gunicorn runtime — the container ENTRYPOINT is
simply `gunicorn -c gunicorn.conf.py app:app`. This replaces the bind/worker
wiring that the old base image's app.sh used to provide.

All values are environment-overridable so operators can tune without rebuilding.
"""

import os

import gunicorn

# ── Custom Server header ───────────────────────────────────────────────────────
gunicorn.SERVER = "BAUERGROUP"

# ── Networking ─────────────────────────────────────────────────────────────────
# Bind on the configured application port (matches SERVER_PORT used elsewhere).
bind = f"0.0.0.0:{os.getenv('SERVER_PORT', '8080')}"

# ── Worker model ───────────────────────────────────────────────────────────────
# NOTE: app.py's Flask-Limiter uses in-memory storage with a single 'global'
# key, so GLOBAL_RATE_LIMIT is enforced PER WORKER — with N workers the effective
# ceiling is N × the configured limit. For a tiny, stateless policy service a
# small, fixed worker count keeps that limit predictable and memory low.
# Override GUNICORN_WORKERS only if you front the limiter with shared storage.
workers = int(os.getenv("GUNICORN_WORKERS", "2"))
worker_class = os.getenv("GUNICORN_WORKER_CLASS", "sync")
threads = int(os.getenv("GUNICORN_THREADS", "1"))

# ── Timeouts ───────────────────────────────────────────────────────────────────
timeout = int(os.getenv("GUNICORN_TIMEOUT", "30"))
graceful_timeout = int(os.getenv("GUNICORN_GRACEFUL_TIMEOUT", "30"))
keepalive = int(os.getenv("GUNICORN_KEEPALIVE", "5"))

# ── Logging (stream to stdout/stderr for container log collectors) ─────────────
accesslog = "-"
errorlog = "-"
loglevel = os.getenv("GUNICORN_LOG_LEVEL", "info").lower()
