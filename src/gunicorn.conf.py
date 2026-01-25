"""Gunicorn configuration for MTA-STS Server."""

import gunicorn

# Custom Server header
gunicorn.SERVER = 'BAUERGROUP'
