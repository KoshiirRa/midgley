# Release Notes - v0.5.2

**Release Date:** September 11, 2026  
**Build Target:** `dev-vm` (`10.42.42.54`)  
**Git Branch:** `dev`  

---

## 🚀 Key Features, Architectural Enhancements & Algorithmic Upgrades

### 1. CoSPOT Compositional Spectral & Wavelet Feature Prompting Engine (Issue #215, arXiv:2609.02093)
- **Mathematical Frequency & Wavelet Decomposition ([`src/cospot_spectral_engine.py`](file:///src/cospot_spectral_engine.py)):**
  - Integrated theoretical concepts from *CoSPOT: Compositional Spectral Prompts for LLM-based Online Time Series Forecasting* ([arXiv:2609.02093v1](https://arxiv.org/abs/2609.02093v1), KAIST).
  - **Discrete Fourier Transform (DFT) Basis Decomposition:** Decomposes lookback sequences into orthogonal frequency bases:
    ```math
    F_k = \sum_{t=0}^{L-1} X_t e^{-i 2\pi k t / L}, \quad k = 0, \dots, \lfloor L/2 \rfloor
    ```
    Extracts dominant cycle periods ($T_{\text{dom}} = L / k^*$), normalized spectral power distributions ($P_k$), low-frequency trend energy ratios ($E_{\text{low}}$), and Shannon Spectral Entropy:
    ```math
    H_{\text{spectral}} = -\frac{\sum P_k \ln(P_k + 10^{-12})}{\ln(K)}
    ```
  - **Discrete Wavelet Transform (DWT) Multi-Resolution Filtering:** Uses 2-level Haar wavelet filtering to isolate high-frequency intraday noise ($D_1$), localized 3-5 day shock fluctuations ($D_2$), and macro trend baselines ($A_2$), computing detail-to-approximation energy ratios ($R_{\text{wavelet}}$) and localized shock magnitudes ($|D_1[-1]| + |D_2[-1]|$).
- **Gemini 2.5 Flash Prompt Context Enrichment ([`src/event_analyzer.py`](file:///src/event_analyzer.py)):**
  - Injects structured `[MARKET FREQUENCY & SPECTRAL REGIME (CoSPOT arXiv:2609.02093)]` natural language context directly into Gemini 2.5 Flash single and batch prompt contracts (`LLM_SINGLE_PROMPT` & `LLM_BATCH_PROMPT`).
  - Addresses LLM "numerical blindness" by providing explicit frequency regime descriptors (e.g. *Coherent structural trend* vs *Turbulent non-stationary dispersion*) and localized wavelet noise states.
- **Ultra-Low Compute Online Projection Head Adaptation:**
  - Implemented `CoSPOTOnlineAdapter` with geometric loss decay ($\delta = 0.90$) and L2 regularization to rapidly adapt linear projection weights to non-stationary concept drift without full model retraining:
    ```math
    \mathcal{L}_{\text{online}} = \sum_{\tau=1}^T \delta^{T-\tau} \ell(f_\theta(X_\tau), \tilde{y}_\tau)
    ```
- **Quantitative Feature Engineering & Chronological Splits ([`src/feature_engineering.py`](file:///src/feature_engineering.py)):**
  - Added 6 rolling spectral features to `create_feature_matrix()`:
    - `cospot_dft_dominant_period`
    - `cospot_dft_low_freq_energy_ratio`
    - `cospot_dft_spectral_entropy`
    - `cospot_dwt_detail_energy_ratio`
    - `cospot_dwt_detail_shock_mag`
    - `cospot_dwt_approx_momentum`
  - Fully integrated into `quant_features` and `hybrid_features` in `prepare_chronological_splits()`.
- **Intraday Anomaly Event Monitor Ingestion ([`src/intraday_event_monitor.py`](file:///src/intraday_event_monitor.py)):**
  - Updated `evaluate_headline_anomaly()` to generate and pass real-time spectral prompt context to `extract_event_features_llm()`, ensuring breaking news impact scoring is conditioned on current frequency-domain market dynamics.
- **Spectral Benchmark Evaluator ([`src/models.py`](file:///src/models.py)):**
  - Added `evaluate_cospot_spectral_benchmarks()` comparing baseline Ridge estimators against spectral-augmented, hybrid-spectral, and online-adapted models on out-of-time test sets.

---

### 2. Vectorize Hindsight Episodic Agent Memory & Qualitative Anomaly Post-Mortems (Issue #230)
- **Biomimetic Retain-Recall-Reflect Triad ([`src/agent_memory.py`](file:///src/agent_memory.py)):**
  - Integrated episodic qualitative memory to transform Saturday weekly model reviews from pure numeric error calculation into automated root-cause post-mortems and historical analogy retrieval.
  - **`Retain` (Experiential Memory Storage):** Automatically captures resolved prediction outcomes, qualitative event shock context, and anomaly classifications (`LARGE_OVERESTIMATE`, `LARGE_UNDERESTIMATE`, `DIRECTIONAL_FLIP`, `CI_BREACH`) when 5-day market prices are backfilled in [`src/prediction_logger.py`](file:///src/prediction_logger.py).
  - **`Recall` (Dense & Semantic Analogy Search):** Enables zero-LLM search over historical forecast shocks using hybrid dense vector cosine similarity and Porter-stemmed BM25 keyword matching (e.g. querying past refinery flaring or hurricane detours in specific PADD regions).
  - **`Reflect` (Agentic Synthesis & Mental Models):** Synthesizes structured qualitative post-mortems for top forecast outliers, attributing discrepancies to event shock decay rates, localized crack margin expansions, or unmodeled physical bottlenecks, and outputs actionable parameter tuning recommendations (news decay $t_{1/2}$, Ridge $\alpha$, crack spread weights).
- **Google Cloud Run (Scale-to-Zero) & Supabase PostgreSQL pgvector Integration ([`src/hindsight_client.py`](file:///src/hindsight_client.py), [`scripts/deploy_hindsight_cloudrun.sh`](file:///scripts/deploy_hindsight_cloudrun.sh), [`scripts/init_supabase_hindsight.sql`](file:///scripts/init_supabase_hindsight.sql)):**
  - Connects to an external Vectorize Hindsight container service hosted on **Google Cloud Run** with `--min-instances 0` ($0 idle cost), backed by **Supabase PostgreSQL** with native `pgvector` and HNSW index support.
  - Features 15-second cold-boot timeout safeguards and seamless automatic failover.
- **Zero-Cost Deterministic Local SQLite FTS5 Fallback:**
  - Built-in `SQLiteMemoryStore` (`data/agent_memory.sqlite`) providing 100% offline reliability, $0 infrastructure cost, and 0 token overhead for basic keys and offline dev-vm evaluation.
- **Weekly Review 2.0 Integration ([`src/weekly_issue_reporter.py`](file:///src/weekly_issue_reporter.py)):**
  - Injects the `## 🧠 Qualitative Anomaly Post-Mortems & Episodic Memory (Issue #230)` section into Saturday automated GitHub review issues, showcasing root-cause diagnoses and historical analogies alongside quantitative MAE metrics.
- **Prometheus Observability & Grafana Exporters ([`src/telemetry.py`](file:///src/telemetry.py), [`docs/TELEMETRY_HANDOFF.md`](file:///docs/TELEMETRY_HANDOFF.md), [`grafana/dashboard_observability.json`](file:///grafana/dashboard_observability.json)):**
  - Emits `agent_memory_operations_total`, `agent_memory_backend_calls_total`, `agent_memory_stored_experiences_total`, and `agent_memory_stored_reflections_total` metrics with dedicated Grafana panels and Axiom/Sentry telemetry monitors.

### 3. Real-Time Discord Webhook Notification Gateway for Intraday Revisions (Issue #234)
- **Multi-Environment Anomaly Notification Engine ([`src/discord_notifier.py`](file:///src/discord_notifier.py)):**
  - Integrated real-time Discord webhook notifications triggered whenever breaking news headlines, refinery outages, or geopolitical supply shocks trip intraday anomaly thresholds.
  - **Environment Distinction (`[PRODUCTION]` vs `[DEVELOPMENT]`):** Dynamically inspects `MIDGLEY_ENV` and `GITHUB_ACTIONS` runtime state via `src/telemetry.py` to label alerts with clear badges (`Production (GitHub Actions / Cloud)` vs `Development (Local / dev-vm)`), preventing staging/dev testing confusion.
  - **Comprehensive Catalyst Telemetry:** Discord Embed payloads deliver rich real-time context:
    - Triggering news headline prose
    - Ingestion source (`Cloudflare_Worker`, `RSS_Feed`, `Webhook_Push`, `Manual_Dispatch`, `SEC_EDGAR_8K`)
    - Affected target regional metro hubs (e.g. `Tulsa`, `Newark`, `Cincinnati`, `Greenville`, `Charlotte`, `Oakland`, `National`)
    - Quantitative impact score vectors (Price Pressure $\Delta P$, Supply Disruption $S$, Geopolitical Risk $G$, OPEC Action)
    - Clickable markdown links to original breaking news articles and Internet Archive Wayback Machine permanent snapshots
  - **Dynamic Severity Color Coding:**
    - 🔴 **Red (`#E74C3C`):** High supply disruption ($S \ge 0.50$) or severe upward price pressure ($\Delta P \ge +0.40$).
    - 🟢 **Green (`#2ECC71`):** Substantial downward price relief ($\Delta P \le -0.20$).
    - 🟠 **Orange (`#E67E22`):** General geopolitical volatility and moderate shocks.
- **Intraday Pipeline Hook ([`src/intraday_event_monitor.py`](file:///src/intraday_event_monitor.py)):**
  - Integrated `send_intraday_discord_notification()` into `IntradayEventMonitor.process_incoming_headline()`, recording `discord_notified` status in `data/intraday_events.json`.
- **Workflow & Environment Variables ([`.github/workflows/intraday_event_monitor.yml`](file:///c:/Users/concentus/Documents/Random%20Ideas%20-%20LLM%20Unleaded%20Gas%20Price%20Prediction%20Modelling/.github/workflows/intraday_event_monitor.yml)):**
  - Injected `DISCORD_WEBHOOK_URL` secret and `MIDGLEY_ENV: "prod"` into the GitHub Actions intraday event dispatch workflow.
### 4. Mathematical Specification & Multi-Agent Pipeline Alignment (Issues #224, #225, #226, #227, #229)
- **Chronological 15-Section Execution Order ([`src/dashboard_generator.py`](file:///src/dashboard_generator.py), [`docs/math.html`](file:///docs/math.html)) (Issue #229):**
  - Restructured the mathematical documentation to mirror the exact sequence of data flow through the multi-agent system:
    1. `01`: Quantitative Commodity Futures & 3-2-1 Crack Spread Modeling
    2. `02`: Alternative Physical Feeds, Macroeconomics & Market Positioning
    3. `03`: Live News Streams, Web Scraping & Multi-Tiered LLM Extraction
    4. `04`: Executive Social Media Stream & Weekday vs. Weekend Gap Dynamics
    5. `05`: Multi-Tiered NOAA Weather Risk & Atmospheric Convective Dynamics
    6. `06`: Global & Regional Maritime Chokepoints, Inland River Barging & Waterborne Terminals
    7. `07`: USGS 3D Hypocentral Seismic Attenuation, Hydrological Telemetry & Industrial AQI Outage Risk
    8. `08`: Microsoft Qlib Symbolic Alpha Factor Mining, Spectral CoSPOT & Dynamic Domain Adaptation
    9. `09`: Econometric Exponential Memory Decay & Category-Specific Shock Fusion
    10. `10`: Standardized Ridge Estimator & Purged Combinatorial Cross-Validation (CPCV)
    11. `11`: CARB Regulatory Burden & PADD 5 Refining Island Isolation
    12. `12`: Ultra-Low Sulfur Diesel (ULSD) & Distillate Crack Spread Modeling
    13. `13`: Dynamic Volatility-Gated Persistence Blending (DV-GPB) & Empirical Residual CI
    14. `14`: Local Metro Basis Differentials, Spatial Freight & Retail Rack Margins
    15. `15`: End-to-End Master Prediction Synthesis & Mathematical Factor Composition
- **Executive Social Media Volatility & Weekend Gap Multiplier (Issue #224):**
  - Documented empirical regression coefficients ($\beta_{\text{OPEC}} = -1.85\%$, $\beta_{\text{tariff}} = +2.10\%$) and the $1.42\times$ weekend market gap multiplier applied during Friday 17:00 to Sunday 18:00 EST market closes:
    ```math
    \mathbf{V}_{\text{social}, t} = \gamma_{\text{weekend}} \cdot \left(\beta_{\text{OPEC}} \cdot \text{Score}_{\text{OPEC}, t} + \beta_{\text{tariff}} \cdot \text{Score}_{\text{tariff}, t}\right), \quad \gamma_{\text{weekend}} = 1.42 \text{ if weekend else } 1.0
    ```
- **Alternative Physical Feeds & Positioning Formulations (Issue #225):**
  - Defined explicit mathematical mappings and economic interpretations for all 7 alternative feeds: Cboe OVX, Baker Hughes Rig Counts, 10Y Treasury Yields, 10Y TIPS Breakeven Inflation, CFTC COT Managed Money Net Longs, FERC Natural Gas / LNG Spark Spreads, and USDA/EIA Ethanol/RIN blendstock costs.
- **Live News Streams, Web Scraping & Tiered LLM Failover Pipeline (Issue #226):**
  - Detailed the multi-channel news ingestion engine: Finlight live financial feeds (150/mo quota valve), Firecrawl web-to-markdown scraper (800/mo safety cap & 24h caching), zero-cost RSS 15-min polling with `max_age_hours=24.0`, incoming webhooks with IPASIS security verification, and the 3-tier LLM failover architecture (Gemini 2.5 Flash $\rightarrow$ GPT-4o-mini $\rightarrow$ Offline Lexicon).
- **Exponential Memory Decay with Category Half-Lives & Diagnostic Fusion (Issue #227):**
  - Updated discrete recursive memory decay accumulator:
    ```math
    \mathbf{M}_t = \mathbf{M}_{t-1} \cdot e^{-\frac{\ln 2}{t_{1/2}}} + \mathbf{V}_t
    ```
    with category half-lives $t_{1/2} \in [2.5, 14.0]\text{ days}$ ($14.0\text{d}$ physical supply disruptions, $7.0\text{d}$ geopolitical risk, $5.0\text{d}$ OPEC action, $4.0\text{d}$ demand sentiment, $2.5\text{d}$ executive social posts) and Context Routing Diagnostic Fusion weighting $\omega_{\text{fusion}} \in [0.85, 1.25]$.

### 5. Interactive Model Data Sources & Ingestion Governance Matrix ([`src/sources_generator.py`](file:///src/sources_generator.py), [`docs/sources.html`](file:///docs/sources.html), [`docs/sources/index.html`](file:///docs/sources/index.html))
- **Dedicated Public Data Sources Catalog:**
  - Implemented modular `src/sources_generator.py` generating comprehensive standalone documentation pages (`docs/sources.html` and `docs/sources/index.html`) cataloging all 26 quantitative commodity futures, NOAA weather feeds, USGS hydrology gages, physical telemetry, state open data portals, and financial media streams feeding the Midgley forecasting engine.
- **6 Comprehensive Domain Category Partitions:**
  - `01`: **Quantitative Commodity Futures & Energy Benchmarks** (7 feeds: RBOB Futures `RB=F`, WTI Crude `CL=F`, Brent Crude `BZ=F`, ULSD Heating Oil `HO=F`, EIA v2 API, FRED St. Louis Fed, USDA Ethanol & RIN Credits).
  - `02`: **Alternative Physical, Upstream & Macroeconomic Telemetry** (6 feeds: Cboe OVX `^OVX`, Baker Hughes Rig Counts, US Treasury & TIPS Yields `^TNX`/`DGS10`/`DFII10`, CFTC COT Energy Positioning, FERC Form 6 Tariffs, Energy Equities `XLE`/`VLO`/`MPC`/`PSX`).
  - `03`: **Real-Time Financial Media, Web Scraping & Event Intelligence** (6 feeds: Finlight.me REST API, Firecrawl Scraper, Free Energy RSS Feeds, Push Webhook Gateway, Executive Social Feed, SEC EDGAR 8-K Outages).
  - `04`: **Atmospheric, Hydrological & Seismic Hazard Telemetry** (8 feeds: NOAA NWS Alerts, NOAA SPC Convective Risk, NOAA NHC Tropical Cones, BSEE Gulf Shut-ins, USGS Water Data Telemetry, USACE Lock Performance, USGS Seismic Hazards, Air Quality & Flaring Index).
  - `05`: **State Open Data, Tax Portals & Crowdsourced Retail Pump Feeds** (3 feeds: Universal 50-State Open Data Portals, U.S. Census Demographics, Live Retail Fuel Feeds).
  - `06`: **Continuous Academic Literature & Developer Catalog Feeds** (3 feeds: arXiv Research Preprints, CORE Open-Access Literature, Tracked Developer Catalog Indexes).
- **Interactive Search & Category Filter Controls:**
  - Real-time client-side search box filtering across feed titles, tickers, consumer module paths, and operational tags.
  - Sticky category filter bar with active feed counters and instant DOM toggling.
- **Master Ingestion & Governance Ledger Matrix:**
  - Searchable tabular ledger summarizing endpoint protocols, authentication profiles ($0 Open Access / Free Keys), caching TTLs, update cadences, and consumer modules for automated API governance.
- **Typography & KaTeX Script Fixes:**
  - Cleaned all catalog cards to use native HTML entities and typography (e.g., `Crack321`, `ΔP`, `PM2.5`, `SO2`, `≥ M3.0`) eliminating unneeded raw LaTeX escaping in card descriptions.
  - Corrected `KATEX_ONLOAD_SCRIPT` JavaScript escaping in `src/dashboard_generator.py` to prevent browser syntax errors on auto-rendered math equations.

### 6. Public Telemetry Page Expansion & Missing Observability Streams (Issue #237)
- **Vectorize Hindsight Episodic Agent Memory Observability ([`src/dashboard_generator.py`](file:///src/dashboard_generator.py), [`docs/telemetry.html`](file:///docs/telemetry.html)):**
  - Surfaced real-time episodic memory statistics directly from `data/telemetry_ledger.json` and `data/agent_memory.sqlite`.
  - **Memory Triad Counters:** Explicitly displays lifetime counts for `Retain` operations (experience storage), `Recall` queries (analogy matching), and `Reflect` syntheses (qualitative post-mortems).
  - **Hybrid Routing Telemetry:** Displays request distribution between Google Cloud Run Vector DB (`midgley-hindsight` + Supabase `pgvector`) vs zero-cost local SQLite FTS5 fallbacks.
  - **Persistent Storage Metrics:** Renders total stored episodic memory records and synthesized anomaly post-mortems.
- **Zero-Cost Data Connector Health & Freshness Audit:**
  - Integrated `src.connector_telemetry.get_telemetry_summary(days=7)` into a dedicated 7-day health audit matrix across all 7 core zero-cost open data providers (EIA API v2, FRED Energy Series, USDA Biofuel & RINs, NOAA Terminal Weather, AAA Regional Retail, Socrata 50-State Portals, USGS Streamflow & Seismic).
  - Tracks 7-day request volume, error counts, failure rate %, average response latency (ms), and data cache freshness.
- **Zero-Cost LLM Fallback & Dollar/Token Savings Accounting:**
  - Integrated `src.fallback_telemetry.fallback_logger.get_summary()` to surface Basic Tier routed calls, Kaggle/zero-cost provider hook executions, and Tier 3 offline lexicon fallbacks, quantifying estimated LLM tokens spared and cumulative dollar savings.
- **Comprehensive API Quota Safety Valves:**
  - Expanded the quota dashboard to provide real-time budget cards for Firecrawl Web-to-Markdown (800/mo cap & 30/day burst limit), Finlight Financial News (150/mo cap & 10/day burst limit), IPASIS Security Verifier (100 req/day cap with 1-hr caching), GasBuddy GraphQL, and NOAA Weather terminal limits.
- **Dynamic Out-of-Metro Demand Map Visualization:**
  - Replaced static mock Leaflet map coordinates with live dynamic serialization of `src.telemetry.get_unmapped_zip_telemetry()`, visualizing unmapped ZIP code query clusters across the United States for target metro expansion planning.

---

## 🧪 Benchmark & Verification Results

- **Simulated 4-Week Reflection Cycle Benchmark ([`tests/test_hindsight_benchmark.py`](file:///tests/test_hindsight_benchmark.py)):**
  - Evaluated 28-day / 224-prediction lifecycle across 8 metro hubs with 6 injected shock anomalies:
    - **Average Retain Latency:** `15.65 ms / write`
    - **Analogy Recall Latency:** `2.02 ms / query`
    - **Reflection Synthesis Latency:** `29.98 ms`
    - **SQLite DB Storage Footprint:** `172.00 KB` (for 224 experiences)
- **Mathematical Specification & Dashboard Generator Test Suite (`tests/test_dashboard_generator.py`):**
  - `18 passed in 341.71s` (100% pass rate) on `dev-vm` (`10.42.42.54`), covering all 18 test cases including `test_data_sources_page_generation` and dynamic telemetry assertions.
- **System Telemetry & Unmapped Zip Geocoding Test Suite (`tests/test_system_telemetry.py`):**
  - `10 passed in 1.94s` (100% pass rate) on `dev-vm` (`10.42.42.54`), validating telemetry page rendering, HTML validity, API server telemetry endpoints, and corruption resilience.
- **Discord Notification & Intraday Anomaly Test Suite (`tests/test_discord_notifier.py`, `tests/test_intraday_event_monitor.py`):**
  - `23 passed in 0.55s` (100% pass rate).
- **CoSPOT Unit & Integration Test Suite (`tests/test_cospot_spectral.py`):**
  - `10 passed in 6.61s` (100% pass rate).
- **Hindsight Memory & Telemetry Test Suite (`tests/test_agent_memory.py`, `tests/test_system_telemetry.py`):**
  - `18 passed in 2.26s` (100% pass rate).

---

## 📋 Closed & Superseded GitHub Issues
- **Issue #215**: `[Feature Request] Evaluate CoSPOT Compositional Spectral Prompting & Wavelet Context for LLM Forecasting (arXiv:2609.02093)` (Completed)
- **Issue #224**: `docs(math): Clarify Step 5 Executive Social Media Volatility with Weekday vs Weekend Gap Dynamics` (Completed)
- **Issue #225**: `docs(math): Update Step 6 Alternative Physical Feeds Formula & Feature Definitions` (Completed)
- **Issue #226**: `docs(math): Comprehensive Update to Step 7 Live News Feed & Scraper Ingestion Pipeline` (Completed)
- **Issue #227**: `docs(math): Update Step 8 Exponential Shock Memory Decay Formulation & Component Descriptions` (Completed)
- **Issue #229**: `docs(math): Reorder and Structure Math Guide Sections into Chronological Pipeline Order` (Completed)
- **Issue #230**: `[Weekly Review 2.0] Evaluate Hindsight Agent Memory (Retain-Recall-Reflect) for Qualitative Anomaly Post-Mortems` (Completed)
- **Issue #234**: `feat(notifications): Discord webhook notification for intraday forecast revisions` (Completed)
- **Issue #237**: `[Telemetry] Surface Missing Backend Telemetry Streams (Hindsight Memory, Connector Health Audit, Fallback Accounting & Quota Valves) on Public Dashboard` (Completed)




