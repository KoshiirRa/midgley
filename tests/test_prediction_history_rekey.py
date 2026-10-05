"""
Unit Tests for Prediction History Clean-Up and Deterministic Re-Keying (Issue #585)
"""

import os
import tempfile
import pandas as pd
import pytest

from scripts.clean_and_rekey_prediction_history import (
    generate_deterministic_forecast_id,
    clean_and_rekey_history
)


def test_deterministic_forecast_id_uniqueness():
    """Verify deterministic forecast_id generation across backtests and live issuances."""
    # Backtests with identical parameters yield identical ID
    id_bt1 = generate_deterministic_forecast_id("National", "v1.6-Ridge", "2026-10-05", 5, "RETROSPECTIVE_BACKTEST")
    id_bt2 = generate_deterministic_forecast_id("National", "v1.6-Ridge", "2026-10-05", 5, "RETROSPECTIVE_BACKTEST")
    assert id_bt1 == id_bt2
    assert len(id_bt1) == 32

    # Different regions yield distinct IDs
    id_tulsa = generate_deterministic_forecast_id("Tulsa_OK", "v1.6-Ridge", "2026-10-05", 5, "RETROSPECTIVE_BACKTEST")
    assert id_bt1 != id_tulsa

    # Live prospective forecasts with different issue timestamps yield distinct IDs
    id_live_am = generate_deterministic_forecast_id("National", "v1.6-Ridge", "2026-10-05", 5, "LIVE_PROSPECTIVE", "2026-09-29 08:00:00")
    id_live_pm = generate_deterministic_forecast_id("National", "v1.6-Ridge", "2026-10-05", 5, "LIVE_PROSPECTIVE", "2026-09-29 16:00:00")
    assert id_live_am != id_live_pm


def test_clean_and_rekey_preserves_live_forecasts(tmp_path):
    """Verify clean_and_rekey_history collapses backtests, preserves all live rows, and drops dummy intraday rows."""
    sample_data = [
        # Duplicate backtests
        {"region": "National", "model_version": "v1.6-Ridge", "forecast_target_date": "2026-10-05", "forecast_horizon_days": 5, "run_type": "RETROSPECTIVE_BACKTEST", "log_timestamp": "2026-09-20 12:00:00", "current_base_price": 2.50, "predicted_5d_price": 2.55},
        {"region": "National", "model_version": "v1.6-Ridge", "forecast_target_date": "2026-10-05", "forecast_horizon_days": 5, "run_type": "RETROSPECTIVE_BACKTEST", "log_timestamp": "2026-09-21 12:00:00", "current_base_price": 2.50, "predicted_5d_price": 2.55},
        # Live forecasts at different timestamps
        {"region": "National", "model_version": "v1.6-Ridge", "forecast_target_date": "2026-10-05", "forecast_horizon_days": 5, "run_type": "LIVE_PROSPECTIVE", "log_timestamp": "2026-09-26 08:00:00", "issued_at_utc": "2026-09-26 08:00:00", "current_base_price": 2.50, "predicted_5d_price": 2.55},
        {"region": "National", "model_version": "v1.6-Ridge", "forecast_target_date": "2026-10-05", "forecast_horizon_days": 5, "run_type": "LIVE_PROSPECTIVE", "log_timestamp": "2026-09-27 08:00:00", "issued_at_utc": "2026-09-27 08:00:00", "current_base_price": 2.52, "predicted_5d_price": 2.58},
        # Dummy intraday row
        {"region": "National", "model_version": "v1.6-Ridge", "forecast_target_date": "2026-10-05", "forecast_horizon_days": 5, "run_type": "INTRADAY_REVISION", "log_timestamp": "2026-09-26 05:42:39", "current_base_price": 3.184, "predicted_5d_price": 3.2502},
    ]

    input_csv = str(tmp_path / "raw_history.csv")
    output_csv = str(tmp_path / "clean_history.csv")
    pd.DataFrame(sample_data).to_csv(input_csv, index=False)

    df_cleaned = clean_and_rekey_history(csv_path=input_csv, source_git_rev="HEAD_NONEXISTENT", output_path=output_csv)

    # 1 backtest, 2 live prospective, 0 dummy intraday = 3 rows total
    assert len(df_cleaned) == 3
    assert len(df_cleaned[df_cleaned["run_type"] == "RETROSPECTIVE_BACKTEST"]) == 1
    assert len(df_cleaned[df_cleaned["run_type"] == "LIVE_PROSPECTIVE"]) == 2
    assert len(df_cleaned[df_cleaned["run_type"] == "INTRADAY_REVISION"]) == 0
    assert df_cleaned["forecast_id"].nunique() == 3


def test_log_predictions_idempotent_after_clean(tmp_path, monkeypatch):
    """Regression test asserting log_predictions adds 0 duplicate backtest rows after clean (Issue #602)."""
    from src.prediction_logger import log_predictions, generate_forecast_id

    test_csv = str(tmp_path / "prediction_history.csv")
    monkeypatch.setattr("src.prediction_logger.HISTORY_CSV_PATH", test_csv)

    pred_df = pd.DataFrame([
        {
            "date": "2026-09-28",
            "forecast_target_date": "2026-10-05",
            "current_price": 2.50,
            "predicted_5d_price": 2.55,
            "forecast_horizon_days": 5
        }
    ])

    log_predictions(
        pred_df,
        region="National",
        model_version="v1.6-Ridge",
        run_type="RETROSPECTIVE_BACKTEST",
        is_retroactive_backtest=True
    )
    df1 = pd.read_csv(test_csv)
    assert len(df1) == 1
    initial_fid = df1.iloc[0]["forecast_id"]
    expected_fid = generate_forecast_id("National", "v1.6-Ridge", "2026-10-05", 5, "RETROSPECTIVE_BACKTEST")
    assert initial_fid == expected_fid

    # Clean the file
    clean_and_rekey_history(csv_path=test_csv, output_path=test_csv)
    df_after_clean = pd.read_csv(test_csv)
    assert len(df_after_clean) == 1

    # Log the exact same prediction again (idempotent logging)
    log_predictions(
        pred_df,
        region="National",
        model_version="v1.6-Ridge",
        run_type="RETROSPECTIVE_BACKTEST",
        is_retroactive_backtest=True
    )
    df2 = pd.read_csv(test_csv)
    assert len(df2) == 1, f"Expected 1 row, got {len(df2)} (duplicate added)"
    assert df2.iloc[0]["forecast_id"] == expected_fid

