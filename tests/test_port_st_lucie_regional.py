"""
Unit Tests for Port St. Lucie, FL Regional Forecasting Module (src/locations/port_st_lucie)
"""

import pytest
import os
import pandas as pd
from src.locations.port_st_lucie.regional import (
    fetch_port_st_lucie_market_data,
    get_port_st_lucie_regional_events,
    _generate_synthetic_port_st_lucie_data
)
from src.locations.port_st_lucie.notebook_builder import build_port_st_lucie_notebook
from src.locations import get_location, list_locations


def test_port_st_lucie_registry_entry():
    """Verify that port_st_lucie is registered in the master locations registry."""
    assert "port_st_lucie" in list_locations()
    info = get_location("port_st_lucie")
    assert info["id"] == "port_st_lucie"
    assert "Port St. Lucie" in info["name"]
    assert callable(info["run_pipeline"])
    assert callable(info["build_notebook"])


def test_port_st_lucie_synthetic_market_data():
    """Verify Port St. Lucie synthetic market data generator produces required feature columns."""
    df = _generate_synthetic_port_st_lucie_data("2024-01-01", "2024-01-31", live_current_price=3.38)
    assert not df.empty
    assert "port_st_lucie_retail_gasoline" in df.columns
    assert "brent_crude_per_gal" in df.columns
    assert "port_st_lucie_rack_crack_spread" in df.columns
    assert pytest.approx(df["port_st_lucie_retail_gasoline"].iloc[-1], rel=1e-3) == 3.38


def test_port_st_lucie_regional_events_merging():
    """Verify Port St. Lucie regional events dataset merges macro news, waterborne logistics, and NOAA weather."""
    df = get_port_st_lucie_regional_events()
    assert not df.empty
    assert "headline" in df.columns
    assert "date" in df.columns
    # Check for Port Everglades or marine offloading headlines
    has_psl_event = df["headline"].str.contains("Port Everglades|St. Lucie|Florida", case=False, regex=True).any()
    assert has_psl_event, "Expected Port Everglades or Florida regional event in dataset"


def test_port_st_lucie_notebook_builder(tmp_path):
    """Verify build_port_st_lucie_notebook creates a valid JSON notebook file."""
    target = os.path.join(tmp_path, "port_st_lucie_nb.ipynb")
    out_path = build_port_st_lucie_notebook(target)
    assert os.path.exists(out_path)
    with open(out_path, "r", encoding="utf-8") as f:
        import json
        nb = json.load(f)
        assert nb["nbformat"] == 4
        assert len(nb["cells"]) >= 4
