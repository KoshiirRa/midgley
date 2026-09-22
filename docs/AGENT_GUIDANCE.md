# Midgley Agent & Developer Guidance (`docs/AGENT_GUIDANCE.md`)

This document establishes operational directives, architectural standards, and workflow protocols for AI coding assistants (Antigravity, Aider, Codex) and human developers maintaining the **Midgley Fuel Intelligence Ecosystem**.

---

## 🏛️ 1. Architecture & Ecosystem Overview

The Midgley ecosystem consists of three tightly coupled components:

```
┌─────────────────────────────────────────────────────────────────────────────────┐
│                          1. MIDGLEY CORE REPOSITORY                             │
│                           (KoshiirRa/midgley)                                  │
│  • Multi-Agent Quantitative Forecasting Engine (Ridge/XGBoost + Event Fusion)    │
│  • NOAA Weather Models, Finlight News, Waterway & Physical Feeds               │
│  • Static API Exporter (docs/api/v1/*.json) & Public Web Dashboard (docs/)     │
│  • Dynamic FastAPI Server & Model Context Protocol (MCP) Gateway                │
└───────────────────────┬──────────────────────────────────┬──────────────────────┘
                        │                                  │
                        │ Static JSON Feeds                │ Dynamic REST/MCP
                        ▼                                  ▼
┌─────────────────────────────────────────────────┐  ┌────────────────────────────┐
│      2. AUTOMOTIVE COMPANION APP                │  │    3. EDGE WORKERS & MCP   │
│         (KoshiirRa/midgley-auto)                │  │ (workers/ & src/mcp_server)│
│  • Native Android Automotive OS & Android Auto  │  │ • Cloudflare Queue Buffer  │
│  • 3-Tier Gateway Selector (CDN / Cloud / LAN)  │  │ • D1 Edge Cache Gateway    │
│  • OBD-II PID 0x2F Fuel Telemetry & Overrides   │  │ • Prometheus Metrics Stream│
│  • 6-Hour Resilient Offline Caching             │  │ • MCP Agent Tool Provider  │
└─────────────────────────────────────────────────┘  └────────────────────────────┘
```

---

## 🐧 2. Dev VM Directives & Execution Standards

All agent sessions MUST adhere to the dedicated local Linux development environment:

### Specifications
* **Host**: `dev-vm` (`10.42.42.54`), Ubuntu 26.04 LTS on hypervisor `LAB-HOST` (`10.42.42.26`).
* **SSH User**: `marty@10.42.42.54`
* **Project Directory Root**: `/home/marty/projects/`
* **Core Repositories on Dev VM**:
  - `/home/marty/projects/midgley` (`KoshiirRa/midgley`)
  - `/home/marty/projects/midgley-auto` (`KoshiirRa/midgley-auto`)

### Execution Rules
1. **Dev Offloading:** Always offload Gradle builds, pytest suites, large data processing runs, and model training to `dev-vm` via SSH. Never run heavy JVM compilation or training loops locally on the Windows host.
2. **POSIX Pathing:** Use native Linux POSIX paths (`/home/marty/projects/...`) when operating on `dev-vm`.
3. **Line Endings:** Enforce LF (`\n`) for all scripts, Kotlin files, and Python sources.
4. **No Plaintext Secret Passing:** Never pass raw GitHub tokens inline in CLI commands or environment variables. Rely on system keyrings or pre-configured credentials.

---

## 🌐 3. Multi-Tier API & Zero-Cost CDN Architecture

Midgley enforces a strict **$0 ongoing infrastructure cost** mandate. All agent interactions and client integrations must observe this 3-tier delivery model:

### Tier 1: Zero-Cost Static CDN Feeds (Production Default)
* **Base URL:** `https://koshiirra.github.io/midgley/`
* **Exporter Module:** `src/static_api_exporter.py` (executed via `src/dashboard_generator.py`).
* **Endpoints:**
  - `/api/v1/combined.json` — National commodity benchmark feed.
  - `/api/v1/combined_{locale}.json` — Regional metro feed (e.g. `combined_tulsa.json`).
  - `/api/v1/{locale}.json` & `/api/v1/combined/{locale}.json` — Compatibility route aliases.
* **Characteristics:** 100% SLA uptime, 0 maintenance, served directly by GitHub Pages CDN cache. Ideal for mobile and in-dash head units.

### Tier 2: Cloudflare Edge Cache & Queue Gateway
* **Workers:** `workers/cache_worker.ts` and `workers/intraday_monitor_worker.ts`.
* **Database:** Cloudflare D1 (`midgley-cache-d1`).
* **Queue:** `intraday-event-queue` with dead-letter queue `intraday-event-dlq`.
* **Telemetry:** Axiom log streaming and Sentry cron heartbeat monitoring.

### Tier 3: Dynamic FastAPI & MCP Server
* **Server Module:** `src/api_server.py` and `src/mcp_server.py` managed by `midgley-api.service` on `dev-vm:8000`.
* **Use Cases:** Live counterfactual shock simulations (`POST /api/v1/forecast/simulate`), scenario discovery (`GET /api/v1/forecast/scenarios`), API key provisioning (`/api/v1/admin/keys`), incoming webhook ingestion, and interactive AI agent MCP tools (`simulate_fuel_market_shock`, `list_market_shock_scenarios`).
* **Seasonal & Climatological Plausibility Engine (`src/scenario_engine.py` - Issue #300):**
  - **Dynamic Plausibility Gating:** Classifies scenarios into `ACTIVE_THREAT` (1.0), `SEASONALLY_PLAUSIBLE` (0.70–0.90), `SEASONALLY_DORMANT` (0.10), `EVERGREEN` (0.80), and `PROSPECTIVE_FORWARD` (0.85).
  - **Prospective Forward Precursor Synthesis:** Formulates predictive "What-If" stress tests 1–14 days ahead of reality from leading precursor indicators (NOAA NHC tropical wave outlooks, NOAA SPC convective risk, USGS drought gradients, statutory CARB RVP spec countdowns).
  - **Counterfactual Transparency:** Annotates off-season simulation requests with transparent warnings (`plausibility_warning`) across REST and MCP surfaces.
* **MiroFish Multi-Agent Financial Simulation & Decision Graphs (`src/scenario_simulator.py` - Issue #307):**
  - **Feature Flag Toggle:** Configured via `MIDGLEY_ENABLE_MULTI_AGENT_SIMULATION` (`1` / `true` to enable, `0` / `false` default) and request-level override `enable_cohort_simulation: Optional[bool]` on `POST /api/v1/forecast/simulate` and MCP `simulate_fuel_market_shock`.
  - **Programmatic Status Check:** `from src.scenario_simulator import is_multi_agent_sim_enabled`. Agents, unit tests, and CI jobs should use this helper to determine whether deliberative simulation mode is active.
  - **4-Persona Market Cohort:** Deliberates across `Agent_Refiner` (crude slates/cracks), `Agent_Logistics` (pipeline allocations/river drafts), `Agent_Consumer` (demand elasticity), and `Agent_Macro` (Cboe OVX tail volatility/OPEC+ quotas).
  - **Equilibrium Consensus & Divergence Index:** Quantifies market disagreement ($\sigma$) and computes cross-commodity shock vectors (RBOB $\Delta P$, Distillate HO $\Delta P$, Regional Freight Basis $\Delta B$).
  - **Dashboard Visibility:** Public dashboard headers dynamically render `Multi-Agent Cohort: ON` (purple) vs `Multi-Agent Cohort: OFF` (slate) based on build-time status.
  - **Offline Tier 3 Fallback:** 100% deterministic elasticity matrix ensures zero downtime and $0 cost when LLM API keys are absent.
* **Alternative & Physical Data Standards:**
  - **Dynamic Ingestion & Bitemporal Tracking:** Physical and qualitative feeds (U.S. BTS Freight Transportation Index & Truck Tonnage, Baker Hughes rig counts, Executive Social Media posts, Key Market Movers statements, EIA PADD balances, EIA-930 grid stress, USDA biofuel costs, official U.S. EIA Daily Regional Spot Wholesale Prices, EPA Weekly EMTS RIN Credits, California Energy Commission (CEC) Weekly Fuels Watch, EPA & CARB Reid Vapor Pressure (RVP) Regulatory Standards, NOAA CO-OPS Marine Telemetry, EIA state/metro retail surveys, FERC Form 6 tariffs, USACE Lock delays, BSEE offshore shut-ins, Geopolitical/Maritime chokepoint feeds, State Energy Agency surveys, CFTC COT positioning, NOAA NHC hurricanes, Energy Equities, and Regional Intraday Event streams) MUST store observation snapshots with `as_of` publication timestamps in `data/*_vintages.json` (e.g., `data/bts_vintages.json`, `data/cec_fuels_vintages.json`, `data/noaa_coops_vintages.json`) to eliminate lookahead bias in historical backtests.
  - **Lookup Caching:** Cache external lookups in `global_cache` (`src/lookup_cache.py`) with appropriate TTLs (15m for social/weather/key movers/geopolitical, 1h for NHC hurricanes, 2h for NOAA CO-OPS marine levels, 4h-6h for grid/locks, 12h for BSEE shut-ins, 24h for daily equities/indices, 7d for weekly releases/CFTC/surveys/tariffs/BTS TSI/CEC fuels).

---

## 🚗 4. Automotive App (`midgley-auto`) Guidelines

When modifying or extending the Android companion application:

1. **Schema Synchronization:** Any modification to `CombinedApiResponse` in `midgley` MUST be mirrored in Kotlinx Serializable models in `midgley-auto` (`app/src/main/java/net/n2yti/midgley/auto/data/models/CombinedModels.kt`).
2. **Dual-Mode Network Layer:** Ensure `MidgleyRepository` properly distinguishes between static CDN URLs (`isStaticHost()` checking for `github.io` / `github.com`) and dynamic endpoints.
3. **Offline Resilience:** All network fetches must catch exceptions and gracefully fall back to cached responses or deterministic regional baselines (`generateOfflineFallbackAdvisor()`).
4. **OBD-II Safety Precedence:** In-dash fill-up recommendations must respect the low-fuel safety reserve rule (< 15% tank capacity immediately emits `FILL_NOW` regardless of 5-day price trajectory).
5. **Testing & Releases:** Always run `./gradlew test assembleDebug` on `dev-vm`. Publish new releases to GitHub using `gh release create` with attached `midgley-auto-vX.Y.Z-debug.apk`.

---

## 🧪 5. Testing & Verification Protocols

### Core Python Engine (`midgley`)
```bash
# Run on dev-vm
ssh marty@10.42.42.54 "cd /home/marty/projects/midgley && pytest tests/ -v"
```
* **Quota Safety:** Ensure tests set `TESTING=1` or mock network calls to avoid consuming Gemini LLM tokens or Finlight/Firecrawl API quotas.
* **Test Isolation:** Verify that unit test runs do not pollute persistent stores (`data/intraday_events.json`, `data/evaluated_headlines.json`, or `docs/`).

### Automotive Android App (`midgley-auto`)
```bash
# Run unit tests and assemble APK on dev-vm
ssh marty@10.42.42.54 "cd /home/marty/projects/midgley-auto && ./gradlew test assembleDebug"
```

---

## 🛡️ 6. Security Guardrails & Hardening Directives

AI agents and contributors must strictly enforce the following security protocols:
1. **Zero Shell Command Interpolation (Issue #343):** Never execute dynamic shell commands or subprocess calls with `shell=True` using untrusted remote manifest data or unverified strings. All reconciler and CLI scripts must route operations through strictly allowlisted, parameterized argument vectors (`ALLOWLISTED_ACTIONS`) with HTTPS scheme enforcement.
2. **Fail-Closed Administrative Authentication (Issue #341):** Admin endpoints (e.g. `/api/v1/admin/keys`) must fail closed with `HTTP 401 Unauthorized` if `MIDGLEY_ADMIN_SECRET` is unset, empty, or whitespace. Never provide a fallback or default development secret in production codebase.
3. **Exact Middleware Route Matching (Issue #344):** API authentication and rate-limiting middleware must match root paths exactly (`request.url.path == "/"`) and never exempt subpaths via generic prefix matches like `"/"`. Only explicit public paths (`/docs`, `/redoc`, `/openapi.json`, `/.well-known`, `/health`) may bypass API key verification.

---

## 📈 7. Quantitative Modeling & Temporal Leakage Prevention (Issue #354)

To prevent lookahead bias and synthetic inflation of out-of-time forecasting performance:
1. **No Backward Filling (`bfill`):** Time-series feature pipelines must never use `bfill()` or backward imputation across time-ordered rows. Forward fill missing values using past observations (`ffill()`) and fill remaining leading initializations with neutral defaults (`fillna(0.0)`).
2. **Chronological Boundary Purging:** When partitioning chronological datasets into train/test splits, enforce an $h$-step boundary purge gap (`train_slice_end = max(1, split_idx - forecast_horizon)`). This guarantees that forward-looking targets $y_t = P_{t+h}$ in the training slice cannot leak future test set prices.
3. **Train-Slice Context Routing Diagnostics:** When computing diagnostic metrics (such as target autocorrelation for dynamic routing), calculate statistics exclusively on the training slice rather than across the full dataset.
4. **Purged Cross-Validation for Stacking Ensembles:** Stacking meta-regressors must use partitioned, purged cross-validation (`PurgedGroupTimeSeriesSplit`) with explicit label horizons and embargo gaps ($h \ge 5$) to prevent out-of-fold training contamination.

---

---

## 🎯 8. Headline Arena Benchmarking & Civic Challenge Directives (Issues #182, #408, #418)

When submitting probabilistic forecasts to [Headline Arena](https://headlinearena.com):
1. **Decoupled 24-Hour Pending Cache (`data/headline_arena_pending_forecasts.json`):** Forecasts generated by daily runs are cached with a 24-hour TTL, decoupling pipeline run times from challenge availability windows.
2. **Idempotency Submission Ledger (`data/headline_arena_submitted_ledger.json`):** Tracks challenge IDs that have received predictions, preventing redundant API calls during periodic cron cycles.
3. **Periodic Dispatch (`scripts/sync_headline_arena.py` & `.github/workflows/headline_arena_sync.yml`):** Runs every 30 minutes to match active challenge windows against the 24h pending forecast cache.
4. **EIA Weekly Retail Gasoline Civic Challenges:** Macro / civic challenges use continuous Gaussian probability density scoring (closed-form CRPS) formatted via `format_eia_retail_civic_payload()` with median target ($P_{50}$) and uncertainty standard deviation ($\sigma$).
5. **Reconciled Statutory CARB Tax Breakdown (Issue #400):** California retail gasoline pricing incorporates $0.953/gal state environmental burden ($0.596 state excise + $0.234 Cap-and-Trade + $0.088 LCFS + $0.035 UST/env fees), totaling $1.407/gal all-in statutory tax including 18.4¢ Federal excise and ~27.0¢ local sales tax.

---

## 📝 9. Documentation Synchronization Mandate

Whenever new features, regional models, data feeds, or API endpoints are added:
1. Update **`AGENTS.md`** to reflect modified or new agent roles.
2. Update **`API.md`** with endpoint specifications, query parameters, and example JSON payloads.
3. Update **`ARCHITECTURE.md`** with mathematical formulations, vector layouts, or data flow changes.
4. Update **`README.md`** with current status badges, supported metros, and quick-start instructions.
5. Update **`SELF_HOSTING.md`** with deployment configurations and environment variables.
6. Synchronize changes to the official GitHub Wiki (`https://github.com/KoshiirRa/midgley.wiki.git`).

