"""Unit tests for Asymmetric Error-Correction Model (AsymmetricECM).

Tests cointegration equilibrium estimation, error-correction decomposition (rockets & feathers),
recursive multi-step ahead forecasting, and asymmetry diagnostics.
"""

import numpy as np
import pandas as pd
import pytest

from src.asymmetric_ecm import AsymmetricECM, fit_regional_asymmetric_ecm


@pytest.fixture
def synthetic_pass_through_data():
    """Generate synthetic wholesale and retail series with known asymmetric pass-through."""
    np.random.seed(42)
    n = 200
    dates = pd.date_range(start="2024-01-01", periods=n, freq="D")
    
    # Wholesale random walk
    wholesale_shocks = np.random.normal(0, 0.05, size=n)
    wholesale = 2.0 + np.cumsum(wholesale_shocks)
    
    # Equilibrium: retail = 1.05 * wholesale + 0.85
    beta = 1.05
    rack_spread = 0.85
    
    retail = np.zeros(n)
    retail[0] = beta * wholesale[0] + rack_spread
    
    # Rockets and feathers: alpha_neg (retail margin squeezed, retail too low) adjustment is faster (-0.35)
    # alpha_pos (retail margin fat, retail too high) adjustment is slower (-0.15)
    alpha_pos = -0.15
    alpha_neg = -0.35
    
    for t in range(1, n):
        # Equilibrium error from previous day
        z_prev = retail[t - 1] - (beta * wholesale[t - 1] + rack_spread)
        z_pos = max(0.0, z_prev)
        z_neg = min(0.0, z_prev)
        
        delta_w = wholesale[t] - wholesale[t - 1]
        delta_r = (
            alpha_pos * z_pos
            + alpha_neg * z_neg
            + 0.5 * delta_w
            + 0.1 * (retail[t - 1] - retail[t - 2] if t > 1 else 0.0)
            + np.random.normal(0, 0.01)
        )
        retail[t] = retail[t - 1] + delta_r

    return pd.DataFrame({
        "wholesale_price": wholesale,
        "retail_price": retail,
    }, index=dates)


def test_asymmetric_ecm_initialization():
    """Test model initialization with custom and default parameters."""
    ecm = AsymmetricECM(wholesale_lags=3, retail_lags=2)
    assert ecm.wholesale_lags == 3
    assert ecm.retail_lags == 2
    assert not ecm.is_fitted


def test_asymmetric_ecm_fit_and_diagnostics(synthetic_pass_through_data):
    """Test model fitting, cointegration estimation, and asymmetry metrics."""
    ecm = AsymmetricECM(wholesale_lags=2, retail_lags=1)
    ecm.fit(synthetic_pass_through_data, wholesale_col="wholesale_price", retail_col="retail_price")
    
    assert ecm.is_fitted
    assert ecm.beta is not None
    assert ecm.rack_spread is not None
    assert 0.90 <= ecm.beta <= 1.20
    assert 0.70 <= ecm.rack_spread <= 1.00
    
    # Verify rockets-and-feathers asymmetry is detected
    diag = ecm.get_asymmetry_diagnostics()
    assert "alpha_pos" in diag
    assert "alpha_neg" in diag
    assert "speed_ratio" in diag
    assert "rockets_and_feathers" in diag
    assert diag["alpha_pos"] < 0
    assert diag["alpha_neg"] < 0
    # Negative error correction should be faster than positive
    assert abs(diag["alpha_neg"]) > abs(diag["alpha_pos"])
    assert diag["speed_ratio"] > 1.0
    assert diag["rockets_and_feathers"] is True


def test_asymmetric_ecm_predict_step_ahead(synthetic_pass_through_data):
    """Test 1 to 5 day forward predictions with realistic bounded outputs."""
    ecm = AsymmetricECM(wholesale_lags=2, retail_lags=1)
    ecm.fit(synthetic_pass_through_data, wholesale_col="wholesale_price", retail_col="retail_price")
    
    # 5-day constant future wholesale scenario
    last_wholesale = synthetic_pass_through_data["wholesale_price"].iloc[-1]
    future_wholesale = [last_wholesale + 0.05 * i for i in range(1, 6)]
    
    preds = ecm.predict_step_ahead(synthetic_pass_through_data, future_wholesale, steps=5)
    
    assert len(preds) == 5
    assert not preds.isna().any()
    # Predictions should be reasonable retail price levels (> $2.00)
    assert (preds > 2.0).all()
    assert (preds < 10.0).all()


def test_fit_regional_asymmetric_ecm_helper(synthetic_pass_through_data):
    """Test regional convenience wrapper."""
    model, diag = fit_regional_asymmetric_ecm(
        synthetic_pass_through_data,
        region_name="Tulsa_OK",
        wholesale_col="wholesale_price",
        retail_col="retail_price",
    )
    assert model.is_fitted
    assert diag["region"] == "Tulsa_OK"
    assert "beta" in diag
    assert "rack_spread" in diag
