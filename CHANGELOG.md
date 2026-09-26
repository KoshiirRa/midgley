# Changelog

All notable changes to this project will be documented in this file.
The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.0.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

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
