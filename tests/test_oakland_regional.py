import os
import sys
import pytest
import pandas as pd

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from src.locations.oakland.regional import (
    fetch_oakland_market_data,
    _generate_synthetic_oakland_data,
    get_oakland_regional_events,
    TOTAL_CARB_TAX_BURDEN
)
from src.locations.oakland.main import run_oakland_pipeline


def test_fetch_oakland_market_data():
    """Verify that fetch_oakland_market_data returns clean DataFrame with expected columns and CARB tax burden."""
    df = fetch_oakland_market_data(start_date="2024-01-01", live_oakland_price=4.950, live_bayarea_price=5.050)
    assert not df.empty, "Oakland market DataFrame should not be empty"
    
    expected_cols = [
        'gasoline_rbob', 'wti_crude', 'brent_crude',
        'oakland_retail_gasoline', 'bayarea_avg_retail_gasoline',
        'san_francisco_retail_gasoline', 'san_jose_retail_gasoline', 'north_bay_retail_gasoline',
        'richmond_crack_spread', 'total_regulatory_tax_burden'
    ]
    for col in expected_cols:
        assert col in df.columns, f"Expected column '{col}' missing from Oakland market data"
        
    assert abs(df['total_regulatory_tax_burden'].iloc[-1] - TOTAL_CARB_TAX_BURDEN) < 1e-4, "CARB tax burden should match TOTAL_CARB_TAX_BURDEN"
    assert df['oakland_retail_gasoline'].iloc[-1] > 4.00, "Oakland retail price should be anchored above $4.00/gal"


def test_synthetic_oakland_data():
    """Verify fallback synthetic generator produces valid data."""
    df = _generate_synthetic_oakland_data("2024-01-01", "2024-03-01", live_oakland_price=4.950, live_bayarea_price=5.050)
    assert not df.empty, "Synthetic DataFrame should not be empty"
    assert len(df) > 10, "Synthetic DataFrame should contain trading days"
    assert 'oakland_retail_gasoline' in df.columns


def test_oakland_regional_events():
    """Verify Oakland regional events include Chevron Richmond, CARB, USGS quakes, and NOAA alerts."""
    events_df = get_oakland_regional_events()
    assert not events_df.empty, "Oakland regional events DataFrame should not be empty"
    assert 'date' in events_df.columns
    assert 'headline' in events_df.columns
    assert 'category' in events_df.columns
    
    headlines_str = " ".join(events_df['headline'].tolist())
    assert "Richmond" in headlines_str or "CARB" in headlines_str or "Hayward" in headlines_str, "Key Oakland headlines missing"


def test_oakland_pipeline_execution():
    """Verify that standalone oakland_main pipeline runs cleanly to completion."""
    results = run_oakland_pipeline(live_oakland_price=4.950, live_bayarea_price=5.050, use_llm_api=False, model_type="ridge")
    assert "metrics_hybrid" in results, "Pipeline execution results should contain 'metrics_hybrid'"
    assert "MAE" in results['metrics_hybrid'], "Hybrid metrics should contain MAE"
    assert results['metrics_hybrid']['MAE'] > 0, "MAE should be greater than 0"
