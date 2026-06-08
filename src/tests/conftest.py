"""Shared pytest fixtures for the MTA-STS Server test suite.

IMPORTANT: app.py builds its singleton MTASTSApp() at *import time* and runs
_validate_config(), which calls sys.exit(1) when required configuration is
missing or invalid. We therefore seed the required environment variables BEFORE
importing the app module — the mirror image of a clean-env fixture.
"""

import os

# Required config — must be set before `import app` below, or the import aborts.
os.environ.setdefault("SERVICE_HOSTNAME", "mta-sts.test.example.com")
os.environ.setdefault("STS_MODE", "enforce")
os.environ.setdefault("STS_MAX_AGE", "86400")
os.environ.setdefault("STS_MX_RECORDS", "mx1.test.example.com, mx2.test.example.com")
os.environ.setdefault("GLOBAL_RATE_LIMIT", "600/minute")
os.environ.setdefault("DYNAMIC_HOSTNAME", "false")

import pytest

from app import app as flask_app  # noqa: E402 — must follow the env seeding above


@pytest.fixture
def client():
    """A Flask test client for the configured MTA-STS app."""
    flask_app.config.update(TESTING=True)
    return flask_app.test_client()
