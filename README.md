# LLM-Augmented Unleaded Gas Price Prediction Model (`midgley` v0.6.8 / v0.7.0-dev)

[![Release: v0.6.8](https://img.shields.io/badge/Release-v0.6.8-orange.svg)](https://github.com/KoshiirRa/midgley/releases/tag/v0.6.8)
[![Development: v0.7.0-dev](https://img.shields.io/badge/Dev-v0.7.0--dev-blue.svg)](https://github.com/KoshiirRa/midgley/tree/dev)
[![GHCR Docker](https://img.shields.io/badge/GHCR-midgley%3Aself--hosted-blue.svg?logo=docker)](https://github.com/KoshiirRa/midgley/pkgs/container/midgley)
[![Daily Gas Price LLM Forecasting & Public Dashboard](https://github.com/KoshiirRa/midgley/actions/workflows/gas_price_forecast.yml/badge.svg)](https://github.com/KoshiirRa/midgley/actions/workflows/gas_price_forecast.yml)
[![Weekly Model Review](https://github.com/KoshiirRa/midgley/actions/workflows/weekly_model_review.yml/badge.svg)](https://github.com/KoshiirRa/midgley/actions/workflows/weekly_model_review.yml)
[![Automated Nightly Dev Release](https://github.com/KoshiirRa/midgley/actions/workflows/nightly_dev_release.yml/badge.svg)](https://github.com/KoshiirRa/midgley/actions/workflows/nightly_dev_release.yml)

[![Public Dashboard](https://img.shields.io/badge/Public_Dashboard-koshiirra.github.io%2Fmidgley-blue.svg)](https://koshiirra.github.io/midgley/)
[![License: Apache 2.0](https://img.shields.io/badge/License-Apache_2.0-blue.svg)](LICENSE)
[![Python 3.10 | 3.11 | 3.12 | 3.13](https://img.shields.io/badge/Python-3.10%20%7C%203.11%20%7C%203.12%20%7C%203.13-green.svg)](pyproject.toml)

An **LLM Multi-Agent Time-Series Forecasting Framework** that integrates qualitative real-world news feeds, **NOAA Weather Models**, **Global Maritime & Inland Waterway Chokepoints (Hormuz/Suez/Rivers/Waterborne Terminals)**, **Agent-Reach Multi-Protocol Reachability Adapters**, **AIHawk Self-Healing State Tax Portals**, **Alternative Physical Feeds (Cboe OVX & Baker Hughes Rigs)**, **Vectorize Hindsight Episodic Memory Synchronization**, and **Tulsa Regional Refining Dynamics** with quantitative commodity futures (`RB=F`, `CL=F`, `BZ=F`) to predict wholesale and retail unleaded gasoline prices.

<!-- START_LIVE_FORECAST -->
### 📢 Live 5-Day Price Forecasts (Updated: 2026-09-22 14:16 UTC)

| Region / Market | Current Price | 5-Day Forecast | Projected Direction | Target Date | Model Version |
| :--- | :--- | :--- | :--- | :--- | :--- |
| **National Wholesale (RBOB)** | `$3.470`/gal | **`$3.513`/gal** | **UP 📈** | `2026-09-28` | `v1.6-Ipatieff-National-Ridge` |
| **Tulsa, OK Metro Retail** | `$3.993`/gal | **`$6.391`/gal** | **UP 📈** | `2026-09-28` | `v1.6-Ipatieff-Tulsa-Ridge` |
| **Newark, DE Metro Retail** | `$4.353`/gal | **`$4.447`/gal** | **UP 📈** | `2026-09-28` | `v1.6-Ipatieff-Newark-Ridge` |
| **Cincinnati, OH Retail** | `$4.441`/gal | **`$4.517`/gal** | **UP 📈** | `2026-09-28` | `v1.6-Ipatieff-CincinnatiOH-Ridge` |
| **Northern Kentucky Retail** | `$4.502`/gal | **`$4.579`/gal** | **UP 📈** | `2026-09-28` | `v1.6-Ipatieff-CincinnatiKY-Ridge` |
| **Greenville, NC Metro Retail** | `$4.128`/gal | **`$4.181`/gal** | **UP 📈** | `2026-09-28` | `v1.6-Ipatieff-Greenville-Ridge` |
| **Oakland, CA Metro Retail** | `$6.232`/gal | **`$6.341`/gal** | **UP 📈** | `2026-09-28` | `v1.6-Ipatieff-Oakland-Ridge` |
| **SF Bay Area 9-County Avg** | `$6.336`/gal | **`$6.446`/gal** | **UP 📈** | `2026-09-28` | `v1.6-Ipatieff-BayArea-Ridge` |

*🌐 View Interactive Web Dashboard & Public Visual Analytics at [koshiirra.github.io/midgley](https://koshiirra.github.io/midgley/)*
<!-- END_LIVE_FORECAST -->

---

## 📜 Etymology & Historical Namesake

This project is named **`midgley`** in ironic homage to **Thomas Midgley Jr.** (1889–1944), the American chemical engineer who invented **tetraethyllead (TEL)** as a gasoline anti-knock additive in 1921 (and later chlorofluorocarbons/CFCs). Environmental historian J. R. McNeill famously remarked that Midgley *"had more adverse impact on the atmosphere than any other single organism in Earth's history."*

In stark contrast to Midgley's legacy of unintended consequences on atmospheric chemistry and public health, this project harnesses modern **LLM intelligence and NOAA atmospheric weather models** to forecast unleaded gasoline markets and mitigate supply disruption risks.

---

## 🌐 Public Interactive Web Dashboard

A live multi-page public web dashboard is automatically updated and deployed on every workflow run via GitHub Pages:

👉 **[https://koshiirra.github.io/midgley/](https://koshiirra.github.io/midgley/)**

- **`/` (Overview)**: Central Midgley overview landing page featuring summary forecast cards for all active locales, rolling accuracy improvement charts, and multi-agent system pillars.
- **`/national` (National Wholesale)**: Dedicated NYMEX RBOB futures forecast & technical analytics page.
- **`/tulsa` (Tulsa Retail Gas)**: Dedicated Tulsa metro retail gas forecast & regional refinery shock simulator, accessible via the top nav **`Metro Areas`** dropdown menu.
- **`/newark` (Newark DE Retail)**: Dedicated Newark, DE (PADD 1B Central Atlantic) metro retail gas forecast featuring Delaware City Refinery turnaround dynamics, C&D Canal maritime detours, and DE state fuel tax ($0.230/gal).
- **`/cincinnati` (Cincinnati OH/KY Cross-River Retail)**: Dedicated Cincinnati OH/KY metro retail gas forecast featuring dual-state fuel tax differential display (OH $3.45 vs NKY $3.325), live USGS river stage telemetry, and Mississippi/Ohio River low-water barge bottleneck simulator.
- **`/greenville` (Greenville NC Retail)**: Dedicated Greenville, NC (PADD 1C South Atlantic) metro retail gas forecast featuring Colonial Pipeline Selma/Apex breakout hub dynamics, NC state gas tax ($0.404/gal), and NOAA Pitt County (NCZ081) Tar River flood / hurricane alerts.
- **`/charlotte` (Charlotte NC Retail)**: Dedicated Charlotte, NC (PADD 1C South Atlantic) metro retail gas forecast featuring Colonial Pipeline Paw Creek breakout hub dynamics, NC/SC cross-border tax differential ($0.404/gal NC vs $0.288/gal SC), and NOAA Mecklenburg County (NCZ071) Catawba River flood / winter ice storm alerts.
- **`/port_st_lucie` (Port St. Lucie FL Retail)**: Dedicated Port St. Lucie, FL (PADD 1C South Atlantic) metro retail gas forecast featuring Florida >95% waterborne marine barge offloading dependency, upstream USGS Gulf Coast departure tracking, Port Everglades & Port Canaveral marine terminals, FL state fuel tax ($0.384/gal), and NOAA St. Lucie County (FLZ147) Atlantic hurricane alerts.
- **`/oakland` (Oakland CA Retail)**: Dedicated Oakland / East Bay retail gas forecast featuring CARB regulatory breakdown ($0.953/gal tax burden), USGS Carquinez Strait runoff & berthing telemetry, and physical hazard risk matrix (USGS quakes, PSPS wildfires, PTWC tsunamis).
- **`/bayarea` (SF Bay Area 9-County Region)**: Dedicated 9-county NorCal regional gas forecast featuring multi-county price matrix (San Francisco $5.12, San Jose $4.98, Oakland $4.95, North Bay $4.85).
- **`/math` (Math Guide)**: Educational guide detailing KaTeX LaTeX equations across all 15 pipeline sections (including 3-2-1 crack spreads, executive social gap multipliers, and CARB tax breakdown).
- **`/sources` (Data Sources Catalog)**: Comprehensive public catalog documenting all 26 quantitative commodity futures, NOAA weather sensors, USGS hydrology stations, state tax portals, and financial news feeds.
- **`/telemetry` (System Observability & Model Evolution)**: Real-time telemetry dashboard featuring Model Learning & Longitudinal Adaptation Tracking (rolling MAE vs naive baseline, LLM win rates, multi-window scoreboards), Vectorize Hindsight episodic memory observability, 7-day zero-cost data connector health audits (EIA, FRED, USDA, NOAA, AAA, Socrata, USGS), zero-cost LLM fallback & cumulative dollar/token savings, expanded API quota safety valves (Firecrawl, Finlight, IPASIS), and dynamic out-of-metro Leaflet demand heatmaps.
- **`MODEL_LEARNING.md` (Longitudinal Evolution Journal)**: Automated persistent Markdown journal documenting multi-window accuracy convergence (7d, 14d, 30d, 90d, All-Time), Sapient PRAXIST hypothesis testing history, categorized episodic memory post-mortems, and multi-agent learning diagrams.
- **`/research` (Research Citations)**: Research literature bibliography cataloging academic papers, preprints, econometric models, and domain citations referenced in Midgley.
- **Weekly Review 2.0 & Episodic Agent Memory (Issue #230)**: Biomimetic Retain-Recall-Reflect memory engine on Google Cloud Run (Scale-to-Zero) + Supabase `pgvector` with local SQLite FTS5 fallback, performing automated qualitative anomaly post-mortems and historical shock analogy retrieval during Saturday reviews.
- **Automated Social Embed Cards**: Dynamic 1200x630px dark-mode Open Graph preview card PNGs (`docs/assets/embeds/*.png`) rendered for Discord, Twitter/X, and Slack link previews.


---

## 🏗️ Architecture Overview

```mermaid
flowchart TD
    subgraph FEEDS["Unstructured News, NOAA Weather & Physical Data Feeds"]
        F1["Geopolitical Headlines & OPEC Press Releases"]
        F2["NOAA NWS & SPC Weather Alerts (t.wxs.us)"]
        F3["Maritime & Waterways (Hormuz, Suez, Rivers, Waterborne Terminals)"]
        F4["Executive Social Feed (Live Truth Social / X Polling & Weekend Gap Classifier)"]
        F5["Physical Alternative Feeds (Cboe OVX & Dynamic Baker Hughes Rigs)"]
        F6["USGS Water Data Telemetry (Streamflow, Stage & Cooling Temp)"]
        F7["USGS Earthquake API Telemetry (earthquake.usgs.gov)"]
        F8["BSEE Offshore Platform Shut-ins & USACE Lock Delays"]
    end

    subgraph EXTRACTOR["1. Event, Weather & Physical Extraction Agent"]
        E1["Google Gemini 2.5 Flash / Domain NLP Lexicon"]
        E2["intraday_event_monitor.py, finlight_feed.py & firecrawl_scraper.py"]
        E3["noaa_weather.py (Token-Efficient Ingestion & SPC Mapping)"]
        E4["pasa_research_agent.py (PaSa Crawler-Selector Multi-Hop Loop)"]
    end

    subgraph FUSION["2. Exponential Memory Fusion Agent"]
        M1["Dynamic Category Decay Accumulator (t½ = 2.5d to 14.0d)"]
    end

    subgraph MODEL["3. Quantitative Forecasting Agent"]
        Q1["Standardized Ridge (α=10.0) / XGBoost Estimator"]
        Q2["Main Model: National Wholesale RBOB Futures"]
    end

    subgraph METRO["4. Localized Metro Area Calibration Agents"]
        L1["Tulsa Metro (tulsa_main.py - Cushing WTI & HF Sinclair Outages)"]
        L2["Newark Metro (newark_main.py - PADD 1B & C&D Canal Detours)"]
        L3["Cincinnati Tri-State (cincinnati_main.py - Dual-State Tax Gap)"]
        L4["Greenville NC (greenville_main.py - Colonial Line 1/2 Hubs)"]
        L5["Charlotte NC (charlotte_main.py - Paw Creek Distribution Hub)"]
        L6["Oakland & SF Bay Area (oakland_main.py - CARB Burden & Physical Risks)"]
        L7["Port St. Lucie FL (port_st_lucie_main.py - Waterborne Marine Freight)"]
        L8["ULSD Distillate Diesel Engine (diesel_main.py - 3-2-1 Crack Margin)"]
    end

    subgraph SIMULATOR["5. Synthesis & Scenario Simulator Agent"]
        S1["src/scenario_engine.py & Climatology Registry (20 Scenarios)"]
        S2["Seasonal Plausibility Gating (Active, Plausible, Dormant, Evergreen)"]
        S3["Prospective Forward Precursor Synthesis (1–14d Lead Time)"]
        S4["Simulates Refinery Outages, Hormuz Blockades & Weather Freezes"]
    end

    subgraph MLOPS["6. MLOps Prediction Logging Agent"]
        P1["prediction_logger.py → data/prediction_history.csv"]
        P2["Rolling 30/60/90d MAE/RMSE & Directional Hit Rates"]
    end

    subgraph REVIEW["7. Model Performance Review & Feedback Loop Agent"]
        R1[".github/workflows/weekly_model_review.yml"]
        R2["weekly_issue_reporter.py, agent_memory.py & hindsight_client.py"]
        R3["Retain-Recall-Reflect: Cloud Run (Scale-to-Zero) + Supabase pgvector & SQLite FTS5"]
        R4["Forward Plausibility Horizon Matrix & Multi-Hub Stress Audit"]
    end

    subgraph DASHBOARD["8. Public Web Dashboard & Presentation Agent"]
        D1["src/dashboard_generator.py → koshiirra.github.io/midgley"]
    end

    FEEDS -->|Unstructured Streams| EXTRACTOR
    EXTRACTOR -->|Structured Bounded Vectors| FUSION
    FUSION -->|Unified Feature Matrix| MODEL
    MODEL -->|Base Commodity Forecast| METRO
    METRO -->|Localized Metro Forecasts| SIMULATOR
    SIMULATOR -->|Real-Time Adjusted Forecasts| MLOPS
    MLOPS -->|Persistent Prediction History| REVIEW
    REVIEW -->|Empirical Diagnostic Feedback Signal| MODEL
    MLOPS -->|Out-of-Time Forecast Data| DASHBOARD
    REVIEW -->|Weekly Accuracy & Issue Reports| DASHBOARD
```

### System Component Breakdown

* **1. Event, Weather & Physical Extraction Agent ([`src/event_analyzer.py`](src/event_analyzer.py), [`src/firecrawl_scraper.py`](src/firecrawl_scraper.py), [`src/finlight_feed.py`](src/finlight_feed.py), [`src/noaa_weather.py`](src/noaa_weather.py), [`src/nhc_hurricane.py`](src/nhc_hurricane.py), [`src/bsee_shutins.py`](src/bsee_shutins.py), [`src/usace_locks.py`](src/usace_locks.py), & [`src/alternative_data_feeds.py`](src/alternative_data_feeds.py)):** Ingests live financial media headlines (`finlight.me`), raw news bulletins, deep web articles and refinery disclosures converted to clean Markdown via Firecrawl Web Scraping API (`src/firecrawl_scraper.py`), NOAA alerts (`t.wxs.us`), NOAA NHC Hurricane advisories (`src/nhc_hurricane.py`), BSEE Gulf offshore platform shut-ins (`src/bsee_shutins.py`), EIA-930 hourly grid stress (`src/data_ingestion.py`), expanded EIA weekly petroleum balance series, USACE LPMS Ohio River lock delays (`src/usace_locks.py`), maritime chokepoints, executive social posts, Cboe OVX volatility, and Baker Hughes rig counts into structured numerical impact vectors. Enforces a 150 call/month Finlight quota safety valve (`data/finlight_quota.json`), an 800 call/month Firecrawl safety cap (`data/firecrawl_quota.json`), fail-closed webhook authentication (`src/api_server.py`), persistent Cloudflare D1 edge deduplication (`workers/intraday_monitor_worker.ts`), and 24-hour headline & evaluated ledger deduplication (`src/intraday_event_monitor.py` & `data/evaluated_headlines.json`, Issue #239).
* **2. Exponential Memory Fusion Agent ([`src/feature_engineering.py`](src/feature_engineering.py)):** Models point-shock persistence over 2–3 weeks using a continuous mathematical decay accumulator ($\mathbf{M}_t = \mathbf{M}_{t-1} \cdot e^{-\frac{\ln 2}{t_{1/2}}} + \mathbf{V}_t$) with dynamic category-specific half-lives $t_{1/2} \in [2.5, 14.0]\text{ days}$ ($14.0\text{d}$ physical supply disruptions, $7.0\text{d}$ geopolitical risk, $5.0\text{d}$ OPEC action, $4.0\text{d}$ demand sentiment, $2.5\text{d}$ executive social posts). Enforces point-in-time `as_of` publication date joins and bitemporal vintage tracking ([`src/data_ingestion.py`](src/data_ingestion.py), [`data/eia_vintages.json`](data/eia_vintages.json)) to eliminate historical scalar broadcasting and lookahead bias during model retraining (Issue #121).
* **3. Quantitative Forecasting Agent ([`src/models.py`](src/models.py)):** Fits regularized linear pipelines (StandardScaler + Ridge Regression $\alpha=10.0$) and XGBoost regressors on 80/20 chronological splits to predict wholesale RBOB futures return shocks. Features **Dynamic Volatility-Gated Persistence Blending (DV-GPB)** ($\lambda_{vol} = \frac{1}{1 + e^{-200.0(\sigma_{14d} - 0.015)}}$) shrinking forecasts to Naive Persistence during low-volatility plateaus while preserving 100% of event shock vectors during active market moves (Issue #214). Computes component-level feature attribution breakdowns (`compute_locale_feature_attribution_breakdown`) allocating signed price impact ($/gal) across 6 standardized domains (*Futures & Commodity, Refining Crack Margin, Weather & Environmental, Tax & Regulatory, Unstructured Sentiment, Regional Logistics*).
* **4. Localized Metro Area Calibration Agents ([`src/locations/`](src/locations/)):** Subpackage calibration modules (`tulsa`, `newark`, `cincinnati`, `greenville`, `charlotte`, `oakland`) that adjust wholesale commodity baselines to regional retail pump prices, dynamic rack margins, delivery hub logistics, reconciled statutory CARB tax components ($0.953/gal total burden), state fuel tax gaps, and infrastructure shocks. Integrates **Empirical Residual CI Recalibration ($\pm 1.96 \cdot \sigma_{\text{residual, 30d}}(r)$)** achieving $\ge 90.0\%$ 95% CI empirical coverage across all 10 metro calibration hubs.
* **5. Synthesis & Scenario Simulator Agent ([`src/scenario_engine.py`](src/scenario_engine.py) & [`src/locations/<location>/main.py`](src/locations/)):** Runs counterfactual "What-If" simulations (e.g. HF Sinclair EF-3 tornado shocks, Cushing pipeline spills, Hormuz blockades, Hayward Fault quakes, PG&E PSPS power shutoffs, and weekend tariff announcements) backed by **Seasonal & Climatological Plausibility Gating** (Issue #300), date-window constraints, active real-time telemetry threshold triggers (NOAA SPC, USGS hydrology, USGS seismic), precursor forward scenario synthesis (1–14 days lookahead), and off-season counterfactual warning annotations.
* **6. MLOps Prediction Logging Agent ([`src/prediction_logger.py`](src/prediction_logger.py)):** Logs 5-market-day out-of-time forecasts (`pd.bdate_range`) and 8 extended MLOps feature/attribution vectors (`llm_price_pressure`, `llm_supply_disruption`, `quant_baseline_5d_price`, `llm_augmentation_delta`, `prediction_lower_95ci`, `prediction_upper_95ci`, `within_95ci_hit`, `data_source_provenance`) to `data/prediction_history.csv`, isolating pure quantitative model forecasts ($\hat{P}_{\text{quant}}$) alongside hybrid forecasts ($\hat{P}_{\text{hybrid}}$) to compute true LLM augmentation deltas ($\Delta_{\text{LLM}} = \hat{P}_{\text{hybrid}} - \hat{P}_{\text{quant}}$, Issue #390), automatically backfills actual ground-truth prices from `yfinance` as target dates arrive, evaluates empirical 95% Confidence Interval Coverage (`within_95ci_hit`), and computes continuous rolling 30/60/90-day MAE, RMSE, MAPE, Directional Hit Rate %, Model MAE Uplift % vs. Naive Persistence, Model vs. Persistence Win Rate %, and LLM vs. Quant Win Rate % via `GET /api/v1/forecast/scoreboard`.
* **7. Model Performance Review & Feedback Loop Agent ([`.github/workflows/weekly_model_review.yml`](.github/workflows/weekly_model_review.yml), [`src/agent_memory.py`](src/agent_memory.py), [`src/hindsight_client.py`](src/hindsight_client.py), [`src/weekly_issue_reporter.py`](src/weekly_issue_reporter.py), [`src/catalog_monitor.py`](src/catalog_monitor.py), [`src/arxiv_monitor.py`](src/arxiv_monitor.py) & [`docs/research_sources.md`](docs/research_sources.md)):** Automated Saturday runner (08:00 AM Central / 13:00 UTC) evaluating rolling MAE/RMSE metrics, performing LLM self-reviews of open GitHub issues, executing **Vectorize Hindsight Episodic Memory** qualitative root-cause post-mortems and historical shock analogy recall with scale-to-zero proactive warmup and zero-data-loss pending memory reconciliation, monitoring developer catalogs & arXiv research preprints, and feeding empirical diagnostic signals back into model recalibration.
* **8. Public Web Dashboard & Presentation Agent ([`src/dashboard_generator.py`](src/dashboard_generator.py) & [`src/regional_metadata.py`](src/regional_metadata.py)):** Builds the multi-page responsive public web app deployed automatically to GitHub Pages ([koshiirra.github.io/midgley](https://koshiirra.github.io/midgley/)), rendering visual driver cards dynamically from decoupled JSON metadata profiles (`data/regional_metadata/`), including interactive technical breakdown pages (`docs/technical_breakdown.html`) and run JSON payloads (`docs/runs/`).

---

## 📱 Executive Social Media & Weekend Market Gap Engine (`src/executive_social_feed.py`)

Our empirical econometric analysis of executive social media posts (Twitter/X and Truth Social energy commentary from 2018–2026) reveals statistically significant price return and volatility correlations (*p* < 0.01):

1. **Dovish OPEC Pressure Posts:** Statements urging OPEC to increase production or ease price hikes cause immediate average **-1.85% single-day wholesale RBOB drops**.
2. **Hawkish Tariff Shocks:** Announcements threatening energy import tariffs (e.g., 25% foreign crude tariffs) produce immediate average **+2.10% price return surges**.
3. **Weekend Market Gap Multiplier (1.42x):** Because commodity futures markets are closed from Friday 17:00 EST to Sunday 18:00 EST, Saturday/Sunday executive social media posts cannot be immediately priced in by spot trading algorithms. On Sunday evening 18:00 EST market reopen, weekend posts generate **42% higher Monday morning open price gap volatility** than baseline weekends.

---

## ⚡ Key Features

1. **Auto-Updating Live README Forecast Table (`src/readme_updater.py`):** Automatically injects the latest 5-day national & Tulsa forecasts into `README.md`.
2. **Public Web Dashboard Generator (`src/dashboard_generator.py`):** Builds a responsive HTML/Tailwind/Chart.js web app (`docs/index.html`) deployed automatically to GitHub Pages ([koshiirra.github.io/midgley](https://koshiirra.github.io/midgley/)).
3. **Regional Tulsa, OK Retail Model (`tulsa_main.py`):** Dedicated regional forecasting module calibrated directly to live local pump prices (**$3.89/gal**), factoring in Cushing WTI crude proximity (50 miles from Tulsa) and HF Sinclair West Tulsa Refinery (125,000 bpd) shocks.
4. **Two-Tiered NOAA Weather Integration (`src/noaa_weather.py`):**
   - **Tier 1 (National Basins):** NOAA NHC Hurricane advisories in Gulf Coast refining hubs & Permian/Bakken winter freeze warnings.
   - **Tier 2 (Localized Regional Metros):** NOAA NWS severe alerts across **Tulsa (`OKZ060/OKZ066`)**, **Newark (`DEZ001`)**, **Cincinnati (`OHZ077/KYZ091`)**, **Greenville (`NCZ081`)**, **Charlotte (`NCZ071`)**, **Oakland / SF Bay (`CAZ508/CAZ511`)**, and **Port St. Lucie (`FLZ147`)**.
5. **Global Maritime Chokepoint & Inland Waterway Logistics Feeds (`src/geopolitical_feeds.py`):** Tracks Iran conflict alerts in the **Strait of Hormuz** (21.0M bpd / 20% of global oil), Red Sea / Suez Canal tanker rerouting events, Venezuela Orinoco heavy crude sanctions, Ohio/Mississippi River tow barge draft constraints, MKARNS navigation, and coastal waterborne lightering/terminal surcharges.
6. **Real-Time Finlight Financial News Stream (`src/finlight_feed.py`):** Integrates live commodity & macroeconomic news articles from tier-1 financial media (Reuters, Bloomberg, Seeking Alpha, Investing.com) using the `finlight.me` REST API.
7. **Executive Social Media & Weekend Gap Engine (`src/executive_social_feed.py`):** Quantifies Trump Twitter/Truth Social energy posts and models Monday morning futures open price gaps (1.42x volatility multiplier).
8. **Alternative Physical Data & Key Movers (`src/alternative_data_feeds.py` & `src/key_movers_feed.py`):** Features Cboe Crude Volatility (`^OVX`), Baker Hughes Active Drilling Rig Counts, and statements from Saudi Energy Minister Prince Abdulaziz & Fed Chair Powell.
9. **MLOps Prediction Tracker, Ground-Truth Backfilling & Cloud DB Sync (`src/prediction_logger.py`, Issue #82):** Logs 5-day out-of-time forecasts to `data/prediction_history.csv`, backfills actual historical market prices from `yfinance` as target dates arrive, automatically backfills test split history for newly added regions (`backfill_new_region_history`), and synchronizes forecast records to cloud relational stores (Turso Edge SQLite, Cloudflare D1 Edge Workers, Neon Postgres) via REST API endpoints (`POST /api/v1/forecast/cloud-sync` & `GET /api/v1/forecast/cloud-status`) with 100% local CSV offline fallback.
10. **Fireworks Tech Graph Automated Architecture Diagram Generator (`src/fireworks_tech_graph.py`, Issue #191):** Synthesizes self-contained, validated SVG vector diagrams outputting to `docs/assets/multi_agent_architecture.svg` and `docs/assets/regional_metro_architecture.svg` visualizing the 8-stage multi-agent execution pipeline and 6 regional metro calibration hubs, with visual embeds in `AGENTS.md` and the public web app landing page (`docs/index.html`).
11. **Weekly Model Performance Review & Issue Self-Review Engine (`src/weekly_issue_reporter.py` & `.github/workflows/weekly_model_review.yml`):** Evaluates rolling MAE/RMSE/Hit Rate metrics across all active regions and performs an automated self-review of all open GitHub repository issues using Gemini 2.5 Flash to identify and rank the issue providing the highest potential modeling improvement.
12. **Local Dev Environment, Web Server & Systemd Timers (`dev-vm` Port 8080 & 8000):** Serves live dashboard analytics from the permanent `dev` branch on `dev-vm`, with systemd user timers (`midgley-daily-forecast.timer` and `midgley-weekly-review.timer`) running daily forecasts and weekly issue audits 24/7.
13. **Automated Nightly Dev Releases (`.github/workflows/nightly_dev_release.yml`):** Automatically builds, tags (`dev-YYYY-MM-DD`), and documents GitHub pre-releases tracking whatever is on the `dev` branch every night at 3:00 AM Central Time (08:00 UTC).
14. **3-Tier Multi-Tier Cache Gateway & Quota Sync (`src/lookup_cache.py`):** High-availability cascading cache (Turso Edge SQLite -> Cloudflare D1 Worker -> Local SQLite `data/lookup_cache.sqlite`) with SHA-256 headline deduplication ($0 token cost on repeated headlines) and cross-runner API quota ledger sync (`quota:finlight:current`).
15. **Locales Metadata & Multi-Region Batch Forecast Gateway (`src/api_server.py`, Issue #48):** Exposes `GET /api/v1/locales` for dynamic discovery of supported locale codes, statutory CARB tax burdens, and refining hub metadata, backed by multi-region batch endpoints (`POST /api/v1/forecast/batch` and `POST /api/v1/combined/batch`).
16. **ZIP Code Geocoding & System Observability Page (`src/zip_geocoding.py` & `docs/telemetry.html`, Issues #50 & #195):** Resolves any 5-digit US ZIP code via a 4-tier fallback engine (Metro Cluster hit -> State/PADD fallback -> Live GasBuddy station search -> Resolution metadata), logs unmapped lookups to `data/unmapped_zip_telemetry.json`, and exposes interactive Leaflet.js query demand heatmaps and candidate expansion metro hubs on `docs/telemetry.html`.
17. **Strategy 4 Incoming Webhook Gateway & Custom Event Triggers (`src/api_server.py` & `docs/WEBHOOK_FORMATTING_GUIDE.md`, Issue #78):** Real-time push ingestion endpoint (`POST /api/v1/events/webhook`) featuring automatic payload transformers (`headline` $\leftarrow$ `title`/`text`/`summary`/`tweet_content` & `url` $\leftarrow$ `link`/`article_url`), HMAC-SHA256 signature verification (`X-Midgley-Signature`), locale-specific target routing matrix, and provider integration recipes for Google Alerts, Zapier, IFTTT, and TradingView.
18. **Autonomous Research & Academic Literature Tools (`src/academic_openalex.py`, `src/semantic_scholar_feed.py`, `src/mcp_server.py`, Issues #263, #264, #266, #267):** Programmatically queries OpenAlex and Semantic Scholar for energy econometrics literature, empirical parameter prior intervals ($t_{1/2} \in [4.0, 5.0]\text{d}$), and single-sentence TL;DR abstracts over the Model Context Protocol, backed by a declarative feed health diagnostic CLI (`python src/intraday_event_monitor.py --check-feeds`).
19. **CodeCogs Visual LaTeX Math UI & Markdown Fallbacks (`src/dashboard_generator.py`, Issue #52):** Generates CodeCogs SVG equation image URLs (`https://latex.codecogs.com/svg.latex?...`) embedding visual math fallbacks alongside raw LaTeX in `docs/technical_breakdown.md` for visual math rendering across GitHub Markdown views, mobile readers, and RSS feeds.
20. **Prometheus Telemetry Metrics Exporter (`src/telemetry.py` & `src/api_server.py`, Issue #107):** Exposes `/metrics` and `/api/v1/metrics` in Prometheus text exposition format, tracking TokenTab token consumption, IPASIS security check/block counts, 3-tier cache hit rates, request counters, and API quota remaining ratios for Grafana observability dashboards.
21. **Zero-Cost Internet Archive Wayback Machine Cloud Archiving (`src/wayback_archiver.py`, Issue #197 & #259):** Automatically resolves Google News redirect links to canonical publisher URLs and submits breaking energy news to the Internet Archive Save API (`https://web.archive.org/save/{url}`), attaching permanent `archive_url` strings to event results in `data/intraday_events.json` and system logs.
22. **GeoPandas Spatial Refinery Distance Buffering Engine (`src/spatial_refinery.py`, Issue #95):** Calculates spatial distance-decay calculation from oil refineries, pipeline corridors, and marine terminals to regional retail gas station clusters using GeoPandas & Shapely in Web Mercator projection (`EPSG:3857`), generating spatial buffer rings (`25mi`, `50mi`, `100mi`, `250mi`, `500mi`) and exponential attenuation weights ($w(d) = \exp(-d / 150.0)$) with spherical Haversine fallback.
23. **USGS Water Data API Telemetry (`src/usgs_water_feed.py`, Issue #56):** Ingests real-time streamflow, gage height, water temperature, and specific conductance across 13 key stations in 6 inland waterway and refining corridors, providing physical bottleneck risk scoring via `GET /api/v1/usgs/water_levels` and MCP tool `get_usgs_water_telemetry`.
24. **USGS Earthquake Web Service Telemetry (`src/usgs_seismic.py`, Issue #55):** Ingests live earthquake GeoJSON data from `earthquake.usgs.gov/fdsnws/event/1/` across 5 critical energy corridors (`bay_area`, `cushing_ok`, `socal`, `mid_atlantic`, `new_madrid`), calculating facility-level distance-decay ground shaking proxies, regional composite risk indices, and pipeline emergency shutoff flags via `GET /api/v1/usgs/seismic` and MCP tool `get_usgs_seismic_telemetry`.
25. **Healthchecks.io Pipeline Heartbeat Monitoring (`src/healthcheck_monitor.py`, Issue #98):** Dispatches automated start, execution duration, success, and failure pings to Healthchecks.io dead-man's snitch endpoints across daily forecasting and Saturday weekly review runs.
26. **Open Source AI Radar Model Discovery (`src/data_ingestion.py` & `src/api_server.py`, Issue #187):** Ingests open-weights LLM/SLM releases, quantization benchmarks, and capability metrics via `OpenSourceAIRadarConnector` and `GET /api/v1/system/radar`.
27. **Self-Hosted ArchiveBox Historical Article Preservation (`src/archive_service.py`, Issue #97):** Asynchronously archives breaking news and energy source URLs to self-hosted ArchiveBox instances with zero pipeline latency and local snapshot ledger fallback (`data/archived_events_ledger.json`).
28. **Sapient PRAXIST Autonomous Energy Research Engine (`src/praxist_engine.py`, Issue #188):** Programmatic research evaluation harness for formulating, backtesting, and statistically validating empirical feature engineering hypotheses and multi-parameter sweeps.
29. **Universal 50-State Open Data Portals Connector (`src/state_open_data.py`, Issue #141):** `UniversalStateOpenDataConnector` provides dynamic resolution across all 50 US States + DC (51 total locales). Queries Socrata open data domains (`data.<state>.gov` / `data.gov`), U.S. Census State Tax Collections API, and FTA motor fuel indices for official state excise tax rates ($/gal), UST environmental cleanup fees, and motor fuel sales volume indices.
30. **Cloudflare Edge Queue Buffer & D1 Cache Gateway (`workers/intraday_monitor_worker.ts` & `workers/cache_worker.ts`, Issues #194 & #196):** Edge message buffer (`intraday-event-queue` producer/consumer bindings) decoupling event burst detection and webhook pushes from origin execution. Features edge authentication over Cloudflare D1 (`midgley-cache-d1`) and Option A2 full-stack telemetry streaming to Axiom Log Analytics and Sentry error/heartbeat tracking.
31. **Zero-Cost LLM Fallback Routing & TokenTab Accounting (`src/fallback_telemetry.py` & `src/token_tracker.py`, Issue #196):** Tiered key access routing `basic` tier requests to zero-cost offline rule lexicons and Kaggle open-source LLM hooks while preserving paid Gemini API tokens for `privileged` tier keys, tracking cumulative token/dollar savings on `docs/telemetry.html`.
32. **Self-Hosted Production Docker Container Image (`ghcr.io/koshiirra/midgley:self-hosted`, Issue #198):** Multi-stage production container packaged with Python 3.13, `uv`, OpenMP runtime, and pre-configured blank-slate National Wholesale RBOB environment variables, published automatically to GitHub Container Registry (`ghcr.io/koshiirra/midgley:self-hosted` & `latest`).
33. **Real-Time Discord Webhook Notification Gateway (`src/discord_notifier.py`, Issue #234):** Automated real-time Discord webhook alerts dispatched on intraday forecast revisions with environment isolation (`[PRODUCTION]` vs `[DEVELOPMENT]`), detailed catalyst telemetry (headline, source, article/archive links, target locales, price pressure $\Delta P$, supply disruption $S$), dynamic severity color-coding, and non-blocking failure resilience.
34. **Model Data Sources & Intelligence Feeds Directory (`src/sources_generator.py` & `docs/sources.html`):** Public technical directory and governance matrix documenting all 26+ input data streams (commodity futures, options volatility, rig counts, NOAA weather, USGS hydrology, USACE locks, USGS seismic, air quality, 50-state tax portals, crowdsourced pump feeds, and academic preprints) with instant category filtering and search.
35. **Headline Arena Independent Benchmark & Calibration Adapter (`src/headline_arena_connector.py`, Issues #182, #408, #410, #418):** Connects Midgley to **Headline Arena** (`headlinearena.com`) to benchmark RBOB Gasoline (`RB`), Cushing WTI Crude (`CL`), Henry Hub Natural Gas (`NG`), and US Dollar Index (`DXY`) daily directional forecasts against frozen criteria and mechanical price settlement. Features OAuth2 client credentials token exchange, closed-form standard normal CDF probability conversion over asset-specific dead-zone thresholds ($\pm0.30\%$ for RB, $\pm0.20\%$ for CL, $\pm0.50\%$ for NG, $\pm0.20\%$ for DXY), decoupled 24-hour pending forecast caching with 30-minute sync loops, environment isolation (`[DEV-TEST]` tagged dry-runs in dev vs automated production submissions), and connector telemetry.
36. **NASA POWER Climatology & Agroclimatology Engine (`src/nasa_power.py`, Issues #370, #420):** Connects to the NASA Langley POWER Point Daily API (`power.larc.nasa.gov`) to ingest daily surface temperatures, precipitation, relative humidity, and solar radiation. Computes PADD 1 heating/cooling degree days ($HDD = \max(0, 65 - T_{\text{mean}})$, $CDD = \max(0, T_{\text{mean}} - 65)$) across primary Atlantic refining and marine terminals (New York Harbor, Delaware City, Boston) for distillate and heating oil demand, and PADD 2 Corn Growing Degree Days ($GDD = \max(0, \frac{\min(86, T_{\text{max}}) + \max(50, T_{\text{min}})}{2} - 50)$) across Midwest ethanol hubs (Des Moines IA, Peoria IL, Omaha NE).
37. **Hindsight Hosted Episodic Memory Telemetry (`src/hindsight_client.py` & `src/agent_memory.py`, Issues #230, #421, #422):** Integrates Vectorize Hindsight-Hosted episodic agent memory with zero cold-start latency, surfacing durable observations, episodic reflections, local SQLite pending cloud reconciliation queue counts, and connector event health telemetry on `docs/telemetry.html`.
38. **Timezone-Aware Market Trading Hours Evaluation (`src/finlight_feed.py` & `src/data_ingestion.py`, Issue #328):** Evaluates NYMEX / US commodity trading hours (08:00 AM – 05:00 PM Eastern, Mon–Fri) with explicit `zoneinfo.ZoneInfo("America/New_York")` conversion across Finlight, AlphaVantage, and OilpriceAPI connectors, preventing premature quota exhaustion on non-Eastern cloud runners.
39. **Universal Discord Webhook Delivery & Embed Formatting (`src/discord_notifier.py`, Issue #330):** Formats rich intraday forecast revisions for standard Discord incoming webhooks by embedding interactive action markdown links directly within embed fields to guarantee zero HTTP 400 rejection on standard webhook endpoints while preserving interactive Action Row button components when dispatched with bot authorizations.
40. **FHWA Monthly Traffic Volume Trends (TVT) Macroeconomic Ingestion (`src/fhwa_traffic_volume.py` & `src/bts_transportation.py`, Issue #369):** Ingests official Federal Highway Administration monthly vehicle miles traveled (VMT) reports across national and 5 regional corridors (Northeast, South Atlantic, North Central, South Central, West) to compute macroeconomic gasoline consumption proxies, YoY travel demand growth, and 12-month moving totals with 60-day bitemporal publication lag gating.

---

## 🛠️ Self-Hosting & Multi-Metro Regional Extension

For operators and developers wishing to host their own custom instance of Midgley or extend the forecasting framework to new metropolitan regions:

👉 **Read the complete [Self-Hosting & Multi-Metro Regional Setup Guide (`SELF_HOSTING.md`)](SELF_HOSTING.md)**

### 🐳 Quick Start: Docker Container Deployment

Deploy a standalone Midgley self-hosted container instance directly from GitHub Container Registry:

```bash
# Pull the latest release container image (e.g. v0.6.8 or v0.7.0-dev)
docker pull ghcr.io/koshiirra/midgley:v0.6.8

# Run container with persistent host volume mounting for SQLite DBs and prediction logs (Issue #375)
docker run -d \
  --name midgley \
  -p 8000:8000 \
  -v $(pwd)/data:/app/data \
  -e GEMINI_API_KEY="AIzaSy..." \
  -e FINLIGHT_API_KEY="fl_live_..." \
  -e MIDGLEY_ADMIN_SECRET="sec_admin_secret_here" \
  ghcr.io/koshiirra/midgley:v0.6.8

# Verify unauthenticated API server health
curl http://localhost:8000/health

# Verify authenticated functional prediction route (if API key authentication is enabled)
curl -H "X-API-Key: $MIDGLEY_API_KEY" "http://localhost:8000/api/v1/forecast/predict?locale=national"
```

> [!TIP]
> **Durable Container State & Backups:** Always mount host volume `-v $(pwd)/data:/app/data` in production. This preserves provisioned API keys (`data/security.db`), episodic agent memories (`data/agent_memory.sqlite`), out-of-time prediction history (`data/prediction_history.csv`), and API quota ledgers across container restarts and image updates. See [`SELF_HOSTING.md`](SELF_HOSTING.md) for automated backup, restore, and rollback runbooks.

Key guide coverage includes:
* **Production Docker Container:** Multi-stage image running Python 3.13, `uv`, OpenMP, FastAPI / MCP transport, and persistent volume mounting.
* **Standalone Server & VM Deployment:** Systemd user service & timer unit files (`midgley-api.service`, `midgley-dev.service`, `midgley-daily-forecast.timer`, `midgley-weekly-review.timer`).
* **3-Tier Edge Cache Configuration:** Step-by-step setup for Turso Edge SQLite, Cloudflare D1/Worker, and local SQLite fallbacks.
* **LLM Discovery Prompts:** Ready-to-use LLM system prompt templates for researching econometric anchors, statutory fuel tax structures, refinery logistics, and NOAA weather alerts.
* **7-Step Developer Tutorial:** Comprehensive guide for adding new metro calibration subpackages (`src/locations/<location>/`) and decoupled JSON profiles (`data/regional_metadata/`).


---

## 📊 Model Performance Summary (v1.4 Finlight-LLM)

| Region / Target | Model Algorithm | MAE ($/gal) | RMSE ($/gal) | MAPE (%) | Directional Hit Rate |
| :--- | :--- | :---: | :---: | :---: | :---: |
| **National Wholesale (RBOB)** | Ridge (α=10.0) + Gemini 2.5 Flash | **$0.1069** | **$0.1490** | **4.76%** | **60.79%** (+4.40% boost) |
| **Tulsa, OK Metro Retail** | Ridge (α=10.0) + Localized NOAA | **$0.1331** | **$0.1880** | **4.83%** | **58.15%** |
