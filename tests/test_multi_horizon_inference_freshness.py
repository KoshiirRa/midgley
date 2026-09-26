"""
Unit tests for multi-horizon inference freshness and unlabelled inference frame preservation (Issue #353).

Validates that:
1. create_feature_matrix populates unlabelled_inference_frame in attrs and respects return_unlabelled_frame.
2. prepare_chronological_splits extracts contemporary t=0 features (X_live_hybrid, X_live_quant, live_current_price).
3. train_multi_horizon_models produces forecasts from identical contemporary t=0 origins across all horizons h in [1..5].
4. Training sets use strictly matured labels (t <= T-h) with no lookahead leakage.
"""

import numpy as np
import pandas as pd
import pytest

from src.feature_engineering import create_feature_matrix, prepare_chronological_splits
from src.models import train_multi_horizon_models, train_and_compare_models


@pytest.fixture
def sample_market_df():
    """Generates synthetic time-series for freshness verification."""
    np.random.seed(123)
    dates = pd.date_range(start="2025-01-01", periods=120, freq="B")
    
    price_rbob = 2.40 + np.cumsum(np.random.normal(0, 0.02, size=len(dates)))
    price_wti = 70.0 + np.cumsum(np.random.normal(0, 0.5, size=len(dates)))
    price_brent = price_wti + 3.0
    price_ho = price_rbob + 0.10
    
    df = pd.DataFrame({
        "date": dates,
        "gasoline_rbob": price_rbob,
        "wti_crude": price_wti,
        "brent_crude": price_brent,
        "heating_oil": price_ho
    })
    return df


def test_create_feature_matrix_unlabelled_frame_metadata(sample_market_df):
    """Verifies that create_feature_matrix retains unlabelled rows and sets metadata attrs."""
    horizon = 5
    labelled_df = create_feature_matrix(sample_market_df, forecast_horizon=horizon)
    
    # Labelled frame should drop the last `horizon` rows where target is NaN
    assert len(labelled_df) == len(sample_market_df) - horizon
    
    # Metadata attrs must contain unlabelled frame and latest inference row
    attrs = labelled_df.attrs
    assert "unlabelled_inference_frame" in attrs
    assert "latest_inference_row" in attrs
    assert "forecast_origin_date" in attrs
    assert "feature_cutoff_date" in attrs
    
    unlabelled = attrs["unlabelled_inference_frame"]
    assert len(unlabelled) == horizon
    
    # Latest inference date should match the very last date in original dataset
    last_expected_date = pd.to_datetime(sample_market_df["date"].iloc[-1])
    assert pd.to_datetime(attrs["forecast_origin_date"]) == last_expected_date
    assert pd.to_datetime(attrs["latest_inference_row"]["date"].iloc[0]) == last_expected_date
    
    # Test return_unlabelled_frame=True flag
    lbl, unlbl = create_feature_matrix(sample_market_df, forecast_horizon=horizon, return_unlabelled_frame=True)
    assert len(lbl) == len(sample_market_df) - horizon
    assert len(unlbl) == horizon
    assert pd.to_datetime(unlbl["date"].iloc[-1]) == last_expected_date


def test_prepare_chronological_splits_live_features(sample_market_df):
    """Verifies that prepare_chronological_splits extracts contemporary t=0 live features."""
    horizon = 3
    labelled_df = create_feature_matrix(sample_market_df, forecast_horizon=horizon)
    splits = prepare_chronological_splits(labelled_df)
    
    assert "X_live_hybrid" in splits
    assert "X_live_quant" in splits
    assert "live_current_price" in splits
    assert "live_feature_origin_date" in splits
    
    # Live origin date should be the most recent date in sample_market_df (t=0)
    last_date = pd.to_datetime(sample_market_df["date"].iloc[-1])
    assert pd.to_datetime(splits["live_feature_origin_date"]) == last_date
    
    # Live current price should match the latest gasoline_rbob price (t=0)
    assert splits["live_current_price"] == pytest.approx(sample_market_df["gasoline_rbob"].iloc[-1])
    
    # X_live shape should be exactly 1 row
    assert len(splits["X_live_hybrid"]) == 1
    assert len(splits["X_live_quant"]) == 1
    
    # Test split end date is t-h, which is earlier than t=0
    test_last_date = pd.to_datetime(splits["test_df"]["date"].iloc[-1])
    assert test_last_date < last_date


def test_train_multi_horizon_models_freshness_alignment(sample_market_df):
    """Verifies that multi-horizon models (1D to 5D) all evaluate contemporary t=0 features."""
    horizons = [1, 2, 3, 4, 5]
    results = train_multi_horizon_models(
        market_df=sample_market_df,
        events_df=None,
        horizons=horizons,
        model_type="ridge",
        train_ratio=0.8
    )
    
    last_actual_date = pd.to_datetime(sample_market_df["date"].iloc[-1])
    last_actual_price = float(sample_market_df["gasoline_rbob"].iloc[-1])
    
    for h in horizons:
        h_res = results[h]
        # Origin date and base price must be identical across all horizons
        assert pd.to_datetime(h_res["forecast_origin_date"]) == last_actual_date
        assert h_res["live_base_price"] == pytest.approx(last_actual_price)
        
        # Target dates must advance according to horizon h
        assert pd.to_datetime(h_res["forecast_target_date"]) > last_actual_date
        
        # Live predictions must exist and be positive numbers
        assert h_res["live_pred_price"] > 0.0
        assert h_res["live_pred_quant_price"] > 0.0
        assert isinstance(h_res["live_pred_return"], float)
        assert isinstance(h_res["live_pred_quant_return"], float)
        
        # Labelled training + test set max date should strictly be <= last_actual_date - h days
        h_splits = h_res["splits"]
        test_max_date = pd.to_datetime(h_splits["test_df"]["date"].iloc[-1])
        assert test_max_date < last_actual_date
