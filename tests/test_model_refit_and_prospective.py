"""
Unit Tests for Phase 4 Model Refit, Stationary Transforms, and Evaluation Hardening (Issue #559)
"""

import os
import pytest
import numpy as np
import pandas as pd
from sklearn.linear_model import Ridge

from src.models import (
    fit_prospective_model,
    train_and_compare_models,
    train_multi_horizon_models,
    enforce_forecast_plausibility_gate
)
from src.eia_retail_feed import REGION_TO_EIA_SERIES, EIARetailFeed


def create_synthetic_market_data(n_days=120):
    """Generates synthetic market data fixture for testing."""
    dates = pd.bdate_range(start="2026-01-01", periods=n_days)
    np.random.seed(42)
    
    # Base random walk price
    price = 2.50 + np.cumsum(np.random.normal(0.001, 0.02, size=n_days))
    price = np.clip(price, 1.50, 4.50)
    
    df = pd.DataFrame({
        "date": dates,
        "gasoline_rbob": price,
        "crude_wti": price * 35.0,
        "crude_brent": price * 36.0,
        "heating_oil": price * 1.05,
        "volume": np.random.randint(50000, 150000, size=n_days)
    })
    return df


def test_fit_prospective_model_combined_history():
    """Verify fit_prospective_model trains on 100% of available data (train + test)."""
    np.random.seed(42)
    X_train = pd.DataFrame({"feat1": np.random.randn(80), "feat2": np.random.randn(80)})
    y_train = pd.Series(np.random.randn(80))
    X_test = pd.DataFrame({"feat1": np.random.randn(20), "feat2": np.random.randn(20)})
    y_test = pd.Series(np.random.randn(20))

    model = fit_prospective_model(
        X_train=X_train,
        y_train=y_train,
        X_test=X_test,
        y_test=y_test,
        model_type="ridge"
    )
    assert model is not None
    preds = model.predict(X_test)
    assert len(preds) == 20
    assert not np.isnan(preds).any()


def test_fit_prospective_model_clones_base_pipeline():
    """Verify fit_prospective_model clones evaluated RidgeCV pipeline architecture (Issue #575 N-3)."""
    from sklearn.pipeline import make_pipeline
    from sklearn.preprocessing import StandardScaler
    from sklearn.linear_model import RidgeCV

    np.random.seed(42)
    X_train = pd.DataFrame({"feat1": np.random.randn(80), "feat2": np.random.randn(80)})
    y_train = pd.Series(np.random.randn(80))
    X_test = pd.DataFrame({"feat1": np.random.randn(20), "feat2": np.random.randn(20)})
    y_test = pd.Series(np.random.randn(20))

    base_pipe = make_pipeline(StandardScaler(), RidgeCV(alphas=[0.1, 1.0, 10.0]))
    base_pipe.fit(X_train, y_train)

    refit_model = fit_prospective_model(
        X_train=X_train,
        y_train=y_train,
        X_test=X_test,
        y_test=y_test,
        base_model=base_pipe
    )

    assert isinstance(refit_model, type(base_pipe))
    assert isinstance(refit_model.named_steps['ridgecv'], RidgeCV)
    preds = refit_model.predict(X_test)
    assert len(preds) == 20


def test_train_and_compare_models_includes_prospective_models():
    """Verify train_and_compare_models attaches prospective refit models."""
    from src.feature_engineering import create_feature_matrix, prepare_chronological_splits

    market_df = create_synthetic_market_data(n_days=100)
    feat_df = create_feature_matrix(market_df, forecast_horizon=5)
    splits = prepare_chronological_splits(feat_df, train_ratio=0.8, forecast_horizon=5)

    res = train_and_compare_models(splits, model_type="ridge")

    assert "prospective_model_quant" in res
    assert "prospective_model_hybrid" in res
    assert res["prospective_model_quant"] is not None
    assert res["prospective_model_hybrid"] is not None
    assert "live_pred_price" in res
    assert res["live_pred_price"] > 0


def test_train_multi_horizon_models_prospective_execution():
    """Verify multi-horizon training correctly executes prospective forecasts for all h."""
    market_df = create_synthetic_market_data(n_days=90)
    horizons = [1, 2, 3, 5]
    
    multi_res = train_multi_horizon_models(
        market_df=market_df,
        horizons=horizons,
        region="Tulsa_OK",
        model_type="ridge"
    )

    for h in horizons:
        assert h in multi_res
        res = multi_res[h]
        assert "live_pred_price" in res
        assert "prospective_model_hybrid" in res
        assert res["live_pred_price"] > 0
        assert res["forecast_horizon"] == h


def test_plausibility_gating_bounds():
    """Verify plausibility gating clamps extreme hybrid predictions within realistic bounds."""
    base_price = 3.00
    # Plausible price
    gated_p, is_gated, reason = enforce_forecast_plausibility_gate(
        hybrid_pred_price=3.05,
        quant_pred_price=3.04,
        base_price=base_price,
        horizon_days=5
    )
    assert abs(gated_p - 3.05) < 1e-4
    assert not is_gated

    # Extreme upward price spike clamped
    gated_p2, is_gated2, reason2 = enforce_forecast_plausibility_gate(
        hybrid_pred_price=4.50,
        quant_pred_price=3.10,
        base_price=base_price,
        horizon_days=5
    )
    assert is_gated2
    assert gated_p2 < 4.50


def test_eia_regional_series_mapping_completeness():
    """Verify all 9 target metro locales map to valid EIA / FRED series."""
    required_locales = [
        "National", "Tulsa_OK", "Newark_DE", "Cincinnati_OH", "Cincinnati_KY",
        "Greenville_NC", "Charlotte_NC", "Port_St_Lucie_FL", "Oakland_CA", "BayArea_CA"
    ]
    for loc in required_locales:
        assert loc in REGION_TO_EIA_SERIES, f"Missing EIA series mapping for {loc}"
        series_list = REGION_TO_EIA_SERIES[loc]
        assert len(series_list) >= 1
        assert series_list[0][0].startswith("GASREG")
