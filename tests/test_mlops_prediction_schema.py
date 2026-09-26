"""
Unit Test Suite for Extended MLOps Prediction History Schema & Observability Metrics (Issue #124)
"""

import os
from datetime import datetime, timedelta
import pytest
import pandas as pd
import numpy as np
import src.prediction_logger as pred_logger
from src.prediction_logger import (
    ensure_history_store,
    log_predictions,
    compute_mlops_observability_summary,
    compute_rolling_scoreboard_metrics,
)
from src.weekly_issue_reporter import format_mlops_observability_markdown_section

@pytest.fixture(autouse=True)
def setup_test_csv(tmp_path, monkeypatch):
    """Isolates prediction history CSV to temporary directory during testing."""
    test_csv = tmp_path / "prediction_history.csv"
    monkeypatch.setattr(pred_logger, "HISTORY_CSV_PATH", str(test_csv))
    yield str(test_csv)


def test_ensure_history_store_creates_extended_columns():
    ensure_history_store()
    csv_path = pred_logger.HISTORY_CSV_PATH
    assert os.path.exists(csv_path)
    df = pd.read_csv(csv_path)
    
    expected_cols = [
        "log_timestamp", "forecast_target_date", "region", "model_version",
        "run_type", "headline_trigger", "current_base_price", "predicted_5d_price",
        "predicted_direction", "actual_5d_price", "actual_direction", "error_dollars",
        "directional_hit", "llm_price_pressure", "llm_supply_disruption",
        "quant_baseline_5d_price", "llm_augmentation_delta", "prediction_lower_95ci",
        "prediction_upper_95ci", "within_95ci_hit", "data_source_provenance"
    ]
    for col in expected_cols:
        assert col in df.columns, f"Missing expected column: {col}"


def test_log_predictions_with_extended_vectors():
    pred_df = pd.DataFrame([{
        "date": "2026-09-01",
        "current_price": 3.50,
        "predicted_5d_price": 3.62,
        "forecast_target_date": "2026-09-06",
        "llm_price_pressure": 0.35,
        "llm_supply_disruption": 0.20,
        "quant_baseline_5d_price": 3.55,
        "llm_augmentation_delta": 0.07,
        "prediction_lower_95ci": 3.48,
        "prediction_upper_95ci": 3.76,
        "data_source_provenance": "GasBuddy_GraphQL"
    }])
    
    n_logged = log_predictions(pred_df, region="Tulsa_OK", model_version="v1.5-MLOps")
    assert n_logged == 1
    
    csv_path = pred_logger.HISTORY_CSV_PATH
    df = pd.read_csv(csv_path)
    assert len(df) == 1
    row = df.iloc[0]
    assert row["region"] == "Tulsa_OK"
    assert row["model_version"] == "v1.5-MLOps"
    assert row["llm_price_pressure"] == 0.35
    assert row["llm_supply_disruption"] == 0.20
    assert row["quant_baseline_5d_price"] == 3.55
    assert row["llm_augmentation_delta"] == 0.07
    assert row["prediction_lower_95ci"] == 3.48
    assert row["prediction_upper_95ci"] == 3.76
    assert row["data_source_provenance"] == "GasBuddy_GraphQL"


def test_compute_mlops_observability_summary(monkeypatch):
    # Insert mock evaluated records into test CSV
    ensure_history_store()
    history_df = pd.DataFrame([
        {
            "log_timestamp": "2026-09-01 10:00:00",
            "forecast_target_date": "2026-09-06",
            "region": "Tulsa_OK",
            "model_version": "v1.5-MLOps",
            "run_type": "DAILY_BATCH",
            "current_base_price": 3.50,
            "predicted_5d_price": 3.60,
            "predicted_direction": "UP",
            "actual_5d_price": 3.58,
            "actual_direction": "UP",
            "error_dollars": 0.02,
            "directional_hit": 1,
            "llm_price_pressure": 0.40,
            "llm_supply_disruption": 0.10,
            "quant_baseline_5d_price": 3.52,
            "llm_augmentation_delta": 0.08,
            "prediction_lower_95ci": 3.48,
            "prediction_upper_95ci": 3.72,
            "within_95ci_hit": 1,
            "data_source_provenance": "GasBuddy_GraphQL"
        },
        {
            "log_timestamp": "2026-09-02 10:00:00",
            "forecast_target_date": "2026-09-07",
            "region": "Newark_DE",
            "model_version": "v1.5-MLOps",
            "run_type": "DAILY_BATCH",
            "current_base_price": 3.20,
            "predicted_5d_price": 3.10,
            "predicted_direction": "DOWN",
            "actual_5d_price": 3.12,
            "actual_direction": "DOWN",
            "error_dollars": 0.02,
            "directional_hit": 1,
            "llm_price_pressure": -0.25,
            "llm_supply_disruption": 0.0,
            "quant_baseline_5d_price": 3.18,
            "llm_augmentation_delta": -0.08,
            "prediction_lower_95ci": 2.98,
            "prediction_upper_95ci": 3.22,
            "within_95ci_hit": 1,
            "data_source_provenance": "AAA_Scraper"
        }
    ])
    csv_path = pred_logger.HISTORY_CSV_PATH
    history_df.to_csv(csv_path, index=False)
    monkeypatch.setattr(pred_logger, "backfill_actual_prices_and_evaluate", lambda: pd.read_csv(csv_path))
    
    summary = compute_mlops_observability_summary(window_days=30)
    assert summary["total_evaluations"] == 2
    assert summary["llm_augmentation_win_rate_pct"] == 100.0
    assert summary["ci_95_coverage_pct"] == 100.0
    assert "GasBuddy_GraphQL" in summary["provenance_breakdown"]
    assert "AAA_Scraper" in summary["provenance_breakdown"]


def test_format_mlops_observability_markdown_section(monkeypatch):
    ensure_history_store()
    history_df = pd.DataFrame([{
        "log_timestamp": "2026-09-01 10:00:00",
        "forecast_target_date": "2026-09-06",
        "region": "Tulsa_OK",
        "model_version": "v1.5-MLOps",
        "run_type": "DAILY_BATCH",
        "current_base_price": 3.50,
        "predicted_5d_price": 3.60,
        "predicted_direction": "UP",
        "actual_5d_price": 3.58,
        "actual_direction": "UP",
        "error_dollars": 0.02,
        "directional_hit": 1,
        "llm_price_pressure": 0.40,
        "llm_supply_disruption": 0.10,
        "quant_baseline_5d_price": 3.52,
        "llm_augmentation_delta": 0.08,
        "prediction_lower_95ci": 3.48,
        "prediction_upper_95ci": 3.72,
        "within_95ci_hit": 1,
        "data_source_provenance": "GasBuddy_GraphQL"
    }])
    csv_path = pred_logger.HISTORY_CSV_PATH
    history_df.to_csv(csv_path, index=False)
    monkeypatch.setattr(pred_logger, "backfill_actual_prices_and_evaluate", lambda: pd.read_csv(csv_path))

    section_md = format_mlops_observability_markdown_section()
    assert "Extended MLOps Observability & Feature Attribution" in section_md
    assert "LLM Augmentation Win Rate" in section_md
    assert "95% Confidence Interval Coverage" in section_md


def test_resolve_model_tag():
    from src.prediction_logger import resolve_model_tag
    from src.version import get_model_version
    
    expected_base = get_model_version().replace(" ", "-")
    tag_tulsa = resolve_model_tag("Tulsa_OK", "Ridge")
    assert tag_tulsa == f"{expected_base}-TulsaOK-Ridge"

    tag_nat = resolve_model_tag("National", "ridge")
    assert tag_nat == f"{expected_base}-National-Ridge"

    tag_custom = resolve_model_tag("Tulsa_OK", "Ridge", custom_version="custom-v1.0")
    assert tag_custom == "custom-v1.0"


def test_log_predictions_dynamic_model_version():
    from src.version import get_model_version

    pred_df = pd.DataFrame([{
        "date": "2026-09-17",
        "current_price": 3.20,
        "predicted_5d_price": 3.25
    }])
    
    n_logged = log_predictions(pred_df, region="Cincinnati_OH")
    assert n_logged == 1

    csv_path = pred_logger.HISTORY_CSV_PATH
    df = pd.read_csv(csv_path)
    assert len(df) == 1
    
    expected_tag = f"{get_model_version().replace(' ', '-')}-CincinnatiOH-Ridge"
    assert df.iloc[0]["model_version"] == expected_tag


def test_backfill_new_region_history_with_quant_baseline():
    from src.prediction_logger import backfill_new_region_history

    dates = ["2026-09-01", "2026-09-02"]
    bases = [3.10, 3.12]
    preds_hybrid = [3.25, 3.20]
    preds_quant = [3.15, 3.14]

    n_logged = backfill_new_region_history(
        test_dates=dates,
        base_prices=bases,
        predicted_prices=preds_hybrid,
        region="Tulsa_OK",
        quant_baseline_prices=preds_quant,
        forecast_horizon_days=5
    )
    assert n_logged == 2

    csv_path = pred_logger.HISTORY_CSV_PATH
    df = pd.read_csv(csv_path)
    assert len(df) == 2
    assert df.iloc[0]["quant_baseline_5d_price"] == 3.15
    assert df.iloc[0]["llm_augmentation_delta"] == 0.10  # 3.25 - 3.15
    assert df.iloc[1]["quant_baseline_5d_price"] == 3.14
    assert df.iloc[1]["llm_augmentation_delta"] == 0.06  # 3.20 - 3.14


def test_mlops_observability_dual_win_rates(monkeypatch):
    ensure_history_store()
    # Row 1: Actual = 3.20, Hybrid Pred = 3.21 (err=0.01), Quant Pred = 3.15 (err=0.05), Base = 3.10 (err=0.10) -> Hybrid wins over both
    # Row 2: Actual = 3.15, Hybrid Pred = 3.30 (err=0.15), Quant Pred = 3.16 (err=0.01), Base = 3.10 (err=0.05) -> Quant wins over Hybrid, Base wins over Hybrid
    # Row 3: Actual = 3.12, Hybrid Pred = 3.11 (err=0.01), Quant Pred = 3.10 (err=0.02), Base = 3.15 (err=0.03) -> Hybrid wins over both
    history_df = pd.DataFrame([
        {
            "log_timestamp": "2026-09-01 10:00:00",
            "forecast_target_date": "2026-09-06",
            "region": "Tulsa_OK",
            "model_version": "v1.5-MLOps",
            "run_type": "DAILY_BATCH",
            "current_base_price": 3.10,
            "predicted_5d_price": 3.21,
            "predicted_direction": "UP",
            "actual_5d_price": 3.20,
            "actual_direction": "UP",
            "error_dollars": 0.01,
            "directional_hit": 1,
            "llm_price_pressure": 0.30,
            "llm_supply_disruption": 0.10,
            "quant_baseline_5d_price": 3.15,
            "llm_augmentation_delta": 0.06,
            "prediction_lower_95ci": 3.05,
            "prediction_upper_95ci": 3.35,
            "within_95ci_hit": 1,
            "data_source_provenance": "GasBuddy_GraphQL"
        },
        {
            "log_timestamp": "2026-09-02 10:00:00",
            "forecast_target_date": "2026-09-07",
            "region": "Tulsa_OK",
            "model_version": "v1.5-MLOps",
            "run_type": "DAILY_BATCH",
            "current_base_price": 3.10,
            "predicted_5d_price": 3.30,
            "predicted_direction": "UP",
            "actual_5d_price": 3.15,
            "actual_direction": "UP",
            "error_dollars": 0.15,
            "directional_hit": 1,
            "llm_price_pressure": 0.50,
            "llm_supply_disruption": 0.20,
            "quant_baseline_5d_price": 3.16,
            "llm_augmentation_delta": 0.14,
            "prediction_lower_95ci": 3.10,
            "prediction_upper_95ci": 3.50,
            "within_95ci_hit": 1,
            "data_source_provenance": "GasBuddy_GraphQL"
        },
        {
            "log_timestamp": "2026-09-03 10:00:00",
            "forecast_target_date": "2026-09-08",
            "region": "Tulsa_OK",
            "model_version": "v1.5-MLOps",
            "run_type": "DAILY_BATCH",
            "current_base_price": 3.15,
            "predicted_5d_price": 3.11,
            "predicted_direction": "DOWN",
            "actual_5d_price": 3.12,
            "actual_direction": "DOWN",
            "error_dollars": 0.01,
            "directional_hit": 1,
            "llm_price_pressure": -0.20,
            "llm_supply_disruption": 0.0,
            "quant_baseline_5d_price": 3.10,
            "llm_augmentation_delta": 0.01,
            "prediction_lower_95ci": 2.95,
            "prediction_upper_95ci": 3.25,
            "within_95ci_hit": 1,
            "data_source_provenance": "GasBuddy_GraphQL"
        }
    ])
    csv_path = pred_logger.HISTORY_CSV_PATH
    history_df.to_csv(csv_path, index=False)
    monkeypatch.setattr(pred_logger, "backfill_actual_prices_and_evaluate", lambda: pd.read_csv(csv_path))

    obs = compute_mlops_observability_summary(window_days=30, include_retroactive=True)
    assert obs["total_evaluations"] == 3
    # 2 out of 3 wins for hybrid over quant (66.67%)
    assert obs["llm_augmentation_win_rate_pct"] == pytest.approx(66.67, rel=1e-2)
    # 2 out of 3 wins for hybrid over persistence (66.67%)
    assert obs["model_vs_persistence_win_rate_pct"] == pytest.approx(66.67, rel=1e-2)


def test_is_retroactive_backtest_auto_derivation(monkeypatch, tmp_path):
    """Verify write-time validation auto-flags retroactive backtest rows vs forward predictions (Issue #389)."""
    test_csv = tmp_path / "test_prediction_history.csv"
    monkeypatch.setattr(pred_logger, "HISTORY_CSV_PATH", str(test_csv))
    ensure_history_store()

    # Case 1: Forward prediction (target date is in the future)
    future_target = (datetime.now() + timedelta(days=5)).strftime("%Y-%m-%d")
    df_forward = pd.DataFrame([{
        "date": datetime.now().strftime("%Y-%m-%d"),
        "forecast_target_date": future_target,
        "current_price": 3.45,
        "predicted_5d_price": 3.50,
        "forecast_horizon_days": 5
    }])
    log_predictions(df_forward, region="Tulsa_OK")

    # Case 2: Retroactive prediction (target date is in the past)
    past_target = (datetime.now() - timedelta(days=30)).strftime("%Y-%m-%d")
    df_retro = pd.DataFrame([{
        "date": (datetime.now() - timedelta(days=35)).strftime("%Y-%m-%d"),
        "forecast_target_date": past_target,
        "current_price": 3.40,
        "predicted_5d_price": 3.45,
        "forecast_horizon_days": 5
    }])
    log_predictions(df_retro, region="Tulsa_OK")

    saved_df = pd.read_csv(str(test_csv))
    assert len(saved_df) == 2
    assert "is_retroactive_backtest" in saved_df.columns
    # First row is forward (False)
    assert bool(saved_df.loc[0, "is_retroactive_backtest"]) is False
    # Second row is retroactive (True)
    assert bool(saved_df.loc[1, "is_retroactive_backtest"]) is True


def test_scoreboard_retroactive_segregation(monkeypatch, tmp_path):
    """Verify rolling scoreboard filters out retroactive backtest records when include_retroactive=False (Issue #389)."""
    test_csv = tmp_path / "test_prediction_history.csv"
    monkeypatch.setattr(pred_logger, "HISTORY_CSV_PATH", str(test_csv))
    ensure_history_store()

    history_df = pd.DataFrame([
        {
            "log_timestamp": "2026-09-01 10:00:00",
            "forecast_target_date": "2026-09-06",
            "region": "Tulsa_OK",
            "model_version": "v1.5-MLOps",
            "run_type": "DAILY_BATCH",
            "current_base_price": 3.00,
            "predicted_5d_price": 3.10,
            "predicted_direction": "UP",
            "actual_5d_price": 3.12,
            "actual_direction": "UP",
            "error_dollars": 0.02,
            "directional_hit": 1,
            "llm_price_pressure": 0.20,
            "llm_supply_disruption": 0.0,
            "quant_baseline_5d_price": 3.08,
            "llm_augmentation_delta": 0.02,
            "prediction_lower_95ci": 2.95,
            "prediction_upper_95ci": 3.25,
            "within_95ci_hit": 1,
            "data_source_provenance": "GasBuddy_GraphQL",
            "forecast_horizon_days": 5,
            "is_retroactive_backtest": False  # Live forward-logged prediction
        },
        {
            "log_timestamp": "2026-09-22 10:00:00",
            "forecast_target_date": "2025-06-15",
            "region": "Tulsa_OK",
            "model_version": "v1.5-MLOps",
            "run_type": "DAILY_BATCH",
            "current_base_price": 3.50,
            "predicted_5d_price": 3.60,
            "predicted_direction": "UP",
            "actual_5d_price": 3.55,
            "actual_direction": "UP",
            "error_dollars": 0.05,
            "directional_hit": 1,
            "llm_price_pressure": 0.30,
            "llm_supply_disruption": 0.10,
            "quant_baseline_5d_price": 3.52,
            "llm_augmentation_delta": 0.08,
            "prediction_lower_95ci": 3.40,
            "prediction_upper_95ci": 3.75,
            "within_95ci_hit": 1,
            "data_source_provenance": "GasBuddy_GraphQL",
            "forecast_horizon_days": 5,
            "is_retroactive_backtest": True  # Retroactive backtest
        }
    ])
    history_df.to_csv(str(test_csv), index=False)
    monkeypatch.setattr(pred_logger, "backfill_actual_prices_and_evaluate", lambda: pd.read_csv(str(test_csv)))

    # Live-only (include_retroactive=False)
    metrics_live = compute_rolling_scoreboard_metrics(window_days="all", include_retroactive=False)
    assert metrics_live["total_evaluations"] == 1
    assert metrics_live["mae_dollars"] == 0.02

    # Full corpus (include_retroactive=True)
    metrics_all = compute_rolling_scoreboard_metrics(window_days="all", include_retroactive=True)
    assert metrics_all["total_evaluations"] == 2
    assert metrics_all["mae_dollars"] == pytest.approx(0.035, rel=1e-2)


