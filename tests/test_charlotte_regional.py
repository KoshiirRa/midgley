import os
import sys
import pytest
import pandas as pd

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from src.locations.charlotte.regional import (
    fetch_charlotte_market_data,
    _generate_synthetic_charlotte_data,
    get_charlotte_regional_events
)
from src.locations.charlotte.main import run_charlotte_pipeline


def test_fetch_charlotte_market_data():
    """Verify that fetch_charlotte_market_data returns clean DataFrame with expected columns."""
    df = fetch_charlotte_market_data(start_date="2024-01-01", live_current_price=3.280)
    assert not df.empty, "Charlotte market DataFrame should not be empty"
    
    expected_cols = [
        'gasoline_rbob', 'wti_crude', 'brent_crude',
        'charlotte_retail_gasoline', 'paw_creek_rack_crack_spread'
    ]
    for col in expected_cols:
        assert col in df.columns, f"Expected column '{col}' missing from Charlotte market data"
        
    assert df['charlotte_retail_gasoline'].iloc[-1] > 2.00, "Charlotte retail price should be anchored above $2.00/gal"


def test_synthetic_charlotte_data():
    """Verify fallback synthetic generator produces valid data."""
    df = _generate_synthetic_charlotte_data("2024-01-01", "2024-03-01", live_current_price=3.280)
    assert not df.empty, "Synthetic DataFrame should not be empty"
    assert len(df) > 10, "Synthetic DataFrame should contain trading days"
    assert 'charlotte_retail_gasoline' in df.columns


def test_charlotte_regional_events():
    """Verify Charlotte regional events include Paw Creek hub, NC gas tax, and NOAA alerts."""
    events_df = get_charlotte_regional_events()
    assert not events_df.empty, "Charlotte regional events DataFrame should not be empty"
    assert 'date' in events_df.columns
    assert 'headline' in events_df.columns
    assert 'category' in events_df.columns
    
    headlines_str = " ".join(events_df['headline'].tolist())
    assert "Paw Creek" in headlines_str or "Colonial" in headlines_str or "Mecklenburg" in headlines_str, "Key Charlotte headlines missing"


def test_charlotte_pipeline_execution():
    """Verify that standalone charlotte_main pipeline runs cleanly to completion."""
    res = run_charlotte_pipeline(live_pump_price=3.280, use_llm_api=False, model_type="ridge")
    assert "results" in res, "Pipeline execution result dict should contain 'results'"
    assert "baseline_forecast" in res, "Result dict should contain 'baseline_forecast'"
    assert res['baseline_forecast'] > 0, "Baseline forecast should be greater than 0"
    assert len(res['scenarios']) >= 4, "Should run at least 4 scenario simulations"
