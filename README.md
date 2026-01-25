# MTA-STS Server

[![Release](https://img.shields.io/github/v/release/bauer-group/CS-MTASTS?style=flat-square)](https://github.com/bauer-group/CS-MTASTS/releases)
[![Docker](https://img.shields.io/badge/docker-ghcr.io-blue?style=flat-square)](https://github.com/bauer-group/CS-MTASTS/pkgs)
[![License](https://img.shields.io/github/license/bauer-group/CS-MTASTS?style=flat-square)](LICENSE)

A lightweight Mail Transfer Agent Strict Transport Security (MTA-STS) policy server implementing [RFC 8461](https://datatracker.ietf.org/doc/html/rfc8461).

## Features

- Serves MTA-STS policy files at `/.well-known/mta-sts.txt`
- Modern dark-themed web interface with policy configuration display
- Copyable DNS record templates with dynamic timestamps
- Global rate limiting for DDoS protection
- Configuration validation at startup with detailed logging
- Health check endpoint for container orchestration
- Runs as non-root user for security
- Multi-platform deployment support (Traefik, Coolify, standalone)

## Quick Start

### 1. Configure Environment

```bash
cp .env.example .env
# Edit .env with your domain settings
```

### 2. Deploy

Choose your deployment method:

| Method | Command |
|--------|---------|
| **Coolify** | `docker compose -f docker-compose.coolify.yml --env-file .env up -d` |
| **Traefik** | `docker compose -f docker-compose.traefik.yml --env-file .env up -d` |
| **Local** | `docker compose -f docker-compose.local.yml --env-file .env up -d` |
| **Development** | `docker compose -f docker-compose.development.yml --env-file .env up -d` |

### 3. Configure DNS

Create the required DNS records (see [DNS Setup](#dns-setup) below).

## Docker Image

Pre-built images are available from GitHub Container Registry:

```bash
docker pull ghcr.io/bauer-group/cs-mtasts/mtasts:latest
```

## Configuration

### Environment Variables

| Variable | Default | Description |
|----------|---------|-------------|
| `SERVICE_HOSTNAME` | `mta-sts.example.com` | MTA-STS hostname (must match DNS) |
| `GLOBAL_RATE_LIMIT` | `600/minute` | Global request rate limit (DDoS protection) |
| `STS_MODE` | `enforce` | Policy mode: `enforce`, `testing`, `none` |
| `STS_MAX_AGE` | `86400` | Policy cache time in seconds (1 day) |
| `STS_MX_RECORDS` | - | Comma-separated list of MX records |
| `TIME_ZONE` | `Etc/UTC` | Container timezone |
| `STACK_NAME` | - | Stack name for container naming |

### Deployment-Specific Variables

| Variable | Used By | Description |
|----------|---------|-------------|
| `PROXY_NETWORK` | Traefik | External Traefik proxy network name |
| `EXPOSED_PORT` | Local, Development | Port mapping (e.g., `8080`, `127.0.0.1:8080`) |

### Deployment Options

| Compose File | Image Source | Port Exposure | Use Case |
|--------------|--------------|---------------|----------|
| `docker-compose.coolify.yml` | GHCR | None (managed) | Coolify or orchestrated deployments |
| `docker-compose.traefik.yml` | GHCR | Via Traefik | Production with TLS via Traefik |
| `docker-compose.local.yml` | GHCR | `EXPOSED_PORT` | Local testing with pre-built image |
| `docker-compose.development.yml` | Build | `EXPOSED_PORT` | Development with source build |

## DNS Setup

### Required: A/AAAA Record

Point your MTA-STS hostname to the server:

```
mta-sts.example.com  A     <server-ip>
mta-sts.example.com  AAAA  <server-ipv6>  (optional)
```

### Required: MTA-STS Policy TXT Record

```
_mta-sts.example.com  TXT  "v=STSv1; id=20240101120000"
```

> **Note:** Update the `id` value (timestamp format: `YYYYMMDDHHmmss`) whenever you change your MTA-STS policy.

### Optional: TLS Reporting (TLSRPT)

Enable receiving TLS failure reports:

```
_smtp._tls.example.com  TXT  "v=TLSRPTv1; rua=mailto:mta-sts@example.com"
```

## API Endpoints

| Endpoint | Method | Description |
|----------|--------|-------------|
| `/` | GET | Web interface with policy info and DNS templates |
| `/.well-known/mta-sts.txt` | GET | MTA-STS policy file (plain text) |
| `/health` | GET | Health check endpoint (JSON) |

### Policy File Format

```
version: STSv1
mode: enforce
max_age: 86400
mx: mx1.example.com
mx: mx2.example.com
```

## STS Modes

| Mode | Behavior | Use Case |
|------|----------|----------|
| `enforce` | Strict TLS requirement; delivery fails without secure connection | Production |
| `testing` | Monitoring mode; allows fallback to plaintext on TLS failure | Initial deployment |
| `none` | MTA-STS disabled | Graceful deprecation |

## Validation

The server validates all configuration at startup:

- **Critical errors** (container will not start):
  - Missing `SERVICE_HOSTNAME`
  - Invalid `STS_MODE`
  - Missing or invalid `STS_MX_RECORDS`

- **Warnings** (logged but container starts):
  - Hostname not starting with `mta-sts.`
  - `STS_MAX_AGE` too short (< 1 day) or too long (> 1 year)
  - Invalid `GLOBAL_RATE_LIMIT` format

## References

- [RFC 8461 - SMTP MTA Strict Transport Security](https://datatracker.ietf.org/doc/html/rfc8461)
- [RFC 8460 - SMTP TLS Reporting](https://datatracker.ietf.org/doc/html/rfc8460)
- [Google MTA-STS Guide](https://support.google.com/a/answer/9261504)

## License

MIT License - See [LICENSE](LICENSE) for details.
