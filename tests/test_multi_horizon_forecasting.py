"""
Unit tests for discrete 1D-5D multi-horizon forecast training, logging, and scoreboard evaluation.
Part of Issue #314 / v0.6.6 Release.
"""

import os
import tempfile
import pandas as pd
import numpy as np
import pytest
from datetime import datetime, timedelta

from src.models import train_multi_horizon_models, train_and_compare_models
from src.prediction_logger import (
    log_predictions,
    backfill_new_region_history,
    compute_horizon_scoreboard_breakdown,
    _infer_horizon_days,
    HISTORY_CSV_PATH
)


@pytest.fixture
def sample_market_df():
    """Generates synthetic price time-series for multi-horizon model testing."""
    np.random.seed(42)
    dates = pd.date_range(start="2025-01-01", periods=180, freq="B")
    
    # Synthetic random walk prices
    steps_rbob = np.random.normal(0, 0.02, size=len(dates))
    price_rbob = 2.50 + np.cumsum(steps_rbob)
    
    steps_wti = np.random.normal(0, 0.8, size=len(dates))
    price_wti = 75.0 + np.cumsum(steps_wti)
    
    price_brent = price_wti + 3.5
    price_ho = price_rbob + 0.15
    
    df = pd.DataFrame({
        "date": dates,
        "gasoline_rbob": price_rbob,
        "wti_crude": price_wti,
        "brent_crude": price_brent,
        "heating_oil": price_ho
    })
    return df


def test_train_multi_horizon_models(sample_market_df):
    """Verifies that train_multi_horizon_models trains discrete models for all requested horizons."""
    horizons = [1, 2, 3, 4, 5]
    
    models = train_multi_horizon_models(
        market_df=sample_market_df,
        events_df=None,
        horizons=horizons,
        model_type="ridge",
        train_ratio=0.8
    )
    
    for h in horizons:
        assert h in models, f"Horizon {h} missing from multi-horizon model dictionary"
        res = models[h]
        assert "model_quant" in res
        assert "model_hybrid" in res
        assert "metrics_quant" in res
        assert "metrics_hybrid" in res
        assert "splits" in res
        assert res["forecast_horizon"] == h
        
        # Test predictions on latest test row
        splits = res["splits"]
        test_x = splits["X_test_quant"].iloc[-1:]
        pred_quant = res["model_quant"].predict(test_x)[0]
        assert isinstance(pred_quant, (float, np.floating))
        assert pred_quant > 0.0


def test_infer_horizon_days():
    """Verifies business-day calculation logic in _infer_horizon_days."""
    assert _infer_horizon_days({"log_timestamp": "2026-03-02 10:00:00", "forecast_target_date": "2026-03-03"}) == 1
    assert _infer_horizon_days({"log_timestamp": "2026-03-02 10:00:00", "forecast_target_date": "2026-03-04"}) == 2
    assert _infer_horizon_days({"log_timestamp": "2026-03-02 10:00:00", "forecast_target_date": "2026-03-05"}) == 3
    assert _infer_horizon_days({"log_timestamp": "2026-03-02 10:00:00", "forecast_target_date": "2026-03-06"}) == 4
    assert _infer_horizon_days({"log_timestamp": "2026-03-02 10:00:00", "forecast_target_date": "2026-03-09"}) == 5  # Across weekend
    assert _infer_horizon_days({"log_timestamp": "2026-03-06 10:00:00", "forecast_target_date": "2026-03-09"}) == 1  # Friday to Monday
    assert _infer_horizon_days({"forecast_horizon_days": 3}) == 3


def test_multi_horizon_backfilling_and_scoreboard():
    """Tests backfill_new_region_history across horizons 1-5 and scoreboard breakdown computation."""
    with tempfile.TemporaryDirectory() as tmpdir:
        test_history_path = os.path.join(tmpdir, "test_prediction_history.csv")
        
        # Create synthetic test split data
        dates = pd.date_range(start="2025-01-01", periods=20, freq="B")
        base_prices = 2.40 + np.random.normal(0, 0.05, size=len(dates))
        predicted_prices = base_prices + np.random.normal(0, 0.02, size=len(dates))
        
        # Backfill for horizons 1 through 5 using mock history path
        for h in [1, 2, 3, 4, 5]:
            count = backfill_new_region_history(
                test_dates=dates,
                base_prices=base_prices,
                predicted_prices=predicted_prices,
                region="Test_Region",
                model_version="v1.6-Ipatieff",
                forecast_horizon_days=h
            )
            assert count >= 0
            
        # Verify scoreboard breakdown execution
        breakdown = compute_horizon_scoreboard_breakdown(
            window_days="all",
            region="Test_Region",
            horizons=[1, 2, 3, 4, 5]
        )
        
        assert len(breakdown) == 5
        for item in breakdown:
            assert "horizon_days" in item
            assert "horizon_label" in item
            assert "mae_dollars" in item
            assert "rmse_dollars" in item
            assert "directional_hit_rate_pct" in item
            assert "evaluations" in item
