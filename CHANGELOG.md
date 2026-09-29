# Changelog

All notable changes to this project will be documented in this file.
The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.0.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

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
