import os

wiki_file = os.path.expanduser("~/projects/midgley/wiki_repo/Data-Ingestion-and-APIs.md")
with open(wiki_file, "r", encoding="utf-8") as f:
    content = f.read()

target = """## 22. User Authentication, Tiered Access Control & Dual Provisioning Framework (Issue #40)
* **Module:** `src/key_manager.py`, `scripts/manage_keys.py`, `src/api_server.py` (Issue #40 & #196)
* **Function:** Restricts REST API endpoints (`/api/v1/prices/*`, `/api/v1/forecast/*`, `/api/v1/combined`, `/api/v1/forecast/simulate`) and MCP transport (`/mcp/sse`, `/mcp/messages`) to authenticated users with salted PBKDF2 SHA-256 token hashing and 30 RPM sliding-window rate limiting.
* **Authentication Headers:**
  - `X-API-Key: mg_prod_...`
  - `Authorization: Bearer mg_prod_...`
  - `?api_key=mg_prod_...` (query parameter for SSE/browser connections)
* **Key Access Tiers:**
  - 👑 **`privileged` tier:** Unlocks full multi-agent LLM inference (Google Gemini 2.5 Flash event analysis, full Stacking Ensemble, and counterfactual shock simulations).
  - 🛡️ **`basic` tier:** Automatically routes event scoring to zero-cost fallback providers (Tier 3 Rule-Based Lexicon, SPC weather mapping, cached news vectors, standard linear Ridge baseline) to conserve Gemini tokens and Finlight API quotas (Issue #196).
* **Dual Provisioning Architecture:**
  - **Method A (CLI Utility - `scripts/manage_keys.py`):** Admin CLI tool supporting `create`, `list`, `revoke`, and `verify` commands directly on the server host.
  - **Method B (Admin REST API - `/api/v1/admin/keys`):** Programmatic key management endpoints (`POST`, `GET`, `DELETE`) protected by `MIDGLEY_ADMIN_SECRET` environment variable (`X-Admin-Secret` header). **Fail-Closed Security (Issue #341):** If `MIDGLEY_ADMIN_SECRET` is unset, empty, or whitespace-only on the server, all admin provisioning endpoints immediately fail closed with `HTTP 401 Unauthorized` (`Admin secret is not configured or invalid`). No default or fallback admin secret is permitted.
  - **Global Middleware Route Matching (Issue #344):** API authentication and rate-limiting middleware enforces exact root matching (`request.url.path == \"/\"`) for public documentation rather than a prefix match on `\"/\"`. All protected API routes (`/api/v1/*`, `/mcp/*`) strictly require valid authentication, while public documentation routes (`/docs`, `/redoc`, `/openapi.json`, `/.well-known`, `/health`) remain exempt.
* **Cloudflare D1 Decoupled Edge Architecture:** Edge workers (`workers/cache_worker.ts`) bind directly to Cloudflare D1 (`midgley-cache-d1`) for edge key/cache verification without relying on calls to home infrastructure."""

replacement = """## 22. User Authentication, Tiered Access Control, Async Verification & MCP Transport Security (Issues #40, #341, #344, #431, #437, #438)
* **Module:** `src/key_manager.py`, `scripts/manage_keys.py`, `src/api_server.py`, `src/mcp_server.py`
* **Function:** Restricts REST API endpoints (`/api/v1/prices/*`, `/api/v1/forecast/*`, `/api/v1/combined`, `/api/v1/forecast/simulate`, `/api/v1/graph/ingest`, `/api/v1/connectors/headline-arena/submit`) and remote MCP transport (`/mcp/sse`, `/mcp/messages`) to authenticated users with salted PBKDF2 SHA-256 token hashing and 30 RPM sliding-window rate limiting.
* **Unified Master & Provisioned Key Auth (Issue #437):** Unifies environment master key `MIDGLEY_API_KEY` with SQLite provisioned keys (`data/security.db`) across all request paths (`X-API-Key`, `Authorization: Bearer`, and query param `?api_key=`), with non-blocking async offloading (`verify_key_async`, `check_rate_limit_async` via `asyncio.to_thread`) to prevent blocking the ASGI event loop.
* **Key Access Tiers:**
  - 👑 **`privileged` tier:** Unlocks full multi-agent LLM inference (Google Gemini 2.5 Flash event analysis, MiroFish multi-agent cohort simulation, custom headline counterfactual shock simulation, graph ingestion, and headline arena submission).
  - 🛡️ **`basic` tier:** Automatically routes event scoring to zero-cost fallback providers (Tier 3 Rule-Based Lexicon, SPC weather mapping, cached news vectors, standard linear Ridge baseline). Unprivileged calls to privileged endpoints return `HTTP 403 Forbidden`.
* **MCP HTTP Transport Security & Session Binding (Issue #431):**
  - Secures remote SSE transport (`GET /mcp/sse`, `POST /mcp/messages`) with API key authentication, rate limiting, and session context binding (`active_mcp_sessions`).
  - Unprivileged HTTP MCP callers are downgraded from LLM cohort simulations to standard catalog shocks, while local CLI `stdio` MCP transport (`python -m src.mcp_server`) remains unauthenticated and unrestricted.
* **Webhook Replay Protection (Issue #437):**
  - Accepts `X-Signature-Timestamp` header and validates timestamp freshness within $\pm 300\text{s}$ (5 minutes).
  - Verifies HMAC over `f"{ts}." + raw_body` (with fallback to legacy raw payload bytes).
* **Protected Diagnostics & Probe Key Cleanup (Issue #437):**
  - Gated `GET /api/v1/system/cache-status?probe=true` behind `X-Admin-Secret`.
  - Automatically purges transient `probe_key` records across SQLite, Turso libSQL, and Cloudflare D1.
* **Dual Provisioning Architecture:**
  - **Method A (CLI Utility - `scripts/manage_keys.py`):** Admin CLI tool supporting `create`, `list`, `revoke`, and `verify` commands directly on the server host.
  - **Method B (Admin REST API - `/api/v1/admin/keys`):** Programmatic key management endpoints (`POST`, `GET`, `DELETE`) protected by `MIDGLEY_ADMIN_SECRET` environment variable (`X-Admin-Secret` header). **Fail-Closed Security (Issue #341):** If `MIDGLEY_ADMIN_SECRET` is unset, empty, or whitespace-only on the server, all admin provisioning endpoints immediately fail closed with `HTTP 401 Unauthorized`.
  - **Global Middleware Route Matching (Issue #344):** API authentication and rate-limiting middleware enforces exact root matching for public documentation. Protected API routes (`/api/v1/*`, `/mcp/*`) strictly require valid authentication.
* **Cloudflare Workers Security & Staging Isolation (Issue #438):**
  - `workers/cache_worker.ts` enforces fail-closed token validation via `CLOUDFLARE_AUTH_TOKEN`.
  - `workers/intraday_monitor_worker.ts` enforces token authentication on `POST /flag`, `/run`, `/trigger` and HTML-escapes query reflections on `GET /flag`.
  - `wrangler.toml` and `workers/wrangler.cache.toml` define `[env.staging]` (`dev` branch) vs `[env.production]` (`main` branch)."""

if target in content:
    content = content.replace(target, replacement)
    with open(wiki_file, "w", encoding="utf-8") as f:
        f.write(content)
    print("Successfully updated Data-Ingestion-and-APIs.md in wiki_repo")
else:
    print("Target section not found exactly in Data-Ingestion-and-APIs.md")
