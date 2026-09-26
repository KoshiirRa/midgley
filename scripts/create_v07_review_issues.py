"""
Ingest review feedback from ChatGPT-6 Astra and Claude Opus 6 into comprehensive GitHub Issues for milestone v0.7.
"""

import json
import os
import subprocess
import sys
import time
import urllib.error
import urllib.request

ISSUES = [
    {
        "id": "SEC-01",
        "title": "fix(security): Rotate committed Supabase password, enforce RLS on Hindsight tables, and scrub credentials from repo & docs",
        "category": "Perimeter & Infrastructure Security",
        "milestone": "v0.7",
        "labels": ["security", "bug", "infrastructure"],
        "effort": "M (Medium)",
        "effort_days": "1-2 days",
        "risk": "High Risk",
        "risk_color": "Red",
        "review_refs": ["CR-1", "D-3", "S-10"],
        "body": """### Summary
Static review identified sensitive secrets committed to the repository and insecure secret handling in deployment scripts:
1. **Committed Supabase Database Credential**: `scripts/deploy_hindsight_cloudrun.sh:23` sets a default connection string for `SUPABASE_DATABASE_URL` containing a plaintext Supabase database password. The script also passes the URL via `--set-env-vars` (line 66), making it visible to Cloud Run viewers.
2. **Missing Row-Level Security (RLS)**: `scripts/init_supabase_hindsight.sql` creates tables without RLS, leaving Hindsight episodic memory accessible if Supabase Data API is enabled with the anon key.
3. **Sensitive Default Values in Documentation**: `SELF_HOSTING.md` contains concrete AirNow API keys, Healthchecks ping UUIDs, and private network addresses in configuration templates.

### Proposed Remediation
1. **Rotate Secrets**: Immediately rotate the Supabase database password in the Supabase management console.
2. **Cloud Run Secret Manager**: Update `scripts/deploy_hindsight_cloudrun.sh` to remove hardcoded default credentials and use Google Cloud Secret Manager (`--set-secrets`) instead of `--set-env-vars`.
3. **Enable RLS**: Add `ALTER TABLE ... ENABLE ROW LEVEL SECURITY;` statements to `scripts/init_supabase_hindsight.sql`.
4. **Scrub Docs Templates**: Replace all concrete keys, URLs, and UUIDs in `SELF_HOSTING.md` and `scripts/update_wiki_audit.py` with generic placeholders (e.g. `your-airnow-api-key-here`, `00000000-0000-0000-0000-000000000000`).
5. **Enable GitHub Push Protection**: Ensure GitHub secret scanning and push protection are enabled on the repository.

### Acceptance Criteria
- [ ] Supabase credentials rotated and removed from all script defaults.
- [ ] `deploy_hindsight_cloudrun.sh` requires `SUPABASE_DATABASE_URL` from environment or Secret Manager.
- [ ] RLS policies defined and enabled on all Hindsight tables.
- [ ] Documentation templates scrubbed of real keys/UUIDs."""
    },
    {
        "id": "DATA-01",
        "title": "fix(data-integrity): Stop recording future & fallback prices as observed actuals and prevent test pollution in prediction ledger",
        "category": "Data Integrity & Evaluation Scaffolding",
        "milestone": "v0.7",
        "labels": ["bug", "data-ingestion", "modeling"],
        "effort": "L (High)",
        "effort_days": "3-5 days",
        "risk": "High Risk",
        "risk_color": "Red",
        "review_refs": ["CR-2", "C01", "P-2", "P-6", "H-3"],
        "body": """### Summary
The ground truth evaluation in `data/prediction_history.csv` is compromised by premature backfilling, fallback contamination, and test artifact pollution:
1. **Unmatured Future Actuals**: `backfill_actual_prices_and_evaluate()` selects all rows where actuals are missing without checking `target_date <= today`. 192 rows with future target dates (up to 2026-10-01) already carry 'actual' prices.
2. **Fallback Price Stamping**: `eia_retail_feed.py` falls back to hardcoded `FALLBACK_RETAIL_PRICES` constants or test-mode mock formulas (`fallback ± k*0.02`), which get stamped with EIA provenance and stored as observed ground truth.
3. **Wholesale vs Retail Mismatch**: National wholesale RBOB futures (`RB=F`) targets fall back to retail `GASREGW` when RBOB actuals are missing.
4. **Test Pollution in Production Ledger**: `tests/test_multi_horizon_forecasting.py` and regional test modules call production backfill functions that write `Test_Region` rows (200 rows in ledger) and test fixture prices directly into `data/prediction_history.csv`.
5. **Target Date Holiday Misalignment**: `pd.bdate_range` target dates land on exchange holidays when no NYMEX RBOB settlement occurs.

### Proposed Remediation
1. **Enforce Target Date Maturity**: Ensure backfill only processes rows where `target_date <= today`. Leave unmatured rows strictly `null`.
2. **Strict Provenance & No Synthetic Fallbacks**: Never stamp fallback constants or mock data as observed EIA actuals. If no real observation exists, keep `actual_price` as `null`.
3. **Segregate Wholesale vs Retail Ground Truth**: Never substitute retail series for wholesale RBOB futures targets. Maintain distinct evaluation cohorts.
4. **Create `tests/conftest.py`**: Intercept all test filesystem writes and redirect `data/`, `docs/`, and `reports/` paths to `tmp_path`. Refuse `Test_*` regions from writing to production ledger files.
5. **Ledger Cleansing & Rebuild**: Audit and purge contaminated future rows, test-region rows, and synthetic fallback actuals from `data/prediction_history.csv`.
6. **Exchange Calendar**: Use NYMEX trading calendar for business day horizon offsets.

### Acceptance Criteria
- [ ] No row with `target_date > today` receives an actual price in the ledger.
- [ ] Test runs do not mutate files in `data/`, `docs/`, or `reports/`.
- [ ] `Test_Region` entries completely removed from `data/prediction_history.csv`.
- [ ] Wholesale and retail actuals kept strictly separate."""
    },
    {
        "id": "MOD-01",
        "title": "fix(modeling): Scope regional intraday shocks, cap cumulative event scores, and enforce hybrid-vs-quant plausibility gating",
        "category": "Quantitative Modeling & Forecast Scaffolding",
        "milestone": "v0.7",
        "labels": ["bug", "modeling", "dashboard"],
        "effort": "M (Medium)",
        "effort_days": "2-3 days",
        "risk": "High Risk",
        "risk_color": "Red",
        "review_refs": ["CR-3", "P-3", "P-8"],
        "body": """### Summary
A runaway forecast occurred in the public README (Tulsa jumped from $3.99 to $6.39 in 5 days, +60%) due to un-scoped national intraday shocks and lack of forecast plausibility gating:
1. **Intraday Shock Broadcasting**: `load_live_regional_intraday_events` treats `National` events as matching *every* regional metro (`src/data_ingestion.py:230-231`). Multiple events on the same day sum and saturate `event_*` features at levels never encountered during training.
2. **Missing Output Gating**: Forecasts are only bounded by a broad ±60% return clip in `src/models.py`. Seasonal plausibility gating only runs on scenario simulations in API server, not live daily forecast issuance.
3. **Unvalidated README Updates**: `src/readme_updater.py` selects the last row (`iloc[-1]`) without filtering for horizon, run type, or plausibility.

### Proposed Remediation
1. **Locale-Specific Event Scoping**: Require explicit regional target tagging for intraday shocks; do not broadcast all national shocks indiscriminately to regional models.
2. **Cumulative Event Score Saturation Cap**: Cap total daily cumulative event shock magnitudes before feature vector construction.
3. **Forecast Plausibility & Divergence Gate**: Implement an automated post-inference gate that compares the hybrid LLM forecast against the physical quantitative baseline. If divergence exceeds volatility-scaled thresholds, flag for human review and clamp to physical bounds.
4. **Validated Single-Source Latest Record**: Unify `README.md`, `docs/runs/latest.json`, and API static exports to read from a single validated, gated forecast record (live, h=5, <36h old).

### Acceptance Criteria
- [ ] Intraday shocks correctly isolated to target geographic locales.
- [ ] Automated plausibility gate prevents unrealistic multi-day retail price spikes.
- [ ] `README.md` and dashboard agree on latest validated regional predictions."""
    },
    {
        "id": "PKG-01",
        "title": "fix(packaging): Resolve runtime py-gasbuddy dependency, lock packaging requirements, and align Python compatibility",
        "category": "Packaging & Deployment Infrastructure",
        "milestone": "v0.7",
        "labels": ["infrastructure", "bug"],
        "effort": "S (Low)",
        "effort_days": "1 day",
        "risk": "Medium Risk",
        "risk_color": "Yellow",
        "review_refs": ["C02", "C-8", "C-9"],
        "body": """### Summary
Dependency resolution and packaging manifests have critical inconsistencies:
1. **Unresolvable Dependency**: `requirements.txt:15` and `pyproject.toml:29` require `py-gasbuddy>=0.7.1`, but PyPI distributions end at version 0.4.2. Clean environment installs fail with `No matching distribution found`.
2. **Manifest Divergence**: `requirements.txt` specifies higher version floors than `pyproject.toml` and promotes optional extras (e.g. feast, pyarrow, wandb) to hard dependencies.
3. **Missing Lockfile**: No lockfile (`uv.lock` or `requirements.lock`) is maintained, resulting in non-reproducible CI and Docker builds.
4. **Python Version Compatibility**: README badge states Python 3.10–3.13 support, but test modules import `tomllib` (Python 3.11+) and CI runs only Python 3.13.

### Proposed Remediation
1. **Fix `py-gasbuddy` Version**: Pin `py-gasbuddy` to verified available version (`>=0.4.2`) or configure vendored distribution.
2. **Harmonize Manifests**: Sync `pyproject.toml` and `requirements.txt` dependencies and dependency groups.
3. **Generate Lockfile**: Add `uv lock` or `pip-compile` lockfile for deterministic CI/CD and container builds.
4. **Align Python Version**: Update `requires-python` in `pyproject.toml` to `>=3.11` and update README compatibility badges accordingly.

### Acceptance Criteria
- [ ] `pip install -r requirements.txt` succeeds in a clean Python 3.11+ virtual environment.
- [ ] `pyproject.toml` and `requirements.txt` dependencies are strictly aligned.
- [ ] Python compatibility claims match CI and runtime requirements."""
    },
    {
        "id": "OPS-01",
        "title": "fix(operations): Enforce LF line endings on Linux shell runners and replace machine-specific systemd paths",
        "category": "DevOps & Local Execution Environments",
        "milestone": "v0.7",
        "labels": ["infrastructure", "bug"],
        "effort": "S (Low)",
        "effort_days": "1 day",
        "risk": "Low Risk",
        "risk_color": "Green",
        "review_refs": ["C03", "C-14", "D05"],
        "body": """### Summary
Scheduled Linux bash scripts and systemd deployment templates contain cross-platform compatibility defects:
1. **CRLF Line Endings**: `scripts/run_local_daily_forecast.sh`, `run_local_intraday_polling.sh`, and `run_local_weekly_review.sh` have CRLF line endings committed in git, causing `set: pipefail\\r: invalid option name` syntax errors when executed with `/bin/bash` on Linux.
2. **Hardcoded User Paths**: Systemd service files in `systemd/` and `midgley-api.service` hardcode user paths (`/home/marty/projects/midgley`) and virtual environments.
3. **Stale Wrangler Configurations**: `workers/wrangler.cache.toml` contains placeholder IDs and invalid main file paths.

### Proposed Remediation
1. **Normalize Line Endings**: Convert all `.sh` scripts to LF (`\\n`) and enforce in `.gitattributes` (`*.sh text eol=lf`).
2. **Parameterized Systemd Units**: Update systemd templates to use `%h` and `EnvironmentFile` configurations.
3. **Clean Wrangler Configs**: Align `wrangler.toml` and remove obsolete cache wrangler files.

### Acceptance Criteria
- [ ] All `.sh` scripts execute cleanly under `bash` on Linux without CRLF errors.
- [ ] `.gitattributes` enforces LF for shell scripts across Git checkouts.
- [ ] Systemd templates work across standard Linux user environments."""
    },
    {
        "id": "SEC-02",
        "title": "fix(security): Authenticate HTTP MCP transport, bind sessions to API keys, and enforce rate limits",
        "category": "API & MCP Architecture",
        "milestone": "v0.7",
        "labels": ["security", "api", "bug"],
        "effort": "M (Medium)",
        "effort_days": "1-2 days",
        "risk": "High Risk",
        "risk_color": "Red",
        "review_refs": ["C04", "S-1"],
        "body": """### Summary
The HTTP Model Context Protocol (MCP) transport in `src/api_server.py` and `src/mcp_server.py` bypasses authentication and rate limiting:
1. **Unauthenticated Endpoints**: `GET /mcp/sse` and `POST /mcp/messages` have no API key dependency or rate limit enforcement.
2. **Unrestricted Model Execution**: Unauthenticated callers can invoke MCP tools that trigger LLM cohort simulations with caller-supplied headlines (`simulate_market_cohort(use_llm=True)`), consuming Gemini API credits without authorization.
3. **Documentation Mismatch**: AGENTS.md states MCP is protected by PBKDF2 API keys and 30 RPM rate limiting, but the route definitions contain no auth dependencies.

### Proposed Remediation
1. **Add Key Authentication**: Add `get_api_key_user` dependency or header/query key verification to `/mcp/sse` and `/mcp/messages`.
2. **Session Binding**: Bind MCP SSE session IDs to the authenticated user identity/tier.
3. **Rate Limiting**: Apply tier-specific rate limits to MCP tool dispatches.
4. **Local Stdio Trust Model**: Maintain unauthenticated access for local stdio subprocess mode while strictly securing HTTP SSE/POST transports.

### Acceptance Criteria
- [ ] `GET /mcp/sse` and `POST /mcp/messages` return 401 Unauthorized when credentials are missing.
- [ ] MCP tool invocations respect caller tier and rate limit policies.
- [ ] Integration tests verify MCP authentication and rate limiting."""
    },
    {
        "id": "DATA-02",
        "title": "feat(data-ingestion): Replace synthetic feature formulas with point-in-time historical vintages and refresh matured RBOB actuals",
        "category": "Feature Engineering & Data Ingestion",
        "milestone": "v0.7",
        "labels": ["data-ingestion", "modeling", "enhancement"],
        "effort": "L (High)",
        "effort_days": "3-5 days",
        "risk": "Medium Risk",
        "risk_color": "Yellow",
        "review_refs": ["C05", "P-1", "C11"],
        "body": """### Summary
Historical training feature matrices in `src/feature_engineering.py` rely on fabricated mathematical formulas rather than authentic observed data:
1. **Synthetic Feature History**: Historical COT positioning is generated with sinusoidal formulas (`80000 + 16000*sin(...)`), while FERC tariffs, USGS, AQI, CEC, and weather histories use day-of-year formulas. Real values are only written to the final row (`df.index[-1]`).
2. **Derivation of M2 Forward Spreads**: NYMEX forward curve connector derives M2 prices using fixed ratios (`M1 * 0.992`), making backwardation/contango flags synthetic.
3. **Unused Cutoff Parameter**: `as_of_cutoff` has zero runtime references inside `create_feature_matrix()`, risking lookahead bias.
4. **Stale RBOB Actuals Cache**: In `prediction_logger.py`, RBOB actuals download is guarded by `if not actuals_map`, meaning once populated, newer matured dates are never fetched even with `force_eval=True`.

### Proposed Remediation
1. **Join Point-in-Time Vintages**: Ingest real historical releases from existing vintage files (`data/*_vintages.json`) keyed by publication timestamp.
2. **Enforce `as_of_cutoff`**: Filter all feature datasets by cutoff timestamp in `create_feature_matrix()`.
3. **Real Contract Forward Curves**: Connect observed prompt vs second-month NYMEX contracts or explicitly flag missing forward data.
4. **Incremental Actuals Refresh**: Refresh RBOB actuals cache when unevaluated matured target dates exist.

### Acceptance Criteria
- [ ] `create_feature_matrix()` joins real vintage histories without sinusoidal formulas.
- [ ] `as_of_cutoff` strictly filters out data published after the cutoff date.
- [ ] RBOB cache fetches newly matured trading dates automatically."""
    },
    {
        "id": "MOD-02",
        "title": "feat(modeling): Pass region parameter through multi-horizon training interface and consolidate regional pipelines",
        "category": "Quantitative Modeling & Regional Architecture",
        "milestone": "v0.7",
        "labels": ["modeling", "enhancement"],
        "effort": "L (High)",
        "effort_days": "3-5 days",
        "risk": "Medium Risk",
        "risk_color": "Yellow",
        "review_refs": ["C06", "D04", "P-5", "P-9"],
        "body": """### Summary
Multi-horizon model training and regional pipelines suffer from parameter omission and extensive code duplication:
1. **Omitted Region Parameter**: `train_multi_horizon_models()` in `src/models.py` has no `region` parameter and calls `create_feature_matrix()` without one, defaulting all regional metros (and National) to `Tulsa_OK` weather/spot routing.
2. **Hardcoded RVP Region**: `create_feature_matrix()` hardcodes `region="National"` for RVP regulatory calculations.
3. **Regional Pipeline Duplication**: ~3,700 lines of boilerplate are duplicated across `src/locations/*/main.py` and `regional.py` (74-98% identical).
4. **Stale Regional Registry Docs**: `SELF_HOSTING.md` instructs editing non-existent `LOCALE_PRICE_KEYS` / `LOCALE_RUNNERS` instead of `LOCALE_MAP` / `PADD_METADATA`.

### Proposed Remediation
1. **Explicit Region Forwarding**: Add `region: str` parameter to `train_multi_horizon_models()` and forward it to `create_feature_matrix()` and RVP engines.
2. **Unified Config-Driven Regional Pipeline**: Refactor regional entry points into a single parameterized runner driven by `data/regional_metadata/*.json`.
3. **Update Documentation**: Correct regional expansion tutorial in `SELF_HOSTING.md` to reference the true registries.

### Acceptance Criteria
- [ ] Regional models train on their specific climatology, RVP regulations, and spot differentials.
- [ ] Metro packages consolidated into a clean, parameterized architecture.
- [ ] Regional registration documentation matches codebase implementation."""
    },
    {
        "id": "STOR-01",
        "title": "fix(storage): Enforce prediction ledger immutability and complete atomic write & advisory lock coverage across API processes",
        "category": "Storage IO & Concurrency Control",
        "milestone": "v0.7",
        "labels": ["infrastructure", "bug"],
        "effort": "M (Medium)",
        "effort_days": "2-3 days",
        "risk": "Medium Risk",
        "risk_color": "Yellow",
        "review_refs": ["C07", "C13", "S-11"],
        "body": """### Summary
Prediction persistence and file I/O lack complete immutability and atomic concurrency guarantees:
1. **Forecast Overwriting on Rerun**: `prediction_logger.py` deduplication retains only the last row (`keep="last"`) when deduplicating on target/horizon/region/model. Running a new forecast overwrites prior issued predictions.
2. **Incomplete Atomic Write Usage**: Several active state and vintage writers (`eia_retail_feed.py`, `ipasis_security.py`, `telemetry.py`, `tokentab_accounting.py`) write files directly without using `storage_io.atomic_write_json`.
3. **In-Process Lock Bypasses**: While shell scripts use `flock`, API background tasks, webhooks, and queue consumers write state files concurrently without cross-process coordination.

### Proposed Remediation
1. **Immutable Forecast Issuance**: Assign unique immutable UUIDs (`forecast_id`) and record issuance timestamps. Store revisions as distinct ledger entries rather than overwriting historical forecasts.
2. **Universal Atomic Writes**: Adopt `storage_io.atomic_write_json` and `storage_io.atomic_write_csv` across all JSON/CSV state writers.
3. **Application-Level Lock Coordination**: Use file locking (`fcntl` / `flock` wrapper) across API and CLI write paths to prevent lost updates.

### Acceptance Criteria
- [ ] Prior issued forecasts are never overwritten by subsequent runs with identical keys.
- [ ] All state and vintage persistence modules use atomic write helpers.
- [ ] Concurrent writes cannot produce corrupted or partially-written JSON/CSV files."""
    },
    {
        "id": "EVAL-01",
        "title": "feat(evaluation): Re-architect 5-tier model hierarchy promotion audit with walking origins and authentic historical data",
        "category": "Model Evaluation & Statistical Audits",
        "milestone": "v0.7",
        "labels": ["modeling", "enhancement"],
        "effort": "L (High)",
        "effort_days": "3-5 days",
        "risk": "Medium Risk",
        "risk_color": "Yellow",
        "review_refs": ["C08", "M-3"],
        "body": """### Summary
The 5-tier model hierarchy evaluation harness (`scripts/evaluate_model_hierarchy.py` and `reports/model_hierarchy_evaluation.md`) operates on synthetic data:
1. **Fabricated Evaluation Features**: `generate_benchmark_feature_matrix` invents synthetic features and defines target prices as linear combinations of those same-row features + small noise.
2. **Horizon Target Reuse**: The same target vector is reused across all horizons, changing only the statistical test rather than evaluating true multi-step ahead forecasts.
3. **Test Module Overwrites Report**: `tests/test_model_hierarchy.py` regenerates and overwrites `reports/model_hierarchy_evaluation.md` during test execution.
4. **Significance Threshold Discrepancy**: The evaluation code gates on $p < 0.10$, whereas documentation and release notes claim $p < 0.05$.

### Proposed Remediation
1. **Real Feature Matrix & Targets**: Execute promotion audits against actual historical feature matrices produced by `create_feature_matrix()` with genuine $h$-step future targets.
2. **Purged Walk-Forward Cross-Validation**: Evaluate tiers across rolling forecast origins using chronological train/test splits.
3. **True Model Architecture Testing**: Fit real Ridge, Stacking, and Hybrid estimators rather than a simplified benchmark Ridge model.
4. **Decouple Tests from Reports**: Ensure unit tests use temporary report paths and do not overwrite committed documentation.

### Acceptance Criteria
- [ ] Model hierarchy evaluation runs on genuine historical market data.
- [ ] Horizons evaluate distinct forward return targets.
- [ ] Promotion gates enforce $p < 0.05$ with multiple testing corrections."""
    },
    {
        "id": "API-01",
        "title": "fix(api): Align API horizon selection with business-day targets and wire conformal prediction intervals into issuance",
        "category": "API Services & Uncertainty Quantification",
        "milestone": "v0.7",
        "labels": ["api", "modeling", "bug"],
        "effort": "M (Medium)",
        "effort_days": "2-3 days",
        "risk": "Medium Risk",
        "risk_color": "Yellow",
        "review_refs": ["C09", "C12", "P-4"],
        "body": """### Summary
The prediction API and interval calibration engines exhibit semantic and operational misalignments:
1. **API Horizon Selection Bug**: `GET /api/v1/forecast/predict` accepts a `days` query parameter but returns the latest prediction row regardless of `days`. It shifts target date by calendar days instead of matching the stored horizon target.
2. **Unwired Conformal Prediction Intervals**: `compute_conformal_prediction_intervals()` in `src/models.py` has tests but is never invoked during live forecast issuance in `src/prediction_logger.py`.
3. **Horizon Pooling**: Live predictions calculate a single pooled residual standard deviation across all horizons and apply a constant 1.96-sigma symmetric interval.

### Proposed Remediation
1. **Horizon-Aware API Dispatch**: Filter stored predictions by matching horizon $h$ and return accurate target dates and freshness metadata.
2. **Wire Horizon-Calibrated Intervals**: Compute empirical nonconformity quantiles segmented strictly by forecast horizon ($h \in [1..5]$) using cleansed out-of-sample prediction residuals.
3. **Persist Calibration Metadata**: Store interval calculation method (conformal vs Gaussian fallback) and calibration sample size in the ledger.

### Acceptance Criteria
- [ ] `/api/v1/forecast/predict?days=N` returns the forecast specifically generated for horizon $N$.
- [ ] Prediction interval widths scale dynamically with discrete forecast horizon uncertainty.
- [ ] Conformal calibration is actively executed during forecast logging."""
    },
    {
        "id": "SEC-03",
        "title": "fix(security): Unify master and provisioned key auth, enforce API key tiers, and harden webhooks & debug probes",
        "category": "API Security & Middleware",
        "milestone": "v0.7",
        "labels": ["security", "api", "bug"],
        "effort": "M (Medium)",
        "effort_days": "2-3 days",
        "risk": "High Risk",
        "risk_color": "Red",
        "review_refs": ["C10", "S-5", "S-6", "S-7", "S-8", "S-9", "S-12"],
        "body": """### Summary
The API server has conflicting authorization layers, un-enforced caller tiers, and unbounded debug endpoints:
1. **Middleware Key Conflict**: When `MIDGLEY_API_KEY` is configured, global middleware accepts only that master key, causing valid provisioned keys, `?api_key=`, and signed webhooks to fail with 401.
2. **Ignored Key Tiers**: `request.state.key_info` is recorded but never checked. Basic tier keys can execute expensive LLM cohort simulations, graph ingestions, and Headline Arena submissions.
3. **Webhook Replay Vulnerability**: HMAC webhooks lack timestamp/nonce validation, allowing captured payloads to be replayed after the 24-hour deduplication window.
4. **Blocking Key Hasher**: Synchronous 100k-iteration PBKDF2 runs inside `async def` route dependencies, blocking the FastAPI asyncio event loop under concurrent load.
5. **Unbounded Debug Endpoints**: `/system/cache-status?probe=true` writes persistent keys without cleanup and exposes infrastructure paths.

### Proposed Remediation
1. **Unified Authentication Architecture**: Centralize credential verification so master keys, provisioned user keys, and admin secrets work harmoniously.
2. **Tier Enforcement**: Restrict LLM simulation, Headline Arena submission, and graph ingestion to authorized key tiers.
3. **Timestamped HMAC Webhooks**: Sign `timestamp.body` and enforce a ±5 minute timestamp freshness window.
4. **Non-Blocking Auth**: Offload PBKDF2 hashing to threadpool or use constant-time SHA-256 for high-entropy tokens.
5. **Secure Debug Probes**: Protect cache probe endpoints with admin authentication and bound public query parameters.

### Acceptance Criteria
- [ ] Master key and provisioned user keys function correctly across all secured endpoints.
- [ ] Sensitive operational endpoints reject unauthorized tier keys.
- [ ] HMAC webhooks reject replayed or expired requests.
- [ ] Key verification does not block the asyncio event loop."""
    },
    {
        "id": "SEC-04",
        "title": "fix(security): Authenticate Cloudflare Worker endpoints, escape dashboard HTML, and isolate dev/prod Worker deploys",
        "category": "Edge Workers & Presentation Security",
        "milestone": "v0.7",
        "labels": ["security", "infrastructure", "dashboard"],
        "effort": "M (Medium)",
        "effort_days": "2-3 days",
        "risk": "High Risk",
        "risk_color": "Red",
        "review_refs": ["S-2", "S-3", "S-4", "S-13", "C-4"],
        "body": """### Summary
Edge workers and the public dashboard generator contain security vulnerabilities:
1. **Unauthenticated Worker Actions**: Intraday Worker exposes `POST /flag` (which creates GitHub issues using maintainer tokens), `GET /flag` (reflected XSS in unescaped query params), and `/run` / `/trigger` without authentication.
2. **Cache Worker Fails Open**: Cache Worker only checks auth if `CLOUDFLARE_AUTH_TOKEN` is set, failing open when the secret is omitted.
3. **Stored XSS in Dashboard**: Intraday anomaly shock banner interpolates raw `trigger_title` into `docs/index.html` without HTML escaping.
4. **Dev Deploying Prod Worker**: `deploy_cloudflare_worker.yml` deploys pushes on `dev` directly to the production Cloudflare Worker.

### Proposed Remediation
1. **Secure Worker Actions**: Require signed tokens for `/flag` issue creation; HTML-escape query parameters in `/flag` UI; place `/run` and `/trigger` behind admin authentication.
2. **Fail-Closed Cache Worker**: Reject all non-health requests if `CLOUDFLARE_AUTH_TOKEN` is missing or invalid.
3. **Dashboard HTML Escaping**: Strictly escape all dynamic text strings in `src/dashboard_generator.py` and enforce Content Security Policy (CSP).
4. **Environment Separation**: Deploy `dev` branch to a staging/preview Cloudflare Worker environment.
5. **Worker Test Suite**: Add comprehensive Vitest tests in `tests/workers.test.ts` for router authorization and fail-closed behaviors.

### Acceptance Criteria
- [ ] Worker endpoints reject unauthenticated requests.
- [ ] Dashboard generator escapes all user/feed inputs.
- [ ] `dev` pushes deploy to staging Worker environment."""
    },
    {
        "id": "CI-01",
        "title": "ci: Add pytest pull request gate, eliminate force-push races across workflows, and single-source project versioning",
        "category": "CI/CD & Release Engineering",
        "milestone": "v0.7",
        "labels": ["infrastructure", "enhancement"],
        "effort": "M (Medium)",
        "effort_days": "2-3 days",
        "risk": "Medium Risk",
        "risk_color": "Yellow",
        "review_refs": ["C-1", "C-2", "C-3", "C-5", "C-10", "C-12", "C-13", "C14"],
        "body": """### Summary
CI/CD workflows lack pull request regression testing, suffer from concurrent git push races, and have fragmented versioning:
1. **No Pytest Gate in CI**: No GitHub Actions workflow runs `pytest`, and no workflows trigger on `pull_request`.
2. **Force-Push Races**: Daily, weekly, and intraday scheduled workflows push changes to `data/` and `docs/` with `push_options: '--force'` under differing concurrency groups, risking silent data loss.
3. **Headline Arena Branch Logic**: `headline_arena_sync.yml` pulls and pushes across `dev` and `main` branches with fallback logic that can create improper merge commits.
4. **Fragmented Versioning**: Five different version strings exist across `pyproject.toml` (0.6.8), `RELEASE_MANIFEST.json` (0.6.5), draft notes (0.7.0), and `version.py` spawns git subprocesses on every call.

### Proposed Remediation
1. **Add PR CI Workflow**: Create a required GitHub Actions workflow triggered on `pull_request` and `push` running `ruff check .` and `pytest` across Python 3.11 and 3.12.
2. **Single Concurrency Group for Data Writers**: Place all workflows that write data into a shared concurrency group, remove `--force`, and use `git pull --rebase` with retry.
3. **Fix Sync Branch Logic**: Explicitly check out and push to targeted repository refs.
4. **Single-Source Version**: Make `pyproject.toml` the sole source of truth for versioning and cache version resolution in `version.py`.

### Acceptance Criteria
- [ ] Pull requests trigger automated `pytest` and `ruff` test suites.
- [ ] Scheduled workflows serialize data updates without force pushes.
- [ ] Version resolution is unified and cached."""
    },
    {
        "id": "DASH-01",
        "title": "fix(dashboard): Replace hardcoded accuracy constants with dynamic ledger metrics and label synthetic demonstrations",
        "category": "Reporting & Public Presentation",
        "milestone": "v0.7",
        "labels": ["dashboard", "documentation", "modeling"],
        "effort": "M (Medium)",
        "effort_days": "2-3 days",
        "risk": "Medium Risk",
        "risk_color": "Yellow",
        "review_refs": ["M-1", "M-2", "M-4", "M-5", "D01", "D-11"],
        "body": """### Summary
Public presentation surfaces display hardcoded accuracy figures and unlabelled synthetic demonstrations:
1. **Hardcoded Accuracy Literals**: `directional_hit_rate_historical: 0.6079` and `historical_mae_dollars: 0.1069` are hardcoded across `src/api_server.py:626`, `src/dashboard_generator.py`, `social_embed_generator.py`, `weekly_issue_reporter.py`, and `README.md`.
2. **Ledger Contradictions**: Recomputed ledger metrics contradict published figures (National MAE is $0.149 vs published $0.1069; directional hit rate is 51.1% vs published 60.79%).
3. **Synthetic Demos Presented as Live**: QuantStats performance tear sheet is generated with `np.random.normal` without disclosure; `/api/v1/forecast/purged-cv` fits on random data.
4. **Unsourced Statistical Claims**: README cites statistically significant (p < 0.01) social media multipliers that originate from fixed code constants without backing notebooks.

### Proposed Remediation
1. **Dynamic Metric Computation**: Compute published MAE, directional accuracy, and interval coverage dynamically from the cleansed prediction ledger with explicit evaluation windows and sample sizes ($N$).
2. **Label Synthetic & Demo Endpoints**: Prominently label illustrative / mock endpoints (e.g. QuantStats tear sheet, purged CV demo) as synthetic demonstrations.
3. **Qualify Parametric Assumptions**: Clearly document heuristic or model assumptions (e.g. weekend gap multipliers) as parametric hypotheses rather than empirical findings unless accompanied by reproducible notebooks.

### Acceptance Criteria
- [ ] All published MAE and hit rate figures are dynamically derived from actual ledger evaluations.
- [ ] Demo endpoints and tear sheets clearly indicate synthetic or illustrative status.
- [ ] API responses return region-specific empirical accuracy metrics."""
    },
    {
        "id": "DOCS-01",
        "title": "docs: Fix relative link drift across mirrors, streamline AGENTS.md, align API/ops docs, and clean root directory",
        "category": "Documentation & Repository Hygiene",
        "milestone": "v0.7",
        "labels": ["documentation", "infrastructure"],
        "effort": "M (Medium)",
        "effort_days": "2-3 days",
        "risk": "Low Risk",
        "risk_color": "Green",
        "review_refs": ["D02", "D03", "D-1", "D-2", "D-5", "D-6", "D-7", "D-8", "D-9", "D-10", "D-12", "D-13", "D-14", "D-15", "D-16", "D-17", "D-18", "H-1", "H-2", "H-4", "H-7"],
        "body": """### Summary
Documentation files suffer from relative link breakage in mirrors, stale system prompts, and root directory clutter:
1. **Broken Relative Links in Mirrors**: Mirroring root docs to `docs/` breaks relative paths (e.g. `src/models.py` resolves to `docs/src/models.py`). 25 broken links exist in `docs/README.md`.
2. **Oversized `AGENTS.md`**: `AGENTS.md` (167 KB, 895 lines) contains extensive historical changelogs rather than concise system prompts, leading to contradictory directives for AI coding agents.
3. **Undocumented & Dead Environment Variables**: 35 active environment variables are undocumented, while several documented variables (e.g. `EIA_API_KEY`, `MIDGLEY_ENABLED_REGIONS`) are never read by code.
4. **Repository Hygiene**: Stale root `dashboard_generator.py` (6,022 lines) differs from `src/dashboard_generator.py`; root `api_server.py` fails on import; unreferenced roadmap JSON dumps clutter root.
5. **Missing Standard Files**: Project lacks `SECURITY.md`, `CONTRIBUTING.md`, `CHANGELOG.md`, and `.env.example`.

### Proposed Remediation
1. **Canonical Links**: Generate site documentation links canonically or use GitHub repository URLs for source code references.
2. **Streamline `AGENTS.md`**: Refactor `AGENTS.md` into a lean (<300 line) system prompt focusing strictly on architectural rules, testing requirements, and invariants.
3. **Sync Environment Variables**: Create a comprehensive `.env.example` documenting all active environment variables and remove dead configuration variables.
4. **Clean Root Directory**: Delete stale root `dashboard_generator.py`, fix root `api_server.py` import shim, and archive one-off triage scripts.
5. **Add Standard Community Files**: Add `SECURITY.md`, `CONTRIBUTING.md`, and `CHANGELOG.md`.

### Acceptance Criteria
- [ ] No broken relative links in published docs pages.
- [ ] `AGENTS.md` is concise, accurate, and under 300 lines.
- [ ] `.env.example` documents all active environment variables.
- [ ] Root directory cleaned of obsolete files and broken import shims."""
    }
]


def get_github_token():
    """Retrieve GitHub token safely from git credential helper without CLI exposure."""
    for var in ["GH_TOKEN", "GITHUB_TOKEN"]:
        t = os.environ.get(var)
        if t:
            return t.strip()

    try:
        p = subprocess.Popen(
            ["git", "credential", "fill"],
            stdin=subprocess.PIPE,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True
        )
        stdout, _ = p.communicate("protocol=https\nhost=github.com\n")
        for line in stdout.splitlines():
            if line.startswith("password="):
                return line.split("=", 1)[1].strip()
    except Exception as e:
        print(f"Error querying git credential helper: {e}", file=sys.stderr)

    return None


def get_repo_milestone_number(token: str, milestone_title: str) -> int | None:
    """Find milestone number by title in KoshiirRa/midgley."""
    url = "https://api.github.com/repos/KoshiirRa/midgley/milestones?state=all"
    req = urllib.request.Request(
        url,
        headers={
            "Authorization": f"Bearer {token}",
            "Accept": "application/vnd.github.v3+json",
            "User-Agent": "midgley-agent"
        }
    )
    try:
        with urllib.request.urlopen(req) as resp:
            data = json.loads(resp.read().decode())
            for m in data:
                if m.get("title", "").strip().lower() == milestone_title.strip().lower():
                    return m.get("number")
    except Exception as e:
        print(f"Could not query milestones: {e}", file=sys.stderr)
    return None


def create_github_issue(token: str, issue_dict: dict, milestone_num: int | None) -> dict:
    """Create a single issue via GitHub REST API."""
    url = "https://api.github.com/repos/KoshiirRa/midgley/issues"
    payload = {
        "title": issue_dict["title"],
        "body": issue_dict["body"],
        "labels": issue_dict["labels"]
    }
    if milestone_num is not None:
        payload["milestone"] = milestone_num

    data_bytes = json.dumps(payload).encode("utf-8")
    req = urllib.request.Request(
        url,
        data=data_bytes,
        headers={
            "Authorization": f"Bearer {token}",
            "Accept": "application/vnd.github.v3+json",
            "Content-Type": "application/json",
            "User-Agent": "midgley-agent"
        }
    )
    try:
        with urllib.request.urlopen(req) as resp:
            return json.loads(resp.read().decode())
    except urllib.error.HTTPError as e:
        err_body = e.read().decode()
        return {"error": e.code, "message": err_body}
    except Exception as e:
        return {"error": str(e)}


def update_local_roadmap_json():
    """Update master_roadmap_summary.json and evaluated_master_roadmap.json."""
    summary_path = "master_roadmap_summary.json"
    evaluated_path = "evaluated_master_roadmap.json"

    if os.path.exists(summary_path):
        with open(summary_path, "r", encoding="utf-8") as f:
            summary_data = json.load(f)
    else:
        summary_data = []

    if os.path.exists(evaluated_path):
        with open(evaluated_path, "r", encoding="utf-8") as f:
            evaluated_data = json.load(f)
    else:
        evaluated_data = []

    existing_titles = {item.get("title") for item in summary_data}

    start_num = 450
    for idx, iss in enumerate(ISSUES):
        if iss["title"] in existing_titles:
            continue

        item_num = start_num + idx
        summary_entry = {
            "number": item_num,
            "title": iss["title"],
            "status": "Ready",
            "milestone": iss["milestone"],
            "labels": iss["labels"],
            "body_preview": iss["body"][:250] + "..."
        }
        summary_data.append(summary_entry)

        eval_entry = {
            "number": item_num,
            "title": iss["title"],
            "category": iss["category"],
            "status": "Ready",
            "milestone": iss["milestone"],
            "labels": iss["labels"],
            "effort": iss["effort"],
            "effort_days": iss["effort_days"],
            "risk": iss["risk"],
            "risk_color": iss["risk_color"],
            "body_snippet": iss["body"][:250] + "..."
        }
        evaluated_data.append(eval_entry)

    with open(summary_path, "w", encoding="utf-8") as f:
        json.dump(summary_data, f, indent=2)

    with open(evaluated_path, "w", encoding="utf-8") as f:
        json.dump(evaluated_data, f, indent=2)

    print(f"Updated {summary_path} and {evaluated_path} with {len(ISSUES)} review issues.")


def main():
    print(f"Ingesting {len(ISSUES)} review issues into v0.7 milestone...")
    update_local_roadmap_json()

    token = get_github_token()
    if not token:
        print("GitHub token not found. Only local roadmap JSON updated.")
        return

    milestone_num = get_repo_milestone_number(token, "v0.7")
    print(f"Target milestone 'v0.7' resolved to GitHub milestone number: {milestone_num}")

    created_issues = []
    for iss in ISSUES:
        print(f"Creating: {iss['title']}...")
        res = create_github_issue(token, iss, milestone_num)
        if "number" in res:
            print(f"  -> Created issue #{res['number']}: {res['html_url']}")
            created_issues.append({"id": iss["id"], "number": res["number"], "url": res["html_url"], "title": iss["title"]})
        else:
            print(f"  -> Failed: {res}")
        time.sleep(0.5)

    print(f"\nDone! Created {len(created_issues)} of {len(ISSUES)} issues on GitHub.")


if __name__ == "__main__":
    main()
