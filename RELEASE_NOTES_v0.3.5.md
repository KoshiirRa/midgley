# Release Notes - v0.3.5-dev

**Release Date:** September 3, 2026  
**Build Target:** `dev-vm` (`10.42.42.54`)  
**Git Branch:** `dev`  

---

## 🚀 Key Features & Architectural Enhancements

### 1. Locales Metadata & Multi-Region Batch Forecast Gateway (Issue #48)
- **Locales Discovery Endpoint (`GET /api/v1/locales`):** Dynamically exposes metadata profiles across all 9 supported locales (`tulsa`, `newark`, `cincinnati`, `greenville`, `charlotte`, `oakland`, `port_st_lucie`, `bayarea`, `national`), return PADD region mappings, statutory fuel tax burdens (including CARB tax components), refining hub logistics, and metadata profiles loaded via `src/regional_metadata.py`.
- **Batch Forecast Endpoint (`POST /api/v1/forecast/batch`):** Enables client applications to query 5-day out-of-time forecasts for multiple locales in a single HTTP request payload (`{"locales": ["tulsa", "oakland", "cincinnati"], "days": 5}`).
- **Batch Combined Endpoint (`POST /api/v1/combined/batch`):** Enables client applications to query combined live pump prices, forecasts, feature attributions, and provenance metadata across multiple locales in a single payload.
- **Unit Test Suite ([`tests/test_api_batch_locales.py`](file:///c:/Users/concentus/Documents/Random%20Ideas%20-%20LLM%20Unleaded%20Gas%20Price%20Prediction%20Modelling/tests/test_api_batch_locales.py)):** Verifies HTTP 200 responses, schema validation, multi-locale payload structures, and default empty list fallbacks.

### 2. Prediction History Cloud Relational Synchronization (Issue #82)
- **Multi-Cloud Relational Sync (`sync_predictions_to_cloud()`):** Synchronizes out-of-time prediction history logs and backfilled actual outcomes to remote relational databases (Turso Edge SQLite via `/v2/pipeline` REST JSON payloads, Cloudflare D1 Edge Workers via `CLOUDFLARE_CACHE_URL` / `workers/cache_worker.ts`, or Neon Postgres) with automatic `prediction_history` table schema creation and record upserts.
- **100% Offline Fallback:** Operates defensively in background execution blocks so local CSV datastore (`data/prediction_history.csv`) remains fully operational without blocking execution if cloud endpoints are offline or credentials are absent.
- **REST Status Endpoints:** Exposed via `POST /api/v1/forecast/cloud-sync` and `GET /api/v1/forecast/cloud-status` (`get_cloud_sync_status()`).

### 3. Fireworks Tech Graph Automated Diagram Generator (Issue #191)
- **SVG Vector Diagram Generator (`src/fireworks_tech_graph.py`):** Auto-synthesizes self-contained dark-theme SVG vector diagrams outputting to `docs/assets/multi_agent_architecture.svg` (~12.5 KB) and `docs/assets/regional_metro_architecture.svg` (~7.7 KB) during public web dashboard builds (`src/dashboard_generator.py`).
### 4. 4-Tier ZIP Code Geocoding & PADD Resolution Engine (Issue #50)
- **ZIP Resolution Module ([`src/zip_geocoding.py`](file:///c:/Users/concentus/Documents/Random%20Ideas%20-%20LLM%20Unleaded%20Gas%20Price%20Prediction%20Modelling/src/zip_geocoding.py)):** Resolves any 5-digit US ZIP code to mapped metro area locale, PADD region, state, and statutory state fuel tax policy via a 4-tier fallback engine (Metro Cluster hit -> State/PADD fallback -> Live GasBuddy station search -> Resolution metadata).
- **REST API Integration:** Query parameters `?zip_code=...` added to `GET /api/v1/prices/live`, `GET /api/v1/forecast/predict`, and `GET /api/v1/combined`.

### 5. Dedicated System Observability & Out-of-Metro Demand Heatmap (Issue #195)
- **Dedicated Telemetry Page ([`docs/telemetry.html`](file:///c:/Users/concentus/Documents/Random%20Ideas%20-%20LLM%20Unleaded%20Gas%20Price%20Prediction%20Modelling/docs/telemetry.html)):** Dedicated web page off `docs/index.html` rendering interactive Leaflet.js maps of requested out-of-metro ZIP codes, state query density, API quota ledgers (`finlight.me` 150 call cap), 3-tier cache hit rates, MLOps model win rates, and candidate metro hub recommendations (Chicago, Houston, Los Angeles, Philadelphia).
- **Telemetry REST Endpoint (`GET /api/v1/telemetry/unmapped-zips`):** Exposes aggregated out-of-metro lookup counts, state query distributions, and expansion hub recommendations.

### 6. User Authentication, Tiered Access Control & Dual Provisioning Framework (Issue #40)
- **SQLite Key Manager Engine ([`src/key_manager.py`](file:///c:/Users/concentus/Documents/Random%20Ideas%20-%20LLM%20Unleaded%20Gas%20Price%20Prediction%20Modelling/src/key_manager.py)):** Manages API keys stored in SQLite database (`data/security.db`) with salted PBKDF2 SHA-256 token hashing and 30 RPM sliding-window rate limiting.
- **Method A CLI Utility ([`scripts/manage_keys.py`](file:///c:/Users/concentus/Documents/Random%20Ideas%20-%20LLM%20Unleaded%20Gas%20Price%20Prediction%20Modelling/scripts/manage_keys.py)):** Admin command-line tool supporting `create`, `list`, `revoke`, and `verify` commands directly on the server host.
- **Method B Admin REST API Gateway (`/api/v1/admin/keys`):** Programmatic key management endpoints (`POST`, `GET`, `DELETE`) protected by `MIDGLEY_ADMIN_SECRET` environment variable (`X-Admin-Secret` header).
- **Endpoint Auth & Tiered Access Control:** Protects `/api/v1/prices/*`, `/api/v1/forecast/*`, `/api/v1/combined`, `/api/v1/forecast/simulate`, `/api/v1/diesel/*`, and `/mcp/*`. `privileged` tier unlocks full multi-agent LLM inference, while `basic` tier automatically routes event scoring to zero-cost fallback providers ([Issue #196](https://github.com/KoshiirRa/midgley/issues/196)) to preserve Gemini tokens and Finlight API quotas.
- **Cloudflare D1 Edge Decoupling:** Edge workers ([`workers/cache_worker.ts`](file:///c:/Users/concentus/Documents/Random%20Ideas%20-%20LLM%20Unleaded%20Gas%20Price%20Prediction%20Modelling/workers/cache_worker.ts)) bind directly to Cloudflare D1 (`midgley-cache-d1`) for edge key/cache verification without relying on calls to home infrastructure.

### 7. Strategy 4 Webhook Gateway Payload Transformers & Multi-Locale Routing (Issue #78)
- **Flexible Payload Transformer (`POST /api/v1/events/webhook`):** Supports generic push webhooks from external alert tools (Zapier, IFTTT, Google Alerts, TradingView) using flexible field alias transformations (`headline` $\leftarrow$ `title` / `text` / `summary` / `tweet_content` / `article_title`, `url` $\leftarrow$ `link` / `article_url` / `web_url`, `source` $\leftarrow$ `origin` / `provider` / `channel`).
- **Target Locales Resolution:** Automatically parses incoming headlines to resolve affected regional metro agents (`Tulsa`, `Newark`, `Cincinnati`, `Greenville`, `Charlotte`, `Oakland`, `Port_St_Lucie`, `National`) via `resolve_target_locales()` in `src/intraday_event_monitor.py`.
- **HMAC-SHA256 Signature Security:** Verifies payload integrity via `X-Midgley-Signature` header when `MIDGLEY_WEBHOOK_SECRET` is set in the environment.
- **Documentation & Integration Guide:** Published complete integration guide in [docs/WEBHOOK_FORMATTING_GUIDE.md](file:///c:/Users/concentus/Documents/Random%20Ideas%20-%20LLM%20Unleaded%20Gas%20Price%20Prediction%20Modelling/docs/WEBHOOK_FORMATTING_GUIDE.md) and GitHub Wiki [Incoming-Webhook-Formatting-Guide.md](file:///c:/Users/concentus/Documents/Random%20Ideas%20-%20LLM%20Unleaded%20Gas%20Price%20Prediction%20Modelling/scratch/midgley.wiki/Incoming-Webhook-Formatting-Guide.md).

### 8. IPASIS API Gateway Security & Telemetry Accounting (Issue #87)
- **Real-Time IP Reputation Filtering ([`src/ipasis_security.py`](file:///c:/Users/concentus/Documents/Random%20Ideas%20-%20LLM%20Unleaded%20Gas%20Price%20Prediction%20Modelling/src/ipasis_security.py)):** Queries IPASIS API (`https://api.ipasis.com/v1/lookup`) to block high-risk origins (Tor exit nodes, malicious proxies, abuse subnets) with `HTTP 403 Forbidden` on incoming push webhooks.
- **Zero-Overhead Private IP Bypass:** Automatically bypasses external API lookups for loopback (`127.0.0.1`, `::1`), RFC 1918 private subnets (`10.x.x.x`, `172.16-31.x.x`, `192.168.x.x`), and internal test runners (`testclient`, `localhost`).
- **1-Hour TTL Cache & Fail-Open Resiliency:** Caches IP lookup results for 3600s (`_IP_CACHE`) and gracefully fails open on network timeouts to prevent service degradation.
- **Quota Accounting & Observability Dashboard:** Tracks daily API request usage against the **100 req/day free allowance cap** (`data/ipasis_telemetry.json`), exposing metrics via `GET /api/v1/security/ip-status` and rendering real-time quota progress cards on `docs/telemetry.html`.

### 9. Cloudflare Queues Edge Event Buffer & Batch Processing Gateway (Issue #194)
- **Cloudflare Queues Edge Buffer (`intraday-event-queue`):** Asynchronous edge event queue (`INTRADAY_QUEUE` producer binding in `wrangler.toml` with `intraday-event-dlq` dead-letter queue) decoupling high-frequency headline burst detection and webhook pushes from origin server execution. Included on Workers Free tier (10,000 free operations/day).
- **Batch Queue Consumer Handler:** `handleQueueBatch` in `workers/intraday_monitor_worker.ts` processes message batches asynchronously, enforcing edge cache deduplication, retry backoffs, and dead-letter queue routing.
- **Origin Batch Consumer Endpoint (`POST /api/v1/events/queue-consumer`):** Batch consumer REST schema in `src/api_server.py` supporting batch headline ingestion and target locale resolution.
- **Unit Test Suite ([`tests/test_cloudflare_queues.py`](file:///c:/Users/concentus/Documents/Random%20Ideas%20-%20LLM%20Unleaded%20Gas%20Price%20Prediction%20Modelling/tests/test_cloudflare_queues.py)):** Full unit test suite verifying single and batch queue payloads, invalid JSON schema handling, and dead-letter fallback.

### 10. System Architecture Diagram Vectorization & LaTeX Math Formatting
- **Fireworks Tech Graph Vector Diagrams (`src/fireworks_tech_graph.py`):** Expanded automated SVG diagram generator (ingested in Issue #191) to synthesize 6 self-contained vector diagrams (`multi_agent_architecture.svg`, `regional_metro_architecture.svg`, `weather_architecture.svg`, `web_routing_architecture.svg`, `cache_gateway_architecture.svg`, `worker_telemetry_architecture.svg`), replacing all ASCII flowcharts in `docs/ARCHITECTURE.md`.
- **KaTeX LaTeX Math Formatting Fixes:** Corrected LaTeX math display blocks (`\[ ... \]`) and dollar sign escaping across `docs/ARCHITECTURE.md` to guarantee clean KaTeX rendering on the `/math` documentation page.

---

## 🧪 Verification & Test Suite Results
- **Full Test Suite Execution on `dev-vm` (`10.42.42.54`):**
  ```bash
  PYTHONPATH=. pytest
  ```
  **Result:** `274 passed, 1 warning in 564.32s` (100% pass rate across 56 test modules).

---

## 📋 Closed GitHub Issues
- **Issue #40**: `feat(security): Implement user authentication & access control for MCP Server & REST API Gateway` (Closed as completed)
- **Issue #48**: `feat(api): Add GET /locales Metadata Endpoint & POST /forecast/batch Endpoint` (Closed as completed)
- **Issue #50**: `feat(geocoding): Add ZIP Code to Locale & PADD Resolution Mapping Engine` (Closed as completed)
- **Issue #78**: `feat(api): expand Strategy 4 incoming webhook gateway with flexible payload transformers & locale routing` (Closed as completed)
- **Issue #82**: `[Feature Request] Synchronize Prediction History & Lookup Cache with Serverless Postgres (Neon / D1)` (Closed as completed)
- **Issue #87**: `feat(security): implement IPASIS API Gateway Security & Telemetry accounting` (Closed as completed)
- **Issue #191**: `[Feature Request] Ingest Fireworks Tech Graph for Automated Architecture Diagram Generation` (Closed as completed)
- **Issue #192**: `[Feature Request] Cloudflare Durable Objects for State Persistence` (Closed as not planned)
- **Issue #194**: `[Feature Request] Cloudflare Queues Integration for Asynchronous Edge Event Buffering` (Closed as completed)
- **Issue #195**: `[Feature Request] Dedicated System Observability & Telemetry Dashboard Page` (Closed as completed)`

