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
Generates 5-day out-of-time quantitative price predictions, expected dollar delta, projected direction (UP/DOWN/FLAT), and historical hit rate.

**Query Parameters:**
* `locale` (optional, string): Target locale code (`national`, `tulsa`, `newark`, `cincinnati`, `oakland`).
* `days` (optional, integer): Forecast horizon in days (1 to 30). Default: `5`.

**Example Request:**
```bash
curl -X GET "http://localhost:8000/api/v1/forecast/predict?locale=tulsa&days=5"
```

---

### 3. `GET /api/v1/combined`
Unified endpoint returning live current pump price, predicted 5-day target forecast, regional rack margin, and key market drivers.

**Example Request:**
```bash
curl -X GET "http://localhost:8000/api/v1/combined?locale=cincinnati"
```

---

### 4. `POST /api/v1/forecast/simulate`
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
* `colonial_outage`: Colonial Pipeline Mainline Outage / Cyberattack Shock (+7.54%)
* `greenville_hurricane`: Category 3 Atlantic Hurricane Landfall & Tar River Flooding (+6.62%)
* `selma_outage`: Selma NC Distribution Hub Tank Farm Outage & Blackout (+5.69%)
* `hayward_quake`: USGS Hayward Fault M>=6.0 Seismic Quake (+8.48%)
* `pge_psps_shutoff`: PG&E PSPS Wildfire Power Shutoff & Blackout (+7.07%)
* `chevron_hydrocracker`: Chevron Richmond Refinery Hydrocracker Outage (+5.76%)
* `carb_transition`: CARB CaRFG Summer-Blend Transition Compliance Surge (+4.44%)
* `weekend_opec_post`: Weekend Executive OPEC Talkdown Post (-1.85%)
* `weekend_tariff_declaration`: Weekend Foreign Energy Tariff Declaration (+2.10%)

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

