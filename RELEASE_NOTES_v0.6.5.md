# Release Notes - v0.6.5

**Release Date:** September 18, 2026  
**Build Target:** `dev-vm` (`10.42.42.54`) & Cloudflare Edge  
**Git Branch:** `main`  

---

## 🚀 Overview & Release Highlights

Midgley **v0.6.5** synchronizes static JSON API pipeline feeds with automated execution workflows, integrates official U.S. Bureau of Transportation Statistics (BTS) physical freight and trucking demand indicators into the quantitative forecasting engine, improves forecast delta resolution for downstream clients, incorporates seasonal and climatological plausibility gating, and introduces MiroFish multi-agent deliberative financial simulation.

---

### 1. U.S. Bureau of Transportation Statistics (BTS) Freight TSI & Truck Tonnage Ingestion (`src/bts_transportation.py` - Issue #74)
- Integrates the official BTS SODA API (`data.bts.gov/resource/bw6n-ddqk.json`) to ingest monthly seasonally adjusted Freight Transportation Services Index (`tsi_freight`), Truck Tonnage Index (`truck_d11`), Petroleum Pipeline/Surface Transport volume (`petroleum_d11`), Passenger TSI, and Total TSI.
- Built a 4-tier resilient fallback hierarchy: Live SODA API $\rightarrow$ Public FRED Series (`TSIFRGHT` / `TRUCKD11`) $\rightarrow$ Persistent Benchmark Cache $\rightarrow$ Curated Historical Baseline Dataset (2020–2026).
- Features 7-day TTL lookup caching in `global_cache` (`data/lookup_cache.sqlite`) and bitemporal point-in-time vintage tracking in `data/bts_vintages.json`.
- Computes month-over-month physical demand momentum indicators (`bts_tsi_freight_mom_pct`, `bts_truck_tonnage_mom_pct`, `bts_petroleum_transport_mom_pct`) and physical demand pressure scores.
- Added REST API endpoint `GET /api/v1/macro/freight-tsi` supporting historical time-series queries and `summary_only` real-time demand momentum snapshots.

---

### 2. Automated Static API Feeds Synchronization (`src/static_api_exporter.py` & `src/dashboard_generator.py`)
- Hooked `export_all_static_api_endpoints()` directly into `generate_public_dashboard()` and `run_all.py` so that all static JSON payloads under `docs/api/v1/*.json`, `docs/api/v1/combined_*.json`, and `docs/api/v1/combined/*.json` are regenerated automatically whenever the pipeline or web dashboard runs.
- Fixed stale API feeds on GitHub Pages that previously served historical cached baseline prices to mobile applications.

---

### 3. Dynamic Forecast Delta Resolution & 5-Day Trajectory Generation (`src/api_server.py`)
- Updated `_get_forecast_impl` to read the latest trained model forecast deltas from `data/prediction_history.csv` across all modeled regional calibration hubs.
- Added smooth 5-day step-ahead trajectory interpolation fields (`day_1_price` through `day_5_price`) in the forecast payload for mobile app UI rendering.

---

### 4. Quantitative Feature Matrix Fusion (`src/feature_engineering.py`)
- Merged 8 new physical transportation features into `create_feature_matrix()` (`bts_tsi_freight`, `bts_truck_tonnage`, `bts_petroleum_transport`, `bts_tsi_freight_mom_pct`, `bts_truck_tonnage_mom_pct`, `bts_petroleum_transport_mom_pct`, `bts_tsi_total`, `bts_rail_carloads`) with daily forward-filling and zero nulls.

---

### 5. Static JSON Feeds Baseline Refresh (`docs/api/v1/`)
- Re-exported all 9 regional static API files reflecting active retail pump prices ($4.01/gal for Tulsa, $4.361/gal for Newark, $4.500/gal for Cincinnati, $6.131/gal for Oakland, etc.).

---

### 6. Seasonal & Climatological Plausibility Gating for Shock Scenarios (`src/scenario_engine.py` - Issue #300)
- Implemented dynamic seasonal and climatological plausibility gating across all 20 scenario catalog presets (`ACTIVE_THREAT`, `SEASONALLY_PLAUSIBLE`, `SEASONALLY_DORMANT`, `EVERGREEN`, and `PROSPECTIVE_FORWARD`).
- Added new `polar_vortex_freeze` preset (Dec 01 – Feb 28 active window) modeling arctic freeze-offs across Texas and Midcontinent refining corridors.
- Built prospective forward scenario generator formulating predictive "What-If" stress tests 1–14 days ahead of reality from leading precursor indicators (NOAA NHC tropical wave outlooks, NOAA SPC convective risk, USGS drought gradients, statutory RVP spec countdowns).
- Added REST API endpoint `GET /api/v1/forecast/scenarios` supporting `?active_only=true` and `?locale=...` query filters.
- Enhanced `POST /api/v1/forecast/simulate` and MCP tool `simulate_fuel_market_shock` with transparent off-season counterfactual warning annotations.
- Added MCP tool `list_market_shock_scenarios` for direct LLM agent scenario discovery.
- Integrated closed-loop Forward Plausibility Horizon Matrix, multi-hub weekly stress audit, and seasonal issue priority boosts in `src/weekly_issue_reporter.py`.

---

### 7. MiroFish Multi-Agent Financial Simulation & Scenario Decision Graphs (`src/scenario_simulator.py` - Issue #307)
- Implemented 4-persona deliberative market cohort (`Agent_Refiner`, `Agent_Logistics`, `Agent_Consumer`, `Agent_Macro`) modeling joint cross-commodity price impacts on RBOB Unleaded Gasoline ($\Delta P_{\text{RBOB}}$), Heating Oil / ULSD Distillate ($\Delta P_{\text{HO}}$), and Regional Freight Basis ($\Delta B_{\text{cents}}$).
- Built single-round structured prompt consensus contract (`COHORT_SIMULATION_PROMPT`) preventing token explosion while calculating the Behavioral Divergence Index ($\sigma$) for market disagreement.
- Integrated Tier 3 Deterministic Elasticity Matrix for 100% offline fallback ($0 API cost).
- Exposes Mermaid flowchart markup (`flowchart TD`) and JSON causal graphs for dashboard display.
- Added modular feature toggle `MIDGLEY_ENABLE_MULTI_AGENT_SIMULATION` (`0` default / `1` active) and dynamic dashboard status badge (`Multi-Agent Cohort: ON` in purple vs `Multi-Agent Cohort: OFF` in slate).

---

## 🧪 Verification & Test Suite Matrix

- **Execution Target:** Dedicated Linux VM (`dev-vm` / `10.42.42.54`).
- **Test Suite Results:**
  - `tests/test_scenario_simulator.py` (6/6 tests passing)
  - `tests/test_scenario_engine.py` (6/6 tests passing)
  - `tests/test_api_server.py` (21/21 tests passing)
  - `tests/test_dashboard_generator.py` (19/19 tests passing)
  - `tests/test_mcp_server.py` (8/8 tests passing)
  - `tests/test_weekly_issue_reporter.py` (6/6 tests passing)
  - `tests/test_bts_transportation.py` (8/8 tests passing)
  - `tests/test_feature_attribution.py` (3/3 tests passing)
  - `tests/test_baker_hughes_feed.py` (4/4 tests passing)
  - Static JSON export validated across all 9 regional metro hubs.

---

## 📋 Upgrading

To update on the **dev** branch:

```bash
git fetch origin
git checkout dev
git pull origin dev
```
