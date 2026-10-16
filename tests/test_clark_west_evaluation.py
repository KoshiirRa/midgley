"""
Unit Tests for Clark-West Test and Multiplicity Control (tests/test_clark_west_evaluation.py)
Validates Issue #567: Clark-West (2007) nested model test, Holm-Bonferroni, Benjamini-Hochberg, and 5-tier hierarchy.
"""

import numpy as np
import pandas as pd
import pytest
from src.model_evaluation import (
    clark_west_test,
    adjust_pvalues_holm_bonferroni,
    adjust_pvalues_benjamini_hochberg,
    ModelHierarchyEvaluator
)


def test_clark_west_test_synthetic():
    np.random.seed(42)
    n = 100
    y_true = np.random.normal(3.0, 0.2, n)
    # Nested model (noisier)
    y_pred_nested = y_true + np.random.normal(0, 0.15, n)
    # Full model (more accurate)
    y_pred_full = y_true + np.random.normal(0, 0.05, n)

    cw_stat, p_val = clark_west_test(y_true, y_pred_nested, y_pred_full, horizon=1)
    
    assert isinstance(cw_stat, float)
    assert isinstance(p_val, float)
    assert 0.0 <= p_val <= 1.0
    assert cw_stat > 0  # Full model is better


def test_multiplicity_adjustments():
    raw_p = [0.005, 0.03, 0.04, 0.12]
    
    holm = adjust_pvalues_holm_bonferroni(raw_p)
    bh = adjust_pvalues_benjamini_hochberg(raw_p)
    
    assert len(holm) == len(raw_p)
    assert len(bh) == len(raw_p)
    
    # All adjusted p-values must be >= raw p-values and <= 1.0
    for r, h, b in zip(raw_p, holm, bh):
        assert h >= r
        assert b >= r
        assert h <= 1.0
        assert b <= 1.0


def test_5tier_hierarchy_evaluation():
    np.random.seed(42)
    n_train, n_test = 80, 20
    
    # Create feature matrix
    cols = ["lag_1", "rsi_14", "eia_inventory", "weather_cdd", "event_shock_score", "extra_feat"]
    X_train = pd.DataFrame(np.random.randn(n_train, len(cols)), columns=cols)
    X_test = pd.DataFrame(np.random.randn(n_test, len(cols)), columns=cols)
    
    y_train_curr = pd.Series(np.random.normal(3.2, 0.1, n_train))
    y_train_fut = y_train_curr + 0.05 * X_train["lag_1"] + 0.02 * X_train["event_shock_score"]
    
    y_test_curr = pd.Series(np.random.normal(3.2, 0.1, n_test))
    y_test_fut = y_test_curr + 0.05 * X_test["lag_1"] + 0.02 * X_test["event_shock_score"]
    
    evaluator = ModelHierarchyEvaluator(region="Test_Region")
    res = evaluator.evaluate_5tier_hierarchy(
        X_train=X_train,
        y_train_future=y_train_fut,
        y_train_current=y_train_curr,
        X_test=X_test,
        y_test_future=y_test_fut,
        y_test_current=y_test_curr,
        horizon=1
    )
    
    assert "tiers" in res
    assert "Tier_0_Naive" in res["tiers"]
    assert "Tier_1_Price_Only" in res["tiers"]
    assert "Tier_4_Full_Hybrid" in res["tiers"]
    
    t4 = res["tiers"]["Tier_4_Full_Hybrid"]
    assert "cw_stat_vs_prev" in t4
    assert "cw_p_value_holm" in t4
    assert "cw_p_value_bh" in t4
