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

All core mathematical transformations — including **CoSPOT Compositional Spectral & Wavelet Feature Prompting** (`src/cospot_spectral_engine.py`, Issue #215, arXiv:2609.02093), Purged Cross-Validation (`src/models.py`), Dynamic Volatility-Gated Persistence Blending (`src/dynamic_region.py`), dynamic **Baker Hughes Rig Count Ingestion** (`src/alternative_data_feeds.py`, Issue #269), **Executive Social Media Live Polling & Weekend Gap Classification** (`src/executive_social_feed.py`, Issue #268), **Key Market Movers Statement Feed** (`src/key_movers_feed.py`, Issue #270), **EIA PADD Inventory & Refinery Utilization** (`src/data_ingestion.py`, Issue #271), **EIA-930 Grid Stress Modeling** (`src/data_ingestion.py`, Issue #272), **USDA Biofuel & Ethanol Rack Feeds** (`src/data_ingestion.py`, Issue #273), **EIA Daily Regional Spot Wholesale Prices** (`src/data_ingestion.py`, Issue #363), **EPA Weekly EMTS RIN Credit Ingestion** (`src/data_ingestion.py`, Issue #365), **EIA State & Metro Surveys** (`src/data_ingestion.py`, Issue #274), **FERC Form 6 Pipeline Tariffs** (`src/data_ingestion.py`, Issue #275), **USACE Lock Delays & Hydrology** (`src/usace_locks.py`, Issue #276), and Qlib Symbolic Alpha mining (`src/qlib_symbolic_engine.py`) — run natively on standard Python libraries (`numpy`, `pandas`, `scipy`) without requiring extra cloud subscriptions or heavy GPU accelerators. Point-in-time publication snapshots are automatically tracked across bitemporal ledgers (`data/*_vintages.json`) and cached in `data/lookup_cache.sqlite`.

```bash
# ==============================================================================
# MIDGLEY CORE ENVIRONMENT CONFIGURATION
# ==============================================================================

# Primary LLM Extraction Engine (Google Gemini)
GEMINI_API_KEY="AIzaSy..."

# Real-Time Financial Energy Media API (finlight.me) - Enforces 150 call/month safety cap
FINLIGHT_API_KEY="fl_live_..."

# Firecrawl Web Scraping API (firecrawl.dev) - Enforces 800 call/month safety cap (Issue #83)
FIRECRAWL_API_KEY="fc-..."

# Official U.S. EIA Open Data v2 Key (Weekly PADD Stocks & Utilization)
EIA_API_KEY="eia_api_key_here"

# U.S. EPA AirNow API Key (airnowapi.org - Free 500 req/hr developer account, Issue #73)
AIRNOW_API_KEY="0882E80D-3459-4F86-ADE5-A38F34CFE021"

# St. Louis Fed FRED Key (Macro Energy & Retail Index Series)
FRED_API_KEY="fred_api_key_here"

# CORE Open-Access Research Literature API Key (Weekly Model Review)
CORE_API_KEY="core_api_key_here"

# Semantic Scholar Academic Graph API Key (Optional, raises rate limits from 100 to 1000 req/5min)
SEMANTIC_SCHOLAR_API_KEY="semantic_scholar_api_key_here"

# OpenAlex CC0 Open-Access Literature API requires NO key (100k free requests/day with mailto header)

# Optional Secondary LLM Tier Failovers (Soft-checked)
OPENAI_API_KEY="sk-proj-..."
ANTHROPIC_API_KEY="sk-ant-..."

# Security Secret for Incoming Webhook Ingestion Gate (HMAC-SHA256 Validation)
MIDGLEY_WEBHOOK_SECRET="super-secret-hmac-key-change-me"

# Admin API Gateway Secret for Key Provisioning (/api/v1/admin/keys - Issue #341)
# MANDATORY: Fails closed (HTTP 401) if unset, empty, or whitespace-only.
MIDGLEY_ADMIN_SECRET="super-secret-admin-token-change-me"

# Master API Key for Administrative System Access (Bypasses per-key rate limits)
MIDGLEY_API_KEY="mg_master_secret_key_change_me"

# IPASIS API Gateway Security Key & Controls (ipasis.com - 100 req/day free)
IPASIS_API_KEY="ipasis_c92c28445c93_d65965edd3bfc851770b9573f777e152"
IPASIS_BLOCK_HIGH_RISK="1"       # Set to 1 to block Tor/Abuse origins with HTTP 403
MIDGLEY_IP_SECURITY_ENABLED="1"   # Set to 0 to disable IP reputation checking

# Optional OilpriceAPI Integration (25 call/day safety cap)
OILPRICEAPI_KEY="op_live_..."

# Weights & Biases (W&B) MLOps & Validation Loss Tracking (wandb.ai, Issue #80)
# Free personal tier (100 GB storage). Optional: runs offline/no-op if unset.
WANDB_API_KEY="wandb_v1_..."
WANDB_PROJECT="midgley-gas-forecasting"
WANDB_MODE="online"               # Options: 'online', 'offline', 'disabled'

# Discord Webhook Notification Gateway (Intraday Forecast Revisions, Issue #234)
# Dispatches real-time alerts on intraday price shocks with environment tagging ([PRODUCTION] vs [DEVELOPMENT])
DISCORD_INTRADAY_WEBHOOK_URL="https://discord.com/api/webhooks/YOUR_WEBHOOK_ID/YOUR_WEBHOOK_TOKEN"

# ==============================================================================
# 3-TIER MULTI-TIER EDGE CACHE & QUOTA LEDGER CREDENTIALS (OPTIONAL)
# ==============================================================================

# Tier 1: Turso Edge SQLite HTTP REST API
TURSO_DATABASE_URL="https://midgley-cache-db.turso.io"
TURSO_AUTH_TOKEN="eyJhbGciOi..."

# Tier 2: Cloudflare D1 / Edge Worker Gateway
CLOUDFLARE_CACHE_URL="https://midgley-cache.worker.dev"
CLOUDFLARE_AUTH_TOKEN="cf_token_..."

# ==============================================================================
# HINDSIGHT EPISODIC AGENT MEMORY (SUPABASE PGVECTOR & CLOUD RUN) (Issue #230)
# ==============================================================================

# Vectorize Hindsight Cloud Run REST API Endpoint (Scale-to-Zero)
HINDSIGHT_API_URL="https://midgley-hindsight-66up5e6b4a-uc.a.run.app"
HINDSIGHT_API_KEY=""              # Optional bearer token if endpoint is authenticated
HINDSIGHT_TIMEOUT="60.0"          # Socket read timeout in seconds (handles scale-to-zero cold boots)
HINDSIGHT_WARMUP_TIMEOUT="75.0"   # Background scale-to-zero container warmup handshake timeout in seconds

# Supabase PostgreSQL pgvector Connection URI (Transaction Pooler Port 5432 or 6543)
SUPABASE_DATABASE_URL="postgresql://postgres.[PROJECT-REF]:[PASSWORD]@aws-0-[REGION].pooler.supabase.com:5432/postgres"

# Google Cloud Project ID (for Cloud Run deployment)
GCP_PROJECT_ID="midgley"

# ==============================================================================
# EDGAR 8-K REFINERY OPERATOR MONITOR (Issue #129)
# ==============================================================================

# SEC EDGAR User-Agent — required for EDGAR 8-K polling (free, name + email only).
# No account or API key needed. Per EDGAR robots.txt access policy.
# Cloudflare Worker production: wrangler secret put SEC_USER_AGENT
# Optional U.S. Census Bureau API Key (api.census.gov - Free public open data)
# Optional: Public keyless queries work out-of-the-box. Add key for high-volume batch runs.
CENSUS_API_KEY=""

# ==============================================================================
# HEADLINE ARENA BENCHMARK & CALIBRATION (headlinearena.com, Issue #182)
# ==============================================================================
# OAuth2 Client Credentials for independent Brier/CRPS daily continuous probability scoring
HEADLINE_ARENA_CLIENT_ID="ha_agent_..."
HEADLINE_ARENA_CLIENT_SECRET="ha_sec_..."  # Or HEADLINE_ARENA_API_KEY
HEADLINE_ARENA_DEV_SUBMIT="0"              # Set to 1 in dev to execute live test submissions (tagged [DEV-TEST])

# Healthchecks Cron & Execution Heartbeat Monitoring (healthchecks.io, Issue #98)
HEALTHCHECKS_PING_URL="https://hc-ping.com/12ab7587-e0ed-40ac-83ad-822f9eb56a3b"
# Or separate daily/weekly endpoints:
# HEALTHCHECKS_DAILY_PING_URL="https://hc-ping.com/<uuid>"
# HEALTHCHECKS_WEEKLY_PING_URL="https://hc-ping.com/<uuid>"

# Self-Hosted ArchiveBox Historical Preservation Server (github.com/ArchiveBox/ArchiveBox, Issue #97)
ARCHIVEBOX_URL="http://10.42.42.54:8000"
ARCHIVEBOX_API_KEY=""

# Comma-separated list of refinery operator tickers to monitor for 8-K filings.
# Default covers PBF Energy, HF Sinclair, Marathon Petroleum, Valero, Phillips 66.
# Cloudflare Worker production: set EDGAR_8K_TICKERS in wrangler.toml [vars].
# Add additional tickers for non-default supplying refineries (see §7 Prompt 3).
EDGAR_8K_TICKERS="PBF,DINO,MPC,VLO,PSX"
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
4. Set `TURSO_DATABASE_URL` and `TURSO_AUTH_TOKEN` in `.env`. Midgley automatically normalizes `turso://`, `libsql://`, and `https://` URI schemes.
5. Midgley automatically initializes the table schema on startup via `_turso_ensure_table()`, or you can test connectivity immediately with the CLI probe:
   ```bash
   python3 -m src.lookup_cache --test-turso
   ```

### Option B: Setting Up Cloudflare D1 / Worker (Tier 2 Backup)
1. Create a Cloudflare D1 database: `npx wrangler d1 create midgley-cache-d1`
2. Initialize the database schema for `lookup_cache`, `seen_rss_headlines`, and `prediction_history` ([scripts/init_d1_schema.sql](file:///scripts/init_d1_schema.sql)):
   ```bash
   npx wrangler d1 execute midgley-cache-d1 --file=scripts/init_d1_schema.sql
   ```
3. Deploy the `midgley-cache-worker` proxy ([workers/cache_worker.ts](file:///workers/cache_worker.ts)) which supports key-value storage, expiration purging, and batch prediction history sync (`POST /api/v1/sync/predictions`):
   ```bash
   npx wrangler deploy --config wrangler.cache.toml
   ```
4. Configure optional telemetry & auth secrets for Option A2 (Axiom & Sentry):
   ```bash
   npx wrangler secret put SENTRY_DSN --config wrangler.cache.toml
   npx wrangler secret put AXIOM_TOKEN --config wrangler.cache.toml
   ```
5. Set `CLOUDFLARE_CACHE_URL` and `CLOUDFLARE_AUTH_TOKEN` in `.env`. Test connectivity via CLI:
   ```bash
   python3 -m src.lookup_cache --test-cloudflare
   ```

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

## 3.5. Setting Up Vectorize Hindsight Episodic Agent Memory (Issue #230)

Midgley integrates an episodic memory layer (**Retain-Recall-Reflect**) to perform automated qualitative root-cause post-mortems and historical shock analogy search during Saturday model reviews (Agent 7).

```
┌─────────────────────────────────────────────────────────────────────────────┐
│                    HINDSIGHT EPISODIC AGENT MEMORY ENGINE                   │
├─────────────────────────────────────────────────────────────────────────────┤
│ 1. RETAIN  ──► Captures resolved predictions, actual prices & anomalies      │
│ 2. RECALL  ──► Zero-LLM search over historical shocks via dense pgvector    │
│ 3. REFLECT ──► Synthesizes root-cause post-mortems & calibration suggestions │
└─────────────────────────────────────────────────────────────────────────────┘
```

### Option A: Cloud Run + Supabase pgvector Setup (Recommended)
1. **Initialize Supabase PostgreSQL Schema:**
   - Open your **Supabase Project Dashboard** $\rightarrow$ **SQL Editor**.
   - Execute [`scripts/init_supabase_hindsight.sql`](file:///scripts/init_supabase_hindsight.sql) to enable the `vector` extension, create `hindsight_memories` and `hindsight_mental_models` tables, and construct HNSW vector indexes.
2. **Deploy to Google Cloud Run (Scale-to-Zero):**
   - Ensure `SUPABASE_DATABASE_URL`, `GCP_PROJECT_ID`, and `GEMINI_API_KEY` are configured in `.env`.
   - Run the deployment script:
     ```bash
     bash scripts/deploy_hindsight_cloudrun.sh
     ```
   - Cloud Run deploys `ghcr.io/vectorize-io/hindsight:latest` with `--min-instances 0` ($0 idle cost) and `--port 8888`.
3. **Configure Endpoint in Midgley:**
   - Set `HINDSIGHT_API_URL` in `.env` and GitHub Repository Secrets:
     ```bash
     HINDSIGHT_API_URL="https://midgley-hindsight-66up5e6b4a-uc.a.run.app"
     HINDSIGHT_TIMEOUT="60.0"
     HINDSIGHT_WARMUP_TIMEOUT="75.0"
     ```
   - **Scale-to-Zero Proactive Warmup & Zero Data Loss:** When deployed with `--min-instances 0`, Cloud Run instances spin down during inactivity and require 20–35s to cold boot. Midgley automatically triggers a non-blocking proactive warmup (`warmup()`) in Step 0 of execution pipelines. If any memory retain requests occur during container cold-start, experiences are safely buffered in local SQLite with `cloud_synced = 0` and automatically reconciled (`sync_pending_memories()`) once the cloud container is fully online.

### Option B: Zero-Cost Local SQLite FTS5 Fallback ($0 / Standalone Default)
If no remote Hindsight or Supabase credentials are configured, Midgley automatically activates `SQLiteMemoryStore` at `data/agent_memory.sqlite`:
* **Zero external services or cloud accounts required.**
* Uses SQLite FTS5 with Porter stemming and BM25 ranking for analogy recall.
* Generates structured post-mortems and parameter calibration recommendations via Gemini 2.5 Flash (or the Tier 3 Offline Rule-Based Lexicon).
* **Region-Scoped Memory Retention (Issue #326):** Memory shock ingestion is scoped specifically to the regional hub being evaluated (`backfill_actual_prices_and_evaluate(target_region=...)`), eliminating redundant global tail re-evaluations and protecting cloud API quotas.

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

### Step 3: Run Baseline Forecast Pipeline & Alpha Factor Mining
Execute the full multi-region prediction pipeline once:
```bash
python3 -m src.locations.national.main --llm
```

Mine Qlib symbolic alpha factors and evaluate DDG-DA domain adaptation benchmarks:
```bash
python3 -m scripts.benchmark_qlib_rd_agent
```

### Step 4: Verify Multi-Horizon Scoreboard & MLOps Accuracy Metrics
Query the rolling scoreboard across discrete forecast horizons (1d through 5d) (Issue #209):
```bash
# Query 5-day horizon scoreboard metrics
curl -X GET "http://localhost:8000/api/v1/forecast/scoreboard?locale=national&window=30&horizon=5"

# Query 1-day (24h tactical) horizon scoreboard metrics
curl -X GET "http://localhost:8000/api/v1/forecast/scoreboard?locale=tulsa&window=30&horizon=1"
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
   - `DISCORD_INTRADAY_WEBHOOK_URL` (or `DISCORD_WEBHOOK_URL`, optional for intraday revision alerts)
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
6. Biofuel & Blendstock Specifications: Statutory ethanol blend mandate (e.g. standard E10, E15, or state bio-mandates), summer Reid Vapor Pressure (RVP in psi) compliance limits (e.g. 7.8 psi, 9.0 psi, or CARB 7.0 psi), seasonal transition dates (May 1 refinery / June 1 retail deadlines), and USDA AMS Midwest ethanol rack basis.

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
7. Official State Open Data Portal & Primary Source: Official state Socrata open data portal domain (e.g. `data.<state>.gov` or `data.gov`), State Department of Revenue/Taxation motor fuel tax bulletin URL, statutory tax adjustment schedule (e.g. annual July 1 rate adjustments or CPI indexation), and monthly taxable motor fuel volume reporting (supporting Midgley's Universal 50-State Open Data Connector).

Write out the KaTeX math formula:
T_{\text{statutory}} = \tau_{\text{state}} + \tau_{\text{federal}} + \tau_{\text{local}} + \tau_{\text{environmental}}
```

### Prompt 3: Regional Refining & Infrastructure Logistics Discovery
```text
You are a Petroleum Supply Chain & Logistics Engineer.
I need a detailed logistical breakdown of fuel supply pipelines and refining capacity for [TARGET METRO CITY, STATE].

Research and specify:
1. Primary Supplying Refineries: Name, location, operator, crude processing capacity (in bpd - barrels per day), and exact WGS84 GPS coordinates (latitude, longitude) for spatial distance-decay buffering.
2. Primary Pipeline Corridors: Specific pipeline systems (e.g., Colonial Pipeline Line 1/2, Kinder Morgan SFPP, Explorer Pipeline, Keystone, Enterprise) and major breakout distribution hubs/terminals.
3. Marine & River Barge Infrastructure: Nearby navigable river channels (e.g., Ohio River, Mississippi River, C&D Canal, Houston Ship Channel, Carquinez Strait) or ocean deepwater anchorages subject to USGS low-water restrictions, stage levels, cooling water thermal limits, or lightering detours.
   - Relevant USGS Hydrological Stations: Identify exact 8-digit USGS Station Numbers (e.g., "03612500" for Ohio River at Cairo, "07179000" for Arkansas River at Tulsa, "01477050" for Delaware River at Chester, "08077637" for Houston Ship Channel) and station names that monitor streamflow (00060), gage height (00065), water temperature (00010), or specific conductance (00095) for the supplying waterways or refinery cooling water intakes.
   - USACE Locks & Dams: Identify key U.S. Army Corps of Engineers (USACE) Locks and Dams along supplying commercial waterways (e.g., Markland, Meldahl, Lock 27, C&D Canal) that govern barge tow transit times and lock closure risks.
4. Logistics & Power Grid Risk Factors: Historical vulnerability to pipeline leaks, refinery fires, marine congestion, and electric power grid vulnerability—specifically identifying the EIA-930 Electric Grid Balancing Authority (BA) / RTO (e.g., ERCOT, MISO, PJM, CAISO, SWPP, SOCO, TVA, NYIS, ISNE) powering the supplying refineries and pipeline pump stations.
5. Metro Centroid & Spatial Buffer Anchor: Representative metro geographic coordinates (WGS84 latitude, longitude), primary 5-digit ZIP code, and approximate pipeline/haul distance (miles) to the primary supplying refinery or distribution rack hub (for GeoPandas spatial distance-decay modeling in `src/spatial_refinery.py`).
6. Fence-Line Air Quality & Industrial Emissions Monitoring (PurpleAir & OpenAQ): Identify fence-line air quality monitoring networks within a 15 km radius downwind of supplying refineries (e.g. PurpleAir optical sensor groups, OpenAQ municipal stations, EPA AirNow station ID) monitoring PM2.5, PM10, SO2, and NO2 to capture early flaring and unplanned FCC unit outage signals in `src/aqi_feed.py`.
7. SEC EDGAR Refinery Operator Monitoring (Issue #129): Identify the publicly traded refinery operators (NYSE/NASDAQ tickers) whose refinery assets directly supply [TARGET METRO CITY, STATE]. Cross-reference against the default `EDGAR_8K_TICKERS` list (`PBF`, `DINO`, `MPC`, `VLO`, `PSX`). If the primary supplying refinery is owned by an operator NOT in the default list (e.g., Delek Group `DKL`, Calumet `CLMT`, Par Pacific `PARR`, or Ergon for a mid-continent or rural region), document the ticker so it can be appended to `EDGAR_8K_TICKERS` in `wrangler.toml` (Cloudflare Worker production) or `.env` (local deployment). This ensures the EDGAR 8-K Refinery Operator Monitor (`src/edgar_8k_monitor.py` / `workers/intraday_monitor_worker.ts`) captures unplanned operational disclosures from the refineries directly supplying the new metro region.

Format the output clearly for integration into a machine learning feature engineering pipeline.
```

### Prompt 4: NOAA Weather, Physical Hydrological, Seismic & Air Quality Outage Hazard Discovery
```text
You are an Operational Meteorologist and Physical Risk Analyst.
I need to map NOAA Weather Service alerts, hydrological constraints, geophysical threat factors, and industrial air quality flaring indicators for [TARGET METRO CITY, STATE] (Zipcode: [ZIPCODE]).

Identify:
1. NOAA NWS Forecast Zone Code (e.g., "OKZ060" for Tulsa, "NCZ081" for Greenville).
2. SPC (Storm Prediction Center) Convective Risk Vulnerabilities: Severe tornado risk, hail, or high wind thresholds.
3. Cold Weather Freeze / Heat Stress & Degree Days: Sub-zero freeze or extreme summer heat vulnerabilities impacting refinery instrumentation, crude pipelines, or cooling tower thermal compliance; identify baseline Heating Degree Days (HDD) and Cooling Degree Days (CDD) profile.
4. Hydrological, Coastal & Marine Hazards: Local river gauge flood stages & water temperatures (USGS Water Data API telemetry: streamflow `00060`, gage height `00065`, water temperature `00010`, specific conductance `00095`); exposure to NOAA National Hurricane Center (NHC) tropical cyclone tracks, coastal storm surge, and BSEE offshore crude production shut-in alerts.
   - Candidate USGS Stations & Thresholds: Identify primary 8-digit USGS station site IDs and flood stage thresholds (action stage, flood stage, moderate flood stage in feet) that could disrupt petroleum rack operations, refinery cooling, or barge navigation.
5. Seismic & Earthquake Hazard Corridors (USGS Earthquake Web Service API - fdsnws/event/1/):
   - Regional Faults & Seismic Clusters: Identify active tectonic fault lines (e.g. Hayward, San Andreas, Ramapo, New Madrid) or wastewater-induced seismicity fault zones (e.g. Oklahoma/Cushing Anadarko & Nemaha fault zones).
   - Geographic Bounding Box: Define `minlatitude`, `maxlatitude`, `minlongitude`, `maxlongitude` coordinates enclosing the regional refining facilities and key delivery pipelines for live USGS GeoJSON queries (`https://earthquake.usgs.gov/fdsnws/event/1/query?format=geojson`).
   - Magnitude Operational Thresholds: Baseline magnitude trigger ($M \ge 3.8$ for shallow induced quakes, $M \ge 4.0$ or $4.5$ for tectonic faults) and catastrophic pipeline trip threshold ($M \ge 6.0$).
   - Facility Vulnerability Targets: Identify exact GPS coordinates for critical refineries, pipeline pump stations, and crude storage tank farms to evaluate distance attenuation and peak ground shaking impact in `src/usgs_seismic.py`.
6. Regional Geophysical, Wildfire & Grid Hazards: CAL FIRE PSPS wildfire power shutoffs (Diablo/Santa Ana red flag high-wind shutoffs), tsunami advisories (NOAA PTWC), and electric power grid vulnerability (EIA-930 Balancing Authority).
7. Fence-Line Air Quality & Industrial Flaring Anomaly Thresholds (PurpleAir, OpenAQ, EPA AirNow - `src/aqi_feed.py`):
   - Refining Corridor Coordinates & Sensor Buffer: Define center GPS coordinates and 15 km radius bounding box enclosing local supplying refineries for live multi-feed AQI queries.
   - Pollutant Baseline Profiles: Research typical ambient baseline levels and standard deviations for fine particulates ($\text{PM}_{2.5}$ in $\mu\text{g}/\text{m}^3$) and sulfur dioxide ($\text{SO}_2$ in $\text{ppb}$).
   - Flaring Outage Anomaly Triggers: Identify statistical $Z$-score thresholds ($Z_{\text{PM2.5}} \ge 3.5$ and $Z_{\text{SO2}} \ge 2.5$) to capture emergency catalytic cracker shutdown flaring while discriminating against ambient wildfire/wood smoke (high $\text{PM}_{2.5}$ with baseline $\text{SO}_2$).
   - Statutory Summer Blend / RVP Mandates: Identify county-level EPA AirNow monitoring sites and statutory Ozone Non-Attainment action day frequencies triggering Reid Vapor Pressure (RVP) summer blend compliance cutovers.
```

### Prompt 5: Decoupled JSON Metadata Profile Generator Prompt
```text
You are an MLOps Engineer for Midgley. Using the research gathered above for [TARGET METRO CITY, STATE] (Region ID: [region_id], e.g., "chicago_il"), generate a complete valid JSON metadata profile matching Midgley's decoupled schema.

Output ONLY valid JSON following this schema:
{
  "$schema": "https://json-schema.org/draft/2020-12/schema",
  "region_id": "[region_id]",
  "display_name": "[TARGET METRO CITY, STATE] Metro Retail",
  "padd_region": "PADD [X] [Region Name]",
  "primary_city": "[TARGET METRO CITY, STATE]",
  "counties": ["[County 1]", "[County 2]"],
  "baseline_price": 3.950,
  "icon_class": "fa-warehouse",
  "theme_color": "emerald",
  "econometric_drivers": {
    "title": "Regional Econometric Drivers & Benchmark Anchors",
    "description": "..."
  },
  "refining_logistics": {
    "title": "Refining Capacity & Pipeline Logistics",
    "description": "...",
    "primary_refinery": "[Refinery Name]",
    "capacity_bpd": 250000,
    "pipelines": ["[Pipeline 1]", "[Pipeline 2]"]
  },
  "tax_structure": {
    "title": "Statutory Tax & Regulatory Overhead",
    "description": "...",
    "state_tax_per_gal": 0.385,
    "federal_tax_per_gal": 0.184,
    "total_tax_per_gal": 0.569,
    "notes": "..."
  },
  "infrastructure_delivery": {
    "title": "Delivery Hub & Dynamic Rack Margin",
    "equation_latex": "\\text{Rack Margin} = P_{\\text{Retail}} - P_{\\text{Wholesale RBOB}} = \\$3.950 - \\$3.184 = \\$0.766/\\text{gal}",
    "description": "...",
    "hub_distance_miles": 25,
    "hub_name": "[Distribution Terminal / Rack Hub Name]"
  },
  "shock_scenarios": [
    {
      "name": "[Scenario Name]",
      "subtitle": "[Scenario Subtitle]",
      "category": "meteorological | hydrological | convective_severe | regulatory_spec | infrastructure | geopolitical",
      "active_window": [6, 1, 11, 30],
      "peak_window": [8, 15, 10, 15],
      "telemetry_hook": "noaa_nhc | noaa_spc | usgs_temp | usgs_stage | evergreen",
      "price_impact_per_gal": 0.150,
      "pct_impact": 4.25,
      "description": "..."
    }
  ]
}
```

> [!TIP]
> **Seasonal Plausibility Gating (Issue #300):** Regional shock scenarios integrated into `src/scenario_engine.py` automatically inherit dynamic plausibility evaluation (`ACTIVE_THREAT`, `SEASONALLY_PLAUSIBLE`, `SEASONALLY_DORMANT`, `EVERGREEN`, `PROSPECTIVE_FORWARD`), ensuring simulations conducted via `POST /api/v1/forecast/simulate` or MCP tool `simulate_fuel_market_shock` respect physical climatological and statutory windows.

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
Implement `fetch_chicago_market_data()` calibrated to local live pump prices ($3.95/gal base) and `get_chicago_regional_events()` defining regional shock scenarios. If adjacent to inland waterways, refinery cooling intakes, or coastal shipping channels, ingest live hydrological risk telemetry via `USGSWaterFeedConnector` (registering any newly discovered 8-digit USGS stations in `USGS_STATIONS` inside `src/usgs_water_feed.py`). If located within an active seismic fault or induced seismicity corridor, ingest live earthquake telemetry via `USGSSeismicConnector` (registering corridor bounding box and facility coordinates in `SEISMIC_CORRIDORS` inside `src/usgs_seismic.py`). If adjacent to supplying refining centers, ingest live fence-line air quality and flaring emissions telemetry via `AQIFeedConnector` (registering corridor bounding box and refinery assets in `AQI_CORRIDORS` inside `src/aqi_feed.py`).

3. **`src/locations/chicago/main.py`**:
Implement `run_chicago_pipeline(live_pump_price=None, use_llm_api=False, model_type="ridge")` which ingests market data, applies exponential decay feature engineering across multi-day horizons, trains discrete 1D–5D step-ahead estimators via `train_multi_horizon_models()`, logs and backfills predictions across all 5 horizons into `data/prediction_history.csv` via `log_predictions()` and `backfill_new_region_history()`, and returns forecast metrics.

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

### Step 6: Register Webhook Locale Routing & Infrastructure Keywords (`src/intraday_event_monitor.py`)
Update `resolve_target_locales()` and `TRIGGER_KEYWORDS` in `src/intraday_event_monitor.py` to register the new region's name, primary refining hubs, pipelines, and logistics keywords:
```python
# Add regional trigger keywords to TRIGGER_KEYWORDS
TRIGGER_KEYWORDS.extend(["chicago", "whiting refinery", "joliet refinery", "miso grid"])

# In resolve_target_locales(headline: str):
if any(k in text for k in ["chicago", "whiting refinery", "joliet refinery", "illinois"]):
    targets.add("Chicago")
```

### Step 7: Connect UI Presentation & Visual Cards (`src/dashboard_generator.py`)
1. Add `CHICAGO_PATH = os.path.join(DOCS_DIR, "chicago.html")` and `build_chicago_html()` in `src/dashboard_generator.py`.
2. Ensure `render_regional_driver_cards_html('chicago_il')` is invoked in the template to render standardized visual cards automatically from `data/regional_metadata/chicago_il.json`.
3. Add the navigation link to the **Metro Areas** dropdown menu in `get_nav_header()`.
4. Update Section 03 (**Equation 3.1: Multi-Tiered Weather Vulnerability Matrix**) in `docs/math.html` and `src/dashboard_generator.py` to append the new regional weather vector term ($\mathbf{W}_{\text{Metro}}$) and document localized NOAA NWS county/zone codes.
5. Update Section 04 (**Global & Regional Maritime Chokepoints, Inland River Barging & Waterborne Terminals** and **Equation 4.1: Unified Global Maritime Detour, Inland River Barge & Coastal Waterborne Freight Rate Model**) in `docs/math.html` and `src/dashboard_generator.py` if the region introduces inland waterway navigation/draft or coastal lightering/terminal surcharges ($\Delta \text{Margin}_{\text{waterborne}, r}$ / $\text{Index}_{\text{barge}}$).

### Step 8: Connect MLOps Prediction Tracker & Multi-Horizon Backfilling (`src/prediction_logger.py`)
Update `src/prediction_logger.py` to include `"Chicago_IL"` in target price columns and historical test-split backfilling across horizons 1 through 5 (`backfill_new_region_history(..., forecast_horizon_days=h)`).

### Step 9: Update GitHub Wiki Documentation (`KoshiirRa/midgley.wiki`)
Whenever adding, modifying, or removing data connectors, API feeds, or regional data sources:
1. Clone the GitHub Wiki repository: `git clone https://github.com/KoshiirRa/midgley.wiki.git`.
2. Document the new data connector in `Data-Ingestion-and-APIs.md` (class name, module path, API provider, endpoints, cost profile, ingested feature keys) and `Incoming-Webhook-Formatting-Guide.md`.
3. Update `Regional-Metro-Models.md` with calibration specs and locale routing keywords.
4. Update `Agent-Architecture.md` under Agent 1 modules list.
5. Update `Project-History-and-Roadmap.md` under the active release phase.
6. Commit and push to `origin/master`.

### Step 10: Modern Neural Forecasting with Nixtla NeuralForecast (Issue #93 Pivot)
For advanced PyTorch deep learning forecasting benchmarks, Midgley specifies **Nixtla `NeuralForecast`** (`N-BEATSx` / `NHITS` with `MQLoss`), which supersedes legacy unmaintained NeuralProphet (stagnant since `v0.9.0` in June 2024):
1. Install optional Nixtla dependencies:
   ```bash
   pip install neuralforecast torch
   ```
2. **Exogenous Feature Integration**: Nixtla `NeuralForecast` accepts historical exogenous shock vectors (`hist_exog_list=['event_shock_decay_5d', 'crack_spread_321_delta_5d']`) and future calendar features (`futr_exog_list=['is_weekend']`).
3. **Resiliency**: If `neuralforecast` or `torch` is omitted in lightweight container environments, Midgley defaults to regularized Ridge/XGBoost and Google TimesFM zero-shot fallback estimators with zero runtime downtime.

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
curl -s http://localhost:8000/api/v1/forecast/predict | jq .
curl -s http://localhost:8000/api/v1/macro/freight-tsi | jq .
```

### 4. Verify Systemd Timers (Linux Deployment)
```bash
systemctl --user status midgley-api.service
systemctl --user list-timers --all
```

### 5. Execute Feature Leakage & Factor Decay Validation Audit (Issue #146)
Run the quantitative research validation auditor to verify point-in-time temporal alignment, calculate Probability of Backtest Overfitting (PBO), and fit multi-horizon factor decay curves:
```bash
python3 scripts/audit_feature_leakage.py --region Tulsa_OK --horizons 1,3,5,10,14,20 --output data/feature_audit_report.json
```

### 6. Verify Model Learning & Longitudinal Adaptation Tracker (Issue #255)
Generate the model learning journal and verify that longitudinal learning curves and multi-window scoreboards calculate cleanly:
```bash
python3 -c "from src.learning_tracker import generate_learning_journal_markdown; generate_learning_journal_markdown()"
head -n 30 MODEL_LEARNING.md
```

### 7. Execute Ingestion Feed Health Diagnostics (Issue #267)
Run the built-in diagnostic probe to verify latency and connectivity across Google News RSS, NYT, Executive Social, Key Movers, and Geopolitical streams:
```bash
python3 src/intraday_event_monitor.py --check-feeds
```

### 8. Verify Model Context Protocol (MCP) Academic Literature Tools (Issue #266)
Verify that the MCP server exposes academic search (`search_academic_literature`) and TL;DR retrieval (`get_academic_paper_tldr`):
```bash
python3 -m pytest tests/test_mcp_server.py tests/test_academic_openalex.py tests/test_semantic_scholar_feed.py -v
```

### 9. Active 3-Tier Edge Cache & Database Diagnostic Probes (Issues #301 & #302)
Run active roundtrip read/write probes against Turso Edge SQLite and Cloudflare D1 layers, or inspect health via REST API:
```bash
# Full multi-tier connectivity probe
python3 -m src.lookup_cache --ping

# Targeted single-tier probes
python3 -m src.lookup_cache --test-turso
python3 -m src.lookup_cache --test-cloudflare

# Query cache statistics and active probe diagnostics via REST API Gateway
curl -s "http://localhost:8000/api/v1/system/cache-status?probe=true" | jq .
```

---

## 10. Upstream Release Manifest & Agent Migration Protocol (Issue #299)

Self-hosted instances and autonomous coding agents maintaining forks can detect upstream schema drifts, feature matrix expansions, and migration actions using the **Machine-Readable Upstream Release Manifest**:

### 1. Query Upstream Release Manifest via REST API
```bash
curl -s http://localhost:8000/api/v1/system/releases/latest | jq .
```

### 2. Run the Compatibility & Upgrade Reconciler CLI (Issue #343)
The upgrade reconciler audits local environment configuration against upstream release manifests. To prevent Arbitrary Code Execution (RCE), the reconciler strictly validates upstream URLs (enforcing HTTPS scheme) and executes only pre-defined, parameterized allowlisted actions without shell interpolation (`shell=False`):
* `retrain_regional_models`: Executes `scripts/manage_regions.py retrain --all`
* `update_static_dashboard`: Executes `src/dashboard_generator.py`
* `run_migrations`: Executes migration utilities with safe argument vectors

```bash
# Audit local configuration vs. upstream manifest (Dry-Run)
python3 scripts/check_updates.py --dry-run

# Automatically apply database migrations and retrain custom regional estimators safely
python3 scripts/check_updates.py --auto-reconcile
```

### 🤖 AI Agent Reconciliation Block
When upstream releases include new econometric features (e.g. Cboe OVX volatility, USGS river tow gauges, maritime chokepoints, California Energy Commission Fuels Watch, EPA RVP regulatory standards, NOAA CO-OPS marine water levels), autonomous AI agents can execute the following deterministic reconciliation sequence:
1. Fetch latest upstream manifest: `python3 -m src.release_manifest`
2. Run update audit: `python3 scripts/check_updates.py --dry-run`
3. Execute regional model realignment: `python3 scripts/manage_regions.py retrain --all`
4. Confirm test suite passes: `pytest tests/`

---

## 9. Zero-Cost Physical & Regulatory Data Ingestion Connectors

Midgley ingests state and federal physical telemetry at **$0 recurring API cost** with 100% offline fallback resilience:
* **California Energy Commission (CEC) Weekly Fuels Watch (`CECWeeklyFuelsConnector`, Issue #364):** Ingests weekly California refinery crude inputs, CARBOB production, NorCal/SoCal refinery utilization, and fuel inventory levels. Enforces Thursday publication schedules with bitemporal tracking in `data/cec_fuels_vintages.json`.
* **EPA & CARB Reid Vapor Pressure (RVP) Regulatory Engine (`RVPRegulatoryEngine`, Issue #366):** Models statutory Title 40 CFR Part 1090 and CARB Phase 3 CaRFG limits (7.8 psi, 9.0 psi, CARB 6.99 psi, RFG 7.4 psi), seasonal transition countdowns (May 1 terminal, June 1 retail, Sept 16 winter), and summer-blend compliance cost premiums.
* **NOAA CO-OPS Coastal Water Levels & Marine Disruption Telemetry (`NOAACOOPSConnector`, Issue #368):** Ingests tidal anomalies and storm surge residuals across critical fuel marine terminals (Houston Ship Channel, Delaware River, Carquinez Strait, Port St. Lucie) with bitemporal snapshots in `data/noaa_coops_vintages.json`.

---

*Midgley Version: `v0.7.0` | Engine: Gemini 2.5 Flash + Stacking Ensemble & Purged CV | License: Apache 2.0*



