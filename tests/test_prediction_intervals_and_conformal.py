"""
Unit Tests for Horizon-Calibrated Prediction Intervals & Conformal Methods (tests/test_prediction_intervals_and_conformal.py)
Validates empirical residual prediction intervals, split conformal bounds, monotonic horizon scaling,
and interval evaluation quality metrics. (Issue #358)
"""

import pytest
import numpy as np
import pandas as pd

from src.models import (
    compute_empirical_residual_prediction_interval,
    compute_empirical_residual_ci,
    compute_conformal_prediction_intervals,
    evaluate_prediction_interval_quality
)
from src.prediction_logger import (
    compute_regional_residual_std
)


@pytest.fixture(autouse=True)
def setup_testing_env(monkeypatch):
    monkeypatch.setenv("TESTING", "1")


def test_empirical_residual_prediction_interval_calculation():
    """Validates point forecast interval bounds and default std scaling."""
    pred = 3.500
    res_std = 0.060

    low, high = compute_empirical_residual_prediction_interval(pred, residual_std_30d=res_std, confidence_level=0.95)
    expected_low = round(3.500 - (1.96 * 0.060), 4)
    expected_high = round(3.500 + (1.96 * 0.060), 4)

    assert low == expected_low
    assert high == expected_high
    assert high > low

    # Check 90% confidence level
    low_90, high_90 = compute_empirical_residual_prediction_interval(pred, residual_std_30d=res_std, confidence_level=0.90)
    assert low_90 > low
    assert high_90 < high


def test_compute_empirical_residual_ci_alias():
    """Validates that legacy alias returns identical results to prediction interval function."""
    pred = 3.250
    res_std = 0.055

    low1, high1 = compute_empirical_residual_prediction_interval(pred, residual_std_30d=res_std)
    low2, high2 = compute_empirical_residual_ci(pred, residual_std_30d=res_std)

    assert low1 == low2
    assert high1 == high2


def test_conformal_prediction_intervals():
    """Validates split conformal interval calibration with nonconformity scores."""
    preds = np.array([3.00, 3.20, 3.50, 3.80])
    # Synthetic calibration residuals with known spread
    residuals = np.array([0.02, -0.04, 0.05, -0.01, 0.03, -0.06, 0.08, -0.02, 0.01, -0.05])

    low_bounds, high_bounds = compute_conformal_prediction_intervals(preds, residuals, alpha=0.10)

    assert len(low_bounds) == len(preds)
    assert len(high_bounds) == len(preds)
    assert (high_bounds > low_bounds).all()

    # All interval widths should be uniform and equal to 2 * quantile
    widths = high_bounds - low_bounds
    assert np.allclose(widths, widths[0], atol=1e-4)


def test_evaluate_prediction_interval_quality():
    """Validates interval evaluation quality metrics (empirical coverage, mean width, pinball loss)."""
    np.random.seed(42)
    actuals = np.array([3.10, 3.25, 3.48, 3.85, 3.02, 3.65, 3.90, 3.30, 3.40, 3.55])
    preds = actuals + np.random.normal(0, 0.04, len(actuals))

    low_bounds = preds - 0.10
    high_bounds = preds + 0.10

    metrics = evaluate_prediction_interval_quality(actuals, low_bounds, high_bounds, nominal_confidence=0.95)

    assert metrics["nominal_coverage"] == 0.95
    assert metrics["sample_size"] == 10
    assert metrics["empirical_coverage_pct"] >= 80.0
    assert metrics["mean_interval_width"] == 0.20
    assert metrics["pinball_loss_lower"] >= 0.0
    assert metrics["pinball_loss_upper"] >= 0.0
    assert metrics["status"] == "VALID"


def test_regional_residual_std_horizon_scaling():
    """Validates that residual std scales monotonically with horizon on fallback and returns positive values."""
    # 1. Unobserved region should scale monotonically via sqrt(h / 5.0)
    fallback_1d = compute_regional_residual_std(region="Unseen_Test_Region", default_std=0.0612, horizon_days=1)
    fallback_3d = compute_regional_residual_std(region="Unseen_Test_Region", default_std=0.0612, horizon_days=3)
    fallback_5d = compute_regional_residual_std(region="Unseen_Test_Region", default_std=0.0612, horizon_days=5)

    assert fallback_1d < fallback_3d < fallback_5d
    assert fallback_1d > 0.0
    assert np.isclose(fallback_5d, 0.0612, atol=1e-3)

    # 2. Real region returns positive horizon-specific std
    std_1d = compute_regional_residual_std(region="National", horizon_days=1)
    std_5d = compute_regional_residual_std(region="National", horizon_days=5)
    assert std_1d > 0.0
    assert std_5d > 0.0
