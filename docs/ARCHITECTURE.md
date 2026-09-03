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
  T_{\text{CARB}} = \tau_{\text{Excise}} + \tau_{\text{CapTrade}} + \tau_{\text{LCFS}} + \tau_{\text{Local/UST}} + \tau_{\text{Federal}} = \$0.634 + \$0.250 + \$0.185 + \$0.150 + \$0.184 = \$0.953/\text{gal}
  \]


### B. Exponential Memory Decay Equation
Real-world event news persistence is modeled via dynamic category-specific exponential memory decay ($t_{1/2} \in [2.5, 14.0]\text{ days}$ depending on shock taxonomy: $14.0\text{d}$ physical supply disruption, $7.0\text{d}$ geopolitical risk, $5.0\text{d}$ OPEC action, $4.0\text{d}$ demand sentiment, $2.5\text{d}$ executive social posts):
\[
\lambda(\text{category}) = \frac{\ln(2)}{t_{1/2}(\text{category})}
\]
\[
\text{Memory}_t = \text{Memory}_{t-1} \times e^{-\lambda(\text{category})} + \text{Shock}_t
\]

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
   └───────────────┬───────────────┘                     └───────────────┬───────────────┘
                   │                                                     │
                   ▼                                                     ▼
   ┌───────────────────────────────┐                     ┌───────────────────────────────┐
   │ NATIONAL MODEL                │                     │ LOCALIZED METRO CALIBRATION   │
   │ (src/locations/national)      │                     │ (src/locations/<location>)    │
   │ • RBOB Wholesale Futures      │                     │ • Tulsa, Newark, Cincinnati,  │
   │ • Directional Acc: 60.79%     │                     │   Greenville, Charlotte,      │
   │                               │                     │   Oakland & SF Bay Area       │
   └───────────────────────────────┘                     └───────────────┬───────────────┘
```

* **Token-Efficient Ingestion Engine (`t.wxs.us`):** Pre-filters NWS alerts and SPC convective outlooks down to ~150–300 tokens per request (a 90%–95% token savings vs raw 3,500-token GeoJSON feature maps).
* **Deterministic Risk Mapping:** Maps SPC convective risks (`HIGH`: 1.0, `MDT`: 0.8, `ENH`: 0.6, `SLGT`: 0.4, `MRGL`: 0.2, `NONE`: 0.0) directly into numerical impact feature vectors without LLM latency or token cost.

---

## 3. Live Pump Price Anchoring & Return Modeling

Instead of predicting raw non-stationary price levels directly, the model learns **5-day percentage price returns** ($\Delta \%$):
\[
\Delta \%_t = \frac{P_{t+5} - P_t}{P_t}
\]
The forecasted price calibrated to live pump prices ($P_{\text{Live}} = \$3.89/\text{gal}$) is calculated as:
\[
\hat{P}_{t+5} = P_{\text{Live}} \times (1 + \hat{\Delta}_{\%})
\]

---

## 4. MLOps Prediction Logging, Feature Attribution & Rolling Scoreboard Engine (`src/prediction_logger.py` & `src/models.py`)

All 5-day out-of-time forecasts are persisted directly to `data/prediction_history.csv` during daily execution runs. As forecast target dates mature, `src/prediction_logger.py` queries ground-truth historical market prices from `yfinance` and populates actual price records.

### Feature Attribution (XAI) Breakdown
`compute_locale_feature_attribution_breakdown` in `src/models.py` decomposes the total projected forecast delta ($\Delta = P_{\text{pred}} - P_{\text{base}}$) into signed dollar contributions ($/gal) across 6 core domain drivers:
1. **Futures & Commodity Benchmark** ($\Delta_{\text{futures}}$)
2. **Refining Yield & Crack Spread** ($\Delta_{\text{crack}}$)
3. **Weather & Environmental Signals** ($\Delta_{\text{weather}}$)
4. **Tax & Regulatory Overhead** ($\Delta_{\text{tax}}$)
5. **Unstructured Intelligence & Sentiment** ($\Delta_{\text{sentiment}}$)
6. **Regional Logistics & Hub Delivery** ($\Delta_{\text{logistics}}$)

Enforcing exact sum equality: $\sum_{k=1}^6 \Delta_k = P_{\text{pred}} - P_{\text{base}}$.

### Realized-vs-Predicted Rolling Scoreboard
`compute_rolling_scoreboard_metrics(window_days=30)` continuously evaluates model performance over rolling 30, 60, 90, and all-time windows, computing:
- **Mean Absolute Error (MAE)**: $\text{MAE} = \frac{1}{N} \sum |y - \hat{y}|$
- **Root Mean Squared Error (RMSE)**: $\text{RMSE} = \sqrt{\frac{1}{N} \sum (y - \hat{y})^2}$
- **Mean Absolute Percentage Error (MAPE)**: $\text{MAPE} = \frac{1}{N} \sum \left|\frac{y - \hat{y}}{y}\right| \times 100$
- **Directional Hit Rate**: $\text{Hit Rate} = \frac{\sum \mathbb{I}(\text{dir}_{\text{pred}} = \text{dir}_{\text{actual}})}{N} \times 100$
- **Naive Persistence Baseline Comparison & Model MAE Uplift**: $\text{Uplift}_{\text{MAE}} = \frac{\text{MAE}_{\text{naive}} - \text{MAE}_{\text{model}}}{\text{MAE}_{\text{naive}}} \times 100$

Exposed live via REST API `GET /api/v1/forecast/scoreboard` and rendered dynamically on the GitHub Pages web dashboard (`docs/index.html`).

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
2. **Estimator Hyperparameter Re-Calibration:** Feeds validation loss signals back into quantitative estimation, optimizing regularized Ridge regression alpha penalties ($\alpha = 10.0$) and re-fitting pipeline scalers.
3. **Feature Decay & Weight Optimization:** Adjusts exponential memory half-lives ($t_{1/2} = 4.0\text{ to }5.0\text{ days}$) and fine-tunes LLM prompt impact scoring weights based on empirical directional success rates.

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

Root entrypoints (`main.py`, `tulsa_main.py`, `newark_main.py`, etc.), notebook build scripts (`build_*.py`), and `src/*_regional.py` modules operate as lightweight delegation shims to `src/locations/`, maintaining 100% backward compatibility for all existing scripts, workflows, and systemd services.

---

## 10. Multi-Tier Lookup Cache Gateway Architecture (Issue #108 / `src/lookup_cache.py`)

All external data ingestion connectors (REST APIs, Socrata open data, EIA/FRED/USDA series, NOAA weather endpoints, commodity spot feeds, and financial news/scrapers) are integrated with the **3-Tier Lookup Cache Gateway** (`src/lookup_cache.py`). This architecture eliminates redundant API requests and synchronizes quota limits across local Dev VM (`10.42.42.54`) and GitHub Actions runners:

```
┌─────────────────────────────────────────────────────────────────────────────┐
│                    EXTERNAL DATA CONNECTORS & FEEDS                         │
│  • EIA, FRED, USDA, OilpriceAPI, Alpha Vantage, Socrata Open Data           │
│  • GasBuddy, AAA Web Scrapers, NOAA Weather, Finlight Energy News           │
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
   * Scans 5 primary energy RSS streams, runs fast-path keyword/regex anomaly detection, deduplicates dispatched items against Cloudflare Cache API (`caches.default`), and fires GitHub Repository Dispatch events (`event_type: "intraday_anomaly"`).

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

