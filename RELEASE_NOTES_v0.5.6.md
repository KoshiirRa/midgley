# Release Notes - v0.5.6

**Release Date:** September 16, 2026  
**Build Target:** `dev-vm` (`10.42.42.54`)  
**Git Branch:** `main`  

---

## 🚀 Key Features, Architectural Enhancements & Algorithmic Upgrades

### 1. Automated Weekly Historical Benchmark & Fallback Refresh Pipeline (Issue #297)
- **Unified Benchmark Orchestrator ([`src/benchmark_updater.py`](file:///src/benchmark_updater.py)):**
  - Designed and deployed a resilient **3-Tier Fallback Architecture** across all 10 registered quantitative data connectors:
    - **Tier 1 (Live Open API):** Real-time API query (FRED, EIA, USGS, Open-Meteo, Census, Treasury Fiscal Data, SEC EDGAR, OilpriceAPI, RSS feeds).
    - **Tier 2 (Weekly Persisted Historical Benchmark):** Dynamic persisted JSON artifact (`data/*_historical.json`) capturing the most recent Friday market closes and weekly benchmark datasets with publication metadata (`updated_at`, `record_count`, `source`).
    - **Tier 3 (Static In-Memory Baseline):** Immutable Python constants (`HISTORICAL_*`, `*_BASE_ANCHORS`) providing a guaranteed 100% offline, air-gapped safety net with zero downtime.
  - Implemented `save_historical_benchmark(key, data)` with atomic JSON persistence and `load_historical_benchmark(key)` with corrupted JSON recovery.
  - Implemented `HistoricalBenchmarkManager` with registered refresh handlers:
    - `baker_hughes`: Baker Hughes rotary drilling rig counts (`data/baker_hughes_historical.json`).
    - `executive_social`: Executive social media commentary (`data/executive_social_historical.json`).
    - `geopolitical`: Maritime chokepoint events (`data/geopolitical_historical.json`).
    - `key_movers`: Key market movers statements (`data/key_movers_historical.json`).
    - `diesel`: Regional retail ULSD diesel pump prices & crack spreads (`data/diesel_historical.json`).
    - `treasury`: U.S. Treasury 10Y-2Y yield curve spreads & 10Y TIPS real yields (`data/treasury_historical.json`).
    - `usgs_water`: USGS river stage heights & streamflow telemetry (`data/usgs_water_historical.json`).
    - `usgs_seismic`: USGS earthquake events & corridor risk indices (`data/usgs_seismic_historical.json`).
    - `census_demographics`: Census ACS demographic profiles (`data/census_demographics_historical.json`).
    - `oilpriceapi`: Spot commodity futures prices (`data/oilpriceapi_historical.json`).
- **Weekly Automation Integration ([`src/weekly_issue_reporter.py`](file:///src/weekly_issue_reporter.py)):**
  - Integrated `refresh_all_historical_benchmarks()` directly into the automated Saturday morning model review workflow (`.github/workflows/weekly_model_review.yml`).
  - Automatically commits refreshed JSON benchmarks back to the repository via `git-auto-commit-action`.
  - Embeds benchmark verification telemetry into the weekly markdown review report.
- **Dedicated Test Suite ([`tests/test_benchmark_updater.py`](file:///tests/test_benchmark_updater.py)):**
  - 65/65 unit and integration tests passing covering atomic persistence, schema integrity, connector handlers, and orchestrator execution passes.

---

### 2. Dynamic Versioning, Model Badging, and Git Tag Auto-Discovery Engine (Issue #298)
- **Single Source of Truth Versioning Engine ([`src/version.py`](file:///src/version.py)):**
  - Implemented `get_version()` with a robust 5-tier resolution hierarchy:
    1. `MIDGLEY_VERSION` environment variable override (e.g. CI/CD matrix releases).
    2. Dynamic Git tags via `git describe --tags --abbrev=0` (or `git tag -l "v*"` sorted semver).
    3. Root filesystem scan for `RELEASE_NOTES_v*.md` files, parsing the latest SemVer tag.
    4. `pyproject.toml` project package version.
    5. Fallback constant `FALLBACK_PACKAGE_VERSION = "0.5.6"`.
  - Implemented `get_model_version()` resolving the active quantitative machine learning model (`v1.6 Ipatieff`):
    1. `MIDGLEY_MODEL_VERSION` environment variable override.
    2. `src.__model_version__` package attribute.
    3. Fallback constant `FALLBACK_MODEL_VERSION = "v1.6 Ipatieff"`.
  - Implemented branch detection with `get_git_branch()` and `is_release_branch()`, supporting local Git inspection and GitHub Actions CI environment variables (`GITHUB_REF_NAME`, `MIDGLEY_BRANCH`).
- **UI Header & Navigation Badging ([`src/dashboard_generator.py`](file:///src/dashboard_generator.py) & [`src/sources_generator.py`](file:///src/sources_generator.py)):**
  - **Dynamic Model Pill Badge:** Replaced legacy hardcoded strings with `get_model_badge()` rendering a blue pill badge (`Model v1.6 Ipatieff` / `bg-blue-500/20 text-blue-400 border border-blue-500/30`).
  - **Dynamic Release vs. Dev Badge:** Updated `get_release_badge()` to dynamically render:
    - `Release v{version}` in orange (`bg-orange-500/20 text-orange-400 border border-orange-500/30`) when on `main` or release branches.
    - `Dev Branch v{version}-dev` in amber (`bg-amber-500/20 text-amber-400 border border-amber-500/30`) when on `dev` or feature branches.
  - Replaced hardcoded version footers and mathematical methodology guide descriptions across all 18+ public web application templates.
- **REST API & Predictor Synchronization ([`src/api_server.py`](file:///src/api_server.py) & [`src/prediction_logger.py`](file:///src/prediction_logger.py)):**
  - FastAPI application metadata `version` dynamically initialized via `get_version()`.
  - `GET /health` endpoint exposes dynamic `version` and `model_version` fields.
  - All endpoint JSON responses dynamically declare `"system": f"Midgley {get_model_version()}"`.
  - Prediction logger default model identifier dynamically resolves to `get_model_version().replace(" ", "-")`.
- **CI/CD Full Git History Fetch ([`.github/workflows/gas_price_forecast.yml`](file:///.github/workflows/gas_price_forecast.yml)):**
  - Added `fetch-depth: 0` to `actions/checkout@v7` and passed `MIDGLEY_BRANCH: ${{ github.ref_name }}` to ensure Git tags and branch context are available during automated dashboard builds.

---

## 🧪 Comprehensive Test Suite & Validation

- **Execution Target:** Local dedicated Linux VM (`dev-vm` / `10.42.42.54`).
- **Newly Added Unit Test Suites:**
  - `tests/test_benchmark_updater.py` (65/65 tests passed in 4.12s)
  - `tests/test_version.py` (8/8 tests passed in 2.06s)
- **Full Repository Test Suite Execution:**
  - **Status:** **579 passed, 3 skipped, 0 failed** in 721.25s (12m 01s).
  - **Test Pass Rate:** 100%.

---

## 📋 Closed & Remediated GitHub Issues

- **[Issue #297](https://github.com/KoshiirRa/midgley/issues/297):** feat(mlops): Implement Automated Weekly Historical Benchmark & Fallback Refresh Pipeline across All Quantitative Data Feeds.
- **[Issue #298](https://github.com/KoshiirRa/midgley/issues/298):** feat(dashboard): Implement Dynamic Versioning, Model Badging, and Git Tag Auto-Discovery Engine across Public Web App and API.

---

## 📚 Documentation & Wiki Enhancements

1. **`midgley.wiki` ([`Data-Ingestion-and-APIs.md`](https://github.com/KoshiirRa/midgley/wiki/Data-Ingestion-and-APIs)):**
   - Added **Section 69: Automated Weekly Historical Benchmark & Fallback Refresh Engine**, documenting the 3-tier fallback architecture, atomic persistence schema, and Saturday morning review schedule.
2. **`midgley_wiki_local` ([`Environment-State-and-Dev-vs-Prod.md`](file:///midgley_wiki_local/Environment-State-and-Dev-vs-Prod.md)):**
   - Added **Section 7: Dynamic Versioning & Single Source of Truth Engine**, documenting the 5-tier resolution hierarchy, dynamic model badging, and branch detection.
