"""
Unit Test Suite for Prediction Target Formulations (tests/test_target_formulations.py)
Tests difference, return, and persistence-residual target transforms and price reconstruction. (Issue #360)
"""

import pytest
import numpy as np
import pandas as pd
from src.models import (
    transform_target,
    reconstruct_price_forecasts,
    evaluate_target_formulations
)


def test_target_transforms_and_exact_inversion():
    y_curr = pd.Series([2.50, 3.00, 3.50, 2.80])
    y_fut = pd.Series([2.60, 2.90, 3.70, 2.80])

    # 1. Level
    t_level = transform_target(y_fut, y_curr, target_mode="level")
    rec_level = reconstruct_price_forecasts(t_level, y_curr.values, target_mode="level")
    np.testing.assert_allclose(rec_level, y_fut.values, rtol=1e-5)

    # 2. Difference
    t_diff = transform_target(y_fut, y_curr, target_mode="difference")
    rec_diff = reconstruct_price_forecasts(t_diff, y_curr.values, target_mode="difference")
    np.testing.assert_allclose(rec_diff, y_fut.values, rtol=1e-5)

    # 3. Log Return
    t_ret = transform_target(y_fut, y_curr, target_mode="return")
    rec_ret = reconstruct_price_forecasts(t_ret, y_curr.values, target_mode="return")
    np.testing.assert_allclose(rec_ret, y_fut.values, rtol=1e-4)

    # 4. Persistence Residual
    t_res = transform_target(y_fut, y_curr, target_mode="persistence_residual")
    rec_res = reconstruct_price_forecasts(t_res, y_curr.values, target_mode="persistence_residual")
    np.testing.assert_allclose(rec_res, y_fut.values, rtol=1e-5)


def test_reconstruction_bounds_clipping():
    y_curr = np.array([3.00, 3.00])
    extreme_positive_return = np.array([1.50, -1.50])
    rec = reconstruct_price_forecasts(extreme_positive_return, y_curr, target_mode="return")
    assert 0.10 <= rec[0] <= 20.0
    assert 0.10 <= rec[1] <= 20.0


def test_evaluate_target_formulations():
    np.random.seed(42)
    n = 60
    X = pd.DataFrame({
        "feat_a": np.random.normal(0, 1, n),
        "feat_b": np.random.normal(0, 1, n)
    })
    y_curr = pd.Series(np.linspace(2.5, 3.2, n))
    y_fut = y_curr + 0.05 * X["feat_a"] + np.random.normal(0, 0.01, n)

    X_train, X_test = X.iloc[:40], X.iloc[40:]
    y_tr_fut, y_te_fut = y_fut.iloc[:40], y_fut.iloc[40:]
    y_tr_curr, y_te_curr = y_curr.iloc[:40], y_curr.iloc[40:]

    results = evaluate_target_formulations(
        X_train, y_tr_fut, y_tr_curr,
        X_test, y_te_fut, y_te_curr
    )

    assert "level" in results
    assert "difference" in results
    assert "return" in results
    assert "persistence_residual" in results

    for mode, res in results.items():
        assert "metrics" in res
        assert "MAE" in res["metrics"]
        assert "persistence_uplift_pct" in res
