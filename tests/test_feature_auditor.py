"""
Unit Tests for Feature Leakage & Factor Decay Auditor (Issue #146)
"""

import os
import json
import tempfile
import numpy as np
import pandas as pd
import pytest

from src.feature_auditor import (
    PointInTimeLeakageAuditor,
    FactorDecayAuditor,
    BacktestOverfittingAuditor,
    FeatureAuditor,
    FeatureAuditReport
)


def test_point_in_time_clean_feature():
    """Verifies that cleanly lagged predictive features receive PASS status."""
    np.random.seed(42)
    n = 100
    prices = 2.50 + np.cumsum(np.random.normal(0, 0.02, n))
    price_series = pd.Series(prices)
    returns = price_series.pct_change().fillna(0.0)

    # Clean lagged feature: signal at t predicts returns at t+1
    clean_feature = returns.shift(1).fillna(0.0) + np.random.normal(0, 0.005, n)

    res = PointInTimeLeakageAuditor.audit_feature_lead_lag(
        feature_series=pd.Series(clean_feature),
        price_returns=returns,
        max_lags=5
    )

    assert res["status"] in ["PASS", "WARN"]
    assert "lead_correlations" in res
    assert "lag_correlations" in res
    assert isinstance(res["contemporaneous_corr"], float)


def test_point_in_time_synthetic_leak():
    """Verifies that a feature with future lookahead leakage triggers WARN/detection."""
    np.random.seed(42)
    n = 100
    prices = 2.50 + np.cumsum(np.random.normal(0, 0.02, n))
    price_series = pd.Series(prices)
    returns = price_series.pct_change().fillna(0.0)

    # Inverted / lookahead leak: feature at t is strongly derived from future returns (t+2)
    # which shows up as strong correlation with backward shift (lead)
    leaky_feature = returns.shift(-2).fillna(0.0) + np.random.normal(0, 0.001, n)

    res = PointInTimeLeakageAuditor.audit_feature_lead_lag(
        feature_series=pd.Series(leaky_feature),
        price_returns=returns,
        max_lags=5,
        threshold_lead_corr=0.30
    )

    # Should detect the anomalous lead/lag structure
    assert res["status"] == "WARN" or res["leakage_detected"] is True
    assert res["max_lag_corr"] > 0.50 or res["max_lead_corr"] > 0.30


def test_factor_decay_curve_fitting():
    """Verifies multi-horizon Spearman Rank IC decay calculation and half-life fitting."""
    np.random.seed(42)
    n = 150
    # Create price series
    prices = 2.40 + np.cumsum(np.random.normal(0.001, 0.02, n))
    price_series = pd.Series(prices)

    # Create synthetic decaying factor
    signal = np.random.normal(0, 1.0, n)
    for i in range(1, len(prices) - 5):
        # Inject positive return correlation decaying over time
        prices[i + 1] += signal[i] * 0.015
        prices[i + 3] += signal[i] * 0.008
        prices[i + 5] += signal[i] * 0.003

    price_series = pd.Series(prices)
    factor_series = pd.Series(signal)

    res = FactorDecayAuditor.evaluate_factor_ic_decay(
        factor_name="test_qualitative_shock",
        factor_series=factor_series,
        price_series=price_series,
        horizons=[1, 3, 5, 10, 14],
        nominal_half_life=4.5
    )

    assert res["status"] in ["PASS", "WARN"]
    assert "horizon_rank_ic" in res
    assert "1D" in res["horizon_rank_ic"]
    assert "5D" in res["horizon_rank_ic"]
    assert res["empirical_half_life_days"] > 0.0
    assert isinstance(res["decay_fit_r2"], float)


def test_cscv_pbo_calculation():
    """Verifies Combinatorial Symmetric Cross-Validation (CSCV) PBO computation."""
    np.random.seed(42)
    n = 80
    X = np.random.randn(n, 5)
    y = 2.5 + 0.5 * X[:, 0] + np.random.randn(n) * 0.1

    res = BacktestOverfittingAuditor.compute_cscv_pbo(X=X, y=y, n_splits=6)

    assert res["status"] in ["PASS", "WARN", "FAIL"]
    assert "pbo" in res
    assert 0.0 <= res["pbo"] <= 1.0
    assert res["combinations_tested"] > 0
    assert "mean_relative_oos_rank" in res


def test_deflated_sharpe_ratio():
    """Verifies Bailey & López de Prado Deflated Sharpe Ratio (DSR) calculation."""
    res = BacktestOverfittingAuditor.compute_deflated_sharpe_ratio(
        estimated_sharpe=1.85,
        num_trials=50,
        var_trials=0.25,
        sample_length=252
    )

    assert "estimated_sharpe" in res
    assert "expected_max_sharpe" in res
    assert "deflated_sharpe_prob" in res
    assert 0.0 <= res["deflated_sharpe_prob"] <= 1.0
    assert isinstance(res["dsr_significant_95"], bool)


def test_feature_auditor_full_matrix():
    """Tests end-to-end FeatureAuditor execution across a feature DataFrame."""
    np.random.seed(42)
    n = 100
    dates = pd.date_range("2026-01-01", periods=n, freq="D")
    base_price = 2.50 + np.cumsum(np.random.normal(0, 0.015, n))

    df = pd.DataFrame({
        "date": dates,
        "gasoline_rbob": base_price,
        "target_rbob_5d": pd.Series(base_price).shift(-5),
        "wti_crude": 75.0 + np.random.normal(0, 2.0, n),
        "cboe_ovx": 30.0 + np.random.normal(0, 2.5, n),
        "geopolitical_risk_shock": np.random.uniform(0.1, 0.8, n),
        "weather_tornado_risk": np.random.uniform(0.0, 0.6, n),
        "refinery_outage_score": np.random.uniform(0.0, 0.5, n)
    })

    auditor = FeatureAuditor(nominal_decay_half_life=4.5)
    report = auditor.audit_feature_matrix(
        feature_df=df,
        target_col="target_rbob_5d",
        price_col="gasoline_rbob",
        horizons=[1, 3, 5, 10]
    )

    assert isinstance(report, FeatureAuditReport)
    audit_dict = report.to_dict()

    assert "summary" in audit_dict
    assert audit_dict["summary"]["total_features"] >= 5
    assert "leakage_audit" in audit_dict
    assert "decay_audit" in audit_dict
    assert "pbo_audit" in audit_dict

    # Test Markdown formatting
    md_text = report.to_markdown()
    assert "# 🔬 Quantitative Feature & Research Validation Audit Report" in md_text
    assert "Point-in-Time Temporal Leakage Findings" in md_text
    assert "Multi-Horizon Factor IC & Decay Half-Life Analysis" in md_text

    # Test JSON file export
    with tempfile.NamedTemporaryFile(suffix=".json", delete=False) as tmp:
        tmp_path = tmp.name

    try:
        report.to_json(tmp_path)
        assert os.path.exists(tmp_path)
        with open(tmp_path, "r", encoding="utf-8") as f:
            loaded_json = json.load(f)
        assert loaded_json["engine"] == "LacunaFeatureAuditor"
    finally:
        if os.path.exists(tmp_path):
            os.remove(tmp_path)
