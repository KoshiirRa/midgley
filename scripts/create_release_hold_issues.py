"""
Script to create GitHub issues for all Release-Readiness Review findings.
Usage: python scripts/create_release_hold_issues.py
"""

import subprocess
import sys

ISSUES = [
    {
        "title": "fix(evaluation): [P1] Align model hierarchy split contract, eliminate silent synthetic fallback, and enforce fail-closed evaluation",
        "labels": ["bug", "modeling", "econometrics", "testing"],
        "body": """## Description (Finding 1)

In `scripts/evaluate_model_hierarchy.py:133-170`, the real-data evaluation path expects split dictionary keys `y_train_hybrid`, `y_test_hybrid`, and `train_df`, which are not returned by `prepare_chronological_splits()`. The resulting `KeyError` is caught by a broad `except Exception:`, silently falling back to `generate_benchmark_feature_matrix()` and falsely claiming a Tier 4 promotion pass. Additionally, the evaluator fits a plain Ridge for all tiers rather than executing the actual Tier 4 pipeline (ECM + conformal bounds).

## Required Fix
1. Align chronological split dictionary keys (`splits['X_train']`, `splits['y_train']`, etc.) using price-level targets.
2. Implement strict **fail-closed** semantics: if authentic evaluation data is unavailable, report `evaluation_status: "FAILED_UNAVAILABLE"`—never fall back to synthetic data during promotion audits.
3. Segregate synthetic simulation reports from genuine model promotion decisions.
4. Execute the actual deployed Tier 4 estimator (Ridge/XGBoost + ECM residual + Conformal inference).
5. Add unit tests verifying that split exceptions or missing observations produce a failed audit rather than a synthetic pass.
"""
    },
    {
        "title": "fix(data-ingestion): [P1] Attach granular provenance metadata to feeds and eliminate synthetic official-source labels",
        "labels": ["bug", "data-ingestion", "hardening", "architecture"],
        "body": """## Description (Finding 2)

In `src/data_ingestion.py:938-1021` (EPA RIN connector) and lines 1372-1455 (CEC connector), offline fallbacks and cache misses return hardcoded baseline numbers but label the payload as `status: SUCCESS` and `source: EPA EMTS / CEC`. Similarly, EIA spot defaults retain official-source success labels.

## Required Fix
1. Preserve field-level provenance metadata: `provenance_type: "OBSERVED" | "ESTIMATED_PROXY" | "SYNTHETIC_FALLBACK" | "UNAVAILABLE"`.
2. Return `status: "UNAVAILABLE"` with null fields when upstream requests fail and valid cached observations are absent.
3. Never persist synthetic baseline values into `data/*_vintages.json`.
4. Add explicit synthetic provenance labels to historical feature matrix baseline generators.
"""
    },
    {
        "title": "fix(feature-engineering): [P1] Implement point-in-time vintage joins to eliminate historical publication leakage",
        "labels": ["bug", "modeling", "math", "architecture"],
        "body": """## Description (Finding 3)

In `src/feature_engineering.py:33-98` (`_load_vintage_timeseries()`), a single global cutoff is applied and deduplication keeps the newest revision for each observation date, merging on observation date. When constructing historical training rows, revisions and initial publications released after historical date $t$ leak into row $t$.

## Required Fix
1. Implement true point-in-time joins: for each historical forecast origin row $t$, filter vintage records strictly where `published_at <= t`.
2. Maintain separate columns for `observation_date` and `publication_date`.
3. Test initial publication, subsequent revision, delayed release, and historical-cutoff inference separately.
"""
    },
    {
        "title": "fix(mcp): [P1] Isolate MCP session context and eliminate module-global caller identity",
        "labels": ["security", "api", "architecture"],
        "body": """## Description (Finding 4)

In `src/mcp_server.py:28-41` and `src/api_server.py:1965-2013`, `_active_mcp_context` is stored in a module-global variable. Asynchronous SSE connections and incoming requests overwrite this global, causing concurrent client sessions to share or elevate authorization tiers.

## Required Fix
1. Replace module-global state with `contextvars.ContextVar` or explicit transport-session-bound context objects.
2. Bind authorization identity strictly to the authenticated SSE owner and transport session.
3. Clear session context immediately on disconnect or request cancellation.
4. Add concurrent multi-session tests verifying isolation between basic and privileged callers.
"""
    },
    {
        "title": "fix(storage): [P1] Prevent lost updates during actuals backfill and fail closed on file lock timeouts",
        "labels": ["bug", "infrastructure", "mlops", "architecture"],
        "body": """## Description (Finding 5)

In `src/prediction_logger.py:638-791`, actual-price backfill reads `prediction_history.csv` under a file lock, releases the lock while querying and evaluating rows, and atomically overwrites the file. Forecasts appended concurrently during evaluation are erased. Additionally, `file_lock()` in `src/storage_io.py:59-61` yields upon timeout instead of raising an exception.

## Required Fix
1. Hold the file lock throughout the backfill read-evaluate-write cycle, or re-read under lock and perform a key-based merge on `forecast_id` before writing.
2. Update `file_lock()` to raise `TimeoutError` when lock acquisition times out.
3. Add multi-process concurrency tests simulating interleaved writes and backfills.
"""
    },
    {
        "title": "fix(packaging): [P1] Configure setuptools package discovery for src layout and add wheel smoke test",
        "labels": ["infrastructure", "python", "testing", "release"],
        "body": """## Description (Finding 6)

In `pyproject.toml:1-16`, setuptools packages the contents of `src/` as top-level modules. When installed as a wheel, imports requiring `src.api_server` fail with `ModuleNotFoundError: No module named 'src'`.

## Required Fix
1. Configure explicit package discovery in `pyproject.toml`:
   ```toml
   [tool.setuptools.packages.find]
   where = ["."]
   include = ["src*", "src.*"]
   ```
2. Include runtime package data assets in wheel builds.
3. Add a CI smoke test that builds the wheel, installs it in an isolated virtualenv outside the repo checkout, and starts the API server.
"""
    },
    {
        "title": "fix(ground-truth): [P1] Route EIA retail ground truth by fuel type and reject gasoline fallbacks for diesel",
        "labels": ["bug", "data-ingestion", "econometrics", "modeling"],
        "body": """## Description (Finding 7)

In `src/eia_retail_feed.py:149-187` and `src/prediction_logger.py:745-752`, unmapped region keys (e.g., `Tulsa_ULSD`) default to regular gasoline series `GASREGW`. Additionally, lookups accept observations up to 14 days old as target-date actuals.

## Required Fix
1. Add explicit mapping for on-highway diesel ground truth (`GASDESW` / PADD diesel series).
2. Fail closed and return `None` when a target fuel/region has no mapped ground-truth series.
3. Eliminate 14-day stale carry-forward actuals for daily metro evaluations, or explicitly label weekly survey proxy evaluations.
"""
    },
    {
        "title": "fix(api): [P1] Validate forecast target maturity, eliminate interval decoupling, and remove synthetic delta fallbacks",
        "labels": ["bug", "api", "modeling", "math"],
        "body": """## Description (Finding 8)

In `src/api_server.py:593-690`, historical forecast records are rebased against today's live base price without checking if their target date has expired, while retaining old target dates and unadjusted interval endpoints. If no forecast exists, a hardcoded positive delta is generated.

## Required Fix
1. Check target maturity: mark forecasts with `forecast_target_date <= today` as expired/stale.
2. Keep prediction intervals and trajectories mathematically coupled with the active point estimate and current horizon residual variance.
3. Return `status: "UNAVAILABLE"` instead of synthesizing positive price deltas when no valid forecast exists.
"""
    },
    {
        "title": "fix(diesel): [P1] Segregate ULSD regional estimator as experimental simulation until fitted on authentic data",
        "labels": ["modeling", "econometrics", "math"],
        "body": """## Description (Finding 9)

In `src/diesel_regional.py:223-264`, `fit_model()` trains on 250 random-normal rows with hardcoded synthetic weights, and exposes the result as a production forecast.

## Required Fix
1. Mark the ULSD regional estimator as `status: "EXPERIMENTAL_SIMULATION"`.
2. Segregate diesel records and accuracy from production scoreboard reporting until trained and validated on authentic historical EIA diesel and NYMEX `HO=F` data.
"""
    },
    {
        "title": "fix(regional): [P2] Standardize dynamic region result contract and restore secondary-region generation",
        "labels": ["bug", "modeling", "mlops", "architecture"],
        "body": """## Description (Findings 10 & 11)

In `src/dynamic_region.py:89-94` and `src/locations/runner.py:158-237`, key mismatches (`predicted_5d_price` vs `live_pred_price`, `current_base_price` vs `current_price`) cause national forecasts to be ignored and regional prediction logging exceptions to be swallowed. Furthermore, regional wrappers collapse dual anchors (Oakland vs Bay Area, Cincinnati OH vs KY) into a single region, omitting secondary-region outputs.

## Required Fix
1. Standardize prediction dictionary keys and logging DataFrame schema across national and dynamic runners.
2. Restore distinct forecast generation and logging for all advertised regional sub-locales.
3. Add tests verifying ledger append and distinct dual-anchor outputs.
"""
    },
    {
        "title": "fix(cloud-sync): [P2] Migrate D1/Turso schemas to forecast IDs and paginate full ledger sync",
        "labels": ["infrastructure", "mlops", "architecture"],
        "body": """## Description (Finding 12)

In `src/prediction_logger.py:133-235` and `workers/cache_worker.ts:185-240`, cloud databases use composite primary key `(log_timestamp, forecast_target_date, region)` instead of `forecast_id`, losing retroactive/prospective metadata and colliding on same-second forecasts. Cloud sync only uploads `tail(50)`, failing to synchronize historical updates or large backlogs.

## Required Fix
1. Migrate Cloudflare D1 and Turso database schemas to primary key `forecast_id`.
2. Preserve `issued_at_utc`, `is_retroactive_backtest`, and actual evaluation fields in cloud schemas.
3. Implement durable change-tracking with pagination to synchronize all pending and backfilled records.
"""
    },
    {
        "title": "fix(econometrics): [P2] Align Asymmetric ECM inference recurrence with fitted lag equation",
        "labels": ["bug", "econometrics", "math", "modeling"],
        "body": """## Description (Finding 13)

In `src/asymmetric_ecm.py:193-220`, inference calculates disequilibrium $z_t$ from the *new* wholesale price instead of lagged disequilibrium $z_{t-1}$, counting wholesale shocks twice. It also initializes lag histories to zeros instead of fitted historical tails.

## Required Fix
1. Compute the error-correction term strictly from the previous period state: $z_{t-1} = \text{retail}_{t-1} - (\beta \cdot \text{wholesale}_{t-1} + c)$.
2. Preserve fitted lag state from historical data for warm-start multi-step inference.
3. Verify recursive multi-step forecasts against hand-calculated equations.
"""
    },
    {
        "title": "fix(inference): [P2] Require valid calibration sample sizes for conformal intervals and unify plausibility clamping",
        "labels": ["modeling", "statistics", "math"],
        "body": """## Description (Findings 14, 15, 16)

In `src/models.py:1286-1309`, split conformal intervals are enabled with $n=10$, where a 95% quantile rank is unattainable. In `src/models.py:583-594`, `StandardScaler()` fits before `RidgeCV` inner temporal splits, leaking statistics into validation folds. In `src/models.py:503-527`, sequential return and quant clamps contradict each other.

## Required Fix
1. Require $n \ge 50$ for formal split conformal bounds; use clearly labeled empirical quantile heuristics when $n < 50$.
2. Embed `StandardScaler()` inside cross-validation pipelines with purged chronological splits.
3. Replace sequential clamping with a unified convex projection onto the intersection of valid return and quant bounds.
"""
    },
    {
        "title": "fix(feature-engineering): [P2] Prevent backward clipping of post-dataset events and harden regional market loaders",
        "labels": ["bug", "modeling", "spatial"],
        "body": """## Description (Findings 17 & 18)

In `src/feature_engineering.py:885-900`, `searchsorted` clips future and weekend events backward to the final trading day of the dataset. In `src/locations/tulsa/regional.py:40-59`, empty market downloads bypass fallbacks and crash with `IndexError: single positional indexer is out-of-bounds`.

## Required Fix
1. Exclude events outside the session date range or advance the forecast origin to the next valid session; never clip forward events backward.
2. Validate DataFrame lengths and required columns in regional market loaders before indexing.
"""
    },
    {
        "title": "fix(testing): [P2] Enforce test fixture file isolation and prevent workspace data pollution",
        "labels": ["testing", "infrastructure", "mlops"],
        "body": """## Description (Finding 19)

In `tests/conftest.py:10-26`, only `HISTORY_CSV_PATH` was redirected. Running pytest mutated 47 data files and 60 doc/artifact files in the working directory.

## Required Fix
1. Redirect all output and data directories (`DATA_DIR`, `VINTAGES_DIR`, `DOCS_OUTPUT_DIR`) to pytest `tmp_path` fixtures.
2. Disable external network access by default in test sessions.
3. Assert a clean git working tree after running unit tests in CI.
"""
    },
    {
        "title": "docs(release): [P2] Reconcile mathematical docs, release notes, driver attributions, and publication freshness gates",
        "labels": ["documentation", "release", "dashboard", "mlops"],
        "body": """## Description (Findings 20, 21, 22)

In `src/models.py:351-406`, driver breakdowns divide net change by fixed percentages rather than calculating true feature attributions. In `docs/math.html` and `RELEASE_NOTES_v0.7.0.md`, documented paths (fixed alpha, CPCV, dependency versions) conflict with actual implementations. In `run_all.py:187-194` and `src/static_api_exporter.py:43-87`, partial location failures still publish a master payload with `status: success`.

## Required Fix
1. Connect driver explanations to real linear/SHAP contributions or label as illustrative allocations.
2. Reconcile documentation and release notes with actual default settings and dependency versions.
3. Implement a strict publication gate in `run_all.py` and `static_api_exporter.py` that halts publication if any required regional forecast fails or is stale.
"""
    }
]

def main():
    print(f"Creating {len(ISSUES)} GitHub issues for Release Hold findings...")
    created = []
    for idx, issue in enumerate(ISSUES, 1):
        print(f"[{idx}/{len(ISSUES)}] {issue['title']}...")
        cmd = [
            "gh", "issue", "create",
            "--title", issue["title"],
            "--body", issue["body"]
        ]
        for label in issue["labels"]:
            cmd.extend(["--label", label])
        
        try:
            res = subprocess.run(cmd, capture_output=True, text=True, check=True)
            url = res.stdout.strip()
            print(f" -> Created: {url}")
            created.append((issue["title"], url))
        except subprocess.CalledProcessError as e:
            print(f" -> Error creating issue: {e.stderr.strip()}", file=sys.stderr)
            return 1
    
    print("\nAll 16 issues created successfully!")
    for title, url in created:
        print(f"* {url} - {title}")
    return 0

if __name__ == "__main__":
    sys.exit(main())
