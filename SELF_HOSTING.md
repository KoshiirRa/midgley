# Self-Hosting & Multi-Metro Regional Deployment Guide

This document provides a comprehensive guide for self-hosting custom instances of the **Midgley LLM-Augmented Unleaded Gas Price Prediction Engine** on standalone Linux servers/VMs (`dev-vm`), containerized Docker environments, or cloud infrastructure (GitHub Actions). It covers high-availability edge caching, IP security gateways, tiered API key management, Prometheus/Grafana observability, Internet Archive cloud archiving, and extending the multi-agent framework to new regional metro areas.

---

## 📋 Table of Contents

1. [System Requirements & Prerequisites](#1-system-requirements--prerequisites)
2. [Environment Configuration & API Keys](#2-environment-configuration--api-keys)
3. [3-Tier Multi-Tier Edge Cache Gateway & Edge Queues](#3-3-tier-multi-tier-edge-cache-gateway--edge-queues)
4. [API Key Provisioning, Tiered Access & Admin Controls](#4-api-key-provisioning-tiered-access--admin-controls)
5. [Observability, Prometheus Metrics & Grafana Integration](#5-observability-prometheus-metrics--grafana-integration)
6. [Standalone Linux VM & Systemd Service Deployment](#6-standalone-linux-vm--systemd-service-deployment)
7. [Containerized Deployment (Docker & Docker Compose)](#7-containerized-deployment-docker--docker-compose)
8. [Zero-Cost Internet Archive Cloud Archiver](#8-zero-cost-internet-archive-cloud-archiver)
9. [Cloud & GitHub Actions Self-Hosting (Fork Deployment)](#9-cloud--github-actions-self-hosting-fork-deployment)
10. [LLM Guidance Prompts for Regional Market Discovery](#10-llm-guidance-prompts-for-regional-market-discovery)
11. [Step-by-Step Developer Guide: Adding New Metro Regions](#11-step-by-step-developer-guide-adding-new-metro-regions)
12. [Verification, Health Checks & Diagnostics](#12-verification-health-checks--diagnostics)

---

## 1. System Requirements & Prerequisites

### Minimum Hardware Specifications
- **Operating System:** Linux (Ubuntu 26.04 / 24.04 / 22.04 LTS recommended), Debian 12+, or macOS 14+.
- **CPU:** 2 vCPUs minimum (4 vCPUs recommended for parallel regional pipeline execution).
- **RAM:** 2 GB RAM minimum (4 GB recommended).
- **Storage:** 10 GB SSD disk space.

### Software Prerequisites
- **Python:** Python 3.11+ (Python 3.11 / 3.12 recommended for `scikit-learn` and `xgboost`).
- **Package Manager:** [`uv`](https://github.com/astral-sh/uv) (recommended for 10–100x faster package resolution) or standard `pip`.
- **Git:** Version 2.34+.
- **System Service Manager:** `systemd` (for background service and timer management on Linux).
- **Container Runtime (Optional):** Docker 24.0+ and Docker Compose v2.20+.

---

## 2. Environment Configuration & API Keys

Midgley features a cascading multi-tier fallback architecture: primary LLM extraction uses Google Gemini 2.5 Flash, with soft failovers to OpenAI/Anthropic, and a 100% offline rule-based lexicon safety net that guarantees operational continuity even with zero API keys.

Create a `.env` file in the project root directory (`/home/marty/projects/midgley/.env` or root folder):

```bash
# ==============================================================================
# MIDGLEY CORE ENVIRONMENT CONFIGURATION
# ==============================================================================

# Primary LLM Extraction Engine (Google Gemini 2.5 Flash)
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

# Admin Secret for Method B Admin API Key Management Endpoint (/api/v1/admin/keys)
MIDGLEY_ADMIN_SECRET="midgley_dev_admin_secret_2026"

# IPASIS API Gateway Security Key & Controls (ipasis.com)
IPASIS_API_KEY="ipasis_c92c28445c93_d65965edd3bfc851770b9573f777e152"
IPASIS_BLOCK_HIGH_RISK="1"       # Set to 1 to block Tor/Abuse origins with HTTP 403
MIDGLEY_IP_SECURITY_ENABLED="1"   # Set to 0 to disable IP reputation checking

# Optional OilpriceAPI Integration (25 call/day safety cap)
OILPRICEAPI_KEY="op_live_..."

# GitHub Personal Access Token (for worker dispatches)
GH_PAT="ghp_..."

# Option A2 Observability Credentials (Axiom & Sentry)
AXIOM_TOKEN="xaat-..."
SENTRY_DSN="https://...@sentry.io/..."

# ==============================================================================
# 3-TIER MULTI-TIER EDGE CACHE CREDENTIALS (OPTIONAL)
# ==============================================================================

# Tier 1: Turso Edge SQLite HTTP REST API
TURSO_DATABASE_URL="https://midgley-cache-db.turso.io"
TURSO_AUTH_TOKEN="eyJhbGciOi..."

# Tier 2: Cloudflare D1 / Edge Worker Gateway
CLOUDFLARE_CACHE_URL="https://midgley-cache.worker.dev"
CLOUDFLARE_AUTH_TOKEN="cf_token_..."
```

---

## 3. 3-Tier Multi-Tier Edge Cache Gateway & Edge Queues

Midgley includes a 3-tier caching system ([`src/lookup_cache.py`](file:///c:/Users/concentus/Documents/Random%20Ideas%20-%20LLM%20Unleaded%20Gas%20Price%20Prediction%20Modelling/src/lookup_cache.py)) that eliminates redundant LLM calls, caches headline scores by SHA-256 hash, and synchronizes API quota ledgers across multiple distributed execution nodes or GitHub runner instances.

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

### Edge Caching Options

- **Tier 1 (Turso Edge SQLite):** Requires `TURSO_DATABASE_URL` and `TURSO_AUTH_TOKEN`. Automatically initializes table schema on startup.
- **Tier 2 (Cloudflare D1 Worker):** Deploy [`workers/cache_worker.ts`](file:///c:/Users/concentus/Documents/Random%20Ideas%20-%20LLM%20Unleaded%20Gas%20Price%20Prediction%20Modelling/workers/cache_worker.ts) using `npx wrangler deploy --config wrangler.cache.toml`.
- **Tier 3 (Local SQLite Fallback):** If no cloud credentials are provided, Midgley automatically persists cache entries locally at `data/lookup_cache.sqlite` with an in-memory cache dict ($0 infrastructure cost).

### Cloudflare Queue Edge Event Buffer (`intraday-event-queue`)
For high-frequency headline burst handling, deploy [`workers/intraday_monitor_worker.ts`](file:///c:/Users/concentus/Documents/Random%20Ideas%20-%20LLM%20Unleaded%20Gas%20Price%20Prediction%20Modelling/workers/intraday_monitor_worker.ts) with Cloudflare Queue binding `INTRADAY_QUEUE`. Incoming RSS alerts are enqueued on the edge and batch-consumed by the origin gateway via `POST /api/v1/events/queue-consumer` on [`src/api_server.py`](file:///c:/Users/concentus/Documents/Random%20Ideas%20-%20LLM%20Unleaded%20Gas%20Price%20Prediction%20Modelling/src/api_server.py).

---

## 4. API Key Provisioning, Tiered Access & Admin Controls

Midgley enforces PBKDF2 SHA-256 API key authentication, per-key request rate limiting (default 30 RPM), and tiered key authorization backed by SQLite storage at `data/security.db` ([`src/key_manager.py`](file:///c:/Users/concentus/Documents/Random%20Ideas%20-%20LLM%20Unleaded%20Gas%20Price%20Prediction%20Modelling/src/key_manager.py)).

```
                      ┌───────────────────────────────────────┐
                      │    INCOMING CLIENT REQUEST AT GATEWAY │
                      └───────────────────┬───────────────────┘
                                          │
                                          ▼
                      ┌───────────────────────────────────────┐
                      │     PBKDF2 SHA-256 KEY VERIFICATION   │
                      │         (data/security.db)            │
                      └───────────────────┬───────────────────┘
                                          │
                         ┌────────────────┴────────────────┐
                         │                                 │
                         ▼                                 ▼
             ┌──────────────────────┐          ┌──────────────────────┐
             │   PRIVILEGED TIER    │          │      BASIC TIER      │
             │ Full Gemini 2.5 LLM │          │ $0 Zero-Cost Provider│
             │   Cloud Inference    │          │  Fallback Hook (#196)│
             └──────────────────────┘          └──────────────────────┘
```

### Key Management Options

#### Method A: CLI Key Management Script
Use [`scripts/manage_keys.py`](file:///c:/Users/concentus/Documents/Random%20Ideas%20-%20LLM%20Unleaded%20Gas%20Price%20Prediction%20Modelling/scripts/manage_keys.py) on the server terminal:

```bash
# Create a new privileged production API key
python3 scripts/manage_keys.py create --user-id client_prod --tier privileged --environment prod

# Create a basic tier key (routes to zero-cost fallback provider)
python3 scripts/manage_keys.py create --user-id client_basic --tier basic --environment dev

# List all active keys
python3 scripts/manage_keys.py list

# Revoke a key by prefix
python3 scripts/manage_keys.py revoke --prefix mg_live_a1b2
```

#### Method B: Admin REST API (`/api/v1/admin/keys`)
Server administrators can manage keys via HTTP requests using the `X-Admin-Secret` header matched against `MIDGLEY_ADMIN_SECRET`:

```bash
# Create a new API key via Admin REST API
curl -X POST http://localhost:8000/api/v1/admin/keys \
  -H "Content-Type: application/json" \
  -H "X-Admin-Secret: midgley_dev_admin_secret_2026" \
  -d '{"user_id": "partner_app", "tier": "privileged", "environment": "prod", "rate_limit_rpm": 60}'
```

---

## 5. Observability, Prometheus Metrics & Grafana Integration

Midgley exports system telemetry and performance metrics in standard Prometheus exposition format ([`src/telemetry.py`](file:///c:/Users/concentus/Documents/Random%20Ideas%20-%20LLM%20Unleaded%20Gas%20Price%20Prediction%20Modelling/src/telemetry.py)).

### Prometheus Metric Endpoints
- **Primary Endpoint:** `GET /api/v1/metrics`
- **Legacy / Standard Alias:** `GET /metrics`

### Exported Core Metrics

| Metric Name | Type | Description |
| :--- | :--- | :--- |
| `llm_tokens_consumed_total` | Counter | Total LLM prompt and completion tokens consumed |
| `llm_estimated_cost_usd_total` | Counter | Estimated total USD cost spent on LLM API calls |
| `ipasis_security_requests_total` | Counter | IPASIS security checks categorized by status (`allowed`, `blocked`, `bypassed`) |
| `cache_gateway_operations_total` | Counter | 3-Tier Edge Cache operations (`hit`, `miss`, `store`) |
| `api_quota_remaining_ratio` | Gauge | Remaining API quota percentage for external feeds (`finlight`, `oilprice`, etc.) |

### Grafana Prometheus Scrape Configuration
Add Midgley to your `prometheus.yml`:

```yaml
scrape_configs:
  - job_name: 'midgley_production'
    scrape_interval: 15s
    metrics_path: '/api/v1/metrics'
    static_configs:
      - targets: ['10.42.42.54:8000']
```

### Option A2 Telemetry (Axiom & Sentry)
For edge workers and background tasks, set `AXIOM_TOKEN` and `SENTRY_DSN`. Logs stream to Axiom dataset `midgley-workers`, while Cloudflare Worker scheduled runs report Sentry Cron Heartbeats (`sendSentryCronCheckIn`). For detailed Axiom APL query templates and alert rules, consult [`OBSERVABILITY_DASHBOARDS.md`](file:///c:/Users/concentus/Documents/Random%20Ideas%20-%20LLM%20Unleaded%20Gas%20Price%20Prediction%20Modelling/OBSERVABILITY_DASHBOARDS.md).

---

## 6. Standalone Linux VM & Systemd Service Deployment

To run Midgley 24/7 on a dedicated Linux host (such as `dev-vm` at `10.42.42.54`), set up `systemd` user services and timers.

### Step 1: Clone Repository & Virtual Environment
```bash
git clone https://github.com/KoshiirRa/midgley.git /home/marty/projects/midgley
cd /home/marty/projects/midgley
uv venv .venv --python 3.11
source .venv/bin/activate
uv pip install -r requirements.txt
```

### Step 2: Systemd Unit Configurations

#### 1. API Server Service (`~/.config/systemd/user/midgley-api.service`)
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

#### 2. Dashboard Web Server Service (`~/.config/systemd/user/midgley-dev.service`)
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

#### 3. Daily Forecast Pipeline Timer (`~/.config/systemd/user/midgley-daily-forecast.service` & `.timer`)

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

#### 4. Weekly Model Review Timer (`~/.config/systemd/user/midgley-weekly-review.service` & `.timer`)

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

### Enabling Services
```bash
systemctl --user daemon-reload
systemctl --user enable --now midgley-api.service
systemctl --user enable --now midgley-dev.service
systemctl --user enable --now midgley-daily-forecast.timer
systemctl --user enable --now midgley-weekly-review.timer
```

---

## 7. Containerized Deployment (Docker & Docker Compose)

Midgley can be deployed in containerized environments using Docker and Docker Compose.

### Production `Dockerfile`
Create a `Dockerfile` in the project root:

```dockerfile
FROM python:3.11-slim

WORKDIR /app

# Install system dependencies
RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential curl git && \
    rm -rf /var/lib/apt/lists/*

# Install uv package manager
RUN pip install --no-cache-dir uv

# Copy dependencies manifest
COPY requirements.txt .
RUN uv pip install --system -r requirements.txt

# Copy application source code
COPY . .

# Expose API port
EXPOSE 8000

CMD ["uvicorn", "src.api_server:app", "--host", "0.0.0.0", "--port", "8000"]
```

### `docker-compose.yml` Stack Definition
Create a `docker-compose.yml` file:

```yaml
version: '3.8'

services:
  api:
    build: .
    container_name: midgley-api
    restart: always
    ports:
      - "8000:8000"
    env_file:
      - .env
    volumes:
      - ./data:/app/data

  dashboard:
    image: python:3.11-slim
    container_name: midgley-dashboard
    restart: always
    working_dir: /app
    volumes:
      - ./docs:/app/docs
    command: python3 -m http.server 8080 --directory docs
    ports:
      - "8080:8080"
```

Start the containers: `docker compose up -d`

---

## 8. Zero-Cost Internet Archive Cloud Archiver

Midgley includes a zero-cost web archiving engine ([`src/wayback_archiver.py`](file:///c:/Users/concentus/Documents/Random%20Ideas%20-%20LLM%20Unleaded%20Gas%20Price%20Prediction%20Modelling/src/wayback_archiver.py)). During intraday event monitoring, articles and breaking news bulletins are automatically submitted to the Internet Archive Save API (`https://web.archive.org/save/{url}`).

- **7-Day Local Cache:** Save requests are deduplicated against `data/wayback_archive_cache.json` to prevent unnecessary HTTP traffic.
- **Archive URL Logging:** Permanent archive URLs (`archive_url`) are recorded alongside event records in `data/intraday_events.json`.

---

## 9. Cloud & GitHub Actions Self-Hosting (Fork Deployment)

For serverless execution via GitHub Actions:

1. **Fork Repository:** Fork `KoshiirRa/midgley` to your personal or organization GitHub account.
2. **Repository Secrets:** Under **Settings -> Secrets and variables -> Actions**, add:
   - `GEMINI_API_KEY`, `FINLIGHT_API_KEY`, `EIA_API_KEY`, `FRED_API_KEY`
   - `MIDGLEY_WEBHOOK_SECRET`, `MIDGLEY_ADMIN_SECRET`
   - `TURSO_DATABASE_URL`, `TURSO_AUTH_TOKEN` (optional)
3. **GitHub Pages Setup:** Set Pages source to **Deploy from a branch**, select branch `main` and folder `/docs`.
4. **Workflows:**
   - `.github/workflows/gas_price_forecast.yml`: Daily forecast & dashboard generation.
   - `.github/workflows/intraday_event_monitor.yml`: 15-minute event monitor.
   - `.github/workflows/weekly_model_review.yml`: Saturday performance review.

---

## 10. LLM Guidance Prompts for Regional Market Discovery

Use these 5 standardized LLM prompts when adding new metro regions to gather the necessary domain knowledge.

### Prompt 1: Econometric Benchmark & Rack Margin Discovery
```text
You are a Senior Energy Econometrician specializing in U.S. refined petroleum markets.
I need to research the regional wholesale benchmark and retail pricing dynamics for [TARGET METRO CITY, STATE] (e.g. "Chicago, IL").

Please research and provide:
1. PADD Region Classification (PADD 1A/1B/1C, PADD 2, PADD 3, PADD 4, or PADD 5).
2. Wholesale Benchmark Futures Ticker (e.g., NYMEX RBOB "RB=F", Cushing WTI "CL=F", Brent Crude "BZ=F").
3. Local Delivery Hub / Rack Margin Formula: How is local rack margin calculated relative to RBOB wholesale?
   P_retail = P_RBOB + DynamicRackMargin
4. Historical Baseline Retail Pump Price ($/gal) anchor for [TARGET METRO CITY].
5. Primary economic drivers (seasonal blends, agricultural diesel demand spikes, industrial corridors).
```

### Prompt 2: Statutory Fuel Tax & Regulatory Overhead Discovery
```text
You are a U.S. State Fuel Tax & Regulatory Policy Specialist.
I need an itemized breakdown of all statutory taxes, environmental fees, and regulatory overheads built into retail unleaded gasoline prices in [TARGET METRO CITY, STATE].

Provide exact quantitative values ($/gal) for:
1. State Motor Fuel Excise Tax ($/gal).
2. Federal Motor Fuel Excise Tax ($0.184/gal fixed).
3. Local/County/Municipal Sales Tax or Fuel Surcharges ($/gal).
4. Environmental & UST (Underground Storage Tank) Inspection Fees ($/gal).
5. Statutory Carbon Fees or Cap-and-Trade / LCFS Overhead ($/gal).
```

### Prompt 3: Regional Refining & Infrastructure Logistics Discovery
```text
You are a Petroleum Supply Chain & Logistics Engineer.
Research supply pipelines and refining capacity for [TARGET METRO CITY, STATE]:
1. Primary Supplying Refineries (Name, location, operator, capacity in bpd).
2. Primary Pipeline Corridors (Colonial Line 1/2, Kinder Morgan, Explorer, Keystone) & breakout terminals.
3. Marine / River Barge Infrastructure (Ohio River, Mississippi River, C&D Canal) and low-water/freeze risks.
4. Historical logistics vulnerabilities (pipeline leaks, refinery fires, grid power outages).
```

### Prompt 4: NOAA Weather & Geophysical Risk Discovery
```text
You are an Operational Meteorologist and Physical Risk Analyst.
Map NOAA Weather Service alerts and threat factors for [TARGET METRO CITY, STATE] (Zipcode: [ZIPCODE]):
1. NOAA NWS Forecast Zone Code (e.g., "OKZ060" for Tulsa, "NCZ081" for Greenville).
2. SPC Convective Risk Vulnerabilities (tornado, hail, wind thresholds).
3. Cold Weather Freeze / Polar Vortex Vulnerability.
4. Flooding & Marine Hazards (river gauge flood stages, hurricane storm surge).
```

### Prompt 5: Decoupled JSON Metadata Profile Generator Prompt
```text
You are an MLOps Engineer for Midgley. Generate a complete valid JSON metadata profile matching Midgley's decoupled schema for [TARGET METRO CITY, STATE] (Region ID: [region_id]).

Output ONLY valid JSON following this schema:
{
  "region_id": "[region_id]",
  "display_name": "[TARGET METRO CITY, STATE]",
  "theme_color": "emerald",
  "icon_class": "fa-gas-pump",
  "econometric_drivers": { "title": "...", "description": "..." },
  "refining_logistics": { "title": "...", "description": "..." },
  "tax_structure": { "title": "...", "description": "..." },
  "infrastructure_delivery": { "title": "...", "description": "...", "equation_latex": "P_{\\text{Retail}} = P_{\\text{RBOB}} + \\text{RackMargin}" },
  "shock_scenarios": [ { "id": "refinery_outage", "name": "...", "impact_gal": 0.150, "description": "..." } ]
}
```

---

## 11. Step-by-Step Developer Guide: Adding New Metro Regions

Follow this 7-step procedure to add a new metro region (e.g., `chicago` / `Chicago, IL`):

1. **LLM Research:** Run Prompts 1–5 to gather regional data.
2. **JSON Metadata Profile:** Save metadata to `data/regional_metadata/chicago_il.json`.
3. **Location Subpackage:** Create directory `src/locations/chicago/` containing `__init__.py`, `regional.py`, `main.py`, and `notebook_builder.py`.
4. **Master Location Registry:** Register the new region in `LOCATIONS` dict within [`src/locations/__init__.py`](file:///c:/Users/concentus/Documents/Random%20Ideas%20-%20LLM%20Unleaded%20Gas%20Price%20Prediction%20Modelling/src/locations/__init__.py).
5. **API Server Routes:** Add `"chicago"` to `LOCALE_PRICE_KEYS` and `LOCALE_RUNNERS` in [`src/api_server.py`](file:///c:/Users/concentus/Documents/Random%20Ideas%20-%20LLM%20Unleaded%20Gas%20Price%20Prediction%20Modelling/src/api_server.py).
6. **Dashboard UI Integration:** Add `build_chicago_html()` in [`src/dashboard_generator.py`](file:///c:/Users/concentus/Documents/Random%20Ideas%20-%20LLM%20Unleaded%20Gas%20Price%20Prediction%20Modelling/src/dashboard_generator.py) and update the navigation header.
7. **MLOps Prediction Tracker:** Update [`src/prediction_logger.py`](file:///c:/Users/concentus/Documents/Random%20Ideas%20-%20LLM%20Unleaded%20Gas%20Price%20Prediction%20Modelling/src/prediction_logger.py) to include the new price column for backfilling and rolling metrics.

---

## 12. Verification, Health Checks & Diagnostics

Verify your self-hosted Midgley installation using these diagnostic commands:

### 1. Unit Test Suite Execution
Run the full test suite from the project root:
```bash
PYTHONPATH=. pytest tests/ -v
```

### 2. Verify Dashboard Generation
```bash
python3 -m src.dashboard_generator
```
Ensure `docs/index.html` and regional HTML pages compile cleanly.

### 3. Verify REST API & Prometheus Metrics Endpoints
```bash
# Check API quota ledger
curl -s http://localhost:8000/api/v1/system/quota | jq .

# Check Prometheus metrics
curl -s http://localhost:8000/api/v1/metrics

# Check fallback telemetry status
curl -s http://localhost:8000/api/v1/telemetry/fallback-status | jq .
```

### 4. Verify Systemd Service Status (Linux VM)
```bash
systemctl --user status midgley-api.service
systemctl --user list-timers --all
```

---

*Midgley Version: `v0.4.1` | Engine: Gemini 2.5 Flash + Standardized Ridge / XGBoost Estimator | License: Apache 2.0*
