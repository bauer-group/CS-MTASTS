"""
MTA-STS Server - Mail Transfer Agent Strict Transport Security Policy Server.

A modern Flask application that serves MTA-STS policies according to RFC 8461.
"""

import logging
import os
import re
import sys

from flask import Flask, Response, render_template
from flask_limiter import Limiter
from werkzeug.middleware.proxy_fix import ProxyFix

# Valid STS modes according to RFC 8461
VALID_STS_MODES = ('enforce', 'testing', 'none')

# Regex patterns for validation
HOSTNAME_PATTERN = re.compile(r'^[a-zA-Z0-9]([a-zA-Z0-9\-\.]*[a-zA-Z0-9])?$')
MX_RECORD_PATTERN = re.compile(r'^[\*a-zA-Z0-9]([a-zA-Z0-9\-\.]*[a-zA-Z0-9])?$')
RATE_LIMIT_PATTERN = re.compile(r'^\d+/(second|minute|hour|day)$')


class MTASTSApp:
    """Main application class for MTA-STS service."""

    def __init__(self) -> None:
        """Initialize the MTA-STS application."""
        self._setup_logging()
        self.logger = logging.getLogger('mta-sts')

        self.flask_app = Flask(__name__, static_folder='static')
        self.flask_app.wsgi_app = ProxyFix(self.flask_app.wsgi_app, x_for=1, x_proto=1, x_host=1)

        self._load_config()
        self._validate_config()
        self._build_policy_content()
        self._log_startup_config()
        self._configure_rate_limiter()
        self._register_routes()

    def _setup_logging(self) -> None:
        """Configure application logging."""
        logging.basicConfig(
            level=logging.INFO,
            format='%(asctime)s [%(levelname)s] %(name)s: %(message)s',
            datefmt='%Y-%m-%d %H:%M:%S'
        )
        # Suppress verbose Flask/Werkzeug output
        logging.getLogger('werkzeug').setLevel(logging.WARNING)

    def _load_config(self) -> None:
        """Load configuration from environment variables."""
        self.service_hostname: str = os.environ.get('SERVICE_HOSTNAME', '')
        self.rate_limit: str = os.environ.get('GLOBAL_RATE_LIMIT', '600/minute')
        self.server_port: int = self._parse_int('SERVER_PORT', 8080)

        # MTA-STS Policy Configuration
        self.sts_mode: str = os.environ.get('STS_MODE', 'enforce').lower()
        self.sts_max_age: int = self._parse_int('STS_MAX_AGE', 86400)
        self.sts_mx_records: list[str] = self._parse_mx_records(
            os.environ.get('STS_MX_RECORDS', '')
        )

    def _parse_int(self, env_var: str, default: int) -> int:
        """Parse integer from environment variable with error handling."""
        value = os.environ.get(env_var, '')
        if not value:
            return default
        try:
            return int(value)
        except ValueError:
            self.logger.error(f"{env_var}='{value}' is not a valid integer, using default: {default}")
            return default

    def _parse_mx_records(self, mx_string: str) -> list[str]:
        """Parse comma-separated MX records into a list."""
        if not mx_string:
            return []
        return [record.strip() for record in mx_string.split(',') if record.strip()]

    def _validate_config(self) -> None:
        """Validate all configuration values and log warnings/errors."""
        errors: list[str] = []
        warnings: list[str] = []

        # SERVICE_HOSTNAME - Required
        if not self.service_hostname:
            errors.append("SERVICE_HOSTNAME is required but not set")
        elif not HOSTNAME_PATTERN.match(self.service_hostname):
            errors.append(f"SERVICE_HOSTNAME='{self.service_hostname}' is not a valid hostname")
        elif not self.service_hostname.startswith('mta-sts.'):
            warnings.append(f"SERVICE_HOSTNAME='{self.service_hostname}' should start with 'mta-sts.' per RFC 8461")

        # STS_MODE - Must be valid
        if self.sts_mode not in VALID_STS_MODES:
            errors.append(f"STS_MODE='{self.sts_mode}' is invalid. Must be one of: {', '.join(VALID_STS_MODES)}")

        # STS_MAX_AGE - Must be positive
        if self.sts_max_age <= 0:
            errors.append(f"STS_MAX_AGE={self.sts_max_age} must be a positive integer")
        elif self.sts_max_age < 86400:
            warnings.append(f"STS_MAX_AGE={self.sts_max_age} is less than 1 day (86400). Consider increasing for production")
        elif self.sts_max_age > 31557600:
            warnings.append(f"STS_MAX_AGE={self.sts_max_age} exceeds 1 year (31557600). This is unusually long")

        # STS_MX_RECORDS - Required and must be valid
        if not self.sts_mx_records:
            errors.append("STS_MX_RECORDS is required but not set or empty")
        else:
            for mx in self.sts_mx_records:
                if not MX_RECORD_PATTERN.match(mx):
                    errors.append(f"STS_MX_RECORDS contains invalid entry: '{mx}'")

        # GLOBAL_RATE_LIMIT - Must match pattern
        if not RATE_LIMIT_PATTERN.match(self.rate_limit):
            warnings.append(f"GLOBAL_RATE_LIMIT='{self.rate_limit}' format is invalid. Expected: number/period (e.g., 600/minute)")
            self.rate_limit = '600/minute'
            warnings.append(f"Using default rate limit: {self.rate_limit}")

        # SERVER_PORT - Must be valid port
        if not 1 <= self.server_port <= 65535:
            errors.append(f"SERVER_PORT={self.server_port} is not a valid port (1-65535)")

        # Log warnings
        for warning in warnings:
            self.logger.warning(warning)

        # Log errors and exit if critical
        if errors:
            for error in errors:
                self.logger.error(error)
            self.logger.critical("Configuration validation failed. Please fix the errors above.")
            sys.exit(1)

    def _build_policy_content(self) -> None:
        """Pre-build the MTA-STS policy content for faster responses."""
        mx_lines = "\n".join(f"mx: {record}" for record in self.sts_mx_records)
        self._policy_content = f"version: STSv1\nmode: {self.sts_mode}\nmax_age: {self.sts_max_age}\n{mx_lines}\n"

    def _log_startup_config(self) -> None:
        """Log the startup configuration."""
        self.logger.info("=" * 60)
        self.logger.info("MTA-STS Server starting")
        self.logger.info("=" * 60)
        self.logger.info(f"SERVICE_HOSTNAME: {self.service_hostname}")
        self.logger.info(f"STS_MODE: {self.sts_mode}")
        self.logger.info(f"STS_MAX_AGE: {self.sts_max_age} seconds")
        self.logger.info(f"STS_MX_RECORDS: {', '.join(self.sts_mx_records)}")
        self.logger.info(f"GLOBAL_RATE_LIMIT: {self.rate_limit}")
        self.logger.info(f"SERVER_PORT: {self.server_port}")
        self.logger.info("=" * 60)

    def _configure_rate_limiter(self) -> None:
        """Configure the rate limiter for request throttling (global limit)."""
        self.rate_limiter = Limiter(
            key_func=lambda: 'global',
            app=self.flask_app,
            default_limits=[self.rate_limit],
            storage_uri="memory://",
        )

    def _register_routes(self) -> None:
        """Register all Flask routes."""

        @self.flask_app.route('/')
        @self.rate_limiter.limit(self.rate_limit)
        def index() -> str:
            """Render the MTA-STS information page."""
            return render_template(
                'index.html',
                SERVICE_HOSTNAME=self.service_hostname,
                STS_MODE=self.sts_mode,
                STS_MAX_AGE=self.sts_max_age,
                STS_MX_RECORDS=self.sts_mx_records,
            )

        @self.flask_app.route('/.well-known/mta-sts.txt')
        @self.rate_limiter.limit(self.rate_limit)
        def mta_sts_policy() -> Response:
            """Return the MTA-STS policy file in plain text format."""
            return Response(self._policy_content, mimetype='text/plain')

        @self.flask_app.route('/health')
        def health() -> Response:
            """Health check endpoint for container orchestration."""
            return Response('{"status":"healthy"}', mimetype='application/json')

    def run(self) -> None:
        """Run the Flask development server."""
        self.flask_app.run(host='0.0.0.0', port=self.server_port)


def is_running_with_wsgi_server() -> bool:
    """Check if the application is running under a WSGI server like Gunicorn."""
    return 'gunicorn' in sys.modules


# Create application instance
application = MTASTSApp()
app = application.flask_app

if __name__ == '__main__':
    if not is_running_with_wsgi_server():
        application.run()
