# 🔬 Monitored Research Sources & Developer Catalogs

This document provides a comprehensive specification of all external intelligence feeds, developer catalog indexes, academic preprint streams, and open data portals monitored by the **Midgley Multi-Agent Forecasting System** during continuous daily execution and weekly model performance review cycles.

---

## 1. Overview & Monitored Data Architecture

The forecasting engine continuously ingests both quantitative time-series data and qualitative event intelligence. During the automated Saturday morning review runner ([`.github/workflows/weekly_model_review.yml`](file:///.github/workflows/weekly_model_review.yml)), the system scans academic research feeds, monitors public developer catalogs for newly released tools or APIs, and updates persistent tracking ledgers.

```
                                  ┌─────────────────────────────────────────────────────────────┐
                                  │            SATURDAY WEEKLY REVIEW PIPELINE                  │
                                  │     (.github/workflows/weekly_model_review.yml @ 08:00 CT) │
                                  └──────────────┬──────────────────────────────┬───────────────┘
                                                 │                              │
                        ┌────────────────────────┼──────────────────────────────┐
                        ▼                        ▼                              ▼
         ┌──────────────────────────────┐┌──────────────────────────────┐┌──────────────────────────────┐
         │   DEVELOPER CATALOG MONITOR  ││    arXiv RESEARCH MONITOR    ││     CORE RESEARCH MONITOR    │
         │    (src/catalog_monitor.py)  ││    (src/arxiv_monitor.py)    ││    (src/core_monitor.py)     │
         └──────────────┬───────────────┘└──────────────┬───────────────┘└──────────────┬───────────────┘
                        │                               │                               │
                        ▼                               ▼                               ▼
         ┌──────────────────────────────┐┌──────────────────────────────┐┌──────────────────────────────┐
         │ 10 Curated Developer Indexes ││  arXiv API (q-fin, econ, cs) ││  CORE API v3 Open-Access     │
         │ Gemini 2.5 Flash Score ≥ 7.0 ││ 7-Day Rolling Paper Filter   ││ 7-Day Energy Search & Filter │
         └──────────────┬───────────────┘└──────────────┬───────────────┘└──────────────┬───────────────┘
                        │                               │                               │
                        └───────────────────────────────┴───────────────────────────────┘
                                                        │
                                                        ▼
                                  ┌─────────────────────────────────────────────────────────────┐
                                  │              GITHUB ISSUE REVIEW & REPO REPORT              │
                                  │           (src/weekly_issue_reporter.py -> Issues)          │
                                  └─────────────────────────────────────────────────────────────┘
```

---

## 2. Monitored Developer Catalogs (`src/catalog_monitor.py`)

The Developer Catalog Monitor ([`src/catalog_monitor.py`](file:///src/catalog_monitor.py)) continuously tracks **10 major developer catalog indexes** to discover new open-source libraries, REST APIs, dataset portals, and quantitative tools.

### Monitored Catalog Indexes

| Catalog Key | Catalog Name | Source Repository / URL | Purpose & Focus Area |
| :--- | :--- | :--- | :--- |
| `public-apis` | **Public APIs Index** | [`public-apis/public-apis`](https://raw.githubusercontent.com/public-apis/public-apis/master/README.md) | Public REST APIs for energy, weather, transportation, and finance. |
| `free-for-dev` | **Free for Developers** | [`ripienaar/free-for-dev`](https://raw.githubusercontent.com/ripienaar/free-for-dev/master/README.md) | SaaS, PaaS, and IaaS offerings with free developer tiers. |
| `freestuff.dev` | **FreeStuff Dev Directory** | [`freestuff.dev`](https://freestuff.dev/) | Curated developer tools, APIs, and zero-cost cloud services. |
| `free-for-life` | **Free For Life Directory** | [`wdhdev/free-for-life`](https://raw.githubusercontent.com/wdhdev/free-for-life/main/README.md) | Always-free software tiers, APIs, and cloud resources. |
| `awesome` | **Awesome Meta-List** | [`sindresorhus/awesome`](https://raw.githubusercontent.com/sindresorhus/awesome/main/readme.md) | Meta-directory of topic-specific curated awesome lists. |
| `awesome-selfhosted` | **Awesome Selfhosted** | [`awesome-selfhosted/awesome-selfhosted`](https://raw.githubusercontent.com/awesome-selfhosted/awesome-selfhosted/master/README.md) | Self-hostable network services, telemetry, and analytics suites. |
| `awesome-quant` | **Awesome Quant** | [`wilsonfreitas/awesome-quant`](https://raw.githubusercontent.com/wilsonfreitas/awesome-quant/master/README.md) | Quantitative finance, econometric modeling, and time-series libraries. |
| `awesome-python` | **Awesome Python** | [`vinta/awesome-python`](https://raw.githubusercontent.com/vinta/awesome-python/master/README.md) | Python data science, machine learning, and pipeline frameworks. |
| `awesome-nodejs` | **Awesome Node.js** | [`sindresorhus/awesome-nodejs`](https://raw.githubusercontent.com/sindresorhus/awesome-nodejs/main/readme.md) | Node.js ecosystem packages and API clients. |
| `api-mega-list` | **API Mega List** | [`cporter202/API-mega-list`](https://raw.githubusercontent.com/cporter202/API-mega-list/master/README.md) | Broad directory of public data APIs and financial connectors. |

### Evaluation & Operational Policies
* **State File Tracking:** Scanned link history is stored in [`data/catalog_monitors_state.json`](file:///data/catalog_monitors_state.json) to diff newly added links between runs.
* **LLM Evaluation Threshold:** New items are scored by Gemini 2.5 Flash for modeling relevance. Items scoring $\ge 7.0/10.0$ trigger automated creation of a GitHub Feature Request issue on `KoshiirRa/midgley`.
* **Domain Taxonomy Labeling:** All auto-generated issues receive appropriate domain taxonomy labels (`data-ingestion`, `infrastructure`, `modeling`, `dashboard`, `integration`, `api`, `security`, `token-efficiency`).
* **Apify Tools Barred Policy:** All catalog monitors and LLM prompts explicitly ignore and discard tools hosted on or referencing Apify (`apify.com`) due to paid subscription and compute unit cost constraints. All ingested resources must be 100% zero-cost.

---

## 3. Academic & Research Paper Feeds (`src/arxiv_monitor.py` & `src/core_monitor.py`)

During weekly Saturday review runs, the forecasting system scans both preprint servers and peer-reviewed open-access literature repositories to discover new modeling methodologies, crack margin theories, and volatility forecasting architectures.

### 3.1 arXiv Research Paper Monitor (`src/arxiv_monitor.py`)

The arXiv Research Paper Monitor queries the official arXiv REST API (`export.arxiv.org/api/query`) to extract newly published or updated preprints in quantitative finance, econometrics, and machine learning.

* **Target Subject Categories:**
  - `q-fin.PR`: Quantitative Finance — Pricing & Risk
  - `econ.EM`: Economics — Econometrics
  - `cs.LG`: Computer Science — Machine Learning
  - `cs.AI`: Computer Science — Artificial Intelligence
* **Keyword Constraints:**
  - Titles containing: `gasoline`, `commodity`, `"crude oil"`, `"futures"`
  - Abstracts containing: `"energy forecasting"`, `"price prediction"`, `"time series"`
* **API Query String:**
  ```text
  (cat:q-fin.PR OR cat:econ.EM OR cat:cs.LG OR cat:cs.AI) AND (ti:gasoline OR ti:commodity OR ti:"crude oil" OR ti:"futures" OR abs:"energy forecasting" OR abs:"price prediction" OR abs:"time series")
  ```
* **Evaluation Window:** Filters papers published within a rolling 7-day window prior to the Saturday review run.
* **Reporting:** Formatted paper abstracts, author lists, and PDF links are injected directly into the weekly model performance review issue report. See [`docs/arxiv_monitoring_spec.md`](file:///docs/arxiv_monitoring_spec.md) for detailed technical specifications.

### 3.2 CORE Open-Access Research Paper Monitor (`src/core_monitor.py`) (Issue #53)

The CORE Open-Access Paper Monitor integrates the [CORE API v3](https://core.ac.uk/services/api) (`https://api.core.ac.uk/v3/search/works`) to discover open-access research papers from global university repositories, academic journals, and conference proceedings.

* **Search Topics & Focus Areas:**
  - `fuel price forecasting`, `gasoline crack margin`, `refinery economics`, `crude oil volatility`, `asymmetric price transmission`, `rockets and feathers econometrics`.
* **API Query String:**
  ```text
  ("gasoline price" OR "fuel price" OR "crack spread" OR "refinery margin" OR "oil price shock") AND (forecasting OR prediction OR econometrics)
  ```
* **Cutoff & Deduplication Filtering:**
  - Enforces a rolling 7-day publication window filter (`max_age_days=7.0`).
  - Deduplicates against previously reviewed DOIs and paper identifiers in `data/catalog_monitors_state.json`.
* **GitHub Actions Integration:** Authenticates via `CORE_API_KEY` secret during Saturday review runs and formats paper titles, authors, journals, and open-access download URLs directly into the weekly model review report.

---

## 4. Open Data & Market Intelligence Feeds

In addition to developer catalogs and academic preprint servers, the system ingests data from several open data portals and market intelligence providers:

### Financial & Macroeconomic Feeds
* **U.S. EIA Open Data API v2 ([`src/data_ingestion.py`](file:///src/data_ingestion.py)):** Weekly retail price series, PADD refinery percent utilization, regional motor gasoline/crude stock inventories, product supplied (implied demand), and bitemporal vintage tracking snapshots (`/petroleum/pri/gnd/data/`, `/petroleum/pnp/pct/data/`, `/petroleum/stoc/wstk/data/`).
* **St. Louis Fed FRED ([`src/data_ingestion.py`](file:///src/data_ingestion.py)):** Weekly national and PADD retail gasoline/diesel series (`GASREGW`, `GASDESW`, `GASREGWCW`, `GASREGWGULF`) and CPI gasoline index (`CUUR0000SETB01`).
* **U.S. Treasury Fiscal Data API ([`src/treasury_yield_feed.py`](file:///src/treasury_yield_feed.py)):** Daily nominal Treasury yields (10Y, 2Y) and 10-Year TIPS real interest rates (`fiscaldata.treasury.gov`), deriving the benchmark 10Y-2Y yield curve spread $\text{Spread}_{10\text{Y}-2\text{Y}}$ and 5-day spread momentum delta (Issue #66).
* **USDA Biofuel & Ethanol Reports ([`src/data_ingestion.py`](file:///src/data_ingestion.py)):** Spot Midwest ethanol (E100) rack prices ($/gal) and RIN D6 Ethanol Credit spot values (`marsapi.ams.usda.gov`).
* **Finlight Financial News Stream ([`src/finlight_feed.py`](file:///src/finlight_feed.py)):** Real-time tier-1 energy news headlines with persistent quota ledger enforcing a 150 call/month safety cap (`data/finlight_quota.json`).

### Weather, Hydrological & Physical Hazards Feeds
* **NOAA NWS & SPC Weather Models ([`src/noaa_weather.py`](file:///src/noaa_weather.py)):** Terminal REST endpoints (`t.wxs.us`) for NWS severe weather alerts and SPC Convective Outlook risk mapping across key refining hubs (Tulsa `74101`, Newark `19711`, Cincinnati `45202`, Greenville `27834`, Charlotte `28202`, Oakland `94612`).
* **USGS Water Data API Telemetry ([`src/usgs_water_feed.py`](file:///src/usgs_water_feed.py)):** Instantaneous streamflow (`00060`), gage height (`00065`), water temperature (`00010`), and specific conductance (`00095`) telemetry across 13 key stations in 6 hydrological clusters (Inland Barge Corridor, Gulf Coast Refining Origin, Bay Area Carquinez Strait, Delaware River/Bay, Tulsa MKARNS, and South Florida Coastal Drainage) to model barge bottlenecks and cooling tower thermal limits (Issue #56).
* **USGS Earthquake Web Service Telemetry ([`src/usgs_seismic.py`](file:///src/usgs_seismic.py)):** Live earthquake GeoJSON feeds (`earthquake.usgs.gov`) across 5 critical refining and storage corridors (`bay_area`, `cushing_ok`, `socal`, `mid_atlantic`, `new_madrid`) with 3D hypocentral distance-decay ground shaking proxies and pipeline shutoff risk indices (Issue #55).
* **Multi-Feed Air Quality (AQI) & EPA AirNow Ozone Alerts ([`src/aqi_feed.py`](file:///src/aqi_feed.py)):** Fine particulate ($\text{PM}_{2.5}$) and chemical gas ($\text{SO}_2, \text{O}_3$) metrics from PurpleAir, OpenAQ, and EPA AirNow (`airnowapi.org`) across 15 km refining fence-line polygons to detect emergency catalytic cracker outages and model statutory seasonal Reid Vapor Pressure (RVP) summer-blend compliance (Issues #54 & #73).
* **Alternative Physical Feeds ([`src/alternative_data_feeds.py`](file:///src/alternative_data_feeds.py)):** Cboe OVX crude oil options volatility index and Baker Hughes North American drilling rig counts.

### Qualitative Intelligence, Web Scraping & Operator Disclosures
* **SEC EDGAR Official 8-K Outage Filings ([`src/edgar_8k_monitor.py`](file:///src/edgar_8k_monitor.py)):** Real-time SEC EDGAR ATOM RSS feeds for major refinery operators (PBF, HF Sinclair, Marathon, Valero, Phillips 66) with a 22-keyword operational relevance gate and Cloudflare Edge polling (Issues #69 & #129).
* **Firecrawl Web-to-Markdown Scraper API ([`src/firecrawl_scraper.py`](file:///src/firecrawl_scraper.py)):** Clean, LLM-ready markdown extraction from breaking energy news articles, refinery press releases, and state motor fuel tax portals with 800 call/month safety cap (Issue #83).
* **Self-Hosted ArchiveBox Preservation ([`src/archive_service.py`](file:///src/archive_service.py)):** Submits qualitative news and outage URLs asynchronously to self-hosted ArchiveBox instances with local markdown snapshot ledger fallback (Issue #97).

### State Demographics & Regional Open Data Portals
* **Universal 50-State Open Data Portals ([`src/state_open_data.py`](file:///src/state_open_data.py)):** Socrata open data portals (`data.<state>.gov` / `data.gov`), U.S. Census State Tax Collections API, and FTA motor fuel indices for official state motor fuel excise tax rates ($/gal) and UST fees across all 50 states + DC.
* **U.S. Census Bureau ACS Demographics & Commuter Metrics ([`src/census_demographics.py`](file:///src/census_demographics.py)):** Ingests MSA- and county-level American Community Survey (ACS-1 / ACS-5) commuter tables (`B08201`, `B08301`, `B08013`) to compute `vehicle_dependency_ratio`, `vehicles_per_household`, `mean_commute_minutes`, and `inelastic_demand_score` with an adaptive annual release-window lifecycle (Sept 1–30 verification, 335+ day locked annual cache) (Issue #75).

### Quantitative Modeling & Research Frameworks
* **Google TimesFM Foundation Model ([`src/timesfm_forecaster.py`](file:///src/timesfm_forecaster.py)):** Decoder-only time-series foundation model with scikit-learn API compatibility for zero-shot forecasting and $P_{10}, P_{50}, P_{90}$ quantile uncertainty bands (Issues #185 & #112).
* **Microsoft Qlib & RD-Agent Alpha Factor Mining ([`src/qlib_symbolic_engine.py`](file:///src/qlib_symbolic_engine.py), [`src/alpha_factor_miner.py`](file:///src/alpha_factor_miner.py), [`src/ddg_da_adapter.py`](file:///src/ddg_da_adapter.py)):** Safe AST-parsed symbolic factor evaluator, autonomous LLM alpha factor discovery loop, and GMM market regime clustering with Gaussian RBF kernel similarity weighting (Issue #127).
* **Dynamic Volatility-Gated Persistence Blending (DV-GPB) ([`src/models.py`](file:///src/models.py)):** Continuous sigmoid volatility gate ($\lambda_{vol} = \frac{1}{1 + e^{-200(\sigma_{14d} - 0.015)}}$) blending model forecasts with naive persistence during quiet markets while preserving 100% shock reactivity, paired with empirical 30-day residual 95% confidence intervals (Issue #214).
* **Qualitative Intelligence Knowledge Graph ([`src/knowledge_graph.py`](file:///src/knowledge_graph.py)):** Pure Python NetworkX graph engine with SQLite persistence, automated petroleum supply topology seeding, GraphRAG 2-hop neighborhood context injection, and episodic shock memory retrieval (Issue #116).
* **Sapient PRAXIST Research Engine ([`src/praxist_engine.py`](file:///src/praxist_engine.py)):** Programmatic research harness for LLM agents to formulate empirical feature hypotheses, run out-of-sample backtests, compute paired $t$-tests and $p$-values, and execute hyperparameter sweeps (Issue #188).
* **Open Source AI Radar ([`src/data_ingestion.py`](file:///src/data_ingestion.py)):** Ingests state-of-the-art open-weights LLMs/SLMs, parameter scales, quantization profiles, and benchmark scores via `GET /api/v1/system/radar` (Issue #187).
* **Healthchecks.io Pipeline Heartbeats ([`src/healthcheck_monitor.py`](file:///src/healthcheck_monitor.py)):** Dispatches start, success, duration, and failure pings across daily forecasting and Saturday review runs (Issue #98).
* **Weights & Biases (W&B) Telemetry ([`src/wandb_logger.py`](file:///src/wandb_logger.py)):** Tracks quantitative model training runs, hyperparameter sweeps, rolling validation loss curves, and backtest risk metrics (Issue #80).

---

## 5. Maintenance & Reference Files

* **Catalog Monitor Source Code:** [`src/catalog_monitor.py`](file:///src/catalog_monitor.py)
* **arXiv Monitor Source Code:** [`src/arxiv_monitor.py`](file:///src/arxiv_monitor.py)
* **CORE Monitor Source Code:** [`src/core_monitor.py`](file:///src/core_monitor.py)
* **Weekly Review Workflow:** [`.github/workflows/weekly_model_review.yml`](file:///.github/workflows/weekly_model_review.yml)
* **arXiv Monitoring Specification:** [`docs/arxiv_monitoring_spec.md`](file:///docs/arxiv_monitoring_spec.md)
* **Research Citations Ledger:** [`RESEARCH_CITATIONS.md`](file:///RESEARCH_CITATIONS.md)
* **System Architecture Document:** [`docs/ARCHITECTURE.md`](file:///docs/ARCHITECTURE.md)
* **Agent Architecture Specification:** [`AGENTS.md`](file:///AGENTS.md)

