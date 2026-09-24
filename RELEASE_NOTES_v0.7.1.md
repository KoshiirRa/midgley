# Release Notes - v0.7.1

**Release Date:** September 24, 2026  
**Build Target:** `dev-vm` (`10.42.42.54`), GitHub Actions & Cloudflare Edge  
**Tracking Issues:** [Issue #431](https://github.com/KoshiirRa/midgley/issues/431), [Issue #437](https://github.com/KoshiirRa/midgley/issues/437), [Issue #438](https://github.com/KoshiirRa/midgley/issues/438)

---

## 🚀 Overview & Release Highlights

Midgley **v0.7.1** is a focused security hardening, transport integrity, and infrastructure isolation release addressing API security, remote Model Context Protocol (MCP) transport, Cloudflare Worker endpoint protection, and CI/CD deployment isolation:

* **🛡️ HTTP MCP Transport Authentication & Session Binding (Issue #431):**
  * Authenticated remote MCP HTTP/SSE transport (`GET /mcp/sse`, `POST /mcp/messages`) via Bearer token, `X-API-Key`, or `?api_key=` query parameter.
  * Bound active SSE sessions to client caller tiers (`active_mcp_sessions`).
  * Enforced rate limits (30 requests/minute) per key and session context.
  * Safely downgraded unprivileged HTTP simulation tool calls to catalog scenarios while preserving unrestricted local CLI `stdio` operation.

* **🔒 Unified API Authentication & Cryptographic Hardening (Issue #437):**
  * Unified environment master key (`MIDGLEY_API_KEY`) and SQLite `KeyManager` provisioned keys across all request paths and query parameters.
  * Offloaded PBKDF2 SHA-256 password hashing and token validation to worker threads (`verify_key_async`, `check_rate_limit_async` via `asyncio.to_thread`), preventing ASGI event loop blocking.
  * Enforced strict API caller tier permissions (`require_privileged_tier`) on sensitive endpoints (`POST /api/v1/forecast/simulate` with custom headlines/cohort sim, `POST /api/v1/connectors/headline-arena/submit`, `POST /api/v1/graph/ingest`).
  * Defeated HMAC webhook replay attacks by validating timestamp freshness ($\pm 300\text{s}$) via `X-Signature-Timestamp` and `f"{ts}." + raw_body` signature hashing.
  * Protected edge cache probe diagnostics (`GET /api/v1/system/cache-status?probe=true`) with `X-Admin-Secret` and implemented automated transient `probe_key` cleanup across SQLite, Turso libSQL, and Cloudflare D1.

* **⚡ Cloudflare Worker Security, Dashboard Escaping & Staging CI (Issue #438):**
  * Configured fail-closed authentication on `workers/cache_worker.ts`, rejecting unauthenticated requests with `401 Unauthorized` if `CLOUDFLARE_AUTH_TOKEN` is unset or invalid.
  * Sanitized query reflections via HTML escaping (`escapeHtml()`) in `GET /flag` and added Bearer token authentication to `POST /flag`, `POST /run`, and `POST /trigger` in `workers/intraday_monitor_worker.ts`.
  * Added Content-Security-Policy (CSP) meta tag and sanitized dynamic event text reflections in `src/dashboard_generator.py`.
  * Isolated Cloudflare Worker staging (`dev` branch $\rightarrow$ `staging`) vs production (`main` branch $\rightarrow$ `production`) deployments in `wrangler.toml`, `workers/wrangler.cache.toml`, and `.github/workflows/deploy_cloudflare_worker.yml`.

---

## 🛠️ Detailed Component Changes

### 1. HTTP MCP Transport Authentication & Session Tier Binding (`src/api_server.py` & `src/mcp_server.py` - Issue #431)
- **SSE Transport Protection:** Remote clients connecting to `GET /mcp/sse` and sending tool messages to `POST /mcp/messages` must supply a valid API key. Supported authentication mechanisms include `Authorization: Bearer <key>`, `X-API-Key: <key>`, or `?api_key=<key>` (ideal for EventSource SSE browser clients).
- **Active Session Context Tracking:** Tracks active MCP session IDs in `active_mcp_sessions` mapping session IDs to authenticated user tiers (`privileged` vs `basic`).
- **Tier Downgrade & Token Protection:** When unprivileged HTTP clients execute the `simulate_fuel_market_shock` tool with custom parameters, the engine automatically downgrades the request to catalog scenario evaluation, preventing unauthorized Gemini token expenditure.
- **Unrestricted Local Stdio Mode:** Maintained standard unauthenticated operation for local CLI tools (`python -m src.mcp_server`), ensuring Claude Desktop and local agent environments continue running without configuration friction.

### 2. Unified Master & Provisioned Key Authentication (`src/key_manager.py` & `src/api_server.py` - Issue #437)
- **Unified Auth Middleware:** Streamlined API authentication middleware to verify credentials across both static environment master keys (`MIDGLEY_API_KEY`) and dynamic SQLite provisioned user keys (`data/security.db`).
- **Asynchronous PBKDF2 Offloading:** Wrapped compute-intensive PBKDF2 SHA-256 iterations in `verify_key_async()` and `check_rate_limit_async()` using `asyncio.to_thread()`, keeping FastAPI request throughput high during high-concurrency bursts.
- **Tier-Gated Endpoint Security:** Implemented `require_privileged_tier()` dependency restricting LLM cohort simulations, graph modifications, and headline arena submissions to verified `privileged` tier keys.
- **Webhook Timestamp Freshness:** Added `X-Signature-Timestamp` validation to `verify_webhook_signature()`. Inbound payloads are verified against $f"{ts}." + \text{raw\_body}$ with a $\pm 300$-second tolerance window, eliminating replay attack vulnerability while preserving backward compatibility for legacy non-timestamped payloads.
- **Diagnostic Endpoint Protection & Probe Cleanup:** Gated `/api/v1/system/cache-status?probe=true` behind `X-Admin-Secret` and enhanced `test_edge_connectivity()` in `src/lookup_cache.py` to automatically delete probe records from local SQLite, Turso libSQL, and Cloudflare D1.

### 3. Worker Authentication, HTML Escaping & CI Environment Isolation (`workers/` & `.github/workflows/` - Issue #438)
- **Fail-Closed Cache Worker:** Configured `workers/cache_worker.ts` to strictly require `CLOUDFLARE_AUTH_TOKEN`. Requests lacking a valid token fail closed with `HTTP 401 Unauthorized`.
- **Intraday Worker Hardening:** Added `escapeHtml()` utility to `workers/intraday_monitor_worker.ts` to neutralize HTML injection vulnerabilities in `GET /flag`. Secured administrative trigger routes (`POST /flag`, `POST /run`, `POST /trigger`) with Bearer token authentication.
- **Dashboard CSP & Text Sanitization:** Embedded strict `Content-Security-Policy` meta tags in `src/dashboard_generator.py` and sanitized dynamic trigger titles and timestamps in HTML cards.
- **Staging vs Production CI Isolation:** Created dedicated `[env.staging]` and `[env.production]` configurations in `wrangler.toml` and `workers/wrangler.cache.toml`. Automated deployment routing in `.github/workflows/deploy_cloudflare_worker.yml` ensures feature branches and `dev` deploy to staging environments, while `main` deploys to production.

---

## 🧪 Verification & Test Coverage

All enhancements were validated against both Python and TypeScript test suites on `dev-vm` (`10.42.42.54`):

* **Python Test Suite:**
  - `tests/test_api_server.py`: 44 tests passed covering master/provisioned key auth, query param auth, privileged vs basic tier permissions, webhook timestamp replay defense, and cache probe gating.
  - `tests/test_mcp_server.py`: 10 tests passed covering local stdio mode, HTTP SSE auth, session context tracking, and tier downgrading.
  - `tests/test_dashboard_generator.py`: 2 tests passed verifying CSP tags and HTML entity escaping.
  - **Result:** `56 passed in 68.32s`.

* **TypeScript / Cloudflare Worker Test Suite:**
  - `tests/workers.test.ts`: 17 tests passed in Vitest covering `cache_worker.ts` fail-closed auth, `intraday_monitor_worker.ts` endpoint authentication, HTML escaping on `GET /flag`, and queue batch processing.
  - **Result:** `17 passed in 0.70s`.
