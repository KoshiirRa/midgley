---
name: midgley-edge-api-ops
description: >-
  Guides changes to Midgley's FastAPI REST gateway (src/api_server.py), MCP
  server (src/mcp_server.py), Cloudflare Workers (workers/), midgley-auto
  client schema contracts, and Docker/systemd/packaging operations. Use when
  modifying API routes, auth/rate-limit middleware, edge cache workers,
  dependencies, or self-hosted deployment templates.
---

# Midgley Edge Workers, API/MCP Gateway & Self-Hosted Operations

Use this runbook when modifying the REST/MCP server, Cloudflare Workers, client API contracts, or self-hosted packaging and service units.

## 1. Security & Gateway Invariants (`src/api_server.py`, `src/mcp_server.py`)

1. **Authentication & Key Tiers**:
   - Preserve unified `MIDGLEY_API_KEY` and SQLite provisioned-key verification via non-blocking `verify_key_async` with constant-time comparison.
   - Enforce `privileged` tier checks on sensitive routes (e.g., custom shock simulations, Headline Arena submissions, graph ingestion); unprivileged callers must receive HTTP 403.
   - Remote MCP HTTP/SSE (`/mcp/sse`, `/mcp/messages`) must enforce API key authentication, 30 RPM rate limiting, and session tier binding. Local CLI `stdio` MCP transport remains unauthenticated.
2. **Webhooks & Admin Probes**:
   - Preserve HMAC-SHA256 signature verification and timestamp replay defense ($\pm 300\text{s}$ via `X-Signature-Timestamp`).
   - Keep admin and cache-probe writes fail-closed (`X-Admin-Secret`) and ensure probe endpoints clean up transient keys across D1/Turso/SQLite.
3. **Secret Hygiene**:
   - Never expose raw credentials, tokens, private host addresses, or machine-specific paths in code, logs, OpenAPI specs, or published docs.

## 2. Cloudflare Workers (`workers/`, `wrangler*.toml`)

- `workers/cache_worker.ts`: Preserve fail-closed Bearer token checks against `CLOUDFLARE_AUTH_TOKEN`.
- `workers/intraday_monitor_worker.ts`: Preserve token authentication on mutating routes (`POST /flag`, `/run`, `/trigger`) and HTML escaping on reflected query parameters.
- Respect staging/production isolation: `--env staging` corresponds to `dev`; `--env production` corresponds to `main`. Do not deploy workers without explicit authorization.

## 3. Client Contract Sync (`midgley-auto`)

- Any change to `CombinedApiResponse` or static JSON payloads (`/api/v1/combined*.json` from `src/static_api_exporter.py`) must be documented and cross-linked for `KoshiirRa/midgley-auto` (`CombinedModels.kt`).
- Keep Android-specific issues routed to `KoshiirRa/midgley-auto`; do not mix release tracks.

## 4. Packaging, Line Endings & Durable Self-Hosting

1. **Dependencies**: Keep version pins/floors aligned across `pyproject.toml`, `requirements.txt`, and `requirements.lock` while preserving Python >=3.11 compatibility (CI tests 3.11, 3.12, 3.13).
2. **Line Endings & Dynamic Paths**: Enforce LF (`\n`) per `.gitattributes`. Use dynamic path resolution in `scripts/run_local_*.sh` and `%h` in `systemd/*.service` templates.
3. **Container Durability**: Keep persistent state on mounted volumes with empty-volume bootstrap migrations (`Dockerfile`, `SELF_HOSTING.md`).
4. **Schedules**: Derive cron/timer schedules directly from `.github/workflows/`, `systemd/*.timer`, and `wrangler*.toml` with explicit time zones and DST awareness rather than copying prose offsets.

## 5. Verification

```sh
ruff check .
TESTING=1 pytest -v tests/test_api_server.py tests/test_api_rate_limiter.py tests/test_api_batch_locales.py
TESTING=1 pytest -v tests/test_docs_links.py
```

If API contracts or environment variables changed, update `API.md` / `SELF_HOSTING.md` / `docs/openapi.json` as applicable and sync mirrors via `python scripts/verify_docs_parity.py --sync`.
