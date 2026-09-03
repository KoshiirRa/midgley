import os
import sys
import pytest
import pandas as pd

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from src.locations.greenville.regional import (
    fetch_greenville_market_data,
    _generate_synthetic_greenville_data,
    get_greenville_regional_events
)
from src.locations.greenville.main import run_greenville_pipeline


def test_fetch_greenville_market_data():
    """Verify that fetch_greenville_market_data returns clean DataFrame with expected columns."""
    df = fetch_greenville_market_data(start_date="2024-01-01", live_current_price=3.250)
    assert not df.empty, "Greenville market DataFrame should not be empty"
    
    expected_cols = [
        'gasoline_rbob', 'wti_crude', 'brent_crude',
        'greenville_retail_gasoline', 'selma_rack_crack_spread'
    ]
    for col in expected_cols:
        assert col in df.columns, f"Expected column '{col}' missing from Greenville market data"
        
    assert df['greenville_retail_gasoline'].iloc[-1] > 2.00, "Greenville retail price should be anchored above $2.00/gal"


def test_synthetic_greenville_data():
    """Verify fallback synthetic generator produces valid data."""
    df = _generate_synthetic_greenville_data("2024-01-01", "2024-03-01", live_current_price=3.250)
    assert not df.empty, "Synthetic DataFrame should not be empty"
    assert len(df) > 10, "Synthetic DataFrame should contain trading days"
    assert 'greenville_retail_gasoline' in df.columns


def test_greenville_regional_events():
    """Verify Greenville regional events include Colonial Pipeline Selma/Apex hubs, NC gas tax, and NOAA alerts."""
    events_df = get_greenville_regional_events()
    assert not events_df.empty, "Greenville regional events DataFrame should not be empty"
    assert 'date' in events_df.columns
    assert 'headline' in events_df.columns
    assert 'category' in events_df.columns
    
    headlines_str = " ".join(events_df['headline'].tolist())
    assert "Selma" in headlines_str or "Colonial" in headlines_str or "Pitt" in headlines_str, "Key Greenville headlines missing"


def test_greenville_pipeline_execution():
    """Verify that standalone greenville_main pipeline runs cleanly to completion."""
    res = run_greenville_pipeline(live_pump_price=3.250, use_llm_api=False, model_type="ridge")
    assert "results" in res, "Pipeline execution result dict should contain 'results'"
    assert "baseline_forecast" in res, "Result dict should contain 'baseline_forecast'"
    assert res['baseline_forecast'] > 0, "Baseline forecast should be greater than 0"
    assert len(res['scenarios']) >= 4, "Should run at least 4 scenario simulations"
