# Midgley MCP & REST API Gateway Documentation

The **Midgley MCP & REST API Gateway** exposes real-time unleaded gasoline pump price ingestion, 5-day out-of-time quantitative forecasting, counterfactual physical/geopolitical shock simulations, and Model Context Protocol (MCP) integrations for AI agents, LLMs, and external financial applications.

---

## 🚀 Quick Start & Endpoint Overview

* **Production Static JSON API (Zero-Cost CDN)**: `https://koshiirra.github.io/midgley/api/v1/`
* **Primary Dev API Base URL**: `http://localhost:8000` (or configured API Gateway)
* **Local Dev VM Direct Port**: `http://10.42.42.54:8000`
* **OpenAPI 3.1 Spec**: `https://koshiirra.github.io/midgley/openapi.json`
* **GPT Action Manifest**: `https://koshiirra.github.io/midgley/.well-known/ai-plugin.json`
* **MCP SSE Connection**: `http://localhost:8000/mcp/sse`

---

## 🌐 Production Zero-Cost Static JSON API (GitHub Pages CDN)

For lightweight client applications (such as mobile apps, automotive head units, and static dashboards) that do not require live parameter evaluation or real-time shock simulations, Midgley automatically exports pre-rendered, CDN-cached JSON feeds directly onto GitHub Pages on every daily forecast batch execution (`src/static_api_exporter.py`).

### Static Feed Endpoints
| URL Pattern | Method | Description |
| :--- | :--- | :--- |
| `https://koshiirra.github.io/midgley/api/v1/combined.json` | `GET` | National combined live price, 5-day forecast, and top catalysts |
| `https://koshiirra.github.io/midgley/api/v1/combined_{locale}.json` | `GET` | Metro-specific combined feed (e.g., `combined_tulsa.json`, `combined_oakland.json`) |
| `https://koshiirra.github.io/midgley/api/v1/{locale}.json` | `GET` | Metro price and forecast payload alias |
| `https://koshiirra.github.io/midgley/api/v1/combined/{locale}.json` | `GET` | Sub-directory route alias for REST path compatibility |

### Available Locales for Static API
`national`, `tulsa`, `oakland`, `newark`, `cincinnati`, `greenville`, `charlotte`, `port_st_lucie`, `bayarea`

### Example Request
```bash
curl -s "https://koshiirra.github.io/midgley/api/v1/combined_tulsa.json"
```

### Static vs Dynamic Architecture
- **Static CDN Mode (GitHub Pages):** $0 infrastructure cost, 100% SLA global CDN delivery, zero server maintenance, ideal for end-user mobile/automotive apps (`midgley-auto`).
- **Dynamic Gateway Mode (`src/api_server.py`):** Real-time shock simulations (`/api/v1/forecast/simulate`), authenticated API key provisioning, webhooks, and Model Context Protocol (MCP) tool executions.

---

## 🔒 Security, Authentication & Key Management (Issue #40)

Midgley endpoints under `/api/v1/prices/*`, `/api/v1/forecast/*`, `/api/v1/combined*`, `/api/v1/diesel/*`, `/api/v1/connectors/headline-arena/submit`, and `/mcp/*` are secured with API Key authentication and per-key rate limiting (**default: 30 requests/minute**).

### Route Access Classification Matrix

| Route Category | Authentication Required | Header / Param | Description |
| :--- | :--- | :--- | :--- |
| **Public / Unauthenticated** | None | None | `/health`, `/`, `/api/v1/locales`, `/api/v1/system/*`, `/api/v1/telemetry/*`, `/api/v1/usgs/*`, `/api/v1/aqi/*`, `/api/v1/macro/*`, `/api/v1/graph/topology`, `/api/v1/graph/subgraph`, `/api/v1/memory/precedents`, `/metrics` |
| **API Key Authenticated** | API Key (`basic` or `privileged`) | `X-API-Key` or `Authorization: Bearer` | `/api/v1/prices/live`, `/api/v1/forecast/predict`, `/api/v1/forecast/batch`, `/api/v1/combined`, `/api/v1/combined/batch`, `/api/v1/forecast/scenarios`, `/api/v1/forecast/simulate`, `/api/v1/forecast/scoreboard`, `/api/v1/forecast/purged-cv`, `/api/v1/diesel/*`, `/api/v1/graph/ingest`, `/api/v1/connectors/headline-arena/submit`, `/mcp/*` |
| **Admin Secret Protected** | Admin Secret | `X-Admin-Secret` | `/api/v1/admin/keys` (POST, GET), `/api/v1/admin/keys/{prefix}` (DELETE), `/api/v1/forecast/cloud-sync` (POST) |
| **HMAC Webhook Signed** | HMAC-SHA256 Signature | `X-Midgley-Signature` | `/api/v1/events/webhook`, `/api/v1/events/queue-consumer`, `/api/v1/events/poll` |

### Authentication Headers
Callers can authenticate using any of the following methods:
* **Header**: `X-API-Key: mg_prod_a1b2c3d4_...`
* **Bearer Token Header**: `Authorization: Bearer mg_prod_a1b2c3d4_...`
* **Query Parameter** (for SSE/browser connections): `?api_key=mg_prod_a1b2c3d4_...`

### Key Access Tiers
* 👑 **`privileged` tier**: Full multi-agent LLM inference (Google Gemini 2.5 Flash event analysis, full Stacking Ensemble, and counterfactual shock simulations).
* 🛡️ **`basic` tier**: Automatically routes LLM event scoring to zero-cost fallback providers (Tier 3 Rule-Based Lexicon, SPC weather mapping, cached news vectors, standard linear Ridge baseline) to conserve Gemini tokens and Finlight API quotas.

### Key Provisioning Methods

#### Method A: Key Management CLI Utility (`scripts/manage_keys.py`)
Used by administrators directly on the host or `dev-vm` server:
```bash
# Provision a key for a user
python scripts/manage_keys.py create --user "alice" --tier privileged --env prod --rpm 30

# List active keys
python scripts/manage_keys.py list

# Revoke a key prefix
python scripts/manage_keys.py revoke --prefix mg_prod_a1b2c3d4
```

#### Method B: Admin REST API Gateway (`/api/v1/admin/keys`)
Secured by the `MIDGLEY_ADMIN_SECRET` environment variable (passed via `X-Admin-Secret` header). **Fail-Closed Security (Issue #341):** If `MIDGLEY_ADMIN_SECRET` is unset, empty, or whitespace-only on the server, all admin provisioning endpoints immediately fail closed with `HTTP 401 Unauthorized` (`Admin secret is not configured or invalid`). No default or fallback admin secret is permitted.

```bash
# Provision a new key programmatically
curl -X POST "http://localhost:8000/api/v1/admin/keys" \
  -H "X-Admin-Secret: $MIDGLEY_ADMIN_SECRET" \
  -H "Content-Type: application/json" \
  -d '{
    "user_id": "partner_app",
    "tier": "privileged",
    "environment": "prod",
    "rate_limit_rpm": 30
  }'

# List active keys
curl -X GET "http://localhost:8000/api/v1/admin/keys" \
  -H "X-Admin-Secret: $MIDGLEY_ADMIN_SECRET"

# Revoke a key by prefix
curl -X DELETE "http://localhost:8000/api/v1/admin/keys/mg_prod_a1b2c3d4" \
  -H "X-Admin-Secret: $MIDGLEY_ADMIN_SECRET"
```

---

## 📡 REST API Endpoints

### 1. `GET /api/v1/prices/live`
Fetches real-time unleaded gas price data using the multi-tiered fallback chain (GasBuddy GraphQL -> AAA Web Scraper -> EIA/yfinance Benchmark -> Prediction History -> Static Anchor) with 15-minute response caching.

**Query Parameters:**
* `locale` (optional, string): `national`, `tulsa`, `newark`, `cincinnati`, `greenville`, `charlotte`, `port_st_lucie`, `oakland`, `bayarea`. Default: `national`.
* `zip_code` (optional, string): 5-digit US zip code for station-level GasBuddy search.

**Example Request:**
```bash
curl -X GET "http://localhost:8000/api/v1/prices/live?locale=oakland" \
  -H "X-API-Key: $MIDGLEY_API_KEY"
```

---

### 2. `GET /api/v1/forecast/predict`
Generates 1-to-5 day out-of-time discrete quantitative price predictions, expected dollar delta, projected direction (UP/DOWN/FLAT), component-level feature attributions (XAI), and natural language driver summary text.

**Query Parameters:**
* `locale` (optional, string): Target locale code (`national`, `tulsa`, `newark`, `cincinnati`, `greenville`, `charlotte`, `port_st_lucie`, `oakland`, `bayarea`).
* `days` (optional, integer): Forecast horizon in days (1 to 30). Default: `5`.

**Example Request:**
```bash
curl -X GET "http://localhost:8000/api/v1/forecast/predict?locale=tulsa&days=5" \
  -H "X-API-Key: $MIDGLEY_API_KEY"
```

---

### 3. `POST /api/v1/forecast/batch` (Issue #377)
Generates 5-day out-of-time forecasts across multiple regional locales in a single batched HTTP request.

**Example Request:**
```bash
curl -X POST "http://localhost:8000/api/v1/forecast/batch" \
  -H "X-API-Key: $MIDGLEY_API_KEY" \
  -H "Content-Type: application/json" \
  -d '{
    "locales": ["national", "tulsa", "newark", "oakland"],
    "days": 5
  }'
```

---

### 4. `GET /api/v1/combined`
Unified endpoint returning live current pump price, predicted 5-day target forecast, regional rack margin, and key market drivers.

**Example Request:**
```bash
curl -X GET "http://localhost:8000/api/v1/combined?locale=cincinnati" \
  -H "X-API-Key: $MIDGLEY_API_KEY"
```

---

### 5. `POST /api/v1/combined/batch` (Issue #377)
Batch unified endpoint returning live current pump prices, 5-day forecasts, and top drivers for multiple locales concurrently.

**Example Request:**
```bash
curl -X POST "http://localhost:8000/api/v1/combined/batch" \
  -H "X-API-Key: $MIDGLEY_API_KEY" \
  -H "Content-Type: application/json" \
  -d '{
    "locales": ["national", "tulsa", "cincinnati", "port_st_lucie"]
  }'
```

---

### 6. `GET /api/v1/forecast/scoreboard`
Returns continuous out-of-time MLOps model accuracy metrics (MAE, RMSE, MAPE, Directional Hit Rate %, Naive Persistence MAE, and Model MAE Uplift %) evaluated against actual ground-truth market prices.

**Query Parameters:**
* `locale` (optional, string): Filter by locale (`national`, `tulsa`, `newark`, `cincinnati`, `greenville`, `charlotte`, `oakland`, `bayarea`, `all`). Default: `all`.
* `window` (optional, string): Rolling evaluation window in days (`30`, `60`, `90`, `all`). Default: `30`.
* `horizon` (optional, string): Filter by forecast target horizon in days (`1`, `2`, `3`, `4`, `5`, `all`). Default: `all`.
* `include_retroactive` (optional, boolean): Restrict strictly to forward out-of-time predictions (`false`). Default: `false`.

**Example Request:**
```bash
curl -X GET "http://localhost:8000/api/v1/forecast/scoreboard?locale=tulsa&window=30&horizon=5&include_retroactive=false" \
  -H "X-API-Key: $MIDGLEY_API_KEY"
```

---

### 7. `GET /api/v1/forecast/purged-cv`
Returns out-of-sample purged and combinatorial cross-validation metrics for Ridge, Stacking Ensemble, and Baseline models with enforced embargo gaps to ensure temporal leakage prevention.

**Example Request:**
```bash
curl -X GET "http://localhost:8000/api/v1/forecast/purged-cv" \
  -H "X-API-Key: $MIDGLEY_API_KEY"
```

---

### 8. `GET /api/v1/forecast/scenarios` & `POST /api/v1/forecast/simulate`
Discovers and executes counterfactual market shocks with seasonal plausibility gating and MiroFish multi-agent cohort simulation (`Agent_Refiner`, `Agent_Logistics`, `Agent_Consumer`, `Agent_Macro`).

**Example Request:**
```bash
curl -X POST "http://localhost:8000/api/v1/forecast/simulate" \
  -H "X-API-Key: $MIDGLEY_API_KEY" \
  -H "Content-Type: application/json" \
  -d '{
    "scenario_id": "port_st_lucie_hurricane",
    "locale": "port_st_lucie",
    "target_date": "2026-09-25",
    "enable_cohort_simulation": true
  }'
```

---

### 9. Distillate & Ultra-Low Sulfur Diesel (ULSD) Endpoints (Issue #41)

* `GET /api/v1/diesel/live`: Fetches real-time retail diesel prices across metro hubs and prompt heating oil crack futures (`HO=F`).
* `GET /api/v1/diesel/forecast`: Generates 5-day out-of-time ULSD wholesale and retail price forecasts.
* `GET /api/v1/diesel/simulate`: Simulates counterfactual distillate market shocks (Colonial Line 2 outage, Polar Vortex, Midwest planting rush).

**Example Request:**
```bash
curl -X GET "http://localhost:8000/api/v1/diesel/live" \
  -H "X-API-Key: $MIDGLEY_API_KEY"
```

---

### 10. Knowledge Graph Endpoints (Issue #230)

* `GET /api/v1/graph/topology`: Returns full knowledge graph topology (nodes, edges, node degrees) mapping refineries, pipelines, delivery hubs, and regulatory bodies.
* `GET /api/v1/graph/subgraph?entity={entity_name}&depth={depth}`: Traverses localized subgraph neighborhood around a specific entity.
* `POST /api/v1/graph/ingest`: Ingests a new event shock or observation into the persistent graph structure.

**Example Request:**
```bash
curl -X GET "http://localhost:8000/api/v1/graph/subgraph?entity=Colonial_Pipeline&depth=2"
```

---

### 11. Headline Arena Benchmarking Connectors (Issue #182 & #408)

* `GET /api/v1/connectors/headline-arena/status`: Returns current pending forecast cache status, submitted challenge ledger, and settlement rules.
* `POST /api/v1/connectors/headline-arena/submit`: Triggers forecast dispatching to Headline Arena civic / macro challenges.

**Example Request:**
```bash
curl -X GET "http://localhost:8000/api/v1/connectors/headline-arena/status"
```

---

### 12. Physical & Macro Data Feed Endpoints

* `GET /api/v1/macro/freight-tsi`: Returns U.S. Bureau of Transportation Statistics (BTS) Freight Transportation Services Index (TSI) and truck tonnage demand momentum.
* `GET /api/v1/macro/traffic-volume`: Returns Federal Highway Administration (FHWA) Monthly Traffic Volume Trends (TVT) and Vehicle Miles Traveled (VMT).
* `GET /api/v1/usgs/water_levels?cluster={cluster}`: Real-time river gage height, streamflow, and water temperature across 6 marine clusters.
* `GET /api/v1/usgs/seismic?corridor={corridor}`: Real-time USGS earthquake telemetry evaluated near refining assets.
* `GET /api/v1/aqi/live`: Fence-line air quality metrics (PurpleAir, OpenAQ, AirNow) for refinery flaring detection.
* `GET /api/v1/aqi/ozone-alerts`: EPA AirNow regional ground-level ozone action days and summer RVP compliance surcharges.

---

### 13. System Observability & Prometheus Metrics

* `GET /metrics` and `GET /api/v1/metrics`: Exports Prometheus-compatible plaintext metrics for scrape collectors (Grafana, Datadog).
* `GET /api/v1/system/quota`: Real-time safety valve quota accounting (Firecrawl 800/mo cap, Finlight 150/mo cap, IPASIS 100/day cap).
* `GET /api/v1/system/telemetry`: 7-day health audit across zero-cost open data connectors.
* `GET /api/v1/system/token-costs`: TokenTab cumulative LLM token consumption and USD costs.
* `GET /api/v1/system/cache-status`: 3-tier cache gateway health and edge probe latencies.

**Example Request:**
```bash
curl -s "http://localhost:8000/metrics"
```

---

## ⚡ Strategy 4 Incoming Webhook Gateway (`POST /api/v1/events/webhook`)

* **Endpoint:** `POST /api/v1/events/webhook`
* **Content-Type:** `application/json`
* **Security Header:** `X-Midgley-Signature: sha256=<hmac_hex>` (HMAC-SHA256 signature; **mandatory in production** under fail-closed security when `MIDGLEY_ENV=prod`).
* **Authentication Behavior:**
  - **Production (`MIDGLEY_ENV=prod`):** Fails closed with `401 Unauthorized` if `MIDGLEY_WEBHOOK_SECRET` is unset or signature is missing/invalid.
  - **Development (`MIDGLEY_ENV=dev` / `TESTING=1`):** Permits unauthenticated pushes when `MIDGLEY_WEBHOOK_SECRET` is unset for local testing convenience.

For provider integration recipes (Google Alerts, Zapier, IFTTT, TradingView), security matrix, and copy-pasteable HMAC signature snippets, see **[WEBHOOK_FORMATTING_GUIDE.md](docs/WEBHOOK_FORMATTING_GUIDE.md)**.

---

## 📦 Cloudflare Queue Batch Consumer Endpoint (`POST /api/v1/events/queue-consumer`)

* **Endpoint:** `POST /api/v1/events/queue-consumer`
* **Content-Type:** `application/json`
* **Security Header:** `X-Midgley-Signature: sha256=<hmac_hex>` (HMAC-SHA256 signature when `MIDGLEY_WEBHOOK_SECRET` is configured).
* **Description:** Asynchronously receives batch queued event payloads pushed by Cloudflare Queue consumers or local queue workers.

---

## 🤖 Model Context Protocol (MCP) Server Integration

The Midgley MCP Server exposes tools, resources, and prompt templates for integration with Claude Desktop, Antigravity CLI (`agy`), and OpenAI Custom GPTs.

### Transport Modes
1. **Stdio Mode**:
   `python -m src.mcp_server`
2. **HTTP/SSE Transport**:
   `http://localhost:8000/mcp/sse`

---

## ⚙️ Service Orchestration (Dev VM)

Managed by systemd user service `midgley-api.service`:
```bash
systemctl --user status midgley-api.service
systemctl --user restart midgley-api.service
```

---

## 🚗 Mobile & In-Dash Client Ecosystem (`midgley-auto`)

The Midgley REST API Gateway powers the dedicated **[Android Auto & Automotive Fuel Assistant (`midgley-auto`)](https://github.com/KoshiirRa/midgley-auto)**.

For complete client schemas, SDK configuration, and AndroidX Car App integration guidelines, see **[API_CONTRACT.md](https://github.com/KoshiirRa/midgley-auto/blob/main/docs/API_CONTRACT.md)** in `midgley-auto`.
