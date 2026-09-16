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
* **Use Cases:** Live counterfactual shock simulations (`POST /api/v1/forecast/simulate`), API key provisioning (`/api/v1/admin/keys`), incoming webhook ingestion, and interactive AI agent MCP tools.
* **Alternative & Physical Data Standards:**
  - **Dynamic Ingestion & Bitemporal Tracking:** Physical and qualitative feeds (Baker Hughes rig counts, Executive Social Media posts, Key Market Movers statements, EIA PADD balances, EIA-930 grid stress, USDA biofuel costs, EIA state/metro retail surveys, FERC Form 6 tariffs, USACE Lock delays, BSEE offshore shut-ins, Geopolitical/Maritime chokepoint feeds, State Energy Agency surveys, CFTC COT positioning, NOAA NHC hurricanes, Energy Equities, and Regional Intraday Event streams) MUST store observation snapshots with `as_of` publication timestamps in `data/*_vintages.json` to eliminate lookahead bias in historical backtests.
  - **Lookup Caching:** Cache external lookups in `global_cache` (`src/lookup_cache.py`) with appropriate TTLs (15m for social/weather/key movers/geopolitical, 1h for NHC hurricanes, 4h-6h for grid/locks, 12h for BSEE shut-ins, 24h for daily equities/indices, 7d for weekly releases/CFTC/surveys/tariffs).

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

## 📝 6. Documentation Synchronization Mandate

Whenever new features, regional models, data feeds, or API endpoints are added:
1. Update **`AGENTS.md`** to reflect modified or new agent roles.
2. Update **`API.md`** with endpoint specifications, query parameters, and example JSON payloads.
3. Update **`ARCHITECTURE.md`** with mathematical formulations, vector layouts, or data flow changes.
4. Update **`README.md`** with current status badges, supported metros, and quick-start instructions.
5. Synchronize changes to the official GitHub Wiki (`https://github.com/KoshiirRa/midgley.wiki.git`).
