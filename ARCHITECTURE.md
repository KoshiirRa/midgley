# System Architecture & Technical Specifications

Technical design document for the **LLM-Augmented Unleaded Gas Price Prediction Engine**.

---

## 1. Mathematical Formulations & Feature Fusion

### A. Crack Spread Proxy Formulations
Gasoline crack spreads represent refiner acquisition and processing margins:
- **National Crack Spread Proxy:**
  \[
  \text{CrackSpread}_{\text{National}} = P_{\text{RBOB Wholesale (\$ / gal)}} - \frac{P_{\text{WTI Crude (\$ / bbl)}}}{42.0}
  \]
- **Tulsa Regional Crack Spread:**
  \[
  \text{CrackSpread}_{\text{Tulsa}} = P_{\text{Tulsa Retail (\$ / gal)}} - \frac{P_{\text{Cushing WTI (\$ / bbl)}}}{42.0}
  \]
- **Newark Regional Crack Spread:**
  \[
  \text{CrackSpread}_{\text{Newark}} = P_{\text{Newark Retail (\$ / gal)}} - \frac{P_{\text{Brent Crude (\$ / bbl)}}}{42.0}
  \]
- **Cincinnati Dual-State Cross-River Rack Margin & Crack Spread:**
  \[
  P_{\text{OH Retail}} = P_{\text{Wholesale RBOB}} + \text{Margin}_{\text{OH}} \quad (P_{\text{Live, OH}} = \$3.450/\text{gal})
  \]
  \[
  P_{\text{KY Retail}} = P_{\text{Wholesale RBOB}} + \text{Margin}_{\text{KY}} \quad (P_{\text{Live, KY}} = \$3.325/\text{gal})
  \]
  \[
  \text{TaxSpread}_{\text{OH-KY}} = P_{\text{OH Retail}} - P_{\text{KY Retail}} = \$0.125/\text{gal}
  \]
- **Oakland & SF Bay Area PADD 5 Richmond Crack Spread & CARB Tax Burden:**
  \[
  \text{CrackSpread}_{\text{Richmond}} = P_{\text{Oakland Retail (\$ / gal)}} - \frac{P_{\text{Brent Crude (\$ / bbl)}}}{42.0} \quad (P_{\text{Live, Oakland}} = \$4.950/\text{gal}, P_{\text{Live, BayArea}} = \$5.050/\text{gal})
  \]
  \[
  T_{\text{CARB}} = \tau_{\text{Excise}} + \tau_{\text{CapTrade}} + \tau_{\text{LCFS}} + \tau_{\text{UST/Env}} = \$0.596 + \$0.234 + \$0.088 + \$0.035 = \$0.953/\text{gal}
  \]
  \[
  T_{\text{All-In}} = T_{\text{CARB}} + \tau_{\text{Federal}} + \tau_{\text{Sales}} = \$0.953 + \$0.184 + \$0.270 = \$1.407/\text{gal}
  \]


### B. NYMEX Forward Curve, Calendar Spreads & 3-2-1 Crack Margin Formulations (Issues #401, #404)
Prompt ($M_1$) and Second Month ($M_2$) calendar spreads quantify forward term structure and physical refinery margins:
- **RBOB Calendar Spread ($M_1 - M_2$):**
  \[
  \text{Spread}_{\text{RBOB}, M_1-M_2} = P_{\text{RBOB}, M_1} - P_{\text{RBOB}, M_2}
  \]
- **WTI Calendar Spread ($M_1 - M_2$):**
  \[
  \text{Spread}_{\text{WTI}, M_1-M_2} = P_{\text{WTI}, M_1} - P_{\text{WTI}, M_2}
  \]
- **Refinery 3-2-1 Crack Margin Barrel-Equivalent ($\$ / \text{bbl}$):**
  \[
  \text{Crack}_{321}^{\text{bbl}} = 2 \cdot (P_{\text{RBOB}} \times 42.0) + 1 \cdot (P_{\text{HO}} \times 42.0) - 3 \cdot P_{\text{WTI}}
  \]
- **Refinery 3-2-1 Crack Margin Gallon-Equivalent ($\$ / \text{gal}$):**
  \[
  \text{Crack}_{321}^{\text{gal}} = \frac{2 \cdot P_{\text{RBOB}} + 1 \cdot P_{\text{HO}} - 3 \cdot \left(\frac{P_{\text{WTI}}}{42.0}\right)}{3.0} = \frac{\text{Crack}_{321}^{\text{bbl}}}{3 \cdot 42.0}
  \]

### C. Exponential Memory Decay Equation
Real-world event news persistence is modeled via exponential memory decay ($t_{1/2} = 4.0\text{ to }5.0\text{ days}$):
\[
\lambda = \frac{\ln(2)}{t_{1/2}}
\]
\[
\text{Memory}_t = \text{Memory}_{t-1} \times e^{-\lambda} + \text{Shock}_t
\]

### D. Official EIA Retail Evaluation Ground Truth (Issue #403)
Point-in-time model evaluation uses official EIA/FRED weekly retail pump prices across PADDs and states as objective evaluation ground truth ($y_{t+h}$ in `prediction_history.csv`).

---

## 2. Two-Tiered NOAA Weather Integration Architecture

The forecasting engine integrates a **two-tiered weather ingestion model** via the NOAA NWS API (`api.weather.gov`) and lightweight terminal connector `t.wxs.us`, combining macro energy basin risks with localized metro-level convective, freeze, and flood threats:

```
               ┌─────────────────────────────────────────────────────────────┐
               │                 NOAA NWS & SPC WEATHER API                  │
               │                   (api.weather.gov / t.wxs.us)              │
               └──────────────────────────────┬──────────────────────────────┘
                                              │
                   ┌──────────────────────────┴──────────────────────────┐
                   ▼                                                     ▼
   ┌───────────────────────────────┐                     ┌───────────────────────────────┐
   │ TIER 1: NATIONAL BASINS       │                     │ TIER 2: LOCALIZED METROS      │
   │ • Gulf Coast Hurricanes (NHC) │                     │ • Tulsa OK (OKZ060 / OKZ066)  │
   │ • Permian Basin Freeze Alerts │                     │ • Newark DE (Delaware City)   │
   │ • Bakken Shale Polar Vortexes │                     │ • Cincinnati OH/KY (Miss River)│
   │                               │                     │ • Greenville NC (NCZ081 Floods)│
   │                               │                     │ • Charlotte NC (NCZ071 Hub)   │
   │                               │                     │ • Oakland & Bay Area (PSPS)   │
   │                               │                     │ • Port St. Lucie FL (FLZ147)  │
   └───────────────┬───────────────┘                     └───────────────┬───────────────┘
                   │                                                     │
                   ▼                                                     ▼
   ┌───────────────────────────────┐                     ┌───────────────────────────────┐
   │ NATIONAL MODEL                │                     │ LOCALIZED METRO CALIBRATION   │
   │ (src/locations/national)      │                     │ (src/locations/<location>)    │
   │ • RBOB Wholesale Futures      │                     │ • Tulsa, Newark, Cincinnati,  │
   │ • Directional Acc: 60.79%     │                     │   Greenville, Charlotte,      │
   │                               │                     │   Oakland, Port St. Lucie     │
   └───────────────────────────────┘                     └───────────────┬───────────────┘
```

* **Token-Efficient Ingestion Engine (`t.wxs.us`):** Pre-filters NWS alerts and SPC convective outlooks down to ~150–300 tokens per request (a 90%–95% token savings vs raw 3,500-token GeoJSON feature maps).
* **Deterministic Risk Mapping:** Maps SPC convective risks (`HIGH`: 1.0, `MDT`: 0.8, `ENH`: 0.6, `SLGT`: 0.4, `MRGL`: 0.2, `NONE`: 0.0) directly into numerical impact feature vectors without LLM latency or token cost.

---

## 3. Stationary Return Target Modeling, Level Reconstruction & Purged Embargo CV (Issues #396, #397)

To ensure stationarity and prevent non-stationary drift or lookahead data leakage:
1. **Target Return Formulation:**
   Instead of predicting raw non-stationary price levels directly, quantitative models (Ridge/XGBoost) are trained on $h$-day forward percentage returns:
   \[
   \hat{r}_{t+h} = \frac{P_{t+h} - P_t}{P_t}
   \]
2. **Out-of-Sample Price Level Reconstruction:**
   Predicted returns are converted back to calibrated price levels ($/gal):
   \[
   \hat{P}_{t+h} = P_t \times (1 + \hat{r}_{t+h})
   \]
3. **Chronological Purge and Embargo Partitions:**
   When generating chronological train/test splits, an explicit boundary gap of $\text{forecast\_horizon} + \text{embargo\_steps}$ is enforced:
   \[
   \text{train\_slice\_end} = \max(1, \text{split\_idx} - (h + \text{embargo}))
   \]
   This prevents overlapping multi-day target returns $r_{t+h}$ from leaking information from the test evaluation window into model training.
4. **Purged Walk-Forward Cross-Validation (`RidgeCV`):**
   Model hyperparameter tuning ($\alpha$ penalty search) and comparative evaluation utilize `PurgedGroupTimeSeriesSplit(chronological_only=True)`. Each validation fold evaluates strictly on out-of-sample data following purged training splits.

---

## 4. MLOps Prediction Logging, Calibrated CI Evaluation & Backfilling Engine (`src/prediction_logger.py`)

All multi-horizon out-of-time forecasts are persisted directly to `data/prediction_history.csv` during daily execution runs. As forecast target dates mature, `src/prediction_logger.py` queries ground-truth historical market prices from official EIA retail feeds (`src/eia_retail_feed.py`) and national futures (`yfinance`), evaluating actual price outcomes, directional hit rates, and calibrated confidence interval coverage.

### 4.1. Injectable Evaluation Architecture (Issue #395)
`backfill_actual_prices_and_evaluate()` supports dependency injection parameters:
* `actuals_map_override: Optional[dict]`: Injects point-in-time commodity futures mappings without network queries.
* `eia_feed_override: Optional[Any]`: Injects mock or cached regional retail ground truth instances.
* `csv_path: Optional[str]`: Routes read/write operations to isolated evaluation test ledgers.
* `force_eval: bool`: Bypasses `TESTING=1` execution guards to ensure 100% test coverage of evaluation logic without external API calls.

### 4.2. Calibrated 95% Confidence Interval Coverage (Issue #394)
Prediction intervals are evaluated strictly against explicit forecast bounds without arbitrary fixed fallback bands:
\[
\text{Hit}_{95\text{CI}, i} = \begin{cases} 1 & \text{if } \hat{P}_{\text{lower}, 95, i} \le P_{\text{actual}, i} \le \hat{P}_{\text{upper}, 95, i} \\ 0 & \text{otherwise} \end{cases}
\]
When interval bounds are missing from legacy records, calibrated bands are dynamically reconstructed using regional residual standard error scaled by the forecast horizon:
\[
\sigma_{\text{res}}(h) = \sigma_{\text{res}} \times \sqrt{\frac{h}{5}}, \quad \hat{P}_{\pm 95} = \hat{P}_{\text{pred}} \pm 1.96 \cdot \sigma_{\text{res}}(h)
\]
The empirical 95% CI coverage rate is tracked and exposed in rolling scoreboard metrics:
\[
\text{Coverage}_{95\text{CI}} = \frac{1}{N} \sum_{i=1}^{N} \text{Hit}_{95\text{CI}, i} \times 100\%
\]

### 4.3. Live Forecast README Automation & Workflow Freshness Gating (Issue #398)
* **README Table Injector (`scripts/readme_updater.py` / `src/readme_updater.py`):** Automatically compiles multi-horizon projections across all 10 active regional hubs into the Markdown live summary table between `<!-- START_LIVE_FORECAST -->` and `<!-- END_LIVE_FORECAST -->` tags.
* **UTC vs Central DST Schedule Alignment:** GitHub Actions cron schedules (`17 7 * * *`) evaluate strictly on UTC (07:17 UTC); during Daylight Saving Time (March to November), US Central Time is CDT (02:17 AM CDT / UTC-5), and during standard time (November to March), Central Time is CST (01:17 AM CST / UTC-6).
* **Forecast Freshness Gating:** The public dashboard (`src/dashboard_generator.py`) evaluates the timestamp of the latest prediction record; if data age exceeds 36 hours, a warning badge (`Forecast Stale (>36h)`) is rendered to alert operators.

---

## 5. Weekly Model Performance Review & Issue Self-Review Engine (`src/weekly_issue_reporter.py` & `.github/workflows/weekly_model_review.yml`)

The weekly model performance review runs automatically on Saturday mornings (08:00 AM Central / 13:00 UTC) via GitHub Actions cloud runners and local `dev-vm` systemd user timers (`midgley-weekly-review.timer`). Its primary purpose is to calculate rolling multi-region error metrics, self-review all open GitHub repository issues, and operate an automated feedback loop back into the forecasting pipeline:

* **Open GitHub Issue Self-Review:** Fetches all open repository issues on `KoshiirRa/midgley`, evaluates each issue's modeling impact using Google Gemini 2.5 Flash (with a domain-specific keyword heuristic fallback), ranks issues, and selects the top issue offering the largest potential reduction to model loss.
* **Branch-Flagged Reporting:** Automatically flags issue titles with the source git branch (e.g. `[dev] 📊 Weekly Model Review Report...`).
* **Mean Absolute Error (MAE):**
  \[
  \text{MAE} = \frac{1}{N} \sum_{i=1}^{N} |P_{\text{actual}, i} - \hat{P}_{\text{pred}, i}|
  \]
* **Root Mean Squared Error (RMSE):**
  \[
  \text{RMSE} = \sqrt{\frac{1}{N} \sum_{i=1}^{N} (P_{\text{actual}, i} - \hat{P}_{\text{pred}, i})^2}
  \]
* **Directional Accuracy (%):**
  \[
  \text{Hit Rate} = \frac{1}{N} \sum_{i=1}^{N} \mathbb{I}\left(\text{sign}(\Delta P_{\text{actual}, i}) == \text{sign}(\Delta \hat{P}_{\text{pred}, i})\right) \times 100\%
  \]

### Continuous Feedback Loop Mechanics:
1. **Diagnostic Validation & Multi-Region Error Tracking:** Calculates rolling metrics across 30-day, 60-day, and 90-day evaluation windows across all active regions (National, Tulsa, Newark, Cincinnati OH/KY, Oakland, SF Bay Area).
2. **Quantitative Feature Leakage & Factor Decay Validation (`src/feature_auditor.py`, Issue #146):** Runs automated point-in-time temporal cross-correlations across EIA, FRED, NOAA, USDA, and futures series to detect lookahead leakage ($|r| > 0.50$), computes multi-horizon Spearman Rank IC decay curves ($H \in \{1, 3, 5, 10, 14, 20\}\text{ days}$) with empirical $t_{1/2}$ curve fitting, and estimates Probability of Backtest Overfitting (PBO via CSCV) / Deflated Sharpe Ratios (DSR).
3. **Estimator Hyperparameter Re-Calibration:** Feeds validation loss signals back into quantitative estimation, optimizing regularized Ridge regression alpha penalties ($\alpha = 10.0$) and re-fitting pipeline scalers.
4. **Feature Decay & Weight Optimization:** Adjusts exponential memory half-lives ($t_{1/2} = 4.0\text{ to }5.0\text{ days}$) and fine-tunes LLM prompt impact scoring weights based on empirical directional success rates.

---

## 6. Multi-Page Web Architecture & Routing (`src/dashboard_generator.py`)

The public presentation layer is compiled by `src/dashboard_generator.py` into static HTML artifacts and Open Graph social preview cards in `docs/`:

```
                               ┌──────────────────────────────────┐
                               │       docs/index.html (/)        │
                               │    Midgley Overview Landing      │
                               │  Summary Forecast Cards Grid     │
                               └────────────────┬─────────────────┘
                                                │
       ┌───────────────────────────────┬────────┴────────┬───────────────────────────────┐
       ▼                               ▼                 ▼                               ▼
┌──────────────┐              ┌──────────────────┐ ┌──────────────┐              ┌──────────────┐
│ /national    │              │ METRO AREAS MENU │ │ /math        │              │ /reports     │
│ Wholesale    │              ├──────────────────┤ │ KaTeX Math   │              │ Technical    │
│ RBOB Futures │              │ • /tulsa (OK)    │ │ Equations &  │              │ Run Reports  │
│ Analytics    │              │ • /newark (DE)   │ │ 10-Layer     │              │ & Run JSONs  │
└──────────────┘              │ • /cincinnati(OH)│ │ Architecture │              └──────────────┘
                              │ • /greenville(NC)│ └──────────────┘
                              │ • /charlotte (NC)│
                              │ • /oakland (CA)  │
                              │ • /bayarea (CA)  │
                              └────────┬─────────┘
                                       │
                                       ▼
                       ┌────────────────────────────────┐
                       │ data/regional_metadata/*.json  │
                       │ Decoupled JSON Driver Cards    │
                       │ (render_regional_driver_cards) │
                       └────────────────────────────────┘
```

Static web routing compatibility is preserved across both direct file routes (`/<page>.html`) and clean directory routes (`/<page>/index.html`) by outputting dual matching file trees (e.g. `docs/tulsa.html` and `docs/tulsa/index.html`). 

Visual driver cards detailing regional econometric factors, refining logistics, statutory tax burdens, and delivery hub equations are rendered dynamically from decoupled JSON profiles (`data/regional_metadata/<region_id>.json`) via `render_regional_driver_cards_html()`, decoupling UI HTML templates from domain metadata.

---

## 7. Local Dev Environment & Permanent Web Server (`dev-vm` Port 8080)

To support rapid iteration and local testing, a dedicated Linux dev environment is configured on `dev-vm`:

* **Permanent `dev` Branch:** A permanent development branch (`origin/dev`) is maintained in the project workspace.
* **Systemd User Service (`midgley-dev.service`):** Runs `python3 -m http.server 8080 --directory docs` as a background user service under systemd.
* **Service Persistence & Linger:** User linger is enabled (`loginctl enable-linger`), allowing the dev web server to start automatically at system boot and persist without an open SSH session. Automatic restart (`Restart=always`) ensures high availability against process crashes.
* **Self-Hosting Guide:** Full systemd service definitions, edge cache configurations, and deployment procedures are documented in [`docs/SELF_HOSTING.md`](SELF_HOSTING.md).

---

## 8. Automated Nightly Dev Release Pipeline (`.github/workflows/nightly_dev_release.yml`)

The project operates an automated release pipeline targeting the `dev` branch:

* **Trigger Schedule:** Scheduled at `0 8 * * *` (03:00 AM Central Time / 08:00 UTC) every night.
* **Pre-Release Tagging:** Publishes pre-release tags in format `dev-YYYY-MM-DD`.
* **Automated Release Notes:** Dynamically computes commit history and pull request contributions between consecutive nightly tags, attaching formatted Markdown release notes to the GitHub Release.

## 9. Modular Location Subpackage Hierarchy (`src/locations/`)

All location-specific forecasting pipelines, regional market data fetchers, event log loaders, and Jupyter notebook builders are organized into a clean, modular subpackage hierarchy under `src/locations/`:

```
src/locations/
├── __init__.py                # Master location registry (LOCATIONS dict, get_location(), list_locations())
├── national/                  # National Wholesale RBOB Futures location package
│   ├── __init__.py
│   ├── main.py                # Main national forecasting pipeline
│   └── notebook_builder.py    # Builds notebooks/gas_price_llm_forecasting.ipynb
├── tulsa/                     # Tulsa Metro, OK location package
│   ├── __init__.py
│   ├── main.py                # Tulsa regional pipeline
│   ├── regional.py            # Tulsa market data & regional events
│   └── notebook_builder.py    # Builds notebooks/tulsa_gas_price_llm_forecasting.ipynb
├── newark/                    # Newark Metro, DE location package
│   ├── __init__.py
│   ├── main.py
│   ├── regional.py
│   └── notebook_builder.py
├── cincinnati/                # Cincinnati Tri-State, OH/KY location package
│   ├── __init__.py
│   ├── main.py
│   ├── regional.py
│   └── notebook_builder.py
├── greenville/                # Greenville Metro, NC location package
│   ├── __init__.py
│   ├── main.py
│   ├── regional.py
│   └── notebook_builder.py
├── charlotte/                 # Charlotte Metro, NC location package
│   ├── __init__.py
│   ├── main.py
│   ├── regional.py
│   └── notebook_builder.py
└── oakland/                   # Oakland & SF Bay Area, CA location package
    ├── __init__.py
    ├── main.py
    ├── regional.py
    └── notebook_builder.py
```

---

## 10. Qualitative Intelligence Knowledge Graph & Agent Memory Layer (`src/knowledge_graph.py`, Issue #116)

Midgley features an embedded zero-cost **Knowledge Graph & Agent Memory Layer**:

* **Graph Engine & Persistence:** Pure Python `NetworkX` graph core with `SQLite` persistence (`data/knowledge_graph.db`), ensuring **$0 infrastructure cost**.
* **Automated Seeding:** Automatically populates 9 refineries, 4 marine chokepoints, 5 PADDs, and 6 metro hubs on initial startup from `src/spatial_refinery.py`.
* **GraphRAG Prompt Context:** Extracts 2-hop subgraphs and precedent memories for incoming headlines, formatting standardized `GraphContextSchema` into LLM prompts (`LLM_SINGLE_PROMPT`) to ground scoring calls with physical supply topology.
* **Episodic Shock Memory & Precedent Search:** Ingests high-impact event shocks into `kg_memory_shocks`, supporting TF-IDF + graph distance precedent retrieval.
* **Council of LLMs Readiness:** Standardizes context serialization across multi-provider LLM ensembles while recording multi-model attribution, individual provider opinions, and consensus disagreement metrics (`council_variance`).

Root entrypoints (`main.py`, `tulsa_main.py`, `newark_main.py`, etc.), notebook build scripts (`build_*.py`), and `src/*_regional.py` modules operate as lightweight delegation shims to `src/locations/`, maintaining 100% backward compatibility for all existing scripts, workflows, and systemd services.

---

## 11. Multi-Tier Lookup Cache Gateway Architecture (Issue #108 / `src/lookup_cache.py`)

All external data ingestion connectors (REST APIs, Socrata open data, EIA/FRED/USDA series, NOAA weather endpoints, commodity spot feeds, and financial news/scrapers) are integrated with the **3-Tier Lookup Cache Gateway** (`src/lookup_cache.py`). This architecture eliminates redundant API requests and synchronizes quota limits across local Dev VM (`10.42.42.54`) and GitHub Actions runners:

```
┌─────────────────────────────────────────────────────────────────────────────┐
│                    EXTERNAL DATA CONNECTORS & FEEDS                         │
│  • EIA, FRED, USDA, OilpriceAPI, Alpha Vantage, Socrata Open Data           │
│  • GasBuddy, AAA, NOAA Weather, USGS Water & Seismic, Multi-Feed AQI        │
└──────────────────────────────────────┬──────────────────────────────────────┘
                                       │
                                       ▼
┌─────────────────────────────────────────────────────────────────────────────┐
│              MULTI-TIER LOOKUP CACHE GATEWAY (`src/lookup_cache.py`)        │
├─────────────────────────────────────────────────────────────────────────────┤
│ • Tier 1 (Primary Edge): Turso Edge SQLite REST API (TURSO_DATABASE_URL)    │
│ • Tier 2 (Backup Edge):  Cloudflare D1/R2 Edge Worker (CLOUDFLARE_CACHE_URL)  │
│ • Tier 3 (Local Core):   SQLite Datastore (`data/lookup_cache.sqlite`) +    │
│                          In-Memory Fast Dict (`global_cache`)              │
└──────────────────────────────────────┬──────────────────────────────────────┘
                                       │
                                       ▼
┌─────────────────────────────────────────────────────────────────────────────┐
│                      LOCAL DISK JSON FALLBACK                               │
│             (`data/{source}_cache.json` / Offline Benchmark)                 │
└─────────────────────────────────────────────────────────────────────────────┘
```

### Key Technical Specifications:
* **Key Namespacing:** Prefixed by service domain (e.g., `oilpriceapi_{key}`, `alphavant_{key}`, `eia_{series_id}`, `fred_{series_id}`, `socrata_{state}_{dataset}`).
* **TTL Policy:** Standardized by data type (15 minutes for live retail scrapers, 1 hour for weather alerts, 24 hours for commodity spot prices, 60 days for quota ledgers).
* **Quota Synchronization:** Dual-environment quota ledger sync via `global_cache.get_quota_ledger(service)` and `global_cache.update_quota_ledger(service, ...)`.

---

## Cloudflare Edge Workers & Option A2 Telemetry Architecture

Midgley deploys two Cloudflare Edge Workers to handle edge triggers and multi-tier edge caching:

1. **`midgley-intraday-monitor` ([workers/intraday_monitor_worker.ts](file:///c:/Users/concentus/Documents/Random%20Ideas%20-%20LLM%20Unleaded%20Gas%20Price%20Prediction%20Modelling/workers/intraday_monitor_worker.ts)):**
   * Executes every 15 minutes via Cloudflare Cron Triggers (`*/15 * * * *`).
   * Scans 5 primary energy RSS streams, runs fast-path keyword/regex anomaly detection (filtering non-energy macro tariffs and agricultural cooking oils like canola), deduplicates dispatched items against Cloudflare D1 database (`midgley-cache-d1` `seen_rss_headlines`) across all global PoPs, and fires GitHub Repository Dispatch events (`event_type: "intraday_anomaly"`).

2. **`midgley-cache-worker` ([workers/cache_worker.ts](file:///c:/Users/concentus/Documents/Random%20Ideas%20-%20LLM%20Unleaded%20Gas%20Price%20Prediction%20Modelling/workers/cache_worker.ts)):**
   * Acts as Tier 2 Edge Cache Gateway over Cloudflare D1 database (`midgley-cache-d1`).
   * Serves `/api/v1/cache/:key` GET/POST endpoints and `/status` health probes with optional Bearer Token authentication.

### Option A2 Observability & Telemetry Engine

```
                             ┌──────────────────────────────────┐
                             │    CLOUDFLARE WORKER INVOCATION  │
                             └────────────────┬─────────────────┘
                                              │
                 ┌────────────────────────────┼────────────────────────────┐
                 │                            │                            │
                 ▼                            ▼                            ▼
  ┌─────────────────────────────┐ ┌─────────────────────────────┐ ┌─────────────────────────────┐
  │ CLOUDFLARE DASHBOARD LOGS   │ │    AXIOM LOG ANALYTICS      │ │  SENTRY CRASH REPORTING     │
  │ • Real-time tail logs       │ │ • 30-day searchable events  │ │ • Uncaught exception stack  │
  │ • Invocation trace graphs   │ │ • `logToAxiom()` HTTPS REST │ │   traces & sourcemaps       │
  │ • Native persistent logs    │ │ • Dataset: `midgley-workers`│ │ • `captureSentryException()`│
  └─────────────────────────────┘ └─────────────────────────────┘ └─────────────────────────────┘
```

* **Cloudflare Native Observability:** Configured in `wrangler.toml` and `wrangler.cache.toml` with `[observability]` (`enabled = true`, `head_sampling_rate = 1.0`, `persist = true`).
* **Axiom Log Analytics (`logToAxiom`):** Ingests structured JSON cycle summaries, RSS warnings, GitHub dispatches, and cache hits/misses directly to Axiom dataset `midgley-workers` via `ctx.waitUntil()` async flushes (0 HTTP latency penalty, $0 subscription cost).
* **Sentry Crash Reporting & Crons (`captureSentryException` & `sendSentryCronCheckIn`):** Captures unhandled runtime errors with stack trace context and executes 2-stage Sentry Cron check-ins (`in_progress` start ping + `ok`/`error` completion ping with matching `check_in_id`) for execution duration tracking and timeout detection.
* **Axiom & Sentry Dashboard Templates & APL Queries:** See [`docs/OBSERVABILITY_DASHBOARDS.md`](file:///c:/Users/concentus/Documents/Random%20Ideas%20-%20LLM%20Unleaded%20Gas%20Price%20Prediction%20Modelling/docs/OBSERVABILITY_DASHBOARDS.md) for ready-to-use APL queries, dashboard widget templates, and alert rules.

---

## 11. System Telemetry Prometheus Metrics & Zero-Cost Cloud Archiving (Issues #107 & #197)

### Prometheus Telemetry Exporter (`/metrics` & `/api/v1/metrics`)
Midgley exposes a standard Prometheus exposition text format endpoint (`GET /api/v1/metrics` and `GET /metrics` in `src/api_server.py`) for Grafana observability:
* **TokenTab Metrics:** `llm_tokens_consumed_total` (by prompt/completion/total) and `llm_estimated_cost_usd_total`.
* **IPASIS Security Metrics:** `ipasis_security_requests_total` tracking checked vs. blocked inbound requests.
* **Multi-Tier Cache Metrics:** `cache_gateway_operations_total` tracking hit vs. miss ratios across lookup tiers.
* **API Quota Ratios:** `api_quota_remaining_ratio` tracking remaining allowances across Finlight, OilpriceAPI, and AlphaVantage.

### Zero-Cost Internet Archive Wayback Machine Cloud Archiver (`src/wayback_archiver.py`)
During intraday event evaluations in `src/intraday_event_monitor.py`, breaking headline URLs are submitted directly to the Internet Archive Save API (`https://web.archive.org/save/{url}`). The permanent `archive_url` string is attached to the event result object, saved in `data/intraday_events.json`, and cached locally at `data/wayback_archive_cache.json` for 100% zero-cost cloud web archiving.

---

## 12. Real-Time Discord Webhook Notification Gateway (Issue #234)

```
       ┌─────────────────────────────────────────────────────────────┐
       │   INTRADAY SHOCK DETECTED (IntradayEventMonitor / Edge)     │
       └──────────────────────────────┬──────────────────────────────┘
                                      │
                                      ▼
       ┌─────────────────────────────────────────────────────────────┐
       │      DISCORD NOTIFICATION ENGINE (src/discord_notifier.py)   │
       │  • Evaluates Environment (MIDGLEY_ENV: 'prod' vs 'dev')     │
       │  • Formats Rich Discord Embed (Color: Red / Green / Orange) │
       │  • Attaches Headline, Source, Target Locales & Factor Vector│
       │  • Attaches Original Article & Wayback Machine Archive URLs │
       └──────────────────────────────┬──────────────────────────────┘
                                      │ HTTP POST (10s Timeout, Non-blocking)
                                      ▼
       ┌─────────────────────────────────────────────────────────────┐
       │             DISCORD CHANNEL INCOMING WEBHOOK                │
       │   🚨 [PRODUCTION] or [DEVELOPMENT] Intraday Revision Alert  │
---

## 13. Chronological 15-Section Mathematical Framework & Pipeline Execution (Issues #224, #225, #226, #227, #229)

The mathematical documentation in [`docs/math.html`](file:///docs/math.html) and generation engine in [`src/dashboard_generator.py`](file:///src/dashboard_generator.py) follow a strict 15-section chronological execution pipeline:

1. **`01` Commodity Futures & 3-2-1 Crack Spread:** NYMEX RBOB ($P_{\text{RBOB}}$), WTI ($P_{\text{WTI}}$), ULSD Heating Oil ($P_{\text{ULSD}}$), and standard 3-2-1 crack spread $\text{Crack}_{321} = \frac{2 \cdot P_{\text{RBOB}} + 1 \cdot P_{\text{ULSD}} - 3 \cdot (P_{\text{WTI}} / 42)}{3}$.
2. **`02` Alternative Physical Feeds & Positioning:** 7 quantitative macro and positioning feeds: Cboe OVX, Baker Hughes Rig Counts, 10-Year Treasury Yields, 10-Year TIPS Breakevens, CFTC COT Managed Money Net Longs, FERC Natural Gas / LNG Spark Spreads, and USDA/EIA Ethanol/RIN blendstock margins.
3. **`03` Live News Streams, Web Scraping & Multi-Tiered LLM Extraction:** Finlight financial news stream (150/mo cap), Firecrawl JavaScript web scraper (800/mo cap & 24h caching), zero-cost RSS polling ($<24\text{h}$ filter), webhook push with IPASIS security verification, and 3-tier LLM failover (Gemini 2.5 Flash $\rightarrow$ GPT-4o-mini $\rightarrow$ Offline Lexicon).
4. **`04` Executive Social Media & Weekend Gap Dynamics:** Social shock vector $\mathbf{V}_{\text{social}, t}$ with empirical regression weights ($\beta_{\text{OPEC}} = -1.85\%$, $\beta_{\text{tariff}} = +2.10\%$) and the $1.42\times$ weekend market close multiplier applied on Monday open reopening.
5. **`05` Multi-Tiered NOAA Weather Risk:** 2-tiered weather ingestion via `t.wxs.us` lightweight terminal endpoints with deterministic SPC convective risk mapping ($90\%-95\%$ token reduction).
6. **`06` Maritime Chokepoints & Inland Waterways:** Hormuz, Suez, Bab el-Mandeb, Delmarva detour, and Mississippi/Ohio River tow draft restrictions.
7. **`07` USGS 3D Hypocentral Seismic Attenuation & AQI Outage Risk:** USGS earthquake hypocentral distance modeling $D_{\text{hypo}} = \sqrt{d_{\text{epicenter}}^2 + \text{depth}^2}$, facility criticalities, and industrial AQI flaring detection.
8. **`08` Microsoft Qlib Alpha Factor Mining & Spectral CoSPOT:** Qlib symbolic expression mining, Discrete Fourier Transform (DFT), Discrete Wavelet Transform (DWT), and spectral entropy features.
9. **`09` Econometric Exponential Memory Decay & Category Shock Fusion:** Recursive decay $\mathbf{M}_t = \mathbf{M}_{t-1} \cdot \exp(-\ln 2 / t_{1/2}) + \mathbf{V}_t$ with category half-lives ($t_{1/2} \in [2.5, 14.0]\text{ days}$) and Context Routing Diagnostic Fusion weighting $\omega_{\text{fusion}} \in [0.85, 1.25]$.
10. **`10` Standardized Ridge Estimator & Purged CPCV:** Regularized regression ($\alpha=10.0$) evaluated via Purged Combinatorial Cross-Validation to eliminate temporal leakage.
11. **`11` CARB Regulatory Burden & PADD 5 Island Isolation:** Reconciled statutory California fuel tax burden $T_{\text{CARB}} = \$0.953/\text{gal}$.
12. **`12` Ultra-Low Sulfur Diesel (ULSD) & Distillate Margin:** Distillate hydrocracking margin modeling.
13. **`13` Dynamic Volatility-Gated Persistence Blending (DV-GPB) & Empirical Residual CI:** Sigmoidal gating parameter $\lambda_{\text{vol}}$ transitioning between Naive Persistence and active event shock forecasts, with $\pm 1.96 \cdot \sigma_{\text{residual, 30d}}$ empirical CI coverage ($\ge 90.0\%$).
14. **`14` Local Metro Basis Differentials & Spatial Freight:** Local rack margin adjustments across 10 metro calibration hubs.
15. **`15` End-to-End Master Prediction Synthesis:** Signed component-level factor attribution breakdown across 6 standardized economic domains.

---

## 14. CoSPOT Spectral Prompting & Hindsight Episodic Agent Memory (Issues #215, #230 & #421)

* **CoSPOT Spectral Feature Prompting Engine ([`src/cospot_spectral_engine.py`](file:///src/cospot_spectral_engine.py), arXiv:2609.02093):** Injects DFT frequency regime descriptors and DWT wavelet shock magnitudes into Gemini 2.5 Flash prompts, eliminating LLM numerical blindness during breaking market events.
* **Vectorize Hindsight Episodic Agent Memory ([`src/agent_memory.py`](file:///src/agent_memory.py) & [`src/hindsight_client.py`](file:///src/hindsight_client.py)):** Biomimetic Retain-Recall-Reflect triad storing forecast experiences, performing zero-LLM analogy recall, and synthesizing qualitative post-mortems for Saturday weekly model reviews, backed by Vectorize Hindsight-Hosted SaaS (Issue #421), local Dev-VM Docker container, and local SQLite FTS5 fallback.
  - **Zero-Cold-Start Hosted Gateway:** Connects to `https://api.hindsight.vectorize.io` with Bearer auth, eliminating the compute cost and 75-second cold boot latencies associated with serverless Cloud Run containers.
  - **Standardized Bank Mission & Reasoning Profiles (`Midgley`):**
    - **Retain Extraction:** Concise extraction of quantitative prediction deviations ($|error| \ge \$0.25/\text{gal}$ or directional flips), physical supply catalysts (refinery outages, pipeline shut-ins, maritime navigation restrictions, EPA/CARB RVP deadlines), and calendar spreads.
    - **Observations Consolidation:** Consolidates durable market dynamics, localized basis spreads (Tulsa, Newark, Cincinnati, Carolinas, Oakland, Port St. Lucie), regulatory blend transitions, and weekly model recalibration lessons into persistent economic beliefs.
    - **Reflect Post-Mortems & Analogies:** Synthesizes qualitative root causes and parameter adjustments (shock decay half-lives $t_{1/2}$, seasonal transition buffers), parameterized with **Skepticism: 4/5**, **Literalism: 4/5**, and **Empathy: 1/5** (Detached).
  - **Socket Read Timeout Retries:** Configurable socket timeout (`HINDSIGHT_TIMEOUT`) with 2-attempt retries and exponential backoff.
  - **Zero-Data-Loss Reconciliation Ledger:** SQLite `cloud_synced` column auto-migration and `sync_pending_memories()` draining locally queued experiences once the remote bank is reachable.

---

## 15. System Telemetry, Connector Health Auditing & Observability Architecture (Issue #237)

```
        ┌─────────────────────────────────────────────────────────────┐
        │            SYSTEM OBSERVABILITY & TELEMETRY HUB             │
        │             (src/telemetry.py & src/dashboard_generator.py) │
        └──────────────┬──────────────────────────────┬───────────────┘
                       │                              │
         ┌─────────────┴────────────┐   ┌─────────────┴────────────┐
         ▼                          ▼   ▼                          ▼
┌──────────────────┐       ┌──────────────────┐       ┌──────────────────┐
│ HINDSIGHT MEMORY │       │ CONNECTOR AUDIT  │       │ FALLBACK SAVINGS │
│ Retain / Recall  │       │ 7-Day EIA, FRED, │       │ Basic Tier &     │
│ & Hosted SaaS vs │       │ USDA, NOAA, AAA, │       │ Lexicon Routing  │
│ SQLite FTS5 Hub  │       │ Socrata & USGS   │       │ Spared LLM $ & Tk│
└──────────────────┘       └──────────────────┘       └──────────────────┘
```

* **Vectorize Hindsight Observability:** Tracks real-time memory operation volume (`retain_count`, `recall_count`, `reflect_count`), hosted cloud bank (`Midgley`) vs local SQLite FTS5 routing, and database experience totals.
* **7-Day Connector Health Audit:** Ingests `src.connector_telemetry` to compute 7-day request volumes, failure rate %, latency, and cache freshness across all zero-cost open data connectors.
* **Zero-Cost Fallback & Dollar Savings Accounting:** Ingests `src.fallback_telemetry` to monitor Basic Tier zero-cost routing and calculate cumulative dollar/token savings.
* **Hard Quota Safety Valves:** Monitors Firecrawl (800/mo cap, 30/day burst limit), Finlight (150/mo cap, 10/day burst limit), and IPASIS Security Verifier (100 req/day cap).
* **Dynamic Out-of-Metro Leaflet Map:** Renders real-time geographic clusters of out-of-metro forecast lookups from `src.telemetry.get_unmapped_zip_telemetry()`.

---

## 16. Seasonal & Climatological Plausibility Gating Engine (Issue #300)

The scenario simulation architecture integrates a **Dynamic Climatological & Meteorological Plausibility Gating Engine** ([`src/scenario_engine.py`](file:///c:/Users/concentus/Documents/Random%20Ideas%20-%20LLM%20Unleaded%20Gas%20Price%20Prediction%20Modelling/src/scenario_engine.py)) ensuring shock simulations and counterfactual stress tests align with physical seasons, regulatory calendar windows, and real-time environmental telemetry:

![Seasonal Plausibility Gating Engine SVG Diagram](docs/assets/scenario_engine_architecture.svg)

```
                  ┌─────────────────────────────────────────────────────────────┐
                  │                 SCENARIO INVOCATION REQUEST                 │
                  │              (REST API, MCP Tool, or Weekly Audit)          │
                  └──────────────────────────────┬──────────────────────────────┘
                                                 │
                                                 ▼
                  ┌─────────────────────────────────────────────────────────────┐
                  │         1. REGISTRY LOOKUP & DATE-WINDOW EVALUATION         │
                  │       (SCENARIO_CLIMATOLOGY_REGISTRY & Date-Math Logic)     │
                  └──────────────────────────────┬──────────────────────────────┘
                                                 │
                     ┌───────────────────────────┴───────────────────────────┐
                     ▼                                                       ▼
      ┌──────────────────────────────┐                       ┌──────────────────────────────┐
      │   DATE OUTSIDE SEASON WINDOW │                       │    DATE WITHIN SEASON WINDOW │
      │   • Status: SEASONALLY_DORMANT                       │    • Status: SEASONALLY_PLAUSIBLE│
      │   • Counterfactual Warning   │                       │    • Plausibility Score: 0.70    │
      └──────────────┬───────────────┘                       └──────────────┬───────────────┘
                     │                                                       │
                     │                 ┌─────────────────────────────────────┘
                     │                 │ Live Physical Telemetry Triggered?
                     │                 ▼
                     │       ┌──────────────────────────────────────┐
                     │       │ ACTIVE PHYSICAL THREAT IDENTIFIED   │
                     │       │ • Status: ACTIVE_THREAT (Score 1.00) │
                     │       │ • NOAA SPC Risk, USGS Stage/Flow/Temp│
                     │       └──────────────────┬───────────────────┘
                     │                          │
                     ▼                          ▼
      ┌─────────────────────────────────────────────────────────────────────┐
      │                2. PROSPECTIVE PRECURSOR SYNTHESIS                   │
      │    (1–14 Days Lead Time for RVP Transition, Storms, Runoff)        │
      └──────────────────────────────────┬──────────────────────────────────┘
                                         │
                                         ▼
      ┌─────────────────────────────────────────────────────────────────────┐
      │            3. MULTI-HUB WEEKLY STRESS AUDIT & REPORTING             │
      │    (Plausibility Matrix & Seasonal Issue Ranking in Saturday Review)│
      └─────────────────────────────────────────────────────────────────────┘
```

* **Plausibility Status Classification (`PlausibilityStatus`):**
  - `ACTIVE_THREAT`: Live physical or meteorological sensor triggers (e.g. NOAA SPC convective risk $\ge 0.40$, USGS Ohio River stage $> 52\text{ ft}$, USGS Carquinez flow $> 40,000\text{ cfs}$) confirm an active or impending hazard.
  - `SEASONALLY_PLAUSIBLE`: Target date falls within the climatological hazard window (e.g. Atlantic Hurricane season June 1 – Nov 30).
  - `SEASONALLY_DORMANT`: Target date falls outside the historical occurrence window. Simulation proceeds as a counterfactual with explicit warning annotations.
  - `EVERGREEN`: Macro geopolitical, cybersecurity, or refinery mechanical failures applicable year-round.
  - `PROSPECTIVE_FORWARD`: Precursor scenarios generated 1–14 days ahead of seasonal regulatory spec switches (e.g. CARB Summer RVP transition Feb 15 / May 1) or storm landfalls.
* **REST API & MCP Tool Integration:**
  - `GET /api/v1/forecast/scenarios`: Returns catalog of scenarios filtered by `active_only`, `locale`, or `target_date`.
  - `POST /api/v1/forecast/simulate` & MCP `simulate_fuel_market_shock`: Enriched with `plausibility` object containing status, numerical score, and warning annotations.
  - MCP `list_market_shock_scenarios`: Tool for agents to discover available shocks and seasonal validity.
* **Weekly Review Feedback Loop:** `src/weekly_issue_reporter.py` embeds the **Forward Plausibility Horizon Matrix**, multi-hub stress audits, and applies seasonal priority boosts ($\times 1.25$) to open GitHub issues matching active threats.

---

## 17. MLOps Ground Truth Integrity, Plausibility Guards & History Sanitation (Issues #391, #392, #399)

1. **Official EIA/FRED Regional Ground Truth:** Regional metro actual price outcomes are resolved strictly from official weekly EIA retail series via `EIARetailFeed` (`src/eia_retail_feed.py`).
2. **Elimination of Synthetic Offsets:** Hardcoded offset ladders (such as `RB=F + $0.55` or `RB=F + $2.05`) and identity fallbacks (`margin_offset = base_price - raw_actual`) are eliminated. If real ground-truth data is unavailable for a date or region, the observation is recorded as unobserved (`np.nan`), preventing artificial directional hits or forced `actual_direction = UP` biases.
3. **Plausibility Validation Guards (`validate_price_plausibility`):** Enforces strict economic boundaries on historical and incoming price inputs:
   - Retail Gasoline Plausibility: $\$1.00/\text{gal} \le P_{\text{Retail}} \le \$10.00/\text{gal}$.
   - Wholesale RBOB Futures Plausibility: $\$0.50/\text{gal} \le P_{\text{Wholesale}} \le \$7.00/\text{gal}$.
4. **Production History Cleansing (`cleanse_prediction_history`):** Automated purification routine purges test fixture entries (`Test_Region`, `Test_*`) and invalid records from `data/prediction_history.csv`.
5. **Disk-Backed Actuals Caching:** National futures actuals are cached locally in `data/rbob_actuals_cache.json`, preventing redundant full-series network calls during backfill cycles.

