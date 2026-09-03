"""
Unit tests for Purged Group Time Series Cross-Validation & Combinatorial Purged CV (Issue #117).
"""

import numpy as np
import pandas as pd
import pytest
from sklearn.linear_model import Ridge
from sklearn.pipeline import make_pipeline
from sklearn.preprocessing import StandardScaler
from src.models import (
    PurgedGroupTimeSeriesSplit,
    CombinatorialPurgedCV,
    evaluate_model_purged_cv
)
from src.api_server import app
from fastapi.testclient import TestClient

client = TestClient(app)

def test_purged_group_time_series_split():
    """Tests basic splitting, fold counts, and purging overlap condition."""
    n_samples = 100
    X = np.random.randn(n_samples, 5)
    y = np.random.randn(n_samples)

    splitter = PurgedGroupTimeSeriesSplit(n_splits=5, label_horizon_steps=5, embargo_steps=5)
    splits = list(splitter.split(X, y))

    assert len(splits) == 5

    for train_idx, test_idx in splits:
        assert len(train_idx) > 0
        assert len(test_idx) > 0

        # Check no index appears in both train and test
        assert len(set(train_idx).intersection(set(test_idx))) == 0

        # Verify purging: test start and end
        test_min, test_max = min(test_idx), max(test_idx)

        # Observation i in train must not overlap with test evaluation range [test_min, test_max + 5]
        for i in train_idx:
            obs_start, obs_end = i, i + 5
            test_eval_start, test_eval_end = test_min, test_max + 5
            embargo_end = test_eval_end + 5

            overlap = (obs_start <= test_eval_end) and (obs_end >= test_eval_start)
            in_embargo = (test_eval_end <= obs_start < embargo_end)

            assert not overlap, f"Train index {i} overlaps with test range [{test_eval_start}, {test_eval_end}]"
            assert not in_embargo, f"Train index {i} falls in embargo range [{test_eval_end}, {embargo_end}]"


def test_combinatorial_purged_cv():
    """Tests Combinatorial Purged Cross-Validation (CPCV) fold generation and purging."""
    n_samples = 120
    X = np.random.randn(n_samples, 4)
    y = np.random.randn(n_samples)

    splitter = CombinatorialPurgedCV(n_splits=6, n_test_splits=2, label_horizon_steps=5, embargo_steps=5)
    splits = list(splitter.split(X, y))

    # C(6, 2) = 15 combinations
    assert len(splits) == 15

    for train_idx, test_idx in splits:
        assert len(train_idx) > 0
        assert len(test_idx) > 0
        assert len(set(train_idx).intersection(set(test_idx))) == 0


def test_evaluate_model_purged_cv():
    """Tests evaluate_model_purged_cv execution and metric dictionary structure."""
    np.random.seed(42)
    n_samples = 200
    X = np.random.randn(n_samples, 5)
    y = 2.5 + 0.8 * X[:, 0] + np.random.randn(n_samples) * 0.1

    model = make_pipeline(StandardScaler(), Ridge(alpha=1.0))
    res = evaluate_model_purged_cv(
        model=model,
        X=X,
        y=y,
        label_horizon_steps=5,
        embargo_steps=5
    )

    assert res["status"] == "success"
    assert res["n_splits"] == 5
    assert res["mean_mae"] > 0.0
    assert res["mean_rmse"] > 0.0
    assert "mean_directional_accuracy_pct" in res
    assert res["purged_pct"] > 0.0


def test_api_purged_cv_endpoint():
    """Tests GET /api/v1/forecast/purged-cv FastAPI endpoint."""
    resp = client.get("/api/v1/forecast/purged-cv?n_splits=5&label_horizon=5")
    assert resp.status_code == 200
    data = resp.json()

    assert data["status"] == "success"
    assert "purged_cv_evaluation" in data
    eval_data = data["purged_cv_evaluation"]
    assert eval_data["status"] == "success"
    assert eval_data["n_splits"] == 5

    # Test combinatorial option
    resp_comb = client.get("/api/v1/forecast/purged-cv?n_splits=6&combinatorial=true")
    assert resp_comb.status_code == 200
    data_comb = resp_comb.json()
    assert data_comb["purged_cv_evaluation"]["splitter_type"] == "CombinatorialPurgedCV"
