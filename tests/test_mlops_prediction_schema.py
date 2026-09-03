"""
Unit Test Suite for Extended MLOps Prediction History Schema & Observability Metrics (Issue #124)
"""

import os
import pytest
import pandas as pd
import numpy as np
import src.prediction_logger as pred_logger
from src.prediction_logger import (
    ensure_history_store,
    log_predictions,
    compute_mlops_observability_summary,
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


def test_compute_mlops_observability_summary():
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
    
    summary = compute_mlops_observability_summary(window_days=30)
    assert summary["total_evaluations"] == 2
    assert summary["llm_augmentation_win_rate_pct"] == 100.0
    assert summary["ci_95_coverage_pct"] == 100.0
    assert "GasBuddy_GraphQL" in summary["provenance_breakdown"]
    assert "AAA_Scraper" in summary["provenance_breakdown"]


def test_format_mlops_observability_markdown_section():
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
    history_df.to_csv(pred_logger.HISTORY_CSV_PATH, index=False)

    section_md = format_mlops_observability_markdown_section()
    assert "Extended MLOps Observability & Feature Attribution" in section_md
    assert "LLM Augmentation Win Rate" in section_md
    assert "95% Confidence Interval Coverage" in section_md
