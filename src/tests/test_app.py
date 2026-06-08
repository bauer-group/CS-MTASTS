"""Functional tests for the MTA-STS Server (RFC 8461).

These run as a hard build gate in the Dockerfile "test" stage: if any assertion
here fails, the production image is never produced.

The environment that the app validates at import time is seeded in conftest.py.
"""

import pytest

from app import MTASTSApp


# ── Endpoints ──────────────────────────────────────────────────────────────────

def test_health_endpoint(client):
    """/health returns a 200 JSON heartbeat for container orchestration."""
    response = client.get("/health")
    assert response.status_code == 200
    assert response.mimetype == "application/json"
    assert response.get_data(as_text=True) == '{"status":"healthy"}'


def test_policy_endpoint_serves_rfc8461_document(client):
    """/.well-known/mta-sts.txt returns the policy as plain text per RFC 8461."""
    response = client.get("/.well-known/mta-sts.txt")
    assert response.status_code == 200
    assert response.mimetype == "text/plain"

    body = response.get_data(as_text=True)
    assert body == (
        "version: STSv1\n"
        "mode: enforce\n"
        "max_age: 86400\n"
        "mx: mx1.test.example.com\n"
        "mx: mx2.test.example.com\n"
    )


def test_policy_lists_every_configured_mx(client):
    """Each MX record from STS_MX_RECORDS appears as its own `mx:` line."""
    body = client.get("/.well-known/mta-sts.txt").get_data(as_text=True)
    mx_lines = [line for line in body.splitlines() if line.startswith("mx:")]
    assert mx_lines == ["mx: mx1.test.example.com", "mx: mx2.test.example.com"]


def test_index_page_renders(client):
    """The landing page renders as HTML and reflects the configured hostname."""
    response = client.get("/")
    assert response.status_code == 200
    assert "text/html" in response.content_type
    assert b"mta-sts.test.example.com" in response.data


def test_unknown_route_returns_404(client):
    """Unmapped paths must not leak into the policy handler."""
    assert client.get("/does-not-exist").status_code == 404


# ── Startup configuration gate ─────────────────────────────────────────────────

def test_invalid_sts_mode_aborts_startup(monkeypatch):
    """An invalid STS_MODE must fail fast at construction (sys.exit(1))."""
    monkeypatch.setenv("STS_MODE", "definitely-not-valid")
    with pytest.raises(SystemExit) as exc_info:
        MTASTSApp()
    assert exc_info.value.code == 1


# ── Learning contribution slot ─────────────────────────────────────────────────
# The validation in app.py._validate_config() guards several other invariants —
# e.g. a missing/empty STS_MX_RECORDS, a non-positive STS_MAX_AGE, or a
# SERVICE_HOSTNAME that fails the hostname regex. Pick the case that matters most
# for your deployment and assert it here, using the test above as a template.
#
# def test_<your_invariant>_aborts_startup(monkeypatch):
#     monkeypatch.setenv(..., ...)
#     with pytest.raises(SystemExit):
#         MTASTSApp()
