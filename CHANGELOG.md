# Changelog

All notable changes to this project will be documented in this file.
The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.0.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [Unreleased]

### Added
- Greater Chicago Metro Calibration Hub (`Chicago_IL`, PADD 2) covering BP Whiting (435 kbpd), CITGO Lemont (177 kbpd), and ExxonMobil Joliet (251 kbpd) refineries (#219).
- Point-in-time regional metadata `data/regional_metadata/chicago_il.json` with Cook County/Chicago tax structure ($0.805/gal statutory base), Indiana cross-border arbitrage, EPA RFG 7.4 psi RVP limits, and shock scenarios (#219).
- Subpackage implementation `src/locations/chicago/` (`main.py`, `regional.py`, `notebook_builder.py`) registered in location specs and multi-metro runner (#219).
- Public dashboard page `docs/chicago.html` with multi-agent architecture, Leaflet refinery delivery corridor maps, and live weather telemetry (#219).
- EPA RVP Reformulated Gasoline (RFG) rules (7.4 psi summer, 13.0 psi winter) for Greater Chicago in `data/regulatory_rvp_rules.json` and `src/rvp_regulations.py` (#219).
- Houston & USGC Metro Calibration Hub (`Houston_TX`, PADD 3) anchoring the US Gulf Coast refining epicenter (>52% US operable refining capacity: Baytown, Port Arthur, Galveston Bay, Deer Park, Pasadena) (#220).
- Point-in-time regional metadata `data/regional_metadata/houston_tx.json` with Texas motor fuel tax structure ($0.200/gal statutory fixed excise, $0.384/gal total baseline with federal), Houston Ship Channel spot pass-through, EPA Low-RVP Area standard (7.8 psi summer), and hurricane/freeze shock scenarios (#220).
- Subpackage implementation `src/locations/houston/` (`main.py`, `regional.py`, `notebook_builder.py`) registered in location specs and multi-metro runner (#220).
- Public dashboard page `docs/houston.html` with USGC refining corridor shock simulations, plain-English automated narrative synthesis, and live weather telemetry (#220).
- EIA API v2 retail gasoline series mappings (`EMM_EPMR_PTE_Y44HO_DPG` for Houston, `EMM_EPMR_PTE_STX_DPG` for Texas, `EMM_EPMR_PTE_R30_DPG` for PADD 3 Gulf Coast) in `src/eia_retail_feed.py` (#220).
- Los Angeles Basin Metro Calibration Hub (`Los_Angeles_CA`, PADD 5) anchoring Southern California's CaRFG refining complex (Marathon Carson/Wilmington 363 kbpd, Chevron El Segundo 269 kbpd, PBF Torrance 166 kbpd, Phillips 66 Wilmington 139 kbpd, Valero Wilmington 85 kbpd) (#221).
- Point-in-time regional metadata `data/regional_metadata/los_angeles_ca.json` with CARB regulatory burden ($0.953/gal statutory base, $1.407/gal total with local sales tax), LA CARBOB spot pass-through (`EER_EPMRU_PF4_RLA_DPG`), CARB Phase 3 RVP standard (7.0 psi March 1–October 31), and El Segundo/Torrance/Newport-Inglewood shock scenarios (#221).
- Subpackage implementation `src/locations/los_angeles/` (`main.py`, `regional.py`, `notebook_builder.py`) registered in location specs and multi-metro runner (#221).
- Public dashboard page `docs/los_angeles.html` with South Coast Basin refining shock simulations, plain-English automated narrative synthesis, and live weather/AQI telemetry (#221).
- EIA API v2 retail gasoline series mapping (`GASREGWLA` -> `EMM_EPMR_PTE_Y05LA_DPG` for Los Angeles-Long Beach-Anaheim MSA) in `src/eia_retail_feed.py` (#221).
- Denver & Rocky Mountain Metro Calibration Hub (`Denver_CO`, PADD 4) anchoring Colorado's Front Range refining hub and Rocky Mountain distribution network (Suncor Commerce City 103 kbpd refinery) (#618).
- Point-in-time regional metadata `data/regional_metadata/denver_co.json` with Colorado statutory motor fuel tax structure ($0.280/gal statutory base, $0.464/gal baseline with federal), Denver rack spot pass-through, EPA Front Range 7.8 psi summer RVP standard, and Suncor outage / ozone nonattainment shock scenarios (#618).
- Subpackage implementation `src/locations/denver/` (`main.py`, `regional.py`, `notebook_builder.py`) registered in location specs and multi-metro runner (#618).
- Public dashboard page `docs/denver.html` with Front Range / PADD 4 shock scenario simulations, plain-English automated narrative synthesis, and live weather telemetry (#618).
- EIA API v2 retail gasoline & diesel series mappings (`GASREGWDEN`, `GASREGWCO`, `GASREGWRM`, `GASDESWRM`) in `src/eia_retail_feed.py` (#618).
- New York Harbor & New York State Metro Calibration Hub (`New_York_NY`, PADD 1B) anchoring Central Atlantic fuel distribution, Phillips 66 Bayway (258 kbpd) refining, Buckeye pipeline corridor, and NY Harbor waterborne barge transit (#635).
- Point-in-time regional metadata `data/regional_metadata/new_york_ny.json` with New York State motor fuel tax structure ($0.472/gal statutory base, $0.656/gal baseline with federal), downstate NYC/suburban county sales tax compounding (+14.0¢/gal), Upstate Adirondacks transport basis spread (+18.0¢/gal), downstate EPA RFG 7.4 psi vs Upstate 9.0 psi summer RVP standards, and Buckeye pipeline / barge freeze shock scenarios (#635).
- Subpackage implementation `src/locations/new_york/` (`main.py`, `regional.py`, `notebook_builder.py`) registered in location specs and multi-metro runner (#635).
- Public dashboard page `docs/new_york.html` with New York Harbor / PADD 1B shock scenario simulations, plain-English automated narrative synthesis, and live weather telemetry (#635).
- EIA API v2 retail gasoline & diesel series mappings (`GASREGWNYC`, `GASREGWNY`, `GASDESWNY`) in `src/eia_retail_feed.py` (#635).
- MinT Hierarchical Engine integration in `src/hierarchical_engine.py` incorporating `New_York_NY` into PADD 1B cluster (`Newark_DE` and `New_York_NY`) with exact aggregation coherence (#635).
- ZIP prefix routing for NY ZIPs (`100`..`149`) resolving to `new_york` hub in `src/zip_geocoding.py`, resolving out-of-metro departure wedge against Delaware baseline (#635).
- Multi-subscriber Discord Webhook & Direct Message (`discord_dm`) subscription registry (`DiscordSubscriptionRegistry` in `src/discord_notifier.py`, `discord_subscriptions` table in `src/db/schema.sql`) with Fernet/HMAC encryption at rest, locale/threshold/direction/catalyst filtering, and automatic dead-webhook (`HTTP 404/410`) and blocked-DM (`HTTP 403 / 50007`) circuit breaking (#235).
- REST API Discord subscription & diagnostic endpoints (`POST /api/v1/notifications/discord/subscribe`, `DELETE /api/v1/notifications/discord/subscriptions/{subscription_id}`, `GET /api/v1/notifications/discord/subscriptions/status`, `POST /api/v1/notifications/discord/test`) protected by IPASIS IP reputation checks in `src/api_server.py` (#235).
- Interactive `/midgley` Discord Application Slash Commands (`subscribe`, `unsubscribe`, `status`, `forecast`, `test-alert`) and locale autocomplete on `/discord/interactions` in `workers/intraday_monitor_worker.ts` with ephemeral (`flags: 64`) in-channel responses, private Direct Message delivery (`DISCORD_BOT_TOKEN`), and `scripts/register_discord_commands.py` (#235).

### Fixed
- Initialized `dynamic_fetches_succeeded` counter and guarded test-mode persistence in `src/alternative_data_feeds.py`.

## [0.8.5] - 2026-10-06

### Added
- Official EIA API v2 client (`EIAClientV2`) in `src/eia_api_client.py` for automated weekly retail ground truth and WPSR supply fundamentals (#608, Finding 3.1 & 3.2).
- Exchange trading calendar engine `NYMEXTradingCalendar` in `src/market_calendar.py` implementing CME Globex holiday rules and RBOB contract roll boundary detection (`is_roll_straddling`) (Finding A-5 & A-8).
- Modern USGS OGC API continuous items endpoint integration (`api.waterdata.usgs.gov`) in `src/usgs_water_feed.py` and `src/usace_locks.py` ahead of legacy waterservices sunset (Finding 3.2).
- Source URLs and announcement dates for statutory fuel tax events in `data/known_future_events.json` (Finding T-1 & T-4).
- Authentic EIA API v2 regional weekly retail gasoline time series (`GASREGWOK`, `GASREGW01B`, `GASREGWOH`, `GASREGWKY`, `GASREGWNC`, `GASREGWFL`, `GASREGWCA`, `EMM_EPMR_PTE_Y05SF_DPG`) mapped to regional metro evaluation targets (#608).
- Deterministic forecast ID generator function `generate_canonical_forecast_id()` and in-memory ledger deduplication (#602).
- Non-destructive union merge logic `merge_historical_geopolitical_records()` in geopolitical news feed (#603).
- Proportional dynamic narrative attribution driver calculation matching forecast direction signs and sums (#604).
- Single-use token tracking table `intraday_flag_tokens` in Cloudflare D1 schema with atomic replay enforcement (#605).
- Dead-man switch heartbeat reporting (Healthchecks.io) in automated prediction pipelines (#606).
- Production Pirate Weather connector wiring (`PirateWeatherConnector`) into `create_feature_matrix()` in `src/feature_engineering.py` for live heating degree days (HDD), cooling degree days (CDD), and freeze warning telemetry (#442).
- Pirate Weather polar freeze telemetry hook in `_evaluate_live_telemetry_trigger()` in `src/scenario_engine.py` evaluating `freeze_off_risk_index` and freezing thresholds for refinery cold-weather outages (#442).
- Pirate Weather MCP tool `get_pirate_weather_telemetry` in `src/mcp_server.py` and REST endpoint `GET /api/v1/weather/pirate` in `src/api_server.py` (#442).

### Changed
- Consolidated Oakland and SF Bay Area into canonical `BayArea_CA` regional hub across specs, runner, public dashboard, and test suites, with `docs/oakland.html` redirecting to `docs/bayarea.html` (Finding 3.7).
- Replaced naive `bdate_range` calendar calculations in `src/models.py` and `src/prediction_logger.py` with exchange trading calendar `NYMEXTradingCalendar` (Finding A-5 & A-8).
- Refactored `AsymmetricECM` to ingest authentic EIA weekly price history for cointegration estimation, replacing synthetic wholesale markup proxies (#607).
- Upgraded model version tagging to semantic version string `v2.1.0-asym-ecm` dynamically resolved via `src.version` (#607).
- Replaced hardcoded accuracy metrics in metro HTML dashboard cards with dynamic evaluations (#604).
- Aligned forecast maturity realization window with exchange trading calendars (`get_target_date_for_horizon`) (#601).
- Updated Ohio motor fuel tax calendar with Ohio HB 519 statutory tax holiday ($-0.385$/gal effective 4 Oct 2026 to 2 Jan 2027; restoration 3 Jan 2027) (#601, Finding T-1).
- Isolated Headline Arena sync job into independent non-blocking CI workflow (#606).

### Fixed
- Eliminated silent fallback to national retail prices when evaluating regional metro forecasts (#608).
- Fixed uncommitted artifact drops by staging untracked files prior to dirty-tree porcelain status checks in GitHub Actions workflows (#606).
- Rotated and removed hardcoded NASA FIRMS API key, enforcing non-empty runtime environment variable injection (#605).
- Fixed high-severity headline truncation and properly URL-encoded Discord webhook flag URLs (#605).
- Corrected official KaTeX 0.16.8 Subresource Integrity (SRI) SHA384 hashes in public sources dashboard (#604).
- Sandboxed `intraday_event_monitor`, `reachability_adapters`, and `wayback_archiver` file writes during test runs in `tests/conftest.py`, eliminating test session fixture checksum pollution (#613).
- Fixed Pirate Weather API query routing for historical timestamps (>2h ago) to use `timemachine.pirateweather.net` instead of standard forecast endpoint, preventing HTTP 400 errors during retrospective backtests (#442).

## [0.8.0] - 2026-09-29

### Added
- Direct edge & cloud database architecture (`src/db/client.py`) connecting to Turso libSQL REST pipeline v2 and Cloudflare D1 with relational schema (`src/db/schema.sql`) (#559, #423).
- Closed-loop Hindsight episodic memory precedent injection and causal anomaly post-mortem reflection (`src/hindsight_context.py`) (#559, #557, #576, #586).
- Full-sample prospective refit cloning evaluated pipeline architecture (`fit_prospective_model`) (#559, #575).
- Bitemporal Vintage Store (`src/vintage_store.py`) with lazy loading and zero-lookahead point-in-time querying (#559, #583).
- Roll-adjusted continuous RBOB futures returns eliminating seasonal contract roll distortion (#444).
- Adaptive Conformal Inference (Gibbs & Candès) and calibrated predictive quantiles (#449).
- Unified statistical evaluation harness with Model Confidence Set and Benjamini-Hochberg FDR gate (#452).
- Semantic news deduplication with 48h Jaccard-Dice clustering and Jordà local projections (#446).
- Cross-platform advisory file locking with POSIX `fcntl` and Windows `msvcrt` (#424, #434, #582).
- Dynamic savings advisor embedding live 5-day model trajectories (`docs/savings.html`) (#559).
- Link-level HMAC-SHA256 signed flag URLs with single-use replay protection and timestamp freshness checks (#574, #581).

### Changed
- Decoupled cloud database synchronization to batch execution in `run_all.py`, reducing CI runtime by >95% (#498).
- Re-keyed prediction history ledger with deterministic SHA-256 primary keys and restored 248 historical live prospective forecasts (#578, #585).
- Upgraded CI workflows with commit-first rebase order, dirty-tree guards, and `MODEL_LEARNING.md` staging (#573, #584).

### Fixed
- Fixed falsy boolean/float value loss in `directional_hit` classification (#582).
- Enforced constant-time `hmac.compare_digest` with UTF-8 byte encoding across API server (#580, #582).
- Prevented invalid foreign key insertions in `intraday_revisions` when parent forecast is absent (#587).
- Fixed SQLite database corruption auto-recovery in Knowledge Graph (#424).

## [0.7.0] - 2026-09-24

### Added
- Standardized `requirements.lock` compiled via `pip-compile` for reproducible builds (#429).
- Automated pull request CI workflow across Python 3.11, 3.12, and 3.13 (#439).
- Append-only prediction history ledger with UUIDv4 `forecast_id` and UTC timestamps (#434).
- Cross-platform advisory file locking (`flock`/`msvcrt`) and atomic JSON writes (#434).
- Point-in-time historical feature vintage joins with zero lookahead leakage (#432).
- Unified regional execution runner (`src/locations/runner.py`) consolidating regional pipelines (#433).
- Authentic historical market data evaluation for 5-tier model hierarchy with $p < 0.05$ promotion gate (#435).
- Discrete horizon-aware API forecast dispatch with split conformal prediction intervals (#436).
- Dynamic scoreboard accuracy metrics and synthetic demonstration disclosures (#440).
- Standard community files, `.env.example`, `SECURITY.md`, and clean root shims (#441).

### Changed
- Parameterized shell runner scripts and systemd user unit definitions (#430).
- Re-architected statistical promotion gate threshold to $p < 0.05$ (#435).
- Made dashboard accuracy statistics dynamically calculated from prediction ledger (#440).

### Fixed
- Fixed DataFrame truthiness ambiguity in regional pipeline execution (#433).
- Eliminated synthetic forward curve multipliers on NYMEX calendar spreads (#432).
- Resolved API horizon query parameter ignoring requested forecast horizon (#436).
