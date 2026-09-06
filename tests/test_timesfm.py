"""
Unit tests for Google TimesFM Foundation Model Integration & Zero-Shot Benchmarking (Issues #185 & #112).
"""

import pytest
import numpy as np
import pandas as pd
from src.timesfm_forecaster import TimesFMForecaster, AnalyticalZeroShotFallback, HAS_TIMESFM
from src.models import (
    evaluate_timesfm_zero_shot_benchmarks,
    train_and_compare_models,
    PurgedGroupTimeSeriesSplit
)


@pytest.fixture
def sample_timeseries_data():
    """Generates synthetic time series dataset for testing."""
    np.random.seed(42)
    n_samples = 100
    dates = pd.date_range(start="2026-01-01", periods=n_samples, freq="D")
    
    # RBOB crude futures trend + noise
    base_price = 2.50 + np.cumsum(np.random.normal(0.005, 0.02, n_samples))
    
    df = pd.DataFrame({
        "date": dates,
        "gasoline_rbob": base_price,
        "gas_ma_7": pd.Series(base_price).rolling(5, min_periods=1).mean(),
        "feature_1": np.random.normal(0, 1, n_samples),
        "feature_2": np.random.normal(0, 1, n_samples),
        "event_sentiment": np.random.normal(0.1, 0.5, n_samples)
    })
    
    X_quant = df[["feature_1", "feature_2"]]
    X_hybrid = df[["feature_1", "feature_2", "event_sentiment"]]
    y = df["gasoline_rbob"] + np.random.normal(0, 0.01, n_samples)
    
    split_idx = 80
    split_data = {
        "X_train_quant": X_quant.iloc[:split_idx],
        "X_test_quant": X_quant.iloc[split_idx:],
        "X_train_hybrid": X_hybrid.iloc[:split_idx],
        "X_test_hybrid": X_hybrid.iloc[split_idx:],
        "y_train": y.iloc[:split_idx],
        "y_test": y.iloc[split_idx:],
        "test_df": df.iloc[split_idx:].copy(),
        "hybrid_feature_names": list(X_hybrid.columns)
    }
    
    return split_data


def test_analytical_fallback_forecast():
    """Tests AnalyticalZeroShotFallback point forecasts and quantile bounds."""
    fallback = AnalyticalZeroShotFallback(horizon_len=5)
    history = pd.Series([2.10, 2.12, 2.15, 2.14, 2.18])
    
    result = fallback.forecast(history)
    assert "pred" in result
    assert "p10" in result
    assert "p50" in result
    assert "p90" in result
    
    assert len(result["pred"]) == 5
    assert len(result["p10"]) == 5
    assert len(result["p90"]) == 5
    
    # Check quantile monotonicity: p10 <= p50 <= p90
    assert np.all(result["p10"] <= result["p50"])
    assert np.all(result["p50"] <= result["p90"])


def test_timesfm_forecaster_status_and_load():
    """Tests TimesFMForecaster initialization and model status retrieval."""
    forecaster = TimesFMForecaster(horizon_len=5)
    status = forecaster.get_model_status()
    
    assert "has_timesfm_pkg" in status
    assert "using_fallback" in status
    assert status["horizon_len"] == 5
    
    loaded = forecaster.load_model()
    # Should complete without error regardless of HAS_TIMESFM
    assert isinstance(loaded, bool)


def test_timesfm_forecaster_zero_shot_and_sklearn_api(sample_timeseries_data):
    """Tests TimesFMForecaster fit, predict, and zero-shot forecasting APIs."""
    split_data = sample_timeseries_data
    X_train = split_data["X_train_quant"]
    y_train = split_data["y_train"]
    X_test = split_data["X_test_quant"]
    
    forecaster = TimesFMForecaster(horizon_len=len(X_test))
    forecaster.fit(X_train, y_train)
    
    preds = forecaster.predict(X_test)
    assert isinstance(preds, np.ndarray)
    assert len(preds) == len(X_test)
    assert not np.isnan(preds).any()
    
    zero_shot_res = forecaster.forecast_zero_shot(y_train.values, horizon_len=5)
    assert len(zero_shot_res["pred"]) == 5
    assert np.all(zero_shot_res["p10"] <= zero_shot_res["p90"])


def test_train_and_compare_models_with_timesfm(sample_timeseries_data):
    """Tests train_and_compare_models integration using model_type='timesfm'."""
    split_data = sample_timeseries_data
    results = train_and_compare_models(split_data, model_type="timesfm")
    
    assert "metrics_quant" in results
    assert "metrics_hybrid" in results
    assert "predictions_quant" in results
    assert len(results["predictions_quant"]) == len(split_data["y_test"])
    assert results["metrics_quant"]["MAE"] >= 0.0


def test_evaluate_timesfm_zero_shot_benchmarks(sample_timeseries_data):
    """Tests evaluate_timesfm_zero_shot_benchmarks function output."""
    split_data = sample_timeseries_data
    res = evaluate_timesfm_zero_shot_benchmarks(split_data)
    
    assert res["status"] == "success"
    assert "benchmarks" in res
    assert "timesfm_zero_shot" in res["benchmarks"]
    assert "persistence" in res["benchmarks"]
    assert "ridge" in res["benchmarks"]
    assert "stacking" in res["benchmarks"]
    
    assert "rankings" in res
    assert len(res["rankings"]) >= 4
    assert isinstance(res["timesfm_uplift_over_persistence_pct"], float)


def test_timesfm_with_purged_cv(sample_timeseries_data):
    """Tests TimesFMForecaster within PurgedGroupTimeSeriesSplit cross-validation."""
    split_data = sample_timeseries_data
    X = np.concatenate([split_data["X_train_quant"], split_data["X_test_quant"]])
    y = np.concatenate([split_data["y_train"], split_data["y_test"]])
    
    splitter = PurgedGroupTimeSeriesSplit(n_splits=3, label_horizon_steps=2, embargo_steps=2)
    forecaster = TimesFMForecaster(horizon_len=5)
    
    fold_count = 0
    for train_idx, test_idx in splitter.split(X, y):
        X_tr, y_tr = X[train_idx], y[train_idx]
        X_te = X[test_idx]
        
        forecaster.fit(X_tr, y_tr)
        preds = forecaster.predict(X_te)
        assert len(preds) == len(X_te)
        fold_count += 1
        
    assert fold_count == 3
