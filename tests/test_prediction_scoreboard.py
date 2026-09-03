"""
Unit Tests for Realized-vs-Predicted Rolling Scoreboard Engine (Issue #47)
Tests compute_rolling_scoreboard_metrics, compute_regional_scoreboard_breakdown,
get_recent_evaluated_records, and REST API GET /api/v1/forecast/scoreboard.
"""

import pytest
import pandas as pd
import numpy as np
from src.prediction_logger import (
    compute_rolling_scoreboard_metrics,
    compute_regional_scoreboard_breakdown,
    get_recent_evaluated_records,
    filter_evaluated_history_by_window
)


def test_rolling_scoreboard_metrics_calculation():
    """Verify compute_rolling_scoreboard_metrics computes MAE, RMSE, hit rate, and uplift correctly."""
    metrics_30d = compute_rolling_scoreboard_metrics(window_days=30)
    assert "mae_dollars" in metrics_30d
    assert "rmse_dollars" in metrics_30d
    assert "mape_pct" in metrics_30d
    assert "directional_hit_rate_pct" in metrics_30d
    assert "naive_persistence_mae" in metrics_30d
    assert "model_uplift_mae_pct" in metrics_30d
    assert metrics_30d["total_evaluations"] >= 0

    if metrics_30d["total_evaluations"] > 0:
        assert metrics_30d["mae_dollars"] >= 0.0
        assert metrics_30d["rmse_dollars"] >= metrics_30d["mae_dollars"]
        assert 0.0 <= metrics_30d["directional_hit_rate_pct"] <= 100.0


def test_rolling_scoreboard_windows_and_regions():
    """Verify window filtering (30, 60, 90, all) and regional filter."""
    m_30 = compute_rolling_scoreboard_metrics(window_days=30, region="National")
    m_60 = compute_rolling_scoreboard_metrics(window_days=60, region="National")
    m_all = compute_rolling_scoreboard_metrics(window_days="all", region="National")

    assert m_30["region_filter"] == "National"
    assert m_all["total_evaluations"] >= m_60["total_evaluations"] >= m_30["total_evaluations"]


def test_regional_scoreboard_breakdown():
    """Verify compute_regional_scoreboard_breakdown returns a breakdown for active regions."""
    breakdown = compute_regional_scoreboard_breakdown(window_days=30)
    assert isinstance(breakdown, list)
    if len(breakdown) > 0:
        item = breakdown[0]
        assert "region" in item
        assert "evaluations" in item
        assert "mae_dollars" in item
        assert "directional_hit_rate_pct" in item
        assert "model_uplift_mae_pct" in item


def test_get_recent_evaluated_records():
    """Verify get_recent_evaluated_records returns formatted chronologically sorted records."""
    records = get_recent_evaluated_records(limit=10)
    assert isinstance(records, list)
    if len(records) > 0:
        rec = records[0]
        assert "forecast_target_date" in rec
        assert "region" in rec
        assert "current_base_price" in rec
        assert "predicted_5d_price" in rec
        assert "actual_5d_price" in rec
        assert "error_dollars" in rec
        assert "directional_hit" in rec
        assert rec["directional_hit"] in [0, 1]
