"""
Tests for Edgeworth Price Cycle Diagnostics & Restoration-Hazard Model (Issue #447).
"""

import numpy as np
import pytest
from src.edgeworth_cycle import EdgeworthCycleAnalyzer, RestorationHazardModel


@pytest.fixture
def cycling_price_series():
    """Generates synthetic Edgeworth cycling prices (sharp restorations + daily undercutting)."""
    np.random.seed(42)
    prices = [3.20]
    days_since_jump = 0
    for _ in range(120):
        # Hazard increases as price falls
        margin = prices[-1] - 2.50
        spike_prob = 0.85 if (margin < 0.20 or days_since_jump > 7) else 0.05
        if np.random.rand() < spike_prob:
            jump = np.random.uniform(0.28, 0.38)
            prices.append(prices[-1] + jump)
            days_since_jump = 0
        else:
            undercut = np.random.uniform(0.015, 0.035)
            prices.append(prices[-1] - undercut)
            days_since_jump += 1
    return prices


@pytest.fixture
def non_cycling_price_series():
    """Generates standard random-walk price series."""
    np.random.seed(42)
    innovations = np.random.normal(0, 0.02, 120)
    return list(3.20 + np.cumsum(innovations))


def test_edgeworth_cycle_diagnostics_detection(cycling_price_series, non_cycling_price_series):
    analyzer = EdgeworthCycleAnalyzer(jump_threshold_cpg=0.08)

    # Test cycling series
    diag_cycling = analyzer.compute_cycle_diagnostics(cycling_price_series)
    assert diag_cycling["fraction_negative_changes"] >= 0.60
    assert diag_cycling["change_skewness"] > 0.80
    assert diag_cycling["total_restorations_detected"] >= 5
    assert diag_cycling["is_cycling"] is True

    # Test non-cycling series
    diag_non_cycling = analyzer.compute_cycle_diagnostics(non_cycling_price_series)
    assert diag_non_cycling["is_cycling"] is False
    assert diag_non_cycling["change_skewness"] < diag_cycling["change_skewness"]


def test_restoration_hazard_model_properties():
    hazard_model = RestorationHazardModel(a=-1.5, b=-4.0, c=0.25, mean_jump_size=0.30, daily_undercut_rate=-0.02)

    # 1. Margin compression increases spike probability
    p_high_margin = hazard_model.compute_restoration_probability(current_margin=0.60, elapsed_days=2, horizon_days=5)
    p_low_margin = hazard_model.compute_restoration_probability(current_margin=0.10, elapsed_days=2, horizon_days=5)
    assert p_low_margin > p_high_margin

    # 2. Longer duration since last spike increases spike probability
    p_fresh_spike = hazard_model.compute_restoration_probability(current_margin=0.30, elapsed_days=1, horizon_days=5)
    p_stale_spike = hazard_model.compute_restoration_probability(current_margin=0.30, elapsed_days=8, horizon_days=5)
    assert p_stale_spike > p_fresh_spike

    # 3. Horizon forecast trajectory
    forecast = hazard_model.forecast_expected_horizon_change(
        current_retail=3.15,
        current_wholesale=2.85,
        elapsed_days=5,
        horizon_days=5
    )
    assert forecast["current_retail"] == 3.15
    assert forecast["current_wholesale"] == 2.85
    assert 0.0 < forecast["restoration_spike_probability_5d"] < 1.0
    assert len(forecast["trajectory"]) == 5
    assert forecast["predicted_5d_retail"] > 0


def test_restoration_hazard_model_fit(cycling_price_series):
    wholesale = [2.50 + np.sin(i / 10.0) * 0.10 for i in range(len(cycling_price_series))]
    hazard_model = RestorationHazardModel()
    hazard_model.fit(cycling_price_series, wholesale)

    assert hazard_model.is_calibrated
    assert hazard_model.b <= 0.0  # Physically meaningful: compressed margin increases hazard
    assert hazard_model.c >= 0.0  # Physically meaningful: elapsed days increase hazard
    assert hazard_model.mean_jump_size > 0.10
