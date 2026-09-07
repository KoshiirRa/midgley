"""
Pytest Test Suite for Microsoft Qlib & RD-Agent Architecture Integration (Issue #127)
Tests Qlib symbolic expression parsing, point-in-time safety, Information Coefficient calculations,
redundancy pruning, and Dynamic Data Grouping Domain Adaptation (DDG-DA).
"""

import os
import json
import pytest
import numpy as np
import pandas as pd

from src.qlib_symbolic_engine import QlibSymbolicEngine, ref, mean_op, std_op, zscore_op, corr_op
from src.alpha_factor_miner import AlphaFactorMiner, calculate_information_coefficient, prune_redundant_factors
from src.ddg_da_adapter import DDGDAAdapter
from src.feature_engineering import create_feature_matrix, prepare_chronological_splits


@pytest.fixture
def sample_market_df():
    np.random.seed(42)
    n = 100
    dates = pd.date_range("2026-01-01", periods=n, freq="B")
    rbob = 2.50 + np.cumsum(np.random.normal(0.001, 0.02, size=n))
    wti = rbob * 28.0 + np.random.normal(0, 1.0, size=n)
    ovx = 25.0 + np.abs(np.cumsum(np.random.normal(0, 0.5, size=n)))
    rigs = 600 + np.cumsum(np.random.randint(-1, 2, size=n))

    return pd.DataFrame({
        "date": dates,
        "gasoline_rbob": rbob,
        "wti_crude": wti,
        "cboe_ovx": ovx,
        "baker_hughes_rigs": rigs
    })


def test_qlib_symbolic_engine_operators(sample_market_df):
    engine = QlibSymbolicEngine()

    # Ref lag test
    s_ref = engine.evaluate_expression("Ref(gasoline_rbob, 2)", sample_market_df)
    assert len(s_ref) == len(sample_market_df)
    assert s_ref.iloc[0] == 0.0
    assert s_ref.iloc[2] == sample_market_df["gasoline_rbob"].iloc[0]

    # Mean test
    s_mean = engine.evaluate_expression("Mean(gasoline_rbob, 5)", sample_market_df)
    assert not s_mean.isna().any()

    # ZScore test
    s_zscore = engine.evaluate_expression("ZScore(gasoline_rbob, 20)", sample_market_df)
    assert not s_zscore.isna().any()

    # Corr test
    s_corr = engine.evaluate_expression("Corr(gasoline_rbob, wti_crude, 10)", sample_market_df)
    assert not s_corr.isna().any()
    assert s_corr.max() <= 1.0 and s_corr.min() >= -1.0


def test_qlib_symbolic_engine_lookahead_safety(sample_market_df):
    with pytest.raises(ValueError, match="Lookahead violation"):
        ref(sample_market_df["gasoline_rbob"], lag=-1)


def test_ast_evaluator_complex_expressions(sample_market_df):
    engine = QlibSymbolicEngine()
    expr = "ZScore(Corr(gasoline_rbob, cboe_ovx, 15), 10)"
    res = engine.evaluate_expression(expr, sample_market_df)
    assert len(res) == len(sample_market_df)
    assert not res.isna().any()


def test_alpha_factor_miner_ic_calculation():
    np.random.seed(42)
    factor = pd.Series(np.random.normal(0, 1, 100))
    target = factor * 0.5 + pd.Series(np.random.normal(0, 0.5, 100))

    ic_dict = calculate_information_coefficient(factor, target)
    assert ic_dict["ic"] > 0.3
    assert ic_dict["rank_ic"] > 0.3
    assert ic_dict["ic_ir"] > 0.0


def test_alpha_factor_miner_pruning():
    np.random.seed(42)
    base_s = pd.Series(np.random.normal(0, 1, 100))
    cand_1 = base_s * 0.99  # Highly correlated
    cand_2 = pd.Series(np.random.normal(0, 1, 100))  # Independent

    cand_df = pd.DataFrame({"cand_1": cand_1, "cand_2": cand_2})
    existing_df = pd.DataFrame({"base_1": base_s})

    pruned = prune_redundant_factors(cand_df, existing_df, max_correlation=0.70)
    assert "cand_1" not in pruned
    assert "cand_2" in pruned


def test_ddg_da_adapter_clustering_and_weighting(sample_market_df):
    adapter = DDGDAAdapter(n_domains=2)
    labels = adapter.fit_domain_grouping(sample_market_df[["gasoline_rbob", "wti_crude", "cboe_ovx"]])
    assert len(labels) == len(sample_market_df)

    weights = adapter.calculate_sample_domain_weights(sample_market_df[["gasoline_rbob", "wti_crude"]], recent_window_size=10)
    assert len(weights) == len(sample_market_df)
    assert np.isclose(np.mean(weights), 1.0, atol=1e-3)


def test_feature_matrix_integration(sample_market_df, tmp_path):
    miner = AlphaFactorMiner()
    mined = miner.mine_alpha_factors(
        sample_market_df,
        target_col="gasoline_rbob",
        forecast_horizon=5,
        min_abs_ic=0.0,
        output_file=str(tmp_path / "alpha_factors.json")
    )
    assert len(mined) > 0
