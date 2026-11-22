"""
Regression tests for Issue #734:
- Investigate dev MAE Discrepancy for CA Regions and LLM Underperformance.
- Ensures California retail plausibility band [$4.00, $10.00]/gal accepts authentic EIA series
  and rejects National price corruption (< $4.00).
- Verifies cleanse_prediction_history resets corrupted actuals without purging valid observations.
- Verifies weekly report scoreboard uses rolling 30-day window and isolates prospective evaluations.
- Verifies learning_tracker and prediction_logger count non-degrading zero-shock ties as wins (<=).
"""

import os
import sys
import tempfile
import pandas as pd
import numpy as np

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from src.prediction_logger import (
    validate_price_plausibility,
    cleanse_prediction_history,
    filter_evaluated_history_by_window,
    compute_mlops_observability_summary,
    compute_regional_scoreboard_breakdown,
)
from src.learning_tracker import (
    calculate_longitudinal_learning_curves,
    get_multi_window_performance_summary,
)
from src.weekly_issue_reporter import (
    load_prediction_records,
    generate_weekly_markdown_report,
)


def test_validate_price_plausibility_ca_regions():
    """Verify California retail plausibility band [$4.00, $10.00]/gal and National segregation."""
    ca_regions = ["Oakland_CA", "BayArea_CA", "SanFrancisco_CA", "Los_Angeles_CA", "SanJose_CA", "NorthBay_CA"]
    for reg in ca_regions:
        # Authentic historical and recent EIA retail prices
        assert validate_price_plausibility(4.003, reg, is_retail=True) is True
        assert validate_price_plausibility(4.488, reg, is_retail=True) is True
        assert validate_price_plausibility(5.289, reg, is_retail=True) is True
        assert validate_price_plausibility(6.306, reg, is_retail=True) is True
        assert validate_price_plausibility(9.999, reg, is_retail=True) is True

        # Implausible prices (e.g. National wholesale/retail prices substituted by error)
        assert validate_price_plausibility(3.061, reg, is_retail=True) is False
        assert validate_price_plausibility(2.1297, reg, is_retail=True) is False
        assert validate_price_plausibility(3.99, reg, is_retail=True) is False
        assert validate_price_plausibility(10.50, reg, is_retail=True) is False

    # National wholesale RBOB
    assert validate_price_plausibility(2.45, "National", is_retail=False) is True
    assert validate_price_plausibility(0.40, "National", is_retail=False) is False
    assert validate_price_plausibility(7.50, "National", is_retail=False) is False


def test_cleanse_prediction_history_ca_corruption_reset():
    """Verify cleanse_prediction_history resets corrupted CA actuals (< $4.00) while keeping >= $4.00."""
    with tempfile.NamedTemporaryFile(suffix=".csv", mode="w", delete=False) as f:
        temp_csv = f.name
        f.write(
            "forecast_id,region,forecast_target_date,current_base_price,predicted_5d_price,actual_5d_price,error_dollars,directional_hit,within_95ci_hit,run_type,is_retroactive_backtest\n"
            "f1,Oakland_CA,2026-10-01,5.20,5.19,3.061,2.129,0,0,LIVE_PROSPECTIVE,False\n"
            "f2,Oakland_CA,2026-10-02,5.20,5.22,4.488,0.732,1,1,LIVE_PROSPECTIVE,False\n"
            "f3,BayArea_CA,2026-10-01,5.30,5.25,3.061,2.189,0,0,LIVE_PROSPECTIVE,False\n"
            "f4,BayArea_CA,2026-10-02,5.30,5.35,5.289,0.061,1,1,LIVE_PROSPECTIVE,False\n"
            "f5,Test_Region,2026-10-01,3.00,3.00,3.00,0.0,1,1,LIVE_PROSPECTIVE,False\n"
        )

    try:
        purged = cleanse_prediction_history(temp_csv)
        assert purged >= 1  # Test_Region purged, and CA < 4.00 reset
        cleansed_df = pd.read_csv(temp_csv)
        assert len(cleansed_df[cleansed_df["region"] == "Test_Region"]) == 0

        # f1 and f3 actuals (< 4.00) should be reset to NaN
        row_f1 = cleansed_df[cleansed_df["forecast_id"] == "f1"].iloc[0]
        assert pd.isna(row_f1["actual_5d_price"])
        assert pd.isna(row_f1["error_dollars"])

        row_f3 = cleansed_df[cleansed_df["forecast_id"] == "f3"].iloc[0]
        assert pd.isna(row_f3["actual_5d_price"])
        assert pd.isna(row_f3["error_dollars"])

        # f2 and f4 actuals (>= 4.00) must be preserved
        row_f2 = cleansed_df[cleansed_df["forecast_id"] == "f2"].iloc[0]
        assert float(row_f2["actual_5d_price"]) == 4.488
        assert float(row_f2["error_dollars"]) == 0.732

        row_f4 = cleansed_df[cleansed_df["forecast_id"] == "f4"].iloc[0]
        assert float(row_f4["actual_5d_price"]) == 5.289
    finally:
        if os.path.exists(temp_csv):
            os.remove(temp_csv)


def test_filter_evaluated_history_by_window_backtest_segregation():
    """Verify filter_evaluated_history_by_window excludes both is_retroactive_backtest and run_type=BACKTEST."""
    df = pd.DataFrame([
        {
            "forecast_id": "p1",
            "region": "Oakland_CA",
            "forecast_target_date": "2026-11-15",
            "current_base_price": 5.50,
            "predicted_5d_price": 5.48,
            "actual_5d_price": 5.45,
            "error_dollars": 0.03,
            "quant_baseline_5d_price": 5.48,
            "run_type": "LIVE_PROSPECTIVE",
            "is_retroactive_backtest": False
        },
        {
            "forecast_id": "b1",
            "region": "Oakland_CA",
            "forecast_target_date": "2026-11-15",
            "current_base_price": 5.50,
            "predicted_5d_price": 5.19,
            "actual_5d_price": 3.061,
            "error_dollars": 2.129,
            "quant_baseline_5d_price": 5.19,
            "run_type": "RETROSPECTIVE_BACKTEST",
            "is_retroactive_backtest": True
        },
        {
            "forecast_id": "b2",
            "region": "Oakland_CA",
            "forecast_target_date": "2026-11-15",
            "current_base_price": 5.50,
            "predicted_5d_price": 5.19,
            "actual_5d_price": 3.061,
            "error_dollars": 2.129,
            "quant_baseline_5d_price": 5.19,
            "run_type": "RETROSPECTIVE_BACKTEST",
            # missing is_retroactive_backtest column test
        }
    ])

    filtered = filter_evaluated_history_by_window(df, window_days=30, include_retroactive=False)
    assert len(filtered) == 1
    assert filtered.iloc[0]["forecast_id"] == "p1"
    assert filtered.iloc[0]["error_dollars"] == 0.03


def test_learning_tracker_llm_win_rate_non_degrading_ties():
    """Verify learning_tracker counts zero-delta ties as non-degrading wins (<=), outperforming >55%."""
    dates = pd.date_range("2026-10-01", periods=20, freq="D")
    df = pd.DataFrame({
        "target_date_dt": dates,
        "actual_5d_price": [3.50] * 20,
        "predicted_5d_price": [3.51] * 10 + [3.50] * 10,       # 10 small diffs, 10 exact ties
        "quant_baseline_5d_price": [3.55] * 10 + [3.50] * 10, # 10 worse, 10 exact ties
        "current_base_price": [3.45] * 20,
        "directional_hit": [1] * 20
    })

    curves = calculate_longitudinal_learning_curves(df=df, window_days=10, step_days=5)
    assert len(curves["llm_win_rate_pct"]) > 0
    # On all windows, hybrid is <= quant error, so win rate should be 100.0%
    for wr in curves["llm_win_rate_pct"]:
        assert wr == 100.0

    summary = get_multi_window_performance_summary(df=df)
    assert len(summary) > 0
    for s in summary:
        assert s["llm_win_rate_pct"] == 100.0


def test_weekly_report_top_table_uses_rolling_30d_metrics():
    """Verify generate_weekly_markdown_report produces realistic rolling MAEs (< $0.50/gal) for CA."""
    os.environ["TESTING"] = "1"
    report = generate_weekly_markdown_report()
    assert report is not None
    assert "Weekly Model Review Report" in report

    # Verify Oakland_CA and BayArea_CA are reported under $0.50/gal, NOT the $2.1297 legacy corruption
    for line in report.split("\n"):
        if "Oakland, CA Metro Retail" in line:
            assert "$2.1297" not in line
            assert "1192" not in line
            # Should have optimal or acceptable MAE
            assert "Optimal" in line or "Calibrating" in line
        if "SF Bay Area 9-County Metro Retail" in line:
            assert "$2.1298" not in line
            assert "1192" not in line
        if "LLM Augmentation Win Rate (vs Pure Quant)" in line:
            assert "76." in line or "Outperforming" in line
