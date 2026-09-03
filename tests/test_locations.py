"""
Unit Tests for src/locations subpackage registry and location modules.
"""

import pytest
import pandas as pd
from src.locations import (
    LOCATIONS,
    list_locations,
    get_location,
    run_national_pipeline,
    run_tulsa_pipeline,
    run_newark_pipeline,
    run_cincinnati_pipeline,
    run_greenville_pipeline,
    run_charlotte_pipeline,
    run_oakland_pipeline
)
from src.locations.tulsa.regional import fetch_tulsa_market_data, get_tulsa_regional_events, _generate_synthetic_tulsa_data
from src.locations.newark.regional import fetch_newark_market_data, get_newark_regional_events, _generate_synthetic_newark_data
from src.locations.cincinnati.regional import fetch_cincinnati_market_data, get_cincinnati_regional_events, _generate_synthetic_cincinnati_data
from src.locations.greenville.regional import fetch_greenville_market_data, get_greenville_regional_events, _generate_synthetic_greenville_data
from src.locations.charlotte.regional import fetch_charlotte_market_data, get_charlotte_regional_events, _generate_synthetic_charlotte_data
from src.locations.oakland.regional import fetch_oakland_market_data, get_oakland_regional_events, _generate_synthetic_oakland_data, TOTAL_CARB_TAX_BURDEN


def test_locations_registry_structure():
    """Verify that all expected locations are registered with required keys."""
    expected_locations = {"national", "tulsa", "newark", "cincinnati", "greenville", "charlotte", "oakland", "port_st_lucie"}
    registered = set(list_locations())
    assert expected_locations.issubset(registered), f"Missing locations in registry: {expected_locations - registered}"

    for loc_id in expected_locations:
        info = get_location(loc_id)
        assert info["id"] == loc_id
        assert "name" in info
        assert callable(info["run_pipeline"])
        assert callable(info["build_notebook"])
        assert "notebook_filename" in info


def test_tulsa_synthetic_market_data():
    """Verify Tulsa regional data generator creates required feature columns."""
    df = _generate_synthetic_tulsa_data("2024-01-01", "2024-01-31", live_current_price=3.89)
    assert not df.empty
    assert "tulsa_retail_gasoline" in df.columns
    assert "cushing_crude_per_gal" in df.columns
    assert "crack_spread" in df.columns
    assert pytest.approx(df["tulsa_retail_gasoline"].iloc[-1], rel=1e-3) == 3.89


def test_newark_synthetic_market_data():
    """Verify Newark regional data generator creates required feature columns."""
    df = _generate_synthetic_newark_data("2024-01-01", "2024-01-31", live_current_price=3.35)
    assert not df.empty
    assert "newark_retail_gasoline" in df.columns
    assert "brent_crude_per_gal" in df.columns
    assert "delaware_city_crack_spread" in df.columns
    assert pytest.approx(df["newark_retail_gasoline"].iloc[-1], rel=1e-3) == 3.35


def test_cincinnati_synthetic_market_data():
    """Verify Cincinnati dual-state regional data generator creates required OH & KY columns."""
    df = _generate_synthetic_cincinnati_data("2024-01-01", "2024-01-31", live_oh_price=3.450, live_ky_price=3.325)
    assert not df.empty
    assert "cincinnati_oh_retail_gasoline" in df.columns
    assert "cincinnati_ky_retail_gasoline" in df.columns
    assert "oh_ky_tax_spread" in df.columns
    assert "catlettsburg_crack_spread" in df.columns
    assert pytest.approx(df["oh_ky_tax_spread"].iloc[-1], rel=1e-2) == 0.125


def test_greenville_synthetic_market_data():
    """Verify Greenville regional data generator creates required feature columns."""
    df = _generate_synthetic_greenville_data("2024-01-01", "2024-01-31", live_current_price=3.25)
    assert not df.empty
    assert "greenville_retail_gasoline" in df.columns
    assert "selma_rack_crack_spread" in df.columns
    assert pytest.approx(df["greenville_retail_gasoline"].iloc[-1], rel=1e-3) == 3.25


def test_charlotte_synthetic_market_data():
    """Verify Charlotte regional data generator creates required feature columns."""
    df = _generate_synthetic_charlotte_data("2024-01-01", "2024-01-31", live_current_price=3.28)
    assert not df.empty
    assert "charlotte_retail_gasoline" in df.columns
    assert "paw_creek_rack_crack_spread" in df.columns
    assert pytest.approx(df["charlotte_retail_gasoline"].iloc[-1], rel=1e-3) == 3.28


def test_oakland_synthetic_market_data():
    """Verify Oakland & Bay Area regional data generator includes CARB tax burden breakdown."""
    df = _generate_synthetic_oakland_data("2024-01-01", "2024-01-31", live_oakland_price=4.950, live_bayarea_price=5.050)
    assert not df.empty
    assert "oakland_retail_gasoline" in df.columns
    assert "bayarea_avg_retail_gasoline" in df.columns
    assert "total_regulatory_tax_burden" in df.columns
    assert pytest.approx(df["total_regulatory_tax_burden"].iloc[0], rel=1e-3) == TOTAL_CARB_TAX_BURDEN


def test_regional_events_loading():
    """Verify regional events functions return populated DataFrames."""
    tulsa_events = get_tulsa_regional_events()
    newark_events = get_newark_regional_events()
    cincinnati_events = get_cincinnati_regional_events()
    greenville_events = get_greenville_regional_events()
    charlotte_events = get_charlotte_regional_events()
    oakland_events = get_oakland_regional_events()

    for name, ev_df in [
        ("Tulsa", tulsa_events),
        ("Newark", newark_events),
        ("Cincinnati", cincinnati_events),
        ("Greenville", greenville_events),
        ("Charlotte", charlotte_events),
        ("Oakland", oakland_events)
    ]:
        assert isinstance(ev_df, pd.DataFrame), f"{name} events is not a DataFrame"
        assert not ev_df.empty, f"{name} events DataFrame is empty"
        assert "date" in ev_df.columns
        assert "headline" in ev_df.columns
