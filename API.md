# Midgley MCP & REST API Gateway Documentation

The **Midgley MCP & REST API Gateway** exposes real-time unleaded gasoline pump price ingestion, 5-day out-of-time quantitative forecasting, counterfactual physical/geopolitical shock simulations, and Model Context Protocol (MCP) integrations for AI agents, LLMs, and external financial applications.

---

## 🚀 Quick Start & Endpoint Overview

* **Primary Dev API Base URL**: `http://localhost:8000` (or configured API Gateway)
* **Local Dev VM Direct Port**: `http://localhost:8000`
* **OpenAPI 3.1 Spec**: `https://koshiirra.github.io/midgley/openapi.json`
* **GPT Action Manifest**: `https://koshiirra.github.io/midgley/.well-known/ai-plugin.json`
* **MCP SSE Connection**: `http://localhost:8000/mcp/sse`

---

## 🔒 Security, Authentication & Key Management (Issue #40)

Midgley endpoints under `/api/v1/prices/*`, `/api/v1/forecast/*`, and `/mcp/*` are secured with API Key authentication and per-key rate limiting (**default: 30 requests/minute**).

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
Secured by the `MIDGLEY_ADMIN_SECRET` environment variable (passed via `X-Admin-Secret` header):
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
* `locale` (optional, string): `national`, `tulsa`, `newark`, `cincinnati`, `greenville`, `oakland`, `bayarea`. Default: `national`.
* `zip_code` (optional, string): 5-digit US zip code for station-level GasBuddy search.

**Example Request:**
```bash
curl -X GET "http://localhost:8000/api/v1/prices/live?locale=oakland"
```

**Example Response:**
```json
{
  "status": "success",
  "timestamp": "2026-08-24T19:18:24Z",
  "locale": {
    "code": "oakland",
    "region_id": "Oakland_CA",
    "name": "Oakland & SF Bay Area, CA",
    "padd_region": "PADD 5 West Coast"
  },
  "price_per_gal": 4.950,
  "source": "AAA Web Scraper (CA)",
  "cache_hit": true,
  "cache_age_seconds": 35.8,
  "carb_tax_regulatory_burden_per_gal": 0.953
}
```

---

### 2. `GET /api/v1/forecast/predict`
Generates 5-day out-of-time quantitative price predictions, expected dollar delta, projected direction (UP/DOWN/FLAT), component-level feature attributions (XAI), and natural language driver summary text.

**Query Parameters:**
* `locale` (optional, string): Target locale code (`national`, `tulsa`, `newark`, `cincinnati`, `greenville`, `charlotte`, `port_st_lucie`, `oakland`, `bayarea`).
* `days` (optional, integer): Forecast horizon in days (1 to 30). Default: `5`.

**Example Request:**
```bash
curl -X GET "http://localhost:8000/api/v1/forecast/predict?locale=tulsa&days=5"
```

**Example Response:**
```json
{
  "status": "success",
  "timestamp": "2026-09-02T19:10:00Z",
  "locale": {
    "code": "tulsa",
    "region_id": "Tulsa_OK",
    "name": "Tulsa, OK Metro Area"
  },
  "forecast": {
    "model_version": "v1.4 Finlight-LLM",
    "forecast_horizon_days": 5,
    "target_date": "2026-09-07",
    "current_base_price": 3.89,
    "predicted_price_per_gal": 3.935,
    "expected_change_dollars": 0.045,
    "expected_change_percent": 1.16,
    "projected_direction": "UP",
    "feature_attributions": {
      "futures_commodity": { "delta_dollars": 0.009, "share_pct": 20.0 },
      "refining_crack_margin": { "delta_dollars": 0.0135, "share_pct": 30.0 },
      "weather_environmental": { "delta_dollars": 0.0023, "share_pct": 5.0 },
      "tax_regulatory": { "delta_dollars": 0.0022, "share_pct": 5.0 },
      "unstructured_sentiment": { "delta_dollars": 0.0045, "share_pct": 10.0 },
      "regional_logistics": { "delta_dollars": 0.0135, "share_pct": 30.0 }
    },
    "driver_breakdown": {
      "summary_text": "Tulsa OK forecast +$0.045/gal driven primarily by refining crack margin, regional logistics.",
      "key_drivers": [
        "Refining Yield & Crack Spread: +$0.0135/gal (30.0% share)",
        "Regional Logistics & Hub Delivery: +$0.0135/gal (30.0% share)"
      ]
    }
  }
}
```

---

## 🍃 Zero-Cost Fallback & Basic Tier Telemetry Endpoint (`GET /api/v1/telemetry/fallback-status` - Issue #196)

* **Endpoint:** `GET /api/v1/telemetry/fallback-status`
* **Description:** Returns aggregated telemetry statistics for zero-cost fallback provider invocations (`ZeroCostProviderHook`), basic tier API key request routing counts, provider distribution (`lexicon`, `kaggle_llm_hook`, `spc_weather`), and estimated LLM token/dollar cost savings.

* **Example Response:**
```json
{
  "total_zero_cost_invocations": 12,
  "basic_tier_routed_count": 5,
  "provider_breakdown": {
    "lexicon": 12,
    "kaggle_llm_hook": 0,
    "spc_weather": 0
  },
  "tokens_saved": 4200,
  "estimated_usd_saved": 0.00126,
  "avg_zero_cost_latency_ms": 1.45,
  "last_updated": "2026-09-04T01:10:00Z"
}
```

---

## 📊 System Observability, Telemetry & Memory Endpoints

### `GET /api/v1/system/telemetry` (Issue #237)
Returns aggregated 7-day health audit metrics across zero-cost open data connectors (EIA, FRED, USDA, NOAA, AAA, Socrata, USGS) including request volumes, error counts, failure rate %, latency, and cache freshness.

### `GET /api/v1/telemetry/unmapped-zips` (Issues #50 & #195)
Returns aggregated telemetry for out-of-metro ZIP code lookups, including top unmapped ZIPs, state and PADD distributions, total query counts, and candidate expansion metro hubs.

### `GET /api/v1/memory/precedents` (Issues #230 & #237)
Queries the Vectorize Hindsight episodic agent memory engine for historical shock precedents, matching query keywords and tags against stored resolved prediction experiences and reflections.

**Query Parameters:**
* `q` (required, string): Query string (e.g. `refinery fire`, `hurricane flood`, `tariffs`).
* `locale` (optional, string): Filter by locale (`tulsa`, `newark`, `oakland`, etc.).
* `limit` (optional, integer): Max results to return. Default: `5`.

### `GET /api/v1/system/quota` (Issues #83, #87, #237)
Returns real-time usage metrics and hard quota safety valve limits for Firecrawl (800/mo cap, 30/day burst limit), Finlight (150/mo cap, 10/day burst limit), IPASIS Security Verifier (100 req/day cap), and NOAA Weather endpoints.

### `GET /api/v1/system/token-costs` (Issue #107)
Returns TokenTab cumulative token consumption (input/output tokens), cache read/write tokens, and estimated USD expenditure across LLM providers.

### `GET /api/v1/security/ip-status` (Issue #87)
Returns IPASIS security telemetry including inspected request counts, blocked high-risk IP origins, and cache hit ratios.

---

### 3. `GET /api/v1/forecast/scoreboard`
Returns continuous out-of-time MLOps model accuracy metrics (MAE, RMSE, MAPE, Directional Hit Rate %, Naive Persistence MAE, and Model MAE Uplift %) evaluated against actual ground-truth market prices over a rolling evaluation window (30, 60, 90, or all days) and discrete forecast horizons (1d through 5d) (Issue #209).

**Query Parameters:**
* `locale` (optional, string): Filter by locale (`national`, `tulsa`, `newark`, `cincinnati`, `greenville`, `charlotte`, `oakland`, `bayarea`, `all`). Default: `all`.
* `window` (optional, string): Rolling evaluation window in days (`30`, `60`, `90`, `all`). Default: `30`.
* `horizon` (optional, string): Filter by forecast target horizon in days (`1`, `2`, `3`, `4`, `5`, `all`). Default: `all`.

**Example Request:**
```bash
curl -X GET "http://localhost:8000/api/v1/forecast/scoreboard?locale=tulsa&window=30&horizon=5"
```

**Example Response:**
```json
{
  "status": "success",
  "system": "Midgley v1.4 Finlight-LLM",
  "timestamp": "2026-09-07T11:00:00Z",
  "filters": {
    "locale": "tulsa",
    "region_code": "Tulsa_OK",
    "window_days": "30",
    "horizon": "5"
  },
  "summary": {
    "window_days": "30",
    "region_filter": "Tulsa_OK",
    "horizon_filter": 5,
    "total_evaluations": 30,
    "mae_dollars": 0.1331,
    "rmse_dollars": 0.1620,
    "mape_pct": 3.42,
    "directional_hit_rate_pct": 58.15,
    "naive_persistence_mae": 0.1740,
    "model_uplift_mae_pct": 23.51
  },
  "horizon_breakdown": [
    {
      "horizon_days": 1,
      "horizon_label": "1-Day (24h Ahead)",
      "evaluations": 30,
      "mae_dollars": 0.0412,
      "rmse_dollars": 0.0583,
      "mape_pct": 1.28,
      "directional_hit_rate_pct": 68.33,
      "naive_persistence_mae": 0.0520,
      "model_uplift_mae_pct": 20.77
    },
    {
      "horizon_days": 2,
      "horizon_label": "2-Day (48h Ahead)",
      "evaluations": 30,
      "mae_dollars": 0.0685,
      "rmse_dollars": 0.0892,
      "mape_pct": 1.84,
      "directional_hit_rate_pct": 64.50,
      "naive_persistence_mae": 0.0841,
      "model_uplift_mae_pct": 18.55
    },
    {
      "horizon_days": 3,
      "horizon_label": "3-Day (72h Ahead)",
      "evaluations": 30,
      "mae_dollars": 0.0910,
      "rmse_dollars": 0.1145,
      "mape_pct": 2.45,
      "directional_hit_rate_pct": 61.20,
      "naive_persistence_mae": 0.1180,
      "model_uplift_mae_pct": 22.88
    },
    {
      "horizon_days": 4,
      "horizon_label": "4-Day (96h Ahead)",
      "evaluations": 30,
      "mae_dollars": 0.1140,
      "rmse_dollars": 0.1410,
      "mape_pct": 2.98,
      "directional_hit_rate_pct": 59.80,
      "naive_persistence_mae": 0.1460,
      "model_uplift_mae_pct": 21.92
    },
    {
      "horizon_days": 5,
      "horizon_label": "5-Day (1-Week Ahead)",
      "evaluations": 30,
      "mae_dollars": 0.1331,
      "rmse_dollars": 0.1620,
      "mape_pct": 3.42,
      "directional_hit_rate_pct": 58.15,
      "naive_persistence_mae": 0.1740,
      "model_uplift_mae_pct": 23.51
    }
  ],
  "regional_breakdown": [
    {
      "region": "Tulsa_OK",
      "evaluations": 30,
      "mae_dollars": 0.1331,
      "rmse_dollars": 0.1620,
      "mape_pct": 3.42,
      "directional_hit_rate_pct": 58.15,
      "naive_persistence_mae": 0.1740,
      "model_uplift_mae_pct": 23.51
    }
  ],
  "recent_evaluations": [
    {
      "log_timestamp": "2026-09-02 08:00:00",
      "forecast_target_date": "2026-08-25",
      "forecast_horizon_days": 5,
      "region": "Tulsa_OK",
      "current_base_price": 3.89,
      "predicted_5d_price": 3.935,
      "actual_5d_price": 3.93,
      "error_dollars": 0.005,
      "directional_hit": 1
    }
  ]
}
```

---

### 4. `GET /api/v1/combined`
Unified endpoint returning live current pump price, predicted 5-day target forecast, regional rack margin, and key market drivers.

**Example Request:**
```bash
curl -X GET "http://localhost:8000/api/v1/combined?locale=cincinnati"
```

---

### 5. `GET /api/v1/usgs/water_levels`
Returns real-time streamflow (`00060`), gage height (`00065`), water temperature (`00010`), and specific conductance (`00095`) telemetry across USGS monitoring stations in 6 hydrological clusters (Inland Barge Corridor, Gulf Coast Refining Origin, Bay Area Carquinez Strait, Delaware River/Bay, Tulsa MKARNS, and South Florida Coastal Drainage) (Issue #56).

**Query Parameters:**
* `cluster` (optional): Filter by regional cluster (`inland_barge`, `gulf_coast`, `bay_area`, `delaware`, `tulsa`, `florida`).

**Example Request:**
```bash
curl -X GET "http://localhost:8000/api/v1/usgs/water_levels?cluster=inland_barge"
```

---

### 6. `GET /api/v1/usgs/seismic`
Returns real-time and historical earthquake telemetry from the USGS Earthquake Web Service API (`earthquake.usgs.gov/fdsnws/event/1/`) evaluated against critical refining, pipeline, and storage infrastructure (Issue #55).

**Query Parameters:**
* `corridor` (optional, default: `bay_area`): Filter by regional refining and delivery corridor (`bay_area`, `cushing_ok`, `socal`, `mid_atlantic`, `new_madrid`, or `all`).
* `days` (optional, default: `30`): Rolling temporal observation window in days.
* `min_mag` (optional): Minimum earthquake magnitude filter (defaults to corridor-specific threshold: $4.0$ in California, $3.8$ in Oklahoma/Mid-Atlantic).

**Example Request:**
```bash
curl -X GET "http://localhost:8000/api/v1/usgs/seismic?corridor=bay_area"
```

**Example Response:**
```json
{
  "status": "SUCCESS",
  "source": "USGS Earthquake Hazards Program (earthquake.usgs.gov)",
  "timestamp": "2026-09-06 00:00:00",
  "filtered_corridor": "bay_area",
  "temporal_window_days": 30,
  "events": [],
  "corridors": {
    "bay_area": {
      "corridor_risk_index": 0.0,
      "max_magnitude": 0.0,
      "active_events_count": 0,
      "highest_impact_event": null
    }
  },
  "indices": {
    "bay_area_seismic_risk_index": 0.0,
    "cushing_storage_seismic_risk_index": 0.0,
    "socal_refining_seismic_risk_index": 0.0,
    "mid_atlantic_seismic_risk_index": 0.0,
    "new_madrid_seismic_risk_index": 0.0,
    "composite_seismic_risk_index": 0.0,
    "is_pipeline_emergency_shutdown_risk": false,
    "is_refinery_inspection_advisory": false,
    "max_magnitude": 0.0,
    "total_significant_quakes": 0
  }
}
```

---

### 7. `POST /api/v1/forecast/simulate`
Simulates counterfactual physical refinery outages, weather disasters, or geopolitical chokepoint shocks.

**Request Body:**
```json
{
  "scenario_id": "hormuz_blockade",
  "locale": "oakland",
  "custom_shock_pct": 0.05
}
```

**Example Request:**
```bash
curl -X POST "http://localhost:8000/api/v1/forecast/simulate" \
     -H "Content-Type: application/json" \
     -d '{"scenario_id": "hormuz_blockade", "locale": "oakland"}'
```

**Supported Scenarios:**
* `hormuz_blockade`: Strait of Hormuz Tanker Blockade (21M bpd) (+2.88%)
* `suez_rerouting`: Red Sea / Suez Canal Rerouting Crisis (+5.32%)
* `tulsa_tornado`: West Tulsa HF Sinclair Refinery EF-3 Tornado (+4.58%)
* `cushing_spill`: Cushing Keystone Pipeline Rupture & Lock (+4.58%)
* `marathon_outage`: Marathon Catlettsburg KY Refinery Outage (+4.78%)
* `mississippi_low_water`: Lower Mississippi & Ohio River Low-Water Bottleneck (+4.20%)
* `houston_ship_channel_closure`: Houston Ship Channel Torrential Runoff & Marine Closure (+5.12%)
* `carquinez_atmospheric_river`: Carquinez Strait Atmospheric River Runoff & Tanker Berthing Halt (+4.35%)
* `summer_refinery_thermal_cutback`: Delaware & Ohio River Summer Refinery Cooling Water Thermal Curtailment (+3.85%)
* `colonial_outage`: Colonial Pipeline Mainline Outage / Cyberattack Shock (+7.54%)
* `greenville_hurricane`: Category 3 Atlantic Hurricane Landfall & Tar River Flooding (+6.62%)
* `selma_outage`: Selma NC Distribution Hub Tank Farm Outage & Blackout (+5.69%)
* `hayward_quake`: USGS Hayward Fault M>=6.0 Seismic Quake (+8.48%)
* `pge_psps_shutoff`: PG&E PSPS Wildfire Power Shutoff & Blackout (+7.07%)
* `chevron_hydrocracker`: Chevron Richmond Refinery Hydrocracker Outage (+5.76%)
* `weekend_opec_post`: Weekend Executive OPEC Talkdown Post (-1.85%)
* `weekend_tariff_declaration`: Weekend Foreign Energy Tariff Declaration (+2.10%)

---

## ⚡ Strategy 4 Incoming Webhook Gateway (`POST /api/v1/events/webhook`)

* **Endpoint:** `POST /api/v1/events/webhook`
* **Content-Type:** `application/json`
* **Security Header:** `X-Midgley-Signature: sha256=<hmac_hex>` (HMAC-SHA256 signature when `MIDGLEY_WEBHOOK_SECRET` is set).
* **Payload Transformer Aliases:**
  - `headline` $\leftarrow$ `headline`, `title`, `text`, `summary`, `tweet_content`, `article_title`, `content`
  - `url` $\leftarrow$ `url`, `link`, `article_url`, `web_url`, `href`
  - `source` $\leftarrow$ `source`, `origin`, `provider`, `channel`, `service`

* **IPASIS Security Filter (Issue #87):** Inspects client IP (`CF-Connecting-IP`, `X-Forwarded-For`), rejecting high-risk Tor/Abuse origins with HTTP 403 Forbidden.
* **Security Telemetry Endpoint:** `GET /api/v1/security/ip-status` — Returns IPASIS IP security gateway status, daily API request accounting (used / 100 allowance), private IP bypass statistics, and blocked origin counts.

For provider integration recipes (Google Alerts, Zapier, IFTTT, TradingView) and HMAC signature examples, see **[WEBHOOK_FORMATTING_GUIDE.md](file:///c:/Users/concentus/Documents/Random%20Ideas%20-%20LLM%20Unleaded%20Gas%20Price%20Prediction%20Modelling/docs/WEBHOOK_FORMATTING_GUIDE.md)**.

---

## 📦 Cloudflare Queue Batch Consumer Endpoint (`POST /api/v1/events/queue-consumer` - Issue #194)

* **Endpoint:** `POST /api/v1/events/queue-consumer`
* **Content-Type:** `application/json`
* **Security Header:** `X-Midgley-Signature: sha256=<hmac_hex>` (HMAC-SHA256 signature when `MIDGLEY_WEBHOOK_SECRET` is set).
* **Description:** Asynchronously receives batch queued event payloads pushed by Cloudflare Queue consumers or local queue workers. Processes queued event items in batch, executing deduplication against edge cache, fast-path anomaly scoring, and regional metro forecast updates.

* **Example Payload:**
```json
{
  "queue_name": "intraday-event-queue",
  "batch_id": "batch_884920",
  "events": [
    {
      "headline": "OPEC Emergency Cut Announced",
      "url": "https://news.example.com/opec1",
      "source": "Cloudflare_Queue_Consumer"
    },
    {
      "headline": "Refinery Outage Reported in PADD 1B",
      "url": "https://news.example.com/refinery2",
      "source": "Cloudflare_Queue_Consumer"
    }
  ]
}
```

---

## 🤖 Model Context Protocol (MCP) Server Integration

The Midgley MCP Server exposes tools, resources, and prompt templates for integration with Claude Desktop, Antigravity CLI (`agy`), and OpenAI Custom GPTs.

### Transport Modes
1. **Stdio Mode**:
   Execute directly in CLI / agent environments:
   ```bash
   python -m src.mcp_server
   ```

2. **HTTP/SSE Transport**:
   Connect via Server-Sent Events (SSE):
   `http://localhost:8000/mcp/sse`

### Exposed MCP Tools
- `get_live_gas_prices(locale, zip_code)`
- `get_gas_price_prediction(locale, days)`
- `get_live_and_forecast(locale)`
- `simulate_fuel_market_shock(locale, scenario_id)`

### Exposed MCP Resources
- `resource://midgley/locales/national`
- `resource://midgley/locales/tulsa`
- `resource://midgley/locales/newark`
- `resource://midgley/locales/cincinnati`
- `resource://midgley/locales/greenville`
- `resource://midgley/locales/oakland`

### Exposed MCP Prompts
- `prompt://midgley/market_summary` (LLM financial briefing prompt template)

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

### Mobile Client Endpoints:
- `GET /api/v1/locations/resolve?lat={lat}&lon={lon}` — Resolves vehicle GPS coordinates to refining hub MSA.
- `GET /api/v1/forecasts/{location_id}` — Returns 5-day out-of-time price trajectory & quantile bands ($P_{10}$, $P_{50}$, $P_{90}$).
- `GET /api/v1/savings?location_id={location_id}&tank_capacity={gallons}` — Returns optimal fill-up recommendation signal (`🟢 WAIT TO FILL UP`, `🔴 FILL UP NOW`), optimal fill day, and net tank savings.
- `GET /api/v1/events/active?location_id={location_id}` — Returns active severe weather alerts (NOAA tornado/polar vortex) & refinery outage warnings.

For complete client schemas, SDK configuration, and AndroidX Car App integration guidelines, see **[API_CONTRACT.md](https://github.com/KoshiirRa/midgley-auto/blob/main/docs/API_CONTRACT.md)** in `midgley-auto`.

