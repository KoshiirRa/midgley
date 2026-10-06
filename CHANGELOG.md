# Changelog

All notable changes to this project will be documented in this file.
The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.0.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

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
