"""
Script to comment & close GitHub Issue #47 and create two new follow-up feature issues.
"""

import subprocess
import sys

def run_gh_cmd(cmd_args: list[str]) -> str:
    res = subprocess.run(["gh"] + cmd_args, capture_output=True, text=True)
    if res.returncode != 0:
        print(f"Error executing gh {' '.join(cmd_args)}:\n{res.stderr}", file=sys.stderr)
        raise RuntimeError(res.stderr)
    return res.stdout.strip()

def main():
    # 1. Comment on Issue #47
    comment_body = """### Resolution Summary for Issue #47

**Feature:** Realized-vs-Predicted Rolling Scoreboard API & Dashboard Section

#### Implementation Details
1. **MLOps Scoreboard Engine (`src/prediction_logger.py`):**
   - Implemented `compute_rolling_scoreboard_metrics(window_days, region)` calculating MAE ($/gal), RMSE ($/gal), MAPE (%), Directional Hit Rate %, Naive Persistence Baseline MAE, and Model MAE Uplift % vs. ground-truth market prices.
   - Implemented `compute_regional_scoreboard_breakdown(window_days)` returning per-locale breakdowns across all 8 active regional markets.
   - Implemented `get_recent_evaluated_records(limit)` returning chronologically-sorted out-of-time evaluation records.

2. **REST API Gateway (`src/api_server.py`):**
   - Exposed `GET /api/v1/forecast/scoreboard` supporting `window` (30, 60, 90, all) and `locale` parameters.
   - Protected by `KeyManager` token authentication.

3. **Public Web Dashboard (`src/dashboard_generator.py` -> `docs/index.html`):**
   - Embedded dynamic Realized-vs-Predicted Rolling Scoreboard section displaying Hero KPI cards and Regional Scoreboard Matrix Table.

4. **Testing & Validation (`tests/test_prediction_scoreboard.py`):**
   - 4 dedicated unit tests; 289/289 total test suite passing."""

    print("Commenting on Issue #47...")
    run_gh_cmd(["issue", "comment", "47", "--body", comment_body])

    print("Closing Issue #47...")
    run_gh_cmd(["issue", "close", "47"])

    # 2. Open New Issue 1: Horizon-Specific Scoreboard Metrics
    issue1_title = "feat(scoreboard): Implement Horizon-Specific Performance Metrics & Forecast Horizon Breakdown"
    issue1_body = """### Context & Motivation
Currently, the rolling scoreboard evaluates overall 5-day out performance. Breaking down performance metrics across 1-day, 2-day, 3-day, 4-day, and 5-day forecast horizons provides deeper granular insight into short-term vs medium-term model accuracy.

### Proposed Implementation
1. Extend `compute_rolling_scoreboard_metrics` and `compute_regional_scoreboard_breakdown` in `src/prediction_logger.py` to support `horizon_days` filtering (1d through 5d).
2. Expose `horizon` query parameter in `GET /api/v1/forecast/scoreboard`.
3. Render a multi-horizon comparison selector / table on the GitHub Pages dashboard (`docs/index.html`).

### Acceptance Criteria
- API accepts `horizon` filter; scoreboard displays per-horizon MAE/RMSE/hit rate breakdowns; unit tests cover horizon filtering."""

    print("Creating Issue 1: Horizon-Specific Scoreboard Metrics...")
    issue1_url = run_gh_cmd(["issue", "create", "--title", issue1_title, "--body", issue1_body, "--label", "enhancement,api,dashboard"])
    print(f"Created Issue 1: {issue1_url}")

    # 3. Open New Issue 2: Automated Model Degradation Alerting
    issue2_title = "feat(mlops): Implement Automated Model Degradation & Baseline Underperformance Alerting"
    issue2_body = """### Context & Motivation
If model MAE uplift drops below zero (`model_uplift_mae_pct < 0.0`), indicating the model is underperforming naive persistence baseline, automated alerts should trigger immediately to notify developers and schedule retraining.

### Proposed Implementation
1. Add degradation threshold check in `src/weekly_model_review.py` evaluating `model_uplift_mae_pct < 0.0`.
2. Integrate Webhook / GitHub Issue alert generation when model degradation is detected.
3. Log alert events to `data/telemetry_alerts.json` and report in `.github/workflows/weekly_model_review.yml`.

### Acceptance Criteria
- Weekly review flags model underperformance; automated alert fires when uplift falls below 0%; unit tests verify threshold triggering."""

    print("Creating Issue 2: Automated Model Degradation Alerting...")
    issue2_url = run_gh_cmd(["issue", "create", "--title", issue2_title, "--body", issue2_body, "--label", "enhancement,modeling"])
    print(f"Created Issue 2: {issue2_url}")

if __name__ == "__main__":
    main()
