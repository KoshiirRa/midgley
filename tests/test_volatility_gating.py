"""
Unit & Backtesting Test Suite for Dynamic Volatility-Gated Persistence Blending (DV-GPB) (Issue #214)
"""

import pytest
import numpy as np
import pandas as pd
from unittest.mock import patch, MagicMock

from src.models import (
    compute_rolling_volatility_index,
    compute_volatility_gate_weight,
    apply_gated_persistence_blending,
    compute_empirical_residual_ci
)
from src.prediction_logger import compute_regional_residual_std
from src.dynamic_region import DynamicRegionRunner


def test_compute_rolling_volatility_index():
    # 1. Flat price series (zero daily change)
    flat_prices = np.array([3.50, 3.50, 3.50, 3.50, 3.50, 3.50, 3.50, 3.50, 3.50, 3.50, 3.50, 3.50, 3.50, 3.50, 3.50])
    vol_flat = compute_rolling_volatility_index(flat_prices, window=14)
    assert vol_flat == pytest.approx(0.0001, abs=0.001)

    # 2. High-volatility price series
    volatile_prices = np.array([3.00, 3.20, 2.90, 3.35, 3.10, 3.50, 3.20, 3.60, 3.30, 3.70, 3.40, 3.80, 3.50, 3.90, 3.60])
    vol_high = compute_rolling_volatility_index(volatile_prices, window=14)
    assert vol_high > 0.10

    # 3. Insufficient data fallback
    sparse_prices = np.array([3.50])
    vol_sparse = compute_rolling_volatility_index(sparse_prices, window=14)
    assert vol_sparse == 0.015


def test_compute_volatility_gate_weight():
    # 1. Low volatility (below threshold 0.015) -> lambda_vol -> 0.0
    lambda_low = compute_volatility_gate_weight(volatility_14d=0.001, threshold=0.015, k=200.0)
    assert lambda_low < 0.10

    # 2. Threshold volatility (0.015) -> lambda_vol = 0.50
    lambda_mid = compute_volatility_gate_weight(volatility_14d=0.015, threshold=0.015, k=200.0)
    assert lambda_mid == pytest.approx(0.50, abs=0.01)

    # 3. High volatility (above threshold 0.015) -> lambda_vol -> 1.0
    lambda_high = compute_volatility_gate_weight(volatility_14d=0.040, threshold=0.015, k=200.0)
    assert lambda_high > 0.90


def test_apply_gated_persistence_blending():
    current_base = 3.50
    raw_pred = 3.70

    # 1. Pure persistence blending (lambda_vol = 0.0)
    pred_flat = apply_gated_persistence_blending(raw_pred, current_base, lambda_vol=0.0)
    assert pred_flat == current_base

    # 2. Pure raw model blending (lambda_vol = 1.0)
    pred_shock = apply_gated_persistence_blending(raw_pred, current_base, lambda_vol=1.0)
    assert pred_shock == raw_pred

    # 3. 50/50 blending (lambda_vol = 0.5)
    pred_mid = apply_gated_persistence_blending(raw_pred, current_base, lambda_vol=0.5)
    assert pred_mid == pytest.approx(3.60, abs=0.001)

    # 4. Closed-loop guardrail active (alpha = 0.5)
    pred_guardrail = apply_gated_persistence_blending(raw_pred, current_base, lambda_vol=1.0, guardrail_active=True, guardrail_alpha=0.5)
    assert pred_guardrail == pytest.approx(3.60, abs=0.001)


def test_compute_empirical_residual_ci():
    pred_price = 3.50
    res_std = 0.05

    lower_ci, upper_ci = compute_empirical_residual_ci(pred_price, residual_std_30d=res_std, confidence_level=0.95)

    assert lower_ci == pytest.approx(3.50 - 1.96 * 0.05, abs=0.001)
    assert upper_ci == pytest.approx(3.50 + 1.96 * 0.05, abs=0.001)

    # Synthetic empirical coverage test (>= 90% coverage)
    np.random.seed(42)
    actuals = pred_price + np.random.normal(0, res_std, 1000)
    hits = (actuals >= lower_ci) & (actuals <= upper_ci)
    coverage_pct = np.mean(hits) * 100.0
    assert coverage_pct >= 90.0


def test_compute_regional_residual_std_fallback():
    # Test fallback standard deviation when no records exist
    res_std = compute_regional_residual_std(region="NonExistent_Region_12345")
    assert res_std == 0.0612


@patch("src.dynamic_region.run_national_pipeline")
def test_dynamic_region_runner_dv_gpb_integration(mock_national):
    mock_national.return_value = {
        "predicted_5d_price": 3.300,
        "current_base_price": 3.000,
        "quant_baseline_price": 3.000,
        "llm_price_pressure": 0.05,
        "llm_supply_disruption": 0.10
    }

    runner = DynamicRegionRunner("tulsa_ok")
    res = runner.run_pipeline(live_pump_price=3.500)

    assert "raw_predicted_5d_price" in res
    assert "predicted_5d_price" in res
    assert "volatility_14d" in res
    assert "gate_weight_lambda" in res
    assert "residual_std_30d" in res
    assert "prediction_lower_95ci" in res
    assert "prediction_upper_95ci" in res

    # Verify bounds are valid
    assert res["prediction_lower_95ci"] < res["predicted_5d_price"] < res["prediction_upper_95ci"]
