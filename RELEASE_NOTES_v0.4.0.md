# Release Notes - v0.4.0

**Release Date:** September 3, 2026  
**Build Target:** `dev-vm` (`10.42.42.54`)  
**Git Branch:** `main`  


---

## 🚀 Key Features & Architectural Enhancements

### 1. CodeCogs Visual LaTeX Math UI & Markdown Fallbacks (Issue #52)
- **Visual Math Generator (`codecogs_url()`):** Implemented URL-encoded CodeCogs SVG equation image generator in [`src/dashboard_generator.py`](file:///c:/Users/concentus/Documents/Random%20Ideas%20-%20LLM%20Unleaded%20Gas%20Price%20Prediction%20Modelling/src/dashboard_generator.py).
- **Markdown & Feed Fallbacks:** Auto-embeds visual SVG equation image tags (`![Exponential Decay Formula](https://latex.codecogs.com/svg.latex?...)`) alongside raw LaTeX notation in `docs/technical_breakdown.md` to guarantee visual math rendering across GitHub Markdown views, mobile readers, RSS feeds, and platforms where client-side KaTeX JavaScript is disabled.

### 2. System Telemetry & Grafana Prometheus Exporter (Issue #107)
- **Prometheus Metrics Engine ([`src/telemetry.py`](file:///c:/Users/concentus/Documents/Random%20Ideas%20-%20LLM%20Unleaded%20Gas%20Price%20Prediction%20Modelling/src/telemetry.py)):** Expanded `format_prometheus_metrics()` to export:
  - TokenTab token consumption & estimated USD costs (`llm_tokens_consumed_total`, `llm_estimated_cost_usd_total`).
  - IPASIS Security checks and blocked requests (`ipasis_security_requests_total`).
  - 3-Tier Cache Gateway operations (`cache_gateway_operations_total` hits vs. misses).
  - API quota remaining ratios (`api_quota_remaining_ratio` for Finlight, OilpriceAPI, AlphaVantage).
- **REST Gateway Exporter ([`src/api_server.py`](file:///c:/Users/concentus/Documents/Random%20Ideas%20-%20LLM%20Unleaded%20Gas%20Price%20Prediction%20Modelling/src/api_server.py)):** Mounted `@app.get("/api/v1/metrics")` as an official route alongside `@app.get("/metrics")` exposing Prometheus text exposition format (`text/plain`).

### 3. Zero-Cost Internet Archive Wayback Machine Cloud Archiver (Issue #197)
- **Wayback Archiver Engine ([`src/wayback_archiver.py`](file:///c:/Users/concentus/Documents/Random%20Ideas%20-%20LLM%20Unleaded%20Gas%20Price%20Prediction%20Modelling/src/wayback_archiver.py)):** Built zero-cost cloud archiving module submitting breaking news, OPEC press releases, and refinery outage URLs to the Internet Archive Save API (`https://web.archive.org/save/{url}`).
- **Event Monitor Hook ([`src/intraday_event_monitor.py`](file:///c:/Users/concentus/Documents/Random%20Ideas%20-%20LLM%20Unleaded%20Gas%20Price%20Prediction%20Modelling/src/intraday_event_monitor.py)):** Automatically archives target article URLs during intraday headline evaluations, attaching the permanent `archive_url` string to event results for logging in `data/intraday_events.json` and system output logs.
- **7-Day Local Cache (`data/wayback_archive_cache.json`):** Deduplicates submission requests to eliminate redundant HTTP calls to the Internet Archive.

---

## 🧪 Verification & Test Suite Results

- **Full Test Suite Execution on `dev-vm` (`10.42.42.54`):**
  ```bash
  PYTHONPATH=. pytest
  ```
  **Result:** `275 passed in 603.97s` (100% pass rate across all 57 test modules).

---

## 📋 Closed & Superseded GitHub Issues
- **Issue #52**: `feat(docs/math): Leverage CodeCogs LaTeX rendering service for equation images across GitHub Markdown & web embeds` (Closed as completed)
- **Issue #97**: `[Feature Request] Deploy Self-Hosted ArchiveBox for Historical News & Event Preservation` (Closed as superseded by #197 zero-cost cloud archiving)
- **Issue #107**: `[Feature Request] Implement System Telemetry & Observability Metrics Engine for Grafana (Token Usage, API Quotas, Latency & Errors)` (Closed as completed)
- **Issue #197**: `[Feature Request] Zero-Cost Internet Archive Wayback Machine Integration for Web Archiving` (Closed as completed)
