"""
Tests for Wholesale RBOB Volatility Distribution Engine (Issue #448).
"""

import numpy as np
import pytest
from src.volatility_engine import (
    GARCHVolatilityModel,
    HARRVModel,
    StudentTPredictiveDistribution,
    RBOBVolatilityEngine
)


@pytest.fixture
def sample_returns():
    np.random.seed(42)
    # Generate synthetic ARCH-like heteroskedastic return series
    n = 250
    e = np.random.normal(0, 1, n)
    sigma = np.zeros(n)
    r = np.zeros(n)
    sigma[0] = 0.02
    for t in range(1, n):
        sigma[t] = np.sqrt(0.00002 + 0.10 * (r[t - 1] ** 2) + 0.85 * (sigma[t - 1] ** 2))
        r[t] = sigma[t] * e[t]
    return r


@pytest.fixture
def sample_prices(sample_returns):
    p0 = 2.45
    return p0 * np.exp(np.cumsum(sample_returns))


def test_garch_volatility_model_fitting(sample_returns):
    model = GARCHVolatilityModel(asymmetric=True)
    model.fit(sample_returns)

    assert model.is_fitted
    assert model.omega > 0
    assert 0 <= model.alpha < 1.0
    assert 0 <= model.beta < 1.0
    assert model.unconditional_variance > 0
    assert model.last_variance > 0

    # Check multi-step variance forecast path
    path = model.forecast_variance_path(horizon=5)
    assert len(path) == 5
    assert all(v > 0 for v in path)

    # Check cumulative volatility
    cum_vol = model.forecast_cumulative_volatility(horizon=5)
    assert cum_vol > 0
    assert cum_vol > np.sqrt(path[0])  # Cumulative 5-day vol should exceed 1-day step vol


def test_har_rv_model_fitting(sample_returns):
    rv_daily = sample_returns ** 2
    har = HARRVModel()
    har.fit(rv_daily)

    assert har.is_fitted
    assert har.intercept > 0
    assert har.beta_d >= 0
    assert har.beta_w >= 0
    assert har.beta_m >= 0

    path = har.forecast_variance_path(horizon=5)
    assert len(path) == 5
    assert all(v > 0 for v in path)

    cum_vol = har.forecast_cumulative_volatility(horizon=5)
    assert cum_vol > 0


def test_student_t_predictive_distribution():
    dist = StudentTPredictiveDistribution(degrees_of_freedom=5.0)

    # Compute return quantiles
    quantiles = dist.compute_quantiles(mu=0.0, cumulative_volatility=0.04)
    assert "q01" in quantiles
    assert "q50" in quantiles
    assert "q99" in quantiles
    assert quantiles["q01"] < quantiles["q50"] < quantiles["q99"]
    assert pytest.approx(quantiles["q50"], abs=1e-4) == 0.0

    # Fit degrees of freedom on standardized t residuals
    np.random.seed(42)
    residuals = np.random.standard_t(df=5, size=200)
    fitted_df = dist.fit_degrees_of_freedom(residuals)
    assert 3.5 <= fitted_df <= 15.0

    # PIT values and test
    realized = np.random.normal(0, 0.03, 100)
    vols = np.full(100, 0.03)
    pit_vals, p_val = dist.compute_pit_values(realized, vols)
    assert len(pit_vals) == 100
    assert all(0.0 <= u <= 1.0 for u in pit_vals)

    # CRPS score
    crps = dist.compute_crps(realized_return=0.015, mu=0.0, cumulative_volatility=0.03, df=6.0)
    assert crps > 0.0


def test_rbob_volatility_engine_full_term_structure(sample_prices):
    engine = RBOBVolatilityEngine(asymmetric=True)
    engine.calibrate(sample_prices)

    assert engine.is_calibrated

    res = engine.forecast_volatility_term_structure(current_price=2.50, max_horizon=5)
    assert res["current_wholesale_price"] == 2.50
    assert "horizons" in res
    assert len(res["horizons"]) == 5

    for h in range(1, 6):
        h_data = res["horizons"][f"horizon_{h}d"]
        assert h_data["horizon_days"] == h
        assert h_data["ensemble_volatility"] > 0
        assert h_data["annualized_volatility_pct"] > 0
        assert h_data["expected_price_range_90pct"][0] < h_data["expected_price_range_90pct"][1]
