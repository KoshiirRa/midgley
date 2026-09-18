# Release Notes - v0.6.5

**Release Date:** September 18, 2026  
**Build Target:** `dev-vm` (`10.42.42.54`) & Cloudflare Edge  
**Git Branch:** `dev`  

---

## 🚀 Overview & Release Highlights

Midgley **v0.6.5** synchronizes the static JSON API pipeline feeds with automated execution workflows, improves forecast delta resolution for downstream clients, and reconciles real-time price alignment across web dashboards and mobile clients:

1. **Automated Static API Feeds Synchronization (`src/static_api_exporter.py` & `src/dashboard_generator.py`):**
   - Hooked `export_all_static_api_endpoints()` directly into `generate_public_dashboard()` and `run_all.py` so that all static JSON payloads under `docs/api/v1/*.json`, `docs/api/v1/combined_*.json`, and `docs/api/v1/combined/*.json` are regenerated automatically whenever the pipeline or web dashboard runs.
   - Fixed stale API feeds on GitHub Pages that previously served historical cached baseline prices to mobile applications.

2. **Dynamic Forecast Delta Resolution & 5-Day Trajectory Generation (`src/api_server.py`):**
   - Updated `_get_forecast_impl` to read the latest trained model forecast deltas from `data/prediction_history.csv` across all modeled regional calibration hubs.
   - Added smooth 5-day step-ahead trajectory interpolation fields (`day_1_price` through `day_5_price`) in the forecast payload for mobile app UI rendering.

3. **Static JSON Feeds Baseline Refresh (`docs/api/v1/`):**
   - Re-exported all 9 regional static API files reflecting active retail pump prices ($4.01/gal for Tulsa, $4.361/gal for Newark, $4.500/gal for Cincinnati, $6.131/gal for Oakland, etc.).

---

## 🧪 Verification & Test Suite Matrix

- **Execution Target:** Dedicated Linux VM (`dev-vm` / `10.42.42.54`).
- **Test Suite Results:**
  - `tests/test_dashboard_generator.py` (22/22 tests passing)
  - `tests/test_api_server.py` (18/18 tests passing)
  - Static JSON export validated across all 9 regional metro hubs.

---

## 📋 Upgrading

To update on the **dev** branch:

```bash
git fetch origin
git checkout dev
git pull origin dev
```
