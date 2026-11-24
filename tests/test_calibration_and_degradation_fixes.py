"""
Regression Tests for Issue #732: Critical Calibration Regression & Model Degradation Fixes.
Validates:
1. Bias-aware RMSE regional residual std & strict PIT as_of_date filtering (no future leakage).
2. Adaptive Conformal Inference (ACI) alpha adaptation & distribution-shift tail expansion.
3. Calibration residual cascade for sparse regions (3..9 live rows do not collapse to default_std).
4. Validation-gated hybrid-vs-quant skill shrinkage and persistence degradation guardrail.
5. Authentic EIA retail history & AsymmetricECM fitting for Newark_DE, Charlotte_NC, Port_St_Lucie_FL.
"""

import numpy as np
import pandas as pd
import pytest

from src.models import (
    AdaptiveConformalInference,
    apply_validation_performance_gating,
    compute_conformal_prediction_intervals,
    enforce_forecast_plausibility_gate,
)
from src.prediction_logger import (
    compute_adaptive_conformal_alpha,
    compute_regional_residual_std,
    filter_evaluated_history_by_window,
    get_regional_calibration_residuals,
    log_predictions,
)
from src.asymmetric_ecm import AsymmetricECM
from src.locations.newark.regional import _generate_synthetic_newark_data
from src.locations.charlotte.regional import _generate_synthetic_charlotte_data
from src.locations.port_st_lucie.regional import _generate_synthetic_port_st_lucie_data


@pytest.fixture(autouse=True)
def isolate_testing_env(monkeypatch):
    monkeypatch.setenv("TESTING", "1")


def test_compute_regional_residual_std_captures_systematic_bias():
    """
    When a region has a persistent basis bias (e.g., actual = pred + $0.30 +/- $0.02),
    centered std is ~$0.02 (collapsing 95% CI to +/- $0.04 -> 0% coverage).
    RMSE-based residual std must reflect total error (~$0.30).
    """
    rows = []
    for i in range(15):
        rows.append({
            "forecast_target_date": f"2026-10-{i + 1:02d}",
            "forecast_horizon_days": 5,
            "region": "Biased_Metro",
            "actual_5d_price": 4.00 + 0.01 * (i % 3),
            "predicted_5d_price": 3.70 + 0.01 * (i % 3),
            "is_retroactive_backtest": False,
        })
    df = pd.DataFrame(rows)

    res_std = compute_regional_residual_std(region="Biased_Metro", window_days=30, horizon_days=5, df=df)
    assert res_std >= 0.29, f"Expected bias-aware RMSE >= 0.29, got {res_std}"


def test_filter_evaluated_history_enforces_pit_as_of_date():
    """Verify as_of_date strictly excludes observations whose target_date lies in the future."""
    df = pd.DataFrame([
        {
            "forecast_target_date": "2026-10-05",
            "forecast_horizon_days": 5,
            "region": "National",
            "actual_5d_price": 2.50,
            "predicted_5d_price": 2.45,
            "is_retroactive_backtest": False,
        },
        {
            "forecast_target_date": "2026-10-20",
            "forecast_horizon_days": 5,
            "region": "National",
            "actual_5d_price": 3.50,
            "predicted_5d_price": 2.50,
            "is_retroactive_backtest": False,
        },
    ])

    pit_df = filter_evaluated_history_by_window(df, window_days=60, region="National", as_of_date="2026-10-10")
    assert len(pit_df) == 1
    assert pit_df.iloc[0]["forecast_target_date"] == "2026-10-05"


def test_conformal_intervals_widen_under_shift_and_small_samples():
    """
    When ACI lowers alpha below target_alpha after misses (forcing k > n),
    compute_conformal_prediction_intervals must widen beyond the historical max residual
    rather than clipping flat at sorted_residuals[-1].
    """
    resids = np.array([0.05, 0.08, 0.10, 0.12, 0.14, 0.15, 0.16, 0.18, 0.19, 0.20])
    low_static, high_static = compute_conformal_prediction_intervals(3.50, resids, alpha=0.05, target_alpha=0.05)
    low_shifted, high_shifted = compute_conformal_prediction_intervals(3.50, resids, alpha=0.01, target_alpha=0.05)

    hw_static = float(high_static - low_static) / 2.0
    hw_shifted = float(high_shifted - low_shifted) / 2.0
    assert hw_shifted > hw_static
    assert hw_shifted > 0.20

    # Also validate AdaptiveConformalInference.compute_interval forwards target_alpha
    aci = AdaptiveConformalInference(target_alpha=0.05, gamma=0.02, initial_alpha=0.05)
    for _ in range(5):
        aci.update(y_true=4.50, lower_bound=3.30, upper_bound=3.70)
    assert aci.current_alpha < 0.05
    low_aci, high_aci = aci.compute_interval(3.50, resids)
    assert (float(high_aci - low_aci) / 2.0) > 0.20


def test_calibration_residuals_cascade_and_adaptive_alpha_pit():
    """
    Regions with 4 live rows (<10) should cascade cleanly rather than returning empty,
    and compute_adaptive_conformal_alpha should decrease alpha after a streak of misses.
    """
    rows = []
    # 15 retroactive rows + 4 recent live rows with misses
    for i in range(15):
        rows.append({
            "forecast_target_date": f"2026-08-{i + 1:02d}",
            "forecast_horizon_days": 5,
            "region": "Sparse_Metro",
            "actual_5d_price": 3.20,
            "predicted_5d_price": 3.00,
            "within_95ci_hit": 1.0,
            "is_retroactive_backtest": True,
        })
    for i in range(6):
        rows.append({
            "forecast_target_date": f"2026-10-{i + 1:02d}",
            "forecast_horizon_days": 5,
            "region": "Sparse_Metro",
            "actual_5d_price": 3.55,
            "predicted_5d_price": 3.10,
            "within_95ci_hit": 0.0,
            "is_retroactive_backtest": False,
        })
    df = pd.DataFrame(rows)

    resids = get_regional_calibration_residuals(
        region="Sparse_Metro",
        horizon_days=5,
        window_days=60,
        min_samples=10,
        as_of_date="2026-10-10",
        df=df,
    )
    assert len(resids) >= 6
    assert float(np.max(resids)) >= 0.44

    eff_alpha = compute_adaptive_conformal_alpha(
        region="Sparse_Metro",
        target_alpha=0.05,
        gamma=0.02,
        as_of_date="2026-10-10",
        df=df,
    )
    assert eff_alpha < 0.05


def test_log_predictions_uses_adaptive_conformal_for_biased_region(tmp_path, monkeypatch):
    """Verify log_predictions computes widened PIT-safe adaptive conformal bounds for a biased region."""
    import src.prediction_logger as pl

    csv_path = str(tmp_path / "prediction_history.csv")
    monkeypatch.setattr(pl, "HISTORY_CSV_PATH", csv_path)

    # Seed matured live history with systematic $0.35 error and prior misses
    seed_rows = []
    for i in range(12):
        seed_rows.append({
            "forecast_id": f"seed_{i}",
            "issued_at_utc": f"2026-10-{i + 1:02d}T04:00:00Z",
            "log_timestamp": f"2026-10-{i + 1:02d} 04:00:00",
            "forecast_target_date": f"2026-10-{i + 2:02d}",
            "forecast_horizon_days": 1,
            "region": "Newark_DE",
            "model_version": "v1.6-Ipatieff-ECM-NewarkDE-Ridge",
            "run_type": "LIVE_PROSPECTIVE",
            "headline_trigger": "",
            "current_base_price": 3.70,
            "predicted_5d_price": 3.70,
            "predicted_direction": "UP",
            "actual_5d_price": 4.05,
            "actual_direction": "UP",
            "error_dollars": 0.35,
            "directional_hit": 1.0,
            "llm_price_pressure": 0.0,
            "llm_supply_disruption": 0.0,
            "quant_baseline_5d_price": 3.70,
            "llm_augmentation_delta": 0.0,
            "prediction_lower_95ci": 3.60,
            "prediction_upper_95ci": 3.80,
            "within_95ci_hit": 0.0,
            "data_source_provenance": "eia_retail_feed:Newark_DE",
            "is_retroactive_backtest": False,
        })
    pd.DataFrame(seed_rows).to_csv(csv_path, index=False)

    new_pred = pd.DataFrame([{
        "date": "2026-10-15",
        "current_price": 3.70,
        "predicted_5d_price": 3.72,
        "quant_baseline_5d_price": 3.71,
        "forecast_horizon_days": 1,
        "is_retroactive_backtest": False,
    }])
    n_logged = log_predictions(
        new_pred,
        region="Newark_DE",
        model_version="v1.6-Ipatieff-ECM-NewarkDE-Ridge",
        run_type="LIVE_PROSPECTIVE",
        forecast_horizon_days=1,
        is_retroactive_backtest=False,
    )
    assert n_logged == 1
    out_df = pd.read_csv(csv_path)
    last_row = out_df.iloc[-1]
    hw = (float(last_row["prediction_upper_95ci"]) - float(last_row["prediction_lower_95ci"])) / 2.0
    # Must cover the $0.35 error regime (not collapse to $0.0537 default_std!)
    assert hw >= 0.35, f"Expected adaptive conformal half-width >= 0.35, got {hw}"


def test_validation_performance_gating_prevents_degraded_hybrid_blowup():
    """
    When hybrid validation MAE degrades relative to quant validation MAE (>=5% worse),
    apply_validation_performance_gating shrinks the event delta to 0 (pure quant).
    When effective model also underperforms persistence, shrinks toward base_price.
    """
    # Case 1: Hybrid 10% worse than quant, quant beats persistence -> falls back to pure quant
    pred, meta = apply_validation_performance_gating(
        raw_hybrid_price=2.76,
        raw_quant_price=2.63,
        base_price=2.60,
        hybrid_val_mae=0.140,
        quant_val_mae=0.120,
        persistence_val_mae=0.125,
    )
    assert meta["validation_gated"] is True
    assert meta["validation_event_weight"] == 0.0
    assert meta["validation_model_weight"] == 1.0
    assert pred == pytest.approx(2.63, abs=1e-4)

    # Case 2: Both hybrid and quant beat persistence, hybrid beats quant -> full hybrid preserved
    pred2, meta2 = apply_validation_performance_gating(
        raw_hybrid_price=2.76,
        raw_quant_price=2.63,
        base_price=2.60,
        hybrid_val_mae=0.100,
        quant_val_mae=0.115,
        persistence_val_mae=0.125,
    )
    assert meta2["validation_gated"] is False
    assert meta2["validation_event_weight"] == 1.0
    assert meta2["validation_model_weight"] == 1.0
    assert pred2 == pytest.approx(2.76, abs=1e-4)

    # Case 3: Effective model worse than persistence -> blended toward base_price
    pred3, meta3 = apply_validation_performance_gating(
        raw_hybrid_price=2.80,
        raw_quant_price=2.80,
        base_price=2.60,
        hybrid_val_mae=0.150,
        quant_val_mae=0.150,
        persistence_val_mae=0.120,
    )
    assert meta3["validation_gated"] is True
    assert meta3["validation_model_weight"] < 1.0
    assert 2.60 < pred3 < 2.80


def test_plausibility_gate_horizon_scaled_floor():
    """Verify 1-day plausibility divergence bound is tighter than 5-day bound."""
    p_1d, gated_1d, _ = enforce_forecast_plausibility_gate(
        hybrid_pred_price=2.75,
        quant_pred_price=2.60,
        base_price=2.60,
        horizon_days=1,
        residual_std=0.05,
    )
    assert gated_1d is True
    assert p_1d < 2.75

    p_5d, gated_5d, _ = enforce_forecast_plausibility_gate(
        hybrid_pred_price=2.75,
        quant_pred_price=2.60,
        base_price=2.60,
        horizon_days=5,
        residual_std=0.05,
    )
    assert gated_5d is False
    assert p_5d == pytest.approx(2.75, abs=1e-4)


@pytest.mark.parametrize(
    "gen_fn,col_name,live_price",
    [
        (_generate_synthetic_newark_data, "newark_retail_gasoline", 3.75),
        (_generate_synthetic_charlotte_data, "charlotte_retail_gasoline", 3.15),
        (_generate_synthetic_port_st_lucie_data, "port_st_lucie_retail_gasoline", 3.45),
    ],
)
def test_regional_series_support_asymmetric_ecm_fitting(gen_fn, col_name, live_price):
    """
    Verify Newark_DE, Charlotte_NC, and Port_St_Lucie_FL retail series preserve non-zero spread
    variance so AsymmetricECM fits cleanly instead of failing with synthetic constant-margin rejection.
    """
    df = gen_fn("2025-01-01", "2025-06-30", live_current_price=live_price)
    assert pytest.approx(df[col_name].iloc[-1], rel=1e-3) == live_price
    spread_var = float(np.var(df[col_name].values - df["gasoline_rbob"].values))
    assert spread_var >= 1e-6

    ecm = AsymmetricECM(wholesale_lags=3, retail_lags=2)
    ecm.fit(retail_data=df[col_name], wholesale_series=df["gasoline_rbob"])
    assert ecm.is_fitted is True
