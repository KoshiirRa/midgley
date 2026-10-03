"""
Unit Tests for External Connector Wiring into Feature Matrix (tests/test_connector_wiring.py)
Validates Issue #565: USACE lock delays, PHMSA pipeline benchmarks, and BSEE shut-ins.
"""

import pandas as pd
import numpy as np
import pytest
from src.feature_engineering import create_feature_matrix


def test_external_connectors_in_feature_matrix():
    dates = pd.date_range("2024-01-01", "2024-01-20", freq="B")
    market_df = pd.DataFrame({
        "date": dates,
        "gasoline_rbob": np.linspace(2.40, 2.55, len(dates)),
        "crude_wti": np.linspace(72.0, 75.0, len(dates)),
        "heating_oil": np.linspace(2.70, 2.80, len(dates)),
        "natural_gas": np.linspace(2.50, 2.60, len(dates))
    })

    feat_df = create_feature_matrix(market_df, forecast_horizon=1, region="National")
    
    # Check USACE lock features
    assert "usace_ohio_river_lock_delay_hours" in feat_df.columns
    assert "usace_lock_queue_vessels" in feat_df.columns
    assert not feat_df["usace_ohio_river_lock_delay_hours"].isna().any()

    # Check PHMSA pipeline features
    assert "phmsa_pipeline_disruption_index" in feat_df.columns
    assert "phmsa_historical_outage_severity" in feat_df.columns
    assert not feat_df["phmsa_pipeline_disruption_index"].isna().any()

    # Check BSEE offshore shut-in features
    assert "bsee_gulf_oil_shutin_pct" in feat_df.columns
    assert "bsee_gulf_evacuated_platforms" in feat_df.columns
    assert not feat_df["bsee_gulf_oil_shutin_pct"].isna().any()
