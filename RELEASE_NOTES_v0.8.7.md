# Release Notes - v0.8.7 (Draft)

Midgley **v0.8.7** is an edge-resilience, zero-cost data ingestion, and out-of-metro geographic routing release. It establishes [`lykmapipo/US-Gas-Prices`](https://github.com/lykmapipo/US-Gas-Prices) daily metro and state CSV archives as the primary source for AAA fuel prices, re-engineers the secondary scraping fallback to execute headless Chromium on **Cloudflare Browser Run / Browser Rendering** (Issue #640), establishes a hyper-local **GasBuddy GraphQL-first fallback cascade** for rural and out-of-metro ZIP code queries, enforces California state physical feasibility bounds, and documents architectural governance decisions including the closure of Issue #531 (*FuelRipple*).

---

## 🎯 Highlights & Improvements

### 1. Primary AAA Fuel Price Ingestion via `lykmapipo/US-Gas-Prices` Daily CSVs
- **Zero-Cost Daily Open Data Ingestion**: Implemented [`fetch_aaa_csv_prices()`](src/live_fuel_feed.py) in [`src/live_fuel_feed.py`](src/live_fuel_feed.py) to ingest daily AAA metro and state fuel price archives published by `lykmapipo/US-Gas-Prices`. Eliminates routine HTML scraping and paid proxy overhead for standard daily calibration updates.
- **7-Day Backward Date Auto-Discovery**: Designed an automated backward-scanning discovery loop that probes dates up to 7 days prior ($t, t-1, \dots, t-7$) to seamlessly handle weekend publishing gaps, upstream GitHub commit cadences, and federal holiday release halts without pipeline failure.
- **24-Hour Cache Tiering (`CACHE_TTL_AAA_CSV = 86400`)**: Integrated caching within `global_cache` (`data/lookup_cache.sqlite`), ensuring that once a daily CSV snapshot is resolved and validated, subsequent regional pipeline runs reuse local cache records without redundant network I/O.
- **Comprehensive Multi-Grade Extraction**: Automatically parses and normalizes prices across all commercial fuel grades: **Regular Unleaded**, **Midgrade**, **Premium**, and **Diesel** for all tracked metro areas and state averages.
- **Pipeline Anchor Integration**: Updated [`fetch_live_metro_retail_price()`](src/live_fuel_feed.py) to position the `lykmapipo` daily CSV as Tier-1 primary, cascading to Cloudflare Browser Run, GasBuddy GraphQL, EIA benchmarks, historical last-known, and static PADD anchors.

### 2. Edge Browser Rendering for Dynamic News & State Fuel Dashboards (Issue #640)
- **Edge Headless Chromium News Scraper**: Integrated Cloudflare Browser Rendering API (`@cloudflare/puppeteer` / Quick Actions) to extract full Markdown text from JavaScript-rendered news articles and energy trade publications behind client-side paywalls or Cloudflare Bot Management challenges.
- **Inverted Scraper Hierarchy & Firecrawl Quota Conservation**: Re-architected [`src/firecrawl_scraper.py`](src/firecrawl_scraper.py) to prioritize zero-cost Cloudflare Browser Run edge rendering ahead of Firecrawl API. Conserves 100% of Midgley's strictly capped Firecrawl quota (30 calls/day, 800 calls/month per `AGENTS.md`) by reserving Firecrawl strictly as a secondary metered fallback.
- **Dedicated Regional Outage & Survey Scraper**: Built [`workers/regional_outage_scraper.ts`](workers/regional_outage_scraper.ts) and exposed three new edge routes in [`workers/intraday_monitor_worker.ts`](workers/intraday_monitor_worker.ts):
  - `GET /api/v1/energy/outages/scaqmd`: Monitors South Coast AQMD Rule 1118 refinery flare incident logs for unplanned flaring events across PADD 5 refining complexes (Chevron El Segundo, Torrance, Phillips 66 Carson/Wilmington, Marathon, Valero) with 1-hour TTL.
  - `GET /api/v1/energy/prices/nyserda`: Scrapes the New York State Energy Research and Development Authority (NYSERDA) weekly transportation fuels price survey across New York regional markets with 12-hour TTL.
  - `POST /api/v1/news/scrape-markdown`: General edge headless Chromium rendering endpoint for arbitrary incoming news/press release URLs with 24-hour D1 `edge_cache` snapshot persistence.
- **Unified Python Client Dispatch**: Enhanced [`src/cloudflare_browser_run.py`](src/cloudflare_browser_run.py) to automatically dispatch to either `CLOUDFLARE_BROWSER_RUN_URL` (edge worker microservice) or direct Cloudflare REST API endpoints (`/browser-run/markdown`), seamlessly passing User-Agent `MidgleyAgent/1.0 (+https://koshiirra.github.io/midgley/)`.
- **AAA Retail Fallback Integration**: Maintained [`fetch_aaa_cloudflare_browser_run()`](src/live_fuel_feed.py) in [`src/live_fuel_feed.py`](src/live_fuel_feed.py) as the secondary AAA scraping fallback behind daily CSVs.

### 3. Out-of-Metro & Rural ZIP Code Fallback Cascade (GasBuddy GraphQL First)
- **Hyper-Local Station Resolution**: Implemented [`fetch_live_out_of_metro_price(zip_code, state_code)`](src/live_fuel_feed.py) in [`src/live_fuel_feed.py`](src/live_fuel_feed.py) to handle non-cluster ZIP codes (`is_metro_cluster_hit == False`):
  $$\text{Query}(\text{ZIP}) \xrightarrow{\text{Non-Cluster}} \text{GasBuddy GraphQL (Station)} \xrightarrow{\text{Fallback A}} \text{AAA State CSV} \xrightarrow{\text{Fallback B}} \text{Cloudflare Browser Run} \xrightarrow{\text{Benchmark}} \text{EIA State} \xrightarrow{\text{Anchor}} \text{PADD Anchor}$$
- **Elimination of Legacy Static Fallbacks**: Completely eliminated the hardcoded `$3.890` static placeholder from [`_get_live_prices_impl()`](src/api_server.py) in [`src/api_server.py`](src/api_server.py).
- **Field-Level Provenance & Granularity Tracking**: Out-of-metro responses now populate full provenance metadata via `global_cache.build_provenance_chain()`, explicitly declaring `requested_granularity: "ZIP"`, dynamic `served_granularity` (`"STATION"` for hyper-local hits or `"STATE"` for state-wide fallbacks), upstream provider names, and cache hit/miss states.

### 4. California State Physical Feasibility Outlier Bounds
- **State-Level Invariant Enforcement**: Enhanced [`is_price_outlier()`](src/live_fuel_feed.py) in [`src/live_fuel_feed.py`](src/live_fuel_feed.py) to enforce California physical feasibility bounds $[\$3.50, \$9.00]$ for state-level queries (`state_code == "CA"` or `region_id == "CA"`).
- **Contamination Shield**: Prevents faulty national fallbacks, erroneous station-level submissions, or scraping parsing glitches from poisoning baseline retail levels in California's high-tax, CARBOB-mandated regulatory environment.

### 5. Architectural Governance & Tool Evaluation: Issue #531 Closure
- **Evaluation of FuelRipple**: Thoroughly analyzed GitHub Issue #531 (*[Tool Evaluation] FuelRipple: Crowdsourced Driver Outage / Panic Buying Sentiment Index*).
- **Architectural Determination**: FuelRipple measures consumer panic perceptions and driver reporting frequency rather than physical refinery runs, terminal rack allocations, or pipeline transit volumes. Integrating reflexive consumer sentiment indices into Midgley's spatial econometric solver introduces uncalibrated feedback loops and violates point-in-time observational integrity.
- **Resolution**: Closed Issue #531 as `not planned` with full architectural justification on GitHub, reaffirming Midgley's commitment to physical and econometric ground truth over sentiment proxies.

### 6. Full Quantitative Forecast Card Delivery via `/midgley forecast` (PR #657 / Commit `0f966197`)
- **Rich Forecast Embed Synthesis**: Resolved an issue where Discord `/midgley forecast` embeds displayed supply chain topology, tax structures, and regional basis wedges, but omitted quantitative forecast predictions.
- **Multi-Day Trajectory Display**: Forecast cards now deliver:
  - Projected pump price ($\$/\text{gal}$) with expected price shift ($\Delta P$ dollars and percentage) and directional trend indicators ($\nearrow$ UP, $\searrow$ DOWN, $\rightarrow$ FLAT).
  - 95% calibrated confidence intervals based on regional historical residual distributions.
  - Active baseline benchmarks and local basis spread synthesis notes for out-of-metro ZIP codes.
  - Complete multi-day out-of-time trajectory path ($1\text{D} \rightarrow 5\text{D}$).

### 7. Leaflet Basemap Tile Authentication & Workflow Secrets (`CARTO_API_KEY` / Issue #646)
- **Authenticated CARTO Dark Matter Tiles**: Integrated [`get_carto_basemap_url()`](src/dashboard_generator.py) in [`src/dashboard_generator.py`](src/dashboard_generator.py) to authenticate Leaflet map tiles across both the Geographic Footprint overview on [`docs/index.html`](docs/index.html) and the demand heatmap on [`docs/telemetry.html`](docs/telemetry.html).
- **Sanitized Credentials**: Sanitized query parameters to prevent cleartext token leakage (`py/clear-text-storage-sensitive-data`), wired `CARTO_API_KEY` through GitHub Actions workflows, and provided configurable `MIDGLEY_BASEMAP_TILE_URL` overrides for self-hosted deployments.

### 8. Production CI/CD Workflow Secret Parity
- **Cloudflare Edge Secret Wiring**: Wired `CLOUDFLARE_ACCOUNT_ID` and `CLOUDFLARE_API_TOKEN` across all production GitHub Actions workflows ([`.github/workflows/gas_price_forecast.yml`](.github/workflows/gas_price_forecast.yml), [`.github/workflows/weekly_model_review.yml`](.github/workflows/weekly_model_review.yml), [`.github/workflows/intraday_event_monitor.yml`](.github/workflows/intraday_event_monitor.yml), [`.github/workflows/deploy_cloudflare_worker.yml`](.github/workflows/deploy_cloudflare_worker.yml)), ensuring scheduled runs can execute Cloudflare Browser Run rendering in production CI.

### 9. Cloudflare Workers AI, Vectorize Deduplication & Hindsight Memory Mesh (Issue #645)
- **Zero-Shot Catalyst & Severity Scoring at the Edge**: Implemented [`workers/ai_event_scorer.ts`](workers/ai_event_scorer.ts) using `@cf/meta/llama-3.2-3b-instruct` to classify incoming news headlines and EDGAR 8-K filings into structured catalyst domains (`refinery_pipeline`, `weather_hurricane`, `geopolitical_opec`, `regulatory_tax`, `noise`), identifying affected hubs, expected direction, and decay half-lives directly at the edge with zero external API fees.
- **Sub-10ms Edge Vector Search with Cloudflare Vectorize**: Wired `[[vectorize]] binding = "EVENT_INDEX"` and `@cf/baai/bge-small-en-v1.5` dense embeddings into [`workers/intraday_monitor_worker.ts`](workers/intraday_monitor_worker.ts). Enforces strict cosine similarity gates: $\ge 0.88$ suppresses redundant wire alerts, $[0.70, 0.88)$ flags evolving development status updates, and $< 0.70$ indexes novel events.
- **Unified Hindsight Memory Mesh (`midgley-event-dedupe`)**: Integrated Tier-2 cross-environment memory recall and non-blocking background retention via `ctx.waitUntil()`. Automatically persists confirmed edge anomalies into the shared Hindsight SaaS `midgley-event-dedupe` memory bank, keeping edge workers and Python batch pipelines ([`src/hindsight_dedupe.py`](src/hindsight_dedupe.py)) 100% synchronized in memory.
- **Grounded Institutional Analyst Briefings**: Powered Discord `/midgley forecast` slash commands and DM alerts with `@cf/meta/llama-3.1-8b-instruct`, dynamically synthesizing a 2-sentence institutional summary explaining wholesale basis movements strictly grounded in point-in-time model metrics.
- **Hermetic Latency Boundaries & Fallbacks**: Enforced a hard 1,500ms `Promise.race` timeout ceiling with deterministic fallback to `fallbackRegexScore()` and D1 cache tables, guaranteeing zero cron halts or worker timeouts. Added 16 unit tests across edge AI scoring, Vectorize deduplication, and Hindsight recall in [`tests/workers.test.ts`](tests/workers.test.ts).

### 10. Cloudflare Browser Run Scraper Failover & Client Hardening (Issue #640)
- **Firecrawl Scraper Failover**: Instrumented [`src/firecrawl_scraper.py`](src/firecrawl_scraper.py) with `_scrape_via_cloudflare_browser_run()`. When `FIRECRAWL_API_KEY` is omitted or safety quotas (800 calls/month, 30/day) are reached, the connector now automatically attempts edge headless rendering via Cloudflare Browser Run before falling back to local deterministic regex HTML parsing.
- **Client Authentication & Dual Endpoint Resilience**: Refactored `resolve_cloudflare_api_token()` in [`src/cloudflare_browser_run.py`](src/cloudflare_browser_run.py) to eliminate invalid Wrangler CLI OAuth token leakage and HTTP 401 errors, requiring explicit `CLOUDFLARE_API_TOKEN` / `CLOUDFLARE_AUTH_TOKEN` environment variables. Added dual-path fallback between `/browser-run/markdown` and `/browser-rendering/markdown`.
- **HTTP Client User-Agent Normalization**: Updated `http_get()` and `http_post()` in [`src/http_client.py`](src/http_client.py) to safely accept and extract `user_agent` keyword arguments directly into request headers, eliminating `TypeError: Session.request() got an unexpected keyword argument 'user_agent'` crashes during Drillinginfo and Enverus daily rig count upstream failovers.
- **Full Connector Telemetry & Audit Observability**: Fully wired `log_connector_event("Cloudflare_Browser_Run", ...)` across [`src/live_fuel_feed.py`](src/live_fuel_feed.py), [`src/firecrawl_scraper.py`](src/firecrawl_scraper.py), and [`src/cloudflare_browser_run.py`](src/cloudflare_browser_run.py), recording real-time latency and execution status into `data/connector_telemetry.json` and the 7-day performance audit table in `docs/telemetry.html`.

### 11. Intraday Anomaly Duplicate Review Filtering & HMAC Signature Resiliency
- **Duplicate & Pending Review Suppression**: Filtered pending reviews and duplicate events in [`src/dashboard_generator.py`](src/dashboard_generator.py) and [`src/data_ingestion.py`](src/data_ingestion.py) to suppress duplicate follow-up catalysts and pending review flags from contaminating intelligence dashboards and regional model inputs.
- **HMAC Flag Link Signature Resiliency**: Hardened duplicate review action links in [`src/discord_notifier.py`](src/discord_notifier.py) with automatic credential fallbacks (`FLAG_SIGNING_KEY` $\rightarrow$ `ADMIN_TOKEN` $\rightarrow$ `CLOUDFLARE_AUTH_TOKEN`), and added `FLAG_SIGNING_KEY` to [`.env.example`](.env.example).

### 12. Friday Pre-Audit Production Data Sync & Discord Notification
- **Automated Friday Afternoon Pre-Audit Reconciliation**: Scheduled [`.github/workflows/pre_audit_data_sync.yml`](.github/workflows/pre_audit_data_sync.yml) every Friday at 21:00 UTC (04:00 PM US Central Time, `cron: '0 21 * * 5'`), reconciling all ground-truth prediction records, run manifests, and telemetry from `origin/main` into `dev` prior to Saturday morning's weekly model performance review.
- **Non-Destructive JSON Merge Engine**: Implemented [`scripts/reconcile_production_sync.py`](scripts/reconcile_production_sync.py) with a 3-way conflict resolver for [`data/intraday_events.json`](data/intraday_events.json) that preserves both newly dispatched production events and qualitative duplicate review decisions made on `dev`.
- **Discord MLOps Embed Notifications**: Automatically dispatches rich status alerts to `DISCORD_WEBHOOK_URL` confirming merge status, number of production commits reconciled, and Saturday review audit readiness. Added 8 unit tests in [`tests/test_reconcile_production_sync.py`](tests/test_reconcile_production_sync.py).

### 13. PADD 2 Midwest Regional & State-Level Event Scoping (Issue #659)
- **Multi-Hub Midwest & PADD 2 Corridor Targeting**: Enhanced [`resolve_target_locales()`](src/intraday_event_monitor.py) in [`src/intraday_event_monitor.py`](src/intraday_event_monitor.py) to map Midwest, Great Lakes, and state-level refinery disruptions (Illinois, Michigan, Indiana, Wisconsin, Ohio, Kentucky) directly to regional metro models (**Chicago** and **Cincinnati**) instead of defaulting to `National` scope.
- **Regional Ingestion Keyword Taxonomy Synchronization**: Extended `REGIONAL_KEYWORDS` in [`load_live_regional_intraday_events()`](src/data_ingestion.py) across all 15 modeled hubs (including `chicago`, `houston`, `losangeles`, `denver`, `newyork`, `seattle`, `phoenix`, `boston`, etc.), ensuring regional daily pipeline feature fusion correctly pulls breaking intraday catalysts.
- **False-Positive Diagnostic Reviewer Disambiguation**: Updated [`scripts/review_false_positive.py`](scripts/review_false_positive.py) to differentiate between true non-energy false positives and **geographic scope misrouting**. When an issue reports regional targeting defects on valid energy disruptions, the agent now recommends extending `resolve_target_locales()` rather than erroneously suppressing legitimate catalysts via `NON_ENERGY_TARIFF_EXCLUDE`. Added regression unit tests across [`tests/test_intraday_event_monitor.py`](tests/test_intraday_event_monitor.py), [`tests/test_false_positive_reviewer.py`](tests/test_false_positive_reviewer.py), and [`tests/test_regional_event_fusion.py`](tests/test_regional_event_fusion.py).

### 14. Non-Breaking Retrospective Statistical Recap Filtering (Issue #658)
- **Periodic Recap & Summary Suppression**: Introduced [`RETROSPECTIVE_RECAP_PATTERNS`](src/intraday_event_monitor.py) in [`src/intraday_event_monitor.py`](src/intraday_event_monitor.py) to filter historical monthly aggregations and retrospective recaps (e.g., `"<Month> marks highest/lowest..."`, `"monthly recap"`, `"year in review"`, `"quarterly summary"`).
- **False Intraday Impulse Shielding**: Prevents historical statistical roundups from being misclassified as breaking physical disruptions, preserving point-in-time observational integrity without applying spurious new $\Delta P$, $S$, or $G$ shocks. Added unit tests in [`tests/test_intraday_event_monitor.py`](tests/test_intraday_event_monitor.py) and [`tests/test_false_positive_reviewer.py`](tests/test_false_positive_reviewer.py).

### 15. Cross-Repository Catalog Deduplication & UTF-8 Subprocess Safety (Issues #679–#692)
- **Cross-Repository Issue Deduplication**: Implemented [`get_existing_issues_cache()`](src/catalog_monitor.py) and enhanced [`check_existing_issue()`](src/catalog_monitor.py) in [`src/catalog_monitor.py`](src/catalog_monitor.py) to audit candidate tools across both `KoshiirRa/midgley` and companion repositories (`KoshiirRa/agentic-trading-robinhood`). Prevents duplicate feature requests when issues are moved or tracked in affiliated projects.
- **Multi-Vector Match Strategy**: Enforces three layers of deduplication matching: exact issue title, normalized tool name (`ingest <tool_name>`), and candidate clean URL in issue bodies.
- **In-Memory Cache Tiering**: Caches repository issues in-memory per run (`_EXISTING_ISSUES_CACHE`) across target repositories, eliminating redundant CLI and REST API calls.
- **UTF-8 Subprocess Decoding Guard**: Enforced `encoding="utf-8", errors="replace"` across all `subprocess.run` invocations in `catalog_monitor.py` to prevent Windows `charmap` `UnicodeDecodeError` when decoding GitHub issues with emoji or special characters.
- **Triage & Cleanup**: Closed duplicate issues #679–#692 with links to their counterparts in `KoshiirRa/agentic-trading-robinhood` (#54–#67), and closed dev review #678 as superseded by production weekly review #693. Added unit tests in [`tests/test_catalog_monitor.py`](tests/test_catalog_monitor.py).

### 16. Expanded Tier-1/Tier-2 Refinery & Regional Midstream 8-K Feed Coverage (Issue #644)
- **Comprehensive Domestic Refining Footprint**: Expanded default 8-K monitoring ticker coverage from 5 operators (`PBF, DINO, MPC, VLO, PSX`) to 12 major Tier-1 supermajors, regional single-refinery operators, and midstream pipelines: `PBF, DINO, MPC, VLO, PSX, XOM, CVX, SU, PARR, DK, KMI, EPD`. Covers Front Range (Denver/PADD 4 via Suncor Commerce City `SU`), Pacific Island supply (Hawaii/PADD 5 via Par Pacific Kapolei `PARR`), Gulf Coast/West Coast corridors (ExxonMobil `XOM`, Chevron `CVX`, Delek `DK`), and critical interstate pipelines (Kinder Morgan Plantation/SFPP `KMI`, Enterprise Products TEPPCO `EPD`).
- **HTTP Conditional GET (ETag & If-Modified-Since Caching)**: Instrumented [`pollEdgar8KFeeds()`](workers/intraday_monitor_worker.ts) in [`workers/intraday_monitor_worker.ts`](workers/intraday_monitor_worker.ts) with ETag and `If-Modified-Since` conditional headers. Unchanged Atom feeds return `304 Not Modified`, skipping expensive XML parsing and bandwidth consumption during routine 15-minute cron cycles.
- **Fast-Path Title Keyword Pre-Filtering**: Pre-filters raw XML entries on operational title keywords (`fire`, `explosion`, `force majeure`, `outage`, `shutdown`, `flaring`, `upset`, `crude distillation`, `coker`, `fcc`, `pipeline`, `hurricane`) before executing full regexes (`linkRegex`, `updatedRegex`), eliminating ~90% of non-operational corporate noise (earnings, appointments, debt offerings) with sub-millisecond CPU overhead.
- **Edge Accession Deduplication via D1 `edgar_8k_seen` Table**: Created Cloudflare D1 migration [`scripts/migrations/0004_create_edgar_8k_seen_table.sql`](scripts/migrations/0004_create_edgar_8k_seen_table.sql) with explicit primary key and secondary indexes (`idx_edgar_8k_seen_accession`, `idx_edgar_8k_seen_ticker`, `idx_edgar_8k_seen_filed_at`). Tracks `accession_id` permanently to prevent duplicate event ingestion across worker cycles and Python batch pipelines.
- **SEC Fair Access Compliance & Test Isolation**: Enforced a 120ms inter-request delay guaranteeing $\le 10\text{ req/s}$ per SEC EDGAR Fair Access policy with compliant `SEC_USER_AGENT` defaults (`Midgley energy-forecasting contact@domain.com`). In `TESTING=1`, all external Atom requests are mocked with synthetic XML fixtures in [`tests/test_intraday_event_monitor.py`](tests/test_intraday_event_monitor.py) and [`tests/workers.test.ts`](tests/workers.test.ts).
- **Public Data Sources Catalog Updates**: Updated Card 3.6 in [`src/sources_generator.py`](src/sources_generator.py) and regenerated [`docs/sources.html`](docs/sources.html) to document expanded operator entities, HTTP 304 caching, and joint consumers.

### 17. Cloudflare Queue Architecture Hardening & Extended CPU Batch Consumption (Issue #643)
- **Bulk SQL Deduplication (`areHeadlinesDispatchedInBatch`)**: Refactored [`handleQueueBatch()`](workers/intraday_monitor_worker.ts) in [`workers/intraday_monitor_worker.ts`](workers/intraday_monitor_worker.ts) from sequential single-message database lookups to single-round-trip bulk SQL deduplication (`SELECT clean_key FROM seen_rss_headlines WHERE clean_key IN (?, ?, ...)`). Deduplicates entire batches of up to 10 messages in one D1 query.
- **Bounded Concurrency Pool (`runWithBoundedConcurrency`)**: Implemented zero-dependency bounded concurrent execution (`limit = 4`) via `Promise.allSettled`, dispatching Workers AI catalyst scoring, Vectorize deduplication, and GitHub repository dispatch actions concurrently across batch messages without triggering GitHub API secondary rate limits.
- **Exponential Retry Backoff**: Enhanced message retry handling to supply dynamic exponential delay options (`message.retry({ delaySeconds })`, scaling from 10s up to 300s based on retry attempts), preventing rapid retry exhaustion on transient 5xx downstream errors.
- **Dead-Letter Queue (DLQ) Consumer & Storage Migration**: Configured consumer block for `intraday-event-dlq` in [`wrangler.toml`](wrangler.toml) and added D1 table [`scripts/migrations/0005_create_queue_dlq_records_table.sql`](scripts/migrations/0005_create_queue_dlq_records_table.sql) (`queue_dlq_records`). The new [`handleDlqBatch()`](workers/intraday_monitor_worker.ts) captures failed payloads with error metadata and attempts, and acknowledges DLQ items to prevent infinite looping.
- **Fail-Closed Admin Triage & Replay Routes**: Added authenticated admin endpoints `GET /admin/queues/dlq` (inspect pending dead-letter messages) and `POST /admin/queues/replay-dlq` (re-enqueue payloads to `INTRADAY_QUEUE` and mark `replayed_at`), protected by constant-time `ADMIN_TOKEN` verification (`timingSafeEqual`).
- **Comprehensive Observability & Test Suite**: Expanded Axiom telemetry with `duration_ms`, `cached_hits`, `semantic_dupes`, `scored_noise`, and `dispatched` metrics, and added 10 automated unit and integration tests in [`tests/workers.test.ts`](tests/workers.test.ts).

---


### 18. Direct Edge Database TCP Connections via `cloudflare:sockets` & Hyperdrive (Issue #641)
- **Direct PostgreSQL Socket Connectivity**: Implemented [`PostgresAdapter`](workers/db_adapter.ts) in [`workers/db_adapter.ts`](workers/db_adapter.ts) utilizing `postgres.js` and Node compatibility (`nodejs_compat`), mapping directly to native `cloudflare:sockets` TCP connections in Cloudflare Workers isolates.
- **Hyperdrive Edge Connection Pooling**: Added support for Cloudflare Hyperdrive bindings (`env.PROD_DB`) in [`workers/cache_worker.ts`](workers/cache_worker.ts), enabling sub-15ms low-latency global query routing, connection pooling, and edge read-caching to centralized PostgreSQL instances (self-hosted on `dev-vm` / `LAB-HOST`, Supabase, or Neon).
- **Multi-Tier Defensive Fallback Architecture**: Built [`ResilientStorageAdapter`](workers/db_adapter.ts) to transparently route operations across storage tiers (`Hyperdrive TCP -> Cloudflare D1 -> In-Memory`), ensuring that network drops, TCP connection timeouts (>5s), or socket refusals automatically fail over to Cloudflare D1 (`env.DB`) while emitting Axiom and Sentry telemetry warnings.
- **Dialect Invariant Decoupling**: Standardized key-value lookups, prediction history batch sync, and distributed advisory locking (`pg_try_advisory_lock` for provider rate-limit mutexes) behind the unified `StorageAdapter` interface, isolating Postgres vs SQLite SQL dialect differences.
- **Pure Test Isolation & Test Suite**: Added 5 automated unit and integration tests in [`tests/workers.test.ts`](tests/workers.test.ts) covering cache operations, batch prediction ingestion, advisory locking, and transparent connection failover under pure mock isolation without opening network sockets.

---

## 🛠️ Data Catalog & Documentation Updates

1. **Data Sources Catalog Card 5.3**:
   - Updated Data Sources Card 5.3 in [`src/sources_generator.py`](src/sources_generator.py) to document the multi-tier retail feed architecture: `lykmapipo` daily CSVs (24h TTL), Cloudflare Browser Run edge rendering, and GasBuddy GraphQL.
   - Regenerated [`docs/sources.html`](docs/sources.html) and [`docs/sources/index.html`](docs/sources/index.html).
2. **Data Sources Catalog Card 3.6 (SEC EDGAR 8-K Outage Filings)**:
   - Updated Data Sources Card 3.6 in [`src/sources_generator.py`](src/sources_generator.py) to reflect Tier-1/Tier-2 operator entities (`PBF, DINO, MPC, VLO, PSX, XOM, CVX, SU, PARR, DK, KMI, EPD`), 15-minute cron with HTTP 304 ETag caching, and consumers (`src/edgar_8k_monitor.py`, `workers/intraday_monitor_worker.ts`).
   - Regenerated [`docs/sources.html`](docs/sources.html) and [`docs/sources/index.html`](docs/sources/index.html).
3. **Release Notes Reconciliation**:
   - Reconciled [`RELEASE_NOTES_v0.8.6.md`](RELEASE_NOTES_v0.8.6.md) to preserve its official release boundary at `29ae13dc` (reverting intermediate draft notes).
   - Opened this document ([`RELEASE_NOTES_v0.8.7.md`](RELEASE_NOTES_v0.8.7.md)) as the active in-progress draft for v0.8.7.

---

## 🧪 Verification Commands & Test Results

All test runs and code analyses were offloaded to the dedicated Linux dev VM (`dev-vm`, `marty@10.42.42.54`):

```bash
# 1. Fuel Feed, ZIP Geocoding & API Server Integration Suite (50 tests)
TESTING=1 pytest -v tests/test_live_fuel_feed.py tests/test_zip_geocoding.py tests/test_api_server.py

# 2. Cloudflare Browser Run, Scrapers & Rig Count Verification (53 tests)
TESTING=1 pytest -v tests/test_cloudflare_browser_run.py tests/test_firecrawl_scraper.py tests/test_enverus_rig_feed.py tests/test_live_fuel_feed.py tests/test_discord_notifier.py

# 3. Data Sources Page Generation Suite
TESTING=1 pytest -v tests/test_dashboard_generator.py -k test_data_sources_page_generation

# 4. Documentation & Link Hygiene Suite
TESTING=1 pytest -v tests/test_docs_links.py

# 5. Full Codebase Linter & Style Enforcement
ruff check src/ tests/
```

### Verified Test Results on `dev-vm`
- **`tests/test_live_fuel_feed.py`**: 12/12 passed (tested `fetch_aaa_csv_prices`, `fetch_aaa_cloudflare_browser_run`, `fetch_live_out_of_metro_price`, `is_price_outlier`, fallback cascades).
- **`tests/test_zip_geocoding.py`**: 13/13 passed (tested cluster hits, rural non-cluster resolution, telemetry aggregation, coordinate lookups).
- **`tests/test_api_server.py`**: 25/25 passed (tested authentication, live prices endpoint with ZIP codes, simulation, webhooks).
- **`tests/test_cloudflare_browser_run.py`**: 11/11 passed (tested client configuration, token resolution, dual endpoints, and error handling).
- **`tests/test_firecrawl_scraper.py`**: 8/8 passed (tested Cloudflare Browser Run failover, quota checks, and fallback extraction).
- **`tests/test_enverus_rig_feed.py`**: 6/6 passed (tested Drillinginfo direct API, worker endpoint, and benchmark fixtures).
- **`tests/test_discord_notifier.py`**: 16/16 passed (tested duplicate review link signature generation, fallbacks, and test suppression).
- **`tests/test_dashboard_generator.py`**: 1/1 passed (`test_data_sources_page_generation`).
- **`tests/test_docs_links.py`**: 2/2 passed (verified zero local `file://` URLs in generated docs).
- **`tests/test_catalog_monitor.py`**: 6/6 passed (tested multi-repo deduplication, exact title, tool name match, URL matching, and barred tool suppression).
- **`tests/test_edgar_8k_monitor.py`**: 9/9 passed (tested operational keyword gates, expanded Tier-1/Tier-2 tickers, accession cache deduplication, and backward-compat shim).
- **`tests/test_intraday_event_monitor.py`**: 35/35 passed (tested regional routing for XOM, CVX, SU, PARR, DK, KMI, EPD, and synthetic Atom fixture test isolation).
- **`tests/workers.test.ts`**: 58/58 passed (tested Cloudflare Worker edge polling, ETag 304 skipping, title pre-filtering, and D1 `edgar_8k_seen` deduplication).
- **`ruff check src/ tests/`**: All checks passed cleanly with zero linting or formatting errors.

---

## 🤖 AI Agent Reconciliation Block

For autonomous AI coding assistants, downstream forks, and self-hosted deployments:

### 1. Architectural Changes
* **Feed Hierarchy**: Retail price resolution now follows `lykmapipo` CSV $\rightarrow$ Cloudflare Browser Run $\rightarrow$ GasBuddy GraphQL $\rightarrow$ EIA $\rightarrow$ History $\rightarrow$ PADD Anchor.
* **Scraper Fallback Cascade**: Web scraping across intelligence feeds follows Firecrawl API $\rightarrow$ Cloudflare Browser Run (`/browser-run/markdown` and `/browser-rendering/markdown`) $\rightarrow$ native deterministic HTML parser.
* **ZIP Resolution**: Out-of-metro ZIP requests strictly return authentic local station observations (via GasBuddy) or state-level observations (via AAA state CSV), never falling back to static arbitrary constants.
* **Edge Intelligence & Vector Mesh**: Cloudflare Workers Paid leverages Workers AI (`@cf/meta/llama-3.2-3b-instruct`) and Vectorize (`midgley-event-embeddings`) for real-time catalyst scoring and sub-10ms semantic deduplication, automatically synchronizing confirmed events into the shared Hindsight SaaS `midgley-event-dedupe` memory bank.
* **EDGAR 8-K Feed Coverage & Edge Caching (Issue #644)**: Expanded default refinery 8-K polling coverage from 5 to 12 operators (`PBF, DINO, MPC, VLO, PSX, XOM, CVX, SU, PARR, DK, KMI, EPD`), introduced ETag / `If-Modified-Since` HTTP 304 conditional request caching, fast-path title keyword pre-filtering, and permanent edge deduplication via Cloudflare D1 `edgar_8k_seen` table ([`scripts/migrations/0004_create_edgar_8k_seen_table.sql`](scripts/migrations/0004_create_edgar_8k_seen_table.sql)).

### 2. Environment Variables & Secrets
* `EDGAR_8K_TICKERS` *(Optional)*: Comma-separated list of refinery operator tickers to poll for 8-K filings (defaults to `"PBF,DINO,MPC,VLO,PSX,XOM,CVX,SU,PARR,DK,KMI,EPD"`).
* `CLOUDFLARE_ACCOUNT_ID` *(Optional)*: Cloudflare Account ID for edge headless browser rendering.
* `CLOUDFLARE_API_TOKEN` *(Optional)*: Cloudflare API token with Browser Rendering and Workers permissions.
* `CLOUDFLARE_BROWSER_RUN_URL` *(Optional)*: URL of a deployed Cloudflare Worker exposing Browser Run capabilities.
* `FLAG_SIGNING_KEY` *(Optional)*: HMAC secret for signing Discord flag and duplicate review buttons (falls back to `ADMIN_TOKEN` / `CLOUDFLARE_AUTH_TOKEN`).
* `CARTO_API_KEY` *(Optional)*: Key for authenticating CARTO Dark Matter map tiles on public dashboards.
* `HINDSIGHT_API_TOKEN` *(Optional)*: Bearer token for authenticating against the Hindsight SaaS memory bank (`midgley-event-dedupe`).
* `HINDSIGHT_API_URL` *(Optional)*: Hindsight API base URL (defaults to `https://api.hindsight.vectorize.io`).
* `HINDSIGHT_DEDUPE_BANK_ID` *(Optional)*: Target memory bank ID (defaults to `midgley-event-dedupe`).

