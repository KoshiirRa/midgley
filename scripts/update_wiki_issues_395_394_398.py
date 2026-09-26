#!/usr/bin/env python3
"""
Wiki Updater for Issues #395, #394, #398 (scripts/update_wiki_issues_395_394_398.py)
Updates MLOps-and-Continuous-Feedback.md and Data-Ingestion-and-APIs.md in the GitHub Wiki repository.
"""

import os
import sys

def update_wiki(wiki_dir: str):
    if not os.path.exists(wiki_dir):
        print(f"Wiki directory {wiki_dir} does not exist.")
        return

    # 1. Update MLOps-and-Continuous-Feedback.md
    mlops_file = os.path.join(wiki_dir, "MLOps-and-Continuous-Feedback.md")
    if os.path.exists(mlops_file):
        with open(mlops_file, "r", encoding="utf-8") as f:
            mlops_content = f.read()

        mlops_addition = """
---

## 8. Injectable MLOps Evaluation Architecture (Issue #395)
`backfill_actual_prices_and_evaluate()` in `src/prediction_logger.py` accepts dependency injection parameters:
* `actuals_map_override: Optional[dict]`: Injects point-in-time futures price dictionaries without network calls.
* `eia_feed_override: Optional[Any]`: Injects mock or cached regional retail ground truth instances (`EIARetailFeed`).
* `csv_path: Optional[str]`: Evaluates against isolated temporary test ledgers.
* `force_eval: bool`: Bypasses `TESTING=1` execution guards, allowing full automated test coverage of actual direction assignment, directional hits, error calculations, and confidence interval bounds in CI pipelines.

---

## 9. Calibrated 95% Confidence Interval Evaluation & Horizon Scaling (Issue #394)
Prediction intervals are evaluated strictly against explicit bounds without arbitrary fixed fallback bands:
$$
\\text{Hit}_{95\\text{CI}, i} = \\begin{cases} 1 & \\text{if } \\hat{P}_{\\text{lower}, 95, i} \\le P_{\\text{actual}, i} \\le \\hat{P}_{\\text{upper}, 95, i} \\\\ 0 & \\text{otherwise} \\end{cases}
$$
When interval bounds are missing, calibrated bands are dynamically reconstructed using regional residual standard error scaled by forecast horizon:
$$
\\sigma_{\\text{res}}(h) = \\sigma_{\\text{res}} \\times \\sqrt{\\frac{h}{5}}, \\quad \\hat{P}_{\\pm 95} = \\hat{P}_{\\text{pred}} \\pm 1.96 \\cdot \\sigma_{\\text{res}}(h)
$$
The empirical 95% CI coverage rate is tracked in rolling scoreboard metrics:
$$
\\text{Coverage}_{95\\text{CI}} = \\frac{1}{N} \\sum_{i=1}^{N} \\text{Hit}_{95\\text{CI}, i} \\times 100\\%
$$
"""
        if "Injectable MLOps Evaluation Architecture" not in mlops_content:
            mlops_content += mlops_addition
            with open(mlops_file, "w", encoding="utf-8") as f:
                f.write(mlops_content)
            print("Updated MLOps-and-Continuous-Feedback.md in wiki")
        else:
            print("MLOps-and-Continuous-Feedback.md already updated")

    # 2. Update Data-Ingestion-and-APIs.md
    apis_file = os.path.join(wiki_dir, "Data-Ingestion-and-APIs.md")
    if os.path.exists(apis_file):
        with open(apis_file, "r", encoding="utf-8") as f:
            apis_content = f.read()

        apis_addition = """
---

## 25. README Live Forecast Automation & Workflow Freshness Gating (Issue #398)
* **README Table Injector (`scripts/readme_updater.py` / `src/readme_updater.py`):** Automatically compiles multi-horizon projections across all 10 active regional hubs into the Markdown live summary table between `<!-- START_LIVE_FORECAST -->` and `<!-- END_LIVE_FORECAST -->` tags.
* **UTC vs Central DST Schedule Alignment:** GitHub Actions cron schedules (`17 7 * * *`) evaluate strictly on UTC (07:17 UTC); during Daylight Saving Time (March to November), US Central Time is CDT (02:17 AM CDT / UTC-5), and during standard time (November to March), Central Time is CST (01:17 AM CST / UTC-6).
* **Forecast Freshness Gating:** The public dashboard (`src/dashboard_generator.py`) evaluates the timestamp of the latest prediction record; if data age exceeds 36 hours, a warning badge (`Forecast Stale (>36h)`) is rendered to alert operators.
"""
        if "README Live Forecast Automation" not in apis_content:
            apis_content += apis_addition
            with open(apis_file, "w", encoding="utf-8") as f:
                f.write(apis_content)
            print("Updated Data-Ingestion-and-APIs.md in wiki")
        else:
            print("Data-Ingestion-and-APIs.md already updated")


if __name__ == "__main__":
    wiki_path = sys.argv[1] if len(sys.argv) > 1 else "/home/marty/projects/midgley/wiki_tmp"
    update_wiki(wiki_path)
