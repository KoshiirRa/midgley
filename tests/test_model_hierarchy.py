"""
Unit Test Suite for 5-Tier Model Hierarchy & Statistical Gating (tests/test_model_hierarchy.py)
Tests Diebold-Mariano hypothesis testing, Stationary Block Bootstrap, and 5-Tier Evaluator. (Issue #362)
"""

import pytest
import numpy as np
import pandas as pd
from src.model_evaluation import (
    diebold_mariano_test,
    stationary_block_bootstrap,
    compute_pinball_loss,
    ModelHierarchyEvaluator
)
from scripts.evaluate_model_hierarchy import run_full_hierarchy_audit


def test_diebold_mariano_test():
    np.random.seed(42)
    # Model 2 has significantly lower errors than Model 1
    e1 = np.random.normal(0.05, 0.02, 60)
    e2 = np.random.normal(0.01, 0.01, 60)

    dm_stat, p_val = diebold_mariano_test(e1, e2, horizon=1)
    assert dm_stat > 0.0
    assert p_val < 0.05

    # Equal errors should yield high p-value
    dm_stat_eq, p_val_eq = diebold_mariano_test(e1, e1, horizon=1)
    assert p_val_eq == 1.0


def test_stationary_block_bootstrap():
    np.random.seed(42)
    e1 = np.random.normal(0.04, 0.01, 50)
    e2 = np.random.normal(0.02, 0.01, 50)

    res = stationary_block_bootstrap(e1, e2, n_bootstraps=200)
    assert "mae_diff_mean" in res
    assert "ci_lower_95" in res
    assert "ci_upper_95" in res
    assert "p_value_bootstrap" in res
    assert res["mae_diff_mean"] > 0.0


def test_pinball_loss():
    y_true = np.array([2.5, 3.0, 3.5])
    y_pred = np.array([2.4, 3.0, 3.6])
    loss = compute_pinball_loss(y_true, y_pred, quantile=0.5)
    assert loss > 0.0


def test_5tier_hierarchy_evaluator():
    np.random.seed(42)
    n = 80
    X = pd.DataFrame({
        "rbob_lag1": np.linspace(2.5, 3.2, n),
        "rsi_14": np.random.uniform(30, 70, n),
        "eia_stocks": np.random.normal(200, 5, n),
        "geopolitical_risk": np.random.exponential(0.1, n)
    })
    y_curr = X["rbob_lag1"]
    y_fut = y_curr + 0.03 * X["geopolitical_risk"] + np.random.normal(0, 0.01, n)

    evaluator = ModelHierarchyEvaluator(region="National")
    res = evaluator.evaluate_5tier_hierarchy(
        X.iloc[:50], y_fut.iloc[:50], y_curr.iloc[:50],
        X.iloc[50:], y_fut.iloc[50:], y_curr.iloc[50:],
        horizon=5
    )

    assert "region" in res
    assert res["region"] == "National"
    assert "tiers" in res
    assert "Tier_0_Naive" in res["tiers"]
    assert "Tier_1_Price_Only" in res["tiers"]
    assert "Tier_2_Physical_Fundamentals" in res["tiers"]
    assert "Tier_3_Qualitative_Events" in res["tiers"]
    assert "Tier_4_Full_Hybrid" in res["tiers"]


def test_evaluate_model_hierarchy_script(tmp_path):
    summary = run_full_hierarchy_audit(horizons=[1, 5], output_dir=str(tmp_path), use_synthetic_fallback=True)
    assert summary["total_regions_evaluated"] == 10
    assert summary["passed_regions_count"] >= 8
    assert "regions" in summary
    assert (tmp_path / "model_hierarchy_evaluation.json").exists()
    assert (tmp_path / "model_hierarchy_evaluation.md").exists()
