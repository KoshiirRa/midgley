## Feature Request: Model Context Protocol (MCP) Server & REST API Endpoint for External LLM & Chatbot Integration

### 📌 Summary

Expose a standardized **Model Context Protocol (MCP) Server** and lightweight **RESTful API Endpoint** for Midgley, enabling external LLMs, AI agents, and chatbots (such as OpenAI ChatGPT Actions, Claude Desktop, Antigravity CLI, Cursor, LangChain, and OpenWebUI) to programmatically query:
1. **Live Ground-Truth Gas Price Data**: Real-time retail pump price lookups via automated AAA and GasBuddy live scrapers/APIs with EIA baseline fallbacks.
2. **Quantitative 5-Day Price Predictions**: Multi-agent quantitative model inference (base commodity futures forecast + regularized Ridge / Gemini 2.5 Flash news decay fusion + localized regional metro calibrations).
3. **Counterfactual Shock Simulations**: Real-time evaluation of physical/geopolitical market shocks (e.g. Strait of Hormuz tanker blockade, Cushing pipeline spill, Chevron Richmond hydrocracker outage, Lower Mississippi river low-water drought).

---

### 💡 Motivations & Use Cases

- **Agentic Interoperability**: AI assistants and financial chatbots currently lack a clean, structured MCP interface to fetch real-time energy commodity prices and predictive analytics without executing full model code or scraping websites themselves.
- **Unified Live + Predictive Payload**: External LLMs often require both current baseline context (*"What is gas in Oakland today?"*) and forward-looking guidance (*"Will prices rise over the next 5 days?"*). Midgley can deliver both in a single, low-latency JSON response.
- **Dual Transport Protocols**:
  - **Standard I/O (`stdio`)**: Enables local agent CLI frameworks (Antigravity, Cursor, Claude Desktop, Aider) to connect to Midgley as an external tool provider.
  - **Server-Sent Events (HTTP/SSE) & REST**: Enables cloud-hosted AI agents, ChatGPT Actions, and web dashboards to query Midgley via HTTPS.

---

### 📐 Technical Architecture & Specification

```
                          ┌────────────────────────────────────────────────────────┐
                          │    EXTERNAL AI AGENTS / CHATBOTS / LLM CALLERS         │
                          │  • Claude Desktop / Antigravity / Cursor (stdio)       │
                          │  • ChatGPT Actions / Custom Web Agents (HTTP/SSE/REST) │
                          └───────────────────────────┬────────────────────────────┘
                                                      │
                                                      ▼
                          ┌────────────────────────────────────────────────────────┐
                          │      MIDGLEY MCP & REST API GATEWAY (Port 8000)        │
                          │  • MCP Gateway: src/mcp_server.py (FastMCP / SSE)      │
                          │  • REST API:     src/api_server.py (FastAPI)           │
                          │  • Security:     Rate Limiting (60 req/m) & Auth Keys │
                          └─────────────┬────────────────────────────┬─────────────┘
                                        │                            │
             ┌──────────────────────────┴────────┐          ┌────────┴──────────────────────────┐
             │                                   │          │                                   │
             ▼                                   │          ▼                                   ▼
┌──────────────────────────┐                     │   ┌──────────────────────────┐   ┌──────────────────────────┐
│ LIVE LOOKUP & CACHE      │                     │   │ QUANTITATIVE FORECASTING │   │ SHOCK SIMULATION ENGINE  │
│ (src/live_fuel_feed.py)  │                     │   │ (src/models.py & *_main) │   │ (main.py scenario list)  │
│ • GasBuddy GraphQL API   │                     │   │ • 5-Day Out-of-Time Pred │   │ • Hormuz Tanker Blockade │
│ • AAA Fuel Gauge Scraper │                     │   │ • Directional Hit Rate   │   │ • Regional Outages & Ice │
│ • EIA API v2 Fallback    │                     │   │ • Key Driver Attribution │   │ • Executive Social Shocks│
│ • SQLite Cache (15m TTL) │                     │   └──────────────────────────┘   └──────────────────────────┘
└──────────────────────────┘                     │
                                                 ▼
                                ┌──────────────────────────────────┐
                                │ UNIFIED JSON RESPONSE / TOOL OUT │
                                │ Live Price + Forecast + Context  │
                                └──────────────────────────────────┘
```

#### 1. Live Lookup & Caching Engine (`src/live_fuel_feed.py` & `src/lookup_cache.py`)
- **Scraper & API Drivers**:
  - `fetch_gasbuddy_live_price(zip_code: str)`: Queries GasBuddy GraphQL endpoint (`https://www.gasbuddy.com/graphql`) for real-time station metrics.
  - `fetch_aaa_live_price(state_code: str, metro_area: str)`: Scrapes AAA Daily Fuel Gauge Report for state and metro averages.
  - `fetch_eia_weekly_fallback(region_code: str)`: EIA v2 API fallback for official regional weekly averages.
- **Cache Management**: SQLite disk-backed / in-memory cache with configurable TTL (default 15 minutes) to protect upstream providers from rate limits and IP blocks.

#### 2. RESTful API Endpoint Layer (`src/api_server.py`)
Built on FastAPI / Starlette with automatic OpenAPI schema generation:
- `GET /api/v1/prices/live?locale={national|tulsa|newark|cincinnati|oakland|zip_code}`: Returns live pump price data.
- `GET /api/v1/forecast/predict?locale={locale}&days=5`: Triggers model inference and returns predicted price, projected delta, and directional signal.
- `GET /api/v1/combined?locale={locale}`: Returns **both** live AAA/GasBuddy current price and 5-day out-of-time forecast.
- `POST /api/v1/forecast/simulate`: Accepts JSON payload specifying custom scenario inputs (e.g. `{"scenario_id": "hormuz_blockade", "locale": "oakland"}`).
- `GET /openapi.json` & `GET /.well-known/ai-plugin.json`: Standardized OpenAI GPT Action manifests.

#### 3. Model Context Protocol (MCP) Server (`src/mcp_server.py`)
Built using FastMCP / MCP Python SDK:
- **Exposed MCP Tools**:
  - `get_live_gas_prices(locale: str, zip_code: Optional[str])`: Fetches real-time AAA/GasBuddy station prices.
  - `get_gas_price_prediction(locale: str, days: int)`: Fetches Midgley 5-day price forecast and directional confidence.
  - `get_live_and_forecast(locale: str)`: Unified tool returning current pump price, predicted 5-day target, rack margin, and top news/weather drivers.
  - `simulate_fuel_market_shock(locale: str, scenario_id: str)`: Simulates real-time refinery outages, weather disasters, or geopolitical chokepoints.
- **Exposed MCP Resources**:
  - `resource://midgley/locales/{locale}`: Context snapshot of historical error metrics, current base price, and target forecasts.
- **Exposed MCP Prompts**:
  - `prompt://midgley/market_summary`: Pre-built system prompt helper for LLM financial summaries.

---

### 📋 Example Combined Endpoint JSON Payload (`/api/v1/combined?locale=oakland`)

```json
{
  "status": "success",
  "timestamp": "2026-08-24T12:11:00Z",
  "locale": {
    "code": "oakland",
    "name": "Oakland & SF Bay Area, CA",
    "padd_region": "PADD 5 West Coast"
  },
  "live_lookup": {
    "current_price_per_gal": 4.950,
    "source": "GasBuddy & AAA Live Lookup",
    "zip_code": "94612",
    "cache_hit": true,
    "cache_age_seconds": 340,
    "carb_tax_regulatory_burden_per_gal": 0.953
  },
  "forecast": {
    "model_version": "v1.4 Finlight-LLM",
    "forecast_horizon_days": 5,
    "target_date": "2026-08-29",
    "predicted_price_per_gal": 5.125,
    "expected_change_dollars": 0.175,
    "expected_change_percent": 3.54,
    "projected_direction": "UP",
    "directional_hit_rate_historical": 0.6079,
    "historical_mae_dollars": 0.1069
  },
  "key_drivers": [
    {
      "category": "Regulatory",
      "description": "CARB CaRFG summer-blend transition compliance surge",
      "impact_score": 0.220
    },
    {
      "category": "Refining",
      "description": "Chevron Richmond Refinery hydrocracker maintenance",
      "impact_score": 0.150
    }
  ]
}
```

---

### ⚙️ Action Plan & Task Checklist

- [ ] **Phase 1: Live Scraper & Lookup Layer (`src/live_fuel_feed.py` & `src/lookup_cache.py`)**
  - [ ] Implement robust GasBuddy GraphQL search client and AAA Web Scraper with fallback logic.
  - [ ] Build SQLite/in-memory response caching with 15-minute TTL.
  - [ ] Add unit tests in `tests/test_live_fuel_feed.py`.

- [ ] **Phase 2: RESTful API Endpoint Server (`src/api_server.py`)**
  - [ ] Implement FastAPI application with `/api/v1/prices/live`, `/api/v1/forecast/predict`, `/api/v1/combined`, and `/api/v1/forecast/simulate` routes.
  - [ ] Integrate OpenAPI 3.1 JSON schema generation (`docs/openapi.json`) and AI Plugin manifest (`docs/.well-known/ai-plugin.json`).
  - [ ] Add unit tests in `tests/test_api_server.py`.

- [ ] **Phase 3: Model Context Protocol (MCP) Integration (`src/mcp_server.py`)**
  - [ ] Create MCP server using FastMCP SDK implementing tools (`get_live_gas_prices`, `get_gas_price_prediction`, `get_live_and_forecast`, `simulate_fuel_market_shock`).
  - [ ] Enable both `stdio` and `HTTP/SSE` transport modes.
  - [ ] Add unit tests in `tests/test_mcp_server.py`.

- [ ] **Phase 4: Service Orchestration & Dev VM Deployment**
  - [ ] Create systemd service unit (`midgley-api.service`) running on `dev-vm`.
  - [ ] Expose public endpoint via Cloudflare Tunnel / HTTPS reverse proxy.
  - [ ] Update documentation in `docs/API.md`, `README.md`, and `AGENTS.md`.
