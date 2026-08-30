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
                                                 ▼                              ▼
                                  ┌──────────────────────────────┐┌──────────────────────────────┐
                                  │   DEVELOPER CATALOG MONITOR  ││    arXiv RESEARCH MONITOR    │
                                  │    (src/catalog_monitor.py)  ││    (src/arxiv_monitor.py)    │
                                  └──────────────┬───────────────┘└──────────────┬───────────────┘
                                                 │                              │
                                                 ▼                              ▼
                                  ┌──────────────────────────────┐┌──────────────────────────────┐
                                  │ 10 Curated Developer Indexes ││  arXiv API (q-fin, econ, cs) │
                                  │ Gemini 2.5 Flash Score ≥ 7.0 ││ 7-Day Rolling Paper Filtering │
                                  └──────────────┬───────────────┘└──────────────┬───────────────┘
                                                 │                              │
                                                 └──────────────┬───────────────┘
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

## 3. Academic & Research Paper Feeds (`src/arxiv_monitor.py`)

The arXiv Research Paper Monitor ([`src/arxiv_monitor.py`](file:///src/arxiv_monitor.py)) queries the official arXiv REST API (`export.arxiv.org/api/query`) during weekly review runs to extract newly published or updated preprints in quantitative finance, econometrics, and machine learning.

### Monitored arXiv Categories & Query Filters

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

---

## 4. Open Data & Market Intelligence Feeds

In addition to developer catalogs and academic preprint servers, the system ingests data from several open data portals and market intelligence providers:

### Financial & Macroeconomic Feeds
* **U.S. EIA Open Data API v2 ([`src/data_ingestion.py`](file:///src/data_ingestion.py)):** Weekly retail price series, PADD refinery percent utilization, and regional motor gasoline/crude stock inventories (`/petroleum/pri/gnd/data/`, `/petroleum/pnp/pct/data/`, `/petroleum/stoc/wstk/data/`).
* **St. Louis Fed FRED ([`src/data_ingestion.py`](file:///src/data_ingestion.py)):** Weekly national and PADD retail gasoline/diesel series (`GASREGW`, `GASDESW`, `GASREGWCW`, `GASREGWGULF`) and CPI gasoline index (`CUUR0000SETB01`).
* **USDA Biofuel & Ethanol Reports ([`src/data_ingestion.py`](file:///src/data_ingestion.py)):** Spot Midwest ethanol (E100) rack prices ($/gal) and RIN D6 Ethanol Credit spot values (`marsapi.ams.usda.gov`).
* **Finlight Financial News Stream ([`src/finlight_feed.py`](file:///src/finlight_feed.py)):** Real-time tier-1 energy news headlines with persistent quota ledger enforcing a 150 call/month safety cap (`data/finlight_quota.json`).

### Weather & Physical Feeds
* **NOAA NWS & SPC Weather Models ([`src/noaa_weather.py`](file:///src/noaa_weather.py)):** Terminal REST endpoints (`t.wxs.us`) for NWS severe weather alerts and SPC Convective Outlook risk mapping across key refining hubs (Tulsa `74101`, Newark `19711`, Cincinnati `45202`, Greenville `27834`, Charlotte `28202`, Oakland `94612`).
* **Alternative Physical Feeds ([`src/alternative_data_feeds.py`](file:///src/alternative_data_feeds.py)):** Cboe OVX crude oil options volatility index and Baker Hughes North American drilling rig counts.

### State & Regional Open Data Portals
* **Universal 50-State Open Data Portals ([`src/state_open_data.py`](file:///src/state_open_data.py)):** Socrata open data portals (`data.<state>.gov` / `data.gov`), U.S. Census State Tax Collections API, and FTA motor fuel indices for official state motor fuel excise tax rates ($/gal) and UST fees across all 50 states + DC.

---

## 5. Maintenance & Reference Files

* **Catalog Monitor Source Code:** [`src/catalog_monitor.py`](file:///src/catalog_monitor.py)
* **arXiv Monitor Source Code:** [`src/arxiv_monitor.py`](file:///src/arxiv_monitor.py)
* **Weekly Review Workflow:** [`.github/workflows/weekly_model_review.yml`](file:///.github/workflows/weekly_model_review.yml)
* **arXiv Monitoring Specification:** [`docs/arxiv_monitoring_spec.md`](file:///docs/arxiv_monitoring_spec.md)
* **System Architecture Document:** [`docs/ARCHITECTURE.md`](file:///docs/ARCHITECTURE.md)
* **Agent Architecture Specification:** [`AGENTS.md`](file:///AGENTS.md)
