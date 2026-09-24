# Self-Hosting & Multi-Metro Regional Deployment Guide

This document provides a comprehensive guide for self-hosting custom instances of the **Midgley LLM-Augmented Unleaded Gas Price Prediction Engine** on standalone Linux servers/VMs or cloud infrastructure (GitHub Actions), configuring high-availability edge caching, leveraging LLM research prompts for new market discovery, and extending the multi-agent framework to new regional metro areas.

---

## 📋 Table of Contents

1. [System Requirements & Prerequisites](#1-system-requirements--prerequisites)
2. [Environment Configuration & API Keys](#2-environment-configuration--api-keys)
3. [Setting Up the 3-Tier Multi-Tier Edge Cache Gateway](#3-setting-up-the-3-tier-multi-tier-edge-cache-gateway)
4. [Production Docker Container & Durable State Architecture](#4-production-docker-container--durable-state-architecture)
5. [Standalone Linux Server & VM Deployment](#5-standalone-linux-server--vm-deployment)
6. [Systemd Services & Automated Timer Schedules](#6-systemd-services--automated-timer-schedules)
7. [Cloud & GitHub Actions Self-Hosting (Fork Deployment)](#7-cloud--github-actions-self-hosting-fork-deployment)
8. [LLM Guidance Prompts for Econometric & Logistics Discovery](#8-llm-guidance-prompts-for-econometric--logistics-discovery)
9. [Step-by-Step Developer Guide: Adding New Metro Regions](#9-step-by-step-developer-guide-adding-new-metro-regions)
10. [Verification, Health Checks & Diagnostics](#10-verification-health-checks--diagnostics)

---

## 1. System Requirements & Prerequisites

### Minimum Hardware Specifications
- **Operating System:** Linux (Ubuntu 22.04 / 24.04 / 26.04 LTS recommended), Debian 12+, or macOS 13+.
- **CPU:** 2 vCPUs minimum (4 vCPUs recommended for parallel regional pipeline execution).
- **RAM:** 2 GB RAM minimum (4 GB recommended).
- **Storage:** 10 GB SSD disk space.

### Software Prerequisites
- **Python:** Python 3.11, 3.12, 3.13 (Python >=3.11 required; Python 3.11, 3.12, and 3.13 tested in CI; Docker image uses `python:3.13-slim` with `uv`).
- **Deterministic Lockfile:** Standard pinned dependencies are maintained in `requirements.lock` (generated via `pip-compile`).
- **Node & Cloudflare Workers:** Node.js 20+, Wrangler CLI v3.x+ (for deploying Cloudflare edge cache and intraday RSS workers).
- **Database & Storage:** SQLite 3.35+ (with JSON1 & FTS5 support), Turso libSQL (Hrana protocol v2), Cloudflare D1.
- **Package Manager:** [`uv`](https://github.com/astral-sh/uv) (recommended for 10–100x faster package resolution) or standard `pip`.
- **Feed Parser Security:** `defusedxml>=0.7.1` is bundled in dependencies to secure unauthenticated upstream XML feeds (arXiv, BSEE, EDGAR 8-K, NHC, RSS) against entity expansion (Billion Laughs) and DoS attacks (Issue #351).
- **Static Analysis Gate:** `ruff>=0.9.0` is bundled to validate syntax and catch fatal scope errors across CI/CD and self-hosted instances (Issue #350).
- **Line Ending Invariants:** Repository `.gitattributes` enforces LF line endings across POSIX and Windows checkouts (Issue #430).

---

## 2. Environment Configuration & API Keys

Midgley features a cascading multi-tier fallback architecture: primary LLM extraction uses Google Gemini 2.5 Flash, with soft failovers to OpenAI/Anthropic, and a 100% offline rule-based lexicon safety net that guarantees operational continuity even with zero API keys. 

All core mathematical transformations — including **CoSPOT Compositional Spectral & Wavelet Feature Prompting** (`src/cospot_spectral_engine.py`, Issue #215, arXiv:2609.02093), Purged Cross-Validation (`src/models.py`), Dynamic Volatility-Gated Persistence Blending (`src/dynamic_region.py`), dynamic **Baker Hughes Rig Count Ingestion** (`src/alternative_data_feeds.py`, Issue #269), **Executive Social Media Live Polling & Weekend Gap Classification** (`src/executive_social_feed.py`, Issue #268), **Key Market Movers Statement Feed** (`src/key_movers_feed.py`, Issue #270), **EIA PADD Inventory & Refinery Utilization** (`src/data_ingestion.py`, Issue #271), **EIA-930 Grid Stress Modeling** (`src/data_ingestion.py`, Issue #272), **USDA Biofuel & Ethanol Rack/RIN Feeds** (`src/data_ingestion.py`, Issue #273), **EIA State & Metro Surveys** (`src/data_ingestion.py`, Issue #274), **FERC Form 6 Pipeline Tariffs** (`src/data_ingestion.py`, Issue #275), **USACE Lock Delays & Hydrology** (`src/usace_locks.py`, Issue #276), and Qlib Symbolic Alpha mining (`src/qlib_symbolic_engine.py`) — run natively on standard Python libraries (`numpy`, `pandas`, `scipy`) without requiring extra cloud subscriptions or heavy GPU accelerators. Point-in-time publication snapshots are automatically tracked across bitemporal ledgers (`data/*_vintages.json`) and cached in `data/lookup_cache.sqlite`.

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

# Security Secret for Incoming Webhook Ingestion Gate (HMAC-SHA256 Validation with Timestamp Replay Defense)
MIDGLEY_WEBHOOK_SECRET="super-secret-hmac-key-change-me"

# REST & MCP API Gateway Master Key (Full Privileged Access)
MIDGLEY_API_KEY="mg_prod_master_key_change_me"

# Admin Secret for Key Provisioning & Edge Probe Diagnostics (Fail-Closed)
MIDGLEY_ADMIN_SECRET="admin-secret-provisioning-token-change-me"

# IPASIS API Gateway Security Key & Controls (ipasis.com - 100 req/day free)
IPASIS_API_KEY="ipasis_live_key_here"
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
2. Initialize the database schema for `lookup_cache`, `seen_rss_headlines`, and `prediction_history` (`scripts/init_d1_schema.sql`):
   ```bash
   npx wrangler d1 execute midgley-cache-d1 --file=scripts/init_d1_schema.sql
   ```
3. Deploy the `midgley-cache-worker` proxy (`workers/cache_worker.ts` with `workers/wrangler.cache.toml`):
   ```bash
   # Deploy staging or production environment
   npx wrangler deploy --config workers/wrangler.cache.toml --env staging
   # Or for production:
   npx wrangler deploy --config workers/wrangler.cache.toml --env production
   ```
4. Configure required authentication token and optional telemetry secrets (Axiom & Sentry):
   > [!IMPORTANT]
   > **Fail-Closed Security (Issue #438)**: `midgley-cache-worker` strictly enforces Bearer token authentication against `CLOUDFLARE_AUTH_TOKEN`. If `CLOUDFLARE_AUTH_TOKEN` is unset or invalid, all cache write, read, and sync endpoints reject requests with `401 Unauthorized`.
   ```bash
   npx wrangler secret put CLOUDFLARE_AUTH_TOKEN --config workers/wrangler.cache.toml --env staging
   npx wrangler secret put SENTRY_DSN --config workers/wrangler.cache.toml --env staging
   npx wrangler secret put AXIOM_TOKEN --config workers/wrangler.cache.toml --env staging
   ```
5. Set `CLOUDFLARE_CACHE_URL` and `CLOUDFLARE_AUTH_TOKEN` in `.env`. Test connectivity via CLI:
   ```bash
   python3 -m src.lookup_cache --test-cloudflare
   ```

### Deploying the Intraday RSS Monitoring Worker (`midgley-intraday-monitor`)
1. Validate TypeScript types and run automated Worker test suite:
   ```bash
   npm run typecheck
   npm test
   ```
2. Deploy the 15-minute intraday RSS monitor worker (`workers/intraday_monitor_worker.ts` with `wrangler.toml`):
   ```bash
   npx wrangler deploy --env staging
   # Or for production:
   npx wrangler deploy --env production
   ```
3. Configure worker secrets (including `CLOUDFLARE_AUTH_TOKEN` for authenticating `POST /flag`, `/run`, `/trigger` endpoints):
   ```bash
   npx wrangler secret put CLOUDFLARE_AUTH_TOKEN --env staging
   npx wrangler secret put GH_PAT --env staging
   npx wrangler secret put SENTRY_DSN --env staging
   npx wrangler secret put AXIOM_TOKEN --env staging
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

### Option A: Vectorize Hindsight-Hosted SaaS (Recommended Cloud Option - Issue #421)
For managed cloud deployment without managing containers or incurring serverless compute costs:
1. **Create an API Key:** Generate an API key on [Vectorize Hindsight Cloud](https://hindsight.vectorize.io).
2. **Configure Environment:** Set the following variables in `.env` and GitHub Repository Secrets:
   ```bash
   HINDSIGHT_API_URL="https://api.hindsight.vectorize.io"
   HINDSIGHT_API_KEY="hsk_..."
   HINDSIGHT_BANK_ID="Midgley"
   ```
3. **Migration & Zero Cold Starts:** Hindsight-Hosted is always warm ($0$ cold-start latency) and operates on a purely pay-per-token/call pricing model (**~$3.50/month** for daily + weekly forecasting workloads, with initial \$5.00 free credit balance). Historical SQLite memories can be bulk-uploaded using `python scripts/migrate_memory_to_hosted.py`.

> [!CAUTION]
> **Cloud Run Scale-to-Zero Cost Overrun Warning (Issue #421):**
> Deploying the `vectorize-io/hindsight` container to Google Cloud Run with `--min-instances 0` (scale-to-zero) was found in production to incur **~$17.14–$35.66/month** in GCP billing. Because the container was provisioned with 2 vCPU / 2GiB RAM and frequently woken up by daily forecast pipelines, weekly model reviews, and telemetry syncs, accumulated container boot/keep-alive seconds exceeded the cost of a dedicated VPS or hosted SaaS. Self-hosted Docker or Hindsight-Hosted SaaS is recommended.

### Option B: Local Dev-VM / Linux Server Self-Hosting ($0 / Dedicated Host)
To run Hindsight on your own infrastructure (e.g. `dev-vm` / `10.42.42.54`):
1. **Initialize Supabase PostgreSQL Schema:**
   - Execute [`scripts/init_supabase_hindsight.sql`](scripts/init_supabase_hindsight.sql) in your Supabase SQL editor.

2. **Run Docker Container on Host:**
   ```bash
   docker run -d \
     --name midgley-hindsight \
     --restart unless-stopped \
     -p 8888:8888 \
     -e HINDSIGHT_API_PORT="8888" \
     -e DATABASE_URL="$SUPABASE_DATABASE_URL" \
     -e HINDSIGHT_API_LLM_PROVIDER="gemini" \
     -e HINDSIGHT_API_LLM_MODEL="gemini-2.5-flash" \
     -e HINDSIGHT_API_LLM_API_KEY="$GEMINI_API_KEY" \
     ghcr.io/vectorize-io/hindsight:latest
   ```
3. **Configure Endpoint:** Point `HINDSIGHT_API_URL="http://10.42.42.54:8888"` in `.env`.

### Option C: Zero-Cost Local SQLite FTS5 Fallback ($0 / Standalone Default)
If no remote Hindsight or Supabase credentials are configured, Midgley automatically activates `SQLiteMemoryStore` at `data/agent_memory.sqlite`:
* **Zero external services or cloud accounts required.**
* Uses SQLite FTS5 with Porter stemming and BM25 ranking for analogy recall.
* Generates structured post-mortems and parameter calibration recommendations via Gemini 2.5 Flash (or the Tier 3 Offline Rule-Based Lexicon).
* **Region-Scoped Memory Retention (Issue #326):** Memory shock ingestion is scoped specifically to the regional hub being evaluated (`backfill_actual_prices_and_evaluate(target_region=...)`), eliminating redundant global tail re-evaluations and protecting cloud API quotas.

---

## 4. Production Docker Container & Durable State Architecture

Midgley provides a production-hardened multi-stage Docker container built on `python:3.13-slim` with `uv`, OpenMP acceleration for XGBoost, and FastAPI/MCP transport.

```
       ┌─────────────────────────────────────────────────────────────┐
       │              HOST PERSISTENT VOLUME: ./data                 │
       │  • security.db (PBKDF2 Keys & Rate Limits)                  │
       │  • agent_memory.sqlite (Hindsight Episodic Memory)          │
       │  • lookup_cache.sqlite (Geocoding & Edge Cache)             │
       │  • prediction_history.csv (Out-of-Time Prediction Ledger)   │
       │  • intraday_events.json & evaluated_headlines.json          │
       │  • finlight_quota.json & firecrawl_quota.json               │
       └──────────────────────────────┬──────────────────────────────┘
                                      │  Mount: -v $(pwd)/data:/app/data
                                      ▼
       ┌─────────────────────────────────────────────────────────────┐
       │             MIDGLEY CONTAINER (PORT 8000)                   │
       │  • FastAPI REST Server & Model Inference Pipeline           │
       │  • MCP Standard Model Context Protocol Server               │
       │  • Automatic SQLite Schema Bootstrap on Fresh Mount         │
       └─────────────────────────────────────────────────────────────┘
```

### Docker Quick Start with Persistent Host Volume

```bash
# 1. Pull the pinned release container image
docker pull ghcr.io/koshiirra/midgley:v0.6.8

# 2. Ensure host data directory exists
mkdir -p data backups

# 3. Run container with persistent volume mount (Issue #375)
docker run -d \
  --name midgley \
  --restart unless-stopped \
  -p 8000:8000 \
  -v $(pwd)/data:/app/data \
  -e GEMINI_API_KEY="AIzaSy..." \
  -e FINLIGHT_API_KEY="fl_live_..." \
  -e MIDGLEY_ADMIN_SECRET="sec_admin_secret_here" \
  ghcr.io/koshiirra/midgley:v0.6.8

# 4. Verify unauthenticated API server health
curl http://localhost:8000/health

# 5. Verify authenticated functional prediction route
curl -H "X-API-Key: $MIDGLEY_API_KEY" "http://localhost:8000/api/v1/forecast/predict?locale=national"
```

### Docker Compose Configuration (`docker-compose.yml`)

```yaml
version: '3.8'

services:
  midgley:
    image: ghcr.io/koshiirra/midgley:v0.6.8
    container_name: midgley
    restart: unless-stopped
    ports:
      - "8000:8000"
    volumes:
      - ./data:/app/data
    environment:
      - GEMINI_API_KEY=${GEMINI_API_KEY}
      - FINLIGHT_API_KEY=${FINLIGHT_API_KEY}
      - MIDGLEY_ADMIN_SECRET=${MIDGLEY_ADMIN_SECRET}
      - MIDGLEY_ENABLED_REGIONS=national,tulsa,newark,cincinnati,greenville,charlotte,oakland,port_st_lucie
    healthcheck:
      test: ["CMD", "curl", "-f", "http://localhost:8000/health"]
      interval: 30s
      timeout: 5s
      retries: 3
      start_period: 10s
```

### Durable Container State Inventory

The container writes all persistent application state into `/app/data`. When mounted to the host via `-v $(pwd)/data:/app/data`, all records remain durable across container upgrades:

| Path on Host / Container | Storage Engine | Purpose & Operator Impact |
| :--- | :--- | :--- |
| `data/security.db` | SQLite 3 | Stores PBKDF2 hashed API keys, roles, and rate limit counters. |
| `data/agent_memory.sqlite` | SQLite 3 + FTS5 | Stores episodic memory vectors and qualitative root-cause reflections. |
| `data/lookup_cache.sqlite` | SQLite 3 | Stores geocoding results, HTTP cache responses, and EIA vintages. |
| `data/prediction_history.csv` | CSV Ledger | Continuous historical record of 5-day out-of-time forecasts and actuals. |
| `data/intraday_events.json` | JSON Ledger | Deduplication ledger and audit log of evaluated breaking news shocks. |
| `data/evaluated_headlines.json` | JSON Ledger | 24-hour headline hash deduplication ledger. |
| `data/finlight_quota.json` | JSON Ledger | Monthly and daily API quota counter for `finlight.me` (150 call limit). |
| `data/firecrawl_quota.json` | JSON Ledger | Monthly and daily API quota counter for `firecrawl.dev` (800 call limit). |
| `data/telemetry_alerts.json` | JSON Ledger | Active MLOps model degradation threshold alerts. |
| `data/fallback_telemetry.json` | JSON Ledger | Cumulative token and dollar savings from Tier 3 offline lexicon fallbacks. |

### Empty Volume Bootstrap Lifecycle

When launching a container with an empty host volume (e.g. fresh `./data` folder):
1. **KeyManager Bootstrap:** Automatically executes schema migrations, creating `api_keys` and `rate_limits` tables in `data/security.db`.
2. **Episodic Memory Bootstrap:** Initializes `memories` table with FTS5 virtual tables and Porter stemming tokenizer in `data/agent_memory.sqlite`.
3. **Lookup Cache Bootstrap:** Initializes key-value HTTP cache tables in `data/lookup_cache.sqlite`.
4. **Prediction History Bootstrap:** Generates standard CSV headers with full 8-dimensional MLOps attribution fields on first forecast run.
5. **Quota Safety Valves:** Initializes zeroed JSON ledgers with statutory safety caps.
6. **Regional Metadata:** Regional driver profiles reside within the versioned application image (`data/regional_metadata/`) and fall back cleanly if customized profiles are omitted.

### Online Backup Runbook

Execute atomic, zero-downtime backups of live SQLite databases and flat-file ledgers on the host:

```bash
# 1. Create timestamped backup destination
BACKUP_DATE=$(date +%F_%H%M%S)
mkdir -p backups/${BACKUP_DATE}

# 2. Atomic online SQLite database snapshots
sqlite3 data/security.db ".backup 'backups/${BACKUP_DATE}/security.db'"
sqlite3 data/agent_memory.sqlite ".backup 'backups/${BACKUP_DATE}/agent_memory.sqlite'"
if [ -f data/lookup_cache.sqlite ]; then
  sqlite3 data/lookup_cache.sqlite ".backup 'backups/${BACKUP_DATE}/lookup_cache.sqlite'"
fi

# 3. Archive prediction logs and JSON deduplication ledgers
tar -czf backups/${BACKUP_DATE}/midgley_ledgers.tar.gz data/*.csv data/*.json

echo "Backup completed successfully at backups/${BACKUP_DATE}"
```

### Restore & Stateful Rollback Runbook

If rolling back a deployment or restoring from disaster:

```bash
# 1. Stop and remove the active container
docker stop midgley && docker rm midgley

# 2. Restore databases and ledgers from backup snapshot
RESTORE_DATE="2026-09-23_120000"
sqlite3 data/security.db ".restore 'backups/${RESTORE_DATE}/security.db'"
sqlite3 data/agent_memory.sqlite ".restore 'backups/${RESTORE_DATE}/agent_memory.sqlite'"
tar -xzf backups/${RESTORE_DATE}/midgley_ledgers.tar.gz -C .

# 3. Pin and run the target release image
docker run -d \
  --name midgley \
  --restart unless-stopped \
  -p 8000:8000 \
  -v $(pwd)/data:/app/data \
  --env-file .env \
  ghcr.io/koshiirra/midgley:v0.6.8

# 4. Verify API recovery
curl http://localhost:8000/health
curl http://localhost:8000/api/v1/system/quota
```

---

## 5. Standalone Linux Server & VM Deployment

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
Execute the full multi-region prediction pipeline (which runs National Wholesale RBOB futures, Tulsa, Newark, Cincinnati, Greenville, Charlotte, Oakland, Port St. Lucie, regional diesel engines, and generates the public web dashboard):
```bash
python3 run_all.py --use-llm-api
```

> [!NOTE]
> If you wish to run only the standalone National Wholesale RBOB model without calibrating regional metros, execute `python3 -m src.locations.national.main --use-llm-api`. Note that `--use-llm-api` is the canonical CLI flag (the `--llm` flag is deprecated and ignored). If `GEMINI_API_KEY` is omitted, `--use-llm-api` gracefully routes event scoring to the zero-cost Tier 3 offline lexicon.

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

## 6. Systemd Services & Automated Timer Schedules

To run Midgley 24/7 on a Linux machine with automated background execution, set up `systemd` user services and timers.

### Process Concurrency & Advisory Lock Barrier (Issue #425)

Scheduled execution units (`midgley-daily-forecast`, `midgley-intraday-polling`, and `midgley-weekly-review`) serialize access to the `data/` directory using an advisory lock barrier (`flock` on file descriptor 9):
```bash
LOCK="${XDG_RUNTIME_DIR:-/tmp}/midgley-data.lock"
exec 9>"$LOCK"
if ! flock -w 900 9; then
    echo "midgley: timed out waiting for data lock" >&2
    exit 75   # EX_TEMPFAIL
fi
```
* **Timeout & Queueing:** Run scripts queue behind active jobs for up to 900 seconds (15 minutes). If a lock acquisition times out, the runner exits with code `75` (`EX_TEMPFAIL`), signalling transient failure rather than terminal corruption.
* **Timer Jitter (`RandomizedDelaySec=120`):** All timers include a 120-second randomized jitter window to prevent simultaneous execution spikes across overlapping cron events or following system cold boots.
* **Intraday Timer Offset (`*:7/15`):** The intraday poller triggers on the 7th minute past each quarter hour (`:07`, `:22`, `:37`, `:52`), eliminating collisions with daily (07:00 UTC) and weekly (13:00 UTC) pipelines.

---

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
ExecStart=/home/marty/projects/midgley/scripts/run_local_daily_forecast.sh
EnvironmentFile=/home/marty/projects/midgley/.env
```

**`midgley-daily-forecast.timer`:**
```ini
[Unit]
Description=Run Midgley Daily Gas Price Forecast at 02:00 AM Central / 07:00 UTC

[Timer]
OnCalendar=*-*-* 07:00:00 UTC
RandomizedDelaySec=120
Persistent=true

[Install]
WantedBy=timers.target
```

### 4. Intraday Event Polling Timer (`~/.config/systemd/user/midgley-intraday-polling.service` & `.timer`)

**`midgley-intraday-polling.service`:**
```ini
[Unit]
Description=Midgley Intraday Event Polling & Anomaly Monitor
After=network.target

[Service]
Type=oneshot
WorkingDirectory=/home/marty/projects/midgley
ExecStart=/home/marty/projects/midgley/scripts/run_local_intraday_polling.sh
EnvironmentFile=/home/marty/projects/midgley/.env
```

**`midgley-intraday-polling.timer`:**
```ini
[Unit]
Description=Run Midgley Intraday Event Polling Every 15 Minutes (Offset :07/:22/:37/:52)

[Timer]
OnCalendar=*:7/15
RandomizedDelaySec=120
Persistent=true

[Install]
WantedBy=timers.target
```

### 5. Weekly Model Review Timer (`~/.config/systemd/user/midgley-weekly-review.service` & `.timer`)

**`midgley-weekly-review.service`:**
```ini
[Unit]
Description=Midgley Weekly Model Performance Review & Issue Self-Audit
After=network.target

[Service]
Type=oneshot
WorkingDirectory=/home/marty/projects/midgley
ExecStart=/home/marty/projects/midgley/scripts/run_local_weekly_review.sh
EnvironmentFile=/home/marty/projects/midgley/.env
```

**`midgley-weekly-review.timer`:**
```ini
[Unit]
Description=Run Midgley Weekly Review Every Saturday at 08:00 AM Central / 13:00 UTC

[Timer]
OnCalendar=Sat *-*-* 13:00:00 UTC
RandomizedDelaySec=120
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
systemctl --user enable --now midgley-intraday-polling.timer
systemctl --user enable --now midgley-weekly-review.timer

# Check active status
systemctl --user list-timers
```

---

## 7. Cloud & GitHub Actions Self-Hosting (Fork Deployment)

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
3. **Configure GitHub Pages (Issue #378):**
   - Navigate to **Settings -> Pages**.
   - Under **Build and deployment**, set **Source** to `GitHub Actions`.
   - The repository uses modern Pages Artifact deployment (`actions/configure-pages@v6`, `actions/upload-pages-artifact@v5`, `actions/deploy-pages@v5`) in `.github/workflows/gas_price_forecast.yml`.
   - *Do NOT select "Deploy from a branch", as that legacy mechanism conflicts with the artifact workflow.*

### Dual-Tier Intraday Monitoring Architecture

Midgley uses a resilient dual-tier architecture for intraday headline monitoring:
- **Tier 1 (Primary — 15-minute Edge Polling):** Cloudflare Worker cron (`workers/intraday_monitor_worker.ts`) executing on a `*/15 * * * *` schedule. Ingests free RSS feeds, evaluates price impact, dispatches real-time Discord Embed alerts, and triggers a repository dispatch when thresholds are tripped.
- **Tier 2 (Fallback — 2-hour Scheduled Runner):** GitHub Actions workflow (`.github/workflows/intraday_event_monitor.yml`) running on a `0 */2 * * *` schedule. Provides reliable scheduled execution and processes incoming webhook push dispatches.

### Master Workflow Cron Schedule Matrix

All workflow triggers in `.github/workflows/` evaluate strictly against UTC. The table below provides the exact schedule mappings:

| Workflow Name | Workflow File | Cron Expression | UTC Time | US Central Time (CDT / CST) | US Eastern Time (EDT / EST) | Purpose |
| :--- | :--- | :--- | :--- | :--- | :--- | :--- |
| **Daily Gas Price Forecast** | `.github/workflows/gas_price_forecast.yml` | `17 7 * * *` | 07:17 UTC | 02:17 AM CDT / 01:17 AM CST | 03:17 AM EDT / 02:17 AM EST | Full multi-region forecasting & Pages deployment |
| **Weekly Model Review** | `.github/workflows/weekly_model_review.yml` | `12 13 * * 6` | Sat 13:12 UTC | Sat 08:12 AM CDT / 07:12 AM CST | Sat 09:12 AM EDT / 08:12 AM EST | Saturday performance audit & Hindsight reflection |
| **Intraday Fallback Monitor** | `.github/workflows/intraday_event_monitor.yml` | `0 */2 * * *` | Every 2 hours | Every 2 hours | Every 2 hours | 2-hour fallback RSS polling & webhook gateway |
| **Nightly Dev Release** | `.github/workflows/nightly_dev_release.yml` | `0 8 * * *` | 08:00 UTC | 03:00 AM CDT / 02:00 AM CST | 04:00 AM EDT / 03:00 AM EST | Automated nightly development snapshot release |
| **Edge Intraday Monitor** | `workers/intraday_monitor_worker.ts` | `*/15 * * * *` | Every 15 min | Every 15 min | Every 15 min | Primary edge headline evaluation & Discord alerts |

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

### Step 5: Register Locale Mapping & Metadata (`src/dynamic_region.py` & `src/api_server.py`)
Add `"chicago"` to `LOCALE_MAP` and `PADD_METADATA` in `src/dynamic_region.py` and register the route handler in `src/api_server.py`:
```python
# In src/dynamic_region.py:
LOCALE_MAP["chicago"] = "Chicago_IL"
LOCALE_MAP["Chicago_IL"] = "chicago"

# In src/api_server.py:
LOCALE_MAP["chicago"] = "Chicago_IL"
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

### Step 8: Connect MLOps Prediction Tracker & Backfilling (`src/prediction_logger.py`)
Update `src/prediction_logger.py` to include `"Chicago_IL"` in target price columns and historical test-split backfilling (`backfill_new_region_history`).

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

### 10. Verify PortWatch Shipping & CARB Compliance Connectors (Issues #384 & #383)
Run diagnostic probes to verify IMF PortWatch maritime activity and CARB regulatory carbon compliance calculations:
```bash
# Verify IMF PortWatch maritime chokepoint transit telemetry
python3 -c "from src.portwatch_connector import IMFPortWatchConnector; c = IMFPortWatchConnector(); print(c.get_global_chokepoint_risk_summary())"

# Verify CARB LCFS and Cap-and-Trade dynamic compliance fee breakdown
python3 -c "from src.carb_compliance import get_dynamic_carb_compliance_breakdown; print(get_dynamic_carb_compliance_breakdown())"
```

### 11. Verify Gulf Coast Refinery Outage Telemetry & Attribution (Issue #406)
Verify unified TCEQ, LDEQ, and NRC emission and outage data ingestion and run attribution reports:
```bash
python3 -c "from src.tceq_emissions import get_unified_gulf_coast_outages; df = get_unified_gulf_coast_outages(); print(f'Total outages logged: {len(df)}')"
python3 -c "from src.weekly_issue_reporter import format_refinery_outage_attribution_markdown; print(format_refinery_outage_attribution_markdown(30))"
```

### 12. Execute 5-Tier Nested Model Evaluation Hierarchy (Issue #362)
Execute formal 5-tier nested baseline hierarchy evaluations with Diebold-Mariano and block bootstrap across all hubs and horizons:
```bash
python3 scripts/evaluate_model_hierarchy.py --all-locales --horizons 1,2,3,4,5 --format all --output data/model_hierarchy_evaluation.json
```

---

*Midgley Version: `v0.7.0` | Engine: Gemini 2.5 Flash + Ridge (α=10.0) | License: Apache 2.0*


