"""
Truncation-Invariance Regression Test Harness (Issue #568)

Mathematically verifies that feature engineering across all quantitative,
physical alternative, and qualitative decay channels exhibits strict point-in-time
invariance and zero lookahead leakage:

    X_truncated[t] == X_full[t]   for all observation dates t in truncated dataset
"""

import pytest
import numpy as np
import pandas as pd
from unittest.mock import patch

from src.feature_engineering import create_feature_matrix


@pytest.fixture
def synthetic_multimodal_dataset():
    """Generates synthetic 120-day time series for market and events."""
    dates = pd.date_range(start="2026-01-01", periods=120, freq="D")
    
    np.random.seed(42)
    p_rbob = 2.40 + np.cumsum(np.random.normal(0, 0.02, size=len(dates)))
    p_wti = 75.0 + np.cumsum(np.random.normal(0, 0.50, size=len(dates)))
    p_brent = p_wti + 4.0 + np.random.normal(0, 0.10, size=len(dates))
    p_ho = p_rbob + 0.15 + np.random.normal(0, 0.01, size=len(dates))
    
    market_df = pd.DataFrame({
        "date": dates,
        "gasoline_rbob": p_rbob,
        "wti_crude": p_wti,
        "brent_crude": p_brent,
        "heating_oil": p_ho
    })
    
    events_records = []
    for i in range(0, len(dates), 5):
        events_records.append({
            "date": dates[i],
            "headline": f"Synthetic energy event shock at {dates[i].strftime('%Y-%m-%d')}",
            "geopolitical_risk": float(np.random.uniform(-0.5, 0.8)),
            "supply_disruption": float(np.random.uniform(0.0, 0.9)),
            "demand_sentiment": float(np.random.uniform(-0.6, 0.6)),
            "opec_action": float(np.random.uniform(-0.4, 0.7)),
            "overall_price_pressure": float(np.random.uniform(-0.5, 0.5))
        })
    events_df = pd.DataFrame(events_records)
    
    return market_df, events_df


def test_truncation_invariance_national_feature_matrix(synthetic_multimodal_dataset):
    market_df, events_df = synthetic_multimodal_dataset
    
    # Define Cutoff date at Day 80 (out of 120)
    cutoff_date = market_df["date"].iloc[80]
    
    # Truncated dataset up to cutoff_date
    market_truncated = market_df[market_df["date"] <= cutoff_date].copy()
    events_truncated = events_df[events_df["date"] <= cutoff_date].copy()
    
    # Full dataset up to Day 120
    market_full = market_df.copy()
    events_full = events_df.copy()
    
    # Build feature matrices with network mocks
    with patch("src.feature_engineering.fetch_cboe_crude_volatility_ovx", return_value=pd.DataFrame()), \
         patch("src.feature_engineering.fetch_baker_hughes_rig_counts", return_value=pd.DataFrame()):
        feat_truncated = create_feature_matrix(market_truncated, events_truncated, region="National")
        feat_full = create_feature_matrix(market_full, events_full, region="National")
    
    assert not feat_truncated.empty
    assert not feat_full.empty
    
    # Common observation dates available in truncated training set
    common_dates = feat_truncated["date"].unique()
    
    feat_truncated_sub = feat_truncated[feat_truncated["date"].isin(common_dates)].sort_values("date").reset_index(drop=True)
    feat_full_sub = feat_full[feat_full["date"].isin(common_dates)].sort_values("date").reset_index(drop=True)
    
    assert len(feat_truncated_sub) == len(feat_full_sub)
    
    # Feature columns to check for zero lookahead leakage
    target_cols = [c for c in feat_truncated_sub.columns if "target" in c]
    feature_cols = [c for c in feat_truncated_sub.columns if c not in ["date"] + target_cols]
    
    for col in feature_cols:
        if col in feat_full_sub.columns:
            val_trunc = feat_truncated_sub[col].values
            val_full = feat_full_sub[col].values
            
            if np.issubdtype(val_trunc.dtype, np.number):
                valid_mask = ~(np.isnan(val_trunc) | np.isnan(val_full))
                np.testing.assert_allclose(
                    val_trunc[valid_mask],
                    val_full[valid_mask],
                    rtol=1e-5,
                    atol=1e-5,
                    err_msg=f"Lookahead leakage detected in feature column '{col}'!"
                )


def test_truncation_invariance_causal_decay(synthetic_multimodal_dataset):
    market_df, events_df = synthetic_multimodal_dataset
    cutoff_date = market_df["date"].iloc[60]
    
    market_truncated = market_df[market_df["date"] <= cutoff_date].copy()
    events_truncated = events_df[events_df["date"] <= cutoff_date].copy()
    
    with patch("src.feature_engineering.fetch_cboe_crude_volatility_ovx", return_value=pd.DataFrame()), \
         patch("src.feature_engineering.fetch_baker_hughes_rig_counts", return_value=pd.DataFrame()):
        feat_truncated = create_feature_matrix(market_truncated, events_truncated, region="National")
        feat_full = create_feature_matrix(market_df, events_df, region="National")
    
    # Find the latest available date in truncated feature matrix
    latest_common_date = feat_truncated["date"].max()
    
    decay_cols = [c for c in feat_truncated.columns if "decay" in c or "shock" in c or "event" in c]
    for col in decay_cols:
        if col in feat_full.columns:
            trunc_val = feat_truncated[feat_truncated["date"] == latest_common_date][col].values[0]
            full_val = feat_full[feat_full["date"] == latest_common_date][col].values[0]
            assert np.isclose(trunc_val, full_val, atol=1e-6), f"Decay feature {col} differs at {latest_common_date}!"


def test_truncation_invariance_cutoff_row(synthetic_multimodal_dataset):
    """
    Verifies that the final observation row (cutoff row) of a truncated dataset
    has identical feature values to the corresponding historical row in the full dataset (Issue #613 T-33).
    Ensures zero live connector pollution on the cutoff row.
    """
    market_df, events_df = synthetic_multimodal_dataset
    cutoff_date = market_df["date"].iloc[80]

    market_truncated = market_df[market_df["date"] <= cutoff_date].copy()
    events_truncated = events_df[events_df["date"] <= cutoff_date].copy()

    with patch("src.feature_engineering.fetch_cboe_crude_volatility_ovx", return_value=pd.DataFrame()), \
         patch("src.feature_engineering.fetch_baker_hughes_rig_counts", return_value=pd.DataFrame()):
        lbl_trunc, unlbl_trunc = create_feature_matrix(
            market_truncated, events_truncated, region="National", return_unlabelled_frame=True
        )
        lbl_full, unlbl_full = create_feature_matrix(
            market_df, events_df, region="National", return_unlabelled_frame=True
        )

    # In the truncated dataset, cutoff_date is the final row (unlabelled contemporary inference row)
    cutoff_row_trunc = unlbl_trunc[unlbl_trunc["date"] == cutoff_date]
    assert not cutoff_row_trunc.empty, f"Cutoff row {cutoff_date} not found in truncated dataset!"

    # In the full dataset, cutoff_date is at index 80 (part of labelled frame)
    full_matching_row = lbl_full[lbl_full["date"] == cutoff_date]
    if full_matching_row.empty:
        full_matching_row = unlbl_full[unlbl_full["date"] == cutoff_date]
    assert not full_matching_row.empty, f"Matching row {cutoff_date} not found in full dataset!"

    target_cols = [c for c in cutoff_row_trunc.columns if "target" in c]
    feature_cols = [c for c in cutoff_row_trunc.columns if c not in ["date"] + target_cols]

    for col in feature_cols:
        if col in full_matching_row.columns:
            v_trunc = cutoff_row_trunc[col].iloc[0]
            v_full = full_matching_row[col].iloc[0]
            if isinstance(v_trunc, (int, float, np.number)) and isinstance(v_full, (int, float, np.number)):
                if not (np.isnan(v_trunc) and np.isnan(v_full)):
                    np.testing.assert_allclose(
                        v_trunc, v_full, rtol=1e-5, atol=1e-5,
                        err_msg=f"Cutoff row lookahead mismatch in feature column '{col}' at {cutoff_date}!"
                    )

