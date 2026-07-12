# mdify — Universal File-to-Markdown Converter

> Convert any document — PDF, Word, Excel, HTML, CSV, JSON, XML — to clean, structurally accurate Markdown. All processing is local. No data leaves your server.

---

## Table of Contents

1. [Overview](#overview)
2. [Prerequisites](#prerequisites)
3. [Quick Start (One Command)](#quick-start)
4. [Environment Variable Reference](#environment-variable-reference)
5. [Service Topology](#service-topology)
6. [Running Tests](#running-tests)
7. [Troubleshooting](#troubleshooting)
8. [Architecture](#architecture)
9. [Contributing](#contributing)

---

## Overview

mdify is a  SaaS application that converts uploaded documents to Markdown with:

- ✅ **100% local parsing** — MarkItDown + pypdf, no LLM APIs
- ✅ **Antivirus scanning** — every file scanned by ClamAV before parsing
- ✅ **Magic-number validation** — file extension spoofing is rejected at the gateway
- ✅ **XXE protection** — all XML parsers globally defused at startup
- ✅ **Ephemeral storage** — all files securely deleted 10 minutes after conversion
- ✅ **Real-time progress** — live staged pipeline visualization via Server-Sent Events
- ✅ **Batch processing** — convert multiple files concurrently, download a single ZIP

---

## Prerequisites

| Requirement | Version |
|-------------|--------|
| Docker | 24.0+ |
| Docker Compose | v2.20+ (plugin) |
| Available RAM | ~3 GB (ClamAV needs ~2 GB) |
| Free disk space | ~5 GB (for ClamAV DB + Docker images) |

> **Note**: No Python or Node.js install required on the host. Everything runs inside Docker.

---

## Quick Start

```bash
# 1. Clone the repository
git clone https://github.com/your-org/mdify.git
cd mdify

# 2. Set up environment
cp .env.example .env
# Edit .env if you need to change default ports

# 3. Start the full stack (takes 2–5 min on first run; ClamAV downloads ~300 MB of signatures)
docker compose up --build

# 4. Open the app
open http://localhost:3000
```

> ⚠️ **First run note**: ClamAV runs `freshclam` on startup to download virus signatures (~300 MB). The `worker` and `backend` services will wait for ClamAV to become healthy before starting. This may take 2–3 minutes on first run.

---

## Environment Variable Reference

| Variable | Default | Description |
|----------|---------|-------------|
| `FRONTEND_PORT` | `3000` | Host port for the React SPA |
| `BACKEND_PORT` | `8000` | Host port for the FastAPI REST API |
| `BACKEND_PUBLIC_URL` | `http://localhost:8000` | Public URL of the API (used by Nginx proxy) |
| `REDIS_URL` | `redis://redis:6379/0` | Redis connection URL for Celery broker |
| `CELERY_BROKER_URL` | `redis://redis:6379/0` | Celery broker URL |
| `CELERY_RESULT_BACKEND` | `redis://redis:6379/1` | Celery result backend URL |
| `CLAMAV_HOST` | `clamav` | ClamAV daemon hostname (internal Docker network) |
| `CLAMAV_PORT` | `3310` | ClamAV daemon port |
| `MAX_UPLOAD_SIZE_MB` | `50` | Maximum file upload size in MB |
| `PURGE_INTERVAL_SECONDS` | `600` | Seconds after completion before files are deleted |

Copy `.env.example` to `.env` and modify as needed. The `.env` file is git-ignored.

---

## Service Topology

```
                    ┌──────────────────────────────┐
         HOST       │       DOCKER NETWORK           │
                    │           mdify_net             │
  :3000 ➡ ┌────────────┐  ┌────────────┐  │
         │ frontend  │─────►│  backend  │  │
         └────────────┘  └────────────┘  │
  :8000 ➡ ┌────────────┐          │         │
         │ backend   │────────────►│  redis   │  │
         └────────────┘          │ (internal)│
                                  └────────────┘  │
                    │  ┌────────────┐  ┌──────────┐  │
                    │  │  worker   │  │  clamav  │  │
                    │  │ (internal)│  │(internal)│  │
                    │  └────────────┘  └──────────┘  │
                    │                               │
                    │  ┌─────────────────────┐     │
                    │  │ conversions_data (volume) │     │
                    │  └─────────────────────┘     │
                    └──────────────────────────────┘
```

**Public ports**: `frontend:3000`, `backend:8000`
**Internal-only**: `redis:6379`, `clamav:3310`, `worker` (no port)
**Shared volume**: `conversions_data` mounted at `/tmp/conversions/` in both `backend` and `worker`

---

## Running Tests

### Inside Docker (recommended)
```bash
# Run all backend tests
docker compose run --rm backend poetry run pytest --cov=src -v

# Run just unit tests
docker compose run --rm backend poetry run pytest tests/unit/ -v

# Run frontend tests
docker compose run --rm frontend npm test

# Run E2E tests (requires full stack)
docker compose up -d
docker compose run --rm frontend npx playwright test
```

### On host (with Python 3.11+ and Node 20+)
```bash
# Backend
cd backend
poetry install
poetry run pytest

# Frontend
cd frontend
npm ci && npm test
```

---

## Troubleshooting

### ClamAV is slow to start / worker won't start
**Cause**: ClamAV downloads ~300 MB of signatures on first run.
**Fix**: Wait 2–3 minutes. Monitor with: `docker compose logs -f clamav`

### ClamAV signature database is stale
**Cause**: `freshclam` update may have failed or signatures are outdated.
**Fix**: `docker compose restart clamav` — this triggers a fresh `freshclam` run.

### Redis connection refused
**Cause**: Redis container not healthy yet, or wrong `REDIS_URL`.
**Fix**: `docker compose ps` to check Redis health. Check `REDIS_URL` in `.env`.

### Sandbox volume permissions error
**Cause**: The `conversions_data` volume may have wrong ownership.
**Fix**:
```bash
docker compose down -v
docker volume rm mdify_conversions_data
docker compose up --build
```

### Files not being purged after 10 minutes
**Cause**: Celery worker may not be running or Redis connectivity issue.
**Fix**: `docker compose logs worker` to check for errors. Ensure worker is healthy.

### Port conflict (3000 or 8000 already in use)
**Fix**: Change `FRONTEND_PORT` or `BACKEND_PORT` in `.env` and restart.

---

## Architecture

mdify uses a Domain-Driven Design with three bounded contexts:

| Context | Responsibility |
|---------|---------------|
| `IngestionContext` | File uploads, magic-number validation, sandbox creation, ClamAV scanning, SSE streaming |
| `ParsingContext` | Celery tasks, MarkItDown adapter (text/tables), pypdf adapter (images) |
| `AssetContext` | Base64 encoding, ZIP packaging (single and batch) |

**Tech stack**: FastAPI + Uvicorn (API), Celery + Redis (async queue), MarkItDown + pypdf (parsers), ClamAV (AV), React + TypeScript + TailwindCSS (frontend).

---

## Contributing

1. Fork the repository and create a feature branch: `git checkout -b feature/001-your-feature`
2. Follow the [mdify Contribution Guidelines](./CONTRIBUTION.md) — TDD, DDD, typed exceptions, no generic errors
3. Commit using [Conventional Commits](https://www.conventionalcommits.org/): `feat:`, `fix:`, `test:`, `refactor:`

---

*All files are processed entirely on your infrastructure. mdify never calls external APIs for parsing.*
