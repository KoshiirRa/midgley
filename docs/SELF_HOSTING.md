# Self-Hosting & Multi-Metro Regional Deployment Guide

This document provides a comprehensive guide for self-hosting custom instances of the **Midgley LLM-Augmented Unleaded Gas Price Prediction Engine** on standalone Linux servers/VMs or cloud infrastructure (GitHub Actions), configuring high-availability edge caching, leveraging LLM research prompts for new market discovery, and extending the multi-agent framework to new regional metro areas.

---

## 📋 Table of Contents

1. [System Requirements & Prerequisites](#1-system-requirements--prerequisites)
2. [Environment Configuration & API Keys](#2-environment-configuration--api-keys)
3. [Setting Up the 3-Tier Multi-Tier Edge Cache Gateway](#3-setting-up-the-3-tier-multi-tier-edge-cache-gateway)
4. [Standalone Linux Server & VM Deployment](#4-standalone-linux-server--vm-deployment)
5. [Systemd Services & Automated Timer Schedules](#5-systemd-services--automated-timer-schedules)
6. [Cloud & GitHub Actions Self-Hosting (Fork Deployment)](#6-cloud--github-actions-self-hosting-fork-deployment)
7. [LLM Guidance Prompts for Econometric & Logistics Discovery](#7-llm-guidance-prompts-for-econometric--logistics-discovery)
8. [Step-by-Step Developer Guide: Adding New Metro Regions](#8-step-by-step-developer-guide-adding-new-metro-regions)
9. [Verification, Health Checks & Diagnostics](#9-verification-health-checks--diagnostics)

---

## 1. System Requirements & Prerequisites

### Minimum Hardware Specifications
- **Operating System:** Linux (Ubuntu 22.04 / 24.04 / 26.04 LTS recommended), Debian 12+, or macOS 13+.
- **CPU:** 2 vCPUs minimum (4 vCPUs recommended for parallel regional pipeline execution).
- **RAM:** 2 GB RAM minimum (4 GB recommended).
- **Storage:** 10 GB SSD disk space.

### Software Prerequisites
- **Python:** Python 3.11+ (Python 3.11 is recommended for optimal compatibility with `scikit-learn` and `xgboost`).
- **Package Manager:** [`uv`](https://github.com/astral-sh/uv) (recommended for 10–100x faster package resolution) or standard `pip`.
- **Git:** Version 2.34+.
- **System Service Manager:** `systemd` (for background service and timer management on Linux).

---

## 2. Environment Configuration & API Keys

Midgley features a cascading multi-tier fallback architecture: primary LLM extraction uses Google Gemini 2.5 Flash, with soft failovers to OpenAI/Anthropic, and a 100% offline rule-based lexicon safety net that guarantees operational continuity even with zero API keys.

Create a `.env` file in the project root directory (`/home/marty/projects/midgley/.env` or root folder):

```bash
# ==============================================================================
# MIDGLEY CORE ENVIRONMENT CONFIGURATION
# ==============================================================================

# Primary LLM Extraction Engine (Google Gemini)
GEMINI_API_KEY="AIzaSy..."

# Real-Time Financial Energy Media API (finlight.me) - Enforces 150 call/month safety cap
FINLIGHT_API_KEY="fl_live_..."

# Official U.S. EIA Open Data v2 Key (Weekly PADD Stocks & Utilization)
EIA_API_KEY="eia_api_key_here"

# St. Louis Fed FRED Key (Macro Energy & Retail Index Series)
FRED_API_KEY="fred_api_key_here"

# Optional Secondary LLM Tier Failovers (Soft-checked)
OPENAI_API_KEY="sk-proj-..."
ANTHROPIC_API_KEY="sk-ant-..."

# Security Secret for Incoming Webhook Ingestion Gate (HMAC-SHA256 Validation)
MIDGLEY_WEBHOOK_SECRET="super-secret-hmac-key-change-me"

# Optional OilpriceAPI Integration (25 call/day safety cap)
OILPRICEAPI_KEY="op_live_..."

# ==============================================================================
# 3-TIER MULTI-TIER EDGE CACHE & QUOTA LEDGER CREDENTIALS (OPTIONAL)
# ==============================================================================

# Tier 1: Turso Edge SQLite HTTP REST API
TURSO_DATABASE_URL="https://midgley-cache-db.turso.io"
TURSO_AUTH_TOKEN="eyJhbGciOi..."

# Tier 2: Cloudflare D1 / Edge Worker Gateway
CLOUDFLARE_CACHE_URL="https://midgley-cache.worker.dev"
CLOUDFLARE_AUTH_TOKEN="cf_token_..."
```

---

## 3. Setting Up the 3-Tier Multi-Tier Edge Cache Gateway

Midgley includes a 3-tier caching system (`src/lookup_cache.py`) that eliminates redundant LLM calls, caches headline scores by SHA-256 hash, and synchronizes API quota ledgers across multiple distributed execution nodes or GitHub runner instances.

```
       ┌─────────────────────────────────────────────────────────────┐
       │               3-TIER EDGE CACHE ARCHITECTURE                │
       └──────────────────────────────┬──────────────────────────────┘
                                      │
           ┌──────────────────────────┼──────────────────────────┐
           │                          │                          │
           ▼                          ▼                          ▼
┌──────────────────────┐   ┌──────────────────────┐   ┌──────────────────────┐
│  TIER 1 (PRIMARY)    │   │  TIER 2 (BACKUP)     │   │  TIER 3 (FALLBACK)   │
│  Turso Edge SQLite   │   │ Cloudflare D1 Worker │   │ Local SQLite & Mem   │
│ (TURSO_DATABASE_URL) │   │(CLOUDFLARE_CACHE_URL)│   │ (lookup_cache.db)    │
└──────────────────────┘   └──────────────────────┘   └──────────────────────┘
```

### Option A: Setting Up Turso Edge SQLite (Tier 1 Primary)
1. Install the Turso CLI: `curl -sSfL https://get.tur.so/install.sh | bash`
2. Create a database: `turso db create midgley-cache`
3. Retrieve your database URL and Auth Token:
   ```bash
   turso db show midgley-cache --url
   turso db tokens create midgley-cache
   ```
4. Set `TURSO_DATABASE_URL` and `TURSO_AUTH_TOKEN` in `.env`.
5. Midgley automatically initializes the table schema on startup via `_turso_ensure_table()`:
   ```sql
   CREATE TABLE IF NOT EXISTS lookup_cache (
       key TEXT PRIMARY KEY,
       value TEXT NOT NULL,
       created_at REAL NOT NULL,
       expires_at REAL NOT NULL
   );
   ```

### Option B: Setting Up Cloudflare D1 / Worker (Tier 2 Backup)
1. Create a Cloudflare D1 database: `npx wrangler d1 create midgley-cache-d1`
2. Deploy the `midgley-cache-worker` proxy ([workers/cache_worker.ts](file:///c:/Users/concentus/Documents/Random%20Ideas%20-%20LLM%20Unleaded%20Gas%20Price%20Prediction%20Modelling/workers/cache_worker.ts)):
   ```bash
   npx wrangler deploy --config wrangler.cache.toml
   ```
3. Configure optional telemetry & auth secrets for Option A2 (Axiom & Sentry):
   ```bash
   npx wrangler secret put SENTRY_DSN --config wrangler.cache.toml
   npx wrangler secret put AXIOM_TOKEN --config wrangler.cache.toml
   ```
4. Set `CLOUDFLARE_CACHE_URL` and `CLOUDFLARE_AUTH_TOKEN` in `.env`.

### Deploying the Intraday RSS Monitoring Worker (`midgley-intraday-monitor`)
1. Deploy the 15-minute intraday RSS monitor worker ([workers/intraday_monitor_worker.ts](file:///c:/Users/concentus/Documents/Random%20Ideas%20-%20LLM%20Unleaded%20Gas%20Price%20Prediction%20Modelling/workers/intraday_monitor_worker.ts)):
   ```bash
   npx wrangler deploy
   ```
2. Configure worker secrets:
   ```bash
   npx wrangler secret put GH_PAT
   npx wrangler secret put SENTRY_DSN
   npx wrangler secret put AXIOM_TOKEN
   ```

### Option C: Standalone Local Fallback (Tier 3 Default)
If no edge credentials are supplied, Midgley defaults to local SQLite persistence at `data/lookup_cache.sqlite` with an in-memory fast dict lookup ($0 cloud infrastructure cost, zero external setup required).

---

## 4. Standalone Linux Server & VM Deployment

Follow these steps to deploy Midgley on a dedicated Linux host (e.g. `dev-vm` / Ubuntu host):

### Step 1: Clone Repository & Set Up Virtual Environment
```bash
# Clone repository
git clone https://github.com/KoshiirRa/midgley.git /home/marty/projects/midgley
cd /home/marty/projects/midgley

# Create Python 3.11 virtual environment using uv or venv
uv venv .venv --python 3.11
source .venv/bin/activate

# Install required dependencies
uv pip install -r requirements.txt
```

### Step 2: Test API Server Execution
Launch the FastAPI REST & MCP server manually to verify installation:
```bash
python3 -m uvicorn src.api_server:app --host 0.0.0.0 --port 8000
```
Test health endpoint:
```bash
curl http://localhost:8000/api/v1/system/quota
```

### Step 3: Run Baseline Forecast Pipeline
Execute the full multi-region prediction pipeline once:
```bash
python3 -m src.locations.national.main --llm
```

---

## 5. Systemd Services & Automated Timer Schedules

To run Midgley 24/7 on a Linux machine with automated background execution, set up `systemd` user services and timers.

### 1. API Server Service (`~/.config/systemd/user/midgley-api.service`)
```ini
[Unit]
Description=Midgley Gas Price Forecasting REST & MCP API Server
After=network.target

[Service]
Type=simple
WorkingDirectory=/home/marty/projects/midgley
ExecStart=/home/marty/projects/midgley/.venv/bin/uvicorn src.api_server:app --host 0.0.0.0 --port 8000
Restart=always
RestartSec=5
EnvironmentFile=/home/marty/projects/midgley/.env

[Install]
WantedBy=default.target
```

### 2. Dashboard Web Server Service (`~/.config/systemd/user/midgley-dev.service`)
```ini
[Unit]
Description=Midgley Web Dashboard HTTP Server (Port 8080)
After=network.target

[Service]
Type=simple
WorkingDirectory=/home/marty/projects/midgley
ExecStart=/usr/bin/python3 -m http.server 8080 --directory docs
Restart=always
RestartSec=5

[Install]
WantedBy=default.target
```

### 3. Daily Forecast Pipeline Timer (`~/.config/systemd/user/midgley-daily-forecast.service` & `.timer`)

**`midgley-daily-forecast.service`:**
```ini
[Unit]
Description=Midgley Daily Gas Price LLM Forecasting Pipeline
After=network.target

[Service]
Type=oneshot
WorkingDirectory=/home/marty/projects/midgley
ExecStart=/home/marty/projects/midgley/.venv/bin/python -m src.locations.national.main --llm
EnvironmentFile=/home/marty/projects/midgley/.env
```

**`midgley-daily-forecast.timer`:**
```ini
[Unit]
Description=Run Midgley Daily Gas Price Forecast at 06:00 AM Central

[Timer]
OnCalendar=*-*-* 06:00:00 America/Chicago
Persistent=true

[Install]
WantedBy=timers.target
```

### 4. Weekly Model Review Timer (`~/.config/systemd/user/midgley-weekly-review.service` & `.timer`)

**`midgley-weekly-review.service`:**
```ini
[Unit]
Description=Midgley Weekly Model Performance Review & Issue Self-Audit
After=network.target

[Service]
Type=oneshot
WorkingDirectory=/home/marty/projects/midgley
ExecStart=/home/marty/projects/midgley/.venv/bin/python -m src.weekly_issue_reporter
EnvironmentFile=/home/marty/projects/midgley/.env
```

**`midgley-weekly-review.timer`:**
```ini
[Unit]
Description=Run Midgley Weekly Review Every Saturday at 08:00 AM Central

[Timer]
OnCalendar=Sat *-*-* 08:00:00 America/Chicago
Persistent=true

[Install]
WantedBy=timers.target
```

### Enabling and Activating Services
```bash
# Reload systemd user daemon
systemctl --user daemon-reload

# Enable and start services
systemctl --user enable --now midgley-api.service
systemctl --user enable --now midgley-dev.service
systemctl --user enable --now midgley-daily-forecast.timer
systemctl --user enable --now midgley-weekly-review.timer

# Check active status
systemctl --user list-timers
```

---

## 6. Cloud & GitHub Actions Self-Hosting (Fork Deployment)

If you prefer serverless execution via GitHub Actions:

1. **Fork the Repository:** Fork `KoshiirRa/midgley` to your personal or organization account.
2. **Configure Repository Secrets:** Navigate to **Settings -> Secrets and variables -> Actions** and add:
   - `GEMINI_API_KEY`
   - `FINLIGHT_API_KEY`
   - `EIA_API_KEY`
   - `FRED_API_KEY`
   - `MIDGLEY_WEBHOOK_SECRET`
   - `TURSO_DATABASE_URL` (optional)
   - `TURSO_AUTH_TOKEN` (optional)
3. **Configure GitHub Pages:**
   - Navigate to **Settings -> Pages**.
   - Under **Build and deployment**, set **Source** to `Deploy from a branch`.
   - Select branch `main` (or `dev`) and folder `/docs`.
4. **Automated Workflows:**
   - `.github/workflows/gas_price_forecast.yml`: Runs daily forecasting & updates GitHub Pages.
   - `.github/workflows/intraday_event_monitor.yml`: Runs 15-minute event monitoring & webhook gateways.
   - `.github/workflows/weekly_model_review.yml`: Runs Saturday performance audits.
   - `.github/workflows/nightly_dev_release.yml`: Builds nightly releases at 08:00 UTC.

---

## 7. LLM Guidance Prompts for Econometric & Logistics Discovery

Before adding a new metro region (e.g., Houston TX, Chicago IL, Seattle WA, Atlanta GA), use the following 5 standardized LLM guidance prompts to research and structure the regional domain knowledge required by Midgley.

### Prompt 1: Econometric Benchmark & Rack Margin Discovery
```text
You are a Senior Energy Econometrician specializing in U.S. refined petroleum markets.
I need to research the regional wholesale benchmark and retail pricing dynamics for [TARGET METRO CITY, STATE] (e.g. "Chicago, IL").

Please research and provide:
1. PADD Region Classification: (PADD 1A/1B/1C, PADD 2, PADD 3, PADD 4, or PADD 5).
2. Wholesale Benchmark Futures Ticker: (e.g., NYMEX RBOB "RB=F", Cushing WTI "CL=F", Brent Crude "BZ=F").
3. Local Delivery Hub / Crack Spread Formula: How is the local rack margin calculated relative to RBOB wholesale?
   Equation: P_retail = P_RBOB + DynamicRackMargin
4. Historical Baseline Retail Pump Price ($/gal) anchor for [TARGET METRO CITY].
5. Primary economic drivers influencing local fuel price volatility (e.g., seasonal summer blend transitions, regional agricultural diesel demand spikes, industrial transportation hubs).

Format your output in concise technical bullet points.
```

### Prompt 2: Statutory Fuel Tax & Statutory Overhead Discovery
```text
You are a U.S. State Fuel Tax & Regulatory Policy Specialist.
I need a complete itemized breakdown of all statutory taxes, environmental fees, and regulatory overheads built into retail unleaded gasoline prices in [TARGET METRO CITY, STATE].

Provide exact quantitative values ($/gal) for:
1. State Motor Fuel Excise Tax ($/gal).
2. Federal Motor Fuel Excise Tax ($0.184/gal fixed).
3. Local/County/Municipal Sales Tax or Fuel Surcharges ($/gal equivalent).
4. Environmental & UST (Underground Storage Tank) Inspection Fees ($/gal).
5. Statutory Carbon Fees or Cap-and-Trade / LCFS Overhead (if applicable, e.g. California CARB / Washington CCA).
6. Total Aggregated Statutory Burden T_statutory ($/gal).

Write out the KaTeX math formula:
T_{\text{statutory}} = \tau_{\text{state}} + \tau_{\text{federal}} + \tau_{\text{local}} + \tau_{\text{environmental}}
```

### Prompt 3: Regional Refining & Infrastructure Logistics Discovery
```text
You are a Petroleum Supply Chain & Logistics Engineer.
I need a detailed logistical breakdown of fuel supply pipelines and refining capacity for [TARGET METRO CITY, STATE].

Research and specify:
1. Primary Supplying Refineries: Name, location, operator, and crude processing capacity (in bpd - barrels per day).
2. Primary Pipeline Corridors: Specific pipeline systems (e.g., Colonial Pipeline Line 1/2, Kinder Morgan SFPP, Explorer Pipeline, Keystone, Enterprise) and major breakout distribution hubs/terminals.
3. Marine / River Barge Infrastructure: Nearby navigable river channels (e.g., Ohio River, Mississippi River, C&D Canal) or ocean deepwater anchorages subject to low-water restrictions, weather delays, or lightering detours.
4. Logistics Risk Factors: Historical vulnerability to pipeline leaks, refinery fires, power grid outages, or barge congestion.

Format the output clearly for integration into a machine learning feature engineering pipeline.
```

### Prompt 4: NOAA Weather & Geophysical Risk Discovery
```text
You are an Operational Meteorologist and Physical Risk Analyst.
I need to map NOAA Weather Service alerts and geophysical threat factors for [TARGET METRO CITY, STATE] (Zipcode: [ZIPCODE]).

Identify:
1. NOAA NWS Forecast Zone Code (e.g., "OKZ060" for Tulsa, "NCZ081" for Greenville).
2. SPC (Storm Prediction Center) Convective Risk Vulnerabilities: Severe tornado risk, hail, or high wind thresholds.
3. Cold Weather Freeze / Polar Vortex Vulnerability: Sub-zero freeze impacts on local refinery instrumentation or crude pipelines.
4. Flooding & Marine Hazards: Local river gauge flood stages (e.g., Tar River, Catawba River, Mississippi Confluence) or coastal hurricane storm surge risks.
5. Regional Geophysical Risks: CAL FIRE PSPS wildfire power shutoffs, USGS seismic fault line risks, or tsunami advisories.
```

### Prompt 5: Decoupled JSON Metadata Profile Generator Prompt
```text
You are an MLOps Engineer for Midgley. Using the research gathered above for [TARGET METRO CITY, STATE] (Region ID: [region_id], e.g., "chicago_il"), generate a complete valid JSON metadata profile matching Midgley's decoupled schema.

Output ONLY valid JSON following this schema:
{
  "region_id": "[region_id]",
  "display_name": "[TARGET METRO CITY, STATE]",
  "theme_color": "emerald",
  "icon_class": "fa-gas-pump",
  "econometric_drivers": {
    "title": "Regional Econometric Drivers & Benchmark Anchors",
    "description": "..."
  },
  "refining_logistics": {
    "title": "Refining Capacity & Pipeline Logistics",
    "description": "..."
  },
  "tax_structure": {
    "title": "Statutory Tax & Regulatory Overhead",
    "description": "..."
  },
  "infrastructure_delivery": {
    "title": "Delivery Hub & Rack Margin Equation",
    "description": "...",
    "equation_latex": "P_{\\text{Retail}} = P_{\\text{RBOB}} + \\text{RackMargin}"
  },
  "shock_scenarios": [
    {
      "id": "refinery_outage",
      "name": "Local Refinery Unplanned Outage",
      "impact_gal": 0.150,
      "description": "..."
    }
  ]
}
```

---

## 8. Step-by-Step Developer Guide: Adding New Metro Regions

To extend Midgley to a new metropolitan region (e.g., adding `chicago` / `Chicago, IL`), follow this 7-step developer tutorial.

```
┌─────────────────────────────────────────────────────────────────────────┐
│                      NEW METRO REGION ADDITION STEPS                    │
├─────────────────────────────────────────────────────────────────────────┤
│ 1. LLM Research & Discovery ──► 2. Create data/regional_metadata/json   │
│ 3. Create src/locations/subpackage ──► 4. Register in src/locations/    │
│ 5. Register in src/api_server.py ──► 6. Connect UI in dashboard_gen     │
│ 7. Connect Tracker in prediction_logger.py ──► Complete Integration!   │
└─────────────────────────────────────────────────────────────────────────┘
```

### Step 1: Execute LLM Discovery Prompts
Run Prompts 1–5 above to research the new metro region and generate its profile data.

### Step 2: Create Decoupled JSON Profile (`data/regional_metadata/chicago_il.json`)
Save the JSON profile generated in Step 1 to `data/regional_metadata/chicago_il.json`.

### Step 3: Create Localized Subpackage Agent (`src/locations/chicago/`)
Create a new folder `src/locations/chicago/` containing four files:

1. **`src/locations/chicago/__init__.py`**:
```python
"""Chicago Metro, IL Regional Location Package (src/locations/chicago)"""
from src.locations.chicago.regional import fetch_chicago_market_data, get_chicago_regional_events
from src.locations.chicago.main import run_chicago_pipeline
from src.locations.chicago.notebook_builder import build_chicago_notebook

__all__ = [
    "fetch_chicago_market_data",
    "get_chicago_regional_events",
    "run_chicago_pipeline",
    "build_chicago_notebook"
]
```

2. **`src/locations/chicago/regional.py`**:
Implement `fetch_chicago_market_data()` calibrated to local live pump prices ($3.95/gal base) and `get_chicago_regional_events()` defining regional shock scenarios.

3. **`src/locations/chicago/main.py`**:
Implement `run_chicago_pipeline(live_pump_price=None, use_llm_api=False, model_type="ridge")` which ingests market data, applies exponential decay feature engineering, fits the Ridge estimator, logs predictions to `data/prediction_history.csv`, and returns forecast metrics.

4. **`src/locations/chicago/notebook_builder.py`**:
Implement `build_chicago_notebook()` returning export path `"chicago_gas_price_llm_forecasting.ipynb"`.

### Step 4: Register Location in Master Registry (`src/locations/__init__.py`)
Update `src/locations/__init__.py`:
```python
from src.locations.chicago import run_chicago_pipeline, build_chicago_notebook

LOCATIONS["chicago"] = {
    "id": "chicago",
    "name": "Chicago Metro, IL",
    "type": "regional",
    "module": "src.locations.chicago",
    "run_pipeline": run_chicago_pipeline,
    "build_notebook": build_chicago_notebook,
    "notebook_filename": "chicago_gas_price_llm_forecasting.ipynb"
}
```

### Step 5: Register API Server Routes & Scenario Endpoints (`src/api_server.py`)
Add `"chicago"` to `LOCALE_PRICE_KEYS` and `LOCALE_RUNNERS` in `src/api_server.py`:
```python
LOCALE_PRICE_KEYS["chicago"] = "Chicago_IL"
LOCALE_RUNNERS["chicago"] = run_chicago_pipeline
```

### Step 6: Connect UI Presentation & Visual Cards (`src/dashboard_generator.py`)
1. Add `CHICAGO_PATH = os.path.join(DOCS_DIR, "chicago.html")` and `build_chicago_html()` in `src/dashboard_generator.py`.
2. Ensure `render_regional_driver_cards_html('chicago_il')` is invoked in the template to render standardized visual cards automatically from `data/regional_metadata/chicago_il.json`.
3. Add the navigation link to the **Metro Areas** dropdown menu in `get_nav_header()`.

### Step 7: Connect MLOps Prediction Tracker & Backfilling (`src/prediction_logger.py`)
Update `src/prediction_logger.py` to include `"Chicago_IL"` in target price columns and historical test-split backfilling (`backfill_new_region_history`).

### Step 8: Update GitHub Wiki Documentation (`KoshiirRa/midgley.wiki`)
Whenever adding, modifying, or removing data connectors, API feeds, or regional data sources:
1. Clone the GitHub Wiki repository: `git clone https://github.com/KoshiirRa/midgley.wiki.git`.
2. Document the new data connector in `Data-Ingestion-and-APIs.md` (class name, module path, API provider, endpoints, cost profile, ingested feature keys).
3. Update `Agent-Architecture.md` under Agent 1 modules list.
4. Update `Project-History-and-Roadmap.md` under the active release phase.
5. Commit and push to `origin/master`.

---

## 9. Verification, Health Checks & Diagnostics

To verify your self-hosted Midgley deployment or newly added metro region:

### 1. Execute Unit Test Suite
```bash
pytest tests/ -v
```

### 2. Verify Dashboard Generation & Regional Card Loading
```bash
python3 -m src.dashboard_generator
```
Verify that `docs/index.html` and regional HTML pages compile without errors.

### 3. Verify System Quota & REST API Health
```bash
curl -s http://localhost:8000/api/v1/system/quota | jq .
curl -s http://localhost:8000/api/v1/forecast/latest | jq .
```

### 4. Verify Systemd Timers (Linux Deployment)
```bash
systemctl --user status midgley-api.service
systemctl --user list-timers --all
```

---

*Midgley Version: `v0.3.3` | Engine: Gemini 2.5 Flash + Ridge (α=10.0) | License: Apache 2.0*
