"""
Unit tests for Feature Matrix Integrity, Time-Series Variance, and Connector Status Transparency (Issue #356).
Validates:
1. Open-Meteo degree days, CFTC COT, FERC tariffs, EIA, USDA, and environmental features exhibit non-zero variance across historical training splits.
2. Target label dropping (t+h) does NOT discard historical features or leave them as all-zero vectors.
3. EIADataConnector and USDABiofuelConnector return transparent status tags (OBSERVED, ESTIMATED, or FALLBACK).
4. prepare_chronological_splits includes active EIA and USDA features in quant_features.
"""

import pytest
import numpy as np
import pandas as pd
from datetime import datetime

from src.feature_engineering import create_feature_matrix, prepare_chronological_splits
from src.data_ingestion import EIADataConnector, USDABiofuelConnector


@pytest.fixture
def synthetic_market_data():
    """Generates 90 business days of synthetic market price history."""
    dates = pd.date_range('2025-09-01', periods=90, freq='B')
    np.random.seed(42)
    rbob = 2.40 + np.cumsum(np.random.normal(0.001, 0.02, 90))
    wti = rbob * 30.0 + np.random.normal(0, 0.5, 90)
    return pd.DataFrame({
        'date': dates,
        'gasoline_rbob': rbob,
        'wti_crude': wti
    })


def test_feature_matrix_non_zero_variance(synthetic_market_data):
    """Verifies that physical, weather, COT, tariff, and biofuel features exhibit non-zero variance across splits."""
    feat_df = create_feature_matrix(synthetic_market_data, forecast_horizon=5, region="Tulsa_OK")
    
    # Must have populated rows
    assert len(feat_df) > 50

    splits = prepare_chronological_splits(feat_df, train_ratio=0.8, forecast_horizon=5)
    X_train = splits['X_train_quant']
    X_test = splits['X_test_quant']

    # Continuous features that must have strictly positive variance in training split
    continuous_features = [
        'hdd_5d_rolling',
        'cdd_5d_rolling',
        'cot_rbob_net_speculative',
        'cot_commercial_hedger_ratio',
        'ferc_colonial_line1_tariff_per_bbl',
        'ferc_pipeline_tariff_index_5d',
        'cec_carbob_stocks_thousand_barrels',
        'eia_gasoline_stocks_us_total',
        'eia_refinery_utilization_us_total',
        'usda_ethanol_rack_price',
        'usda_e10_blendstock_offset'
    ]

    for feat in continuous_features:
        assert feat in X_train.columns, f"Feature {feat} missing from X_train"
        assert feat in X_test.columns, f"Feature {feat} missing from X_test"
        
        train_std = float(X_train[feat].std())
        assert train_std > 0.0, f"Feature {feat} has zero variance in training split (std={train_std})"
        assert not X_train[feat].isna().any(), f"Feature {feat} contains NaN values in training split"


def test_eia_connector_status_transparency():
    """Verifies EIADataConnector status returns OBSERVED, ESTIMATED, or FALLBACK."""
    conn = EIADataConnector()
    res = conn.fetch_padd_inventory_and_refinery_data()

    assert "status" in res
    assert res["status"] in ["OBSERVED", "ESTIMATED", "FALLBACK"]
    assert "refinery_utilization" in res
    assert "gasoline_stocks_million_bbl" in res


def test_usda_biofuel_connector_status_transparency():
    """Verifies USDABiofuelConnector status returns OBSERVED, ESTIMATED, or FALLBACK."""
    conn = USDABiofuelConnector()
    res = conn.fetch_ethanol_blendstock_costs()

    assert "status" in res
    assert res["status"] in ["OBSERVED", "ESTIMATED", "FALLBACK"]
    assert "e100_ethanol_rack_price_per_gal" in res
    assert "calculated_e10_blendstock_offset_per_gal" in res


def test_eia_usda_quant_features_inclusion(synthetic_market_data):
    """Verifies EIA and USDA features are actively included in quant_features and hybrid_features."""
    feat_df = create_feature_matrix(synthetic_market_data, forecast_horizon=5)
    splits = prepare_chronological_splits(feat_df, train_ratio=0.8, forecast_horizon=5)

    quant_names = splits['quant_feature_names']
    hybrid_names = splits['hybrid_feature_names']

    expected_additions = [
        'eia_gasoline_stocks_us_total',
        'eia_refinery_utilization_us_total',
        'eia_refinery_net_production_padd1',
        'eia_refinery_net_production_padd3',
        'eia_pipeline_movements_padd3_to_padd1',
        'usda_ethanol_rack_price',
        'usda_rin_d6_credit_value',
        'usda_e10_blendstock_offset'
    ]

    for feat in expected_additions:
        assert feat in quant_names, f"Feature {feat} missing from quant_features"
        assert feat in hybrid_names, f"Feature {feat} missing from hybrid_features"
