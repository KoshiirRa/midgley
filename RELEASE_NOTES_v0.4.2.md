# Release Notes - v0.4.2

**Release Date:** September 4, 2026  
**Build Target:** `dev-vm` (`10.42.42.54`)  
**Git Branch:** `dev`  

---

## 🚀 Key Features, Bug Fixes & Architectural Enhancements

### 1. Tulsa AAA Scraper Bug Fix & `py-gasbuddy` Integration (Issue #206)
- **GraphQL Fuel Data Ingestion:** Integrated `py-gasbuddy` GraphQL client (`py-gasbuddy>=0.7.1`) in [`src/live_fuel_feed.py`](file:///c:/Users/concentus/Documents/Random%20Ideas%20-%20LLM%20Unleaded%20Gas%20Price%20Prediction%20Modelling/src/live_fuel_feed.py) to resolve HTML structure changes in AAA state average scrapers.
- **Robust Fallback Chain:** Establishes resilient live pump pricing lookups for Tulsa metro and state-level averages with seamless GasBuddy station telemetry fallbacks.

### 2. Baker Hughes Ingestion & Feature Matrix Fix (Issue #203)
- **NameError Resolution:** Fixed `UnboundLocalError`/`NameError` in [`src/alternative_data_feeds.py`](file:///c:/Users/concentus/Documents/Random%20Ideas%20-%20LLM%20Unleaded%20Gas%20Price%20Prediction%20Modelling/src/alternative_data_feeds.py) during Baker Hughes rig count processing.
- **Feature Matrix Alignment:** Preserves drilling rig count features (`baker_hughes_total_rigs`, `baker_hughes_oil_rigs`) in [`src/feature_engineering.py`](file:///c:/Users/concentus/Documents/Random%20Ideas%20-%20LLM%20Unleaded%20Gas%20Price%20Prediction%20Modelling/src/feature_engineering.py), preventing feature drops during baseline quantitative model execution.

### 3. GitHub Actions CI Runner & Node Deprecation Upgrades (Issue #202)
- **Workflow Modernization:** Upgraded Node.js runner environments across all GitHub Actions workflows (`deploy_cloudflare_worker.yml`, `docker_publish.yml`, `gas_price_forecast.yml`, `intraday_event_monitor.yml`, `nightly_dev_release.yml`, `sync_self_hosted.yml`, `weekly_model_review.yml`).
- **Runner Warning Elimination:** Resolves Node 20 runner deprecation warnings, aligning CI automation with supported Node 22/24 execution standards.

### 4. Dynamic Region Runner & Regional Metro Calibration Engine
- **Flexible Metro Profiles ([`src/dynamic_region.py`](file:///c:/Users/concentus/Documents/Random%20Ideas%20-%20LLM%20Unleaded%20Gas%20Price%20Prediction%20Modelling/src/dynamic_region.py)):** Implemented `DynamicRegionRunner` class enabling programmatic instantiation and execution of custom regional metro forecasting pipelines.
- **CLI Region Management ([`scripts/manage_regions.py`](file:///c:/Users/concentus/Documents/Random%20Ideas%20-%20LLM%20Unleaded%20Gas%20Price%20Prediction%20Modelling/scripts/manage_regions.py)):** Created CLI tool to list, add, and evaluate dynamic metro profiles with custom PADD allocations, ZIP anchors, and local tax policies.

### 5. Dynamic Release Banner Version Binding
- **Version Parity ([`src/dashboard_generator.py`](file:///c:/Users/concentus/Documents/Random%20Ideas%20-%20LLM%20Unleaded%20Gas%20Price%20Prediction%20Modelling/src/dashboard_generator.py)):** Bound public web dashboard release headers dynamically to package version (`midgley.__version__`) and environment overrides (`MIDGLEY_BRANCH` / `MIDGLEY_VERSION`), eliminating hardcoded version text drift.

---

## 🧪 Verification & Test Suite Results

- **Full Test Suite Execution on `dev-vm` (`10.42.42.54`):**
  ```bash
  PYTHONPATH=. pytest
  ```
  **Result:** `286 passed in 586.70s` (100% pass rate across all 58 test modules).

---

## 📋 Closed & Superseded GitHub Issues
- **Issue #202**: `fix(ci): Upgrade Node environment settings & resolve Node 20 runner deprecation warnings` (Closed as completed)
- **Issue #203**: `fix(ingestion): Resolve Baker Hughes NameError and feature matrix drop` (Closed as completed)
- **Issue #206**: `fix(scraping): Resolve Tulsa AAA state average scraper bug & integrate py_gasbuddy GraphQL feeds` (Closed as completed)
