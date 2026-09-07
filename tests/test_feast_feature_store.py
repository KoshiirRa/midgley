"""
Unit tests for Issue #94: Feast Feature Store for Point-in-Time Backtesting Correctness
Tests Feast initialization, Parquet file source exports, FeatureViews,
point-in-time (AS OF) temporal join correctness, and model integration.
"""

import os
import tempfile
import pytest
import pandas as pd
import numpy as np

from src.feast_store import MidgleyFeastStore
from src.feature_engineering import create_feature_matrix, get_feast_point_in_time_features
from src.models import train_models_with_feast_point_in_time

try:
    import pyarrow
    HAS_PARQUET = True
except ImportError:
    try:
        import fastparquet
        HAS_PARQUET = True
    except ImportError:
        HAS_PARQUET = False


def test_feast_store_initialization():
    """Verify MidgleyFeastStore initializes directory structure and feature_store.yaml."""
    with tempfile.TemporaryDirectory() as tmpdir:
        store = MidgleyFeastStore(repo_path=tmpdir)
        assert os.path.exists(os.path.join(tmpdir, "feature_store.yaml"))
        assert os.path.exists(os.path.join(tmpdir, "feast_parquet"))


@pytest.mark.skipif(not HAS_PARQUET, reason="pyarrow or fastparquet required for Feast parquet tests")
def test_prepare_parquet_sources():
    """Verify prepare_parquet_sources exports EIA, FRED, NOAA, and LLM decay Parquet files."""
    dates = pd.date_range("2026-01-01", periods=10, freq="D")
    market_df = pd.DataFrame({
        "date": dates,
        "gasoline_rbob": [2.50 + i * 0.02 for i in range(10)],
        "wti_crude": [70.0 + i * 0.5 for i in range(10)],
        "heating_oil": [2.20 + i * 0.01 for i in range(10)]
    })
    events_df = pd.DataFrame({
        "date": dates[:3],
        "geopolitical_risk": [0.8, 0.4, 0.2],
        "supply_disruption": [0.0, 0.5, 0.0]
    })

    with tempfile.TemporaryDirectory() as tmpdir:
        store = MidgleyFeastStore(repo_path=tmpdir)
        paths = store.prepare_parquet_sources(market_df, events_df, region="Tulsa_OK")
        
        assert "eia" in paths
        assert "fred" in paths
        assert "noaa" in paths
        assert "llm_decay" in paths

        for name, pth in paths.items():
            assert os.path.exists(pth)
            df_parquet = pd.read_parquet(pth)
            assert "event_timestamp" in df_parquet.columns
            assert "created_timestamp" in df_parquet.columns


@pytest.mark.skipif(not HAS_PARQUET, reason="pyarrow or fastparquet required for Feast parquet tests")
def test_point_in_time_join_correctness():
    """
    Verifies point-in-time (AS OF) join semantics:
    Guarantees that an observation published at timestamp t2 is NOT leaked
    when querying historical features for an entity at timestamp t1 < t2.
    """
    t1 = pd.Timestamp("2026-01-05")
    t2 = pd.Timestamp("2026-01-10")

    market_df = pd.DataFrame({
        "date": [t1, t2],
        "gasoline_rbob": [2.50, 3.50],
        "wti_crude": [70.0, 90.0]
    })

    with tempfile.TemporaryDirectory() as tmpdir:
        store = MidgleyFeastStore(repo_path=tmpdir)
        store.prepare_parquet_sources(market_df, region="Tulsa_OK")

        entity_df = pd.DataFrame({
            "event_timestamp": [t1],
            "location_id": ["Tulsa_OK"],
            "market_id": ["RBOB_FUTURES"]
        })

        feature_refs = ["eia_weekly_fv:gasoline_rbob", "eia_weekly_fv:wti_crude"]
        result = store.get_historical_point_in_time_features(
            entity_df=entity_df,
            feature_refs=feature_refs,
            region="Tulsa_OK"
        )

        assert not result.empty
        # Verify that at timestamp t1, gasoline_rbob is 2.50 (not 3.50 from t2)
        retrieved_gas = result.loc[0, "gasoline_rbob"]
        assert abs(retrieved_gas - 2.50) < 1e-4, f"Data leakage detected! Expected 2.50 at t1, got {retrieved_gas}"


def test_feature_engineering_feast_integration():
    """Verify get_feast_point_in_time_features and create_feature_matrix(use_feast=True)."""
    dates = pd.date_range("2026-01-01", periods=30, freq="B")
    market_df = pd.DataFrame({
        "date": dates,
        "gasoline_rbob": [2.50 + i * 0.01 for i in range(30)],
        "wti_crude": [70.0 + i * 0.2 for i in range(30)]
    })

    feat_df = create_feature_matrix(market_df, use_feast=True)
    assert not feat_df.empty
    assert "rbob_rsi_14" in feat_df.columns


def test_models_train_with_feast():
    """Verify train_models_with_feast_point_in_time executes model training pipeline."""
    dates = pd.date_range("2026-01-01", periods=40, freq="B")
    market_df = pd.DataFrame({
        "date": dates,
        "gasoline_rbob": [2.50 + i * 0.01 for i in range(40)],
        "wti_crude": [70.0 + i * 0.2 for i in range(40)]
    })

    results = train_models_with_feast_point_in_time(market_df, forecast_horizon=5)
    assert results["status"] == "success"
    assert "ridge_metrics" in results
    assert "MAE" in results["ridge_metrics"]
    assert results["used_feast"] is True
